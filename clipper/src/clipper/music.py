import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

def load_music_library(library_dir: str = "music_library") -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    lib_path = Path(library_dir) / "library.json"
    lic_path = Path(library_dir) / "licenses.json"
    
    if not lib_path.exists():
        return [], {}
        
    with open(lib_path, "r", encoding="utf-8") as f:
        tracks = json.load(f)
    with open(lic_path, "r", encoding="utf-8") as f:
        licenses = json.load(f)
        
    return tracks, licenses

def select_track_for_clip(clip_meta: Dict[str, Any], library_dir: str = "music_library", excluded_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Selects the best mood-matched instrumental track for a clip.
    Ranking criteria:
    - Mood tag overlap (50%)
    - BPM in range (20%)
    - Energy match (20%)
    - Duration fit (10%)
    Never reuses the same track in back-to-back clips (excluded_ids).
    """
    tracks, licenses = load_music_library(library_dir)
    if not tracks:
        return None
        
    excluded = set(excluded_ids or [])
    available = [t for t in tracks if t["id"] not in excluded]
    if not available:
        available = tracks # Fall back if all used
        
    mood_info = clip_meta.get("mood", {})
    primary_mood = mood_info.get("primary_mood", "casual").lower()
    target_energy = mood_info.get("energy_0_to_10", 5.0)
    bpm_range = mood_info.get("bpm_range", [90, 140])
    
    scored_tracks = []
    for t in available:
        score = 0.0
        
        # 1. Mood match (50%)
        t_moods = [m.lower() for m in t.get("moods", [])]
        if primary_mood in t_moods:
            score += 50.0
        elif any(genre in t_moods for genre in mood_info.get("genre_hints", [])):
            score += 35.0
        else:
            score += 15.0
            
        # 2. BPM match (20%)
        bpm = t.get("bpm", 120.0)
        if bpm_range[0] <= bpm <= bpm_range[1]:
            score += 20.0
        else:
            dist = min(abs(bpm - bpm_range[0]), abs(bpm - bpm_range[1]))
            score += max(0.0, 20.0 - dist * 0.4)
            
        # 3. Energy match (20%)
        t_energy = t.get("energy", 5.0)
        e_diff = abs(t_energy - target_energy)
        score += max(0.0, 20.0 - e_diff * 3.0)
        
        # 4. Duration fit (10%)
        if t.get("duration", 0) >= clip_meta.get("duration", 55.0):
            score += 10.0
        else:
            score += 5.0
            
        scored_tracks.append((score, t))
        
    scored_tracks.sort(key=lambda x: x[0], reverse=True)
    best_track = scored_tracks[0][1]
    
    # Attach license info
    track_lic = licenses.get(best_track["id"], {})
    
    result = dict(best_track)
    result["abs_file_path"] = str(Path(library_dir) / best_track["file"])
    result["license_info"] = track_lic
    return result

def search_music_library(query: str, library_dir: str = "music_library") -> List[Dict[str, Any]]:
    tracks, _ = load_music_library(library_dir)
    query_lower = query.lower()
    matches = []
    for t in tracks:
        text = f"{t['title']} {t['artist']} {' '.join(t.get('moods', []))}".lower()
        if any(term in text for term in query_lower.split()):
            matches.append(t)
    return matches

def add_track_to_library(file_path: str, title: str, artist: str, mood_tags: List[str], license_type: str, library_dir: str = "music_library"):
    import librosa
    lib_path = Path(library_dir)
    tracks_dir = lib_path / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    
    src = Path(file_path)
    dest = tracks_dir / src.name
    shutil.copy2(src, dest)
    
    # Analyze
    y, sr = librosa.load(str(dest), sr=22050, duration=60.0)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo[0] if hasattr(tempo, '__iter__') else tempo)
    dur = float(librosa.get_duration(path=str(dest)))
    
    track_id = src.stem.lower().replace(" ", "_")
    
    tracks, licenses = load_music_library(library_dir)
    tracks.append({
        "id": track_id,
        "title": title or src.stem,
        "artist": artist or "Unknown",
        "file": f"tracks/{src.name}",
        "bpm": round(bpm, 1),
        "duration": round(dur, 2),
        "moods": mood_tags,
        "energy": 6.0,
        "valence": 0.5,
        "instrumental_only": True
    })
    licenses[track_id] = {
        "title": title or src.stem,
        "artist": artist or "Unknown",
        "license": license_type or "CC-BY",
        "commercial_ok": True,
        "attribution_required": True
    }
    
    with open(lib_path / "library.json", "w") as f:
        json.dump(tracks, f, indent=2)
    with open(lib_path / "licenses.json", "w") as f:
        json.dump(licenses, f, indent=2)
    print(f"Added '{title}' to music library.")
