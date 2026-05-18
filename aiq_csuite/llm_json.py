"""Shared JSON LLM calls for AiQ scenario engine and reporting."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from config import GEMINI_API_KEY, GEMINI_MODEL, OPENAI_API_KEY, OPENAI_MODEL  # noqa: F401
from gemini_service import _is_gemini_quota_error, _strip_json, parse_scoring_json_object
from ollama_client import ollama_available, ollama_generate_text, resolve_backend
from openai_client import openai_generate_text


def llm_mode() -> tuple[str, str]:
    return resolve_backend(GEMINI_API_KEY, OPENAI_API_KEY)


def llm_json(
    prompt: str,
    *,
    system: str = "Return only valid JSON. No markdown fences.",
    temperature: float = 0.2,
    max_tokens: int = 2500,
) -> Dict[str, Any]:
    mode, err = llm_mode()
    if mode == "error":
        raise RuntimeError(err)
    if mode == "openai":
        raw = openai_generate_text(
            prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system,
            response_json=True,
        )
        return parse_scoring_json_object(raw or "{}")
    if mode == "ollama":
        raw = ollama_generate_text(
            system + "\n\n" + prompt,
            temperature=temperature,
            num_predict=max_tokens,
        )
        return parse_scoring_json_object(raw or "{}")
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        system_instruction=system,
    )
    try:
        r = model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "response_mime_type": "application/json",
            },
        )
        return parse_scoring_json_object(r.text or "{}")
    except Exception as e:
        if _is_gemini_quota_error(e) and ollama_available():
            raw = ollama_generate_text(
                system + "\n\n" + prompt,
                temperature=temperature,
                num_predict=max_tokens,
            )
            return parse_scoring_json_object(raw or "{}")
        raise
