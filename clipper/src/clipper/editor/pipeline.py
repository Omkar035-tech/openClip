import os
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from clipper.editor.models import AnalysisConfig, ProjectModel, RenderConfig, SegmentModel
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
from clipper.editor.auto_editor_engine import run_auto_editor_analysis, export_auto_editor_nle

# In-memory real-time pipeline event logs
project_logs: Dict[str, List[Dict[str, str]]] = {}

def append_project_log(project_id: str, message: str, level: str = "info"):
    if project_id not in project_logs:
        project_logs[project_id] = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = {"time": timestamp, "message": message, "level": level}
    project_logs[project_id].append(entry)
    print(f"[{timestamp}] [LongForm:{project_id[:8]}] [{level.upper()}] {message}")

def get_project_logs(project_id: str) -> List[Dict[str, str]]:
    return project_logs.get(project_id, [])

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
                
            append_project_log(project_id, f"Initializing analysis for '{proj.title}' (Duration: {proj.metadata.duration:.1f}s)")
            
            # --- AUTO-EDITOR HIGH SPEED ENGINE (DEFAULT) ---
            if getattr(config, "engine_mode", "auto_editor") == "auto_editor":
                append_project_log(project_id, f"⚡ Triggering Auto-Editor engine (Threshold: {config.threshold_percent}%, Margin: {config.margin_sec}s)...")
                update_project_status(project_id, "analyzing", 20.0, "Auto-Editor analyzing audio waveform...")
                
                raw_segments = run_auto_editor_analysis(
                    video_path=proj.source_video_path,
                    project_id=project_id,
                    threshold_percent=config.threshold_percent,
                    margin_sec=config.margin_sec,
                    log_callback=lambda msg: append_project_log(project_id, msg)
                )
                
                update_project_status(project_id, "analyzing", 85.0, "Parsing contiguous Edit Decision List...")
                segment_models = [SegmentModel(**s) for s in raw_segments]
                save_segments(project_id, segment_models)
                
                kept_count = sum(1 for s in segment_models if s.action == "KEEP")
                cut_count = sum(1 for s in segment_models if s.action == "CUT")
                kept_dur = sum(s.duration for s in segment_models if s.action == "KEEP")
                
                edl_data = {
                    "project_id": project_id,
                    "source_media_path": proj.source_video_path,
                    "original_duration": proj.metadata.duration,
                    "estimated_edited_duration": round(kept_dur, 2),
                    "cut_count": cut_count,
                    "kept_count": kept_count,
                    "segments": [s.model_dump() for s in segment_models]
                }
                push_history_state(project_id, "Auto-Editor Initial Analysis", edl_data)
                append_project_log(project_id, f"Analysis complete in record time! Kept: {kept_dur:.1f}s ({kept_count} clips), Cut: {proj.metadata.duration - kept_dur:.1f}s ({cut_count} cuts)", level="success")
                update_project_status(project_id, "review_ready", 100.0, "Analysis complete. Ready for Review & Playback.")
                return

            # --- HYBRID AI MULTI-MODAL PIPELINE (ALTERNATIVE) ---
            update_project_status(project_id, "analyzing", 5.0, "Extracting 16kHz audio stream...")
            
            cache_dir = Path("clipper/cache/long_form") / project_id
            cache_dir.mkdir(parents=True, exist_ok=True)
            wav_path = str(cache_dir / "audio_16k.wav")
            
            append_project_log(project_id, f"Extracting 16kHz mono PCM stream to: {wav_path}")
            extract_analysis_audio(proj.source_video_path, wav_path)
            append_project_log(project_id, "Audio extraction complete.")
            
            update_project_status(project_id, "analyzing", 25.0, "Running Voice Activity & Energy Detection...")
            append_project_log(project_id, f"Running VAD (Threshold: {config.silence_threshold_db} dB, Min Silence: {config.min_silence_duration}s)...")
            speech_intervals = detect_speech_intervals(wav_path, silence_threshold_db=config.silence_threshold_db, min_silence_duration=config.min_silence_duration)
            
            speech_count = sum(1 for s in speech_intervals if s["type"] == "speech")
            silence_count = sum(1 for s in speech_intervals if s["type"] == "silence")
            append_project_log(project_id, f"VAD detected {speech_count} speech blocks and {silence_count} silence pauses.")
            
            update_project_status(project_id, "analyzing", 45.0, "Detecting visual scene cut boundaries...")
            scenes = []
            if config.enable_scene_detection:
                append_project_log(project_id, "Scanning video with PySceneDetect ContentDetector...")
                scenes = detect_visual_scenes(proj.source_video_path)
                append_project_log(project_id, f"Scene analysis identified {len(scenes)} visual shot transitions.")
            else:
                append_project_log(project_id, "Scene detection skipped (disabled in config).")
                
            update_project_status(project_id, "analyzing", 65.0, "Transcribing dialogue with word timestamps...")
            append_project_log(project_id, "Running faster-whisper speech recognition...")
            transcript_phrases = transcribe_long_form_audio(proj.source_video_path, cache_dir=str(cache_dir))
            append_project_log(project_id, f"Transcription completed ({len(transcript_phrases)} dialogue phrases extracted).")
            
            update_project_status(project_id, "analyzing", 80.0, "AI Editorial Intelligence reviewing candidate pauses...")
            keep_candidates = [
                {"start": s["start"], "end": s["end"], "reason": "Dialogue speech", "tags": ["speech"]}
                for s in speech_intervals if s["type"] == "speech"]
            
            if config.enable_llm_editorial:
                append_project_log(project_id, f"Dispatching candidate pauses to {config.llm_provider.upper()} editorial agent...")
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
                retained_pauses = 0
                for d in decisions:
                    if d["action"] == "KEEP":
                        retained_pauses += 1
                        keep_candidates.append({
                            "start": d["start"],
                            "end": d["end"],
                            "reason": d.get("reason", "Editorial retention"),
                            "tags": d.get("tags", ["reaction", "editorial"])
                        })
                append_project_log(project_id, f"Editorial agent evaluated pauses: retained {retained_pauses} meaningful reaction/suspense blocks.")
            else:
                append_project_log(project_id, "LLM editorial review skipped (disabled in config).")
                        
            update_project_status(project_id, "analyzing", 92.0, "Constructing Non-Destructive Edit Decision List (EDL)...")
            append_project_log(project_id, f"Building contiguous EDL with +{config.safety_padding_sec}s speech safety padding...")
            edl = build_contiguous_edl(
                project_id=project_id,
                source_media_path=proj.source_video_path,
                total_duration=proj.metadata.duration,
                keep_intervals=keep_candidates,
                padding_sec=config.safety_padding_sec
            )
            
            save_segments(project_id, edl.segments)
            push_history_state(project_id, "Initial AI Analysis", edl.model_dump())
            append_project_log(project_id, f"EDL generated successfully! Retained: {edl.estimated_edited_duration:.1f}s, Cuts: {edl.cut_count}, Kept: {edl.kept_count}")
            append_project_log(project_id, "Project ready for interactive review.", level="success")
            update_project_status(project_id, "review_ready", 100.0, "Analysis complete. Ready for Review & Playback.")
            
        except Exception as e:
            err_msg = str(e)
            append_project_log(project_id, f"Analysis pipeline failed: {err_msg}", level="error")
            print(f"[LongFormWorker] Error during analysis of {project_id}: {err_msg}")
            update_project_status(project_id, "failed", 0.0, "Analysis failed", error_msg=err_msg)
            
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
                
            append_project_log(project_id, "Starting master video render pipeline...")
            update_project_status(project_id, "rendering", 15.0, "Constructing FFmpeg filtergraph...")
            segments = get_segments(project_id)
            
            kept_count = sum(1 for s in segments if s.action == "KEEP")
            append_project_log(project_id, f"Assembling filtergraph for {kept_count} kept clips with audio crossfades...")
            
            update_project_status(project_id, "rendering", 40.0, "Encoding master MP4 with hardware acceleration...")
            final_file = render_edl_video(
                source_video_path=proj.source_video_path,
                segments=segments,
                output_mp4_path=output_mp4_path,
                config=config
            )
            append_project_log(project_id, f"Render completed: {Path(final_file).name}", level="success")
            update_project_status(project_id, "completed", 100.0, f"Render finished: {Path(final_file).name}")
        except Exception as e:
            err_msg = str(e)
            append_project_log(project_id, f"Render failed: {err_msg}", level="error")
            print(f"[LongFormRenderWorker] Error during render of {project_id}: {err_msg}")
            update_project_status(project_id, "failed", 0.0, "Render failed", error_msg=err_msg)
            
    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
