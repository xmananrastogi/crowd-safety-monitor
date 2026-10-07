"""
Manages configurable spatial zones within the camera field of view.
Allows for per-zone extraction of YOLO density and Farnebäck optical flow.
"""
import cv2
import numpy as np

class ZoneManager:
    def __init__(self, zones_config):
        """
        zones_config: dict mapping zone_name to polygon vertices (list of tuples), or None for full frame.
        """
        self.zones = {}
        for name, polygon in zones_config.items():
            if polygon is not None:
                self.zones[name] = np.array(polygon, dtype=np.int32)
            else:
                self.zones[name] = None
                
    @classmethod
    def generate_grid_zones(cls, frame_width, frame_height, rows=4, cols=4, disabled_zones=None):
        """
        Mathematically generates a grid of polygonal zones.
        """
        disabled = disabled_zones or []
        zones = {}
        cell_w = frame_width // cols
        cell_h = frame_height // rows
        
        for r in range(rows):
            for c in range(cols):
                zone_name = f"Zone_{r}_{c}"
                if zone_name in disabled:
                    continue
                    
                x1 = c * cell_w
                y1 = r * cell_h
                x2 = frame_width if c == cols - 1 else (c + 1) * cell_w
                y2 = frame_height if r == rows - 1 else (r + 1) * cell_h
                
                polygon = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
                zones[zone_name] = polygon
                
        return zones
                
    def filter_boxes_by_zone(self, boxes, ids, confidences, zone_name):
        """Returns boxes, ids, and confs that fall inside the specified zone."""
        polygon = self.zones.get(zone_name)
        if polygon is None:
            return boxes, ids, confidences
            
        valid_boxes, valid_ids, valid_confs = [], [], []
        
        # If boxes is empty, just return empty lists
        if boxes is None or len(boxes) == 0:
            return [], [], []
            
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box
            cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            
            # pointPolygonTest returns >0 if inside, 0 if on edge, <0 if outside
            if cv2.pointPolygonTest(polygon, (cx, cy), False) >= 0:
                valid_boxes.append(box)
                if ids is not None and len(ids) > i:
                    valid_ids.append(ids[i])
                if confidences is not None and len(confidences) > i:
                    valid_confs.append(confidences[i])
                    
        return np.array(valid_boxes) if valid_boxes else np.array([]), \
               np.array(valid_ids) if valid_ids else np.array([]), \
               np.array(valid_confs) if valid_confs else np.array([])
               
    def get_zone_flow_mask(self, frame_shape, zone_name):
        """Generates a boolean mask array for the given zone's optical flow extraction."""
        polygon = self.zones.get(zone_name)
        if polygon is None:
            # Full frame
            return np.ones(frame_shape[:2], dtype=bool)
            
        mask = np.zeros(frame_shape[:2], dtype=np.uint8)
        cv2.fillPoly(mask, [polygon], 1)
        return mask.astype(bool)
        
    def draw_zones(self, frame):
        """Draws the spatial zones on the frame."""
        display_frame = frame.copy()
        for name, polygon in self.zones.items():
            if polygon is not None:
                cv2.polylines(display_frame, [polygon], True, (255, 0, 0), 2)
                M = cv2.moments(polygon)
                if M['m00'] != 0:
                    cx = int(M['m10']/M['m00'])
                    cy = int(M['m01']/M['m00'])
                    cv2.putText(display_frame, name, (cx-20, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            else:
                cv2.putText(display_frame, f"Zone: {name} (Global)", (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        return display_frame
