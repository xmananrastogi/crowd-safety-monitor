import os
import cv2
import numpy as np
import unittest
from core.detector import PersonDetector

class TestPersonDetector(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Initialize detector (will download yolov8n.pt if missing)
        cls.detector = PersonDetector(model_path="yolov8n.pt", conf_thresh=0.2)
        
        # Create a directory to save verification frames
        cls.output_dir = "data/output"
        os.makedirs(cls.output_dir, exist_ok=True)
        
        # Create a dummy image. 
        cls.dummy_frame = np.ones((480, 640, 3), dtype=np.uint8) * 200

    def test_detection_pipeline(self):
        # 1. Run detection
        count, boxes, confidences = self.detector.detect(self.dummy_frame)
        
        # Assert return types
        self.assertIsInstance(count, int)
        self.assertIsInstance(boxes, (list, np.ndarray))
        self.assertIsInstance(confidences, (list, np.ndarray))
        
        # 2. Draw boxes (even if 0 detections, it should return the frame safely)
        drawn_frame = self.detector.draw_boxes(self.dummy_frame, boxes, confidences)
        self.assertEqual(drawn_frame.shape, self.dummy_frame.shape)
        
        # 3. Save frame for verification
        output_path = os.path.join(self.output_dir, "test_detector_output.jpg")
        cv2.imwrite(output_path, drawn_frame)
        self.assertTrue(os.path.exists(output_path))
        
        # 4. Verify the discrete signal D_raw[n] recorded the sample
        signal = self.detector.get_density_signal()
        self.assertGreaterEqual(len(signal), 1)
        self.assertEqual(signal[-1], count)

if __name__ == '__main__':
    unittest.main()
