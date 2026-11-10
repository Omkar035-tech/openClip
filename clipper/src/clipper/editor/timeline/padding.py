from typing import List, Dict, Any

def apply_safety_padding(intervals: List[Dict[str, Any]], padding_sec: float = 0.40, max_duration: float = 100000.0) -> List[Dict[str, Any]]:
    """
    Extends speech boundaries by padding_sec at both ends to protect conversational
    intonation, word attacks, and trail-offs. Reconciles overlapping padded intervals.
    """
    if not intervals:
        return []
        
    padded = []
    for seg in intervals:
        start = max(0.0, seg["start"] - padding_sec)
        end = min(max_duration, seg["end"] + padding_sec)
        padded.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "action": seg.get("action", "KEEP"),
            "reason": seg.get("reason", "Speech segment"),
            "tags": seg.get("tags", ["speech"])
        })
        
    # Sort and merge overlapping keep intervals
    padded.sort(key=lambda x: x["start"])
    merged = [padded[0]]
    
    for current in padded[1:]:
        prev = merged[-1]
        if current["start"] <= prev["end"]:
            # Overlap: extend previous interval
            prev["end"] = max(prev["end"], current["end"])
            prev["tags"] = list(set(prev.get("tags", []) + current.get("tags", [])))
        else:
            merged.append(current)
            
    return merged
