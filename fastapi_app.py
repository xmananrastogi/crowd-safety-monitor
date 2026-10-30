import cv2
import asyncio
import time
import uvicorn
from fastapi import FastAPI, WebSocket, Request, UploadFile, File
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import config
from app.pipeline import CrowdSafetyPipeline
from core.video import VideoStream
import threading
import tempfile
import os
import json
from datetime import datetime
import numpy as np

SNAPSHOT_DIR = "snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Camera Registry & Dynamic Feed Management
CAMERA_REGISTRY = [
    {
        "id": "CAM-01",
        "name": "Concourse Main",
        "description": "High-density pedestrian concourse (35+ tracked)",
        "source": "data/mall_dense_crowd.mp4",
        "type": "video"
    },
    {
        "id": "CAM-02",
        "name": "Bottleneck Corridor",
        "description": "Constricted queue bottleneck corridor",
        "source": "data/temple_queue_crowd.mp4",
        "type": "video"
    },
    {
        "id": "CAM-03",
        "name": "Crosswalk Intersection",
        "description": "Street-level pedestrian scramble crossing",
        "source": "data/crosswalk_dense.mp4",
        "type": "video"
    },
    {
        "id": "CAM-04",
        "name": "Boulevard Choke",
        "description": "Commercial pedestrian shopping boulevard",
        "source": "data/calle_preciados.mp4",
        "type": "video"
    },
    {
        "id": "WEBCAM",
        "name": "Hardware Device",
        "description": "Integrated / USB live camera device",
        "source": 0,
        "type": "device"
    }
]
active_camera_id = "CAM-01"

# Globals to share state between background thread and FastAPI routes
current_frame = None
current_telemetry = {}
new_video_source = "data/mall_dense_crowd.mp4"
snapshot_manifest = []          # List of saved snapshots [{filename, timestamp, risk}]
show_flow_vectors = False       # Toggle for flow overlay
show_heatmap = False            # Toggle for density heatmap overlay
prev_person_count = None        # For trend arrow calculation

# Session history for report generation
session_history = {
    'video_name': 'Live Monitor',
    'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    'risk_timeline': [],       # [{'t': timestamp, 'v': score}]
    'person_timeline': [],     # [{'t': timestamp, 'v': count}]
    'peak_risk': 0.0,
    'peak_persons': 0,
    'peak_asphyxia': 0.0,
    'total_alerts': 0,
    'frames_processed': 0,
    'avg_density': 0.0,
    'density_sum': 0.0,
}

