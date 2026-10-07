import unittest
from unittest.mock import MagicMock
import numpy as np

import config
from app.pipeline import CrowdSafetyPipeline

class TestCrowdScenarios(unittest.TestCase):
    
    def setUp(self):
        # 1. Standardize Experimental Configuration for predictable testing
        config.MAX_CAPACITY_PER_ZONE = 100
        config.SPATIAL_ZONES = {"Global": None}
        config.MOVING_AVERAGE_WINDOW = 5
        config.DURATION_THRESHOLD_DENSITY = 50.0
        config.DURATION_THRESHOLD_CONGESTION = 50.0
        config.MIN_DURATION_FRAMES = 10
        config.MAX_DURATION_FRAMES = 100
        config.DURATION_DECAY_RATE = 2
        config.WEIGHT_DENSITY = 0.45
        config.WEIGHT_CONGESTION = 0.35
        config.WEIGHT_DURATION = 0.20
        config.RISK_SAFE_MAX = 30
        config.RISK_WARN_MAX = 60
        
        self.pipeline = CrowdSafetyPipeline()
        
        # 2. Deep Mocking
        self.pipeline.detector.detect = MagicMock()
        self.pipeline.motion_estimator.update_flow = MagicMock()
        self.pipeline.motion_estimator.estimate_zone_motion = MagicMock()
        self.pipeline.zone_engines['Global']['density'].estimate_density = MagicMock()
        
        self.dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def run_scenario(self, frames_data):
        record = None
        for i, (mock_density, mock_motion) in enumerate(frames_data):
            
            # The Motion module internally calculates Congestion as the inverse of motion.
            motion_norm = min(mock_motion / 5.0, 1.0)
            mock_congestion = (1.0 - motion_norm) * 100.0
            
            # Empty Scene logic bypass
            if mock_density == 0:
                mock_congestion = 0.0
            
            # Mock global AI
            self.pipeline.detector.detect.return_value = (int(mock_density), [], [], [])
            self.pipeline.motion_estimator.update_flow.return_value = None
            
            # Mock Zone logic
            self.pipeline.zone_engines['Global']['density'].estimate_density.return_value = (int(mock_density), mock_density)
            self.pipeline.motion_estimator.estimate_zone_motion.return_value = (mock_motion, mock_congestion)
            
            res = self.pipeline.process_frame(self.dummy_frame, i, i * 33) 
            if res is not None:
                record = res['zones']['Global']['record']
                
        return record

    def print_scenario_result(self, name, record, expected_cat):
        print(f"\n--- Scenario: {name} ---")
        print(f"Density D[n]:    {record['smoothed_density']:.1f}%")
        print(f"Motion M[n]:     {record['motion_magnitude']:.2f}")
        print(f"Congestion C[n]: {record['smoothed_congestion']:.1f}%")
        print(f"Duration T[n]:   {record['duration_score']:.1f}%")
        print(f"Risk Score R[n]: {record['risk_score']:.1f}")
        print(f"Final Category:  {record['risk_category']} (Expected: {expected_cat})")

    # =========================================================================
    # THE 10 SCENARIOS
    # =========================================================================

    def test_01_low_density_normal_motion(self):
        """1. Low-density normally moving crowd -> Safe"""
        # Dens=20%, Motion=3.0 (Congestion ~40%). Both below 50% thresholds.
        data = [(20.0, 3.0)] * 50
        rec = self.run_scenario(data)
        self.print_scenario_result("1. Low Density, Normal Motion", rec, "Safe")
        
        self.assertEqual(rec['risk_category'], "Safe")
        self.assertEqual(rec['duration_score'], 0.0)

    def test_02_high_density_normal_motion(self):
        """2. High-density normally moving crowd -> Warning"""
        # Dens=80%, Motion=3.0 (Congestion ~40%). Density high, but crowd is moving freely.
        data = [(80.0, 3.0)] * 50
        rec = self.run_scenario(data)
        self.print_scenario_result("2. High Density, Normal Motion", rec, "Warning")
        
        # Should NOT trigger duration because congestion is < 50%
        self.assertEqual(rec['duration_score'], 0.0) 
        self.assertEqual(rec['risk_category'], "Warning")

    def test_03_high_density_low_motion(self):
        """3. High-density low-movement crowd -> High Risk"""
        # Dens=90%, Motion=0.5 (Congestion ~90%). Both > 50%.
        data = [(90.0, 0.5)] * 100
        rec = self.run_scenario(data)
        self.print_scenario_result("3. High Density, Low Motion", rec, "High Risk")
        
        self.assertEqual(rec['risk_category'], "High Risk")

    def test_04_short_temporary_congestion(self):
        """4. Short temporary congestion -> Warning"""
        # High density, normally moving for 20 frames
        # Stalls for 5 frames (less than MIN_DURATION_FRAMES=10)
        # Recovers to normal movement
        data = [(80.0, 3.0)] * 20 + [(90.0, 0.5)] * 5 + [(80.0, 3.0)] * 10
        rec = self.run_scenario(data)
        self.print_scenario_result("4. Short Temporary Congestion", rec, "Warning")
        
        # Duration tracker ignores the 5-frame spike
        self.assertEqual(rec['duration_score'], 0.0)
        self.assertEqual(rec['risk_category'], "Warning")

    def test_05_prolonged_congestion(self):
        """5. Prolonged congestion -> High Risk"""
        # Sustained stall for 150 frames. Duration builds up significantly.
        data = [(90.0, 0.5)] * 150
        rec = self.run_scenario(data)
        self.print_scenario_result("5. Prolonged Congestion", rec, "High Risk")
        
        self.assertEqual(rec['duration_score'], 100.0) # Hit the max cap
        self.assertEqual(rec['risk_category'], "High Risk")

    def test_06_empty_scene(self):
        """6. Empty scene -> Safe"""
        # Density=0, Motion=0 (Congestion will calculate high mathematically, but risk remains low)
        data = [(0.0, 0.0)] * 50
        rec = self.run_scenario(data)
        self.print_scenario_result("6. Empty Scene", rec, "Safe")
        
        self.assertEqual(rec['risk_category'], "Safe")

    def test_07_noisy_video(self):
        """7. Noisy video -> LPF keeps state stable"""
        # Normal crowd, but bounding boxes and optical flow are highly erratic
        np.random.seed(42) # Reproducible randomness
        data = []
        for _ in range(100):
            d = max(0.0, min(100.0, 40.0 + np.random.normal(0, 30))) # Base 40, huge noise
            m = max(0.0, min(5.0, 3.0 + np.random.normal(0, 2)))
            data.append((d, m))
            
        rec = self.run_scenario(data)
        self.print_scenario_result("7. Noisy Video", rec, "Warning or Safe")
        
        # The LPF prevents it from wildly spiking to High Risk
        self.assertNotEqual(rec['risk_category'], "High Risk")

    def test_08_partial_occlusion(self):
        """8. Partial occlusion -> Temporary drop in D[n], system recovers smoothly"""
        # Steady density of 80, drops to 40 suddenly (e.g. bus blocks view), returns to 80
        data = [(80.0, 2.5)] * 30 + [(40.0, 2.5)] * 10 + [(80.0, 2.5)] * 30
        rec = self.run_scenario(data)
        self.print_scenario_result("8. Partial Occlusion", rec, "Warning")
        
        self.assertEqual(rec['risk_category'], "Warning")

    def test_09_sudden_movement(self):
        """9. Sudden movement -> Congestion clears, Risk drops"""
        # High density, congested crowd suddenly disperses (running)
        data = [(80.0, 0.5)] * 50 + [(80.0, 5.0)] * 20
        rec = self.run_scenario(data)
        self.print_scenario_result("9. Sudden Movement", rec, "Warning")
        
        # Congestion should drop significantly (near 0)
        self.assertTrue(rec['smoothed_congestion'] < 10.0)

    def test_10_invalid_video(self):
        """10. Invalid/unsupported video -> Handled gracefully"""
        res = self.pipeline.process_frame(None, 0, 0)
        print("\n--- Scenario: 10. Invalid Video ---")
        print("Safely returned None.")
        
        self.assertIsNone(res)

if __name__ == '__main__':
    unittest.main()
