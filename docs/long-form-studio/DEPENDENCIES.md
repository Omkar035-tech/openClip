# Long-Form Studio — Dependency Ledger

| Package | Version | Purpose | Why Selected Over Alternatives |
| :--- | :--- | :--- | :--- |
| **`scenedetect`** | `0.7.3` | Visual scene boundary detection | Industry standard for content-aware scene cut detection; fast OpenCV engine. |
| **`opentimelineio`** | `0.18.1` | NLE timeline interchange (.otio) | Universal interchange standard supported by DaVinci Resolve, Premiere, and Final Cut. |
| **`faster-whisper`** | `1.2.1` (Pre-installed) | Speech-to-text with word timestamps | 4x faster than vanilla OpenAI Whisper via CTranslate2 with INT8/FP16 quantization. |
| **`librosa` / `scipy`** | `1.0.0` / `1.18.1` (Pre-installed) | Audio features (RMS, spectral centroid, pitch) | Fast NumPy vectorized audio DSP. |
| **`opencv-python`** | `5.0.0.93` (Pre-installed) | Frame difference and motion detection | Hardware-accelerated computer vision matrix operations. |
| **`groq`** | `1.7.0` (Pre-installed) | High-speed LLM editorial triage | 280-500 tokens/sec allows real-time editorial decisions on 5-hour video metadata. |
| **`google-genai`** | `3.0.0` (Pre-installed) | Gemini 2.5 Flash editorial fallback | High reliability multi-modal fallback provider. |
| **`fastapi` / `uvicorn`** | `0.162.2` / `0.54.0` (Pre-installed) | REST API & WebSocket server | Asynchronous request processing and background streaming. |
| **`ffmpeg` / `ffprobe`** | `9.0.2` (System) | Video decoding, slicing, transitions, render | Native system binary with NVENC hardware acceleration. |
