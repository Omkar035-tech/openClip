# AGENTS.md — Clipper: AI Podcast-to-Viral-Short Clipping Engine

Clipper is an automated, fast, open-source pipeline optimized for Apple Silicon (M4 / Metal GPU) that transforms long-form podcasts into production-ready 9:16 vertical shorts (1080x1920 @ 30fps) for YouTube Shorts, TikTok, and Instagram Reels.

---

## 1. Quick Start Commands

```bash
# Activate environment
cd /Users/omkar-dev/Documents/antigravity/brave-bell/clipper
source .venv/bin/activate

# End-to-end run (5 shorts, bold-pop subtitles, auto mood music)
clipper run "/path/to/podcast.mp4" --n 5 --style bold-pop --music auto

# Inspect or search background music library
clipper music list
clipper music search "playful comedy banter"

# Run individual pipeline stages
clipper transcribe "/path/to/podcast.mp4"
clipper pick "/path/to/podcast.mp4"
clipper render "/path/to/podcast.mp4" 1    # Render only clip #1

# Batch process an entire directory of podcasts
clipper batch "/path/to/podcast_folder" --n 3
```

---

## 2. Architecture & Pipeline Stages

```
Source Video (16:9)
       │
       ▼
[Stage 1: Transcribe] ──> mlx-whisper (Metal GPU) / faster-whisper INT8 ──> transcript.json (word timestamps)
       │
       ▼
[Stage 2: Audio Signals] ──> librosa RMS + spectral centroid variance ──> features.json
       │
       ▼
[Stage 3 & 4: Selection] ──> Overlapping sentence windows + Semantic/Acoustic Scorer ──> ranked.json
       │
       ▼
[Stage 7: Reframe 9:16] ──> MediaPipe / Haar active face tracking with EMA + deadband smoothing
       │
       ▼
[Stage 8: Virtual Camera] ──> 110% hook zoom punch-in (0-3s), dynamic push-ins, white flash, progress bar
       │
       ▼
[Stage 9: Captions] ──> Kinetic typography: Montserrat ExtraBold, neon yellow word-pop, 6px stroke
       │
       ▼
[Stage 10: Mood Music] ──> Curated commercial-use CC0/CC-BY instrumental library + sidechain ducking
       │
       ▼
[Stage 12 & 13: Mix & Export] ──> -14.0 LUFS EBU R128 mastering, 1080x1920 30fps MP4 + manifests & SRT
```

---

## 3. Project Layout

```
clipper/
  ├── pyproject.toml              # uv Python project definition (Python 3.11+)
  ├── config.yaml                 # Central configuration for models, camera, music, audio
  ├── .env.example                # API key template (Gemini API key optional; local fallback built-in)
  ├── AGENTS.md                   # This instruction file for AI agents & developers
  ├── README.md                   # Overview & quickstart
  ├── src/clipper/
  │     ├── __init__.py
  │     ├── cli.py                # Typer CLI commands (run, transcribe, pick, render, music, batch)
  │     ├── cache.py              # SHA-256 video hashing & cache invalidation
  │     ├── transcribe.py         # Apple Silicon GPU mlx-whisper & faster-whisper fallback
  │     ├── audio_features.py     # Librosa acoustic energy, RMS, and spectral centroid
  │     ├── pick.py               # Candidate windowing & multimodal semantic + acoustic scoring
  │     ├── verify.py             # Optional 480p proxy visual verification
  │     ├── reframe.py            # Face tracking & jitter-free 9:16 reframing
  │     ├── camera.py             # Virtual camera moves, hook zooms, flash, progress bar
  │     ├── captions.py           # Kinetic word-highlight typography & ASS/SRT generator
  │     ├── music.py              # Mood-matching algorithm & music library index
  │     ├── mix.py                # Voice highpass + sidechain ducking + -14 LUFS loudnorm
  │     └── render.py             # Video assembly, automated QA, and asset bundling
  ├── fonts/                      # OFL-licensed fonts (Montserrat, Inter, Poppins, Anton, Bebas Neue)
  ├── styles/                     # Caption presets (bold-pop.json, clean-box.json, highlight-sweep.json)
  ├── music_library/
  │     ├── tracks/               # Instrumental tracks (CC0 / CC-BY commercial use)
  │     ├── sfx/                  # Procedural CC0 whoosh & pop audio
  │     ├── library.json          # Track metadata, BPM, mood tags, energy levels
  │     └── licenses.json         # Exact license texts and attribution records
  ├── cache/<video_hash>/         # Cached transcripts, audio features, and rankings
  └── out/<video_name>/           # Rendered vertical shorts, SRTs, manifests, credits
```

