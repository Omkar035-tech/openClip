import os
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from clipper.editor.models import AnalysisConfig, ProjectModel, RenderConfig
from clipper.editor.storage import get_project, update_project_status, save_segments, push_history_state
from clipper.editor.ingestion import extract_analysis_audio
from clipper.editor.audio.vad import detect_speech_intervals
from clipper.editor.audio.transcriber import transcribe_long_form_audio
from clipper.editor.visual.scene import detect_visual_scenes
from clipper.editor.visual.motion import estimate_window_motion
from clipper.editor.intelligence.context_builder import build_editorial_context_payload
from clipper.editor.intelligence.editorial_agent import EditorialAgent
from clipper.editor.timeline.edl import build_contiguous_edl
from clipper.editor.render.ffmpeg_builder import render_edl_video

def run_project_analysis_async(project_id: str, config: AnalysisConfig):
    """
    Executes the multi-stage analysis pipeline in a background thread:
    1. Ingestion / Audio extraction
    2. VAD speech interval analysis
    3. faster-whisper transcription
    4. PySceneDetect visual boundary detection
    5. Context synthesis & AI Editorial evaluation
    6. Non-destructive EDL generation
    """
    def _worker():
        try:
            proj = get_project(project_id)
            if not proj:
                return
                
            update_project_status(project_id, "analyzing", 10.0, "Extracting 16kHz audio stream...")
            cache_dir = Path("clipper/cache/long_form") / project_id
            cache_dir.mkdir(parents=True, exist_ok=True)
            wav_path = str(cache_dir / "audio_16k.wav")
            extract_analysis_audio(proj.source_video_path, wav_path)
            
            update_project_status(project_id, "analyzing", 30.0, "Running Voice Activity & Energy Detection...")
            speech_intervals = detect_speech_intervals(wav_path, silence_threshold_db=config.silence_threshold_db)
            
            update_project_status(project_id, "analyzing", 45.0, "Detecting visual scene cut boundaries...")
            scenes = []
            if config.enable_scene_detection:
                scenes = detect_visual_scenes(proj.source_video_path)
                
            update_project_status(project_id, "analyzing", 60.0, "Transcribing dialogue with word timestamps...")
            transcript_phrases = transcribe_long_form_audio(wav_path)
            
            update_project_status(project_id, "analyzing", 75.0, "AI Editorial Intelligence reviewing candidate pauses...")
            # Speech intervals become KEEP candidates
            keep_candidates = [{"start": s["start"], "end": s["end"], "reason": "Dialogue speech", "tags": ["speech"]} for s in speech_intervals if s["type"] == "speech"]
            
            if config.enable_llm_editorial:
                silence_intervals = [s for s in speech_intervals if s["type"] == "silence"]
                context_payload = build_editorial_context_payload(
                    window_id="global_window",
                    start_sec=0.0,
                    end_sec=proj.metadata.duration,
                    speech_intervals=speech_intervals,
                    silence_intervals=silence_intervals,
                    transcript_phrases=transcript_phrases,
                    scenes=scenes,
                    content_type=config.content_type
                )
                agent = EditorialAgent(provider=config.llm_provider, model_id=config.llm_model)
                decisions = agent.evaluate_window(context_payload)
                for d in decisions:
                    if d["action"] == "KEEP":
                        keep_candidates.append({
                            "start": d["start"],
                            "end": d["end"],
                            "reason": d.get("reason", "Editorial retention"),
                            "tags": d.get("tags", ["reaction", "editorial"])
                        })
                        
            update_project_status(project_id, "analyzing", 90.0, "Constructing Non-Destructive Edit Decision List (EDL)...")
            edl = build_contiguous_edl(
                project_id=project_id,
                source_media_path=proj.source_video_path,
                total_duration=proj.metadata.duration,
                keep_intervals=keep_candidates,
                padding_sec=config.safety_padding_sec
            )
            
            save_segments(project_id, edl.segments)
            push_history_state(project_id, "Initial AI Analysis", edl.model_dump())
            update_project_status(project_id, "review_ready", 100.0, "Analysis complete. Ready for Review & Playback.")
            
        except Exception as e:
            print(f"[LongFormWorker] Error during analysis of {project_id}: {e}")
            update_project_status(project_id, "failed", 0.0, "Analysis failed", error_msg=str(e))
            
    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

def run_project_render_async(project_id: str, config: RenderConfig, output_mp4_path: str):
    """Executes FFmpeg rendering of all approved KEEP segments in background."""
    def _worker():
        try:
            from clipper.editor.storage import get_segments
            proj = get_project(project_id)
            if not proj:
                return
                
            update_project_status(project_id, "rendering", 15.0, "Constructing FFmpeg filtergraph...")
            segments = get_segments(project_id)
            
            update_project_status(project_id, "rendering", 40.0, "Encoding master MP4 with hardware acceleration...")
            final_file = render_edl_video(
                source_video_path=proj.source_video_path,
                segments=segments,
                output_mp4_path=output_mp4_path,
                config=config
            )
            update_project_status(project_id, "completed", 100.0, f"Render finished: {Path(final_file).name}")
        except Exception as e:
            print(f"[LongFormRenderWorker] Error during render of {project_id}: {e}")
            update_project_status(project_id, "failed", 0.0, "Render failed", error_msg=str(e))
            
    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
