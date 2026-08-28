"""
Implements Signals & Systems concepts: Filtering, Duration tracking, and Risk equation.
"""
import numpy as np
from collections import deque

class SignalProcessor:
    def __init__(self, window_size, max_capacity, max_duration_frames):
        # Moving average filter buffers (Low-Pass Filter)
        self.density_buffer = deque(maxlen=window_size)
        self.motion_buffer = deque(maxlen=window_size)
        
        self.max_capacity = max_capacity
        self.max_duration_frames = max_duration_frames
        
        # Duration accumulator
        self.duration_counter = 0

    def moving_average(self, new_value, buffer):
        """Applies a causal Moving Average (Low-Pass Filter) to the signal."""
        buffer.append(new_value)
        return float(np.mean(buffer))

    def calculate_congestion(self, avg_motion):
        """
        Maps motion magnitude to a 0-100% Congestion signal.
        Low movement = High congestion.
        (This mapping assumes max expected motion magnitude is roughly 5.0 for normalization)
        """
        MAX_EXPECTED_MOTION = 5.0
        motion_norm = min(avg_motion / MAX_EXPECTED_MOTION, 1.0)
        
        # Inverse relationship: Congestion = 1.0 - motion
        congestion_norm = 1.0 - motion_norm
        return congestion_norm * 100.0

    def process(self, raw_person_count, raw_motion, dur_thresh_d, dur_thresh_c):
        """
        Processes instantaneous measurements into smoothed signals and calculates state.
        """
        # 1. Normalize Density (0-100%)
        raw_density = min((raw_person_count / self.max_capacity) * 100.0, 100.0)
        
        # 2. Convert Motion to Congestion (0-100%)
        raw_congestion = self.calculate_congestion(raw_motion)
        
        # 3. Apply Low-Pass Filter (Temporal Smoothing)
        smoothed_density = self.moving_average(raw_density, self.density_buffer)
        smoothed_congestion = self.moving_average(raw_congestion, self.motion_buffer)
        
        # 4. State Tracking: Congestion Duration
        if smoothed_density > dur_thresh_d and smoothed_congestion > dur_thresh_c:
            self.duration_counter += 1
        else:
            # Decay duration if conditions improve
            self.duration_counter = max(0, self.duration_counter - 2)
            
        duration_score = min((self.duration_counter / self.max_duration_frames) * 100.0, 100.0)
        
        return smoothed_density, smoothed_congestion, duration_score

    def calculate_risk(self, density, congestion, duration, w_d, w_c, w_t):
        """Calculates the Risk index based on the proposed weighted equation."""
        risk = (w_d * density) + (w_c * congestion) + (w_t * duration)
        return min(risk, 100.0)
        
    def get_risk_category(self, risk_score, safe_max, warn_max):
        """Classifies the numerical risk into discrete states."""
        if risk_score <= safe_max:
            return "Safe"
        elif risk_score <= warn_max:
            return "Warning"
        else:
            return "High Risk"
