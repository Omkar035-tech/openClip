import os
import sys
import time
import yaml
import json
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Clipper: Fast, open-source podcast-to-viral-short engine for Apple Silicon")
console = Console()

def load_config() -> dict:
    cfg_path = Path("config.yaml")
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}

@app.command()
def run(
    video: str = typer.Argument(..., help="Path to input podcast video file"),
    n: int = typer.Option(5, "--n", "-n", help="Number of viral shorts to generate"),
    style: str = typer.Option("bold-pop", "--style", "-s", help="Caption style preset (bold-pop, clean-box, highlight-sweep)"),
    music: str = typer.Option("auto", "--music", "-m", help="Music mode: auto, off, or path to audio file"),
    verify: bool = typer.Option(False, "--verify/--no-verify", help="Toggle visual proxy verification")
):
    """Executes the full pipeline: Transcribe -> Extract signals -> Pick top viral moments -> Reframe 9:16 -> Mix mood music -> Render shorts."""
    start_total = time.time()
    video_path = Path(video).resolve()
    if not video_path.exists():
        console.print(f"[bold red]Error:[/] Video file '{video}' not found.")
        raise typer.Exit(1)
        
    config = load_config()
    config["general"]["n_clips"] = n
    config["captions"]["style"] = style
    config["models"]["visual_verify"] = verify
    if music == "off":
        config["music"]["enabled"] = False
        
    console.print(f"[bold cyan]=== Starting Clipper Production for {video_path.name} ===[/]")
    
    # Cache setup
    from .cache import compute_file_hash, CacheManager
    cache_mgr = CacheManager(config.get("general", {}).get("cache_dir", "cache"))
    video_hash = compute_file_hash(str(video_path))
    cache_dir = cache_mgr.get_cache_dir(video_hash)
    console.print(f"[green]Video Hash:[/] {video_hash[:16]} (Cache: {cache_dir})")
    
    # 1. Transcribe (Stage 1)
    from .transcribe import transcribe_video
    t0 = time.time()
    transcript = transcribe_video(str(video_path), cache_dir, config)
    console.print(f"[bold green]✓[/] Transcription complete in {time.time()-t0:.1f}s ({len(transcript)} segments)")
    
    # 2. Local Audio Signals (Stage 2)
    from .audio_features import compute_audio_features
    wav_path = cache_dir / "audio_16k.wav"
    t1 = time.time()
    features = compute_audio_features(str(wav_path), transcript, cache_dir)
    console.print(f"[bold green]✓[/] Audio features analyzed in {time.time()-t1:.1f}s")
    
    # 3. LLM / Semantic Selection & Ranking (Stage 3 & 4)
    from .pick import select_and_rank_clips
    t2 = time.time()
    top_clips = select_and_rank_clips(transcript, features, config, cache_dir)
    console.print(f"[bold green]✓[/] Selected top {len(top_clips)} clips in {time.time()-t2:.1f}s")
    
    # Display Selection Table
    table = Table(title="Selected Viral Short Candidates")
    table.add_column("#", style="cyan")
    table.add_column("Title", style="bold yellow")
    table.add_column("Time Range", style="green")
    table.add_column("Score", style="magenta")
    table.add_column("Mood & Music Prompt", style="blue")
    
    for i, c in enumerate(top_clips, 1):
        table.add_row(
            str(i),
            c["suggested_title"],
            f"{c['start']:.1f}s - {c['end']:.1f}s ({c['duration']:.1f}s)",
            f"{c['score_total']:.1f}",
            f"{c['mood']['primary_mood']}: {c['mood']['music_prompt'][:35]}..."
        )
    console.print(table)
    
    # 4. Render All Clips (Stage 6 - 13)
    from .render import render_short_clip
    out_dir = Path(config.get("general", {}).get("output_dir", "out")) / video_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    
    excluded_music = []
    manifests = []
    
    for idx, clip_meta in enumerate(top_clips, 1):
        t_render = time.time()
        m = render_short_clip(str(video_path), clip_meta, idx, out_dir, config, excluded_music)
        manifests.append(m)
        console.print(f"[bold green]✓[/] Rendered Short #{idx} in {time.time()-t_render:.1f}s")
        
    # Copy selection report to out_dir
    sel_report = cache_dir / "selection_report.md"
    if sel_report.exists():
        import shutil
        shutil.copy2(sel_report, out_dir / "selection_report.md")
        
    total_time = time.time() - start_total
    console.print(f"\n[bold green]=== All {len(top_clips)} shorts generated successfully in {total_time:.1f}s! ===[/]")
    console.print(f"Output files stored in: [bold cyan]{out_dir.resolve()}[/]")

