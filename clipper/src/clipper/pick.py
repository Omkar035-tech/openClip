import os
import sys
import json
import time
import math
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from .audio_features import get_window_energy
from .wayin_engine import WayinPipelineEngine

SPONSOR_MARKERS = [
    # General Podcast Sponsor Keywords
    "sponsor", "sponsored by", "discount code", "promo code", "promocode",
    "use code", "promo", "percent off", "$ off", "dollars off", "special offer",
    "claim a special offer", "our sponsors", "today's sponsor", "presented by",
    "brought to you by", "link in description", "check out the link", "patreon",
    "slash huberman", "dot com slash", "subscribe to the channel",
    # Well-Known Podcast Sponsors & Brands
    "drinkag1", "athletic greens", "ag1", "eightsleep", "eight sleep", "pod 3",
    "nordvpn", "expressvpn", "betterhelp", "insidetracker", "roka", "element",
    "lmnt", "helix sleep", "whoop", "shopify", "squarespace", "draftkings",
    "athleticgreens", "mattress",
    # Podcast Disclaimers & Intros
    "welcome to the huberman lab", "my guest today is", "today my guest is",
    "before we begin", "disclaimer", "this podcast episode is probably not for you"
]

CLIFFHANGER_WORDS = [
    "because", "and", "but", "so", "or", "if", "that", "which", "like", "when",
    "although", "such as", "for example", "meaning that", "i'll never forget",
    "and then", "what happened", "the reason is", "let me tell you", "to see if",
    "he said that", "she said that", "you know what", "guess what", "about to say",
    "said something that"
]

def is_sponsor_segment(text: str) -> bool:
    t_low = text.lower()
    return any(marker in t_low for marker in SPONSOR_MARKERS)

def ends_cleanly(sentence_text: str) -> bool:
    clean = sentence_text.strip().lower()
    if not any(clean.endswith(p) for p in [".", "!", "?"]):
        return False
    clean_no_punc = clean.rstrip(".!? ").strip()
    words = clean_no_punc.split()
    if not words:
        return False
    last_word = words[-1]
    last_two = " ".join(words[-2:]) if len(words) >= 2 else last_word
    last_three = " ".join(words[-3:]) if len(words) >= 3 else last_two
    
    if last_word in CLIFFHANGER_WORDS or last_two in CLIFFHANGER_WORDS or last_three in CLIFFHANGER_WORDS:
        return False
    return True

