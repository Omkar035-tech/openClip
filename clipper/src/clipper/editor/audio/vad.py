import numpy as np
import soundfile as sf
from pathlib import Path
from typing import List, Dict, Any, Tuple

def detect_speech_intervals(wav_path: str, silence_threshold_db: float = -35.0, min_speech_duration: float = 0.25, min_silence_duration: float = 0.8) -> List[Dict[str, Any]]:
    """
    Fast Voice Activity & Speech Interval Detector.
    Calculates windowed RMS energy profile and produces continuous speech/silence blocks.
    """
    data, sr = sf.read(wav_path)
    if data.ndim > 1:
        data = data.mean(axis=1)
        
    window_size = int(sr * 0.05) # 50ms frames
    hop_size = int(sr * 0.025)   # 25ms step
    
    # Calculate RMS in dB per frame
    rms_values = []
    times = []
    
    num_frames = (len(data) - window_size) // hop_size
    for i in range(max(0, num_frames)):
        frame = data[i * hop_size : i * hop_size + window_size]
        rms = np.sqrt(np.mean(frame**2) + 1e-12)
        rms_db = 20 * np.log10(rms + 1e-12)
        rms_values.append(rms_db)
        times.append(i * (hop_size / sr))
        
    rms_values = np.array(rms_values)
    times = np.array(times)
    
    # Binary speech mask
    is_speech = rms_values > silence_threshold_db
    
    # Merge short glitches and extract intervals
    intervals: List[Dict[str, Any]] = []
    if len(is_speech) == 0:
        return intervals
        
    current_state = is_speech[0]
    start_time = 0.0
    
    for i in range(1, len(is_speech)):
        if is_speech[i] != current_state:
            end_time = float(times[i])
            duration = end_time - start_time
            
            # Filter noise jitter
            if current_state and duration >= min_speech_duration:
                intervals.append({"type": "speech", "start": round(start_time, 2), "end": round(end_time, 2), "duration": round(duration, 2)})
            elif not current_state and duration >= min_silence_duration:
                intervals.append({"type": "silence", "start": round(start_time, 2), "end": round(end_time, 2), "duration": round(duration, 2)})
                
            current_state = is_speech[i]
            start_time = end_time
            
    # Final trailing interval
    final_time = float(len(data) / sr)
    if final_time > start_time:
        duration = final_time - start_time
        if current_state and duration >= min_speech_duration:
            intervals.append({"type": "speech", "start": round(start_time, 2), "end": round(final_time, 2), "duration": round(duration, 2)})
        elif not current_state and duration >= min_silence_duration:
            intervals.append({"type": "silence", "start": round(start_time, 2), "end": round(final_time, 2), "duration": round(duration, 2)})
            
    return intervals
