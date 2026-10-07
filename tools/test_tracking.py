"""
Headless Demo Script to visually verify robust Multi-Object Tracking.
Generates an annotated MP4 video showcasing trajectory persistence and CSV telemetry.
"""
import cv2
import os
import sys

# Ensure parent dir is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from core.video import VideoStream
from app.pipeline import CrowdSafetyPipeline

def run_tracking_demo():
    print("Starting Robust Tracking Demo...")
    
    # Setup output directory
    os.makedirs('data/output', exist_ok=True)
    
    # We will use Global zone to track everything for the demo
    config.SPATIAL_ZONES = {"Global": None}
    
    video_stream = VideoStream(config.VIDEO_SOURCE)
    
    pipeline = CrowdSafetyPipeline(video_resolution=(video_stream.width, video_stream.height))
    
    # Setup Video Writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_video = None
    
    frame_count = 0
    max_frames = 150 # Process a 5-second snippet to keep it quick
    
    while frame_count < max_frames:
        data = video_stream.read_frame()
        if data is None:
            break
            
        results = pipeline.process_frame(data['frame'], data['frame_number'], data['timestamp_ms'])
        if results is None:
            continue
            
        frame = data['frame']
        
        # 1. Draw Zones
        frame = pipeline.zone_manager.draw_zones(frame)
        
        # 2. Draw Trajectories and Boxes (The new robust tracker visualization)
        frame = pipeline.detector.draw_boxes(frame, results['global_boxes'], results['global_ids'], results['global_confidences'])
        
        # 3. Draw Optical Flow (HSV Heatmap)
        frame = pipeline.motion_estimator.draw_flow_hsv(frame, results['flow'])
        
        # Overlay stats
        cv2.putText(frame, f"TRACKING DEMO | Frame {frame_count}", (20, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Initialize writer once we know the frame size
        if out_video is None:
            h, w = frame.shape[:2]
            out_video = cv2.VideoWriter('data/output/tracking_demo.mp4', fourcc, 30.0, (w, h))
            
        out_video.write(frame)
        frame_count += 1
        print(f"\rProcessed {frame_count}/{max_frames} frames...", end="")
        
    print("\nDemo processing complete.")
    
    if out_video:
        out_video.release()
    video_stream.release()
    
    # Save telemetries
    pipeline.save_to_csv()
    pipeline.save_tracking_csv()
    print("Saved tracking_demo.mp4 and telemetry CSVs to data/output/")

if __name__ == "__main__":
    run_tracking_demo()
