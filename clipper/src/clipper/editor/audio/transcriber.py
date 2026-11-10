from typing import List, Dict, Any, Optional
from pathlib import Path
from clipper.transcribe import transcribe_video

def transcribe_long_form_audio(video_or_audio_path: str, cache_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Transcribes audio using faster-whisper and produces structured segment dictionaries
    with word-level timestamps.
    """
    path = Path(video_or_audio_path)
    
    if cache_dir:
        c_dir = Path(cache_dir)
    else:
        c_dir = path.parent / ".transcribe_cache"
    c_dir.mkdir(parents=True, exist_ok=True)
    
    config = {
        "models": {
            "whisper_hardware": "auto",
            "cpu_threads": 4
        }
    }
    
    # Calls transcribe_video(video_path, cache_dir, config)
    # returns list of segments: [{'id': 0, 'start': 0.0, 'end': 4.2, 'text': '...', 'words': [...]}, ...]
    segments = transcribe_video(str(path.resolve()), c_dir, config)
    
    phrases = []
    if not segments:
        return phrases
        
    for seg in segments:
        seg_text = seg.get("text", "").strip()
        seg_start = seg.get("start", 0.0)
        seg_end = seg.get("end", 0.0)
        
        # If words list is present, extract words
        words = seg.get("words", [])
        if words:
            # We can also chunk by sentence punctuation inside words
            curr_words = []
            curr_start = words[0].get("start", seg_start)
            for w in words:
                w_text = w.get("word", "")
                curr_words.append(w_text)
                if any(w_text.endswith(p) for p in [".", "!", "?", "...", ","]):
                    curr_end = w.get("end", seg_end)
                    phrases.append({
                        "start": round(curr_start, 2),
                        "end": round(curr_end, 2),
                        "text": " ".join(curr_words).strip(),
                        "duration": round(curr_end - curr_start, 2)
                    })
                    curr_words = []
                    curr_start = w.get("end", seg_end)
            if curr_words:
                curr_end = words[-1].get("end", seg_end)
                phrases.append({
                    "start": round(curr_start, 2),
                    "end": round(curr_end, 2),
                    "text": " ".join(curr_words).strip(),
                    "duration": round(curr_end - curr_start, 2)
                })
        else:
            if seg_text:
                phrases.append({
                    "start": round(seg_start, 2),
                    "end": round(seg_end, 2),
                    "text": seg_text,
                    "duration": round(seg_end - seg_start, 2)
                })
                
    return phrases