def save_snapshot(frame, risk_score, category, zone):
    """Saves the current frame as a timestamped JPEG snapshot."""
    global snapshot_manifest
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = f"alert_{ts}_risk{int(risk_score)}.jpg"
    filepath = os.path.join(SNAPSHOT_DIR, filename)
    cv2.imwrite(filepath, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    snapshot_manifest.insert(0, {
        "filename": filename,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "risk": round(risk_score, 1),
        "category": category,
        "zone": zone
    })
    # Keep last 50 snapshots only
    snapshot_manifest = snapshot_manifest[:50]

def draw_flow_vectors(frame, flow, step=24):
    """Draws professional optical flow arrows color-coded by magnitude."""
    if flow is None:
        return frame
    h, w = frame.shape[:2]
    ys, xs = np.mgrid[step:h-step:step, step:w-step:step]
    ys = ys.flatten().astype(int)
    xs = xs.flatten().astype(int)
    fxs = flow[ys, xs, 0]
    fys = flow[ys, xs, 1]
    mags = np.sqrt(fxs**2 + fys**2)

    for x, y, fx, fy, mag in zip(xs, ys, fxs, fys, mags):
        if mag < 0.5:  # Skip near-static pixels
            continue
        end_x = int(x + fx * 3)
        end_y = int(y + fy * 3)
        # Color: low magnitude = cyan, high magnitude = red
        t = min(mag / 8.0, 1.0)
        color = (
            int(0   + t * 0),
            int(200 - t * 200),
            int(255 * t)
        )  # Cyan -> Red in BGR
        cv2.arrowedLine(frame, (x, y), (end_x, end_y), color, 1, tipLength=0.4)
    return frame


def draw_density_heatmap(frame, boxes):
    """Draws a smooth density heatmap overlay using Gaussian blobs centered on each person."""
    if boxes is None or len(boxes) == 0:
        return frame
    h, w = frame.shape[:2]
    heatmap = np.zeros((h, w), dtype=np.float32)

    # Radius scales with frame size for consistency
    radius = int(min(h, w) * 0.07)
    if radius < 20:
        radius = 20

    for box in boxes:
        x1, y1, x2, y2 = map(int, box)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        # Gaussian centered on the person
        y_grid, x_grid = np.ogrid[max(0, cy - radius):min(h, cy + radius),
                                   max(0, cx - radius):min(w, cx + radius)]
        dist_sq = (x_grid - cx) ** 2 + (y_grid - cy) ** 2
        gaussian = np.exp(-dist_sq / (2 * (radius / 2.5) ** 2))
        # Accumulate
        y_start, y_end = max(0, cy - radius), min(h, cy + radius)
        x_start, x_end = max(0, cx - radius), min(w, cx + radius)
        heatmap[y_start:y_end, x_start:x_end] += gaussian

    # Normalize to 0-255
    if heatmap.max() > 0:
        heatmap = (heatmap / heatmap.max() * 255).astype(np.uint8)
    else:
        return frame

    # Apply JET colormap (blue = empty, red = packed)
    colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

    # Only overlay where there's actual heat (mask out the blue background)
    mask = heatmap > 10
    mask_3ch = np.stack([mask, mask, mask], axis=-1)

    blended = frame.copy()
    blended[mask_3ch] = cv2.addWeighted(frame, 0.4, colored, 0.6, 0)[mask_3ch]
    return blended


def process_video():
    global current_frame, current_telemetry, new_video_source, prev_person_count, show_flow_vectors, show_heatmap, session_history
    
    current_source = None
    video_stream = None
    pipeline = None
    last_snapshot_risk = 0.0
    
    while True:
        if new_video_source is not None:
            if video_stream is not None:
                video_stream.release()
                
            if new_video_source == "STOP":
                video_stream = None
                current_source = None
                current_telemetry = {}
                prev_person_count = None
            else:
                current_source = new_video_source
                video_stream = VideoStream(current_source)
                pipeline = CrowdSafetyPipeline(video_resolution=(video_stream.width, video_stream.height))
                # Reset session history for new video
                active_cam = next((c for c in CAMERA_REGISTRY if c['id'] == active_camera_id), None)
                vname = active_cam['name'] if active_cam else (os.path.basename(str(current_source)) if current_source else 'Live Monitor')
                session_history = {
                    'video_name': vname,
                    'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'risk_timeline': [],
                    'person_timeline': [],
                    'peak_risk': 0.0,
                    'peak_persons': 0,
                    'peak_asphyxia': 0.0,
                    'total_alerts': 0,
                    'frames_processed': 0,
                    'avg_density': 0.0,
                    'density_sum': 0.0,
                }
                
            new_video_source = None
            
        if video_stream is None:
            blank_image = np.zeros((720, 1280, 3), np.uint8)
            blank_image[:] = (21, 17, 15)
            text = "SYSTEM STANDBY - UPLOAD VIDEO TO BEGIN ANALYSIS"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1)[0]
            text_x = (1280 - text_size[0]) // 2
            text_y = (720 + text_size[1]) // 2
            cv2.putText(blank_image, text, (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX, 0.6, (150, 150, 150), 1)
            ret, buffer = cv2.imencode('.jpg', blank_image)
            current_frame = buffer.tobytes()
            time.sleep(0.1)
            continue
            
        data = video_stream.read_frame()
        if data is None:
            video_stream.release()
            video_stream = VideoStream(current_source)
            continue
            
        results = pipeline.process_frame(data['frame'], data['frame_number'], data['timestamp_ms'])
        if results is None:
            continue
            
        # --- Draw frame ---
        frame = data['frame']
        frame = pipeline.zone_manager.draw_zones(frame)

        # Density heatmap overlay
        if show_heatmap and len(results.get('global_boxes', [])) > 0:
            frame = draw_density_heatmap(frame, results['global_boxes'])

        # Flow vector overlay
        if show_flow_vectors and results.get('flow') is not None:
            frame = draw_flow_vectors(frame, results['flow'])

        frame = pipeline.detector.draw_boxes(frame, results['global_boxes'], results['global_ids'], results['global_confidences'])

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        current_frame = buffer.tobytes()

        # --- Telemetry ---
        zones_data = results['zones']
        if zones_data:
            highest_risk_zone_name = max(zones_data.keys(), key=lambda z: zones_data[z]['record']['R_z[n]'])
            rec = zones_data[highest_risk_zone_name]['record']
            risk_score = rec.get('R_z[n]', 0.0)
            category = rec.get('Risk_Category', 'Safe')
            person_count = int(results.get('global_count', len(results.get('global_boxes', []))))

            # Feature 2: Person count trend
            if prev_person_count is None:
                trend = 'stable'
            elif person_count > prev_person_count:
                trend = 'up'
            elif person_count < prev_person_count:
                trend = 'down'
            else:
                trend = 'stable'
            prev_person_count = person_count

            rec['zone'] = highest_risk_zone_name
            rec['fps'] = results['fps']
            rec['person_count'] = person_count
            rec['person_trend'] = trend
            rec['flow_enabled'] = show_flow_vectors
            rec['heatmap_enabled'] = show_heatmap
            rec['camera_id'] = active_camera_id
            active_cam = next((c for c in CAMERA_REGISTRY if c['id'] == active_camera_id), None)
            rec['camera_name'] = active_cam['name'] if active_cam else active_camera_id
            rec['all_zones'] = {
                z: {
                    'risk': round(zones_data[z]['record'].get('R_z[n]', 0.0), 1),
                    'density': round(zones_data[z]['record'].get('D_z[n]', 0.0), 1),
                    'speed': round(zones_data[z]['record'].get('Tracked_Speed_z[n]', 0.0), 1),
                    'persons': int(zones_data[z]['record'].get('D_raw', 0))
                }
                for z in zones_data.keys()
            }
            current_telemetry = rec

            # Session history tracking
            now_str = datetime.now().strftime("%H:%M:%S")
            session_history['frames_processed'] += 1
            density_val = rec.get('D_z[n]', 0.0)
            session_history['density_sum'] += density_val
            session_history['avg_density'] = session_history['density_sum'] / session_history['frames_processed']
            if risk_score > session_history['peak_risk']:
                session_history['peak_risk'] = round(risk_score, 1)
            if person_count > session_history['peak_persons']:
                session_history['peak_persons'] = person_count
            asphyxia_val = float(rec.get('Suffocation_Risk_z[n]', 0.0))
            if asphyxia_val > session_history.get('peak_asphyxia', 0.0):
                session_history['peak_asphyxia'] = round(asphyxia_val, 1)
            # Sample timeline every 30 frames (~1 sec) to keep it manageable
            if session_history['frames_processed'] % 30 == 0:
                session_history['risk_timeline'].append({'t': now_str, 'v': round(risk_score, 1)})
                session_history['person_timeline'].append({'t': now_str, 'v': person_count})

            # Snapshot on critical alert (max 1 per 15 seconds)
            if category == 'High Risk' and (time.time() - last_snapshot_risk) > 15:
                save_snapshot(frame, risk_score, category, highest_risk_zone_name)
                session_history['total_alerts'] += 1
                last_snapshot_risk = time.time()

        time.sleep(0.01)

@app.on_event("startup")
async def startup_event():
    # Start the OpenCV processing loop in a daemon thread so it doesn't block the ASGI server
    thread = threading.Thread(target=process_video, daemon=True)
    thread.start()

def generate_mjpeg():
    global current_frame
    while True:
        if current_frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + current_frame + b'\r\n')
        # Stream at 30 FPS
        time.sleep(1/30)

