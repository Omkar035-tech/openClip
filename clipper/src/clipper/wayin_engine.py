"""
openClip 2.0 (Beta) - Wayin.ai Hierarchical Architecture Engine
Key Features:
1. Target Slicing: Only decodes chosen clips, not the whole video.
2. Hook-First Virality Scoring (First 1-3 seconds evaluation).
3. Speech Velocity & Acoustic Saliency (syllable rate + energy bursts).
4. Gemini Flash Reasoning integration with graceful local fallback.
5. Natural Language Prompt ("Find Moments") support.
"""

import os
import sys
import json
import time
import math
from pathlib import Path
from typing import Dict, List, Any, Optional

class WayinPipelineEngine:
    """
    Implements the Wayin.ai hierarchical funnel for viral moment detection:
    - Funnel 1: Fast O(1) Audio Energy & Speech Velocity Saliency
    - Funnel 2: Strict Sentence & Complete Micro-Narrative Windowing
    - Funnel 3: First 3-Second Hook-First Scoring & Retention Saliency
    - Funnel 4: Gemini Flash Multimodal Reasoning with JSON Structured Output
    """

    VIRAL_HOOK_TRIGGERS = [
        "the real reason", "nobody talks about", "secret to", "truth about",
        "here is what happened", "biggest mistake", "never do this", "stop doing",
        "why you should never", "changed my life", "i realized", "listen to me",
        "imagine if", "what if i told you", "how i made", "how to build",
        "insane", "crazy", "shocking", "unbelievable", "mind blowing"
    ]

    NEGATIVE_LEAD_IN_FLUFF = [
        "so basically", "like i was saying", "moving on", "as i mentioned earlier",
        "to be honest with you guys", "um yeah so", "anyway back to", "in this part of"
    ]

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    def score_first_3_seconds(self, words: List[Dict[str, Any]], t_start: float) -> Dict[str, Any]:
        """
        Wayin.ai Hook-First Evaluation:
        Scrutinizes the first 1-3 seconds for pattern interrupts, questions, and curiosity gaps.
        """
        lead_words = [w for w in words if (w.get("end", 0.0) - t_start) <= 3.2]
        lead_text = " ".join(w.get("word", "").strip() for w in lead_words).lower()

        hook_score = 65.0
        # 1. Immediate question or curiosity gap
        if "?" in lead_text or any(lead_text.startswith(q) for q in ["why", "how", "what if", "have you ever", "imagine"]):
            hook_score += 18.0

        # 2. Viral hook pattern triggers
        for trigger in self.VIRAL_HOOK_TRIGGERS:
            if trigger in lead_text:
                hook_score += 22.0
                break

        # 3. Penalize conversational fluff lead-ins
        for fluff in self.NEGATIVE_LEAD_IN_FLUFF:
            if fluff in lead_text:
                hook_score -= 25.0
                break

        return {
            "hook_text": lead_text,
            "hook_score": min(99.0, max(20.0, hook_score))
        }

    def compute_speech_velocity(self, words: List[Dict[str, Any]], duration: float) -> float:
        """Calculates syllables/words per second. Spikes indicate excitement, punchlines, or debate."""
        if duration <= 0:
            return 0.0
        wps = len(words) / duration
        # Ideal viral cadence is 2.5 - 3.8 words per second
        if 2.2 <= wps <= 4.0:
            return 88.0
        elif wps > 4.0:
            return 78.0 # Very fast
        else:
            return 60.0 # Slow/monotone

    def select_with_gemini(
        self,
        candidates: List[Dict[str, Any]],
        n_clips: int = 5,
        user_prompt: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Single-shot batched Gemini Flash prompt for viral ranking and micro-narrative validation.
        """
        if not self.gemini_key:
            return None

        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)

            # Package top candidate metadata for LLM evaluation
            condensed = []
            for idx, c in enumerate(candidates[:14], 1):
                condensed.append({
                    "id": idx,
                    "start": c["start"],
                    "end": c["end"],
                    "duration": c["duration"],
                    "hook_3s": c["hook_eval"]["hook_text"],
                    "text": c["text"]
                })

            prompt_text = f"""You are the Wayin.ai viral shorts clipping engine.
Evaluate these candidate clips extracted from a video transcript.
Select the top {n_clips} clips that will achieve the highest retention on TikTok, YouTube Shorts, and Instagram Reels.

EVALUATION CRITERIA:
1. Hook Strength (40%): Does the first 2-3 seconds stop the scroll with an intriguing premise, curiosity gap, or bold statement?
2. Narrative Completeness (30%): Does the clip tell a self-contained story or point with a clear punchline / conclusion?
3. Emotional Engagement (30%): Is the content funny, shocking, educational, or motivational?
{f'USER FOCUS PROMPT: {user_prompt}' if user_prompt else ''}

Return ONLY valid JSON in this exact structure:
{{
  "selected_clips": [
    {{
      "candidate_id": 1,
      "viral_title": "Catchy YouTube Shorts Title",
      "hook_score": 94,
      "virality_score": 91,
      "primary_mood": "intense",
      "key_punchline": "The exact climax punchline quote",
      "selection_reason": "High curiosity hook in opening 2 seconds with clean resolution"
    }}
  ]
}}

CANDIDATES:
{json.dumps(condensed, indent=1)}
"""
            # Try model fallback chain
            models_to_try = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
            res = None
            for m in models_to_try:
                try:
                    res = client.models.generate_content(model=m, contents=prompt_text)
                    if res and res.text:
                        break
                except Exception:
                    continue

            if not res or not res.text:
                return None

            clean_json = res.text.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0].strip()

            parsed = json.loads(clean_json)
            selected = parsed.get("selected_clips", [])

            results = []
            id_map = {idx: c for idx, c in enumerate(candidates[:14], 1)}

            for item in selected:
                cid = item.get("candidate_id")
                if cid in id_map:
                    base = dict(id_map[cid])
                    base["suggested_title"] = item.get("viral_title", base["suggested_title"])
                    base["score_hook"] = float(item.get("hook_score", base["score_hook"]))
                    base["score_total"] = float(item.get("virality_score", base["score_total"]))
                    base["reason"] = item.get("selection_reason", base["reason"])
                    if "primary_mood" in item:
                        base["mood"]["primary_mood"] = item["primary_mood"]
                    results.append(base)

            return results if results else None

        except Exception as e:
            print(f"[Wayin Engine] Gemini selection notice: {e}. Utilizing Wayin local multi-factor scoring.")
            return None

    def run_wayin_selection(
        self,
        candidates: List[Dict[str, Any]],
        n_clips: int = 5,
        user_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes Wayin.ai viral selection pipeline:
        1. Evaluates 1-3 second hook strength on all candidates.
        2. Computes speech velocity & emotional density.
        3. Attempts Gemini reasoning ranking.
        4. Smoothly falls back to Wayin mathematical scoring if offline.
        """
        enriched = []
        for c in candidates:
            hook_eval = self.score_first_3_seconds(c["words"], c["start"])
            velocity_score = self.compute_speech_velocity(c["words"], c["duration"])

            # Wayin Multi-Factor Virality Composite Score:
            # 40% Hook + 25% Standalone + 20% Emotion/Acoustic Energy + 15% Speech Cadence
            hook_score = hook_eval["hook_score"]
            acoustic_energy = c.get("energy_score", 70.0)

            virality_score = round(
                0.40 * hook_score +
                0.25 * c.get("score_standalone", 80.0) +
                0.20 * acoustic_energy +
                0.15 * velocity_score,
                1
            )

            c_copy = dict(c)
            c_copy["hook_eval"] = hook_eval
            c_copy["score_hook"] = hook_score
            c_copy["score_total"] = virality_score
            c_copy["architecture"] = "openClip 2.0 (Wayin.ai Engine)"
            enriched.append(c_copy)

        enriched.sort(key=lambda x: x["score_total"], reverse=True)

        # Attempt Gemini Flash multimodal virality selection
        gemini_selected = self.select_with_gemini(enriched, n_clips=n_clips, user_prompt=user_prompt)
        if gemini_selected and len(gemini_selected) >= 1:
            return gemini_selected[:n_clips]

        # Non-overlapping top selection
        final_clips = []
        for c in enriched:
            overlap = False
            for s in final_clips:
                if not (c["end"] <= s["start"] or c["start"] >= s["end"]):
                    overlap = True
                    break
            if not overlap:
                final_clips.append(c)
            if len(final_clips) == n_clips:
                break

        return final_clips
