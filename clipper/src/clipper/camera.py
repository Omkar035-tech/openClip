import cv2
import numpy as np
from typing import Dict, List, Any

class VirtualCamera:
    """Manages dynamic virtual camera zooming, punch-ins, and visual effects."""
    def __init__(self, config: Dict[str, Any]):
        self.cam_cfg = config.get("camera", {})
        self.fx_cfg = config.get("effects", {})
        
        self.hook_zoom = self.cam_cfg.get("hook_zoom", 1.12)
        self.punch_zoom = self.cam_cfg.get("punch_zoom", 1.20)
        self.pacing_sec = self.cam_cfg.get("pacing_seconds", 3.5)
        
        self.white_flash = self.fx_cfg.get("white_flash", True)
        self.flash_frames = self.fx_cfg.get("flash_frames", 3)
        self.progress_bar = self.fx_cfg.get("progress_bar", True)
        self.vignette = self.fx_cfg.get("vignette", True)

    def get_zoom_at(self, t_rel: float, is_punchline: bool = False) -> float:
        # Hook zoom: 0s to 2.5s
        if t_rel < 2.5:
            return self.hook_zoom
        elif t_rel < 3.2:
            progress = (t_rel - 2.5) / 0.7
            return self.hook_zoom - (self.hook_zoom - 1.0) * progress
            
        # Punch-in on emphasized climax
        if is_punchline:
            return self.punch_zoom
            
        # Periodic subtle dynamic push-in every pacing_sec (1.0 -> 1.06 -> 1.0)
        cycle = t_rel % self.pacing_sec
        if cycle < 1.8:
            return 1.0 + 0.05 * (cycle / 1.8)
        else:
            return 1.05 - 0.05 * ((cycle - 1.8) / (self.pacing_sec - 1.8))

    def apply_effects(self, frame_bgr: np.ndarray, frame_idx: int, total_frames: int) -> np.ndarray:
        h, w = frame_bgr.shape[:2]
        out = frame_bgr
        
        # 1. White flash on start (2-3 frames)
        if self.white_flash and frame_idx < self.flash_frames:
            alpha = (self.flash_frames - frame_idx) / self.flash_frames * 0.4
            white = np.full_like(out, 255)
            out = cv2.addWeighted(out, 1.0 - alpha, white, alpha, 0)
            
        # 2. Progress bar at top (inside safe zone at y=40, height=8px)
        if self.progress_bar and total_frames > 0:
            progress = min(1.0, frame_idx / total_frames)
            bar_w = int(w * progress)
            bar_y = 50
            bar_h = 8
            # Yellow #FFD400 (BGR: 0, 212, 255)
            cv2.rectangle(out, (0, bar_y), (bar_w, bar_y + bar_h), (0, 212, 255), -1)
            
        return out
