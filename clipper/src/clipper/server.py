import os
import sys
import json
import time
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
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
    print(entry)

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

def run_pipeline_thread(payload: Dict[str, Any]):
    try:
        studio_state["status"] = "processing"
        studio_state["error_message"] = None
        studio_state["progress"] = 5
        studio_state["completed_clips"] = []
        
        video_path = payload.get("video_path", "").strip()
        if not video_path or not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        v_path = Path(video_path).resolve()
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
        
        # Caption customization
        config["captions"]["font_file"] = payload.get("font_file", "Montserrat-ExtraBold.ttf")
        config["captions"]["font_size"] = int(payload.get("font_size", 68))
        config["captions"]["primary_color"] = payload.get("primary_color", "#FFFFFF")
        config["captions"]["active_color"] = payload.get("active_color", "#FFD400")
        config["captions"]["stroke_color"] = payload.get("stroke_color", "#000000")
        config["captions"]["auto_detect_emphasis"] = bool(payload.get("auto_detect_emphasis", True))
        
        # Effects customization
        config["effects"]["white_flash"] = bool(payload.get("effects_flash", True))
        config["effects"]["progress_bar"] = bool(payload.get("effects_progress", True))
        config["effects"]["vignette"] = bool(payload.get("effects_vignette", True))
        config["camera"]["hook_zoom"] = float(payload.get("hook_zoom", 1.12))
        
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
        log_event("Scanning dialogue for curiosity hooks, comedy banter, and punchlines...")
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
        for idx, clip_meta in enumerate(ranked_clips, 1):
            studio_state["current_clip"] = clip_meta["suggested_title"]
            studio_state["stage"] = f"Rendering Short #{idx}/{total_clips}: '{clip_meta['suggested_title']}'"
            base_p = 50 + int(45 * (idx - 1) / total_clips)
            studio_state["progress"] = base_p
            log_event(f"Rendering #{idx}: '{clip_meta['suggested_title']}' ({clip_meta['duration']}s)...")
            
            # Custom OST override if selected
            if selected_track_id and selected_track_id != "auto":
                clip_meta_custom = dict(clip_meta)
                clip_meta_custom["custom_track_id"] = selected_track_id
            else:
                clip_meta_custom = clip_meta
                
            manifest = render_short_clip(str(v_path), clip_meta_custom, idx, out_dir, config, excluded_music)
            
            # Register completed clip
            clip_file = f"short_{idx:02d}.mp4"
            studio_state["completed_clips"].append({
                "clip_id": f"short_{idx:02d}",
                "title": clip_meta["suggested_title"],
                "duration": clip_meta["duration"],
                "score": clip_meta["score_total"],
                "time_range": f"{clip_meta['start']:.1f}s - {clip_meta['end']:.1f}s",
                "mp4_url": f"/api/videos/{v_path.stem}/{clip_file}",
                "srt_url": f"/api/videos/{v_path.stem}/short_{idx:02d}.srt",
                "text": clip_meta["text"],
                "mood": clip_meta["mood"]["primary_mood"]
            })
            log_event(f"Successfully finished Short #{idx} (1080x1920 @ 30fps).")
            
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

@app.api_route("/api/music/{filename}", methods=["GET", "HEAD"])
async def stream_music_track(filename: str):
    track_path = BASE_DIR / "music_library" / "tracks" / filename
    if not track_path.exists():
        raise HTTPException(status_code=404, detail="Track not found")
    return FileResponse(track_path, media_type="audio/mpeg")

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
