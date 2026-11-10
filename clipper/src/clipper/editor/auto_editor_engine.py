import os
import sys
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional

def _get_auto_editor_cmd() -> str:
    """Finds auto-editor binary in current venv or PATH."""
    venv_ae = Path(sys.executable).parent / "auto-editor.exe"
    if venv_ae.exists():
        return str(venv_ae.resolve())
    venv_ae_unix = Path(sys.executable).parent / "auto-editor"
    if venv_ae_unix.exists():
        return str(venv_ae_unix.resolve())
    # Try adjacent to current working directory
    local_ae = Path("clipper/.venv/Scripts/auto-editor.exe").resolve()
    if local_ae.exists():
        return str(local_ae)
    return "auto-editor"

def run_auto_editor_analysis(
    video_path: str,
    project_id: str = "proj",
    threshold_percent: float = 4.0,
    margin_sec: float = 0.2,
    log_callback: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Executes auto-editor binary on the video file to produce high-speed silence/speech cuts
    in ~10-20 seconds. Exports an intermediate Premiere XML and parses it into
    contiguous SegmentModel dictionaries.
    """
    video_p = Path(video_path).resolve()
    if not video_p.exists():
        raise FileNotFoundError(f"Source video not found: {video_p}")
        
    cache_dir = Path("clipper/cache/auto_editor")
    cache_dir.mkdir(parents=True, exist_ok=True)
    xml_output = cache_dir / f"ae_{os.getpid()}_{video_p.stem}.xml"
    
    ae_cmd = _get_auto_editor_cmd()
    
    cmd = [
        ae_cmd,
        str(video_p),
        "--edit", f"audio:threshold={threshold_percent}%",
        "--margin", f"{margin_sec}s",
        "--export", "premiere",
        "-o", str(xml_output.resolve())
    ]
    
    if log_callback:
        log_callback(f"Running Auto-Editor engine: {' '.join(cmd)}")
        
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise RuntimeError(f"Auto-Editor engine execution failed:\n{process.stderr}")
        
    if not xml_output.exists():
        raise FileNotFoundError(f"Auto-Editor did not create expected XML output at {xml_output}")
        
    try:
        # Parse XML into contiguous segments
        tree = ET.parse(xml_output)
        root = tree.getroot()
        tb_elem = root.find(".//sequence/rate/timebase")
        timebase = float(tb_elem.text) if tb_elem is not None else 30.0
        
        clips = root.findall(".//media/video/track/clipitem")
        keep_ranges = []
        for c in clips:
            in_val = c.find("in")
            out_val = c.find("out")
            if in_val is not None and out_val is not None:
                cin = round(float(in_val.text) / timebase, 3)
                cout = round(float(out_val.text) / timebase, 3)
                if cout > cin:
                    keep_ranges.append((cin, cout))
                    
        # Total duration probe via ffprobe
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_p)
        ]
        p_res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        total_dur = float(p_res.stdout.strip()) if p_res.returncode == 0 else (keep_ranges[-1][1] if keep_ranges else 0.0)
        
        segments = []
        curr = 0.0
        seg_idx = 0
        
        for cin, cout in keep_ranges:
            if cin > curr + 0.02:
                # Silence / dead air gap
                segments.append({
                    "id": f"{project_id}_seg_{seg_idx}",
                    "index": seg_idx,
                    "source_start": round(curr, 3),
                    "source_end": round(cin, 3),
                    "duration": round(cin - curr, 3),
                    "action": "CUT",
                    "confidence": 0.95,
                    "reason": f"Dead air / silence below {threshold_percent}%"
                })
                seg_idx += 1
                
            # Kept vocal / content slice
            segments.append({
                "id": f"{project_id}_seg_{seg_idx}",
                "index": seg_idx,
                "source_start": round(cin, 3),
                "source_end": round(cout, 3),
                "duration": round(cout - cin, 3),
                "action": "KEEP",
                "confidence": 0.98,
                "reason": "Active speech / audio activity"
            })
            seg_idx += 1
            curr = cout
            
        if curr < total_dur - 0.05:
            segments.append({
                "id": f"{project_id}_seg_{seg_idx}",
                "index": seg_idx,
                "source_start": round(curr, 3),
                "source_end": round(total_dur, 3),
                "duration": round(total_dur - curr, 3),
                "action": "CUT",
                "confidence": 0.95,
                "reason": "Trailing dead air"
            })
            
        if log_callback:
            kept_count = sum(1 for s in segments if s["action"] == "KEEP")
            cut_count = sum(1 for s in segments if s["action"] == "CUT")
            log_callback(f"Auto-Editor successfully identified {kept_count} kept clips and {cut_count} cuts in record time!")
            
        return segments
    finally:
        if xml_output.exists():
            try:
                xml_output.unlink()
            except Exception:
                pass

def export_auto_editor_nle(
    video_path: str,
    export_format: str,
    threshold_percent: float = 4.0,
    margin_sec: float = 0.2,
    output_path: Optional[str] = None
) -> str:
    """
    Exports NLE timelines directly using Auto-Editor's native exporters:
    'premiere' (.xml), 'resolve' (.fcpxml), 'final-cut-pro' (.fcpxml), 'shotcut' (.mlt)
    """
    video_p = Path(video_path).resolve()
    ext_map = {
        "premiere": ".xml",
        "resolve": ".fcpxml",
        "final-cut-pro": ".fcpxml",
        "shotcut": ".mlt"
    }
    ext = ext_map.get(export_format, ".xml")
    if not output_path:
        out_p = Path("clipper/cache/exports") / f"{video_p.stem}_{export_format}{ext}"
    else:
        out_p = Path(output_path).resolve()
        
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    ae_cmd = _get_auto_editor_cmd()
    
    cmd = [
        ae_cmd,
        str(video_p),
        "--edit", f"audio:threshold={threshold_percent}%",
        "--margin", f"{margin_sec}s",
        "--export", export_format,
        "-o", str(out_p.resolve())
    ]
    
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return str(out_p.resolve())
