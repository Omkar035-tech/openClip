import json
import re
from typing import List, Dict, Any

def sanitize_and_parse_llm_json(raw_text: str) -> List[Dict[str, Any]]:
    """
    Extracts and validates structured decision array from raw LLM output.
    Ensures start, end, action, and reasoning fields exist and are sanitized.
    """
    cleaned = raw_text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0].strip()
        
    try:
        data = json.loads(cleaned)
    except Exception:
        # Fallback regex extraction if json has trailing commas or formatting flaws
        match = re.search(r"(\[.*\])", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
            except Exception:
                return []
        else:
            return []
            
    decisions = []
    items = data.get("decisions", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
        
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            start = float(item.get("start", 0.0))
            end = float(item.get("end", 0.0))
            action = str(item.get("action", "CUT")).upper().strip()
            if action not in ["KEEP", "CUT", "REVIEW", "EMPHASIZE"]:
                action = "CUT"
            confidence = float(item.get("confidence", 0.85))
            reason = str(item.get("reason", "Editorial assessment"))
            tags = item.get("tags", [])
            if not isinstance(tags, list):
                tags = []
                
            if end > start:
                decisions.append({
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "action": action,
                    "confidence": round(min(1.0, max(0.0, confidence)), 2),
                    "reason": reason,
                    "tags": [str(t) for t in tags]
                })
        except Exception:
            continue
            
    return decisions
