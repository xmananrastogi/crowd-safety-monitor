"""
Handles video acquisition and preprocessing.
"""
import cv2
import time
import logging

class VideoStream:
    def __init__(self, source, target_fps=None, resolution=None, gaussian_blur=False):
        """
        Initializes the video stream.
        
        Args:
            source: Integer (0 for webcam) or String (path to video file).
            target_fps: Desired FPS to simulate frame sampling reduction. If None, process all frames.
            resolution: Tuple (width, height) to resize frames. If None, keep original.
            gaussian_blur: Boolean, if True, applies a spatial low-pass filter (Gaussian Blur).
        """
        self.source = source
        self.cap = cv2.VideoCapture(source)
        
        if not self.cap.isOpened():
            logging.error(f"Failed to open video source: {source}")
            raise ValueError(f"Cannot open video source: {source}")
            
        self.original_fps = self.cap.get(cv2.CAP_PROP_FPS)
        # Fallback if OpenCV cannot determine FPS
        if self.original_fps <= 0:
            self.original_fps = 30.0 
            
        self.target_fps = target_fps
        self.resolution = resolution
        self.gaussian_blur = gaussian_blur
        
        # Calculate how many frames to skip if target_fps is lower than original
        self.frame_skip = 1
        if self.target_fps and self.target_fps < self.original_fps:
            self.frame_skip = int(round(self.original_fps / self.target_fps))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.frame_count = 0
        self.start_time = time.time()

    def read_frame(self):
        """
        Reads, preprocesses, and returns the next sampled frame in chronological order.
        
        Returns:
            Dictionary containing:
                'frame': Preprocessed NumPy array (or None if end of video)
                'frame_number': The discrete index n (original frame number)
                'timestamp_ms': Timestamp of the frame in milliseconds
        """
        while True:
            ret, frame = self.cap.read()
            self.frame_count += 1
            
            # Safely handle end-of-video or read errors
            if not ret:
                return None 
                
            # Configurable frame sampling / FPS reduction
            if self.frame_skip > 1 and self.frame_count % self.frame_skip != 0:
                continue # Skip this frame to reduce effective FPS
                
            break
            
        # Get frame timestamp preserving time context
        timestamp_ms = self.cap.get(cv2.CAP_PROP_POS_MSEC)
        
        # Preprocessing: Resize
        if self.resolution is not None:
            frame = cv2.resize(frame, self.resolution)
            
        # Preprocessing: Spatial Low-Pass Filter (Gaussian Blur)
        # Reduces high-frequency spatial noise (e.g., CCTV grain)
        if self.gaussian_blur:
            frame = cv2.GaussianBlur(frame, (5, 5), 0)
            
        return {
            'frame': frame,
            'frame_number': self.frame_count,
            'timestamp_ms': timestamp_ms
        }

    def get_fps(self):
        """Returns the effective frames per second of the video source."""
        if self.target_fps and self.target_fps < self.original_fps:
            return self.target_fps
        return self.original_fps
        
    def release(self):
        """Releases the video capture resource."""
        self.cap.release()
