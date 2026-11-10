import numpy as np
import soundfile as sf
from typing import Dict, Any

def extract_window_audio_features(wav_path: str, start_sec: float, end_sec: float) -> Dict[str, float]:
    """Calculates RMS loudness, peak amplitude, and zero-crossing rate for a specific window."""
    try:
        data, sr = sf.read(wav_path)
        if data.ndim > 1:
            data = data.mean(axis=1)
            
        i_start = max(0, int(start_sec * sr))
        i_end = min(len(data), int(end_sec * sr))
        
        if i_end <= i_start:
            return {"rms_energy": 0.0, "peak_amplitude": 0.0, "zcr": 0.0}
            
        chunk = data[i_start:i_end]
        rms = float(np.sqrt(np.mean(chunk**2) + 1e-12))
        peak = float(np.max(np.abs(chunk)))
        
        # Zero-crossing rate
        zcr = float(np.mean(np.abs(np.diff(np.sign(chunk)))) / 2.0)
        
        return {
            "rms_energy": round(rms, 4),
            "peak_amplitude": round(peak, 4),
            "zcr": round(zcr, 4)
        }
    except Exception:
        return {"rms_energy": 0.0, "peak_amplitude": 0.0, "zcr": 0.0}
