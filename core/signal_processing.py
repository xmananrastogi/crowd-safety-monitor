"""
Implements Signals & Systems concepts: Discrete-Time Filtering and State tracking.
Provides comparative implementations of FIR (Moving Average) and IIR (EWMA) filters.
"""
import numpy as np
from collections import deque

class SignalProcessor:
    def __init__(self, window_size, ewma_alpha, max_duration_frames, min_duration_frames=30, decay_rate=2):
        self.window_size = window_size
        self.ewma_alpha = ewma_alpha
        
        # FIR: Moving average filter buffers (Low-Pass Filter)
        self.density_buffer = deque(maxlen=window_size)
        self.motion_buffer = deque(maxlen=window_size)
        
        # IIR: Exponentially Weighted Moving Average state
        self.ewma_density = None
        self.ewma_congestion = None
        
        self.max_duration_frames = max_duration_frames
        self.min_duration_frames = min_duration_frames
        self.decay_rate = decay_rate
        
        # Duration accumulator
        self.duration_counter = 0

    @property
    def group_delay_frames(self):
        """
        Calculates the theoretical Group Delay (τ) for the FIR Moving Average filter.
        For a symmetric MA filter of length N, delay is exactly (N-1)/2 samples.
        """
        return (self.window_size - 1) / 2.0

    def process(self, normalized_density, raw_congestion, dur_thresh_d, dur_thresh_c):
        """
        Processes instantaneous measurements into smoothed signals and calculates state.
        Returns both FIR (default) and EWMA (experimental) outputs.
        """
        # 1. FIR Low-Pass Filter
        self.density_buffer.append(normalized_density)
        self.motion_buffer.append(raw_congestion)
        
        fir_density = float(np.mean(self.density_buffer))
        fir_congestion = float(np.mean(self.motion_buffer))
        
        # 2. IIR EWMA Filter
        if self.ewma_density is None:
            # Initialization
            self.ewma_density = normalized_density
            self.ewma_congestion = raw_congestion
        else:
            self.ewma_density = (self.ewma_alpha * normalized_density) + ((1.0 - self.ewma_alpha) * self.ewma_density)
            self.ewma_congestion = (self.ewma_alpha * raw_congestion) + ((1.0 - self.ewma_alpha) * self.ewma_congestion)
        
        # 3. State Tracking: Abnormal Congestion Duration (Using FIR for standard risk logic)
        if fir_density > dur_thresh_d and fir_congestion > dur_thresh_c:
            self.duration_counter += 1
        else:
            self.duration_counter = max(0, self.duration_counter - self.decay_rate)
            
        # 4. Calculate T[n]
        if self.duration_counter < self.min_duration_frames:
            duration_score = 0.0
        else:
            duration_score = min((self.duration_counter / self.max_duration_frames) * 100.0, 100.0)
            
        return {
            'fir_density': fir_density,
            'fir_congestion': fir_congestion,
            'ewma_density': float(self.ewma_density),
            'ewma_congestion': float(self.ewma_congestion),
            'duration_score': duration_score
        }
