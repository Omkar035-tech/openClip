"""
Hardware detection and execution profile manager.
Supports Apple Silicon (Metal/VideoToolbox), NVIDIA GPUs (CUDA/NVENC), and CPU fallback.
Provides user-configurable hardware acceleration mode per pipeline stage.
"""

import os
import sys
import shutil
import subprocess
from typing import Dict, Any, List, Optional

_HW_INFO_CACHE: Optional[Dict[str, Any]] = None
_NVENC_AVAILABLE: Optional[bool] = None
_VIDEOTOOLBOX_AVAILABLE: Optional[bool] = None

def detect_hardware() -> Dict[str, Any]:
    """
    Detects system platform, CPU cores, GPU capabilities (NVIDIA CUDA / Apple Metal),
    and available FFmpeg hardware accelerators.
    """
    global _HW_INFO_CACHE
    if _HW_INFO_CACHE is not None:
        return _HW_INFO_CACHE

    info = {
        "platform": sys.platform,
        "os_name": "macOS" if sys.platform == "darwin" else ("Windows" if os.name == "nt" else "Linux"),
        "cpu_count": os.cpu_count() or 4,
        "cuda_available": False,
        "cuda_device_name": None,
        "cuda_device_count": 0,
        "apple_silicon": False,
        "nvenc_available": False,
        "videotoolbox_available": False,
    }

    # 1. Check NVIDIA CUDA via ctranslate2 / torch
    try:
        import ctranslate2
        cuda_count = ctranslate2.get_cuda_device_count()
        if cuda_count > 0:
            info["cuda_available"] = True
            info["cuda_device_count"] = cuda_count
    except Exception:
        pass

    if not info["cuda_available"]:
        try:
            import torch
            if torch.cuda.is_available():
                info["cuda_available"] = True
                info["cuda_device_count"] = torch.cuda.device_count()
        except Exception:
            pass

    # Try reading GPU device name from nvidia-smi if available
    if info["cuda_available"] or shutil.which("nvidia-smi"):
        try:
            res = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout.strip():
                info["cuda_device_name"] = res.stdout.strip().splitlines()[0]
                info["cuda_available"] = True
        except Exception:
            pass

    # 2. Check Apple Silicon Metal
    if sys.platform == "darwin":
        try:
            res = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, timeout=2)
            brand = res.stdout.strip()
            if "Apple" in brand:
                info["apple_silicon"] = True
                info["apple_chip"] = brand
        except Exception:
            pass

    # 3. Check FFmpeg Hardware Encoders
    info["nvenc_available"] = check_nvenc_support()
    info["videotoolbox_available"] = check_videotoolbox_support()

    _HW_INFO_CACHE = info
    return info

def check_nvenc_support() -> bool:
    """Verifies whether ffmpeg h264_nvenc works on the current system."""
    global _NVENC_AVAILABLE
    if _NVENC_AVAILABLE is not None:
        return _NVENC_AVAILABLE
    try:
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30", "-c:v", "h264_nvenc", "-f", "null", "-"]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
        _NVENC_AVAILABLE = (res.returncode == 0)
    except Exception:
        _NVENC_AVAILABLE = False
    return _NVENC_AVAILABLE

def check_videotoolbox_support() -> bool:
    """Verifies whether ffmpeg h264_videotoolbox works on macOS."""
    global _VIDEOTOOLBOX_AVAILABLE
    if _VIDEOTOOLBOX_AVAILABLE is not None:
        return _VIDEOTOOLBOX_AVAILABLE
    if sys.platform != "darwin":
        _VIDEOTOOLBOX_AVAILABLE = False
        return False
    try:
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30", "-c:v", "h264_videotoolbox", "-f", "null", "-"]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
        _VIDEOTOOLBOX_AVAILABLE = (res.returncode == 0)
    except Exception:
        _VIDEOTOOLBOX_AVAILABLE = False
    return _VIDEOTOOLBOX_AVAILABLE

def get_h264_encoder_params(hw_mode: str = "auto") -> List[str]:
    """
    Returns optimal FFmpeg CLI args for H.264 video rendering based on chosen mode:
    'auto', 'gpu' (NVENC / VideoToolbox), or 'cpu' (libx264).
    """
    hw = detect_hardware()

    if hw_mode in ("auto", "gpu"):
        # 1. Try NVENC on NVIDIA
        if hw.get("nvenc_available") or check_nvenc_support():
            # -preset p5: High quality, fast real-time hardware encode
            # -cq 19: Constant quality equivalent to CRF 18
            return ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19", "-pix_fmt", "yuv420p"]
        
        # 2. Try VideoToolbox on Apple Silicon macOS
        if hw.get("videotoolbox_available") or check_videotoolbox_support():
            return ["-c:v", "h264_videotoolbox", "-b:v", "8500k", "-pix_fmt", "yuv420p"]

    # 3. CPU Fallback (libx264)
    return ["-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p"]

def get_transcribe_device(hw_mode: str = "auto", cpu_threads: int = 4) -> Dict[str, Any]:
    """
    Determines Whisper execution device ('cuda', 'mlx', or 'cpu') and precision ('float16', 'int8').
    """
    hw = detect_hardware()

    if hw_mode in ("auto", "gpu"):
        # Check Apple Silicon
        if hw.get("apple_silicon") and sys.platform == "darwin":
            return {
                "backend": "mlx",
                "device": "metal",
                "compute_type": "float16",
                "threads": cpu_threads
            }
        # Check NVIDIA CUDA
        if hw.get("cuda_available"):
            return {
                "backend": "faster-whisper",
                "device": "cuda",
                "compute_type": "float16",
                "threads": cpu_threads
            }

    # CPU mode or fallback
    return {
        "backend": "faster-whisper",
        "device": "cpu",
        "compute_type": "int8",
        "threads": max(1, min(cpu_threads, hw.get("cpu_count", 4)))
    }
