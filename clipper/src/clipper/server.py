import subprocess
import numpy as np
import os
import sys
import json
import time
import shutil
import threading
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Any, Optional

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse, Response
import cv2
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from clipper.cache import compute_file_hash, CacheManager
from clipper.transcribe import transcribe_video
from clipper.audio_features import compute_audio_features
from clipper.pick import select_and_rank_clips
from clipper.render import render_short_clip
from clipper.music import load_music_library, add_track_to_library
from clipper.hardware import detect_hardware

app = FastAPI(title="Clipper Studio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Studio State
studio_state = {
    "status": "idle", # idle, processing, completed, error
    "stage": "Ready for input",
    "progress": 0,
    "current_clip": "",
    "logs": [],
    "candidates": [],
    "completed_clips": [],
    "error_message": None
}

def log_event(message: str):
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    studio_state["logs"].append(entry)
    if len(studio_state["logs"]) > 100:
        studio_state["logs"] = studio_state["logs"][-100:]
    try:
        print(entry)
    except UnicodeEncodeError:
        safe_entry = entry.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
        print(safe_entry)

def load_config() -> dict:
    cfg_path = BASE_DIR / "config.yaml"
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}

@app.get("/", response_class=HTMLResponse)
async def serve_studio_ui():
    index_file = Path(__file__).resolve().parent / "web" / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h2>Clipper Studio UI not found.</h2>")
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/api/hardware")
async def get_hardware():
    return {"hardware": detect_hardware()}

@app.get("/api/config")
async def get_studio_config():
    cfg = load_config()
    tracks, licenses = load_music_library(str(BASE_DIR / "music_library"))
    
    # List available fonts in clipper/fonts
    fonts_dir = BASE_DIR / "fonts"
    font_files = [f.name for f in fonts_dir.glob("*.ttf")] + [f.name for f in fonts_dir.glob("*.otf")]
    
    return {
        "config": cfg,
        "tracks": tracks,
        "fonts": font_files,
        "status": studio_state
    }

@app.get("/api/status")
async def get_status():
    return studio_state

@app.post("/api/upload-ost")
async def upload_custom_ost(
    file: UploadFile = File(...),
    title: str = Form(""),
    artist: str = Form("Custom Artist"),
    mood: str = Form("custom, upbeat")
):
    """Uploads a custom OST track and indexes it into the music library."""
    tracks_dir = BASE_DIR / "music_library" / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    
    dest_path = tracks_dir / file.filename
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    t_title = title if title.strip() else dest_path.stem
    mood_tags = [m.strip() for m in mood.split(",") if m.strip()]
    
    log_event(f"Indexing custom OST: '{t_title}' by {artist}...")
    add_track_to_library(str(dest_path), t_title, artist, mood_tags, "User Upload (Commercial Permitted)", str(BASE_DIR / "music_library"))
    
    tracks, _ = load_music_library(str(BASE_DIR / "music_library"))
    return {"success": True, "message": f"Added '{t_title}' to music library", "tracks": tracks}

@app.post("/api/captions/auto-detect")
async def auto_detect_caption_emphasis(payload: Dict[str, Any]):
    """Analyzes sample text and wraps high-impact viral words in {{...}} emphasis tags."""
    text = payload.get("text", "").strip()
    if not text:
        return {"highlighted_text": "", "emphasis_words": []}
        
    import re
    # Patterns to auto-detect: numbers, brand entities, emotional superlatives, power words
    power_keywords = [
        "seven 11", "7 11", "7-eleven", "7-11", "10,000", "10000", "million", "billion", "dollars",
        "impossible", "conqueror", "strength", "discipline", "warrior", "suffer", "pain", "obsessed",
        "never quit", "hack", "fucking suck", "truth", "mindset", "secret", "biggest mistake",
        "life changing", "conquer", "destroy", "failure"
    ]
    
    highlighted = text
    found_words = []
    
    # 1. Multi-word phrase matches first
    for kw in power_keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        if pattern.search(highlighted):
            found_words.append(kw)
            highlighted = pattern.sub(f"{{{{{kw}}}}}", highlighted)
            
    # 2. Single word matches if no phrase was matched
    if not found_words:
        words = text.split()
        for w in words:
            clean_w = w.strip(" ,.!?\"'")
            if (len(clean_w) >= 6 and clean_w.isupper()) or clean_w.lower() in ["never", "crazy", "truth", "power", "money", "mind", "hate", "fight"]:
                found_words.append(clean_w)
                highlighted = highlighted.replace(clean_w, f"{{{{{clean_w}}}}}")
                break
                
    return {"highlighted_text": highlighted, "emphasis_words": found_words}

