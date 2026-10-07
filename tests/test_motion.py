import os
import cv2
import numpy as np
import unittest
from core.motion import MotionEstimator

class TestMotionEstimator(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.estimator = MotionEstimator(max_expected_motion=2.0)
        cls.output_dir = "data/output"
        os.makedirs(cls.output_dir, exist_ok=True)
        
        # Create a frame
        cls.frame1 = np.ones((100, 100, 3), dtype=np.uint8) * 100
        # Create a second frame shifted to the right
        cls.frame2 = np.ones((100, 100, 3), dtype=np.uint8) * 100
        # Add a block to both to track motion
        cv2.rectangle(cls.frame1, (20, 20), (40, 40), (255, 255, 255), -1)
        cv2.rectangle(cls.frame2, (30, 20), (50, 40), (255, 255, 255), -1) # Shifted right by 10 px

    def test_optical_flow_pipeline(self):
        # Frame 1
        m1, c1, flow1 = self.estimator.estimate_motion(self.frame1)
        self.assertEqual(m1, 0.0) # Prev gray was None
        
        # Frame 2
        m2, c2, flow2 = self.estimator.estimate_motion(self.frame2)
        
        self.assertGreater(m2, 0.0) # Motion should be > 0
        self.assertIsInstance(flow2, np.ndarray)
        self.assertEqual(flow2.shape, (100, 100, 2))
        
        # Visualization test
        drawn = self.estimator.draw_flow_arrows(self.frame2, flow2)
        
        output_path = os.path.join(self.output_dir, "test_flow_arrows.jpg")
        cv2.imwrite(output_path, drawn)
        self.assertTrue(os.path.exists(output_path))
        
        # Signals test
        self.assertGreaterEqual(len(self.estimator.M), 2)
        self.assertGreaterEqual(len(self.estimator.C), 2)
        
    def test_congestion_normalization(self):
        estimator = MotionEstimator(max_expected_motion=10.0)
        estimator.estimate_motion(self.frame1)
        
        # Mock motion calculation by replacing prev_gray manually
        estimator.prev_gray = cv2.cvtColor(self.frame1, cv2.COLOR_BGR2GRAY) 
        
        m, c, _ = estimator.estimate_motion(self.frame1) # No movement
        
        # Zero motion = 100% congestion
        self.assertAlmostEqual(m, 0.0)
        self.assertAlmostEqual(c, 100.0)

if __name__ == '__main__':
    unittest.main()
