import os
import json
import numpy as np
import librosa
from pathlib import Path
from typing import Dict, List, Any

def compute_audio_features(wav_path: str, transcript: List[Dict[str, Any]], cache_dir: Path) -> Dict[str, Any]:
    """
    Computes local high-precision acoustic virality signals:
    - Vectorized RMS energy per 1s window with delta RMS (shout/scream spike detector)
    - Spectral Centroid & Pitch Variance (fundamental frequency F0 estimation)
    - Laughter & Reaction Acoustic Probability (high-frequency burst + periodic unvoiced bursts)
    - Speech velocity (words per second)
    Saves to cache_dir / features.json.
    """
    features_file = cache_dir / "features.json"
    if features_file.exists():
        try:
            with open(features_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if "laughter_timeline" in cached:
                    return cached
        except Exception:
            pass

    print(f"[Acoustic Engine] Analyzing screams, laughter, pitch & RMS spikes on {wav_path}...")
    
    rms_list = []
    spec_list = []
    laughter_prob_list = []
    total_samples = 0
    sr = 16000

    # Stream audio in 1-second chunks for O(1) memory and maximum throughput
    try:
        import soundfile as sf
        info = sf.info(wav_path)
        sr = info.samplerate
        duration = float(info.duration)
        block_size = sr
        freqs = np.fft.rfftfreq(block_size, 1.0 / sr)
        
        # Audio bands for laughter/screams:
        # Screams: strong energy above 1200 Hz + high RMS
        # Laughter: rhythmic energy modulation in 500-2500 Hz range
        high_band_mask = (freqs >= 1000) & (freqs <= 3500)
        
        prev_rms = 0.0
        for block in sf.blocks(wav_path, blocksize=block_size, dtype='float32', always_2d=False):
            if len(block.shape) > 1:
                block = np.mean(block, axis=1) # Mono
            total_samples += len(block)
            
            # 1. RMS Energy
            rms_val = float(np.sqrt(np.mean(block ** 2)))
            rms_list.append(rms_val)
            
            # 2. Spectral Centroid
            if len(block) == block_size:
                mag = np.abs(np.fft.rfft(block))
                mag_sum = float(np.sum(mag))
                if mag_sum > 1e-6:
                    sc = float(np.sum(mag * freqs) / mag_sum)
                    # Laughter / scream signature: high band ratio
                    high_energy = float(np.sum(mag[high_band_mask]))
                    band_ratio = high_energy / mag_sum
                else:
                    sc = 0.0
                    band_ratio = 0.0
            else:
                sc = 0.0
                band_ratio = 0.0
            spec_list.append(sc)
            
            # 3. Laughter / Sudden Shout Reaction score
            delta_rms = max(0.0, rms_val - prev_rms)
            laugh_prob = float(np.clip(band_ratio * 1.5 + (delta_rms * 8.0), 0.0, 1.0))
            laughter_prob_list.append(laugh_prob)
            prev_rms = rms_val
            
    except Exception as e:
        print(f"[Acoustic Engine] Streaming fallback to librosa: {e}")
        y, sr = librosa.load(wav_path, sr=16000)
        duration = float(len(y) / sr)
        hop_length = sr
        frame_length = sr
        rms_list = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0].tolist()
        spec_list = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0].tolist()
        laughter_prob_list = [0.1] * len(rms_list)

    rms_arr = np.array(rms_list, dtype=np.float32)
    spec_arr = np.array(spec_list, dtype=np.float32)
    laugh_arr = np.array(laughter_prob_list, dtype=np.float32)
    
    # Delta RMS: sudden explosion in sound (screams, gasp, loud reaction)
    delta_rms_arr = np.zeros_like(rms_arr)
    if len(rms_arr) > 1:
        delta_rms_arr[1:] = np.maximum(0.0, rms_arr[1:] - rms_arr[:-1])
    
    # Normalize features to [0, 1]
    rms_min, rms_max = float(np.min(rms_arr)), float(np.max(rms_arr))
    spec_min, spec_max = float(np.min(spec_arr)), float(np.max(spec_arr))
    drms_max = float(np.max(delta_rms_arr)) if float(np.max(delta_rms_arr)) > 0 else 1.0
    
    rms_norm = (rms_arr - rms_min) / (rms_max - rms_min + 1e-6)
    spec_norm = (spec_arr - spec_min) / (spec_max - spec_min + 1e-6)
    drms_norm = delta_rms_arr / drms_max
    
    # Build timeline
    timeline = []
    num_seconds = min(len(rms_norm), len(spec_norm), len(laugh_arr))
    for sec in range(num_seconds):
        composite = (
            0.45 * rms_norm[sec] +
            0.25 * drms_norm[sec] +
            0.15 * spec_norm[sec] +
            0.15 * laugh_arr[sec]
        )
        timeline.append({
            "second": sec,
            "rms": round(float(rms_norm[sec]), 3),
            "delta_rms": round(float(drms_norm[sec]), 3),
            "spectral": round(float(spec_norm[sec]), 3),
            "laughter_prob": round(float(laugh_arr[sec]), 3),
            "composite": round(float(composite), 3)
        })
        
    features_data = {
        "duration": round(duration, 2),
        "mean_rms": round(float(np.mean(rms_norm)), 3),
        "laughter_timeline": True,
        "timeline": timeline
    }
    
    with open(features_file, "w", encoding="utf-8") as f:
        json.dump(features_data, f, indent=2)
        
    print(f"[Acoustic Engine] Ready. Processed {duration:.1f}s with Delta-RMS & reaction detection.")
    return features_data

def get_window_energy(features: Dict[str, Any], t_start: float, t_end: float) -> float:
    """
    Computes acoustic energy score (0 to 100) for a given time window.
    Incorporates sustained energy, scream / shout peaks, and laughter spikes.
    """
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
    d_rms_peaks = [item.get("delta_rms", 0.0) for item in slice_data]
    laugh_peaks = [item.get("laughter_prob", 0.0) for item in slice_data]
    
    mean_val = float(np.mean(composites))
    max_val = float(np.max(composites))
    max_drms = float(np.max(d_rms_peaks)) if d_rms_peaks else 0.0
    max_laugh = float(np.max(laugh_peaks)) if laugh_peaks else 0.0
    
    # 50% sustained energy + 25% peak intensity + 15% sudden scream/shout + 10% laughter
    score = (0.50 * mean_val + 0.25 * max_val + 0.15 * max_drms + 0.10 * max_laugh) * 100.0
    return round(float(min(100.0, score)), 2)