@app.post("/api/captions/save-style")
async def save_captions_style(payload: Dict[str, Any]):
    """Saves custom caption playground styling into config.yaml."""
    cfg = load_config()
    if "captions" not in cfg:
        cfg["captions"] = {}
        
    cfg["captions"]["font_file"] = payload.get("font_file", "Montserrat-ExtraBold.ttf")
    cfg["captions"]["font_size"] = int(payload.get("font_size", 68))
    cfg["captions"]["primary_color"] = payload.get("primary_color", "#FFFFFF")
    cfg["captions"]["active_color"] = payload.get("active_color", "#FFD400")
    cfg["captions"]["emphasis_color"] = payload.get("emphasis_color", "#FFD400")
    cfg["captions"]["stroke_color"] = payload.get("stroke_color", "#000000")
    cfg["captions"]["stroke_width"] = int(payload.get("stroke_width", 7))
    cfg["captions"]["rotation_angle"] = float(payload.get("rotation_angle", 0.0))
    cfg["captions"]["bg_mode"] = payload.get("bg_mode", "none")
    cfg["captions"]["bg_color"] = payload.get("bg_color", "rgba(0,0,0,0.65)")
    cfg["captions"]["bg_radius"] = int(payload.get("bg_radius", 14))
    cfg["captions"]["fade_duration"] = float(payload.get("fade_duration", 0.12))
    cfg["captions"]["auto_detect_emphasis"] = bool(payload.get("auto_detect_emphasis", True))
    
    cfg_path = BASE_DIR / "config.yaml"
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
        
    log_event(f"Applied new caption style from Playground (Rotation: {cfg['captions']['rotation_angle']}°, Font: {cfg['captions']['font_file']})")
    return {"success": True, "message": "Caption style saved to config and active for all renders."}

