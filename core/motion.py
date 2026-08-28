"""
Handles Farnebäck Optical Flow to estimate crowd motion/congestion.
"""
import cv2
import numpy as np

class MotionEstimator:
    def __init__(self):
        self.prev_gray = None

    def estimate_motion(self, frame, bounding_boxes=None):
        """
        Estimates the magnitude of motion in the frame using Optical Flow.
        If bounding_boxes are provided, it averages motion only within those boxes.
        Returns the average motion magnitude.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.prev_gray is None:
            self.prev_gray = gray
            return 0.0

        # Calculate dense optical flow
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray, gray, None, 
            0.5, 3, 15, 3, 5, 1.2, 0
        )
        
        # Calculate magnitude of the flow vectors
        magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        self.prev_gray = gray

        # If no boxes are provided, calculate global average motion
        if bounding_boxes is None or len(bounding_boxes) == 0:
            return float(np.mean(magnitude))
            
        # Calculate motion localized to detected people
        total_motion = 0
        area_count = 0
        for box in bounding_boxes:
            x1, y1, x2, y2 = map(int, box)
            # Ensure coordinates are within frame bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(gray.shape[1], x2), min(gray.shape[0], y2)
            
            roi_magnitude = magnitude[y1:y2, x1:x2]
            if roi_magnitude.size > 0:
                total_motion += np.sum(roi_magnitude)
                area_count += roi_magnitude.size
                
        if area_count == 0:
            return 0.0
            
        avg_motion = total_motion / area_count
        return float(avg_motion)
