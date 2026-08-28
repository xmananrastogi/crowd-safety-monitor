"""
Orchestrates the data flow between video ingestion, processing, and output.
"""
import cv2
import config
from core.video import VideoStream
from core.detector import PersonDetector
from core.motion import MotionEstimator
from core.signal_processing import SignalProcessor

class CrowdSafetyPipeline:
    def __init__(self):
        # Initialize components
        self.detector = PersonDetector(config.YOLO_MODEL, config.CONFIDENCE_THRESHOLD)
        self.motion_estimator = MotionEstimator()
        
        self.signal_processor = SignalProcessor(
            window_size=config.MOVING_AVERAGE_WINDOW,
            max_capacity=config.MAX_CAPACITY,
            max_duration_frames=config.MAX_DURATION_FRAMES
        )

    def process_frame(self, frame):
        """
        Runs the full pipeline on a single frame.
        """
        # 1. Spatial Processing (YOLO)
        person_count, boxes = self.detector.detect(frame)
        
        # 2. Temporal Processing (Optical Flow)
        avg_motion = self.motion_estimator.estimate_motion(frame, boxes)
        
        # 3. Signal Processing (Smoothing & State Tracking)
        smoothed_density, smoothed_congestion, duration_score = self.signal_processor.process(
            person_count, 
            avg_motion,
            config.DURATION_THRESHOLD_DENSITY,
            config.DURATION_THRESHOLD_CONGESTION
        )
        
        # 4. Risk Calculation
        risk_score = self.signal_processor.calculate_risk(
            smoothed_density, 
            smoothed_congestion, 
            duration_score,
            config.WEIGHT_DENSITY,
            config.WEIGHT_CONGESTION,
            config.WEIGHT_DURATION
        )
        
        risk_category = self.signal_processor.get_risk_category(
            risk_score, 
            config.RISK_SAFE_MAX, 
            config.RISK_WARN_MAX
        )
        
        return {
            'boxes': boxes,
            'density': smoothed_density,
            'congestion': smoothed_congestion,
            'duration': duration_score,
            'risk_score': risk_score,
            'risk_category': risk_category
        }
