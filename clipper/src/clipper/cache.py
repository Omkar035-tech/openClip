import os
import hashlib
import json
from pathlib import Path

def compute_file_hash(filepath: str, block_size: int = 65536) -> str:
    """Computes SHA-256 hash of a file for cache keys."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while block := f.read(block_size):
            sha256.update(block)
    return sha256.hexdigest()

class CacheManager:
    """Manages cached transcripts, audio features, and candidate rankings."""
    def __init__(self, base_dir: str = "cache"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def get_cache_dir(self, video_hash: str) -> Path:
        p = self.base_dir / video_hash
        p.mkdir(parents=True, exist_ok=True)
        return p
        
    def get(self, video_hash: str, key: str):
        target = self.get_cache_dir(video_hash) / f"{key}.json"
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None
        
    def set(self, video_hash: str, key: str, data):
        target = self.get_cache_dir(video_hash) / f"{key}.json"
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
    def has(self, video_hash: str, key: str) -> bool:
        target = self.get_cache_dir(video_hash) / f"{key}.json"
        return target.exists() and target.stat().st_size > 0
