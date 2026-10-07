"""
Handles Farnebäck Optical Flow to estimate crowd motion and congestion signals.
Upgraded to support spatial and crowd masking for robust directional statistics.
"""
import cv2
import numpy as np

class MotionEstimator:
    def __init__(self, fb_params=None, max_expected_motion=5.0):
        """
        Initializes the motion estimator.
        """
        self.prev_gray = None
        self.max_expected_motion = max_expected_motion
        
        self.fb_params = fb_params or {
            'pyr_scale': 0.5, 'levels': 3, 'winsize': 15,
            'iterations': 3, 'poly_n': 5, 'poly_sigma': 1.2, 'flags': 0
        }

    def update_flow(self, frame):
        """
        Calculates the dense optical flow for the entire frame once.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.prev_gray is None:
            self.prev_gray = gray
            return None
            
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray, gray, None,
            pyr_scale=self.fb_params['pyr_scale'],
            levels=self.fb_params['levels'],
            winsize=self.fb_params['winsize'],
            iterations=self.fb_params['iterations'],
            poly_n=self.fb_params['poly_n'],
            poly_sigma=self.fb_params['poly_sigma'],
            flags=self.fb_params['flags']
        )
        self.prev_gray = gray
        return flow

    def estimate_zone_motion(self, flow, mask, person_count, boxes=None):
        """
        Extracts advanced motion statistics strictly within the crowd regions of a specific zone.
        
        Returns:
            dict containing: mean_magnitude, median_magnitude, dominant_direction, directional_consistency, congestion
        """
        # Default empty result
        empty_res = {
            'mean_magnitude': 0.0,
            'median_magnitude': 0.0,
            'dominant_direction': 0.0,
            'directional_consistency': 0.0,
            'congestion': 0.0 if person_count == 0 else 100.0 
        }
        
        if flow is None or person_count == 0:
            return empty_res
            
        # Get dense magnitude and angle (in degrees)
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1], angleInDegrees=True)
        
        # Create Crowd Mask
        crowd_mask = np.zeros(mask.shape, dtype=bool)
        if boxes is not None and len(boxes) > 0:
            crowd_mask_img = np.zeros(mask.shape, dtype=np.uint8)
            for box in boxes:
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(crowd_mask_img, (x1, y1), (x2, y2), 1, -1)
            crowd_mask = crowd_mask_img.astype(bool)
        else:
            # If no boxes provided, default to evaluating the entire zone
            crowd_mask = np.ones(mask.shape, dtype=bool)
            
        # Final Mask: Must be inside the Zone AND inside a Crowd bounding box
        final_mask = mask & crowd_mask
        
        masked_magnitude = magnitude[final_mask]
        masked_angle = angle[final_mask]
        
        if len(masked_magnitude) == 0:
            return empty_res
            
        # Magnitude Stats
        mean_mag = float(np.mean(masked_magnitude))
        median_mag = float(np.median(masked_magnitude))
        
        # Directional Stats (using Mean Resultant Vector)
        rad_angles = np.radians(masked_angle)
        mean_x = np.mean(np.cos(rad_angles))
        mean_y = np.mean(np.sin(rad_angles))
        
        directional_consistency = float(np.sqrt(mean_x**2 + mean_y**2)) # 0.0 to 1.0
        dominant_direction = float(np.degrees(np.arctan2(mean_y, mean_x)) % 360)
        
        # Congestion Estimate
        motion_norm = min(mean_mag / self.max_expected_motion, 1.0)
        congestion = (1.0 - motion_norm) * 100.0
            
        return {
            'mean_magnitude': mean_mag,
            'median_magnitude': median_mag,
            'dominant_direction': dominant_direction,
            'directional_consistency': directional_consistency,
            'congestion': congestion
        }

    def draw_flow_arrows(self, frame, flow, step=16):
        """Visualizes the optical flow field with vectors."""
        display_frame = frame.copy()
        if flow is None:
            return display_frame
            
        h, w = frame.shape[:2]
        y, x = np.mgrid[step/2:h:step, step/2:w:step].reshape(2, -1).astype(int)
        fx, fy = flow[y, x].T
        
        lines = np.vstack([x, y, x + fx, y + fy]).T.reshape(-1, 2, 2)
        lines = np.int32(lines + 0.5)
        
        cv2.polylines(display_frame, lines, 0, (0, 255, 0), 1)
        for (x1, y1), (_x2, _y2) in lines:
            cv2.circle(display_frame, (x1, y1), 1, (0, 255, 0), -1)
            
        return display_frame
        
    def draw_flow_hsv(self, frame, flow):
        """Visualizes the dense optical flow field as an HSV color map (Heatmap)."""
        if flow is None:
            return frame.copy()
            
        hsv = np.zeros_like(frame)
        hsv[..., 1] = 255
        
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        # Hue represents direction
        hsv[..., 0] = ang * 180 / np.pi / 2
        # Value represents magnitude
        hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
        
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        # Blend the heatmap over the original frame
        return cv2.addWeighted(frame, 0.4, bgr, 0.6, 0)

    def draw_zone_dominant_arrows(self, frame, zone_manager, zone_results):
        """
        Draws a thick arrow from the center of each zone indicating the dominant movement direction.
        """
        display_frame = frame.copy()
        
        for zone_name, data in zone_results.items():
            record = data['record']
            density = record.get('D_z[n]', 0.0)
            
            # Only draw if there's meaningful crowd presence
            if density > 5.0:
                magnitude = record.get('M_raw_z[n]', 0.0)
                if magnitude < 0.5:
                    continue # Too static to draw a meaningful arrow
                    
                direction_deg = record.get('Dominant_Dir_z[n]', 0.0)
                direction_rad = np.radians(direction_deg)
                
                # Find geometric center of zone
                zone = zone_manager.zones.get(zone_name)
                if not zone:
                    continue
                    
                poly = zone['polygon']
                M = cv2.moments(poly)
                if M['m00'] != 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])
                    
                    # Scale arrow length by magnitude (clamped)
                    length = min(max(magnitude * 5.0, 20.0), 100.0)
                    end_x = int(cx + length * np.cos(direction_rad))
                    end_y = int(cy + length * np.sin(direction_rad))
                    
                    cv2.arrowedLine(display_frame, (cx, cy), (end_x, end_y), (0, 255, 255), 4, tipLength=0.3)
                    
        return display_frame

class DirectionalAnalyzer:
    """
    Tracks historical direction to detect sudden reversals and chaotic movement.
    Uses circular statistics (Mean Resultant Vector) to avoid 359/1 degree wrap-around bugs.
    """
    def __init__(self, history_size=30, reversal_threshold=135, abrupt_threshold=60, min_magnitude=0.5, min_consistency=0.3):
        self.history_size = history_size
        self.reversal_threshold = reversal_threshold
        self.abrupt_threshold = abrupt_threshold
        self.min_magnitude = min_magnitude
        self.min_consistency = min_consistency
        
        self.angles_x = []
        self.angles_y = []
        
    def _angular_difference(self, a, b):
        diff = abs(a - b) % 360
        return 360 - diff if diff > 180 else diff

    def evaluate(self, current_direction, current_consistency, current_magnitude):
        """
        Returns a string of detected Abnormal Movement Indicators.
        """
        indicators = []
        
        # Evaluate against moving average if we have enough history
        if len(self.angles_x) >= self.history_size // 2:
            mean_x = np.mean(self.angles_x)
            mean_y = np.mean(self.angles_y)
            avg_direction = np.degrees(np.arctan2(mean_y, mean_x)) % 360
            
            diff = self._angular_difference(current_direction, avg_direction)
            
            if current_magnitude > self.min_magnitude:
                if diff > self.reversal_threshold:
                    indicators.append("Sudden Reversal")
                elif diff > self.abrupt_threshold:
                    indicators.append("Abrupt Directional Change")
                    
                if current_consistency < self.min_consistency:
                    indicators.append("Highly Inconsistent Movement")
                    
        # Update circular moving average
        rad = np.radians(current_direction)
        self.angles_x.append(np.cos(rad))
        self.angles_y.append(np.sin(rad))
        
        if len(self.angles_x) > self.history_size:
            self.angles_x.pop(0)
            self.angles_y.pop(0)
            
        return " | ".join(indicators) if indicators else "None"
