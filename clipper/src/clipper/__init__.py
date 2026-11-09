"""Clipper package: Fast, open-source podcast-to-viral-short engine."""
import os
import shutil
from pathlib import Path

__version__ = "0.1.0"

def _ensure_ffmpeg_path():
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return
    candidates = [
        Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages",
        Path.home() / "scoop" / "apps" / "ffmpeg" / "current" / "bin",
        Path("C:/ProgramData/chocolatey/bin"),
        Path("C:/ffmpeg/bin"),
        Path("/usr/local/bin"),
        Path("/opt/homebrew/bin"),
    ]
    for c in candidates:
        if not c.exists():
            continue
        if c.name == "Packages":
            for bin_match in c.glob("**/ffmpeg-*-full_build/bin"):
                if bin_match.is_dir() and (bin_match / "ffmpeg.exe").exists():
                    os.environ["PATH"] = str(bin_match) + os.pathsep + os.environ.get("PATH", "")
                    return
        elif (c / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")).exists():
            os.environ["PATH"] = str(c) + os.pathsep + os.environ.get("PATH", "")
            return

_ensure_ffmpeg_path()
