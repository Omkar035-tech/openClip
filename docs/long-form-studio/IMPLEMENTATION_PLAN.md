# Long-Form Studio — Implementation Plan & Roadmap

## 1. Execution Phases

### Stage 1: Foundation & Isolation
- Create `docs/long-form-studio/` specifications (EDL, API, Database, Dependencies, Test Plan).
- Define Pydantic models in `clipper/src/clipper/editor/models.py`.
- Implement local SQLite database store in `clipper/src/clipper/editor/storage.py` (`clipper/long_form_projects.db`).
- Implement media ingestion and FFprobe probing in `clipper/src/clipper/editor/ingestion.py`.

### Stage 2: Media Analysis Modules
- Audio Extraction: 16kHz 16-bit mono stream via FFmpeg subprocess.
- Voice Activity Detection: Silero VAD / fast energy envelope fallback in `audio/vad.py`.
- Audio Features: RMS, zero-crossing rate, spectral centroid in `audio/features.py`.
- Speech Transcription: reuse faster-whisper from `clipper.transcribe` with word timestamps in `audio/transcriber.py`.
- Scene Boundary Detection: PySceneDetect integration with adaptive content detector in `visual/scene.py`.
- Visual Motion: Fast 2fps grayscale optical flow / frame difference in `visual/motion.py`.

### Stage 3: Editorial Intelligence & LLM Triage
- Compact Context Builder: Group 3-5 minute windows, summarize high-confidence audio/visual intervals, and isolate borderline segments in `intelligence/context_builder.py`.
- Editorial Agent: Groq Cloud LPU (`llama-3.3-70b-versatile`) with Gemini Fallback (`gemini-2.5-flash`) in `intelligence/editorial_agent.py`.
- Strict Output Validator: Ensure valid JSON with start, end, action, confidence, and editorial reasoning in `intelligence/validator.py`.

### Stage 4: Non-Destructive Edit Decision List (EDL)
- Core EDL data structure with segment sorting, gap detection, and output timestamp recalculation in `timeline/edl.py`.
- Safety Padding Enforcer: Add +0.4s to +0.8s padding around speech boundaries to avoid abrupt cutoffs in `timeline/padding.py`.
- OpenTimelineIO (.otio) serialization in `timeline/otio_export.py`.

### Stage 5: Backend API Integration
- Mount `/api/long-form/*` routes in `clipper/src/clipper/server.py`.
- Background task coordination: ThreadPoolExecutor / async workers for chunked ingestion and analysis.
- Live progress polling endpoint `/api/long-form/projects/{id}/status`.

### Stage 6: Frontend Studio Integration
- Dual Studio Workspace Navigation in `clipper/src/clipper/web/index.html`:
  - Toggle between `Shorts Studio` (existing 9:16 viral clip generator) and `Long-Form Studio` (16:9 full-length editor).
- Long-Form Studio Dashboard & Upload modal.
- Live Progress Tracker (Ingestion -> VAD -> Scene -> Whisper -> LLM -> EDL).
- Interactive Dual-Color Timeline Canvas:
  - Green blocks for KEEP, Red for CUT, Yellow for REVIEW.
  - One-click Cut Restoration and Override.
  - Video preview with synchronized timeline scrubbing.
- Export Center: MP4 rendering preset controls and .otio download.

### Stage 7: FFmpeg Filtergraph Rendering & Verification
- Filtergraph builder with crossfades, intro/outro fades, and audio normalization in `render/ffmpeg_builder.py`.
- Automated test suite validating ingestion, analysis, EDL padding, and render pipeline.
