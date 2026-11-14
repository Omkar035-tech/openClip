import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

class FaceTracker:
    """
    Computes smooth, cinematic horizontal crop center cx for any target aspect ratio
    (9:16, 4:5, 2:3, 1:1, 16:9).
    Includes OpenCV-based Motion Energy & Sudden Face Reaction Spikes Metric
    (detects sudden head turns, jumps, screams, shock reactions).
    """
    def __init__(
        self,
        src_w: int = 1280,
        src_h: int = 720,
        target_w: int = 1080,
        target_h: int = 1350,
        alpha: float = 0.08,
        deadband_px: int = 16,
        step: int = 4
    ):
        self.src_w = src_w
        self.src_h = src_h
        self.target_w = target_w
        self.target_h = target_h
        
        # Calculate unscaled crop width based on target aspect ratio
        calculated_crop_w = int(src_h * (target_w / target_h))
        if calculated_crop_w > src_w:
            self.crop_w = src_w
            self.crop_h = int(src_w * (target_h / target_w))
        else:
            self.crop_w = calculated_crop_w
            self.crop_h = src_h
            
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

    def detect_face_center(self, frame_bgr: np.ndarray, detect_w: int = 960) -> Optional[Tuple[float, float, float]]:
        """
        Detects primary speaker face center and size on downscaled frame.
        Returns: (center_x, center_y, face_width) in original coordinate space, or None.
        """
        if self.haar_cascade.empty() or frame_bgr is None:
            return None
        
        detect_w = min(self.src_w, detect_w)
        scale = detect_w / float(self.src_w)
        detect_h = int(self.src_h * scale)
        small = cv2.resize(frame_bgr, (detect_w, detect_h), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        min_dim = max(18, int(30 * scale))
        faces = self.haar_cascade.detectMultiScale(
            gray,
            scaleFactor=1.10,
            minNeighbors=4,
            minSize=(min_dim, min_dim)
        )
        
        if len(faces) == 0:
            return None
            
        valid_faces = []
        for (bx, by, bw, bh) in faces:
            aspect = bw / float(bh)
            if 0.60 <= aspect <= 1.40:
                area = bw * bh
                valid_faces.append((area, bx, by, bw, bh))
                
        if not valid_faces:
            return None
            
        valid_faces.sort(key=lambda f: f[0], reverse=True)
        _, bx, by, bw, bh = valid_faces[0]
        
        orig_cx = float((bx + bw / 2.0) / scale)
        orig_cy = float((by + bh / 2.0) / scale)
        orig_w = float(bw / scale)
        
        return (orig_cx, orig_cy, orig_w)

    def compute_motion_energy_spike(self, prev_gray: Optional[np.ndarray], curr_gray: np.ndarray) -> float:
        """
        Measures sudden optical flow / pixel intensity variance for streamer reaction spike detection.
        Higher values correspond to jumpscares, rapid physical gestures, screaming or head shaking.
        """
        if prev_gray is None:
            return 0.0
        diff = cv2.absdiff(curr_gray, prev_gray)
        motion_score = float(np.mean(diff))
        return motion_score

    def compute_trajectory(
        self,
        cap: cv2.VideoCapture,
        start_frame: int,
        num_frames: int,
        step: Optional[int] = None
    ) -> List[float]:
        """
        Computes fluid, jitter-free horizontal trajectory with momentum dampening.
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

        # 1. Fill gaps with temporal stickiness
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
            if abs(delta) > self.deadband:
                effective_delta = delta - (self.deadband if delta > 0 else -self.deadband)
                curr += self.alpha * effective_delta
            smoothed.append(curr)
            
        # 3. Interpolate to full frame count & clamp bounds
        half_crop = self.crop_w / 2.0
        min_cx = half_crop
        max_cx = max(half_crop, self.src_w - half_crop)
        
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
    Computes split-screen reel framing for streamers, reaction creators & gameplay:
    - Top or Bottom webcam placement.
    - Automated detection: detects face and expands to natural square / card framing.
    - Manual mode: takes custom crop coordinates [x, y, w, h] selected by user in UI.
    - Custom gameplay region [x, y, w, h] to exclude webcam or focus on UI/action.
    - Full-frame blurred & darkened background of original video for cinematic reel aesthetics.
    """
    def __init__(
        self,
        src_w: int = 1920,
        src_h: int = 1080,
        cam_placement: str = "top",
        mode: str = "auto",
        manual_cam_box: Optional[Tuple[int, int, int, int]] = None,
        manual_game_box: Optional[Tuple[int, int, int, int]] = None,
        alpha: float = 0.08
    ):
        self.src_w = src_w
        self.src_h = src_h
        self.cam_placement = cam_placement.lower() if cam_placement in ("top", "bottom") else "top"
        self.mode = mode.lower() if mode in ("auto", "manual") else "auto"
        self.manual_cam_box = manual_cam_box
        self.manual_game_box = manual_game_box
        self.alpha = alpha
        
        cascade_path = Path("assets/haarcascade_frontalface_default.xml")
        if not cascade_path.exists():
            cascade_path = Path(__file__).resolve().parent.parent.parent / "assets" / "haarcascade_frontalface_default.xml"
        if not cascade_path.exists():
            cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        self.haar_cascade = cv2.CascadeClassifier(str(cascade_path))

    def detect_facecam_box(self, frame_bgr: np.ndarray, detect_w: int = 960) -> Tuple[int, int, int, int]:
        """
        Detects streamer face and expands to natural square/card framing box.
        If manual mode is specified and manual_cam_box is provided, returns that.
        """
        if self.mode == "manual" and self.manual_cam_box:
            mx, my, mw, mh = self.manual_cam_box
            mx = max(0, min(self.src_w - 10, int(mx)))
            my = max(0, min(self.src_h - 10, int(my)))
            mw = max(10, min(self.src_w - mx, int(mw)))
            mh = max(10, min(self.src_h - my, int(mh)))
            return (mx, my, mw, mh)

        default_w = int(self.src_w * 0.32)
        default_h = int(default_w * 0.68)
        default_box = (0, 0, default_w, default_h)
        
        if self.haar_cascade.empty() or frame_bgr is None:
            return default_box
            
        detect_w = min(self.src_w, detect_w)
        scale = detect_w / float(self.src_w)
        detect_h = int(self.src_h * scale)
        small = cv2.resize(frame_bgr, (detect_w, detect_h), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        min_dim = max(18, int(30 * scale))
        faces = self.haar_cascade.detectMultiScale(
            gray,
            scaleFactor=1.10,
            minNeighbors=4,
            minSize=(min_dim, min_dim)
        )
        if len(faces) == 0:
            return default_box
            
        faces = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)
        bx, by, bw, bh = faces[0]
        
        bx = float(bx) / scale
        by = float(by) / scale
        bw = float(bw) / scale
        bh = float(bh) / scale
        
        fcx = bx + bw / 2.0
        fcy = by + bh / 2.0
        
        cam_w = int(max(bw * 3.2, self.src_w * 0.28))
        cam_h = int(cam_w * 0.65)
        
        cx1 = int(fcx - cam_w / 2.0)
        cy1 = int(fcy - cam_h * 0.48)
        
        cx1 = max(0, min(self.src_w - cam_w, cx1))
        cy1 = max(0, min(self.src_h - cam_h, cy1))
        
        return (cx1, cy1, cam_w, cam_h)

    def composite_streamer_frame(
        self,
        frame_bgr: np.ndarray,
        cam_box: Tuple[int, int, int, int],
        target_w: int = 1080,
        target_h: int = 1920,
        game_box: Optional[Tuple[int, int, int, int]] = None
    ) -> np.ndarray:
        """
        Composites:
        1. Blurred & darkened full-frame background of frame_bgr.
        2. Cropped webcam card (top or bottom) with sleek double border.
        3. Zoomed gameplay video (custom game_box crop or centered default, filling remaining vertical space).
        """
        # 1. Background
        bg_scale = max(target_w / float(self.src_w), target_h / float(self.src_h))
        bg_w = int(self.src_w * bg_scale)
        bg_h = int(self.src_h * bg_scale)
        bg_resized = cv2.resize(frame_bgr, (bg_w, bg_h), interpolation=cv2.INTER_LINEAR)
        bg_x = (bg_w - target_w) // 2
        bg_y = (bg_h - target_h) // 2
        canvas = bg_resized[bg_y:bg_y + target_h, bg_x:bg_x + target_w]
        canvas = cv2.GaussianBlur(canvas, (75, 75), 0)
        canvas = (canvas * 0.55).astype(np.uint8)

        # 2. Extract webcam card
        cx1, cy1, cw, ch = cam_box
        cw = max(10, min(self.src_w - cx1, cw))
        ch = max(10, min(self.src_h - cy1, ch))
        cam_crop = frame_bgr[cy1:cy1 + ch, cx1:cx1 + cw]
        
        cam_disp_w = int(target_w * 0.92)
        aspect = float(ch) / float(cw) if cw > 0 else 0.65
        cam_disp_h = int(cam_disp_w * aspect)
        max_cam_h = int(target_h * 0.38)
        if cam_disp_h > max_cam_h:
            cam_disp_h = max_cam_h
            cam_disp_w = int(cam_disp_h / aspect)
            
        cam_resized = cv2.resize(cam_crop, (cam_disp_w, cam_disp_h), interpolation=cv2.INTER_LANCZOS4)
        cam_x = (target_w - cam_disp_w) // 2

        # 3. Gameplay section (Support user-defined manual_game_box to completely exclude webcam)
        g_box = game_box or self.manual_game_box
        game_disp_w = target_w
        game_disp_h = min(int(target_h * 0.52), int(target_w * (self.src_h / float(self.src_w)) * 1.35))

        if g_box and len(g_box) == 4 and g_box[2] > 20 and g_box[3] > 20:
            gx1, gy1, gw, gh = g_box
            gx1 = max(0, min(self.src_w - 10, gx1))
            gy1 = max(0, min(self.src_h - 10, gy1))
            gw = max(10, min(self.src_w - gx1, gw))
            gh = max(10, min(self.src_h - gy1, gh))
            game_crop = frame_bgr[gy1:gy1 + gh, gx1:gx1 + gw]
        else:
            crop_gh = int(self.src_h * 0.95)
            crop_gw = int(crop_gh * (game_disp_w / float(game_disp_h)))
            if crop_gw > self.src_w:
                crop_gw = self.src_w
                crop_gh = int(crop_gw * (game_disp_h / float(game_disp_w)))
                
            gx1 = (self.src_w - crop_gw) // 2
            gy1 = (self.src_h - crop_gh) // 2
            game_crop = frame_bgr[gy1:gy1 + crop_gh, gx1:gx1 + crop_gw]

        game_resized = cv2.resize(game_crop, (game_disp_w, game_disp_h), interpolation=cv2.INTER_LANCZOS4)

        # 4. Position elements based on cam_placement
        if self.cam_placement == "bottom":
            game_y = 60
            canvas[game_y:game_y + game_disp_h, 0:game_disp_w] = game_resized
            
            cam_y = game_y + game_disp_h + 35
            if cam_y + cam_disp_h > target_h - 20:
                cam_y = target_h - cam_disp_h - 20
                
            cv2.rectangle(canvas, (cam_x - 4, cam_y - 4), (cam_x + cam_disp_w + 4, cam_y + cam_disp_h + 4), (20, 20, 20), 4)
            cv2.rectangle(canvas, (cam_x - 1, cam_y - 1), (cam_x + cam_disp_w + 1, cam_y + cam_disp_h + 1), (120, 120, 120), 2)
            canvas[cam_y:cam_y + cam_disp_h, cam_x:cam_x + cam_disp_w] = cam_resized
        else:
            cam_y = 60
            cv2.rectangle(canvas, (cam_x - 4, cam_y - 4), (cam_x + cam_disp_w + 4, cam_y + cam_disp_h + 4), (20, 20, 20), 4)
            cv2.rectangle(canvas, (cam_x - 1, cam_y - 1), (cam_x + cam_disp_w + 1, cam_y + cam_disp_h + 1), (120, 120, 120), 2)
            canvas[cam_y:cam_y + cam_disp_h, cam_x:cam_x + cam_disp_w] = cam_resized
            
            game_y = cam_y + cam_disp_h + 30
            if game_y + game_disp_h > target_h:
                game_disp_h = target_h - game_y
                game_resized = cv2.resize(game_crop, (game_disp_w, game_disp_h), interpolation=cv2.INTER_LANCZOS4)
            canvas[game_y:game_y + game_disp_h, 0:game_disp_w] = game_resized

        return canvas
