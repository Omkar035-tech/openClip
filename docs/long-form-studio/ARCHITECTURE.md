# Long-Form Studio — Architecture Specification

## 1. Overview & System Scope
**Long-Form Studio** is an intelligent, automated long-form video editing system designed to ingest 2–5 hour raw multi-modal footage (podcasts, gaming streams, tutorials, vlogs, and talking-head content) and synthesize a condensed, highly engaging master video (typically 1.5–3 hours).

### Key Differentiators:
- **Human-Grade Editorial Intelligence**: Unlike naive silence clippers that blindly cut audio whenever volume dips below an arbitrary threshold, Long-Form Studio analyzes multimodal evidence (VAD, pitch, spectral energy, scene cuts, optical motion, and LLM semantic context) to preserve dramatic silences, horror suspense, joke setups, and complete thoughts.
- **Non-Destructive Virtual Timeline (EDL)**: The raw video is never altered. The system constructs a JSON-based Edit Decision List with complete undo/redo, safety padding, and review overrides.
- **Strict Architectural Isolation**: Operates as an independent subsystem within openClip, reusing shared low-level utilities (hardware detection, faster-whisper, ffmpeg utilities, API health checks) without altering or endangering the existing 9:16 Shorts Studio pipeline.

---

## 2. High-Level System Architecture

```text
                               LONG-FORM STUDIO
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
       [Web UI / Dashboard]                         [FastAPI API Engine]
       - Workspace Navigation                      - Project Management
       - Project Creation                          - Media Ingestion & Chunking
       - Dual-Color Review Timeline                - Background Worker Pipeline
       - Cut Overrides & Playback                  - Stream/OTIO/MP4 Exporters
       - Rendering & Preset Center                           │
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      ▼
                        MEDIA PROCESSING PIPELINE
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
      AUDIO ENGINE              VISUAL ENGINE             SEMANTIC ENGINE
      - 16kHz Extraction        - PySceneDetect Cuts      - faster-whisper
      - Silero VAD Detection    - Frame Difference        - Word/Sentence Marks
      - RMS & Spectral Energy   - Optical Motion Map      - Rolling Windows
            │                         │                         │
            └─────────────────────────┼─────────────────────────┘
                                      ▼
                             FEATURE FUSION LAYER
                        (Normalized Chunk Timestamps)
                                      │
                                      ▼
                           AI EDITORIAL INTELLIGENCE
                      (Groq LPU / Gemini Fallback Agent)
                                      │
                    KEEP / CUT / REVIEW / EMPHASIZE / CHAPTER
                                      │
                                      ▼
                        NON-DESTRUCTIVE TIMELINE (EDL)
                    - Speech-edge Safety Padding (+0.4s to +0.8s)
                    - Overlap & Interval Reconciliation
                    - Undo / Redo History Stack
                                      │
                                      ▼
                       INTERACTIVE REVIEW & RENDER ENGINE
                    - Live Preview of Kept vs Cut Footage
                    - FFmpeg Complex Filtergraph Builder
                    - Crossfades / Audio Ducking / Dissolves
                    - Master 1080p MP4 / OpenTimelineIO (.otio)
```

---

## 3. Directory Layout & Module Boundaries

The implementation lives under `clipper/src/clipper/editor/`:

```text
clipper/src/clipper/editor/
├── __init__.py                # Package exports
├── models.py                  # Pydantic schemas (Projects, Chunks, Segments, EDL)
├── storage.py                 # SQLite metadata persistence & project store
├── ingestion.py               # FFprobe probe, audio extraction, chunk slicing
├── audio/
│   ├── __init__.py
│   ├── vad.py                 # Silero / energy-based VAD interval detector
│   ├── features.py            # RMS, pitch, spectral centroid, speech rate
│   └── transcriber.py         # faster-whisper wrapper with word timestamps
├── visual/
│   ├── __init__.py
│   ├── scene.py               # PySceneDetect boundary detector
│   └── motion.py              # Frame difference & optical motion analysis
├── intelligence/
│   ├── __init__.py
│   ├── context_builder.py     # Compact JSON context aggregator
│   ├── editorial_agent.py     # Groq/Gemini LPU editorial reviewer
│   └── validator.py           # Untrusted LLM output validation & sanitizer
├── timeline/
│   ├── __init__.py
│   ├── edl.py                 # Non-destructive Edit Decision List representation
│   ├── padding.py             # Context-aware safety padding enforcer
│   └── otio_export.py         # OpenTimelineIO interchange generator
└── render/
    ├── __init__.py
    ├── ffmpeg_builder.py      # Hardware-accelerated filtergraph constructor
    └── render_worker.py       # Async rendering pipeline with progress tracking
```

---

## 4. Multi-Modal Decision Scoring Formula

For any candidate interval $t$, the system computes an empirical confidence score:
$$S(t) = w_a \cdot A(t) + w_v \cdot V(t) + w_c \cdot C(t) + w_e \cdot E(t)$$

Where:
- $A(t)$: Voice activity probability & acoustic RMS energy
- $V(t)$: Scene transition flag & visual motion magnitude
- $C(t)$: Semantic relevance determined from Whisper dialogue context
- $E(t)$: Emotional / vocal intensity variation

### Triage Rules:
1. **Definite Dead Air** ($A(t) < 0.05 \land V(t) < 0.08$ for $> 2.5s$): Deterministically marked as `CUT` (no LLM tokens spent).
2. **Definite Speech** ($A(t) > 0.90 \land \text{Dialogue Active}$): Deterministically marked as `KEEP`.
3. **Borderline Intervals**: Dispatched to the AI Editorial Agent (Groq / Gemini) with surrounding conversational context.
