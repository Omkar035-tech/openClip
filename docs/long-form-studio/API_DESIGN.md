# Long-Form Studio — REST API Specification

Base URL: `http://localhost:8080/api/long-form`

---

## 1. Project Management

### `POST /projects`
Creates a new long-form editing project from an uploaded or local video.
- **Request Body**:
  ```json
  {
    "title": "Episode 42: Building AI",
    "video_path": "c:/Users/echo/Documents/dev_env/openClip/clipper/uploads/source.mp4",
    "content_type": "podcast"
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "project_id": "lf_proj_98a72b",
    "title": "Episode 42: Building AI",
    "duration": 7200.5,
    "width": 1920,
    "height": 1080,
    "status": "created"
  }
  ```

### `GET /projects`
Lists all long-form projects, durations, and review readiness.

### `GET /projects/{id}`
Returns full project metadata and pipeline status.

---

## 2. Ingestion & Analysis Pipeline

### `POST /projects/{id}/analyze`
Triggers the multi-modal analysis pipeline in background worker threads.
- **Request Body**:
  ```json
  {
    "safety_padding_sec": 0.45,
    "silence_threshold_db": -35.0,
    "enable_scene_detection": true,
    "enable_llm_editorial": true,
    "llm_provider": "groq",
    "llm_model": "llama-3.3-70b-versatile"
  }
  ```
- **Response**: `202 Accepted`
  ```json
  {
    "status": "analyzing",
    "job_id": "analysis_job_123",
    "message": "Analysis pipeline dispatched in background."
  }
  ```

### `GET /projects/{id}/status`
Real-time progress endpoint queried by the frontend.
- **Response**:
  ```json
  {
    "project_id": "lf_proj_98a72b",
    "status": "analyzing",
    "progress_pct": 68.5,
    "current_stage": "AI Editorial Triage (Chunk 14/20)",
    "stages": {
      "audio_extraction": "completed",
      "vad_detection": "completed",
      "scene_detection": "completed",
      "whisper_transcription": "completed",
      "llm_editorial": "in_progress",
      "edl_generation": "pending"
    }
  }
  ```

---

## 3. Timeline & Non-Destructive Review

### `GET /projects/{id}/timeline`
Returns the current Edit Decision List (kept vs. cut segments).
- **Response**:
  ```json
  {
    "project_id": "lf_proj_98a72b",
    "original_duration": 7200.0,
    "estimated_edited_duration": 4320.5,
    "cut_count": 34,
    "kept_count": 35,
    "segments": [
      {
        "id": "seg_01",
        "index": 0,
        "source_start": 0.0,
        "source_end": 45.2,
        "action": "KEEP",
        "reason": "Intro hook dialogue",
        "tags": ["speech", "hook"]
      },
      {
        "id": "seg_02",
        "index": 1,
        "source_start": 45.2,
        "source_end": 78.0,
        "action": "CUT",
        "reason": "Extended silence / mic check",
        "tags": ["dead_air"]
      }
    ]
  }
  ```

### `POST /projects/{id}/segment/{segment_id}/override`
Allows the user to flip an action (e.g. from `CUT` to `KEEP` or vice-versa) with immediate recalculation.
- **Request Body**:
  ```json
  {
    "action": "KEEP",
    "reason": "User manual restore"
  }
  ```

### `POST /projects/{id}/undo` & `POST /projects/{id}/redo`
Restores previous EDL timeline revisions from the SQLite history table.

---

## 4. Rendering & Export

### `POST /projects/{id}/render`
Kicks off the FFmpeg filtergraph render worker.
- **Request Body**:
  ```json
  {
    "preset": "1080p_nvenc",
    "transitions": true,
    "audio_fade_in_sec": 0.5,
    "audio_fade_out_sec": 0.5
  }
  ```

### `GET /projects/{id}/export/otio`
Generates and downloads an OpenTimelineIO (`.otio`) file for DaVinci Resolve or Premiere Pro.
