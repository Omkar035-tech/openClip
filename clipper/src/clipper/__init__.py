"""Clipper package: Fast, open-source podcast-to-viral-short engine."""
import os
import sys
import shutil
from pathlib import Path

__version__ = "0.1.0"

def _ensure_cuda_dlls():
    """Ensures nvidia cuBLAS, cuDNN, and CUDA runtime DLLs are available in PATH and os.add_dll_directory."""
    if os.name != "nt":
        return
    # Check site-packages/nvidia directories (installed via nvidia-cublas-cu12, nvidia-cudnn-cu12, etc.)
    base_dirs = [
        Path(sys.prefix) / "Lib" / "site-packages" / "nvidia",
        Path(__file__).resolve().parent.parent.parent / ".venv" / "Lib" / "site-packages" / "nvidia",
    ]
    for b in base_dirs:
        if b.is_dir():
            for bin_dir in b.glob("*/bin"):
                if bin_dir.is_dir():
                    bin_str = str(bin_dir)
                    if bin_str not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = bin_str + os.pathsep + os.environ.get("PATH", "")
                    if hasattr(os, "add_dll_directory"):
                        try:
                            os.add_dll_directory(bin_str)
                        except Exception:
                            pass

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

_ensure_cuda_dlls()
_ensure_ffmpeg_path()
