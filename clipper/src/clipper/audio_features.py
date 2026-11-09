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
    
    rms_list = []
    spec_list = []
    total_samples = 0
    sr = 16000

    # High-speed vectorized streaming via SoundFile (O(1) memory, zero RAM spikes)
    try:
        import soundfile as sf
        info = sf.info(wav_path)
        sr = info.samplerate
        duration = float(info.duration)
        
        # Stream 1-second chunks
        block_size = sr
        freqs = np.fft.rfftfreq(block_size, 1.0 / sr)
        
        for block in sf.blocks(wav_path, blocksize=block_size, dtype='float32', always_2d=False):
            if len(block.shape) > 1:
                block = np.mean(block, axis=1) # Convert to mono
            total_samples += len(block)
            
            # Vectorized RMS
            rms_val = float(np.sqrt(np.mean(block ** 2)))
            rms_list.append(rms_val)
            
            # Vectorized Spectral Centroid
            if len(block) == block_size:
                mag = np.abs(np.fft.rfft(block))
                mag_sum = float(np.sum(mag))
                if mag_sum > 1e-6:
                    sc = float(np.sum(mag * freqs) / mag_sum)
                else:
                    sc = 0.0
            else:
                sc = 0.0
            spec_list.append(sc)
            
    except Exception as e:
        print(f"SoundFile streaming unavailable ({e}), using librosa fallback...")
        y, sr = librosa.load(wav_path, sr=16000)
        duration = float(len(y) / sr)
        hop_length = sr
        frame_length = sr
        rms_list = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0].tolist()
        spec_list = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0].tolist()
    
    rms_arr = np.array(rms_list, dtype=np.float32)
    spec_arr = np.array(spec_list, dtype=np.float32)
    
    # Normalize features to [0, 1]
    rms_min, rms_max = float(np.min(rms_arr)), float(np.max(rms_arr))
    spec_min, spec_max = float(np.min(spec_arr)), float(np.max(spec_arr))
    
    rms_norm = (rms_arr - rms_min) / (rms_max - rms_min + 1e-6)
    spec_norm = (spec_arr - spec_min) / (spec_max - spec_min + 1e-6)
    
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
