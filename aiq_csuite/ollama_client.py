"""Local, free Ollama HTTP API (no key). https://github.com/ollama/ollama"""
import json
import urllib.error
import urllib.request
from typing import List, Optional, Tuple

from config import GEMINI_MODEL, OLLAMA_BASE, OLLAMA_MODEL


def _post(path: str, body: dict, timeout: int = 120) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def ollama_available() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def ollama_chat(
    system: str,
    history: List[dict],
    last_user: str,
    model: Optional[str] = None,
    temperature: float = 0.55,
) -> str:
    """history: {role, content} with role in user|model/assistant/ai"""
    mdl = model or OLLAMA_MODEL
    messages = [{"role": "system", "content": system}]
    for h in history:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("model", "assistant", "ai"):
            messages.append({"role": "assistant", "content": content})
        else:
            messages.append({"role": "user", "content": content})
    messages.append({"role": "user", "content": last_user})
    out = _post(
        "/api/chat",
        {
            "model": mdl,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 8192,
                # Interviewer lines need a full turn; the default (often 128) truncates questions mid-sentence.
                "num_predict": 1500,
            },
        },
    )
    return (out.get("message") or {}).get("content", "").strip()


def ollama_generate_text(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    num_predict: int = 1200,
) -> str:
    mdl = model or OLLAMA_MODEL
    out = _post(
        "/api/generate",
        {
            "model": mdl,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": num_predict},
        },
    )
    return (out.get("response") or "").strip()


def resolve_backend(gemini_key: str) -> Tuple[str, str]:
    """
    Returns ("gemini"|"ollama", message for /health).
    """
    from config import LLM_PROVIDER

    if LLM_PROVIDER == "gemini":
        if not gemini_key:
            return "error", "AIQ_LLM_PROVIDER=gemini but no GOOGLE_API_KEY / GEMINI_API_KEY"
        return "gemini", f"using Gemini model={GEMINI_MODEL}"
    if LLM_PROVIDER == "ollama":
        if ollama_available():
            return "ollama", f"using Ollama at {OLLAMA_BASE} model={OLLAMA_MODEL}"
        return "error", f"AIQ_LLM_PROVIDER=ollama but Ollama not reachable at {OLLAMA_BASE}"
    # auto
    if gemini_key:
        return "gemini", "auto: using Gemini (key present)"
    if ollama_available():
        return "ollama", f"auto: no Gemini key, using Ollama at {OLLAMA_BASE} model={OLLAMA_MODEL}"
    return "error", (
        "auto: set GOOGLE_API_KEY for Gemini, or install Ollama and run: "
        f"ollama pull {OLLAMA_MODEL} && ollama serve"
    )
