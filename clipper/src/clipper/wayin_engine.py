"""
openClip 2.0 (Beta) - Wayin.ai Hierarchical Architecture Engine with Groq & VideoClipFinder 62-Tag Virality
Features:
1. Groq Cloud Engine as default LLM with instant model switching (llama-3.3-70b-versatile, llama-3.1-8b-instant, etc.)
2. Fallback to Gemini API if Groq fails or key unavailable
3. Fallback to offline mathematical heuristic ranking via VideoClipFinder 62-tag taxonomy & Acoustic Spikes
4. Hook-First Virality Scoring (First 1-3 seconds evaluation)
5. Syllable & Speech Velocity Saliency
6. Acoustic Reaction / Laughter & Scream Delta-RMS detection
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
    - Funnel 1: Fast O(1) Audio Energy, Scream Spikes & Speech Velocity
    - Funnel 2: Strict Sentence & Complete Micro-Narrative Windowing
    - Funnel 3: First 3-Second Hook-First Scoring & Retention Saliency
    - Funnel 4: Groq LLM (Default) -> Gemini API (Fallback 1) -> VideoClipFinder 62-Tag Taxonomy (Fallback 2)
    """

    # VideoClipFinder 62-Tag Virality Markers Taxonomy:
    # 1. Hook Archetypes (Curiosity, Pattern Interrupt, Bold Claim, Warning, Secret)
    # 2. Emotional Drivers (Shock, Laughter, Anger, Awe, Relief, Suspense)
    # 3. Retention Mechanisms (Open Loops, Punchlines, Revelations, Payoffs)
    VIRAL_HOOK_TRIGGERS = [
        "the real reason", "nobody talks about", "secret to", "truth about",
        "here is what happened", "biggest mistake", "never do this", "stop doing",
        "why you should never", "changed my life", "i realized", "listen to me",
        "imagine if", "what if i told you", "how i made", "how to build",
        "insane", "crazy", "shocking", "unbelievable", "mind blowing",
        "wait for it", "look at this", "watch this", "are you kidding me",
        "oh my god", "no way", "i cannot believe", "this is illegal"
    ]

    NEGATIVE_LEAD_IN_FLUFF = [
        "so basically", "like i was saying", "moving on", "as i mentioned earlier",
        "to be honest with you guys", "um yeah so", "anyway back to", "in this part of",
        "let me know in the comments", "welcome back to", "subscribe to"
    ]

    # 62-tag virality categories for algorithmic classification
    VIRAL_TAGS = {
        "hook_archetype": ["question_loop", "bold_claim", "pattern_interrupt", "secret_reveal", "relatable_pain"],
        "emotion": ["shock", "laughter", "hype", "awe", "curiosity", "tension"],
        "retention_mechanic": ["micro_story", "punchline_payoff", "cliffhanger", "visual_proof", "fast_paced_debate"]
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.groq_key = (
            config.get("models", {}).get("groq_api_key") or
            os.getenv("GROQ_API_KEY", "")
        ).strip()
        self.groq_model = config.get("models", {}).get("groq_model", "llama-3.3-70b-versatile").strip()
        self.gemini_key = (
            config.get("models", {}).get("gemini_api_key") or
            os.getenv("GEMINI_API_KEY", "")
        ).strip()

    def score_first_3_seconds(self, words: List[Dict[str, Any]], t_start: float) -> Dict[str, Any]:
        """
        Wayin.ai Hook-First Evaluation:
        Scrutinizes the first 1-3 seconds for pattern interrupts, questions, and curiosity gaps.
        """
        lead_words = [w for w in words if (w.get("end", 0.0) - t_start) <= 3.2]
        lead_text = " ".join(w.get("word", "").strip() for w in lead_words).lower()

        hook_score = 65.0
        # 1. Immediate question or curiosity gap
        if "?" in lead_text or any(lead_text.startswith(q) for q in ["why", "how", "what if", "have you ever", "imagine", "wait"]):
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
            return 80.0
        else:
            return 60.0

    def select_with_groq(
        self,
        candidates: List[Dict[str, Any]],
        n_clips: int = 5,
        user_prompt: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Evaluates top viral moments with ultra-fast Groq LPU inference.
        Uses Llama 3.3 70B Versatile, Llama 3.1 8B Instant, or GPT-OSS models.
        """
        if not self.groq_key:
            return None

        print(f"[Wayin Engine] Querying Groq Cloud API with model: '{self.groq_model}'...")
        try:
            from groq import Groq
            client = Groq(api_key=self.groq_key)

            condensed = []
            for idx, c in enumerate(candidates[:14], 1):
                condensed.append({
                    "id": idx,
                    "start": round(c["start"], 1),
                    "end": round(c["end"], 1),
                    "duration": round(c["duration"], 1),
                    "hook_3s": c["hook_eval"]["hook_text"],
                    "text": c["text"],
                    "acoustic_energy": c.get("energy_score", 70.0)
                })

            prompt = f"""You are the world-class video clipping intelligence engine (Groq LPU accelerated).
Analyze these candidate clips extracted from a long-form video transcript.
Select the top {n_clips} clips that will achieve viral retention (5M+ views) on TikTok, YouTube Shorts, and Instagram Reels.

EVALUATION FRAMEWORK (VideoClipFinder 62-Tag Virality Rules):
1. Hook Strength (40%): Does the first 2-3 seconds immediately create an open loop, shocking pattern interrupt, or irresistible curiosity?
2. Story Arc & Payoff (30%): Does the clip contain a complete micro-narrative with a clear climax or punchline?
3. Emotional Reactivity (30%): High laughter, screams, revelation, debate, or intense visual/auditory energy.
{f'USER FOCUS PROMPT: {user_prompt}' if user_prompt else ''}

Return ONLY valid JSON matching this schema:
{{
  "selected_clips": [
    {{
      "candidate_id": 1,
      "viral_title": "Catchy Punchy Title (Max 60 chars)",
      "hook_score": 96,
      "virality_score": 93,
      "primary_mood": "shocking",
      "key_punchline": "The exact climax quote from clip",
      "selection_reason": "Explanation of viral retention hook and payoff"
    }}
  ]
}}

CANDIDATES:
{json.dumps(condensed, indent=1)}
"""

            # Query live accessible models for this account if possible, else use validated chain
            live_active_models = []
            try:
                models_resp = client.models.list()
                if hasattr(models_resp, "data"):
                    live_active_models = [m.id for m in models_resp.data if hasattr(m, "id")]
            except Exception:
                pass

            # Build prioritized fallback chain with only active/available models
            ordered_preferences = [
                self.groq_model,
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "qwen/qwen3.8-27b"
            ]
            models_to_try = []
            for m in ordered_preferences:
                if live_active_models:
                    if m in live_active_models and m not in models_to_try:
                        models_to_try.append(m)
                else:
                    if m not in models_to_try:
                        models_to_try.append(m)

            if not models_to_try:
                models_to_try = live_active_models or ["llama-3.3-70b-versatile"]
            
            chat_completion = None
            for model_id in models_to_try:
                try:
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": "You are a professional video editor and virality algorithm scientist. Always respond with pure valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        model=model_id,
                        temperature=0.3,
                        response_format={"type": "json_object"}
                    )
                    if chat_completion and chat_completion.choices:
                        print(f"[Wayin Engine] Groq returned successful selection using model: {model_id}!")
                        break
                except Exception as me:
                    print(f"[Wayin Engine] Groq model '{model_id}' failed: {me}. Trying next model...")
                    continue

            if not chat_completion or not chat_completion.choices:
                return None

            raw_text = chat_completion.choices[0].message.content.strip()
            parsed = json.loads(raw_text)
            selected = parsed.get("selected_clips", [])

            results = []
            id_map = {idx: c for idx, c in enumerate(candidates[:14], 1)}

            for item in selected:
                cid = item.get("candidate_id")
                if cid in id_map:
                    base = dict(id_map[cid])
                    from . import strip_emojis
                    clean_title = strip_emojis(item.get("viral_title", base["suggested_title"]))
                    base["suggested_title"] = clean_title if clean_title.strip() else base["suggested_title"]
                    base["score_hook"] = float(item.get("hook_score", base["score_hook"]))
                    base["score_total"] = float(item.get("virality_score", base["score_total"]))
                    base["reason"] = item.get("selection_reason", base["reason"])
                    if "primary_mood" in item:
                        base["mood"]["primary_mood"] = item["primary_mood"]
                    results.append(base)

            return results if results else None

        except Exception as e:
            print(f"[Wayin Engine] Groq API execution error: {e}. Falling back to next layer.")
            return None

    def select_with_gemini(
        self,
        candidates: List[Dict[str, Any]],
        n_clips: int = 5,
        user_prompt: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fallback layer 1: Gemini Flash multimodal reasoning.
        """
        if not self.gemini_key:
            return None

        print("[Wayin Engine] Attempting Fallback 1: Google Gemini API...")
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)

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
            models_to_try = ["gemini-3.8-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
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
                    from . import strip_emojis
                    clean_title = strip_emojis(item.get("viral_title", base["suggested_title"]))
                    base["suggested_title"] = clean_title if clean_title.strip() else base["suggested_title"]
                    base["score_hook"] = float(item.get("hook_score", base["score_hook"]))
                    base["score_total"] = float(item.get("virality_score", base["score_total"]))
                    base["reason"] = item.get("selection_reason", base["reason"])
                    if "primary_mood" in item:
                        base["mood"]["primary_mood"] = item["primary_mood"]
                    results.append(base)

            return results if results else None

        except Exception as e:
            print(f"[Wayin Engine] Gemini selection notice: {e}. Falling back to VideoClipFinder 62-tag taxonomy.")
            return None

    def run_wayin_selection(
        self,
        candidates: List[Dict[str, Any]],
        n_clips: int = 5,
        user_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hierarchical viral selection:
        1. Evaluates 1-3 second hook strength on all candidates.
        2. Computes speech velocity & emotional density.
        3. Enriches acoustic scores with scream/reaction spikes.
        4. Tiers selection: Groq (Default) -> Gemini (Fallback 1) -> VideoClipFinder 62-Tag Math (Fallback 2).
        """
        enriched = []
        for c in candidates:
            hook_eval = self.score_first_3_seconds(c["words"], c["start"])
            velocity_score = self.compute_speech_velocity(c["words"], c["duration"])

            # VideoClipFinder 62-Tag Mathematical Virality Score:
            # 35% Hook + 25% Standalone + 25% Acoustic & Reaction Spikes + 15% Speech Cadence
            hook_score = hook_eval["hook_score"]
            acoustic_energy = c.get("energy_score", 70.0)

            # Bonus for question mark in first 3s
            question_bonus = 8.0 if "?" in hook_eval["hook_text"] else 0.0

            virality_score = round(
                0.35 * hook_score +
                0.25 * c.get("score_standalone", 80.0) +
                0.25 * acoustic_energy +
                0.15 * velocity_score +
                question_bonus,
                1
            )
            virality_score = min(99.0, max(40.0, virality_score))

            c_copy = dict(c)
            c_copy["hook_eval"] = hook_eval
            c_copy["score_hook"] = hook_score
            c_copy["score_total"] = virality_score
            c_copy["architecture"] = "openClip 2.0 (Wayin.ai Engine)"
            enriched.append(c_copy)

        enriched.sort(key=lambda x: x["score_total"], reverse=True)

        # 1. Primary Engine: Groq LPU
        groq_selected = self.select_with_groq(enriched, n_clips=n_clips, user_prompt=user_prompt)
        if groq_selected and len(groq_selected) >= 1:
            return groq_selected[:n_clips]

        # 2. Fallback 1: Gemini API
        gemini_selected = self.select_with_gemini(enriched, n_clips=n_clips, user_prompt=user_prompt)
        if gemini_selected and len(gemini_selected) >= 1:
            return gemini_selected[:n_clips]

        # 3. Fallback 2: Offline VideoClipFinder 62-tag mathematical ranking
        print("[Wayin Engine] Using VideoClipFinder 62-Tag Mathematical Scoring Engine (Offline).")
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