---

## 4. Configuration Knobs (`config.yaml`)

| Knob | Default | Purpose |
| :--- | :--- | :--- |
| `general.n_clips` | `5` | Number of ranked clips to export |
| `models.whisper_backend` | `"mlx"` | Primary transcription engine (`mlx` for Metal GPU, `faster-whisper` for CPU) |
| `models.gemini_model` | `"gemini-2.5-flash"` | Gemini model used when `GEMINI_API_KEY` is present |
| `clip.target_duration` | `55.0` | Target clip duration in seconds (48.0s min, 59.5s max) |
| `captions.style` | `"bold-pop"` | Subtitle visual preset (`bold-pop`, `clean-box`, `highlight-sweep`) |
| `camera.hook_zoom` | `1.12` | Camera zoom factor during the first 2.5s hook |
| `camera.smoothing_alpha` | `0.08` | Exponential moving average smoothing for face panning |
| `camera.deadband_px` | `16` | Pixel threshold to suppress micro-jitter |
| `music.level_db` | `-22.0` | Background music base volume (~14dB below speech) |
| `music.ducking_threshold_db` | `-30.0` | Threshold where voice ducks background music |
| `audio.target_lufs` | `-14.0` | Final integrated audio loudness (EBU R128) |

---

## 5. Antigravity & OpenCode Integration

### Running directly within Antigravity
Antigravity can invoke any clipper task directly using the `run_command` tool:
```bash
/Users/omkar-dev/Documents/antigravity/brave-bell/clipper/.venv/bin/clipper run "<video_path>" --n 5
```
Because Clipper implements automatic local fallback scoring, **no API tokens or cloud credentials are required**. It runs 100% offline and locally on your Apple Silicon hardware.

### OpenCode Custom Skill
A skill configuration is registered in `.opencode/skills/podcast-clipper/SKILL.md` allowing natural language prompts like:
> *"Turn this podcast into 5 viral shorts using bold-pop style and mood music."*

---

## 6. Adding Custom Fonts & Caption Presets

1. **Adding a Font:** Download any `.ttf` or `.otf` font file (OFL license recommended) into `clipper/fonts/`.
2. **Adding a Style Preset:** Create a JSON file in `clipper/styles/<preset-name>.json`:
```json
{
  "name": "neon-glow",
  "font": "BebasNeue-Regular.ttf",
  "font_size": 72,
  "font_color": "#FFFFFF",
  "active_color": "#00FFCC",
  "stroke_color": "#000000",
  "stroke_width": 6,
  "box_enabled": false,
  "position_ratio": 0.68
}
```

---

## 7. Adding Custom Background Music Tracks

1. Add your instrumental track (`.mp3` or `.wav`):
```bash
clipper music add --path "/path/to/track.mp3"
```
2. The track will be analyzed with `librosa` for BPM, energy, and beat times, and registered in `music_library/library.json` and `music_library/licenses.json`.

---

## 8. Feedback Loop (`feedback.json`)

To train few-shot preferences and refine scoring over time:
When you rate a clip good or bad:
```json
{
  "clip_id": "short_01",
  "video_hash": "9d740890...",
  "rating": "positive",
  "music_rating": "positive",
  "transcript": "...",
  "notes": "Excellent hook and comedic timing"
}
```
Positive ratings are prioritized as few-shot exemplars; downvoted music tracks are avoided for similar mood prompts.