@app.get("/video_feed")
async def video_feed():
    """Returns a continuous MJPEG stream of the OpenCV frames."""
    return StreamingResponse(generate_mjpeg(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Sends JSON telemetry to the frontend via WebSockets."""
    await websocket.accept()
    try:
        while True:
            if current_telemetry:
                await websocket.send_json(current_telemetry)
            await asyncio.sleep(0.1) # 10 updates per second is plenty
    except Exception as e:
        pass # Client disconnected

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serves the main HUD."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/cameras")
async def get_cameras():
    return JSONResponse(content={
        "active_camera_id": active_camera_id,
        "cameras": CAMERA_REGISTRY
    })

@app.post("/api/cameras/add")
async def add_camera(req: Request):
    global CAMERA_REGISTRY, new_video_source, active_camera_id
    try:
        body = await req.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})
        
    name = (body.get("name") or "").strip() or f"Feed {len(CAMERA_REGISTRY) + 1}"
    source = body.get("source")
    if source is None or str(source).strip() == "":
        return JSONResponse(status_code=400, content={"error": "Source is required"})
        
    source_str = str(source).strip()
    if source_str.isdigit():
        source_val = int(source_str)
        source_type = "device"
    elif source_str.startswith("rtsp://"):
        source_val = source_str
        source_type = "rtsp"
    elif source_str.startswith("http://") or source_str.startswith("https://"):
        source_val = source_str
        source_type = "network"
    else:
        source_val = source_str
        source_type = "file"
        
    cam_id = f"FEED-{len(CAMERA_REGISTRY) + 1:02d}"
    cam_entry = {
        "id": cam_id,
        "name": name,
        "description": body.get("description", "Operator configured feed"),
        "source": source_val,
        "type": source_type
    }
    CAMERA_REGISTRY.append(cam_entry)
    
    if body.get("switch_now", True):
        active_camera_id = cam_id
        new_video_source = source_val
        
    return JSONResponse(content={
        "status": "success",
        "camera": cam_entry,
        "active_camera_id": active_camera_id
    })

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    global new_video_source, active_camera_id, CAMERA_REGISTRY
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    clean_filename = os.path.basename(file.filename)
    dest_path = os.path.join(upload_dir, clean_filename)
    
    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)
        
    cam_id = f"UPL-{len(CAMERA_REGISTRY) + 1:02d}"
    cam_entry = {
        "id": cam_id,
        "name": f"Upload: {clean_filename}",
        "description": f"Operator uploaded video ({len(content)//1024} KB)",
        "source": dest_path,
        "type": "upload"
    }
    CAMERA_REGISTRY.append(cam_entry)
    active_camera_id = cam_id
    new_video_source = dest_path
    
    return {
        "status": "success",
        "filename": clean_filename,
        "camera_id": cam_id,
        "camera": cam_entry
    }

@app.post("/switch_camera")
async def switch_camera(req: Request):
    global new_video_source, active_camera_id
    try:
        body = await req.json()
    except Exception:
        body = {}
        
    cam_id = body.get("camera_id")
    target_source = None
    matched_cam = None
    
    if cam_id:
        for cam in CAMERA_REGISTRY:
            if cam["id"] == cam_id:
                target_source = cam["source"]
                matched_cam = cam
                active_camera_id = cam_id
                break
                
    if target_source is None and "source" in body:
        target_source = body["source"]
        active_camera_id = "CUSTOM"
        
    if target_source is None:
        target_source = CAMERA_REGISTRY[0]["source"]
        active_camera_id = CAMERA_REGISTRY[0]["id"]
        matched_cam = CAMERA_REGISTRY[0]
        
    new_video_source = target_source
    return {
        "status": "success",
        "camera_id": active_camera_id,
        "camera": matched_cam,
        "source": str(target_source)
    }

@app.post("/stop")
async def stop_video():
    global new_video_source
    new_video_source = "STOP"
    return {"status": "success"}

@app.post("/toggle_flow")
async def toggle_flow():
    global show_flow_vectors
    show_flow_vectors = not show_flow_vectors
    return {"flow_enabled": show_flow_vectors}

@app.post("/toggle_heatmap")
async def toggle_heatmap():
    global show_heatmap
    show_heatmap = not show_heatmap
    return {"heatmap_enabled": show_heatmap}

@app.get("/snapshots")
async def list_snapshots():
    return JSONResponse(content=snapshot_manifest)

@app.get("/snapshots/{filename}")
async def get_snapshot(filename: str):
    path = os.path.join(SNAPSHOT_DIR, filename)
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return FileResponse(path, media_type="image/jpeg", filename=filename)

@app.get("/report")
async def generate_report():
    """Returns session analysis data for the report page."""
    return JSONResponse(content={
        'video_name': session_history.get('video_name', 'Live Monitor'),
        'start_time': session_history.get('start_time') or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'duration': f"{session_history['frames_processed'] // 30}s ({session_history['frames_processed']} frames)",
        'peak_risk': session_history['peak_risk'],
        'peak_persons': session_history['peak_persons'],
        'peak_asphyxia': session_history.get('peak_asphyxia', 0.0),
        'avg_density': round(session_history['avg_density'], 1),
        'total_alerts': session_history['total_alerts'],
        'total_snapshots': len(snapshot_manifest),
        'risk_timeline': session_history['risk_timeline'][-180:],  # Last 180 data points
        'person_timeline': session_history['person_timeline'][-180:],
        'snapshots': snapshot_manifest[:20],
    })

@app.get("/report_page", response_class=HTMLResponse)
async def report_page(request: Request):
    return templates.TemplateResponse("report.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8080, reload=True)
