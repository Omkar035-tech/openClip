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


class StreamerSplitTracker:
    """
    Computes split-screen framing for streamers & reaction creators (e.g., Casho / Twitch):
    - Top (1080x760): Cropped and centered on streamer's facecam box.
    - Seam Divider (1080x4): Subtle styled accent bar.
    - Bottom (1080x1156): Center crop of main gameplay / content action.
    """
    def __init__(self, src_w: int = 1920, src_h: int = 1080, alpha: float = 0.08):
        self.src_w = src_w
        self.src_h = src_h
        self.alpha = alpha
        
        # Locate Haar cascade
        cascade_path = Path("assets/haarcascade_frontalface_default.xml")
        if not cascade_path.exists():
            cascade_path = Path(__file__).resolve().parent.parent.parent / "assets" / "haarcascade_frontalface_default.xml"
        if not cascade_path.exists():
            cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        self.haar_cascade = cv2.CascadeClassifier(str(cascade_path))

    def detect_facecam_box(self, frame_bgr: np.ndarray) -> Tuple[int, int, int, int]:
        """Detects streamer face and expands to natural webcam framing box (aspect ratio 1080:760)."""
        default_w = int(self.src_w * 0.35)
        default_h = int(default_w * 760 / 1080)
        default_box = (0, 0, default_w, default_h)
        
        if self.haar_cascade.empty():
            return default_box
            
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.haar_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(50, 50))
        if len(faces) == 0:
            return default_box
            
        faces = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)
        bx, by, bw, bh = faces[0]
        
        # Center of face
        fcx = bx + bw / 2
        fcy = by + bh / 2
        
        # Scale to include streamer shoulders and webcam frame
        cam_w = int(max(bw * 2.4, self.src_w * 0.28))
        cam_h = int(cam_w * 760 / 1080)
        
        x1 = int(fcx - cam_w / 2)
        y1 = int(fcy - cam_h * 0.45) # Keep eyes/head centered
        
        # Clamp within frame
        x1 = max(0, min(self.src_w - cam_w, x1))
        y1 = max(0, min(self.src_h - cam_h, y1))
        
        return (x1, y1, cam_w, cam_h)

    def composite_streamer_frame(
        self,
        frame_bgr: np.ndarray,
        cam_box: Tuple[int, int, int, int],
        target_w: int = 1080,
        target_h: int = 1920
    ) -> np.ndarray:
        """
        Crops top webcam & bottom gameplay, then composites into full 1080x1920 9:16 frame.
        """
        top_h = 760
        divider_h = 4
        bottom_h = target_h - top_h - divider_h # 1156
        
        cx1, cy1, cw, ch = cam_box
        webcam_crop = frame_bgr[cy1:cy1 + ch, cx1:cx1 + cw]
        top_cam_resized = cv2.resize(webcam_crop, (target_w, top_h), interpolation=cv2.INTER_LANCZOS4)
        
        # Gameplay crop: Center of screen avoiding facecam if facecam is on an edge
        game_w = int(self.src_h * target_w / bottom_h)
        gx1 = int((self.src_w - game_w) / 2)
        # Shift slightly away from facecam if facecam is in a corner
        if cx1 < self.src_w * 0.25:
            gx1 = min(self.src_w - game_w, gx1 + int(self.src_w * 0.08))
        elif cx1 > self.src_w * 0.75:
            gx1 = max(0, gx1 - int(self.src_w * 0.08))
            
        gx1 = max(0, min(self.src_w - game_w, gx1))
        game_crop = frame_bgr[0:self.src_h, gx1:gx1 + game_w]
        bottom_game_resized = cv2.resize(game_crop, (target_w, bottom_h), interpolation=cv2.INTER_LANCZOS4)
        
        # Composite vertical stack
        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        canvas[0:top_h, 0:target_w] = top_cam_resized
        
        # Styled Accent Divider Bar (Amber Gold #FFD400)
        canvas[top_h:top_h + divider_h, 0:target_w] = [0, 212, 255]
        
        canvas[top_h + divider_h:target_h, 0:target_w] = bottom_game_resized
        return canvas
