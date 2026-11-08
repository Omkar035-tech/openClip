---
name: podcast-clipper
description: Transforms long-form podcasts into high-retention 9:16 vertical shorts with kinetic captions, face tracking, and mood-matched music using Clipper.
---

# Podcast Clipper Skill

Trigger this skill whenever the user asks to:
- Make shorts, reels, or TikToks from a podcast or video
- Find the funniest, most viral, or highest-retention clips in a video
- Reframe 16:9 video to 9:16 vertical format with kinetic animated subtitles and background music

## CLI Usage

The Clipper CLI is installed at `/Users/omkar-dev/.local/bin/clipper`.

```bash
# Run full automated production on a video
clipper run "<video_path>" --n 5 --style bold-pop --music auto

# Fast selection / candidate check without full video rendering
clipper pick "<video_path>"

# Render a single clip from the candidates
clipper render "<video_path>" 1
```

All models run locally on Apple Silicon (M4 / Metal GPU) with zero API keys required.
Rendered deliverables are saved in `clipper/out/<video_name>/`.
