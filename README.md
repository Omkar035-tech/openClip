# openClip 🎬⚡

> Fast, reusable, open-source **"Podcast to Viral Short"** clipping system & Studio Web UI optimized for Apple Silicon (M-series Macs) and modern GPUs.

openClip automatically transforms long-form horizontal podcasts and interviews into high-retention 9:16 vertical shorts (1080x1920 @ 30fps) with AI moment selection, kinetic karaoke captions, face centering, dynamic virtual camera movements, and mood-matched background soundtracks.

---

## ✨ Features

- **⚡ Fast GPU Transcription**: Uses `mlx-whisper` (Apple Silicon Metal) or `faster-whisper` for lightning-fast word-level transcription and timestamping.
- **🎯 Acoustic & Semantic Heuristic Moment Detection**: Identifies viral hooks by combining audio energy (RMS, pitch variance, speech rate) with semantic transcripts. Works 100% offline without requiring paid API keys, with optional Gemini Flash / Ollama LLM reranking.
- **📐 Smart 9:16 Reframing**: Face detection with Exponential Moving Average (EMA) smoothing and deadband damping to eliminate camera jitter.
- **🎥 Dynamic Camera Moves**: Virtual camera zoom punch-ins on emphasized punchlines (110–120%), slow push-ins, and cuts synced to music beats.
- **🔤 Animated Word-Level Kinetic Captions**: Crisp ASS karaoke subtitles burned directly into the video stream via `ffmpeg`/`libass`.
  - Presets: `bold-pop` (Montserrat ExtraBold with scale pop), `clean-box` (Inter Bold), and `highlight-sweep`.
  - **Auto-Detect Text Emphasis**: Automatically detects punchlines and makes key words bold and scaled up.
- **🎵 Mood-Matched Background Music**: Curated commercial-use CC-BY/CC0 instrumental tracks with automatic BPM matching, dynamic sidechain ducking (-22 dB), and EBU R128 loudness normalization (-14.0 LUFS).
- **🖥️ Studio Web UI (`http://localhost:8080`)**:
  - Live interactive font and subtitle test box.
  - Video format toggle (9:16 vertical vs landscape), clip count limit (up to 5), and max duration slider (15s–60s).
  - Custom OST upload with automatic BPM and audio energy indexing.
  - In-UI vertical 9:16 video player to preview all completed shorts.
  - YouTube Shorts automation modal with pre-formatted titles, descriptions, and hashtags.

---

## 🚀 Quick Start

### 1. Prerequisites
- **macOS** (Apple Silicon M1/M2/M3/M4 recommended) or Linux.
- **FFmpeg** with `libass` and `videotoolbox`:
  ```bash
  brew install ffmpeg uv
  ```

### 2. Installation
Clone the repository and install dependencies using `uv`:
```bash
git clone https://github.com/Omkar035-tech/openClip.git
cd openClip/clipper
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 3. Launching the Studio Web UI
Start the interactive local web dashboard:
```bash
clipper ui --port 8080
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser:
1. Select your input video file.
2. Customize subtitle styling and test in the live preview box.
3. Choose your background music or upload your own custom OST.
4. Click **"Generate Viral Shorts"** and watch the real-time pipeline run.
5. Preview completed 9:16 vertical shorts and prepare YouTube metadata.

---

## 🛠️ CLI Usage

You can also run openClip directly from the command line:

```bash
# Run the complete end-to-end pipeline
clipper run "/path/to/podcast.mp4" --n-clips 5 --max-duration 56

# Run individual pipeline stages:
clipper transcribe "/path/to/podcast.mp4"
clipper pick "/path/to/podcast.mp4"
clipper render "/path/to/podcast.mp4"
clipper music add "/path/to/song.mp3" --title "My Track" --mood "upbeat, energetic"
```

---

## 📁 Repository Layout

```text
openClip/
├── README.md
├── .gitignore
├── .opencode/
│   └── skills/podcast-clipper/SKILL.md  # OpenCode agent integration
└── clipper/
    ├── pyproject.toml                   # Python dependencies & CLI setup
    ├── config.yaml                      # Global pipeline knobs and styling
    ├── AGENTS.md                        # Agent execution and skill guide
    ├── assets/                          # Face detection Haar cascades
    ├── fonts/                           # OFL-licensed TrueType/OpenType fonts
    ├── music_library/                   # Curated CC-BY instrumental tracks & index
    ├── styles/                          # Subtitle JSON presets (bold-pop, etc.)
    └── src/clipper/
        ├── cli.py                       # Typer command-line interface
        ├── server.py                    # FastAPI Studio Web backend
        ├── web/index.html               # Responsive Studio Web UI
        ├── transcribe.py                # mlx-whisper & faster-whisper engine
        ├── audio_features.py            # Librosa acoustic energy & pitch extraction
        ├── pick.py                      # Heuristic & LLM moment selection
        ├── reframe.py                   # 9:16 face tracking & center crop
        ├── camera.py                    # Virtual camera zoom & keyframe generator
        ├── captions.py                  # ASS karaoke subtitle compiler
        ├── music.py                     # BPM, mood matching & track library
        ├── mix.py                       # Sidechain ducking & EBU R128 loudness
        ├── render.py                    # FFmpeg compositor & VideoToolbox encoder
        └── cache.py                     # Content-hash caching layer
```

---

## ⚖️ License & Attribution

- **openClip Core**: Open-source under the MIT License.
- **Bundled Fonts**: Licensed under the SIL Open Font License (OFL).
- **Starter Music Library**: Curated instrumental compositions by Kevin MacLeod ([incompetech.com](https://incompetech.com)), licensed under Creative Commons: By Attribution 4.0 (CC-BY 4.0).
