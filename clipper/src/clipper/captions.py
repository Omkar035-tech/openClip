import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

# Initialize better-profanity censor
try:
    from better_profanity import profanity
    profanity.load_censor_words()
except Exception:
    profanity = None

def censor_word_partial(raw_word: str) -> str:
    # First strip any unmappable non-BMP emoji characters from word
    if raw_word:
        raw_word = "".join(c for c in str(raw_word) if ord(c) < 0x10000)
    """
    Censors vulgar words by retaining first and last letter and replacing middle characters with asterisks:
    e.g., 'fuck' -> 'f**k', 'bitch' -> 'b***h', 'ass' -> 'a*s', 'motherfucker' -> 'm**********r'
    Preserves leading and trailing punctuation marks.
    """
    if not raw_word or not profanity:
        return raw_word
        
    # Extract leading & trailing punctuation
    prefix = ""
    for c in raw_word:
        if not c.isalnum():
            prefix += c
        else:
            break
            
    suffix = ""
    for c in reversed(raw_word):
        if not c.isalnum():
            suffix = c + suffix
        else:
            break
            
    core = raw_word[len(prefix):len(raw_word) - len(suffix)] if len(suffix) > 0 else raw_word[len(prefix):]
    if not core:
        return raw_word
        
    if profanity.contains_profanity(core.lower()):
        if len(core) <= 2:
            censored_core = core[0] + "*"
        else:
            censored_core = core[0] + ("*" * (len(core) - 2)) + core[-1]
        return prefix + censored_core + suffix
        
    return raw_word

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

def hex_to_rgba(c: str, default_alpha: int = 255) -> Tuple[int, int, int, int]:
    """Parses #RGB, #RRGGBB, #RRGGBBAA or rgba(...) strings into (r, g, b, a) tuple."""
    if not c:
        return (255, 255, 255, default_alpha)
    c = str(c).strip()
    if c.startswith("rgba"):
        try:
            parts = c.replace("rgba(", "").replace(")", "").split(",")
            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
            a = int(float(parts[3]) * 255) if float(parts[3]) <= 1.0 else int(parts[3])
            return (r, g, b, a)
        except Exception:
            return (255, 255, 255, default_alpha)
            
    c = c.lstrip('#')
    if len(c) == 3:
        c = ''.join(x + x for x in c)
    if len(c) == 6:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), default_alpha)
    elif len(c) == 8:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), int(c[6:8], 16))
    return (255, 255, 255, default_alpha)

