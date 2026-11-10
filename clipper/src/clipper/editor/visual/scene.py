import os
from pathlib import Path
from typing import List, Dict, Any
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector

def detect_visual_scenes(video_path: str, threshold: float = 27.0, min_scene_len_sec: float = 1.5) -> List[Dict[str, float]]:
    """
    Detects scene transitions using PySceneDetect ContentDetector.
    Returns list of scene cuts: [{'start': 0.0, 'end': 14.2, 'duration': 14.2}, ...]
    """
    path = Path(video_path)
    if not path.exists():
        return []
        
    try:
        video = open_video(str(path.resolve()))
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=int(min_scene_len_sec * video.frame_rate)))
        scene_manager.detect_scenes(video)
        
        scenes = scene_manager.get_scene_list()
        results = []
        for start_time, end_time in scenes:
            t_start = start_time.get_seconds()
            t_end = end_time.get_seconds()
            results.append({
                "start": round(t_start, 2),
                "end": round(t_end, 2),
                "duration": round(t_end - t_start, 2)
            })
        return results
    except Exception as e:
        print(f"[PySceneDetect] Warning: Scene detection encountered {e}, falling back to empty scene list.")
        return []
