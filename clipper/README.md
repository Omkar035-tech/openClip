# Clipper

Fast, reusable, open-source podcast-to-viral-short clipping engine for Apple Silicon M4.

## Features
- **GPU-Accelerated Transcription**: Apple Silicon `mlx-whisper` large-v3-turbo / `faster-whisper`.
- **Intelligent Selection**: Semantic hook detection + acoustic energy dynamics (RMS + spectral variance).
- **Automated 9:16 Reframing**: Face tracking with EMA smoothing and deadband to eliminate camera jitter.
- **Dynamic Camera**: Hook zoom, punchline punch-ins, push-ins.
- **Kinetic Subtitles**: Word-level karaoke highlighting in `bold-pop`, `clean-box`, and `highlight-sweep` styles.
- **Mood-Matched Background Music**: Curated commercial-use instrumental library with sidechain ducking and EBU R128 loudness mastering (-14.0 LUFS).
