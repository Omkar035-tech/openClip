from typing import List, Dict, Any

def build_editorial_context_payload(
    window_id: str,
    start_sec: float,
    end_sec: float,
    speech_intervals: List[Dict[str, Any]],
    silence_intervals: List[Dict[str, Any]],
    transcript_phrases: List[Dict[str, Any]],
    scenes: List[Dict[str, Any]],
    content_type: str = "general"
) -> Dict[str, Any]:
    """
    Constructs a compact JSON context payload representing a 3-5 minute window.
    Filters out obvious speech and obvious dead air so LLM only reasons on borderline/narrative sections.
    """
    # Isolate phrases inside this window
    window_phrases = [
        p["text"] for p in transcript_phrases
        if (p["start"] >= start_sec and p["start"] <= end_sec) or (p["end"] >= start_sec and p["end"] <= end_sec)
    ]
    
    # Borderline pauses: silences between 1.5s and 12s that might contain reactions/suspense
    borderline_pauses = [
        {"start": s["start"], "end": s["end"], "duration": s["duration"]}
        for s in silence_intervals
        if (s["start"] >= start_sec and s["end"] <= end_sec) and (1.2 <= s["duration"] <= 20.0)
    ]
    
    return {
        "window_id": window_id,
        "window_range": f"{start_sec:.1f}s - {end_sec:.1f}s",
        "content_type": content_type,
        "dialogue_summary": " ... ".join(window_phrases[:12]),
        "candidate_pauses_for_review": borderline_pauses[:10]
    }
