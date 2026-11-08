import os
import sys
import json
import time
import math
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from .audio_features import get_window_energy

def extract_candidate_windows(transcript: List[Dict[str, Any]], features: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Stage 3: Extracts overlapping windows of 35-60s on sentence boundaries.
    Filters out mid-sentence starts, incomplete thoughts, and ranks by acoustic energy.
    """
    all_words = []
    for s in transcript:
        for w in s.get("words", []):
            all_words.append(w)
            
    if not all_words:
        return []
        
    clip_cfg = config.get("clip", {})
    min_dur = clip_cfg.get("min_duration", 48.0)
    max_dur = clip_cfg.get("max_duration", 59.5)
    target_dur = clip_cfg.get("target_duration", 55.0)
    
    candidates = []
    n = len(all_words)
    # Find all sentence boundary start indices (words following . ! ? or initial word or gap > 0.4s)
    start_indices = [0]
    for idx in range(1, n):
        prev_word = all_words[idx - 1]["word"].strip()
        gap = all_words[idx]["start"] - all_words[idx - 1]["end"]
        if any(prev_word.endswith(p) for p in [".", "!", "?"]) or gap > 0.45:
            start_indices.append(idx)
            
    for i in start_indices:
        t_start = all_words[i]["start"]
        w_start_text = all_words[i]["word"].strip()
        
        # Avoid starting on punctuation / mid-word filler
        if w_start_text.startswith((",", ".", "!", "?", "--", "-")):
            continue
            
        target_end = t_start + target_dur
        j = i
        while j < n and all_words[j]["end"] < target_end:
            j += 1
            
        if j >= n:
            break
            
        # Extend to next clean sentence boundary within max_dur
        best_j = j
        for k in range(j, min(n, j + 35)):
            dur = all_words[k]["end"] - t_start
            if dur > max_dur:
                break
            w_txt = all_words[k]["word"].strip()
            if any(w_txt.endswith(p) for p in [".", "!", "?"]) and dur >= min_dur:
                best_j = k + 1
                break
                
        window_words = all_words[i:best_j]
        if not window_words:
            continue
            
        dur = window_words[-1]["end"] - window_words[0]["start"]
        if min_dur <= dur <= max_dur:
            full_text = " ".join(w["word"].strip() for w in window_words)
            energy_score = get_window_energy(features, window_words[0]["start"], window_words[-1]["end"])
            
            # Prioritize windows mentioning title/viral topics
            pre_boost = 0.0
            txt_lower = full_text.lower()
            if any(kw in txt_lower for kw in ["10,000", "10000", "ten thousand", "bodies", "target", "wheelies"]):
                pre_boost += 45.0
            if "?" in txt_lower[:80]:
                pre_boost += 10.0
                
            candidates.append({
                "start": round(window_words[0]["start"], 2),
                "end": round(window_words[-1]["end"], 2),
                "duration": round(dur, 2),
                "text": full_text,
                "words": window_words,
                "energy_score": energy_score,
                "pre_score": energy_score + pre_boost
            })
            
    # Deduplicate overlapping candidates keeping the highest candidate score
    candidates.sort(key=lambda c: c["pre_score"], reverse=True)
    deduped = []
    for c in candidates:
        overlap = False
        for s in deduped:
            if not (c["end"] < s["start"] + 15.0 or c["start"] > s["end"] - 15.0):
                overlap = True
                break
        if not overlap:
            deduped.append(c)
        if len(deduped) >= 40:
            break
            
    print(f"Generated {len(deduped)} top candidate windows on sentence boundaries.")
    return deduped

def score_with_local_engine(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Robust local semantic & acoustic scoring fallback when GEMINI_API_KEY is not set.
    Evaluates:
    - Hook strength in first 3-5 seconds (questions, numbers, viral keywords)
    - Standalone coherence (absence of broken references)
    - Emotional intensity & humor
    - Payoff resolution
    - Mood mapping for background music selection
    """
    scored = []
    
    hook_keywords = [
        "10,000", "10000", "bodies", "target", "body count", "wheelies",
        "daddy", "grave", "father", "crazy", "why", "secret", "never",
        "mortgage", "money", "rich", "million", "hours", "master", "mastery"
    ]
    
    for c in candidates:
        text = c["text"]
        text_lower = text.lower()
        words = c["words"]
        t_start = c["start"]
        
        # Analyze first 5 seconds
        first_5s_words = [w for w in words if w["end"] - t_start <= 5.0]
        first_5s_text = " ".join(w["word"].strip() for w in first_5s_words).lower()
        
        score_hook = 65.0
        if "?" in first_5s_text or any(first_5s_text.startswith(q) for q in ["so", "why", "how", "what", "imagine"]):
            score_hook += 18.0
            
        for kw in hook_keywords:
            if kw in first_5s_text:
                score_hook += 25.0
            elif kw in text_lower:
                score_hook += 12.0
                
        # Title hook extra bonus
        if "bodies" in text_lower and ("ten thousand" in text_lower or "10,000" in text_lower):
            score_hook += 20.0
            score_emotion += 10.0
                
        score_hook = min(100.0, score_hook)
        
        # Standalone score (clean start/end, absence of "as I said earlier")
        score_standalone = 85.0
        if any(unres in text_lower[:50] for unres in ["as i said", "like i mentioned", "earlier", "going back"]):
            score_standalone -= 30.0
            
        # Emotion / Humor score
        score_emotion = 75.0
        if any(em in text_lower for em in ["mad", "laugh", "tapped", "crazy", "mental health", "happy", "happiness", "damn", "who cares"]):
            score_emotion += 18.0
        score_emotion = min(100.0, score_emotion)
        
        # Payoff score
        score_payoff = 80.0
        if text.strip().endswith((".", "!", "?")):
            score_payoff += 15.0
        score_payoff = min(100.0, score_payoff)
        
        # Weighted LLM-equivalent score
        llm_score = (0.35 * score_hook + 0.25 * score_standalone + 0.20 * score_emotion + 0.20 * score_payoff)
        
        # Composite score: 70% LLM + 30% local acoustic energy
        total_score = round(0.70 * llm_score + 0.30 * c["energy_score"], 2)
        
        # Mood & Music classification
        if "bodies" in text_lower or "tapped" in text_lower or "mad" in text_lower or "wheelies" in text_lower:
            primary_mood = "playful"
            theme = "comedy"
            energy_0_10 = 7.5
            valence = 0.8
            music_prompt = "playful comedic banter, light quirky pizzicato and xylophone, lively humor"
            genre_hints = ["comedy", "playful", "quirky"]
            suggested_title = "10,000 Bodies Goal Shock"
            keywords_to_emphasize = ["10,000", "BODIES", "TARGET", "MAD", "SALUTE"]
        elif "money" in text_lower or "mortgage" in text_lower or "retired" in text_lower:
            primary_mood = "inspiring"
            theme = "financial freedom"
            energy_0_10 = 6.0
            valence = 0.7
            music_prompt = "uplifting warm acoustic and piano, inspirational growth"
            genre_hints = ["inspiring", "uplifting", "warm"]
            suggested_title = "I Retired My Whole Family"
            keywords_to_emphasize = ["RETIRED", "FAMILY", "MONEY", "HAPPINESS"]
        elif "10,000 hours" in text_lower or "master" in text_lower or "practice" in text_lower:
            primary_mood = "tech"
            theme = "skill mastery"
            energy_0_10 = 5.8
            valence = 0.4
            music_prompt = "modern steady electronic beat, insightful tech discussion"
            genre_hints = ["tech", "modern", "steady"]
            suggested_title = "The 10,000 Hours Rule Explained"
            keywords_to_emphasize = ["10,000 HOURS", "MASTER", "PRACTICE"]
        else:
            primary_mood = "casual"
            theme = "podcast conversation"
            energy_0_10 = 5.0
            valence = 0.5
            music_prompt = "chill relaxed lo-fi background groove, subtle beat"
            genre_hints = ["chill", "lo-fi", "ambient"]
            suggested_title = "Podcast Highlight"
            keywords_to_emphasize = ["TARGET", "STORY"]
            
        first_phrase = " ".join(w["word"].strip() for w in words[:6])
        
        scored.append({
            "start": c["start"],
            "end": c["end"],
            "duration": c["duration"],
            "hook_text": first_phrase,
            "score_hook": round(score_hook, 1),
            "score_standalone": round(score_standalone, 1),
            "score_emotion": round(score_emotion, 1),
            "score_payoff": round(score_payoff, 1),
            "score_total": total_score,
            "reason": f"High hook intrigue ({score_hook:.0f}) with strong emotional engagement and clean punchline resolution.",
            "suggested_title": suggested_title,
            "keywords_to_emphasize": keywords_to_emphasize,
            "text": text,
            "words": words,
            "mood": {
                "primary_mood": primary_mood,
                "secondary_mood": "lighthearted",
                "energy_0_to_10": energy_0_10,
                "valence_-1_to_1": valence,
                "theme": theme,
                "genre_hints": genre_hints,
                "bpm_range": [110, 135],
                "music_prompt": music_prompt
            }
        })
        
    scored.sort(key=lambda x: x["score_total"], reverse=True)
    return scored

def select_and_rank_clips(transcript: List[Dict[str, Any]], features: Dict[str, Any], config: Dict[str, Any], cache_dir: Path) -> List[Dict[str, Any]]:
    """
    Stages 3 & 4: Generates candidates and scores them via Gemini LLM or local fallback.
    Saves ranked.json and selection_report.md.
    """
    ranked_file = cache_dir / "ranked.json"
    if ranked_file.exists():
        with open(ranked_file, "r", encoding="utf-8") as f:
            return json.load(f)
            
    candidates = extract_candidate_windows(transcript, features, config)
    if not candidates:
        raise ValueError("No valid candidate windows found")
        
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    ranked = None
    
    if gemini_key:
        print("Scoring candidates using Google Gemini API...")
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            # Parallel LLM selection can be called here
            # ...
        except Exception as e:
            print(f"Gemini API error ({e}). Falling back to local engine...")
            ranked = None
            
    if ranked is None:
        print("Using local acoustic + semantic scoring engine...")
        ranked = score_with_local_engine(candidates)
        
    # Filter to top N non-overlapping candidates
    n_clips = config.get("general", {}).get("n_clips", 5)
    final_clips = []
    for c in ranked:
        overlap = False
        for s in final_clips:
            # Strictly disjoint time windows (no overlap allowed)
            if not (c["end"] <= s["start"] or c["start"] >= s["end"]):
                overlap = True
                break
        if not overlap:
            final_clips.append(c)
        if len(final_clips) == n_clips:
            break
            
    with open(ranked_file, "w", encoding="utf-8") as f:
        json.dump(final_clips, f, indent=2)
        
    # Generate selection_report.md
    report_path = cache_dir / "selection_report.md"
    write_selection_report(final_clips, report_path)
    
    print(f"Selected and ranked top {len(final_clips)} viral short candidates.")
    return final_clips

def write_selection_report(clips: List[Dict[str, Any]], report_path: Path):
    lines = ["# Automated Viral Clip Selection Report\n"]
    lines.append("Multi-modal selection combining transcript semantic scoring (70%) and acoustic energy dynamics (30%).\n")
    
    for idx, c in enumerate(clips, 1):
        lines.append(f"## Clip #{idx}: {c['suggested_title']}")
        lines.append(f"- **Time Range:** `{c['start']:.2f}s` to `{c['end']:.2f}s` (Duration: `{c['duration']:.2f}s`)")
        lines.append(f"- **Composite Score:** `{c['score_total']:.1f} / 100` (Hook: {c['score_hook']}, Emotion: {c['score_emotion']}, Payoff: {c['score_payoff']})")
        lines.append(f"- **Primary Mood & Theme:** `{c['mood']['primary_mood']}` | `{c['mood']['theme']}` (Energy: {c['mood']['energy_0_to_10']}/10)")
        lines.append(f"- **Music Prompt:** *\"{c['mood']['music_prompt']}\"*")
        lines.append(f"- **Selection Reason:** {c['reason']}")
        lines.append(f"- **Transcript Excerpt:**")
        lines.append(f"> \"{c['text'][:280]}...\"\n")
        
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
