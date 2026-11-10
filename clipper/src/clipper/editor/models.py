from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class VideoMetadata(BaseModel):
    duration: float
    width: int
    height: int
    fps: float
    video_codec: str
    audio_codec: Optional[str] = None
    bitrate: Optional[int] = None

class AnalysisConfig(BaseModel):
    safety_padding_sec: float = Field(0.40, ge=0.1, le=1.5, description="Padding added around speech edges")
    silence_threshold_db: float = Field(-35.0, description="Volume threshold for silence detection")
    min_silence_duration: float = Field(1.5, ge=0.5, description="Minimum silence duration to mark for cut")
    enable_scene_detection: bool = Field(True, description="Detect visual scene cuts via PySceneDetect")
    enable_motion_analysis: bool = Field(True, description="Analyze optical motion between frames")
    enable_llm_editorial: bool = Field(True, description="Use LLM to review borderline intervals")
    llm_provider: str = Field("groq", description="Primary editorial intelligence provider ('groq' or 'gemini')")
    llm_model: str = Field("llama-3.3-70b-versatile", description="Model ID")
    content_type: str = Field("general", description="Content profile ('gaming', 'podcast', 'tutorial', 'vlog', 'general')")

class SegmentModel(BaseModel):
    id: str
    index: int
    source_start: float
    source_end: float
    output_start: float = 0.0
    output_end: float = 0.0
    duration: float
    action: str = Field("KEEP", description="'KEEP', 'CUT', 'REVIEW', 'EMPHASIZE'")
    confidence: float = 1.0
    reason: str = ""
    tags: List[str] = []
    transition_in: str = "cut" # cut, crossfade, fade_in, dissolve
    transition_out: str = "none"
    user_overridden: bool = False

class EDLModel(BaseModel):
    project_id: str
    source_media_path: str
    original_duration: float
    estimated_edited_duration: float
    cut_count: int
    kept_count: int
    segments: List[SegmentModel]
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ProjectModel(BaseModel):
    id: str
    title: str
    source_video_path: str
    content_type: str = "general"
    metadata: VideoMetadata
    status: str = "created" # created, analyzing, review_ready, rendering, completed, failed
    progress_pct: float = 0.0
    current_stage: str = ""
    error_message: Optional[str] = None
    created_at: str
    updated_at: str

class RenderConfig(BaseModel):
    preset: str = Field("1080p_nvenc", description="Hardware or CPU encoding preset")
    include_transitions: bool = True
    audio_fade_in_sec: float = 0.3
    audio_fade_out_sec: float = 0.4
    output_filename: Optional[str] = None
