import os
import subprocess
from pathlib import Path
from clipper.editor.models import VideoMetadata, AnalysisConfig, SegmentModel, EDLModel, RenderConfig
from clipper.editor.timeline.edl import build_contiguous_edl
from clipper.editor.render.ffmpeg_builder import render_edl_video

def generate_synthetic_test_video(out_path: str, duration_sec: int = 15):
    """
    Generates a 15-second synthetic MP4:
    0-5s: Blue background with 440Hz test sine tone (Speech proxy)
    5-10s: Black background with silence (Dead air proxy)
    10-15s: Green background with 880Hz test sine tone (Speech proxy)
    """
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=blue:s=640x360:d=5",
        "-f", "lavfi", "-i", f"sine=f=440:d=5",
        "-f", "lavfi", "-i", f"color=c=black:s=640x360:d=5",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono:d=5",
        "-f", "lavfi", "-i", f"color=c=green:s=640x360:d=5",
        "-f", "lavfi", "-i", f"sine=f=880:d=5",
        "-filter_complex",
        "[0:v][1:a][2:v][3:a][4:v][5:a]concat=n=3:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-c:a", "aac",
        str(out_p.resolve())
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    return str(out_p.resolve())

def test_full_pipeline_render():
    test_video = "clipper/cache/test_synthetic_source.mp4"
    rendered_output = "clipper/cache/test_synthetic_master.mp4"
    
    print("1. Generating synthetic 15-second test video...")
    generate_synthetic_test_video(test_video, duration_sec=15)
    assert Path(test_video).exists()
    
    print("2. Constructing EDL with middle 5s cut...")
    # Kept: 0-5s and 10-15s, Middle 5-10s is CUT
    keep_moments = [
        {"start": 0.0, "end": 5.0, "reason": "Blue intro speech"},
        {"start": 10.0, "end": 15.0, "reason": "Green outro speech"}
    ]
    edl = build_contiguous_edl("test_synth_proj", test_video, total_duration=15.0, keep_intervals=keep_moments, padding_sec=0.1)
    
    assert edl.cut_count == 1
    assert edl.kept_count == 2
    
    print("3. Executing FFmpeg Render Worker...")
    cfg = RenderConfig(preset="cpu", audio_fade_in_sec=0.2, audio_fade_out_sec=0.2)
    rendered_path = render_edl_video(test_video, edl.segments, rendered_output, cfg)
    
    assert Path(rendered_path).exists()
    size = Path(rendered_path).stat().st_size
    assert size > 10000, f"Rendered file too small: {size} bytes"
    print(f"✓ Full Render Pipeline successfully produced master MP4 ({size} bytes)")
    
    # Clean up test artifacts
    if Path(test_video).exists(): Path(test_video).unlink()
    if Path(rendered_output).exists(): Path(rendered_output).unlink()

if __name__ == "__main__":
    test_full_pipeline_render()
    print("ALL LONG-FORM INTEGRATION RENDER TESTS PASSED!")
