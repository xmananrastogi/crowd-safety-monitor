"""
Configuration settings for the Crowd Safety Monitor.
"""

# Video source (0 for webcam, or path to video file)
VIDEO_SOURCE = "data/sample_video.mp4"

# Detection settings
YOLO_MODEL = "yolov8n.pt"  # Using nano model for real-time speed
CONFIDENCE_THRESHOLD = 0.3 # Confidence for person detection
MAX_CAPACITY = 100         # Max expected people in frame for normalization

# Signal Processing / Filtering Settings
MOVING_AVERAGE_WINDOW = 30 # Number of frames for moving average filter
FPS_ESTIMATE = 30          # Expected frames per second

# Risk Equation Weights
WEIGHT_DENSITY = 0.45
WEIGHT_CONGESTION = 0.35
WEIGHT_DURATION = 0.20

# Thresholds
RISK_SAFE_MAX = 30
RISK_WARN_MAX = 60

# Duration Settings
DURATION_THRESHOLD_DENSITY = 50.0      # Density % threshold to start counting duration
DURATION_THRESHOLD_CONGESTION = 50.0   # Congestion % threshold to start counting duration
MAX_DURATION_FRAMES = 30 * 60          # 60 seconds at 30 FPS = 100% Duration score
