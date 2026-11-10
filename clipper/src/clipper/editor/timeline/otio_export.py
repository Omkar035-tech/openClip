from pathlib import Path
from typing import Optional
import opentimelineio as otio
from clipper.editor.models import EDLModel

def export_edl_to_otio(edl: EDLModel, output_otio_path: str) -> str:
    """
    Serializes the EDL into an OpenTimelineIO (.otio) file, importable into
    DaVinci Resolve, Adobe Premiere Pro, and Final Cut Pro.
    """
    timeline = otio.schema.Timeline(name=f"Edit_{edl.project_id}")
    track = otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)
    timeline.tracks.append(track)
    
    fps = 30.0 # Standard editorial reference
    source_media = otio.schema.ExternalReference(target_url=edl.source_media_path)
    
    for seg in edl.segments:
        if seg.action == "KEEP":
            start_frame = int(seg.source_start * fps)
            duration_frames = int(seg.duration * fps)
            
            time_range = otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(start_frame, fps),
                duration=otio.opentime.RationalTime(duration_frames, fps)
            )
            
            clip = otio.schema.Clip(
                name=f"Segment_{seg.index}",
                media_reference=source_media,
                source_range=time_range
            )
            track.append(clip)
            
    out_p = Path(output_otio_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    otio.adapters.write_to_file(timeline, str(out_p.resolve()))
    return str(out_p.resolve())
