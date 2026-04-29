import hmac
import os
import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

import httpx
from flask import Flask, Response, render_template, jsonify, request

from .bundle_loader import (
    bundle_fingerprint,
    get_remote_bundle,
    load_json_bundle,
    public_bundle_hint,
)
from .docx_build import build_docx
from .service import build_rows_from_bundle, load_csv_module, render_csv_string

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)


@app.after_request
def _frame_embed_notion(resp):
    # So Notion (and other parents) can iframe /embed. Tighten frame-ancestors on a public host if you prefer.
    if (request.path or "") in ("/embed", "/e"):
        resp.headers["Content-Security-Policy"] = "frame-ancestors *"
    return resp


def _str_eq(a: str, b: str) -> bool:
    a, b = a or "", b or ""
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _auth_mode() -> str:
    u = (os.environ.get("CONTENTFUL_PORTAL_USER") or "").strip()
    p = (os.environ.get("CONTENTFUL_PORTAL_PASSWORD") or "").strip()
    k = (os.environ.get("CONTENTFUL_PORTAL_LINK_KEY") or "").strip()
    if k and (u and p):
        return "both"
    if k:
        return "key"
    if u and p:
        return "basic"
    return "none"


@app.before_request
def _remote_access_gate() -> Any:
    """
    Optional: restrict a public deploy to your team.
    - CONTENTFUL_PORTAL_LINK_KEY: add ?k=<key> to the URL, or send header X-Contentful-Portal-Key: <key>
      (useful for Notion embed: paste URL with k=… on a private page).
    - CONTENTFUL_PORTAL_USER + CONTENTFUL_PORTAL_PASSWORD: standard HTTP Basic (full-page; browser will prompt).
    If both are set, either a valid k OR valid Basic is accepted.
    """
    mode = _auth_mode()
    if mode == "none":
        return None
    pth = request.path or ""
    if pth == "/api/health" and (os.environ.get("PORTAL_PROTECT_HEALTH", "").lower() not in ("1", "true", "yes")):
        return None
    u_env = (os.environ.get("CONTENTFUL_PORTAL_USER") or "").strip()
    p_env = (os.environ.get("CONTENTFUL_PORTAL_PASSWORD") or "").strip()
    link_key = (os.environ.get("CONTENTFUL_PORTAL_LINK_KEY") or "").strip()

    def deny_basic():
        r = Response(
            "Not authorized. Use the shared link (with k=) or your team password.\n",
            401,
            mimetype="text/plain; charset=utf-8",
        )
        if mode in ("basic", "both") and u_env and p_env:
            r.headers["WWW-Authenticate"] = 'Basic realm="Contentful portal"'
        return r

    if link_key:
        got = (request.headers.get("X-Contentful-Portal-Key") or "").strip() or (request.args.get("k") or request.args.get("key") or "").strip()
        if _str_eq(got, link_key):
            return None
        if mode == "key":
            return deny_basic()

    if (mode in ("basic", "both")) and u_env and p_env:
        a = request.authorization
        if a and a.type == "basic" and _str_eq(a.username or "", u_env) and _str_eq(a.password or "", p_env):
            return None
    return deny_basic()


_cache: dict = {
    "fingerprint": None,
    "rows": None,
    "cols": None,
    "locales": None,
    "err": None,
}