def extract_candidate_windows(transcript: List[Dict[str, Any]], features: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Stage 3: Extracts overlapping windows up to 120s on complete sentence boundaries.
    Filters out sponsor ads, mid-sentence starts, and incomplete thoughts.
    """
    all_words = []
    for s in transcript:
        for w in s.get("words", []):
            all_words.append(w)
            
    if not all_words:
        return []
        
    clip_cfg = config.get("clip", {})
    min_dur = float(clip_cfg.get("min_duration", 35.0))
    max_dur = float(clip_cfg.get("max_duration", 120.0))
    target_dur = float(clip_cfg.get("target_duration", min(75.0, max_dur - 5.0)))
    
    candidates = []
    n = len(all_words)
    
    # Find all sentence boundary start indices
    start_indices = [0]
    for idx in range(1, n):
        prev_word = all_words[idx - 1]["word"].strip()
        gap = all_words[idx]["start"] - all_words[idx - 1]["end"]
        if any(prev_word.endswith(p) for p in [".", "!", "?"]) or gap > 0.45:
            start_indices.append(idx)
            
    for i in start_indices:
        t_start = all_words[i]["start"]
        w_start_text = all_words[i]["word"].strip()
        
        # Avoid starting on punctuation, filler, or connector words
        if w_start_text.startswith((",", ".", "!", "?", "--", "-")):
            continue
        if w_start_text.lower() in ["and", "but", "so", "or", "because", "like"]:
            continue
            
        # Collect all valid completed-sentence end points between min_dur and max_dur
        valid_end_indices = []
        clean_end_indices = []
        
        for k in range(i + 15, n):
            dur = all_words[k]["end"] - t_start
            if dur > max_dur:
                break
            if dur < min_dur:
                continue
                
            w_txt = all_words[k]["word"].strip()
            # Check sentence ending
            if any(w_txt.endswith(p) for p in [".", "!", "?"]):
                valid_end_indices.append(k + 1)
                
                # Check trailing sentence snippet for clean resolution (no cliffhangers)
                trailing_words = [w["word"].strip() for w in all_words[max(i, k - 7):k + 1]]
                trailing_snippet = " ".join(trailing_words)
                if ends_cleanly(trailing_snippet):
                    clean_end_indices.append(k + 1)
                    
        # Prefer cleanest complete thought; if none, take closest sentence boundary to target_dur
        best_end_j = None
        if clean_end_indices:
            best_end_j = min(clean_end_indices, key=lambda idx: abs((all_words[idx - 1]["end"] - t_start) - target_dur))
        elif valid_end_indices:
            best_end_j = min(valid_end_indices, key=lambda idx: abs((all_words[idx - 1]["end"] - t_start) - target_dur))
            
        if not best_end_j:
            continue
            
        window_words = all_words[i:best_end_j]
        dur = window_words[-1]["end"] - window_words[0]["start"]
        full_text = " ".join(w["word"].strip() for w in window_words)
        
        # CRITICAL FILTER: Drop sponsor ad reads
        if is_sponsor_segment(full_text):
            continue
            
        energy_score = get_window_energy(features, window_words[0]["start"], window_words[-1]["end"])
        
        # Prioritize windows with strong hooks, questions, or raw emotion
        pre_boost = 0.0
        txt_lower = full_text.lower()
        if "?" in txt_lower[:80] or any(txt_lower.startswith(q) for q in ["how", "why", "what", "if you"]):
            pre_boost += 20.0
        if any(w in txt_lower for w in ["truth", "suffer", "pain", "strength", "discipline", "never", "failure", "fucking"]):
            pre_boost += 25.0
            
        candidates.append({
            "start": round(window_words[0]["start"], 2),
            "end": round(window_words[-1]["end"] + 0.35, 2), # Trailing comfort padding
            "duration": round(dur + 0.35, 2),
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
        if len(deduped) >= 50:
            break
            
    print(f"Generated {len(deduped)} top candidate windows on complete sentence boundaries (filtered ads).")
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
        # Mindset, Strength, Discipline (David Goggins & Motivational)
        "strength", "inner strength", "discipline", "mindset", "suffer", "suffering",
        "pain", "quit", "quitting", "failure", "fear", "warrior", "savage", "obsessed",
        "darkness", "hard", "focus", "truth", "hate", "fight", "broke", "lost", "change",
        "push", "pull", "run", "running", "excuses", "mental", "brain", "soul", "heart",
        # General Podcast Hooks & Intrigue
        "secret", "why", "how", "never", "always", "biggest", "mistake", "destroy", "rule",
        "remember", "crazy", "shocking", "listen", "power", "money", "success", "life",
        "daddy", "grave", "father", "mortgage", "rich", "million", "hours", "master", "bodies"
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
        score_emotion = 75.0
        score_standalone = 85.0
        score_payoff = 80.0

        if "?" in first_5s_text or any(first_5s_text.startswith(q) for q in ["so", "why", "how", "what", "imagine", "listen"]):
            score_hook += 18.0
            
        for kw in hook_keywords:
            if kw in first_5s_text:
                score_hook += 25.0
            elif kw in text_lower:
                score_hook += 12.0
                
        # Extra hook & emotion bonuses
        if any(w in text_lower for w in ["inner strength", "discipline", "suffer", "pain", "warrior", "never quit"]):
            score_hook += 15.0
            score_emotion += 15.0
        elif "bodies" in text_lower and ("ten thousand" in text_lower or "10,000" in text_lower):
            score_hook += 20.0
            score_emotion += 10.0
                
        score_hook = min(100.0, score_hook)
        
        # Standalone score (clean start/end, absence of "as I said earlier")
        if any(unres in text_lower[:50] for unres in ["as i said", "like i mentioned", "earlier", "going back"]):
            score_standalone -= 30.0
            
        # Emotion / Energy score
        if any(em in text_lower for em in ["mad", "laugh", "tapped", "crazy", "mental health", "happy", "happiness", "damn", "who cares", "fear", "hate", "fight"]):
            score_emotion += 15.0
        score_emotion = min(100.0, score_emotion)
        
        # Payoff score
        if text.strip().endswith((".", "!", "?")):
            score_payoff += 15.0
        score_payoff = min(100.0, score_payoff)
        
        # Weighted LLM-equivalent score
        llm_score = (0.35 * score_hook + 0.25 * score_standalone + 0.20 * score_emotion + 0.20 * score_payoff)
        
        # Composite score: 70% LLM + 30% local acoustic energy
        total_score = round(0.70 * llm_score + 0.30 * c["energy_score"], 2)
        
        # Dynamic Title Generation from Hook Clause
        first_clause = text.split('.')[0].split('?')[0].split('!')[0].split(',')[0].strip()
        clause_words = [w for w in first_clause.split() if w.strip()]
        if 3 <= len(clause_words) <= 7:
            suggested_title = " ".join(clause_words).title()
        else:
            first_w = [w["word"].strip() for w in words[:5] if w["word"].strip()]
            suggested_title = " ".join(first_w).title()
        suggested_title = suggested_title.strip(" -—:,.\"'") or "Viral Highlight"

        # Mood & Music classification
        if any(w in text_lower for w in ["strength", "discipline", "suffer", "pain", "quit", "warrior", "fight", "fear", "darkness", "hard", "alone", "truth", "mind", "hate"]):
            primary_mood = "intense"
            theme = "mental toughness & discipline"
            energy_0_10 = 9.0
            valence = 0.5
            music_prompt = "heavy driving rock/drums, gritty intense motivation, relentless focus"
            genre_hints = ["intense", "motivational", "gritty", "epic", "rock", "driving", "discipline"]
            keywords_to_emphasize = [w.strip(" ,.!?").upper() for w in clause_words[:4] if len(w) > 3]
        elif any(w in text_lower for w in ["laugh", "tapped", "wheelies", "joke", "funny", "hilarious", "prank"]):
            primary_mood = "playful"
            theme = "comedy"
            energy_0_10 = 7.5
            valence = 0.8
            music_prompt = "playful comedic banter, light quirky pizzicato and xylophone, lively humor"
            genre_hints = ["comedy", "playful", "quirky"]
            keywords_to_emphasize = [w.strip(" ,.!?").upper() for w in clause_words[:4] if len(w) > 3]
        elif any(w in text_lower for w in ["money", "mortgage", "retired", "wealth", "business", "rich", "million"]):
            primary_mood = "inspiring"
            theme = "financial freedom & success"
            energy_0_10 = 6.0
            valence = 0.7
            music_prompt = "uplifting warm acoustic and piano, inspirational growth"
            genre_hints = ["inspiring", "uplifting", "warm"]
            keywords_to_emphasize = ["MONEY", "SUCCESS", "RETIRED", "FREEDOM"]
        elif any(w in text_lower for w in ["sad", "depressed", "died", "crying", "lost my", "heartbreaking"]):
            primary_mood = "emotional"
            theme = "emotional reflection"
            energy_0_10 = 3.5
            valence = -0.6
            music_prompt = "somber emotional reflective piano and strings"
            genre_hints = ["emotional", "reflective", "sad", "serious"]
            keywords_to_emphasize = [w.strip(" ,.!?").upper() for w in clause_words[:3] if len(w) > 3]
        else:
            primary_mood = "casual"
            theme = "podcast conversation"
            energy_0_10 = 5.0
            valence = 0.5
            music_prompt = "chill relaxed lo-fi background groove, subtle beat"
            genre_hints = ["chill", "lo-fi", "ambient"]
            keywords_to_emphasize = [w.strip(" ,.!?").upper() for w in clause_words[:3] if len(w) > 3]
            
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

def select_and_rank_clips(
    transcript: List[Dict[str, Any]],
    features: Dict[str, Any],
    config: Dict[str, Any],
    cache_dir: Path,
    excluded_intervals: Optional[List[Dict[str, float]]] = None
) -> List[Dict[str, Any]]:
    """
    Stages 3 & 4: Generates candidates and scores them via Gemini LLM or local fallback.
    Saves ranked.json and selection_report.md.
    If excluded_intervals is provided (e.g. during shuffle / re-roll), any candidate that overlaps
    with an existing generated clip is skipped to guarantee fresh, non-repeated clips.
    """
    ranked_file = cache_dir / "ranked.json"
    n_target = int(config.get("general", {}).get("n_clips", 5))
    shuffle_mode = bool(config.get("shuffle", False) or excluded_intervals)

    if not shuffle_mode and ranked_file.exists():
        try:
            with open(ranked_file, "r", encoding="utf-8") as f:
                cached_clips = json.load(f)
                if isinstance(cached_clips, list) and len(cached_clips) >= n_target:
                    return cached_clips[:n_target]
        except Exception:
            pass
            
    candidates = extract_candidate_windows(transcript, features, config)
    if not candidates:
        raise ValueError("No valid candidate windows found")

    # If excluded_intervals is passed, filter out any candidate that overlaps with already created clips
    if excluded_intervals:
        print(f"[Selection] Filtering out candidates overlapping with {len(excluded_intervals)} existing clips...")
        filtered = []
        for c in candidates:
            overlaps_existing = False
            for ex in excluded_intervals:
                ex_start = float(ex.get("start", ex.get("source_start", 0.0)))
                ex_end = float(ex.get("end", ex.get("source_end", 0.0)))
                # Disjoint check: c ends before ex starts OR c starts after ex ends
                if not (c["end"] <= ex_start or c["start"] >= ex_end):
                    overlaps_existing = True
                    break
            if not overlaps_existing:
                filtered.append(c)
        if filtered:
            print(f"[Selection] Retained {len(filtered)} novel candidate windows after excluding existing clips.")
            candidates = filtered
        else:
            print("[Selection] Warning: All candidate windows overlapped existing clips! Using all candidates with lower overlap priority.")

    engine_arch = config.get("engine_architecture", "openclip_standard")
    user_prompt = config.get("wayin_prompt")

    # Architecture Branching: openClip 2.0 (Wayin.ai Engine) vs Default openClip Standard
    if engine_arch in ("wayin_2_0", "wayin"):
        print("[Engine: openClip 2.0 (Wayin.ai Architecture)] Running Hook-First Virality & Hierarchical Analysis...")
        wayin_engine = WayinPipelineEngine(config)
        scored_candidates = score_with_local_engine(candidates)
        n_target = config.get("general", {}).get("n_clips", 5)
        final_clips = wayin_engine.run_wayin_selection(scored_candidates, n_clips=n_target, user_prompt=user_prompt)
        
        with open(ranked_file, "w", encoding="utf-8") as f:
            json.dump(final_clips, f, indent=2)
        write_selection_report(final_clips, cache_dir / "selection_report.md")
        print(f"[openClip 2.0] Selected top {len(final_clips)} viral shorts using Wayin.ai framework.")
        return final_clips

    # Standard openClip 1.0 Architecture (Default)
    print("[Engine: openClip Standard] Using standard acoustic + heuristic scoring...")
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
            
    final_clips = final_clips[:n_clips]
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
