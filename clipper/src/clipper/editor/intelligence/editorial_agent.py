import os
import json
from typing import List, Dict, Any, Optional
from groq import Groq
from google import genai
from clipper.editor.intelligence.validator import sanitize_and_parse_llm_json

class EditorialAgent:
    def __init__(self, provider: str = "groq", model_id: str = "llama-3.3-70b-versatile"):
        self.provider = provider
        self.model_id = model_id
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")

    def evaluate_window(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Sends borderline pauses and context to Groq (or Gemini fallback) to decide
        whether to KEEP (suspense/reaction/thought pause) or CUT (dead air/phone checking).
        """
        prompt = f"""You are a master long-form video editor for {payload.get('content_type', 'general')} videos.
Review the dialogue context and candidate pauses below. 
Decide whether each pause should be 'CUT' (boring dead air, awkward silence, inactivity) or 'KEEP' (suspenseful pause, reaction, natural comedic timing, dramatic breath, setup).

DIALOGUE CONTEXT:
"{payload.get('dialogue_summary', '')}"

CANDIDATE PAUSES TO EVALUATE:
{json.dumps(payload.get('candidate_pauses_for_review', []), indent=2)}

Respond with a strictly valid JSON array of decisions:
[
  {{
    "start": 12.4,
    "end": 18.2,
    "action": "KEEP",
    "confidence": 0.95,
    "reason": "Suspenseful horror reaction before scream",
    "tags": ["suspense", "reaction"]
  }}
]
"""
        # Try Groq Cloud first if key exists
        if self.provider == "groq" and self.groq_key:
            try:
                client = Groq(api_key=self.groq_key)
                resp = client.chat.completions.create(
                    model=self.model_id,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=1024
                )
                text = resp.choices[0].message.content or ""
                decisions = sanitize_and_parse_llm_json(text)
                if decisions:
                    return decisions
            except Exception as e:
                print(f"[EditorialAgent] Groq attempt failed ({e}), trying Gemini fallback...")

        # Fallback to Gemini if available
        if self.gemini_key:
            try:
                client = genai.Client(api_key=self.gemini_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                text = response.text or ""
                return sanitize_and_parse_llm_json(text)
            except Exception as e:
                print(f"[EditorialAgent] Gemini fallback failed: {e}")

        # Deterministic editorial heuristic fallback (if no API keys configured)
        fallback_decisions = []
        for p in payload.get("candidate_pauses_for_review", []):
            dur = p.get("duration", 0.0)
            action = "CUT" if dur > 2.5 else "KEEP"
            reason = f"Dead air pause ({dur}s)" if action == "CUT" else "Natural cadence pause"
            fallback_decisions.append({
                "start": p["start"],
                "end": p["end"],
                "action": action,
                "confidence": 0.80,
                "reason": reason,
                "tags": ["vad_heuristic"]
            })
        return fallback_decisions