def chunk_words(words: List[Dict[str, Any]], max_words: int = 3, max_gap: float = 0.45) -> List[Dict[str, Any]]:
    """
    Chunks word-level timestamps into concise readable 2-4 word screen phrases.
    Recognizes {{word}} emphasis tags and strips delimiters while setting is_emphasis flag.
    """
    phrases = []
    curr = []
    
    for w in words:
        raw_word = str(w.get("word", "")).strip()
        is_tagged_emphasis = False
        if "{{" in raw_word or "}}" in raw_word:
            is_tagged_emphasis = True
            clean_word = raw_word.replace("{{", "").replace("}}", "").strip()
        else:
            clean_word = raw_word
            
        # Apply partial asterisk profanity censoring (e.g. fuck -> f**k)
        censored_clean_word = censor_word_partial(clean_word)

        w_item = dict(w)
        w_item["word"] = censored_clean_word
        if is_tagged_emphasis:
            w_item["is_emphasis"] = True
            
        if not curr:
            curr.append(w_item)
            continue
            
        gap = w_item["start"] - curr[-1]["end"]
        prev_punct = any(curr[-1]["word"].strip().endswith(p) for p in [".", "!", "?", ",", ";"])
        
        if len(curr) >= max_words or gap > max_gap or (len(curr) >= 2 and prev_punct):
            phrases.append({
                "start": curr[0]["start"],
                "end": curr[-1]["end"] + 0.15,
                "words": list(curr),
                "text": " ".join(item["word"].strip() for item in curr)
            })
            curr = [w_item]
        else:
            curr.append(w_item)
            
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
    """
    High-performance frame-by-frame kinetic caption renderer with PIL.
    Supports:
    - Custom fonts & auto font scaling
    - Active word karaoke pop & emphasis tags ({{word}})
    - Word & Phrase background boxes/pills with customizable fill & radius
    - Dynamic rotation angles (-15° to +15°) for energetic tilted captions
    - Fade in / Fade out alpha transitions
    - Custom letter spacing & stroke outlines
    """
    def __init__(self, font_path: str, style_cfg: Dict[str, Any]):
        self.font_path = font_path
        self.style = style_cfg or {}
        self.font_sizes = [84, 76, 68, 60, 52, 44]
        self.fonts = {s: ImageFont.truetype(font_path, s) for s in self.font_sizes}
        
    def render(self, img_w: int, img_h: int, cur_time: float, phrases: List[Dict[str, Any]]) -> Image.Image:
        overlay = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        
        active_phrase = None
        for p in phrases:
            if p["start"] <= cur_time <= p["end"]:
                active_phrase = p
                break
                
        if not active_phrase:
            return overlay
            
        words = active_phrase["words"]
        max_safe_w = int(self.style.get("max_safe_width", 920))
        base_font_size = int(self.style.get("font_size", 68))
        
        # Pick best font matching requested size or scaling down if phrase is long
        chosen_font = self.fonts.get(base_font_size)
        if not chosen_font:
            try:
                chosen_font = ImageFont.truetype(self.font_path, base_font_size)
            except Exception:
                chosen_font = self.fonts[68]
                
        # Fade In / Fade Out Alpha calculation
        fade_dur = float(self.style.get("fade_duration", 0.12))
        alpha_mult = 1.0
        if fade_dur > 0:
            f_in = min(1.0, max(0.0, (cur_time - active_phrase["start"]) / fade_dur))
            f_out = min(1.0, max(0.0, (active_phrase["end"] - cur_time) / fade_dur))
            alpha_mult = min(f_in, f_out)
            
        # Parse Colors
        primary_col = hex_to_rgba(self.style.get("primary_color", "#FFFFFF"), int(255 * alpha_mult))
        active_col = hex_to_rgba(self.style.get("active_color", "#FFD400"), int(255 * alpha_mult))
        emphasis_col = hex_to_rgba(self.style.get("emphasis_color", self.style.get("active_color", "#FFD400")), int(255 * alpha_mult))
        stroke_col = hex_to_rgba(self.style.get("stroke_color", "#000000"), int(255 * alpha_mult))
        stroke_w = int(self.style.get("stroke_width", 7))
        rotation_angle = float(self.style.get("rotation_angle", 0.0))
        random_flip = bool(self.style.get("random_flip", False))
        if random_flip and abs(rotation_angle) > 0.05:
            # Alternates or pseudorandomly flips angle sign per phrase based on start time / index
            phrase_seed = int(active_phrase["start"] * 100)
            if (phrase_seed % 2) == 1:
                rotation_angle = -rotation_angle
        
        bg_mode = self.style.get("bg_mode", "none")
        if self.style.get("box_enabled", False) and bg_mode == "none":
            bg_mode = "phrase"
            
        bg_col = hex_to_rgba(self.style.get("bg_color", "rgba(0,0,0,0.65)"), int(200 * alpha_mult))
        bg_radius = int(self.style.get("bg_radius", 14))
        pad_x, pad_y = self.style.get("bg_padding", [18, 10])
        
        space_w = chosen_font.getbbox(" ")[2] - chosen_font.getbbox(" ")[0]
        word_boxes = []
        tot_w = 0
        
        for w in words:
            w_str = str(w["word"]).strip().upper()
            is_emph = bool(w.get("is_emphasis", False))
            
            bbox = chosen_font.getbbox(w_str)
            w_w = bbox[2] - bbox[0]
            w_h = bbox[3] - bbox[1]
            word_boxes.append({
                "str": w_str,
                "width": w_w,
                "height": w_h,
                "meta": w,
                "is_emphasis": is_emph
            })
            tot_w += w_w
        tot_w += space_w * (len(words) - 1)
        
        # Determine canvas padding to allow clean rotation without edge clipping
        strip_pad = 80
        strip_w = tot_w + strip_pad * 2 + pad_x * 2
        strip_h = 240
        strip_img = Image.new("RGBA", (strip_w, strip_h), (0, 0, 0, 0))
        strip_draw = ImageDraw.Draw(strip_img)
        
        draw_x = strip_pad + pad_x
        draw_y = (strip_h - 70) // 2
        
        # Draw Full-Phrase Background Box if requested
        if bg_mode == "phrase":
            p_rect = [draw_x - pad_x, draw_y - pad_y, draw_x + tot_w + pad_x, draw_y + 68 + pad_y]
            strip_draw.rounded_rectangle(p_rect, radius=bg_radius, fill=bg_col)
            
        for wb in word_boxes:
            w_str = wb["str"]
            w_w = wb["width"]
            w_meta = wb["meta"]
            is_emph = wb["is_emphasis"]
            is_active = (w_meta["start"] <= cur_time <= w_meta["end"] + 0.08)
            
            # Word-specific background pill (e.g. around active word or emphasis tags)
            if (bg_mode == "word" and is_active) or (bg_mode == "emphasis" and is_emph):
                w_rect = [draw_x - 10, draw_y - 6, draw_x + w_w + 10, draw_y + 62]
                strip_draw.rounded_rectangle(w_rect, radius=10, fill=bg_col)
                
            if is_active:
                fill_color = active_col
                y_offset = -4
                sw = stroke_w + 1
            elif is_emph:
                fill_color = emphasis_col
                y_offset = -2
                sw = stroke_w + 1
            else:
                fill_color = primary_col
                y_offset = 0
                sw = stroke_w
                
            pos_x = draw_x
            pos_y = draw_y + y_offset
            
            # Draw outline / stroke
            if sw > 0:
                for dx in range(-sw, sw + 1):
                    for dy in range(-sw, sw + 1):
                        if dx * dx + dy * dy <= sw * sw:
                            strip_draw.text((pos_x + dx, pos_y + dy), w_str, font=chosen_font, fill=stroke_col)
                            
            # Draw fill text
            strip_draw.text((pos_x, pos_y), w_str, font=chosen_font, fill=fill_color)
            draw_x += w_w + space_w
            
        # Position on main overlay
        base_y = int(img_h * float(self.style.get("position_ratio", 0.70)))
        center_x = img_w // 2
        center_y = base_y
        
        if abs(rotation_angle) > 0.05:
            # Bicubic rotation with expand
            rotated_strip = strip_img.rotate(rotation_angle, resample=Image.BICUBIC, expand=True)
            rot_w, rot_h = rotated_strip.size
            overlay.paste(rotated_strip, (center_x - rot_w // 2, center_y - rot_h // 2), rotated_strip)
        else:
            overlay.paste(strip_img, (center_x - strip_w // 2, center_y - strip_h // 2), strip_img)
            
        return overlay
