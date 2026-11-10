# Long-Form Studio — Database & State Design

## Storage Strategy: SQLite Database
The long-form editing subsystem uses a dedicated SQLite database located at:
`clipper/long_form_editor.db`

This ensures complete isolation from the legacy manifest JSON files used in Shorts Studio while enabling fast queries, transaction safety, and full undo/redo state tracking.

---

## Schema Definitions

### 1. `projects` Table
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | TEXT | PRIMARY KEY | Unique UUID or timestamp slug (e.g. `proj_20261110_abc`) |
| `title` | TEXT | NOT NULL | User-assigned or derived video title |
| `source_video_path` | TEXT | NOT NULL | Absolute path to raw uploaded video |
| `content_type` | TEXT | DEFAULT 'general' | `gaming`, `podcast`, `tutorial`, `vlog`, `general` |
| `duration` | REAL | NOT NULL | Original video duration in seconds |
| `width` | INTEGER | NOT NULL | Video resolution width (e.g. 1920) |
| `height` | INTEGER | NOT NULL | Video resolution height (e.g. 1080) |
| `fps` | REAL | NOT NULL | Video frame rate (e.g. 30.0, 60.0) |
| `status` | TEXT | NOT NULL | `created`, `analyzing`, `review_ready`, `rendering`, `completed`, `failed` |
| `progress_pct` | REAL | DEFAULT 0.0 | Overall analysis/render progress (0.0 to 100.0) |
| `current_stage` | TEXT | DEFAULT '' | Description of active stage (e.g. 'Extracting audio') |
| `created_at` | TEXT | NOT NULL | ISO 8601 timestamp |
| `updated_at` | TEXT | NOT NULL | ISO 8601 timestamp |

### 2. `timeline_segments` Table
Represents individual cut/keep intervals on the Edit Decision List:
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | TEXT | PRIMARY KEY | Segment UUID |
| `project_id` | TEXT | NOT NULL (FK) | Reference to `projects.id` |
| `index_order` | INTEGER | NOT NULL | Sequential segment ordering (0, 1, 2...) |
| `source_start` | REAL | NOT NULL | Start timestamp in original footage (seconds) |
| `source_end` | REAL | NOT NULL | End timestamp in original footage (seconds) |
| `output_start` | REAL | DEFAULT 0.0 | Calculated start in edited timeline |
| `output_end` | REAL | DEFAULT 0.0 | Calculated end in edited timeline |
| `action` | TEXT | NOT NULL | `KEEP`, `CUT`, `REVIEW`, `EMPHASIZE` |
| `confidence` | REAL | DEFAULT 1.0 | Score between 0.0 and 1.0 |
| `reason` | TEXT | DEFAULT '' | Editorial rationale (e.g. "Silence", "Suspense reaction") |
| `tags` | TEXT | DEFAULT '[]' | JSON list of tags (e.g. `["speech", "reaction"]`) |
| `transition` | TEXT | DEFAULT 'cut' | `cut`, `crossfade`, `dissolve`, `fade_in`, `fade_out` |
| `user_overridden`| INTEGER | DEFAULT 0 | 1 if human modified AI verdict, 0 if original AI |

### 3. `history_states` Table (Undo / Redo Stack)
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Monotonic state revision |
| `project_id` | TEXT | NOT NULL (FK) | Reference to `projects.id` |
| `action_description` | TEXT | NOT NULL | e.g. "Restored segment 120s-145s" |
| `edl_snapshot_json` | TEXT | NOT NULL | Full JSON serialization of segments |
| `created_at` | TEXT | NOT NULL | ISO 8601 timestamp |

### 4. `render_jobs` Table
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | TEXT | PRIMARY KEY | Render task identifier |
| `project_id` | TEXT | NOT NULL (FK) | Reference to `projects.id` |
| `output_video_path`| TEXT | NOT NULL | Absolute path to final exported MP4 |
| `export_preset` | TEXT | DEFAULT '1080p_nvenc'| Selected encoder & bitrate preset |
| `status` | TEXT | NOT NULL | `queued`, `rendering`, `completed`, `failed` |
| `progress_pct` | REAL | DEFAULT 0.0 | Rendering progress percentage |
| `final_duration` | REAL | DEFAULT 0.0 | Duration of the finalized video |
| `error_log` | TEXT | DEFAULT '' | FFmpeg stderr diagnostics if failed |
| `created_at` | TEXT | NOT NULL | ISO 8601 timestamp |
