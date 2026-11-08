import os
import json
import numpy as np
import librosa
from pathlib import Path
from typing import Dict, List, Any

def compute_audio_features(wav_path: str, transcript: List[Dict[str, Any]], cache_dir: Path) -> Dict[str, Any]:
    """
    Computes local cheap acoustic signals:
    - RMS energy per 1s window
    - Pitch variance / spectral centroid
    - Speech rate (words per second)
    Combines these into an energy score per candidate segment window.
    Saves to cache_dir / features.json.
    """
    features_file = cache_dir / "features.json"
    if features_file.exists():
        with open(features_file, "r", encoding="utf-8") as f:
            return json.load(f)
            
    print(f"Analyzing acoustic signals (RMS energy, spectral variance) on {wav_path}...")
    # Load audio at 16kHz
    y, sr = librosa.load(wav_path, sr=16000)
    duration = float(len(y) / sr)
    
    # Hop length of 1 second (16000 samples)
    hop_length = sr
    frame_length = sr
    
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    spec_cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    
    # Normalize features to [0, 1]
    rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-6)
    spec_norm = (spec_cent - np.min(spec_cent)) / (np.max(spec_cent) - np.min(spec_cent) + 1e-6)
    
    # Per-second timeline
    timeline = []
    num_seconds = min(len(rms_norm), len(spec_norm))
    for sec in range(num_seconds):
        timeline.append({
            "second": sec,
            "rms": round(float(rms_norm[sec]), 3),
            "spectral": round(float(spec_norm[sec]), 3),
            "composite": round(float(0.6 * rms_norm[sec] + 0.4 * spec_norm[sec]), 3)
        })
        
    features_data = {
        "duration": round(duration, 2),
        "mean_rms": round(float(np.mean(rms_norm)), 3),
        "timeline": timeline
    }
    
    with open(features_file, "w", encoding="utf-8") as f:
        json.dump(features_data, f, indent=2)
        
    print(f"Computed acoustic features for {duration:.1f}s audio.")
    return features_data

def get_window_energy(features: Dict[str, Any], t_start: float, t_end: float) -> float:
    """Computes acoustic energy score (0 to 100) for a given time window."""
    timeline = features.get("timeline", [])
    if not timeline:
        return 50.0
        
    s_idx = max(0, int(t_start))
    e_idx = min(len(timeline), int(t_end) + 1)
    
    if s_idx >= e_idx:
        return 50.0
        
    slice_data = timeline[s_idx:e_idx]
    if not slice_data:
        return 50.0
        
    composites = [item["composite"] for item in slice_data]
    mean_val = float(np.mean(composites))
    max_val = float(np.max(composites))
    
    # Score 0 - 100
    score = (0.7 * mean_val + 0.3 * max_val) * 100.0
    return round(float(score), 2)
