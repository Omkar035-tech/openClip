import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from faster_whisper import WhisperModel
try:
    import av
    _orig_av_open = av.open
    def _patched_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)
    av.open = _patched_av_open
except ImportError:
    pass

def extract_audio(video_path: str, output_wav: str) -> str:
    """Extracts 16kHz mono WAV from input video."""
    os.makedirs(os.path.dirname(os.path.abspath(output_wav)), exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_wav
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_wav

def transcribe_video(video_path: str, cache_dir: Path, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Transcribes video with word-level timestamps on Apple Silicon.
    Primary: mlx-whisper (GPU). Fallback: faster-whisper.
    Caches results in cache_dir / transcript.json.
    """
    transcript_file = cache_dir / "transcript.json"
    if transcript_file.exists():
        print(f"Loaded cached transcript from {transcript_file}")
        with open(transcript_file, "r", encoding="utf-8") as f:
            return json.load(f)
            
    wav_path = cache_dir / "audio_16k.wav"
    print(f"Extracting 16kHz audio from {video_path}...")
    extract_audio(video_path, str(wav_path))
    
    backend = config.get("models", {}).get("whisper_backend", "mlx")
    model_name = config.get("models", {}).get("whisper_model", "mlx-community/whisper-large-v3-turbo")
    fallback_model = config.get("models", {}).get("fallback_whisper_model", "base.en")
    
    results = None
    
    # 1. Primary: MLX-Whisper on Apple Silicon GPU (macOS only)
    if backend == "mlx" and sys.platform == "darwin":
        try:
            print(f"Running mlx-whisper GPU transcription ({model_name})...")
            t0 = time.time()
            import mlx_whisper
            res = mlx_whisper.transcribe(
                str(wav_path),
                path_or_hf_repo=model_name,
                word_timestamps=True,
                verbose=False
            )
            raw_segments = res.get("segments", [])
            results = []
            for s in raw_segments:
                words = []
                for w in s.get("words", []):
                    words.append({
                        "word": w.get("word", ""),
                        "start": round(w.get("start", 0.0), 2),
                        "end": round(w.get("end", 0.0), 2),
                        "probability": round(w.get("probability", 1.0), 2)
                    })
                results.append({
                    "id": s.get("id", len(results)),
                    "start": round(s.get("start", 0.0), 2),
                    "end": round(s.get("end", 0.0), 2),
                    "text": s.get("text", "").strip(),
                    "words": words,
                    "speaker": "Speaker"
                })
            print(f"mlx-whisper completed in {time.time()-t0:.1f}s ({len(results)} segments)")
        except Exception as e:
            print(f"mlx-whisper failed or unavailable ({e}). Falling back to faster-whisper...")
            results = None
            
    # 2. Fallback: faster-whisper (CTranslate2 INT8)
    if results is None:
        print(f"Running faster-whisper fallback ({fallback_model})...")
        t0 = time.time()
        # Faster-whisper with CTranslate2 INT8 quantization & optimized greedy decoding
        model = WhisperModel(fallback_model, device="cpu", compute_type="int8", cpu_threads=4)
        segments_gen, _ = model.transcribe(
            str(wav_path),
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400),
            beam_size=1,
            condition_on_previous_text=False
        )
        results = []
        for s in segments_gen:
            words = []
            if s.words:
                for w in s.words:
                    words.append({
                        "word": w.word,
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 2)
                    })
            results.append({
                "id": s.id,
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "text": s.text.strip(),
                "words": words,
                "speaker": "Speaker"
            })
        print(f"faster-whisper completed in {time.time()-t0:.1f}s ({len(results)} segments)")
        
    with open(transcript_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    return results
