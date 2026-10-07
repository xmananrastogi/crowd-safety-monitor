import cv2
import asyncio
import time
import uvicorn
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import config
from app.pipeline import CrowdSafetyPipeline
from core.video import VideoStream
import threading

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Globals to share state between background thread and FastAPI routes
current_frame = None
current_telemetry = {}

def process_video():
    global current_frame, current_telemetry
    
    video_stream = VideoStream(config.VIDEO_SOURCE)
    pipeline = CrowdSafetyPipeline(video_resolution=(video_stream.width, video_stream.height))
    
    while True:
        data = video_stream.read_frame()
        if data is None:
            # Loop video for the demo
            video_stream.release()
            video_stream = VideoStream(config.VIDEO_SOURCE)
            continue
            
        results = pipeline.process_frame(data['frame'], data['frame_number'], data['timestamp_ms'])
        if results is None:
            continue
            
        # Draw on frame
        frame = data['frame']
        frame = pipeline.zone_manager.draw_zones(frame)
        frame = pipeline.detector.draw_boxes(frame, results['global_boxes'], results['global_ids'], results['global_confidences'])
        
        # High tech HUD effect on the video feed
        cv2.putText(frame, "OMNI-EYE SECURE LINK ACTIVE", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
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

if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8000, reload=True)
