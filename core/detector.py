"""
Handles YOLO person detection to generate the Spatial Density signal D_raw[n].
"""
import cv2
import numpy as np
from ultralytics import YOLO

class PersonDetector:
    def __init__(self, model_path='yolov8n.pt', conf_thresh=0.3):
        """
        Initializes the YOLO object detector.
        Args:
            model_path: Path to the YOLO weights (default uses YOLOv8 nano).
            conf_thresh: Configurable confidence threshold for detections.
        """
        # YOLO will automatically download 'yolov8n.pt' if not present locally.
        self.model = YOLO(model_path)
        self.conf_thresh = conf_thresh
        # COCO dataset class 0 is 'person'
        self.person_class_id = 0 
        
        # Store the discrete-time density signal D_raw[n]
        self.D_raw = []

    def detect(self, frame):
        """
        Detects people in the frame and extracts spatial information.
        
        Args:
            frame: A NumPy array representing the image frame.
            
        Returns:
            count (int): Number of people detected (value for D_raw[n]).
            boxes (list): List of bounding boxes [x1, y1, x2, y2].
            confidences (list): Confidence scores for each detection.
        """
        # Run inference, restricting to the person class
        results = self.model(frame, classes=[self.person_class_id], conf=self.conf_thresh, verbose=False)
        
        boxes = []
        confidences = []
        
        if len(results) > 0:
            # Extract bounding boxes and confidences on CPU
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            
        count = len(boxes)
        
        # Record the count for the discrete-time signal D_raw[n]
        self.D_raw.append(count)
            
        return count, boxes, confidences
        
    def draw_boxes(self, frame, boxes, confidences):
        """
        Draws bounding boxes and confidence scores on a copy of the frame.
        """
        display_frame = frame.copy()
        
        for box, conf in zip(boxes, confidences):
            x1, y1, x2, y2 = map(int, box)
            
            # Draw rectangle
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw confidence label
            label = f"Person: {conf:.2f}"
            cv2.putText(display_frame, label, (x1, max(y1 - 10, 10)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
        return display_frame
        
    def get_density_signal(self):
        """
        Returns the recorded discrete-time density signal D_raw[n].
        """
        return np.array(self.D_raw)
