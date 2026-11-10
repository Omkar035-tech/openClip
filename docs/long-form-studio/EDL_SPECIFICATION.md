# Long-Form Studio — Edit Decision List (EDL) Specification

## 1. Overview
The **Edit Decision List (EDL)** is the central source of truth for the long-form editing workflow. It describes the transformation from raw video to the finalized edit without mutating the underlying media.

---

## 2. Segment Data Model

```json
{
  "version": "1.0",
  "project_id": "lf_proj_abc123",
  "source_media": {
    "path": "c:/Users/echo/Documents/dev_env/openClip/clipper/uploads/gameplay.mp4",
    "duration": 1800.0,
    "fps": 60.0,
    "width": 1920,
    "height": 1080
  },
  "summary": {
    "total_source_duration": 1800.0,
    "total_output_duration": 1140.2,
    "retained_ratio": 0.633,
    "total_cuts": 18,
    "total_transitions": 3
  },
  "segments": [
    {
      "id": "seg_001",
      "index": 0,
      "source_start": 0.0,
      "source_end": 42.5,
      "output_start": 0.0,
      "output_end": 42.5,
      "duration": 42.5,
      "action": "KEEP",
      "confidence": 0.98,
      "reason": "Opening intro and stream welcome",
      "tags": ["speech", "intro"],
      "transition_in": "fade_in_0.5s",
      "transition_out": "none",
      "user_overridden": false
    },
    {
      "id": "seg_002",
      "index": 1,
      "source_start": 42.5,
      "source_end": 85.0,
      "output_start": 42.5,
      "output_end": 42.5,
      "duration": 42.5,
      "action": "CUT",
      "confidence": 0.92,
      "reason": "Player bathroom break / dead screen",
      "tags": ["dead_air", "inactivity"],
      "transition_in": "none",
      "transition_out": "none",
      "user_overridden": false
    },
    {
      "id": "seg_003",
      "index": 2,
      "source_start": 85.0,
      "source_end": 210.0,
      "output_start": 42.5,
      "output_end": 167.5,
      "duration": 125.0,
      "action": "KEEP",
      "confidence": 0.95,
      "reason": "Intense horror encounter gameplay",
      "tags": ["reaction", "high_energy", "speech"],
      "transition_in": "crossfade_0.3s",
      "transition_out": "none",
      "user_overridden": false
    }
  ]
}
```

---

## 3. Strict Timeline Validation Invariants
1. **Monotonicity**: `source_start` must always be strictly less than `source_end`.
2. **Contiguity**: For segment $k$ and segment $k+1$, `segments[k].source_end == segments[k+1].source_start` without gaps or overlaps.
3. **Safety Padding Integrity**: Any vocal boundary must have safety margin padding $\Delta t \in [0.3s, 0.8s]$ unless it intersects a scene cut.
4. **Non-Destructive Recalculation**: Changing an action from `CUT` to `KEEP` or vice versa automatically shifts all subsequent `output_start` and `output_end` values deterministically in $O(N)$ time.
