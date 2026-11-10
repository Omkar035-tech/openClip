# Long-Form Studio — Comprehensive Test Plan

## 1. Unit Test Coverage
- **`test_models.py`**: Validates Pydantic serialization, defaults, and boundary constraints.
- **`test_storage.py`**: Validates SQLite schema initialization, project creation, status transitions, and history stacks.
- **`test_ingestion.py`**: Validates FFprobe parsing, audio stream extraction, and chunk slicing logic.
- **`test_vad.py`**: Validates speech vs non-speech interval detection on synthetic sine/silence audio.
- **`test_scene.py`**: Validates scene cut boundary extraction.
- **`test_edl.py`**: Validates contiguous timeline verification, speech padding, and output timestamp recalculation on cut overrides.
- **`test_editorial_validator.py`**: Validates JSON sanitization from untrusted LLM outputs.

## 2. Integration & End-to-End Test
- **Synthetic End-to-End Pipeline**:
  - Generate a 30-second synthetic multi-segment MP4 containing:
    1. 0s–8s: Synthetic tone / test speech (Action: `KEEP`)
    2. 8s–16s: Absolute silence with static frame (Action: `CUT`)
    3. 16s–24s: High visual motion + synthetic voice (Action: `KEEP`)
    4. 24s–30s: Dead air silence (Action: `CUT`)
  - Run full Long-Form Studio pipeline: Ingestion -> VAD -> Scene -> EDL -> Review Override -> FFmpeg Render -> Output Verification.
  - Verify that the resulting rendered video has a valid duration (~16 seconds), clean audio transitions, and passes ffprobe integrity inspection.

## 3. Regression Safeguard Tests
- Run existing openClip verification tests to ensure Shorts Studio and Wayin 2.0 endpoints remain 100% operational.
