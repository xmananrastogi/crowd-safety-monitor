"""
Handles YOLO person detection and robust multi-object tracking.
"""
import cv2
import numpy as np
from collections import defaultdict
from ultralytics import YOLO

class PersonDetector:
    def __init__(self, model_path='yolov8n.pt', conf_thresh=0.3, max_trail_len=30):
        """
        Initializes the YOLO object tracker.
        Args:
            model_path: Path to the YOLO weights.
            conf_thresh: Confidence threshold for detections.
            max_trail_len: How many past points to remember for trajectory lines.
        """
        self.model = YOLO(model_path)
        self.conf_thresh = conf_thresh
        self.person_class_id = 0 
        
        # Tracking history for visualization
        self.max_trail_len = max_trail_len
        self.trajectories = defaultdict(list)
        
        self.D_raw = []

    def detect(self, frame):
        """
        Detects and tracks people using ByteTrack.
        
        Returns:
            count (int): Number of people detected.
            boxes (list): List of bounding boxes [x1, y1, x2, y2].
            ids (list): List of unique tracking IDs.
            confidences (list): Confidence scores.
        """
        # Run tracking using ByteTrack
        results = self.model.track(
            frame, 
            classes=[self.person_class_id], 
            conf=self.conf_thresh, 
            persist=True, 
            tracker="bytetrack.yaml", 
            verbose=False
        )
        
        boxes = []
        ids = []
        confidences = []
        
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            if results[0].boxes.id is not None:
                ids = results[0].boxes.id.cpu().numpy()
            
        count = len(boxes)
        self.D_raw.append(count)
        
        # --- Update Trajectory Memory ---
        current_ids = set()
        
        if ids is not None and len(ids) > 0:
            for box, t_id in zip(boxes, ids):
                if t_id is None:
                    continue
                t_id = int(t_id)
                current_ids.add(t_id)
                x1, y1, x2, y2 = box
                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                
                self.trajectories[t_id].append((cx, cy))
                if len(self.trajectories[t_id]) > self.max_trail_len:
                    self.trajectories[t_id].pop(0)
                    
        # Garbage collection: remove disappeared IDs to prevent memory leaks
        stale_ids = list(set(self.trajectories.keys()) - current_ids)
        for s_id in stale_ids:
            del self.trajectories[s_id]
            
        return count, boxes, ids, confidences
        
    def draw_boxes(self, frame, boxes, ids, confidences):
        """
        Draws bounding boxes, tracking IDs, confidence scores, and historical trajectories.
        """
        display_frame = frame.copy()
        
        if ids is None or len(ids) == 0:
            ids = [None] * len(boxes)
            
        for box, t_id, conf in zip(boxes, ids, confidences):
            x1, y1, x2, y2 = map(int, box)
            
            # Draw box
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            id_text = f"ID:{int(t_id)}" if t_id is not None else ""
            label = f"{id_text} {conf:.2f}".strip()
            cv2.putText(display_frame, label, (x1, max(y1 - 10, 10)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
            # Draw trajectory path
            if t_id is not None:
                t_id = int(t_id)
                if t_id in self.trajectories and len(self.trajectories[t_id]) > 1:
                    pts = np.array(self.trajectories[t_id], np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    # Draw a blue trajectory line behind the person
                    cv2.polylines(display_frame, [pts], isClosed=False, color=(255, 0, 0), thickness=2)
                        
        return display_frame
        
    def get_tracking_speeds(self, query_ids):
        """
        Calculates the average movement speed (pixels per frame) of the provided track IDs.
        """
        if query_ids is None or len(query_ids) == 0:
            return 0.0
            
        speeds = []
        for q_id in query_ids:
            if q_id is not None:
                q_id = int(q_id)
                if q_id in self.trajectories and len(self.trajectories[q_id]) >= 2:
                    p1 = self.trajectories[q_id][-2]
                    p2 = self.trajectories[q_id][-1]
                    dist = np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
                    speeds.append(dist)
                    
        if len(speeds) == 0:
            return 0.0
            
        return float(np.mean(speeds))
        
    def get_density_signal(self):
        """Returns the recorded discrete-time density signal D_raw[n]."""
        return np.array(self.D_raw)