def run_pipeline_thread(payload: Dict[str, Any]):
    try:
        studio_state["status"] = "processing"
        studio_state["error_message"] = None
        studio_state["progress"] = 5
        studio_state["completed_clips"] = []
        
        raw_video_path = payload.get("video_path", "").strip().strip('"').strip("'")
        if not raw_video_path:
            raise FileNotFoundError("No video path provided")
            
        # Cross-platform path resolution (Windows backslashes / POSIX slashes)
        v_path = Path(raw_video_path).expanduser().resolve()
        if not v_path.exists():
            alt_candidates = [
                BASE_DIR / "uploads" / v_path.name,
                BASE_DIR / raw_video_path,
                Path.home() / "Downloads" / v_path.name,
                Path.home() / "Videos" / v_path.name,
                Path.home() / "Movies" / v_path.name,
                Path.home() / "Desktop" / v_path.name,
            ]
            found_alt = next((c for c in alt_candidates if c.exists()), None)
            if found_alt:
                v_path = found_alt.resolve()
            else:
                raise FileNotFoundError(f"Video file not found: {raw_video_path}")
        config = load_config()
        
        # Apply user knobs
        n_clips = min(5, max(1, int(payload.get("n_clips", 5))))
        max_duration = float(payload.get("max_duration", 75.0))
        min_duration = min(max_duration - 10.0, 35.0)
        
        config["general"]["n_clips"] = n_clips
        config["clip"]["layout"] = payload.get("layout", "podcast_vertical")
        config["clip"]["max_duration"] = max_duration
        config["clip"]["min_duration"] = min_duration
        config["clip"]["target_duration"] = min(75.0, max_duration - 5.0)
        
        # Caption customization from playground / UI
        config["captions"]["font_file"] = payload.get("font_file", "Montserrat-ExtraBold.ttf")
        config["captions"]["font_size"] = int(payload.get("font_size", 68))
        config["captions"]["primary_color"] = payload.get("primary_color", "#FFFFFF")
        config["captions"]["active_color"] = payload.get("active_color", "#FFD400")
        config["captions"]["emphasis_color"] = payload.get("emphasis_color", payload.get("active_color", "#FFD400"))
        config["captions"]["stroke_color"] = payload.get("stroke_color", "#000000")
        config["captions"]["stroke_width"] = int(payload.get("stroke_width", 7))
        config["captions"]["rotation_angle"] = float(payload.get("rotation_angle", 0.0))
        config["captions"]["bg_mode"] = payload.get("bg_mode", "none")
        config["captions"]["bg_color"] = payload.get("bg_color", "rgba(0,0,0,0.65)")
        config["captions"]["bg_radius"] = int(payload.get("bg_radius", 14))
        config["captions"]["fade_duration"] = float(payload.get("fade_duration", 0.12))
        config["captions"]["auto_detect_emphasis"] = bool(payload.get("auto_detect_emphasis", True))
        
        # Aspect ratio customization (16:9, 1:1, 4:5, 2:3, 9:16)
        if "clip" not in config:
            config["clip"] = {}
        config["clip"]["aspect_ratio"] = payload.get("aspect_ratio", "4:5")
        
        # Streamer webcam split layout customization
        is_streamer = bool(payload.get("streamer_layout_enabled", False))
        if is_streamer:
            config["clip"]["layout"] = "streamer_split"
            config["clip"]["cam_placement"] = payload.get("cam_placement", "top")
            config["clip"]["streamer_mode"] = payload.get("streamer_mode", "auto")
            manual_box = payload.get("manual_cam_box")
            if manual_box and isinstance(manual_box, list) and len(manual_box) == 4:
                config["clip"]["manual_cam_box"] = [int(v) for v in manual_box]
            else:
                config["clip"]["manual_cam_box"] = None
        else:
            config["clip"]["layout"] = payload.get("layout", "podcast_vertical")

        # Effects customization
        config["effects"]["white_flash"] = bool(payload.get("effects_flash", True))
        config["effects"]["progress_bar"] = bool(payload.get("effects_progress", True))
        config["effects"]["vignette"] = bool(payload.get("effects_vignette", True))
        config["camera"]["hook_zoom"] = float(payload.get("hook_zoom", 1.12))
        
        # Architecture & Model Engine Selection (Groq Cloud -> Gemini -> Heuristic Fallback)
        config["engine_architecture"] = payload.get("engine_architecture", "openclip_standard")
        config["wayin_prompt"] = payload.get("wayin_prompt")
        
        if "models" not in config:
            config["models"] = {}
        if payload.get("groq_api_key"):
            config["models"]["groq_api_key"] = payload.get("groq_api_key").strip()
        if payload.get("groq_model"):
            config["models"]["groq_model"] = payload.get("groq_model").strip()
        if payload.get("gemini_api_key"):
            config["models"]["gemini_api_key"] = payload.get("gemini_api_key").strip()

        # Performance & Hardware Customization (GPU/CPU selection per module)
        if "performance" not in config:
            config["performance"] = {}
        config["performance"]["whisper_hardware"] = payload.get("whisper_hardware", "auto")
        config["performance"]["render_hardware"] = payload.get("render_hardware", "auto")
        config["performance"]["cpu_threads"] = int(payload.get("cpu_threads", os.cpu_count() or 4))
        render_workers = max(1, min(4, int(payload.get("render_workers", 2))))

        # Face Tracking & Camera Customization
        if "camera" not in config:
            config["camera"] = {}
        config["camera"]["smoothing_alpha"] = float(payload.get("face_alpha", 0.08))
        config["camera"]["deadband_px"] = int(payload.get("face_deadband", 16))

        # Music customization
        music_mode = payload.get("music_mode", "auto")
        if music_mode == "off":
            config["music"]["enabled"] = False
        else:
            config["music"]["enabled"] = True
            config["music"]["level_db"] = float(payload.get("music_level_db", -22.0))
            
        # 1. Video Hashing & Cache (5% - 15%)
        studio_state["stage"] = "Validating cache & extracting audio"
        studio_state["progress"] = 10
        log_event(f"Starting pipeline for '{v_path.name}'...")
        
        cache_mgr = CacheManager(str(BASE_DIR / config.get("general", {}).get("cache_dir", "cache")))
        v_hash = compute_file_hash(str(v_path))
        cache_dir = cache_mgr.get_cache_dir(v_hash)
        log_event(f"Video Hash: {v_hash[:16]} (Cache: {cache_dir.name})")
        
        # 2. Transcription (15% - 30%)
        studio_state["stage"] = "Transcribing with GPU speech recognition"
        studio_state["progress"] = 20
        log_event("Transcribing speech with word-level timestamps...")
        transcript = transcribe_video(str(v_path), cache_dir, config)
        log_event(f"Transcription ready ({len(transcript)} segments).")
        
        # 3. Audio Energy & Features (30% - 40%)
        studio_state["stage"] = "Analyzing acoustic signals & emotional energy"
        studio_state["progress"] = 35
        log_event("Analyzing RMS volume, speech tempo, and pitch variance...")
        wav_path = cache_dir / "audio_16k.wav"
        features = compute_audio_features(str(wav_path), transcript, cache_dir)
        
        # 4. Multimodal Selection & Viral Hook Scoring (40% - 50%)
        studio_state["stage"] = "AI Semantic & Viral Moment Detection"
        studio_state["progress"] = 45
        if config.get("engine_architecture") in ("wayin_2_0", "wayin"):
            log_event("[openClip 2.0 (Beta)] Running Wayin.ai Hierarchical Funnel (Hook-First 1-3s Saliency + Gemini Reasoning)...")
        else:
            log_event("[openClip Standard] Scanning dialogue for curiosity hooks, comedy banter, and punchlines...")
        ranked_clips = select_and_rank_clips(transcript, features, config, cache_dir)
        studio_state["candidates"] = [
            {
                "index": i + 1,
                "title": c["suggested_title"],
                "start": c["start"],
                "end": c["end"],
                "duration": c["duration"],
                "score": c["score_total"],
                "mood": c["mood"]["primary_mood"],
                "text": c["text"][:160] + "..."
            }
            for i, c in enumerate(ranked_clips)
        ]
        log_event(f"Identified top {len(ranked_clips)} viral moments.")
        
        # 5. Video Rendering & Compositing (50% - 95%)
        out_dir = BASE_DIR / config.get("general", {}).get("output_dir", "out") / v_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        
        excluded_music = []
        # If user picked a specific OST
        selected_track_id = payload.get("selected_track_id")
        
        total_clips = len(ranked_clips)
        log_event(f"Starting hardware-accelerated concurrent render of {total_clips} shorts ({render_workers} workers, encoder: {config['performance']['render_hardware']})...")
        
        # Prepare render tasks
        render_jobs = []
        for idx, clip_meta in enumerate(ranked_clips, 1):
            if selected_track_id and selected_track_id != "auto":
                c_meta = dict(clip_meta)
                c_meta["custom_track_id"] = selected_track_id
            else:
                c_meta = clip_meta
            render_jobs.append((idx, c_meta))
            
        completed_count = 0
        
        def render_worker(job):
            idx, c_meta = job
            log_event(f"[Worker] Launching render for Short #{idx}: '{c_meta['suggested_title']}' ({c_meta['duration']}s)...")
            manifest = render_short_clip(str(v_path), c_meta, idx, out_dir, config, excluded_music)
            return idx, c_meta, manifest

        with concurrent.futures.ThreadPoolExecutor(max_workers=render_workers) as executor:
            future_to_job = {executor.submit(render_worker, job): job for job in render_jobs}
            for future in concurrent.futures.as_completed(future_to_job):
                idx, c_meta, manifest = future.result()
                completed_count += 1
                
                # Register completed clip in studio state
                clip_file = f"short_{idx:02d}.mp4"
                studio_state["completed_clips"].append({
                    "clip_id": f"short_{idx:02d}",
                    "title": c_meta["suggested_title"],
                    "duration": c_meta["duration"],
                    "score": c_meta["score_total"],
                    "time_range": f"{c_meta['start']:.1f}s - {c_meta['end']:.1f}s",
                    "mp4_url": f"/api/videos/{v_path.stem}/{clip_file}",
                    "srt_url": f"/api/videos/{v_path.stem}/short_{idx:02d}.srt",
                    "text": c_meta["text"],
                    "mood": c_meta["mood"]["primary_mood"]
                })
                # Keep clips ordered 1 -> 5 in preview UI
                studio_state["completed_clips"].sort(key=lambda x: x["clip_id"])
                
                pct = 50 + int(45 * completed_count / total_clips)
                studio_state["progress"] = pct
                studio_state["stage"] = f"Rendered {completed_count}/{total_clips} shorts ({pct}%)"
                log_event(f"Successfully finished Short #{idx} (1080x1920 @ 30fps) - {completed_count}/{total_clips} ready.")
            
        studio_state["stage"] = "All shorts rendered successfully!"
        studio_state["progress"] = 100
        studio_state["status"] = "completed"
        log_event(f"Production finished! All {len(ranked_clips)} shorts are ready for preview.")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        studio_state["status"] = "error"
        studio_state["error_message"] = str(e)
        studio_state["stage"] = f"Error: {e}"
        log_event(f"Error during production: {e}")

