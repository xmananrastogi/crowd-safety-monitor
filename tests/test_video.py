import os
import cv2
import numpy as np
import unittest
from core.video import VideoStream

class TestVideoAcquisition(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Create a dummy video file for testing
        cls.test_video_path = "test_dummy_video.avi"
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(cls.test_video_path, fourcc, 30.0, (320, 240))
        
        # Write 60 frames (2 seconds) of dummy data
        for i in range(60):
            frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            cv2.putText(frame, f"Frame {i}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            out.write(frame)
        out.release()

    @classmethod
    def tearDownClass(cls):
        # Cleanup dummy video after tests complete
        if os.path.exists(cls.test_video_path):
            os.remove(cls.test_video_path)

    def test_video_opens_and_reads(self):
        stream = VideoStream(self.test_video_path)
        data = stream.read_frame()
        self.assertIsNotNone(data)
        self.assertIn('frame', data)
        self.assertIn('frame_number', data)
        self.assertIn('timestamp_ms', data)
        self.assertEqual(data['frame_number'], 1)
        stream.release()

    def test_preprocessing_resize(self):
        stream = VideoStream(self.test_video_path, resolution=(160, 120))
        data = stream.read_frame()
        self.assertEqual(data['frame'].shape, (120, 160, 3)) # height, width, channels
        stream.release()

    def test_fps_reduction(self):
        # Original is 30 FPS. Target 15 FPS means it should read every 2nd frame.
        stream = VideoStream(self.test_video_path, target_fps=15.0)
        data1 = stream.read_frame()
        self.assertEqual(data1['frame_number'], 2) # Skips frame 1
        data2 = stream.read_frame()
        self.assertEqual(data2['frame_number'], 4) # Skips frame 3
        stream.release()

    def test_gaussian_blur(self):
        stream = VideoStream(self.test_video_path, gaussian_blur=True)
        data = stream.read_frame()
        self.assertIsNotNone(data['frame'])
        stream.release()
        
    def test_invalid_path(self):
        with self.assertRaises(ValueError):
            VideoStream("non_existent_video_12345.mp4")

if __name__ == '__main__':
    unittest.main()
