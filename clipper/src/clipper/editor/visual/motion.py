import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any

def estimate_window_motion(video_path: str, start_sec: float, end_sec: float, sample_fps: int = 2) -> Dict[str, float]:
    """
    Samples frames at 2fps within a time window and calculates normalized frame difference.
    Returns average motion score [0.0 to 1.0].
    """
    path = Path(video_path)
    cap = cv2.VideoCapture(str(path.resolve()))
    if not cap.isOpened():
        return {"avg_motion": 0.0, "peak_motion": 0.0}
        
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000.0)
    
    prev_gray = None
    motion_scores = []
    
    current_sec = start_sec
    step = 1.0 / max(1, sample_fps)
    
    while current_sec < end_sec:
        cap.set(cv2.CAP_PROP_POS_MSEC, current_sec * 1000.0)
        ret, frame = cap.read()
        if not ret:
            break
            
        small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        
        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            score = float(np.mean(diff) / 255.0)
            motion_scores.append(score)
            
        prev_gray = gray
        current_sec += step
        
    cap.release()
    
    if not motion_scores:
        return {"avg_motion": 0.0, "peak_motion": 0.0}
        
    return {
        "avg_motion": round(float(np.mean(motion_scores)), 4),
        "peak_motion": round(float(np.max(motion_scores)), 4)
    }
