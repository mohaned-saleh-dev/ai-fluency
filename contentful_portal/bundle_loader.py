"""
Load space_export.json from a local file or a remote URL (for cloud deployments).
"""
import json
import os
from pathlib import Path
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

import httpx

_root = Path(__file__).resolve().parent.parent
_DEFAULT = _root / "contentful-export" / "space_export.json"


def _headers() -> dict:
    h: dict = {}
    t = (os.environ.get("EXPORT_JSON_BEARER") or "").strip()
    if t:
        h["Authorization"] = f"Bearer {t}"
    r = (os.environ.get("EXPORT_JSON_EXTRA_HEADER") or "").strip()
    # e.g. "X-My-Key: value"  (one line)
    if ":" in r and not r.startswith("Authorization"):
        name, val = r.split(":", 1)
        h[name.strip()] = val.strip()
    return h


def get_remote_bundle(
    if_none_match: Optional[str],
) -> Tuple[Optional[dict], int, Optional[str]]:
    """
    GET EXPORT_JSON_URL. If if_none_match is set, sends If-None-Match (conditional GET).
    Returns (data or None on 304, status_code, ETag or None).
    """
    url = (os.environ.get("EXPORT_JSON_URL") or "").strip()
    if not url:
        raise ValueError("get_remote_bundle requires EXPORT_JSON_URL")
    h = _headers()
    if if_none_match:
        h["If-None-Match"] = if_none_match
    to = int(os.environ.get("EXPORT_JSON_TIMEOUT", "300"))
    with httpx.Client(timeout=to, follow_redirects=True) as c:
        r = c.get(url, headers=h)
    if r.status_code == 304:
        return None, 304, if_none_match
    r.raise_for_status()
    return (r.json(), r.status_code, r.headers.get("ETag"))


def load_json_bundle() -> Any:
    """
    Load from local path only. For remote, use get_remote_bundle in the app.
    If CONTENTFUL_EXPORT_JSON is set, use that file.
    Else use default project path.
    """
    cpath = (os.environ.get("CONTENTFUL_EXPORT_JSON") or "").strip()
    if cpath:
        p = Path(cpath)
    else:
        p = _DEFAULT
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def bundle_fingerprint() -> str:
    """String that changes when the input source changes (for cache)."""
    url = (os.environ.get("EXPORT_JSON_URL") or "").strip()
    if url:
        return f"u:{url}"
    cpath = (os.environ.get("CONTENTFUL_EXPORT_JSON") or "").strip()
    p = Path(cpath) if cpath else _DEFAULT
    try:
        st = p.stat()
        return f"f:{p.resolve()}:{st.st_mtime_ns}"
    except OSError:
        return f"e:{p}"


def public_bundle_hint() -> str:
    """Safe string for the UI (no tokens)."""
    url = (os.environ.get("EXPORT_JSON_URL") or "").strip()
    if url:
        try:
            p = urlparse(url)
            return f"URL ({p.netloc}…)" if p.netloc else "Remote URL"
        except Exception:
            return "Remote URL"
    cpath = (os.environ.get("CONTENTFUL_EXPORT_JSON") or "").strip()
    if cpath:
        return str(cpath)
    return str(_DEFAULT)
