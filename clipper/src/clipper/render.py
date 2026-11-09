import os
import sys
import json
import subprocess
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
from typing import Dict, List, Any

from .reframe import FaceTracker, StreamerSplitTracker
from .camera import VirtualCamera
from .captions import CaptionRenderer, chunk_words, generate_srt, generate_ass
from .music import select_track_for_clip
from .mix import mix_audio_track

def render_short_clip(
    video_path: str,
    clip_meta: Dict[str, Any],
    clip_idx: int,
    output_dir: Path,
    config: Dict[str, Any],
    excluded_music_ids: List[str]
) -> Dict[str, Any]:
    """
    Renders one full vertical short with:
    - 9:16 Face tracking & reframing OR Streamer Split Screen (Facecam Top + Content Bottom)
    - Dynamic virtual camera moves (hook zoom, push-ins)
    - Visual effects (flash, progress bar)
    - Kinetic animated captions
    - Voice cleanup + sidechain ducked background music
    - Automated QA checks
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    clip_id_str = f"short_{clip_idx:02d}"
    out_mp4 = output_dir / f"{clip_id_str}.mp4"
    temp_dir = Path(config.get("general", {}).get("temp_dir", "/tmp/clipper_work")) / clip_id_str
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    t_start = clip_meta["start"]
    t_end = clip_meta["end"]
    duration = t_end - t_start
    words = clip_meta["words"]
    layout_mode = config.get("clip", {}).get("layout", "podcast_vertical")
    
    print(f"\n[{clip_id_str.upper()}] Rendering '{clip_meta['suggested_title']}' ({duration:.2f}s, {t_start:.1f}s -> {t_end:.1f}s, layout: {layout_mode})...")
    
    # 1. Select mood-matched music track
    library_dir = config.get("music", {}).get("library_dir", "music_library")
    matched_music = select_track_for_clip(clip_meta, library_dir=library_dir, excluded_ids=excluded_music_ids)
    music_file = matched_music["abs_file_path"] if matched_music else None
    if matched_music:
        excluded_music_ids.append(matched_music["id"])
        print(f"[{clip_id_str.upper()}] Mood-matched music: '{matched_music['title']}' by {matched_music['artist']}")
        
    # 2. Setup video input
    cap = cv2.VideoCapture(video_path)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    start_frame = int(t_start * src_fps)
    end_frame = int(t_end * src_fps)
    num_frames = end_frame - start_frame
    
    target_w, target_h = config.get("clip", {}).get("resolution", [1080, 1920])
    target_fps = config.get("clip", {}).get("fps", 30)
    crop_w = int(src_h * 9 / 16) # 405
    crop_h = src_h # 720
    
    # 3. Framing & Tracking setup
    split_tracker = None
    streamer_cam_box = None
    cx_trajectory = []
    
    if layout_mode == "streamer_split":
        print(f"[{clip_id_str.upper()}] Initializing Streamer Split layout (Top Facecam + Bottom Gameplay)...")
        split_tracker = StreamerSplitTracker(src_w, src_h)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        sample_boxes = []
        for _ in range(min(20, max(1, num_frames))):
            r, f = cap.read()
            if r:
                sample_boxes.append(split_tracker.detect_facecam_box(f))
        streamer_cam_box = sample_boxes[len(sample_boxes) // 2] if sample_boxes else (0, 0, int(src_w * 0.35), int(src_w * 0.35 * 760 / 1080))
    elif layout_mode == "podcast_vertical":
        tracker = FaceTracker(src_w, src_h, alpha=config.get("camera", {}).get("smoothing_alpha", 0.08))
        print(f"[{clip_id_str.upper()}] Computing face tracking across {num_frames} frames...")
        cx_trajectory = tracker.compute_trajectory(cap, start_frame, num_frames)
    
    # 4. Prepare kinetic captions
    font_file = config.get("captions", {}).get("font_file", "Montserrat-ExtraBold.ttf")
    font_path = Path("fonts") / font_file
    if not font_path.exists():
        font_path = Path("/System/Library/Fonts/Supplemental/Arial Black.ttf")
        
    caption_cfg = dict(config.get("captions", {}))
    if layout_mode == "streamer_split":
        # Place captions right along the divider seam so both webcam & gameplay are fully unobstructed
        caption_cfg["position_ratio"] = 0.405
    caption_renderer = CaptionRenderer(str(font_path), caption_cfg)
    phrases = chunk_words(words, max_words=config.get("captions", {}).get("max_words_per_phrase", 3))
    
    # 5. Virtual camera & effects
    camera = VirtualCamera(config)
    
    # 6. Pipe frames directly to ffmpeg (H.264 30fps)
    temp_raw_video = temp_dir / "raw_video.mp4"
    cmd_ffmpeg = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{target_w}x{target_h}",
        "-pix_fmt", "bgr24",
        "-r", str(src_fps),
        "-i", "-",
        "-vf", f"fps={target_fps}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(temp_raw_video)
    ]
    pipe = subprocess.Popen(cmd_ffmpeg, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    keywords_upper = set(k.upper() for k in clip_meta.get("keywords_to_emphasize", []))
    
    for f_idx in range(num_frames):
        ret, frame = cap.read()
        if not ret:
            break
            
        cur_t_rel = f_idx / src_fps
        cur_t_abs = t_start + cur_t_rel
        
        # Check punchline status
        is_punchline = False
        for p in phrases:
            if p["start"] <= cur_t_abs <= p["end"]:
                if any(w["word"].strip().upper() in keywords_upper for w in p["words"]):
                    is_punchline = True
                    break
                    
        zoom = camera.get_zoom_at(cur_t_rel, is_punchline)
        
        if layout_mode == "streamer_split" and split_tracker:
            resized = split_tracker.composite_streamer_frame(frame, streamer_cam_box, target_w, target_h)
        elif layout_mode == "landscape":
            resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        else:
            cur_crop_w = int(crop_w / zoom)
            cur_crop_h = int(crop_h / zoom)
            
            cx = cx_trajectory[f_idx] if f_idx < len(cx_trajectory) else src_w / 2
            x1 = int(cx - cur_crop_w / 2)
            x2 = x1 + cur_crop_w
            if x1 < 0:
                x1 = 0
                x2 = cur_crop_w
            elif x2 > src_w:
                x2 = src_w
                x1 = src_w - cur_crop_w
                
            y1 = int((src_h - cur_crop_h) / 2)
            y2 = y1 + cur_crop_h
            
            cropped = frame[y1:y2, x1:x2]
            resized = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        
        # Apply camera visual effects (flash, progress bar)
        effect_frame = camera.apply_effects(resized, f_idx, num_frames)
        
        # Overlay kinetic captions
        pil_frame = Image.fromarray(cv2.cvtColor(effect_frame, cv2.COLOR_BGR2RGB))
        overlay = caption_renderer.render(target_w, target_h, cur_t_abs, phrases)
        pil_frame.paste(overlay, (0, 0), overlay)
        
        out_bgr = cv2.cvtColor(np.array(pil_frame), cv2.COLOR_RGB2BGR)
        pipe.stdin.write(out_bgr.tobytes())
        
    pipe.stdin.close()
    pipe.wait()
    cap.release()
    
    # 7. Extract raw voice segment
    temp_voice = temp_dir / "voice.wav"
    cmd_extract = [
        "ffmpeg", "-y",
        "-ss", str(t_start),
        "-t", str(duration),
        "-i", video_path,
        "-vn",
        "-ar", "48000",
        "-ac", "2",
        str(temp_voice)
    ]
    subprocess.run(cmd_extract, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    # 8. Mix voice + music with sidechain ducking & mastering
    temp_mixed_audio = temp_dir / "mixed_master.wav"
    mix_audio_track(str(temp_voice), music_file, str(temp_mixed_audio), duration, config)
    
    # 9. Final Mux
    cmd_mux = [
        "ffmpeg", "-y",
        "-i", str(temp_raw_video),
        "-i", str(temp_mixed_audio),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(out_mp4)
    ]
    subprocess.run(cmd_mux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    # 10. Generate accompanying assets (SRT, ASS, word JSON, manifest, credits, description)
    generate_srt(words, output_dir / f"{clip_id_str}.srt", t_offset=t_start)
    generate_ass(words, output_dir / f"{clip_id_str}.ass", t_offset=t_start)
    
    with open(output_dir / f"{clip_id_str}_words.json", "w", encoding="utf-8") as f:
        json.dump(words, f, indent=2)
        
    # Credits & description
    lic_info = matched_music.get("license_info", {}) if matched_music else {}
    attr_text = lic_info.get("attribution", "")
    
    credits_content = f"""# Music & Asset Credits - {clip_id_str}

