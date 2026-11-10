import os
from pathlib import Path
from clipper.editor.models import VideoMetadata, AnalysisConfig, SegmentModel, EDLModel
from clipper.editor.timeline.padding import apply_safety_padding
from clipper.editor.timeline.edl import build_contiguous_edl, recalculate_output_timestamps
from clipper.editor.intelligence.validator import sanitize_and_parse_llm_json

def test_safety_padding_logic():
    intervals = [
        {"start": 10.0, "end": 15.0, "action": "KEEP"},
        {"start": 15.2, "end": 20.0, "action": "KEEP"}
    ]
    # Adding 0.4s padding should bridge the 0.2s gap into a single continuous kept interval
    padded = apply_safety_padding(intervals, padding_sec=0.40)
    assert len(padded) == 1
    assert padded[0]["start"] == 9.6
    assert padded[0]["end"] == 20.4
    print("✓ test_safety_padding_logic passed")

def test_contiguous_edl_builder():
    keep_moments = [
        {"start": 5.0, "end": 10.0, "reason": "Speech 1"},
        {"start": 20.0, "end": 30.0, "reason": "Speech 2"}
    ]
    total_duration = 40.0
    edl = build_contiguous_edl("test_proj", "dummy.mp4", total_duration, keep_moments, padding_sec=0.5)
    
    assert edl.cut_count >= 2 # 0-4.5s cut, 10.5-19.5s cut, 30.5-40s cut
    assert edl.kept_count == 2
    assert edl.original_duration == 40.0
    assert edl.estimated_edited_duration > 0.0
    print("✓ test_contiguous_edl_builder passed")

def test_llm_json_validator():
    raw_response = """
    Here are the editorial decisions:
    ```json
    [
      {
        "start": 14.2,
        "end": 22.5,
        "action": "KEEP",
        "confidence": 0.96,
        "reason": "Dramatic pause before shout",
        "tags": ["suspense", "reaction"]
      },
      {
        "start": 25.0,
        "end": 35.0,
        "action": "CUT",
        "confidence": 0.90,
        "reason": "Dead air phone check",
        "tags": ["dead_air"]
      }
    ]
    ```
    """
    decisions = sanitize_and_parse_llm_json(raw_response)
    assert len(decisions) == 2
    assert decisions[0]["action"] == "KEEP"
    assert decisions[0]["confidence"] == 0.96
    assert decisions[1]["action"] == "CUT"
    print("✓ test_llm_json_validator passed")

if __name__ == "__main__":
    print("Running Long-Form Studio Unit Tests...")
    test_safety_padding_logic()
    test_contiguous_edl_builder()
    test_llm_json_validator()
    print("ALL LONG-FORM STUDIO UNIT TESTS PASSED!")