@app.command()
def transcribe(video: str = typer.Argument(..., help="Path to video")):
    """Runs GPU transcription on video and caches word-level transcript."""
    config = load_config()
    from .cache import compute_file_hash, CacheManager
    from .transcribe import transcribe_video
    v_path = Path(video).resolve()
    cache_mgr = CacheManager(config.get("general", {}).get("cache_dir", "cache"))
    cache_dir = cache_mgr.get_cache_dir(compute_file_hash(str(v_path)))
    transcribe_video(str(v_path), cache_dir, config)
    console.print(f"[green]Transcript cached in {cache_dir / 'transcript.json'}[/]")

@app.command()
def pick(video: str = typer.Argument(..., help="Path to video")):
    """Extracts candidate windows and ranks top clips."""
    config = load_config()
    from .cache import compute_file_hash, CacheManager
    from .transcribe import transcribe_video
    from .audio_features import compute_audio_features
    from .pick import select_and_rank_clips
    v_path = Path(video).resolve()
    cache_mgr = CacheManager(config.get("general", {}).get("cache_dir", "cache"))
    cache_dir = cache_mgr.get_cache_dir(compute_file_hash(str(v_path)))
    transcript = transcribe_video(str(v_path), cache_dir, config)
    features = compute_audio_features(str(cache_dir / "audio_16k.wav"), transcript, cache_dir)
    clips = select_and_rank_clips(transcript, features, config, cache_dir)
    console.print(f"[green]Ranked {len(clips)} clips in {cache_dir / 'ranked.json'}[/]")

@app.command()
def music(
    action: str = typer.Argument("list", help="list, search, or add"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query for mood/genre"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Audio file path to add")
):
    """Manages the instrumental background music library."""
    from .music import load_music_library, search_music_library, add_track_to_library
    if action == "list":
        tracks, _ = load_music_library("music_library")
        table = Table(title="Instrumental Music Library")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="bold yellow")
        table.add_column("Artist", style="green")
        table.add_column("BPM", style="magenta")
        table.add_column("Moods", style="blue")
        for t in tracks:
            table.add_row(t["id"], t["title"], t["artist"], str(t["bpm"]), ", ".join(t.get("moods", [])))
        console.print(table)
    elif action == "search" and query:
        matches = search_music_library(query, "music_library")
        console.print(f"[yellow]Matches for '{query}':[/]")
        for m in matches:
            console.print(f" - [bold cyan]{m['title']}[/] by {m['artist']} ({', '.join(m.get('moods', []))})")
    elif action == "add" and path:
        add_track_to_library(path, Path(path).stem, "User Added", ["custom"], "User Granted", "music_library")

@app.command()
def render(
    video: str = typer.Argument(..., help="Path to video file"),
    clip_index: int = typer.Argument(1, help="Index of ranked clip to render (1-based)")
):
    """Renders a single specific ranked candidate clip."""
    config = load_config()
    from .cache import compute_file_hash, CacheManager
    from .render import render_short_clip
    v_path = Path(video).resolve()
    cache_mgr = CacheManager(config.get("general", {}).get("cache_dir", "cache"))
    cache_dir = cache_mgr.get_cache_dir(compute_file_hash(str(v_path)))
    ranked_file = cache_dir / "ranked.json"
    if not ranked_file.exists():
        console.print("[red]No ranked clips found. Run 'clipper pick <video>' first.[/]")
        raise typer.Exit(1)
        
    with open(ranked_file, "r") as f:
        clips = json.load(f)
        
    if clip_index < 1 or clip_index > len(clips):
        console.print(f"[red]Invalid clip index {clip_index}. Available: 1 to {len(clips)}[/]")
        raise typer.Exit(1)
        
    clip_meta = clips[clip_index - 1]
    out_dir = Path(config.get("general", {}).get("output_dir", "out")) / v_path.stem
    render_short_clip(str(v_path), clip_meta, clip_index, out_dir, config, [])
    console.print(f"[bold green]✓[/] Rendered clip #{clip_index} to {out_dir}")

@app.command()
def batch(
    folder: str = typer.Argument(..., help="Folder containing podcast video files"),
    n: int = typer.Option(5, "--n", "-n", help="Number of clips per video")
):
    """Batch-processes all video files in a folder into viral shorts."""
    folder_path = Path(folder).resolve()
    extensions = {".mp4", ".mov", ".mkv", ".m4v"}
    video_files = [f for f in folder_path.iterdir() if f.suffix.lower() in extensions]
    console.print(f"[bold cyan]Found {len(video_files)} videos in {folder_path}[/]")
    for v in video_files:
        console.print(f"\n[bold yellow]>>> Processing {v.name}...[/]")
        run(str(v), n=n, style="bold-pop", music="auto", verify=False)

@app.command()
def ui(port: int = typer.Option(8080, "--port", "-p", help="Port to run the studio server on")):
    """Starts the interactive Clipper Studio Web UI."""
    from .server import start_server
    start_server(port)

@app.command()
def app_window():
    """Launches openClip Studio as a native Windows desktop software application."""
    from .desktop import launch_desktop_app
    launch_desktop_app()

def main():
    app()

if __name__ == "__main__":
    app()