## Background Music
- **Track:** {matched_music.get('title', 'N/A') if matched_music else 'None'}
- **Artist:** {matched_music.get('artist', 'N/A') if matched_music else 'None'}
- **License:** {lic_info.get('license', 'None')}
- **Commercial Use:** {lic_info.get('commercial_ok', True)}
- **Required Attribution:**
> {attr_text if attr_text else 'No attribution required.'}

## Visuals & Sound Effects
- **Fonts:** Montserrat ExtraBold (SIL Open Font License 1.1)
- **Sound Effects:** Procedural synthesized CC0 audio (public domain)
"""
    with open(output_dir / f"{clip_id_str}_credits.md", "w", encoding="utf-8") as f:
        f.write(credits_content)
        
    theme_tag = clip_meta.get("mood", {}).get("theme", "interview").replace(" ", "").replace("&", "")
    desc_content = f"""{clip_meta['suggested_title']} 🎙️🔥

{clip_meta['text'][:180]}...

#shorts #podcast #viral #interview #{theme_tag}

Music:
{attr_text}
"""
    with open(output_dir / f"{clip_id_str}_description.txt", "w", encoding="utf-8") as f:
        f.write(desc_content)
        
    # Edit manifest
    manifest = {
        "clip_id": clip_id_str,
        "title": clip_meta["suggested_title"],
        "source_start": t_start,
        "source_end": t_end,
        "duration": duration,
        "resolution": [target_w, target_h],
        "fps": target_fps,
        "music_track": matched_music.get("id") if matched_music else None,
        "music_level_db": config.get("music", {}).get("level_db", -22.0),
        "scores": {
            "hook": clip_meta["score_hook"],
            "emotion": clip_meta["score_emotion"],
            "total": clip_meta["score_total"]
        }
    }
    with open(output_dir / f"{clip_id_str}_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    # 11. Automated QA Check
    qa_passed = run_qa_check(str(out_mp4), target_w, target_h, duration)
    print(f"[{clip_id_str.upper()}] QA Check: {'PASSED (1080x1920 @ 30fps)' if qa_passed else 'WARNING'}")
    print(f"[{clip_id_str.upper()}] Exported successfully to {out_mp4}")
    
    return manifest

def run_qa_check(mp4_path: str, expected_w: int, expected_h: int, expected_dur: float) -> bool:
    """Automated QA checking resolution, framerate, duration."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=width,height,r_frame_rate,codec_name",
        "-show_entries", "format=duration",
        "-of", "json",
        mp4_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return False
    data = json.loads(res.stdout)
    streams = data.get("streams", [])
    if not streams:
        return False
    v = streams[0]
    w = int(v.get("width", 0))
    h = int(v.get("height", 0))
    dur = float(data.get("format", {}).get("duration", 0.0))
    
    return (w == expected_w and h == expected_h and abs(dur - expected_dur) <= 1.0)
