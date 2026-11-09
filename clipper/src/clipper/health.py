import os
import sys
import json
import urllib.request
from typing import Dict, Any, List

def check_groq_health(api_key: str) -> Dict[str, Any]:
    """
    Queries GroqCloud GET https://api.groq.com/openai/v1/models with the user's API key
    to get the live list of currently active and accessible models.
    """
    if not api_key or not api_key.strip():
        return {
            "status": "error",
            "message": "Groq API key not provided. Enter key to test health.",
            "models": []
        }
    
    clean_key = api_key.strip()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/models",
        headers={
            "Authorization": f"Bearer {clean_key}",
            "Content-Type": "application/json",
            "User-Agent": "openClip-Studio/1.0"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                models_list = [m.get("id") for m in data.get("data", []) if m.get("id") and m.get("active", True)]
                return {
                    "status": "healthy",
                    "message": f"GroqCloud connection verified ({len(models_list)} models available).",
                    "models": models_list
                }
            else:
                return {
                    "status": "error",
                    "message": f"Groq responded with HTTP {resp.status}",
                    "models": []
                }
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_msg)
            msg = err_json.get("error", {}).get("message", err_msg)
        except Exception:
            msg = err_msg or str(e)
        return {
            "status": "error",
            "message": f"Groq API Error ({e.code}): {msg[:140]}",
            "models": []
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Connection failed: {str(e)[:140]}",
            "models": []
        }

def check_gemini_health(api_key: str) -> Dict[str, Any]:
    """
    Queries Google Gemini API with the user's API key to test availability.
    """
    if not api_key or not api_key.strip():
        return {
            "status": "error",
            "message": "Gemini API key not provided. Enter key to test health.",
            "models": []
        }
        
    clean_key = api_key.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={clean_key}"
    req = urllib.request.Request(
        url,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "openClip-Studio/1.0"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                available = []
                for m in data.get("models", []):
                    name = m.get("name", "").replace("models/", "")
                    if "flash" in name.lower() or "pro" in name.lower():
                        available.append(name)
                return {
                    "status": "healthy",
                    "message": f"Gemini API connection verified ({len(available)} models active).",
                    "models": available
                }
            else:
                return {
                    "status": "error",
                    "message": f"Gemini responded with HTTP {resp.status}",
                    "models": []
                }
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_msg)
            msg = err_json.get("error", {}).get("message", err_msg)
        except Exception:
            msg = err_msg or str(e)
        return {
            "status": "error",
            "message": f"Gemini API Error ({e.code}): {msg[:140]}",
            "models": []
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Connection failed: {str(e)[:140]}",
            "models": []
        }
