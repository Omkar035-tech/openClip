import os
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Response
from fastapi.responses import FileResponse

from clipper.editor.models import AnalysisConfig, RenderConfig
from clipper.editor.storage import (
    list_projects, get_project, get_segments, save_segments,
    delete_project, push_history_state
)
from clipper.editor.ingestion import create_long_form_project, probe_video
from clipper.editor.pipeline import (
    run_project_analysis_async, run_project_render_async, get_project_logs
)
from clipper.editor.timeline.otio_export import export_edl_to_otio
from clipper.editor.timeline.edl import recalculate_output_timestamps, EDLModel

router = APIRouter(prefix="/api/long-form", tags=["Long-Form Studio"])

@router.get("/projects")
async def api_list_projects():
    return {"projects": list_projects()}

@router.post("/projects")
async def api_create_project(payload: Dict[str, Any]):
    video_path = payload.get("video_path")
    if not video_path or not Path(video_path).exists():
        raise HTTPException(status_code=400, detail="Invalid video_path provided")
        
    title = payload.get("title")
    content_type = payload.get("content_type", "general")
    try:
        project = create_long_form_project(video_path, title=title, content_type=content_type)
        return {"project": project.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")

@router.get("/projects/{project_id}")
async def api_get_project(project_id: str):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": proj.model_dump()}

@router.delete("/projects/{project_id}")
async def api_delete_project(project_id: str):
    success = delete_project(project_id)
    return {"success": success}

@router.post("/projects/{project_id}/analyze")
async def api_start_analysis(project_id: str, config: Optional[AnalysisConfig] = None):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    cfg = config or AnalysisConfig(content_type=proj.content_type)
    run_project_analysis_async(project_id, cfg)
    return {
        "status": "analyzing",
        "project_id": project_id,
        "message": "Long-form multimodal analysis started in background worker."
    }

@router.get("/projects/{project_id}/status")
async def api_get_project_status(project_id: str):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "project_id": proj.id,
        "status": proj.status,
        "progress_pct": proj.progress_pct,
        "current_stage": proj.current_stage,
        "error_message": proj.error_message,
        "updated_at": proj.updated_at
    }

@router.get("/projects/{project_id}/logs")
async def api_get_project_logs(project_id: str):
    return {
        "project_id": project_id,
        "logs": get_project_logs(project_id)
    }

@router.get("/projects/{project_id}/timeline")
async def api_get_timeline(project_id: str):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    segments = get_segments(project_id)
    cut_count = sum(1 for s in segments if s.action == "CUT")
    kept_count = sum(1 for s in segments if s.action == "KEEP")
    edited_duration = sum(s.duration for s in segments if s.action == "KEEP")
    
    return {
        "project_id": project_id,
        "original_duration": proj.metadata.duration,
        "estimated_edited_duration": round(edited_duration, 2),
        "cut_count": cut_count,
        "kept_count": kept_count,
        "segments": [s.model_dump() for s in segments]
    }

@router.post("/projects/{project_id}/segment/{segment_id}/override")
async def api_override_segment(project_id: str, segment_id: str, payload: Dict[str, Any]):
    action = payload.get("action", "KEEP").upper()
    reason = payload.get("reason", "Manual user override")
    
    segments = get_segments(project_id)
    found = False
    for s in segments:
        if s.id == segment_id:
            s.action = action
            s.reason = reason
            s.user_overridden = True
            found = True
            break
            
    if not found:
        raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")
        
    recalculate_output_timestamps(segments)
    save_segments(project_id, segments)
    push_history_state(project_id, f"Override segment {segment_id} to {action}", [s.model_dump() for s in segments])
    
    return {
        "success": True,
        "segment_id": segment_id,
        "new_action": action,
        "message": f"Segment updated to {action}. Output timeline recalculated."
    }

@router.post("/projects/{project_id}/render")
async def api_render_master(project_id: str, config: Optional[RenderConfig] = None):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    cfg = config or RenderConfig()
    out_dir = Path("clipper/out/long_form")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    filename = cfg.output_filename or f"{Path(proj.source_video_path).stem}_edited_master.mp4"
    dest_mp4 = out_dir / filename
    
    run_project_render_async(project_id, cfg, str(dest_mp4.resolve()))
    return {
        "status": "rendering",
        "output_path": str(dest_mp4.resolve()),
        "message": "Master video render dispatched with hardware acceleration."
    }

@router.get("/projects/{project_id}/export/otio")
async def api_export_otio(project_id: str):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    segments = get_segments(project_id)
    if not segments:
        raise HTTPException(status_code=400, detail="No timeline segments exist to export")
        
    edl = EDLModel(
        project_id=project_id,
        source_media_path=proj.source_video_path,
        original_duration=proj.metadata.duration,
        estimated_edited_duration=sum(s.duration for s in segments if s.action == "KEEP"),
        cut_count=sum(1 for s in segments if s.action == "CUT"),
        kept_count=sum(1 for s in segments if s.action == "KEEP"),
        segments=segments
    )
    
    out_otio = Path("clipper/out/long_form") / f"{project_id}_timeline.otio"
    file_path = export_edl_to_otio(edl, str(out_otio.resolve()))
    return FileResponse(file_path, media_type="application/octet-stream", filename=Path(file_path).name)
