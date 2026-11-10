import sqlite3
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from clipper.editor.models import ProjectModel, VideoMetadata, SegmentModel, EDLModel

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "long_form_editor.db"

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Projects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lf_projects (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        source_video_path TEXT NOT NULL,
        content_type TEXT DEFAULT 'general',
        duration REAL NOT NULL,
        width INTEGER NOT NULL,
        height INTEGER NOT NULL,
        fps REAL NOT NULL,
        video_codec TEXT NOT NULL,
        audio_codec TEXT,
        bitrate INTEGER,
        status TEXT NOT NULL,
        progress_pct REAL DEFAULT 0.0,
        current_stage TEXT DEFAULT '',
        error_message TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # Timeline Segments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lf_segments (
        id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        segment_index INTEGER NOT NULL,
        source_start REAL NOT NULL,
        source_end REAL NOT NULL,
        output_start REAL DEFAULT 0.0,
        output_end REAL DEFAULT 0.0,
        duration REAL NOT NULL,
        action TEXT NOT NULL,
        confidence REAL DEFAULT 1.0,
        reason TEXT DEFAULT '',
        tags TEXT DEFAULT '[]',
        transition_in TEXT DEFAULT 'cut',
        transition_out TEXT DEFAULT 'none',
        user_overridden INTEGER DEFAULT 0,
        PRIMARY KEY (project_id, id),
        FOREIGN KEY(project_id) REFERENCES lf_projects(id) ON DELETE CASCADE
    );
    """)

    # Timeline History (Undo / Redo snapshots)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lf_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        action_description TEXT NOT NULL,
        edl_snapshot_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES lf_projects(id) ON DELETE CASCADE
    );
    """)

    # Render Jobs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lf_render_jobs (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        output_video_path TEXT NOT NULL,
        export_preset TEXT NOT NULL,
        status TEXT NOT NULL,
        progress_pct REAL DEFAULT 0.0,
        final_duration REAL DEFAULT 0.0,
        error_log TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES lf_projects(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

def save_project(proj: ProjectModel) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
    INSERT INTO lf_projects (
        id, title, source_video_path, content_type, duration, width, height, fps,
        video_codec, audio_codec, bitrate, status, progress_pct, current_stage,
        error_message, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        title = excluded.title,
        status = excluded.status,
        progress_pct = excluded.progress_pct,
        current_stage = excluded.current_stage,
        error_message = excluded.error_message,
        updated_at = excluded.updated_at;
    """, (
        proj.id, proj.title, proj.source_video_path, proj.content_type,
        proj.metadata.duration, proj.metadata.width, proj.metadata.height, proj.metadata.fps,
        proj.metadata.video_codec, proj.metadata.audio_codec, proj.metadata.bitrate,
        proj.status, proj.progress_pct, proj.current_stage, proj.error_message,
        proj.created_at, now
    ))
    conn.commit()
    conn.close()

def update_project_status(project_id: str, status: str, progress_pct: float, current_stage: str, error_msg: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
    UPDATE lf_projects SET
        status = ?,
        progress_pct = ?,
        current_stage = ?,
        error_message = ?,
        updated_at = ?
    WHERE id = ?
    """, (status, progress_pct, current_stage, error_msg, now, project_id))
    conn.commit()
    conn.close()

def get_project(project_id: str) -> Optional[ProjectModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lf_projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return ProjectModel(
        id=row["id"],
        title=row["title"],
        source_video_path=row["source_video_path"],
        content_type=row["content_type"],
        metadata=VideoMetadata(
            duration=row["duration"],
            width=row["width"],
            height=row["height"],
            fps=row["fps"],
            video_codec=row["video_codec"],
            audio_codec=row["audio_codec"],
            bitrate=row["bitrate"]
        ),
        status=row["status"],
        progress_pct=row["progress_pct"],
        current_stage=row["current_stage"],
        error_message=row["error_message"],
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )

def list_projects() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lf_projects ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "title": r["title"],
            "source_video_path": r["source_video_path"],
            "content_type": r["content_type"],
            "duration": r["duration"],
            "width": r["width"],
            "height": r["height"],
            "fps": r["fps"],
            "status": r["status"],
            "progress_pct": r["progress_pct"],
            "current_stage": r["current_stage"],
            "error_message": r["error_message"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"]
        })
    return results

def save_segments(project_id: str, segments: List[SegmentModel]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Replace existing segments atomically
    cursor.execute("DELETE FROM lf_segments WHERE project_id = ?", (project_id,))
    for s in segments:
        cursor.execute("""
        INSERT INTO lf_segments (
            id, project_id, segment_index, source_start, source_end, output_start, output_end,
            duration, action, confidence, reason, tags, transition_in, transition_out, user_overridden
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s.id, project_id, s.index, s.source_start, s.source_end, s.output_start, s.output_end,
            s.duration, s.action, s.confidence, s.reason, json.dumps(s.tags),
            s.transition_in, s.transition_out, 1 if s.user_overridden else 0
        ))
    conn.commit()
    conn.close()

def get_segments(project_id: str) -> List[SegmentModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lf_segments WHERE project_id = ? ORDER BY segment_index ASC", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    
    segments = []
    for r in rows:
        try:
            tags = json.loads(r["tags"])
        except Exception:
            tags = []
        segments.append(SegmentModel(
            id=r["id"],
            index=r["segment_index"],
            source_start=r["source_start"],
            source_end=r["source_end"],
            output_start=r["output_start"],
            output_end=r["output_end"],
            duration=r["duration"],
            action=r["action"],
            confidence=r["confidence"],
            reason=r["reason"],
            tags=tags,
            transition_in=r["transition_in"],
            transition_out=r["transition_out"],
            user_overridden=bool(r["user_overridden"])
        ))
    return segments

def push_history_state(project_id: str, description: str, edl_data: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
    INSERT INTO lf_history (project_id, action_description, edl_snapshot_json, created_at)
    VALUES (?, ?, ?, ?)
    """, (project_id, description, json.dumps(edl_data), now))
    conn.commit()
    conn.close()

def delete_project(project_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lf_segments WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM lf_history WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM lf_render_jobs WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM lf_projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return True
