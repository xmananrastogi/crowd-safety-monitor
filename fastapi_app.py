import cv2
import asyncio
import time
import uvicorn
from fastapi import FastAPI, WebSocket, Request, UploadFile, File
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import config
from app.pipeline import CrowdSafetyPipeline
from core.video import VideoStream
import threading
import tempfile
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Globals to share state between background thread and FastAPI routes
current_frame = None
current_telemetry = {}
new_video_source = None

def process_video():
    global current_frame, current_telemetry, new_video_source
    
    current_source = None
    video_stream = None
    pipeline = None
    
    while True:
        if new_video_source is not None:
            if video_stream is not None:
                video_stream.release()
            current_source = new_video_source
            video_stream = VideoStream(current_source)
            pipeline = CrowdSafetyPipeline(video_resolution=(video_stream.width, video_stream.height))
            new_video_source = None
            
        if video_stream is None:
            # Display a waiting placeholder frame
            import numpy as np
            blank_image = np.zeros((720, 1280, 3), np.uint8)
            blank_image[:] = (21, 17, 15) # Dark slate background
            
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
            # Loop video for the demo
            video_stream.release()
            video_stream = VideoStream(current_source)
            continue
            
        results = pipeline.process_frame(data['frame'], data['frame_number'], data['timestamp_ms'])
        if results is None:
            continue
            
        # Draw on frame
        frame = data['frame']
        frame = pipeline.zone_manager.draw_zones(frame)
        frame = pipeline.detector.draw_boxes(frame, results['global_boxes'], results['global_ids'], results['global_confidences'])
        
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        current_frame = buffer.tobytes()
        
        # update telemetry
        zones_data = results['zones']
        if zones_data:
            highest_risk_zone_name = max(zones_data.keys(), key=lambda z: zones_data[z]['record']['R_z[n]'])
            rec = zones_data[highest_risk_zone_name]['record']
            rec['zone'] = highest_risk_zone_name
            rec['fps'] = results['fps']
            current_telemetry = rec
            
        # Throttle processing slightly to prevent CPU maxout
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

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    global new_video_source
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    content = await file.read()
    tfile.write(content)
    tfile.close()
    
    new_video_source = tfile.name
    return {"status": "success", "filename": file.filename}

if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8080, reload=True)
