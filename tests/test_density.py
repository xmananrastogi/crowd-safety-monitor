import unittest
import numpy as np
from core.density import DensityEstimator

class TestDensityEstimator(unittest.TestCase):
    
    def test_full_frame_density(self):
        estimator = DensityEstimator(max_capacity=50)
        
        # Mock 10 bounding boxes
        boxes = [[0, 0, 10, 10] for _ in range(10)]
        
        raw, norm = estimator.estimate_density(boxes, (480, 640, 3))
        
        self.assertEqual(raw, 10)
        # 10 / 50 = 20%
        self.assertEqual(norm, 20.0)
        self.assertEqual(len(estimator.D_raw), 1)
        self.assertEqual(len(estimator.D_norm), 1)
        
    def test_roi_filtering(self):
        # Define an ROI square from (100,100) to (200,200)
        roi = [(100, 100), (200, 100), (200, 200), (100, 200)]
        estimator = DensityEstimator(max_capacity=10, roi_polygon=roi)
        
        # Box 1: Center is (150, 150) -> Inside
        # Box 2: Center is (50, 50) -> Outside
        # Box 3: Center is (150, 199) -> Inside
        boxes = [
            [140, 140, 160, 160], 
            [40, 40, 60, 60],     
            [140, 198, 160, 200]  
        ]
        
        raw, norm = estimator.estimate_density(boxes, (480, 640, 3))
        
        self.assertEqual(raw, 2)
        # 2 / 10 = 20%
        self.assertEqual(norm, 20.0)
        
    def test_normalization_edge_cases(self):
        estimator = DensityEstimator(max_capacity=5)
        
        # Zero people
        raw, norm = estimator.estimate_density([], (480, 640, 3))
        self.assertEqual(raw, 0)
        self.assertEqual(norm, 0.0)
        
        # Exceeding capacity (6 people, max 5) -> Should cap at 100%
        boxes = [[0, 0, 10, 10] for _ in range(6)]
        raw, norm = estimator.estimate_density(boxes, (480, 640, 3))
        self.assertEqual(raw, 6)
        self.assertEqual(norm, 100.0)

if __name__ == '__main__':
    unittest.main()
