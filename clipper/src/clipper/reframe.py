import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional

class FaceTracker:
    """
    Computes smooth horizontal crop center cx for 9:16 vertical framing (405x720 window).
    Uses MediaPipe face detection with OpenCV Haar Cascade fallback.
    Smooths using Exponential Moving Average (EMA) with deadband to prevent camera wobble.
    """
    def __init__(self, src_w: int = 1280, src_h: int = 720, alpha: float = 0.08, deadband_px: int = 15):
        self.src_w = src_w
        self.src_h = src_h
        self.crop_w = int(src_h * 9 / 16) # 405
        self.alpha = alpha
        self.deadband = deadband_px
        
        # Locate cascade XML
        cascade_path = Path("assets/haarcascade_frontalface_default.xml")
        if not cascade_path.exists():
            cascade_path = Path(__file__).resolve().parent.parent.parent / "assets" / "haarcascade_frontalface_default.xml"
        if not cascade_path.exists():
            cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
            
        self.haar_cascade = cv2.CascadeClassifier(str(cascade_path))
        
    def detect_face_center(self, frame_bgr: np.ndarray) -> Optional[float]:
        if self.haar_cascade.empty():
            return None
        # Fast gray downscale for real-time face detection
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.haar_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(60, 60))
        if len(faces) > 0:
            faces = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)
            bx, by, bw, bh = faces[0]
            return float(bx + bw / 2)
        return None

    def compute_trajectory(self, cap: cv2.VideoCapture, start_frame: int, num_frames: int, step: int = 2) -> List[float]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        raw_centers = []
        default_cx = self.src_w / 2
        
        for f in range(0, num_frames, step):
            ret, frame = cap.read()
            if not ret:
                break
            face_cx = self.detect_face_center(frame)
            raw_centers.append(face_cx)
            if step > 1 and f + 1 < num_frames:
                cap.grab()
                
        # Interpolate missing detections
        cx_interp = []
        last = default_cx
        for val in raw_centers:
            if val is not None:
                last = val
            cx_interp.append(last)
            
        # Smooth with EMA + deadband
        smoothed = []
        curr = cx_interp[0] if cx_interp else default_cx
        for val in cx_interp:
            diff = val - curr
            if abs(diff) > self.deadband:
                curr += self.alpha * (diff - (self.deadband if diff > 0 else -self.deadband))
            smoothed.append(curr)
            
        # Expand to all frames and clamp
        full_trajectory = []
        half_crop = self.crop_w / 2
        min_cx = half_crop
        max_cx = self.src_w - half_crop
        
        for i in range(num_frames):
            idx = min(int(i / step), len(smoothed) - 1)
            cx = smoothed[idx]
            clamped = max(min_cx, min(max_cx, cx))
            full_trajectory.append(clamped)
            
        return full_trajectory
