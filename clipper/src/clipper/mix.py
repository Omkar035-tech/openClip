import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

def mix_audio_track(
    voice_wav: str,
    music_mp3: Optional[str],
    output_wav: str,
    duration: float,
    config: Dict[str, Any]
) -> str:
    """
    Mixes voice and mood-matched background music according to Stage 10 & 12 specs:
    - Voice cleanup: Highpass 80Hz, light compression
    - Music EQ: Highpass 60Hz, -3.5dB pocket dip at 2.5kHz
    - Music ducking: ffmpeg sidechaincompress keyed by speech (threshold -30dB, ratio 7:1)
    - Fade in 0.5s, Fade out 1.2s landing at the end
    - Final mastering: EBU R128 loudnorm (-14.0 LUFS, -1.0 dBTP)
    """
    music_cfg = config.get("music", {})
    audio_cfg = config.get("audio", {})
    
    target_lufs = audio_cfg.get("target_lufs", -14.0)
    max_tp = audio_cfg.get("max_true_peak", -1.0)
    music_level_db = music_cfg.get("level_db", -22.0)
    
    if not music_mp3 or not os.path.exists(music_mp3) or not music_cfg.get("enabled", True):
        # Voice-only mastering
        print("Mixing voice-only track (music disabled)...")
        filter_str = (
            f"highpass=f=80, acompressor=threshold=-20dB:ratio=3:attack=10:release=100,"
            f"loudnorm=I={target_lufs}:LRA=7:TP={max_tp}"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", voice_wav,
            "-af", filter_str,
            "-ar", "48000",
            "-ac", "2",
            output_wav
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return output_wav
        
    print(f"Mixing voice with background track ({os.path.basename(music_mp3)}) with sidechain ducking...")
    
    fade_out_start = max(0.0, duration - 1.2)
    # Filtergraph:
    # 1. Voice stream [0:a]: highpass 80Hz, compression -> [voice_clean], split -> [v_main][v_key]
    # 2. Music stream [1:a]: trim, highpass 60Hz, 2.5kHz notch dip, volume adjustment, fade in/out -> [music_eq]
    # 3. Ducking: [music_eq] sidechaincompressed by [v_key] -> [music_ducked]
    # 4. Amix: [v_main] + [music_ducked] -> loudnorm -> [out]
    filter_complex = (
        "[0:a]highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=10:release=100,asplit=2[v_main][v_key];"
        f"[1:a]atrim=0:{duration},highpass=f=60,equalizer=f=2500:t=q:w=1:g=-3.5,"
        f"volume={music_level_db}dB,afade=t=in:ss=0:d=0.5,afade=t=out:st={fade_out_start:.2f}:d=1.2[music_eq];"
        "[music_eq][v_key]sidechaincompress=threshold=-30dB:ratio=7:attack=20:release=300[music_ducked];"
        f"[v_main][music_ducked]amix=inputs=2:duration=first:dropout_transition=2,"
        f"loudnorm=I={target_lufs}:LRA=7:TP={max_tp}[out]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", voice_wav,
        "-stream_loop", "-1",
        "-i", music_mp3,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-ar", "48000",
        "-ac", "2",
        output_wav
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_wav
