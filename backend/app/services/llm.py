from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def _call_gemini(system: str, user: str, max_tokens: int) -> dict | None:
    if not settings.GOOGLE_API_KEY:
        return None
    try:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.LLM_MODEL}:generateContent?key={settings.GOOGLE_API_KEY}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=settings.LLM_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return _extract_json(text)
    except Exception:
        logger.debug("Gemini call failed")
        return None


def _call_groq(system: str, user: str, max_tokens: int) -> dict | None:
    if not settings.GROQ_API_KEY:
        return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=settings.LLM_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
        return _extract_json(text)
    except Exception:
        logger.debug("Groq call failed")
        return None


def call_llm_json(system: str, user: str, max_tokens: int = 2500) -> dict | None:
    """Call Gemini → fall back to Groq → fall back to deterministic heuristics.

    Never raises — callers fall back to deterministic heuristics (SRS-3.3).
    """
    if not settings.has_llm:
        return None

    result = _call_gemini(system, user, max_tokens)
    if result is not None:
        return result

    logger.info("Gemini unavailable, trying Groq…")
    result = _call_groq(system, user, max_tokens)
    if result is not None:
        return result

    logger.warning("Both Gemini and Groq failed — falling back to heuristics.")
    return None


def _extract_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None
