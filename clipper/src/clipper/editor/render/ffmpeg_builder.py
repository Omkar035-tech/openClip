import subprocess
import tempfile
import os
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
    Renders approved KEEP segments into a polished master MP4/MKV.
    For small cuts (<= 80 segments), executes in a single filtergraph pass.
    For large long-form videos (> 80 segments), processes safely in batches
    and concatenates seamlessly to prevent Windows command line length overflow (WinError 206).
    """
    out_p = Path(output_mp4_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    kept_segments = [s for s in segments if s.action == "KEEP"]
    if not kept_segments:
        raise ValueError("Cannot render video: No segments are marked as 'KEEP'!")
        
    hw = detect_hardware()
    vcodec = "h264_nvenc" if hw.get("cuda") else "libx264"
    preset_arg = ["-preset", "p4", "-tune", "hq"] if vcodec == "h264_nvenc" else ["-preset", "fast", "-crf", "20"]
    
    fade_in = config.audio_fade_in_sec
    fade_out = config.audio_fade_out_sec
    total_duration = sum(s.duration for s in kept_segments)

    BATCH_SIZE = 80
    if len(kept_segments) <= BATCH_SIZE:
        filter_lines = []
        concat_inputs = []
        for idx, seg in enumerate(kept_segments):
            v_label = f"v{idx}"
            a_label = f"a{idx}"
            filter_lines.append(f"[0:v]trim=start={seg.source_start:.3f}:end={seg.source_end:.3f},setpts=PTS-STARTPTS[{v_label}];")
            filter_lines.append(f"[0:a]atrim=start={seg.source_start:.3f}:end={seg.source_end:.3f},asetpts=PTS-STARTPTS[{a_label}];")
            concat_inputs.append(f"[{v_label}][{a_label}]")
            
        num_segments = len(kept_segments)
        concat_str = "".join(concat_inputs) + f"concat=n={num_segments}:v=1:a=1[outv_raw][outa_raw];"
        filter_lines.append(concat_str)
        
        fade_out_start = max(0.0, total_duration - fade_out)
        v_filter = f"[outv_raw]fade=t=in:st=0:d={fade_in},fade=t=out:st={fade_out_start:.2f}:d={fade_out}[outv]"
        a_filter = f"[outa_raw]afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_out_start:.2f}:d={fade_out}[outa]"
        filter_lines.append(f"{v_filter};{a_filter}")
        full_filtergraph = "".join(filter_lines)
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(Path(source_video_path).resolve()),
            "-filter_complex", full_filtergraph,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", vcodec
        ] + preset_arg + [
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(out_p.resolve())
        ]
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if process.returncode != 0:
            if vcodec == "h264_nvenc":
                print("[Render] NVENC returned non-zero, falling back to CPU libx264...")
                cmd[cmd.index("-c:v") + 1] = "libx264"
                cmd[cmd.index("-preset") + 1] = "fast"
                if "-tune" in cmd: cmd.remove("-tune")
                if "hq" in cmd: cmd.remove("hq")
                process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            else:
                raise RuntimeError(f"FFmpeg render failed:\n{process.stderr[-800:]}")
        return str(out_p.resolve())

    # Large segment lists (> 80 cuts) - Render in batches and stitch cleanly
    # to avoid Windows command line length overflow (WinError 206)
    temp_dir = Path("clipper/cache") / f"render_batches_{os.getpid()}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_parts = []
    
    try:
        batches = [kept_segments[i:i + BATCH_SIZE] for i in range(0, len(kept_segments), BATCH_SIZE)]
        for b_idx, batch in enumerate(batches):
            f_lines = []
            c_inputs = []
            for idx, seg in enumerate(batch):
                v_label = f"v{idx}"
                a_label = f"a{idx}"
                f_lines.append(f"[0:v]trim=start={seg.source_start:.3f}:end={seg.source_end:.3f},setpts=PTS-STARTPTS[{v_label}];")
                f_lines.append(f"[0:a]atrim=start={seg.source_start:.3f}:end={seg.source_end:.3f},asetpts=PTS-STARTPTS[{a_label}];")
                c_inputs.append(f"[{v_label}][{a_label}]")
            f_lines.append("".join(c_inputs) + f"concat=n={len(batch)}:v=1:a=1[outv][outa]")
            part_path = temp_dir / f"batch_part_{b_idx}.mp4"
            
            cmd_batch = [
                "ffmpeg", "-y",
                "-i", str(Path(source_video_path).resolve()),
                "-filter_complex", "".join(f_lines),
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", vcodec
            ] + preset_arg + [
                "-c:a", "aac",
                str(part_path.resolve())
            ]
            
            p_b = subprocess.run(cmd_batch, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if p_b.returncode != 0:
                if vcodec == "h264_nvenc":
                    cmd_batch[cmd_batch.index("-c:v") + 1] = "libx264"
                    cmd_batch[cmd_batch.index("-preset") + 1] = "fast"
                    if "-tune" in cmd_batch: cmd_batch.remove("-tune")
                    if "hq" in cmd_batch: cmd_batch.remove("hq")
                    p_b = subprocess.run(cmd_batch, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
                else:
                    raise RuntimeError(f"FFmpeg batch {b_idx} render failed:\n{p_b.stderr[-800:]}")
            temp_parts.append(part_path)
            
        # Concat demuxer script
        concat_script_file = temp_dir / "concat_list.txt"
        with open(concat_script_file, "w", encoding="utf-8") as f:
            for tp in temp_parts:
                f.write(f"file '{tp.resolve().as_posix()}'\n")
                
        # Final stitch
        cmd_final = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_script_file.resolve()),
            "-c", "copy",
            str(out_p.resolve())
        ]
        p_final = subprocess.run(cmd_final, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if p_final.returncode != 0:
            raise RuntimeError(f"Final concat stitch failed:\n{p_final.stderr[-800:]}")
            
        return str(out_p.resolve())
    finally:
        # Cleanup temporary files
        for p in temp_parts:
            if p.exists():
                try: p.unlink()
                except Exception: pass
        if (temp_dir / "concat_list.txt").exists():
            try: (temp_dir / "concat_list.txt").unlink()
            except Exception: pass
        try:
            temp_dir.rmdir()
        except Exception:
            pass
