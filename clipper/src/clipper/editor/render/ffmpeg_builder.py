import subprocess
from pathlib import Path
from typing import List
from clipper.editor.models import SegmentModel, RenderConfig
from clipper.hardware import detect_hardware

def render_edl_video(
    source_video_path: str,
    segments: List[SegmentModel],
    output_mp4_path: str,
    config: RenderConfig
) -> str:
    """
    Renders approved KEEP segments into a polished MP4 using hardware-accelerated
    FFmpeg concat and filtergraph processing.
    """
    out_p = Path(output_mp4_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    kept_segments = [s for s in segments if s.action == "KEEP"]
    if not kept_segments:
        raise ValueError("Cannot render video: No segments are marked as 'KEEP'!")
        
    hw = detect_hardware()
    # Select encoder
    vcodec = "h264_nvenc" if hw.get("cuda") else "libx264"
    preset_arg = ["-preset", "p4", "-tune", "hq"] if vcodec == "h264_nvenc" else ["-preset", "fast", "-crf", "20"]
    
    # 1. Build FFmpeg filter_complex inputs
    # For robust rendering across hours of content, generate an input filtergraph
    filter_parts = []
    concat_inputs = []
    
    for idx, seg in enumerate(kept_segments):
        v_label = f"v{idx}"
        a_label = f"a{idx}"
        filter_parts.append(f"[0:v]trim=start={seg.source_start:.3f}:end={seg.source_end:.3f},setpts=PTS-STARTPTS[{v_label}];")
        filter_parts.append(f"[0:a]atrim=start={seg.source_start:.3f}:end={seg.source_end:.3f},asetpts=PTS-STARTPTS[{a_label}];")
        concat_inputs.append(f"[{v_label}][{a_label}]")
        
    num_segments = len(kept_segments)
    concat_str = "".join(concat_inputs) + f"concat=n={num_segments}:v=1:a=1[outv_raw][outa_raw];"
    filter_parts.append(concat_str)
    
    # Audio fades & final master normalization
    fade_in = config.audio_fade_in_sec
    fade_out = config.audio_fade_out_sec
    total_duration = sum(s.duration for s in kept_segments)
    fade_out_start = max(0.0, total_duration - fade_out)
    
    filter_parts.append(f"[outv_raw]fade=t=in:st=0:d={fade_in},fade=t=out:st={fade_out_start:.2f}:d={fade_out}[outv];")
    filter_parts.append(f"[outa_raw]afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_out_start:.2f}:d={fade_out}[outa]")
    
    full_filter = "".join(filter_parts)
    
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(Path(source_video_path).resolve()),
        "-filter_complex", full_filter,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", vcodec
    ] + preset_arg + [
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(out_p.resolve())
    ]
    
    # Execute render
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        # Fallback to pure libx264 if NVENC had session limits or profile mismatch
        if vcodec == "h264_nvenc":
            print("[Render] NVENC returned non-zero, falling back to CPU libx264...")
            cmd[cmd.index("-c:v") + 1] = "libx264"
            cmd[cmd.index("-preset") + 1] = "fast"
            cmd.remove("-tune")
            cmd.remove("hq")
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        else:
            raise RuntimeError(f"FFmpeg render failed:\n{process.stderr[-800:]}")
            
    return str(out_p.resolve())