def _get_export() -> Tuple[Optional[List[dict]], Optional[List[str]], List[str], Optional[str]]:
    url = (os.environ.get("EXPORT_JSON_URL") or "").strip()
    if url:
        if _cache.get("url_frozen") and _cache.get("rows") is not None:
            return _cache["rows"], _cache["cols"], _cache["locales"] or [], None
        inm = _cache.get("bundle_etag")
        try:
            bundle, code, new_etag = get_remote_bundle(inm)
        except httpx.HTTPError as e:
            return None, None, [], f"Failed to download bundle: {e}"
        except (json.JSONDecodeError, OSError, ValueError) as e:
            return None, None, [], f"Invalid bundle: {e}"
        if code == 304 and _cache.get("rows") is not None:
            return _cache["rows"], _cache["cols"], _cache["locales"] or [], None
        if bundle is None:
            return None, None, [], "No JSON body from URL"
        try:
            m = load_csv_module()
            rows, cols, ordered = build_rows_from_bundle(bundle, m)
        except Exception as e:
            return None, None, [], f"Export build failed: {e}"
        _cache["rows"] = rows
        _cache["cols"] = cols
        _cache["locales"] = ordered
        _cache["bundle_etag"] = new_etag
        _cache["url_frozen"] = not new_etag
        return rows, cols, ordered, None

    fp = bundle_fingerprint()
    if _cache.get("fingerprint") == fp and _cache.get("rows") is not None:
        return _cache["rows"], _cache["cols"], _cache["locales"] or [], None
    try:
        bundle = load_json_bundle()
    except FileNotFoundError as e:
        return None, None, [], f"Bundle file not found: {e}"
    except (json.JSONDecodeError, OSError) as e:
        return None, None, [], f"Invalid bundle: {e}"
    try:
        m = load_csv_module()
        rows, cols, ordered = build_rows_from_bundle(bundle, m)
    except Exception as e:
        return None, None, [], f"Export build failed: {e}"
    _cache["fingerprint"] = fp
    _cache["rows"] = rows
    _cache["cols"] = cols
    _cache["locales"] = ordered
    return rows, cols, ordered, None


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _server_port() -> int:
    return int(os.environ.get("PORT", "5050"))


def _lan_ip() -> str:
    override = (os.environ.get("PORTAL_LAN_IP") or "").strip()
    if override:
        return override
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return str(ip)
    except OSError:
        return "127.0.0.1"


@app.get("/")
def index():
    rows, cols, locales, err = _get_export()
    n = len(rows) if rows else 0
    p = _server_port()
    return render_template(
        "index.html",
        ready=err is None and n > 0,
        err=err,
        count=n,
        bundle_hint=public_bundle_hint(),
        has_docx=bool(n),
        lan_url=f"http://{_lan_ip()}:{p}",
        server_port=p,
    )


@app.get("/api/health")
def health():
    rows, _, __, err = _get_export()
    return jsonify(
        {
            "ok": err is None and rows is not None,
            "count": len(rows) if rows else 0,
            "error": err,
        }
    )


@app.get("/embed")
@app.get("/e")
def embed_mini():
    """Minimal UI for Notion embed (iframe): same /download/* API, same origin — no CORS. Notion does not run Python/JS; it only embeds this URL."""
    rows, __, ___, err = _get_export()
    n = len(rows) if rows else 0
    return render_template(
        "embed.html",
        ready=err is None and n > 0,
        err=err,
        count=n,
    )


@app.get("/api/server-info")
def server_info():
    p = _server_port()
    return jsonify(
        {
            "port": p,
            "lan_url": f"http://{_lan_ip()}:{p}",
            "hostname": socket.gethostname(),
        }
    )


@app.get("/download/entries.csv")
def download_csv():
    rows, cols, _, err = _get_export()
    if err or not rows or not cols:
        return Response(err or "No data", status=400, mimetype="text/plain")
    body = render_csv_string(rows, cols)
    r = Response(body, content_type="text/csv; charset=utf-8")
    r.headers["Content-Disposition"] = (
        f"attachment; filename=contentful-entries-{_ts()}.csv"
    )
    return r


@app.get("/download/entries.docx")
def download_docx():
    rows, _, locales, err = _get_export()
    if err or not rows or not locales:
        return Response(err or "No data", status=400, mimetype="text/plain")
    data = build_docx(rows, locales)
    r = Response(
        data,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    r.headers["Content-Disposition"] = f"attachment; filename=contentful-entries-{_ts()}.docx"
    return r


@app.post("/api/refresh")
def refresh():
    _cache.clear()
    return jsonify({"ok": True})

