"""
Experimental Statistical Anomaly Detector.
Identifies crowd behavior that deviates significantly from a calibrated normal baseline
using robust Z-score standard deviations.
"""
import numpy as np

class StatisticalAnomalyDetector:
    def __init__(self, zone_name, baseline_frames=300):
        """
        Initializes the Anomaly Detector for a specific zone.
        Args:
            baseline_frames: Number of frames to use for initial normal calibration.
        """
        self.zone_name = zone_name
        self.baseline_frames = baseline_frames
        
        self.frame_count = 0
        self.history = []
        
        # Calibration metrics
        self.mu = None
        self.sigma = None
        
        self.is_calibrating = True
        
    def evaluate(self, features):
        """
        Evaluates a feature vector: [Density, Movement, DirConsistency, Congestion, Duration]
        Returns:
            anomaly_score (float 0-100)
            is_calibrating (bool)
        """
        x = np.array(features, dtype=float)
        
        if self.frame_count < self.baseline_frames:
            # Calibration Phase: Accumulate history
            self.history.append(x)
            self.frame_count += 1
            return 0.0, True
            
        elif self.frame_count == self.baseline_frames:
            # End of Calibration: Compute mathematical baseline
            hist_array = np.array(self.history)
            self.mu = np.mean(hist_array, axis=0)
            self.sigma = np.std(hist_array, axis=0)
            
            # Free memory
            self.history.clear()
            self.is_calibrating = False
            self.frame_count += 1
            
        # Monitoring Phase
        # Calculate robust Z-scores (add epsilon to prevent division-by-zero on static features)
        epsilon = 1e-5
        z_scores = np.abs(x - self.mu) / (self.sigma + epsilon)
        
        # The severity of the anomaly is driven by the single most deviant feature
        max_z = np.max(z_scores)
        
        # Map unbounded Z-score (0 to ~5.0+) to a bounded 0-100 anomaly score.
        # Uses an exponential decay function so that Z=3 (3 std devs) is roughly 90.9% anomaly score.
        anomaly_score = 100.0 * (1.0 - np.exp(-0.8 * max_z))
        
        return float(anomaly_score), False
