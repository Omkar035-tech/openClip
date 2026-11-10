import uuid
from typing import List, Dict, Any, Tuple
from clipper.editor.models import SegmentModel, EDLModel
from clipper.editor.timeline.padding import apply_safety_padding

def build_contiguous_edl(
    project_id: str,
    source_media_path: str,
    total_duration: float,
    keep_intervals: List[Dict[str, Any]],
    padding_sec: float = 0.40
) -> EDLModel:
    """
    Transforms kept speech/reaction intervals into a strict, contiguous,
    non-destructive Edit Decision List covering 0.0s to total_duration.
    """
    # 1. Apply safety padding around kept moments
    padded_keeps = apply_safety_padding(keep_intervals, padding_sec=padding_sec, max_duration=total_duration)
    
    # 2. Build full contiguous timeline alternating between KEEP and CUT
    segments: List[SegmentModel] = []
    current_time = 0.0
    seg_idx = 0
    
    for k in padded_keeps:
        k_start = max(0.0, k["start"])
        k_end = min(total_duration, k["end"])
        
        # If there is a gap between current_time and k_start, that gap is a CUT
        if k_start > current_time + 0.15: # Ignore microscopic jitter < 150ms
            gap_duration = k_start - current_time
            segments.append(SegmentModel(
                id=f"seg_{uuid.uuid4().hex[:8]}",
                index=seg_idx,
                source_start=round(current_time, 2),
                source_end=round(k_start, 2),
                duration=round(gap_duration, 2),
                action="CUT",
                confidence=0.92,
                reason="Dead air / non-speech pause",
                tags=["dead_air"],
                transition_in="none",
                transition_out="none"
            ))
            seg_idx += 1
            
        # The Kept segment
        keep_duration = max(0.0, k_end - k_start)
        if keep_duration > 0.1:
            segments.append(SegmentModel(
                id=f"seg_{uuid.uuid4().hex[:8]}",
                index=seg_idx,
                source_start=round(k_start, 2),
                source_end=round(k_end, 2),
                duration=round(keep_duration, 2),
                action="KEEP",
                confidence=0.95,
                reason=k.get("reason", "Speech & engagement dialogue"),
                tags=k.get("tags", ["speech"]),
                transition_in="cut",
                transition_out="none"
            ))
            seg_idx += 1
            
        current_time = k_end
        
    # Trailing segment if video ends on a pause
    if current_time < total_duration - 0.2:
        gap_duration = total_duration - current_time
        segments.append(SegmentModel(
            id=f"seg_{uuid.uuid4().hex[:8]}",
            index=seg_idx,
            source_start=round(current_time, 2),
            source_end=round(total_duration, 2),
            duration=round(gap_duration, 2),
            action="CUT",
            confidence=0.95,
            reason="Trailing dead air",
            tags=["dead_air"],
            transition_in="none",
            transition_out="none"
        ))
        
    # 3. Recalculate output timestamps
    recalculate_output_timestamps(segments)
    
    cut_count = sum(1 for s in segments if s.action == "CUT")
    kept_count = sum(1 for s in segments if s.action == "KEEP")
    edited_duration = sum(s.duration for s in segments if s.action == "KEEP")
    
    return EDLModel(
        project_id=project_id,
        source_media_path=source_media_path,
        original_duration=round(total_duration, 2),
        estimated_edited_duration=round(edited_duration, 2),
        cut_count=cut_count,
        kept_count=kept_count,
        segments=segments
    )

def recalculate_output_timestamps(segments: List[SegmentModel]) -> None:
    """Updates output_start and output_end for all segments based on current KEEP/CUT actions."""
    timeline_cursor = 0.0
    for s in segments:
        if s.action == "KEEP":
            s.output_start = round(timeline_cursor, 2)
            s.output_end = round(timeline_cursor + s.duration, 2)
            timeline_cursor += s.duration
        else:
            # Cut segment has zero duration on output timeline
            s.output_start = round(timeline_cursor, 2)
            s.output_end = round(timeline_cursor, 2)
