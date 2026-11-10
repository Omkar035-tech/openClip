from typing import List, Dict, Any, Optional
from pathlib import Path
from clipper.transcribe import transcribe_video

def transcribe_long_form_audio(video_or_audio_path: str, cache_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Transcribes audio using faster-whisper and produces structured segment dictionaries
    with word-level timestamps.
    """
    path = Path(video_or_audio_path)
    # Reuses proven faster-whisper engine from clipper.transcribe
    words = transcribe_video(path)
    
    # Structure into dialogue phrases/sentences
    phrases = []
    if not words:
        return phrases
        
    current_phrase = []
    phrase_start = words[0]["start"]
    
    for w in words:
        current_phrase.append(w["word"])
        # Split on sentence boundaries or natural conversational pauses (> 0.8s)
        if any(w["word"].endswith(p) for p in [".", "!", "?", "...", ","]) or (w.get("pause_after", 0.0) > 0.8):
            phrase_end = w["end"]
            phrases.append({
                "start": round(phrase_start, 2),
                "end": round(phrase_end, 2),
                "text": " ".join(current_phrase).strip(),
                "duration": round(phrase_end - phrase_start, 2)
            })
            current_phrase = []
            phrase_start = w["end"]
            
    if current_phrase:
        phrase_end = words[-1]["end"]
        phrases.append({
            "start": round(phrase_start, 2),
            "end": round(phrase_end, 2),
            "text": " ".join(current_phrase).strip(),
            "duration": round(phrase_end - phrase_start, 2)
        })
        
    return phrases
