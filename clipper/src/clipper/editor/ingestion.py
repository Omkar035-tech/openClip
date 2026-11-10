import subprocess
import json
import uuid
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from clipper.editor.models import VideoMetadata, ProjectModel
from clipper.editor.storage import save_project

def probe_video(video_path: str) -> VideoMetadata:
    """Uses ffprobe to extract reliable duration, resolution, codecs, and fps."""
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found at: {video_path}")
        
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path.resolve())
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    probe_data = json.loads(result.stdout)
    
    video_stream = next((s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in probe_data.get("streams", []) if s.get("codec_type") == "audio"), None)
    
    if not video_stream:
        raise ValueError(f"No video stream detected in file: {video_path}")
        
    # Calculate FPS
    fps = 30.0
    r_frame_rate = video_stream.get("r_frame_rate", "30/1")
    if "/" in r_frame_rate:
        num, den = r_frame_rate.split("/")
        if float(den) > 0:
            fps = float(num) / float(den)
    else:
        try:
            fps = float(r_frame_rate)
        except Exception:
            fps = 30.0
            
    # Duration
    duration = float(probe_data.get("format", {}).get("duration") or video_stream.get("duration") or 0.0)
    width = int(video_stream.get("width", 1920))
    height = int(video_stream.get("height", 1080))
    v_codec = video_stream.get("codec_name", "unknown")
    a_codec = audio_stream.get("codec_name") if audio_stream else None
    bitrate = int(probe_data.get("format", {}).get("bit_rate") or 0)
    
    return VideoMetadata(
        duration=round(duration, 2),
        width=width,
        height=height,
        fps=round(fps, 2),
        video_codec=v_codec,
        audio_codec=a_codec,
        bitrate=bitrate if bitrate > 0 else None
    )

def extract_analysis_audio(video_path: str, output_wav_path: str) -> str:
    """
    Extracts a 16kHz 16-bit mono PCM .wav audio stream for ultra-fast VAD,
    feature extraction, and Whisper transcription.
    """
    out_p = Path(output_wav_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    if out_p.exists() and out_p.stat().st_size > 1024:
        return str(out_p.resolve())
        
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(Path(video_path).resolve()),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(out_p.resolve())
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    return str(out_p.resolve())

def create_long_form_project(video_path: str, title: Optional[str] = None, content_type: str = "general") -> ProjectModel:
    """Initializes a new long-form project and saves metadata to SQLite."""
    meta = probe_video(video_path)
    path = Path(video_path)
    
    proj_title = title or path.stem.replace("_", " ").replace("-", " ").strip()
    proj_id = f"lf_{uuid.uuid4().hex[:10]}"
    now = datetime.utcnow().isoformat()
    
    project = ProjectModel(
        id=proj_id,
        title=proj_title,
        source_video_path=str(path.resolve()),
        content_type=content_type,
        metadata=meta,
        status="created",
        progress_pct=0.0,
        current_stage="Project Created",
        error_message=None,
        created_at=now,
        updated_at=now
    )
    save_project(project)
    return project
