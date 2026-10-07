import cv2
import numpy as np
import os

os.makedirs('data', exist_ok=True)
width, height = 1280, 720
fps = 30
duration = 10 # 10 seconds
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('data/synthetic_crowd.mp4', fourcc, fps, (width, height))

for i in range(fps * duration):
    frame = np.ones((height, width, 3), dtype=np.uint8) * 40 # Dark gray background
    
    # Draw "people" moving
    # Person 1
    cv2.circle(frame, (100 + i*3, 360), 30, (200, 200, 200), -1)
    # Person 2
    cv2.circle(frame, (1000 - i*2, 100 + i), 25, (150, 150, 150), -1)
    # Person 3
    cv2.circle(frame, (640, 600 - i*2), 35, (180, 180, 180), -1)
    # Person 4
    cv2.circle(frame, (200 + i*4, 150 + i*2), 28, (120, 120, 120), -1)
    # Person 5
    cv2.circle(frame, (800 - i*3, 600 - i*1), 32, (160, 160, 160), -1)
    
    out.write(frame)

out.release()
print("Successfully generated data/synthetic_crowd.mp4")
