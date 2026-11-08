import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

def format_timestamp_srt(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        secs += 1
        millis = 0
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def format_timestamp_ass(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        secs += 1
        centis = 0
    return f"{hrs:d}:{mins:02d}:{secs:02d}.{centis:02d}"

def chunk_words(words: List[Dict[str, Any]], max_words: int = 3, max_gap: float = 0.45) -> List[Dict[str, Any]]:
    """Chunks word-level timestamps into concise readable 2-4 word screen phrases."""
    phrases = []
    curr = []
    
    for w in words:
        if not curr:
            curr.append(w)
            continue
            
        gap = w["start"] - curr[-1]["end"]
        prev_punct = any(curr[-1]["word"].strip().endswith(p) for p in [".", "!", "?", ",", ";"])
        
        if len(curr) >= max_words or gap > max_gap or (len(curr) >= 2 and prev_punct):
            phrases.append({
                "start": curr[0]["start"],
                "end": curr[-1]["end"] + 0.15,
                "words": list(curr),
                "text": " ".join(item["word"].strip() for item in curr)
            })
            curr = [w]
        else:
            curr.append(w)
            
    if curr:
        phrases.append({
            "start": curr[0]["start"],
            "end": curr[-1]["end"] + 0.2,
            "words": list(curr),
            "text": " ".join(item["word"].strip() for item in curr)
        })
    return phrases

def generate_srt(words: List[Dict[str, Any]], srt_path: Path, t_offset: float = 0.0):
    phrases = chunk_words(words)
    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, p in enumerate(phrases, 1):
            s = format_timestamp_srt(max(0.0, p["start"] - t_offset))
            e = format_timestamp_srt(max(0.0, p["end"] - t_offset))
            f.write(f"{idx}\n{s} --> {e}\n{p['text']}\n\n")

def generate_ass(words: List[Dict[str, Any]], ass_path: Path, t_offset: float = 0.0, style_name: str = "bold-pop"):
    """
    Generates ASS subtitle file with word-level karaoke tags (\\k).
    Configured for 1080x1920 vertical layout with safe zone alignment.
    """
    phrases = chunk_words(words)
    
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BoldPop,Montserrat ExtraBold,68,&H00FFFFFF,&H0000D4FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,6,3,2,60,60,540,1
Style: CleanBox,Inter Bold,62,&H00FFFFFF,&H0000E6FF,&H00000000,&HA0000000,-1,0,0,0,100,100,1,0,3,4,0,2,60,60,540,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    style_tag = "BoldPop" if style_name == "bold-pop" else "CleanBox"
    
    events = []
    for p in phrases:
        s_str = format_timestamp_ass(max(0.0, p["start"] - t_offset))
        e_str = format_timestamp_ass(max(0.0, p["end"] - t_offset))
        
        # Build karaoke text
        karaoke_parts = []
        for w in p["words"]:
            dur_cs = int(round((w["end"] - w["start"]) * 100))
            w_text = w["word"].strip().upper()
            karaoke_parts.append(f"{{\\k{dur_cs}}}{w_text} ")
            
        line_text = "".join(karaoke_parts).strip()
        events.append(f"Dialogue: 0,{s_str},{e_str},{style_tag},,0,0,0,,{line_text}")
        
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")

class CaptionRenderer:
    """High-performance frame-by-frame kinetic caption renderer with PIL."""
    def __init__(self, font_path: str, style_cfg: Dict[str, Any]):
        self.font_path = font_path
        self.style = style_cfg
        self.font_sizes = [72, 64, 54, 46]
        self.fonts = {s: ImageFont.truetype(font_path, s) for s in self.font_sizes}
        
    def render(self, img_w: int, img_h: int, cur_time: float, phrases: List[Dict[str, Any]]) -> Image.Image:
        overlay = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        active_phrase = None
        for p in phrases:
            if p["start"] <= cur_time <= p["end"]:
                active_phrase = p
                break
                
        if not active_phrase:
            return overlay
            
        words = active_phrase["words"]
        max_safe_w = 920
        
        # Select best font size
        chosen_font = self.fonts[64]
        for f_size in self.font_sizes:
            f = self.fonts[f_size]
            space_w = f.getbbox(" ")[2] - f.getbbox(" ")[0]
            total_w = sum((f.getbbox(w["word"].strip().upper())[2] - f.getbbox(w["word"].strip().upper())[0]) for w in words)
            total_w += space_w * (len(words) - 1)
            if total_w <= max_safe_w or f_size == self.font_sizes[-1]:
                chosen_font = f
                break
                
        space_w = chosen_font.getbbox(" ")[2] - chosen_font.getbbox(" ")[0]
        word_boxes = []
        tot_w = 0
        for w in words:
            w_str = w["word"].strip().upper()
            bbox = chosen_font.getbbox(w_str)
            w_w = bbox[2] - bbox[0]
            w_h = bbox[3] - bbox[1]
            word_boxes.append((w_str, w_w, w_h, w))
            tot_w += w_w
        tot_w += space_w * (len(words) - 1)
        
        cur_x = (img_w - tot_w) // 2
        base_y = int(img_h * self.style.get("position_ratio", 0.70))
        
        # Clean-box preset background
        if self.style.get("box_enabled", False):
            pad_x, pad_y = self.style.get("box_padding", [24, 14])
            box_rect = [cur_x - pad_x, base_y - pad_y, cur_x + tot_w + pad_x, base_y + 70 + pad_y]
            draw.rounded_rectangle(box_rect, radius=16, fill=(0, 0, 0, 160))
            
        stroke_w = self.style.get("stroke_width", 7)
        
        for w_str, w_w, w_h, w_meta in word_boxes:
            is_active = (w_meta["start"] <= cur_time <= w_meta["end"] + 0.08)
            
            if is_active:
                fill_col = (255, 212, 0, 255) # Pop active yellow
                y_offset = -4
                sw = stroke_w + 1
            else:
                fill_col = (255, 255, 255, 255) # White
                y_offset = 0
                sw = stroke_w
                
            # Draw outline
            pos_x = cur_x
            pos_y = base_y + y_offset
            for dx in range(-sw, sw + 1):
                for dy in range(-sw, sw + 1):
                    if dx * dx + dy * dy <= sw * sw:
                        draw.text((pos_x + dx, pos_y + dy), w_str, font=chosen_font, fill=(0, 0, 0, 255))
            # Draw text
            draw.text((pos_x, pos_y), w_str, font=chosen_font, fill=fill_col)
            cur_x += w_w + space_w
            
        return overlay
