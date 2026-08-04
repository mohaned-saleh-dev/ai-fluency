"""Minimal OpenAI Chat Completions client via stdlib urllib."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from config import OPENAI_API_KEY, OPENAI_BASE, OPENAI_MODEL


# Models learned at runtime to reject a custom temperature (the gpt-5 family accepts only
# the default). Kept as a learned set rather than a name prefix so a new model generation
# does not silently break the app the day it ships.
_NO_CUSTOM_TEMPERATURE: set = set()
# Gateways/proxies that still want the legacy token parameter.
_WANTS_LEGACY_MAX_TOKENS: set = set()


def _adapt_body_to_error(body: Dict[str, Any], detail: str) -> bool:
    """Drop or swap a parameter this model rejects. True if the call is worth retrying.

    OpenAI keeps narrowing which sampling parameters a model accepts, and the errors are
    specific and machine-readable, so adapt to what the endpoint actually says instead of
    hardcoding which families take what.
    """
    model = str(body.get("model") or "")
    low = detail.lower()
    if "temperature" in low and ("does not support" in low or "unsupported value" in low):
        if "temperature" in body:
            body.pop("temperature", None)
            _NO_CUSTOM_TEMPERATURE.add(model)
            return True
    if "max_tokens" in low and "not supported" in low and "max_tokens" in body:
        body["max_completion_tokens"] = body.pop("max_tokens")
        return True
    if "max_completion_tokens" in low and "not supported" in low and "max_completion_tokens" in body:
        body["max_tokens"] = body.pop("max_completion_tokens")
        _WANTS_LEGACY_MAX_TOKENS.add(model)
        return True
    return False


def _token_limit_key(model: str) -> str:
    return "max_tokens" if model in _WANTS_LEGACY_MAX_TOKENS else "max_completion_tokens"


def _post_json(path: str, body: Dict[str, Any], timeout: int = 120, max_tries: int = 3) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    last_err: Optional[Exception] = None
    # A model can reject more than one parameter (e.g. max_tokens *and* temperature), so
    # allow a few adaptations; bounded so a persistent 400 can never spin.
    adaptations_left = 3
    attempt = 0
    while attempt < max_tries:
        req = urllib.request.Request(
            f"{OPENAI_BASE}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8")
            except Exception:
                detail = str(e)
            last_err = RuntimeError(f"OpenAI HTTP {e.code}: {detail[:900]}")
            # A rejected parameter is a fixable mismatch, not a failure: adapt and retry
            # immediately without consuming a retry budget meant for rate limits.
            if e.code == 400 and adaptations_left > 0 and _adapt_body_to_error(body, detail):
                adaptations_left -= 1
                continue
            if e.code in (429, 500, 502, 503, 504) and attempt < max_tries - 1:
                attempt += 1
                time.sleep(2.0 * attempt)
                continue
            raise last_err
        except (urllib.error.URLError, OSError) as e:
            last_err = e
            if attempt < max_tries - 1:
                attempt += 1
                time.sleep(2.0 * attempt)
                continue
            raise
    if last_err:
        raise last_err
    return {}


def _extract_text(resp: Dict[str, Any]) -> str:
    choices = resp.get("choices") or []
    if not choices:
        return ""
    msg = (choices[0] or {}).get("message") or {}
    txt = msg.get("content")
    if isinstance(txt, str):
        return txt.strip()
    if isinstance(txt, list):
        out: List[str] = []
        for part in txt:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                out.append(part["text"])
        return "\n".join(out).strip()
    return ""


def openai_chat(
    system: str,
    history: List[dict],
    last_user: str,
    model: Optional[str] = None,
    temperature: float = 0.45,
    max_output_tokens: int = 2048,
) -> str:
    mdl = model or OPENAI_MODEL
    messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
    for h in history:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("model", "assistant", "ai"):
            messages.append({"role": "assistant", "content": content})
        else:
            messages.append({"role": "user", "content": content})
    messages.append({"role": "user", "content": last_user})
    body: Dict[str, Any] = {
        "model": mdl,
        "messages": messages,
        _token_limit_key(mdl): int(max_output_tokens),
    }
    if mdl not in _NO_CUSTOM_TEMPERATURE:
        body["temperature"] = float(temperature)
    resp = _post_json("/chat/completions", body)
    return _extract_text(resp)


def openai_generate_text(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_output_tokens: int = 1200,
    system_instruction: Optional[str] = None,
    response_json: bool = False,
    timeout: int = 120,
    max_tries: int = 3,
) -> str:
    mdl = model or OPENAI_MODEL
    messages: List[Dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    body: Dict[str, Any] = {
        "model": mdl,
        "messages": messages,
        _token_limit_key(mdl): int(max_output_tokens),
    }
    if mdl not in _NO_CUSTOM_TEMPERATURE:
        body["temperature"] = float(temperature)
    if response_json:
        body["response_format"] = {"type": "json_object"}
    resp = _post_json("/chat/completions", body, timeout=timeout, max_tries=max_tries)
    return _extract_text(resp)
