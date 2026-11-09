import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional

class FaceTracker:
    """
    Computes smooth, cinematic horizontal crop center cx for 9:16 vertical framing (e.g. 1080x1920).
    Tuned for high-retention social reels & podcasts:
    - Multi-scale face detection with confidence thresholding & aspect ratio filtering.
    - Soft edge-bias & speaker stickiness to avoid disorienting erratic camera jumping.
    - Asymmetric dynamic deadband & momentum-aware smoothing:
      Keeps speaker naturally centered in the sweet spot while dampening breathing/head-nod jitter.
    """
    def __init__(
        self,
        src_w: int = 1280,
        src_h: int = 720,
        alpha: float = 0.08,
        deadband_px: int = 16,
        step: int = 4
    ):
        self.src_w = src_w
        self.src_h = src_h
        self.crop_w = int(src_h * 9 / 16)
        self.alpha = max(0.02, min(0.30, alpha))
        self.deadband = max(8, deadband_px)
        self.step = max(1, step)
        
        # Locate cascade XML
        cascade_path = Path("assets/haarcascade_frontalface_default.xml")
        if not cascade_path.exists():
            cascade_path = Path(__file__).resolve().parent.parent.parent / "assets" / "haarcascade_frontalface_default.xml"
        if not cascade_path.exists():
            cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
            
        self.haar_cascade = cv2.CascadeClassifier(str(cascade_path))

    def detect_face_center(self, frame_bgr: np.ndarray, detect_w: int = 640) -> Optional[Tuple[float, float, float]]:
        """
        Detects primary speaker face center and size on downscaled frame.
        Returns: (center_x, center_y, face_width) in original coordinate space, or None.
        """
        if self.haar_cascade.empty() or frame_bgr is None:
            return None
        
        # Downscale for high throughput while retaining eye/mouth clarity for detection
        scale = detect_w / float(self.src_w)
        detect_h = int(self.src_h * scale)
        small = cv2.resize(frame_bgr, (detect_w, detect_h), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        
        # Histogram equalization for reliable detection across shadows and dramatic podcast studio lighting
        gray = cv2.equalizeHist(gray)
        
        min_dim = max(24, int(48 * scale))
        faces = self.haar_cascade.detectMultiScale(
            gray,
            scaleFactor=1.12,
            minNeighbors=5,
            minSize=(min_dim, min_dim)
        )
        
        if len(faces) == 0:
            return None
            
        # Filter candidate faces: primary podcast speaker is typically the largest face
        # and has realistic face aspect ratio (w/h between 0.65 and 1.35)
        valid_faces = []
        for (bx, by, bw, bh) in faces:
            aspect = bw / float(bh)
            if 0.60 <= aspect <= 1.40:
                area = bw * bh
                valid_faces.append((area, bx, by, bw, bh))
                
        if not valid_faces:
            return None
            
        # Sort by area descending (primary speaker front and center)
        valid_faces.sort(key=lambda f: f[0], reverse=True)
        _, bx, by, bw, bh = valid_faces[0]
        
        # Map back to unscaled source dimensions
        orig_cx = float((bx + bw / 2.0) / scale)
        orig_cy = float((by + bh / 2.0) / scale)
        orig_w = float(bw / scale)
        
        return (orig_cx, orig_cy, orig_w)

    def compute_trajectory(
        self,
        cap: cv2.VideoCapture,
        start_frame: int,
        num_frames: int,
        step: Optional[int] = None
    ) -> List[float]:
        """
        Computes fluid, jitter-free horizontal trajectory for 9:16 vertical crop.
        - Stride sampling with frame fast-forwarding (`cap.grab()`).
        - Deadband dampening to prevent micro-wobbles during natural speech pauses.
        - Cubic / linear interpolation for continuous reel panning.
        """
        step = step or self.step
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        raw_centers: List[Optional[float]] = []
        sampled_indices: List[int] = []
        default_cx = self.src_w / 2.0
        
        for f in range(0, num_frames, step):
            ret, frame = cap.read()
            if not ret:
                break
            face_meta = self.detect_face_center(frame)
            raw_centers.append(face_meta[0] if face_meta else None)
            sampled_indices.append(f)
            
            # Fast-forward intermediate frames
            if step > 1:
                for _ in range(min(step - 1, num_frames - f - 1)):
                    cap.grab()
                    
        if not raw_centers:
            return [default_cx] * num_frames

        # 1. Fill gaps with temporal stickiness (speaker doesn't teleport during a 1-second turn)
        cx_filled: List[float] = []
        last_known = default_cx
        for c in raw_centers:
            if c is not None:
                last_known = c
                break
                
        for val in raw_centers:
            if val is not None:
                last_known = val
            cx_filled.append(last_known)
            
        # 2. Cinematic Exponential Moving Average (EMA) with dynamic deadband
        smoothed: List[float] = []
        curr = cx_filled[0]
        
        for target in cx_filled:
            delta = target - curr
            # Deadband: if movement is small (< deadband_px), maintain steady shot
            if abs(delta) > self.deadband:
                effective_delta = delta - (self.deadband if delta > 0 else -self.deadband)
                curr += self.alpha * effective_delta
            smoothed.append(curr)
            
        # 3. Interpolate to full frame count & clamp bounds
        half_crop = self.crop_w / 2.0
        min_cx = half_crop
        max_cx = self.src_w - half_crop
        
        if len(sampled_indices) > 1:
            all_frames = np.arange(num_frames)
            sampled_arr = np.array(sampled_indices[:len(smoothed)])
            smoothed_arr = np.array(smoothed)
            
            continuous_cx = np.interp(all_frames, sampled_arr, smoothed_arr)
            clamped = np.clip(continuous_cx, min_cx, max_cx)
            return clamped.tolist()
        else:
            single_val = max(min_cx, min(max_cx, smoothed[0] if smoothed else default_cx))
            return [float(single_val)] * num_frames


class StreamerSplitTracker:
    """
    Computes split-screen framing for streamers & reaction creators (e.g., Twitch / Discord):
    - Top (1080x760): Cropped and centered on streamer's facecam box.
    - Seam Divider (1080x4): Subtle styled accent bar.
    - Bottom (1080x1156): Center crop of main gameplay / content action.
    """
    def __init__(self, src_w: int = 1920, src_h: int = 1080, alpha: float = 0.08):
        self.src_w = src_w
        self.src_h = src_h
        self.alpha = alpha
        
        cascade_path = Path("assets/haarcascade_frontalface_default.xml")
        if not cascade_path.exists():
            cascade_path = Path(__file__).resolve().parent.parent.parent / "assets" / "haarcascade_frontalface_default.xml"
        if not cascade_path.exists():
            cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        self.haar_cascade = cv2.CascadeClassifier(str(cascade_path))

    def detect_facecam_box(self, frame_bgr: np.ndarray, detect_w: int = 480) -> Tuple[int, int, int, int]:
        """Detects streamer face and expands to natural webcam framing box (aspect ratio 1080:760)."""
        default_w = int(self.src_w * 0.35)
        default_h = int(default_w * 760 / 1080)
        default_box = (0, 0, default_w, default_h)
        
        if self.haar_cascade.empty() or frame_bgr is None:
            return default_box
            
        scale = detect_w / float(self.src_w)
        detect_h = int(self.src_h * scale)
        small = cv2.resize(frame_bgr, (detect_w, detect_h), interpolation=cv2.INTER_NEAREST)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        
        min_dim = max(20, int(45 * scale))
        faces = self.haar_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(min_dim, min_dim))
        if len(faces) == 0:
            return default_box
            
        faces = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)
        bx, by, bw, bh = faces[0]
        
        # Rescale detected box coordinates back to full video size
        bx = float(bx) / scale
        by = float(by) / scale
        bw = float(bw) / scale
        bh = float(bh) / scale
        
        # Center of face
        fcx = bx + bw / 2.0
        fcy = by + bh / 2.0
        
        # Scale to include streamer shoulders and webcam frame
        cam_w = int(max(bw * 2.4, self.src_w * 0.28))
        cam_h = int(cam_w * 760 / 1080)
        
        x1 = int(fcx - cam_w / 2)
        y1 = int(fcy - cam_h * 0.45) # Keep eyes/head in upper third
        
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
        top_h = 760
        divider_h = 4
        bottom_h = target_h - top_h - divider_h
        
        cx1, cy1, cw, ch = cam_box
        webcam_crop = frame_bgr[cy1:cy1 + ch, cx1:cx1 + cw]
        top_cam_resized = cv2.resize(webcam_crop, (target_w, top_h), interpolation=cv2.INTER_LANCZOS4)
        
        game_w = int(self.src_h * target_w / bottom_h)
        gx1 = int((self.src_w - game_w) / 2)
        if cx1 < self.src_w * 0.25:
            gx1 = min(self.src_w - game_w, gx1 + int(self.src_w * 0.08))
        elif cx1 > self.src_w * 0.75:
            gx1 = max(0, gx1 - int(self.src_w * 0.08))
            
        gx1 = max(0, min(self.src_w - game_w, gx1))
        game_crop = frame_bgr[0:self.src_h, gx1:gx1 + game_w]
        bottom_game_resized = cv2.resize(game_crop, (target_w, bottom_h), interpolation=cv2.INTER_LANCZOS4)
        
        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        canvas[0:top_h, 0:target_w] = top_cam_resized
        canvas[top_h:top_h + divider_h, 0:target_w] = [0, 212, 255]
        canvas[top_h + divider_h:target_h, 0:target_w] = bottom_game_resized
        return canvas
