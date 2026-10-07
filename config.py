"""
Configuration settings for the Crowd Safety Monitor.
"""

# Video source (0 for webcam, or path to video file)
VIDEO_SOURCE = "data/sample_video.mp4"

# Detection settings
YOLO_MODEL = "yolov8n.pt"  # Using nano model for real-time speed
CONFIDENCE_THRESHOLD = 0.3 # Confidence for person detection
MAX_CAPACITY_PER_ZONE = 50 # Max expected people in a single zone

# Grid and Spatial Zone Settings
USE_GRID = True
GRID_SIZE = (4, 4) # (Rows, Columns)
DISABLED_ZONES = [] # List of zone names to ignore (e.g. ['Zone_0_0', 'Zone_1_1'])

SPATIAL_ZONES = {
    "Global": None # Used if USE_GRID is False. None means the entire frame.
}

# Signal Processing / Filtering Settings
MOVING_AVERAGE_WINDOW = 30 # Number of frames for moving average filter
FPS_ESTIMATE = 30          # Expected frames per second

# Optical Flow Settings
FARNEBACK_PARAMS = {
    'pyr_scale': 0.5,
    'levels': 3,
    'winsize': 15,
    'iterations': 3,
    'poly_n': 5,
    'poly_sigma': 1.2,
    'flags': 0
}
MAX_EXPECTED_MOTION = 5.0 # For congestion normalization

# Risk Equation Weights
WEIGHT_DENSITY = 0.45
WEIGHT_CONGESTION = 0.35
WEIGHT_DURATION = 0.20

# Thresholds
RISK_SAFE_MAX = 30
RISK_WARN_MAX = 60

# Configurable Risk Engine Model
# Options: "Linear", "Interaction", "Persistence"
RISK_MODEL = "Linear"
MOVING_AVERAGE_WINDOW = 30
# EWMA smoothing factor (0.0 to 1.0)
EWMA_ALPHA = 0.1
# Duration Settings
DURATION_THRESHOLD_DENSITY = 75.0      # Experimental density % threshold to start counting duration
DURATION_THRESHOLD_CONGESTION = 50.0   # Experimental congestion % threshold to start counting duration
MIN_DURATION_FRAMES = 30               # Minimum frames before duration becomes an active risk
MAX_DURATION_FRAMES = 30 * 60          # 60 seconds at 30 FPS = 100% Duration score
DURATION_DECAY_RATE = 2                # Rate at which the duration decays when conditions are safe

# Congestion State Machine
STATE_MACHINE_BUFFER = 5.0             # Hysteresis Schmitt Trigger margin
PERSISTENCE_LIMIT_FRAMES = 30          # Frames in DEVELOPING before PERSISTENT CONGESTION

# Alert State System
RISK_ALERT_PERSISTENCE = 5             # Frames risk must stay beyond threshold before state escalation

# Experimental Statistical Anomaly Detector
ENABLE_ANOMALY_DETECTION = True
ANOMALY_BASELINE_FRAMES = 300          # 10 seconds at 30fps to calibrate normal baseline

# Suffocation / Compressive Asphyxia Settings
SUFFOCATION_MIN_DENSITY = 75.0         # Minimum density to even consider suffocation risk
SUFFOCATION_MIN_CONGESTION = 75.0      # Minimum congestion to even consider suffocation risk
