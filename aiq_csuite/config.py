import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent


def _normalize_admin_value(raw: Optional[str]) -> str:
    s = ("" if raw is None else str(raw)).replace("\ufeff", "").strip()
    if len(s) >= 2 and s[0] in "\"'" and s[0] == s[-1]:
        s = s[1:-1].strip()
    return s


def _split_admin_secrets(raw: Optional[str]) -> list[str]:
    if raw is None:
        return []
    txt = str(raw).replace("\r", "\n")
    for sep in (";", ","):
        txt = txt.replace(sep, "\n")
    out: list[str] = []
    for part in txt.split("\n"):
        s = _normalize_admin_value(part)
        if s:
            out.append(s)
    return out


p = BASE_DIR / ".env"
try:
    from dotenv import dotenv_values, load_dotenv

    if p.is_file():
        load_dotenv(p, override=True)
    else:
        load_dotenv(override=True)
    if p.is_file():
        _file_vals = dotenv_values(p) or {}
        _from_file = _file_vals.get("AIQ_ADMIN_SECRET")
        if _from_file is not None and str(_from_file).strip() != "":
            os.environ["AIQ_ADMIN_SECRET"] = _normalize_admin_value(str(_from_file))
        _from_file_multi = _file_vals.get("AIQ_ADMIN_SECRETS")
        if _from_file_multi is not None and str(_from_file_multi).strip() != "":
            os.environ["AIQ_ADMIN_SECRETS"] = str(_from_file_multi)
except ImportError:
    pass


def _truthy_env(key: str) -> bool:
    return os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on")


def _resolve_instance_dir() -> Path:
    """
    Writable app data directory (SQLite DB name + orchestrator_weights.json live here).

    - AIQ_LOCAL_DATA_DIR or AIQ_USER_DATA_DIR — explicit absolute path (highest priority).
    - AIQ_STORE_DATA_IN_HOME=1 — ~/.aiq_csuite (recommended for local-only work on your Mac).
    - Otherwise — <repo>/aiq_csuite/instance (default).
    """
    explicit = os.environ.get("AIQ_LOCAL_DATA_DIR") or os.environ.get("AIQ_USER_DATA_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()
    if _truthy_env("AIQ_STORE_DATA_IN_HOME"):
        return (Path.home() / ".aiq_csuite").resolve()
    return (BASE_DIR / "instance").resolve()


INSTANCE_DIR = _resolve_instance_dir()
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
DB_PATH = Path(os.environ.get("AIQ_SQLITE_PATH", str(INSTANCE_DIR / "aiq_csuite.db"))).expanduser().resolve()

GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
# gemini-2.0-flash is 404 for many new users; use 2.5+ on https://ai.google.dev/gemini-api/docs/models
# Override in .env: AIQ_GEMINI_MODEL=…
GEMINI_MODEL = os.environ.get("AIQ_GEMINI_MODEL", "gemini-2.5-flash")
# Second LLM call for "paste" detection: set 1 to use Gemini (more calls, more quota)
AIQ_LLM_CLASSIFY = os.environ.get("AIQ_LLM_CLASSIFY", "").lower() in ("1", "true", "yes")
# who answers: "gemini" | "ollama" | "auto" (if key: gemini, else ollama if running, else error)
LLM_PROVIDER = os.environ.get("AIQ_LLM_PROVIDER", "auto").strip().lower() or "auto"
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
# (after loading .env) normalize admin secret; file value was re-injected into os above
# normalize so .env "quotes" or BOM / stray spaces don't break auth
_raw_admin = os.environ.get("AIQ_ADMIN_SECRET", "change-me-in-production")
ADMIN_SECRET = _normalize_admin_value(_raw_admin) or "change-me-in-production"
_raw_admin_multi = os.environ.get("AIQ_ADMIN_SECRETS", "")
ADMIN_SECRETS = _split_admin_secrets(_raw_admin_multi)
if not ADMIN_SECRETS:
    ADMIN_SECRETS = [ADMIN_SECRET]
elif ADMIN_SECRET not in ADMIN_SECRETS:
    ADMIN_SECRETS.append(ADMIN_SECRET)

# re-export for comparing pasted / URL / Bearer values to ADMIN_SECRET
normalize_admin_token = _normalize_admin_value

# Approximate 10 min session: nudge to wrap
TARGET_DURATION_SEC = int(os.environ.get("AIQ_TARGET_SEC", "600"))

# Open (unended) sessions are auto-closed after this many hours (no new messages; complete may still run).
SESSION_MAX_AGE_HOURS = float(os.environ.get("AIQ_SESSION_MAX_AGE_HOURS", "24"))
SESSION_MAX_AGE_SEC = SESSION_MAX_AGE_HOURS * 3600.0


def ensure_instance():
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    # DB may be overridden to another folder via AIQ_SQLITE_PATH
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