@app.post("/api/generate")
async def start_generation(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    if studio_state["status"] == "processing":
        raise HTTPException(status_code=400, detail="A clipping generation task is already in progress.")
        
    studio_state["status"] = "processing"
    studio_state["logs"] = []
    studio_state["candidates"] = []
    studio_state["completed_clips"] = []
    log_event("Received generation request from Studio UI...")
    
    thread = threading.Thread(target=run_pipeline_thread, args=(payload,), daemon=True)
    thread.start()
    
    return {"success": True, "message": "Generation started"}

@app.api_route("/api/videos/{video_name}/{filename}", methods=["GET", "HEAD"])
async def stream_output_video(video_name: str, filename: str):
    import urllib.parse
    decoded_name = urllib.parse.unquote(video_name)
    file_path = BASE_DIR / "out" / decoded_name / filename
    if not file_path.exists():
        file_path = BASE_DIR / "out" / video_name / filename
    if not file_path.exists():
        # Fallback to brave-bell output directory
        file_path = BASE_DIR.parent / "output" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
        
    media_type = "video/mp4" if filename.endswith(".mp4") else "text/plain"
    return FileResponse(file_path, media_type=media_type)

@app.get("/api/gallery")
async def get_rendered_gallery():
    """
    Returns hierarchical folder-based structure of all rendered video projects and their shorts.
    """
    import urllib.parse
    out_dir = BASE_DIR / "out"
    projects = []
    
    if out_dir.exists():
        for p in sorted(out_dir.iterdir(), key=lambda d: d.stat().st_mtime if d.is_dir() else 0, reverse=True):
            if not p.is_dir() or p.name.startswith("."):
                continue
                
            mp4_files = sorted(list(p.glob("short_*.mp4")), key=lambda f: f.name)
            if not mp4_files:
                continue
                
            # Clean display name
            display_name = (
                p.name
                .replace("vidssave.com _", "")
                .replace("_ Grilling with Castillo 720P", " (Castillo Interview)")
                .replace("(1080p, en)", "")
                .strip()
            )
            
            clips = []
            for idx, mp4_file in enumerate(mp4_files, 1):
                base_name = mp4_file.stem
                manifest_file = p / f"{base_name}_manifest.json"
                desc_file = p / f"{base_name}_description.txt"
                
                manifest_data = {}
                if manifest_file.exists():
                    try:
                        with open(manifest_file, "r", encoding="utf-8") as mf:
                            manifest_data = json.load(mf)
                    except Exception:
                        pass
                        
                desc_text = ""
                if desc_file.exists():
                    try:
                        with open(desc_file, "r", encoding="utf-8") as df:
                            desc_text = df.read()
                    except Exception:
                        pass
                        
                title = manifest_data.get("title", f"Short #{idx}")
                dur = round(float(manifest_data.get("duration", 60.0)), 1)
                t_start = manifest_data.get("source_start", 0.0)
                t_end = manifest_data.get("source_end", dur)
                music = manifest_data.get("music_track", "Carefree (CC-BY)")
                score = manifest_data.get("scores", {}).get("total", 96.0)
                
                encoded_folder = urllib.parse.quote(p.name)
                clips.append({
                    "id": idx,
                    "clip_id": base_name,
                    "title": title,
                    "duration": dur,
                    "time_range": f"{t_start:.1f}s - {t_end:.1f}s ({dur}s)",
                    "music": music,
                    "score": f"{score:.1f} / 100",
                    "file": f"/api/videos/{encoded_folder}/{mp4_file.name}",
                    "srt": f"/api/videos/{encoded_folder}/{base_name}.srt",
                    "description": desc_text or f"Highlights from {display_name}",
                    "excerpt": (desc_text.splitlines()[0] if desc_text else title).strip()
                })
                
            projects.append({
                "folder_name": p.name,
                "display_name": display_name,
                "clip_count": len(clips),
                "clips": clips
            })
            
    return {"projects": projects}

@app.post("/api/upload-video")
async def upload_source_video(file: UploadFile = File(...)):
    """
    Handles upload of source videos (.mp4, .mkv, .mov, .webm) into local workspace uploads directory.
    """
    allowed_exts = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported format {ext}. Allowed: {', '.join(allowed_exts)}")
        
    uploads_dir = BASE_DIR / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    clean_filename = Path(file.filename).name
    dest_path = uploads_dir / clean_filename
    
    total_bytes = 0
    with open(dest_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
            total_bytes += len(chunk)
            
    size_mb = round(total_bytes / (1024 * 1024), 2)
    log_event(f"Uploaded source video: {clean_filename} ({size_mb} MB) -> {dest_path}")
    
    return {
        "success": True,
        "filename": clean_filename,
        "path": str(dest_path.resolve()),
        "size_mb": size_mb
    }

@app.get("/api/local-videos")
async def list_local_videos():
    """
    Scans uploads and common local directories for ready-to-clip .mp4 and .mkv videos.
    """
    found = []
    seen_paths = set()
    
    scan_dirs = [
        ("Uploads", BASE_DIR / "uploads"),
        ("Downloads", Path.home() / "Downloads"),
        ("Movies", Path.home() / "Movies"),
        ("Videos", Path.home() / "Videos"),
        ("Desktop", Path.home() / "Desktop")
    ]
    
    for label, folder in scan_dirs:
        if not folder.exists():
            continue
        try:
            for item in folder.glob("*.*"):
                if item.is_file() and item.suffix.lower() in [".mp4", ".mkv", ".mov"]:
                    full_p = str(item.resolve())
                    if full_p not in seen_paths and item.stat().st_size > 1024 * 1024:
                        seen_paths.add(full_p)
                        size_mb = round(item.stat().st_size / (1024 * 1024), 1)
                        found.append({
                            "name": item.name,
                            "path": full_p,
                            "size_mb": size_mb,
                            "source": label
                        })
        except Exception:
            pass
            
    return {"videos": found[:20]}

@app.api_route("/api/music/{filename}", methods=["GET", "HEAD"])
async def stream_music_track(filename: str):
    track_path = BASE_DIR / "music_library" / "tracks" / filename
    if not track_path.exists():
        raise HTTPException(status_code=404, detail="Track not found")
    return FileResponse(track_path, media_type="audio/mpeg")

@app.get("/api/video/frame")
async def get_video_frame(path: str, timestamp: float = 2.0):
    """Extracts a single frame from the video as JPEG for previewing and manual crop area selection."""
    if not path or not path.strip():
        raise HTTPException(status_code=400, detail="Video path parameter is required")
        
    raw_path_str = path.strip().strip('"').strip("'")
    v_path = Path(raw_path_str)
    
    # Try various resolution strategies
    if not v_path.exists():
        # Try relative to BASE_DIR
        candidate1 = (BASE_DIR / raw_path_str).resolve()
        if candidate1.exists():
            v_path = candidate1
        else:
            # Try searching inside uploads/
            candidate2 = (BASE_DIR / "uploads" / Path(raw_path_str).name).resolve()
            if candidate2.exists():
                v_path = candidate2
            else:
                # Try matching without exact special characters
                cleaned_name = "".join(c for c in Path(raw_path_str).name if c.isalnum() or c in " ._-")
                match_found = None
                for uf in (BASE_DIR / "uploads").glob("*.*"):
                    uf_clean = "".join(c for c in uf.name if c.isalnum() or c in " ._-")
                    if cleaned_name and cleaned_name in uf_clean:
                        match_found = uf.resolve()
                        break
                if match_found:
                    v_path = match_found
                else:
                    raise HTTPException(status_code=404, detail=f"Video file not found: {raw_path_str}")

    cap = cv2.VideoCapture(str(v_path))
    ret, frame = False, None
    if cap.isOpened():
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_idx = max(0, int(timestamp * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            # Fallback to reading first available frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
        cap.release()

    # If cv2 fails (e.g. Unicode path or unusual container format), fallback to ffmpeg pipe
    if not ret or frame is None:
        try:
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(max(0.0, timestamp)),
                "-i", str(v_path),
                "-vframes", "1",
                "-f", "image2pipe",
                "-vcodec", "mjpeg",
                "-"
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
            if proc.returncode == 0 and len(proc.stdout) > 0:
                frame = cv2.imdecode(np.frombuffer(proc.stdout, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    ret = True
        except Exception as e:
            pass
    
    if not ret or frame is None:
        raise HTTPException(status_code=500, detail="Could not extract video frame")
        
    h, w = frame.shape[:2]
    # Check if face can be auto-detected to return suggested box
    cascade_path = BASE_DIR / "assets" / "haarcascade_frontalface_default.xml"
    detected_box = None
    if cascade_path.exists():
        face_cascade = cv2.CascadeClassifier(str(cascade_path.resolve()))
        scale = 960.0 / float(w)
        detect_h = int(h * scale)
        small = cv2.resize(frame, (960, detect_h), interpolation=cv2.INTER_LINEAR)
        gray = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
        faces = face_cascade.detectMultiScale(gray, 1.10, 4, minSize=(20, 20))
        if len(faces) > 0:
            faces = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)
            bx, by, bw, bh = faces[0]
            bx, by, bw, bh = bx / scale, by / scale, bw / scale, bh / scale
            fcx, fcy = bx + bw / 2.0, by + bh / 2.0
            cam_w = int(max(bw * 3.2, w * 0.28))
            cam_h = int(cam_w * 0.65)
            cx1 = max(0, min(w - cam_w, int(fcx - cam_w / 2.0)))
            cy1 = max(0, min(h - cam_h, int(fcy - cam_h * 0.48)))
            detected_box = [cx1, cy1, cam_w, cam_h]
            
    success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        raise HTTPException(status_code=500, detail="Encoding frame failed")
        
    return Response(
        content=buffer.tobytes(),
        media_type="image/jpeg",
        headers={
            "X-Video-Width": str(w),
            "X-Video-Height": str(h),
            "X-Detected-Cam-Box": json.dumps(detected_box) if detected_box else "null"
        }
    )

@app.post("/api/youtube/prepare")
async def prepare_youtube_short(payload: Dict[str, Any]):
    """Prepares YouTube Shorts metadata ready for API upload."""
    title = payload.get("title", "Viral Podcast Short")[:100]
    desc = payload.get("description", "")
    tags = payload.get("tags", ["shorts", "podcast", "viral", "interview"])
    
    formatted_desc = f"{desc}\n\n#shorts #podcast #interview #viral\n\nAutomated by Clipper Studio"
    
    return {
        "status": "ready_for_upload",
        "snippet": {
            "title": f"{title} #shorts",
            "description": formatted_desc,
            "tags": tags,
            "categoryId": "24" # Entertainment
        },
        "status_setting": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        },
        "message": "Metadata formatted for YouTube Data API v3 Shorts upload."
    }

def start_server(port: int = 8080):
    print(f"Starting Clipper Studio on http://localhost:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

if __name__ == "__main__":
    start_server(8080)
