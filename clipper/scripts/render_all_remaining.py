import os
import sys
import json
import time
from pathlib import Path

BASE_DIR = Path("/Users/omkar-dev/Documents/antigravity/brave-bell/clipper")
sys.path.insert(0, str(BASE_DIR / "src"))

import yaml
from clipper.render import render_short_clip

with open(BASE_DIR / "config.yaml", "r") as f:
    config = yaml.safe_load(f)

video_path = "/Users/omkar-dev/Movies/OpenFilm/Projects/Untitled/assets/vidssave.com _10,000 bodies is my target_ _ Grilling with Castillo 720P.mp4"
video_hash = "9d74089070f07f2431c94e1c401459f2d37a8367a8e4260daf302037af43c61d"

cache_dir = BASE_DIR / "cache" / video_hash
with open(cache_dir / "ranked.json", "r") as f:
    ranked = json.load(f)

out_dir = BASE_DIR / "out" / Path(video_path).stem
out_dir.mkdir(parents=True, exist_ok=True)

# Keep track of excluded music IDs so each clip gets a distinct track
excluded = ["carefree"] # short_01 used carefree

for idx in range(2, len(ranked) + 1):
    clip_meta = ranked[idx - 1]
    t0 = time.time()
    print(f"\n--- RENDERING CLIP {idx}/{len(ranked)} ---")
    render_short_clip(video_path, clip_meta, idx, out_dir, config, excluded)
    print(f"--- CLIP {idx} FINISHED IN {time.time()-t0:.1f}s ---")

# Copy selection_report.md
import shutil
sel_rep = cache_dir / "selection_report.md"
if sel_rep.exists():
    shutil.copy2(sel_rep, out_dir / "selection_report.md")
    
# Copy all shorts into the workspace output and OpenFilm output folder as well
ws_out = Path("/Users/omkar-dev/Documents/antigravity/brave-bell/output")
ws_out.mkdir(parents=True, exist_ok=True)
for item in out_dir.glob("short_*.mp4"):
    shutil.copy2(item, ws_out / item.name)

# Also update OpenFilm film.html to load short_01 by default
film_html = Path("/Users/omkar-dev/Movies/OpenFilm/Projects/Untitled/film.html")
if film_html.exists():
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Clipper Shorts - Grilling with Castillo</title>
  <meta name="viewport" content="width=1080, height=1920">
  <meta name="film:fps" content="30">
  <meta name="film:duration" content="{ranked[0]['duration']:.2f}">
</head>
<body style="margin: 0; background-color: #000; overflow: hidden;">
  <main>
    <section data-track="video" data-type="video">
      <video src="output/short_01.mp4" 
             data-in="0" 
             data-out="{ranked[0]['duration']:.2f}" 
             data-start="0" 
             data-duration="{ranked[0]['duration']:.2f}"
             style="width: 1080px; height: 1920px; object-fit: cover;"></video>
    </section>
  </main>
</body>
</html>
"""
    with open(film_html, "w") as f:
        f.write(html_content)
        
    # Copy short_01 into OpenFilm output folder
    of_out = Path("/Users/omkar-dev/Movies/OpenFilm/Projects/Untitled/output")
    of_out.mkdir(parents=True, exist_ok=True)
    for item in out_dir.glob("short_*.mp4"):
        shutil.copy2(item, of_out / item.name)

print("\nALL CLIPS RENDERED AND SYNCHRONIZED SUCCESSFULLY!")
