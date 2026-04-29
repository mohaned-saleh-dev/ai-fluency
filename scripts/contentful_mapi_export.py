#!/usr/bin/env python3
"""
One-off: export space data via Content Management API (no npm).
Requires env: CONTENTFUL_MANAGEMENT_TOKEN
Usage:
  CONTENTFUL_MANAGEMENT_TOKEN=... python3 contentful_mapi_export.py
"""
import json
import os
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://api.contentful.com"
SPACE = os.environ.get("CONTENTFUL_SPACE_ID", "zbmxie3yr3cc")
ENV = os.environ.get("CONTENTFUL_ENVIRONMENT", "master")
_DEFAULT_OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "contentful-export",
    "space_export.json",
)
OUT = os.path.normpath(
    os.environ.get("CONTENTFUL_EXPORT_JSON_PATH", _DEFAULT_OUT)
)


def req(path: str, params: dict) -> dict:
    token = os.environ.get("CONTENTFUL_MANAGEMENT_TOKEN")
    if not token:
        print("Set CONTENTFUL_MANAGEMENT_TOKEN", file=sys.stderr)
        sys.exit(1)
    q = urlencode(params)
    url = f"{BASE}{path}"
    if q:
        url = f"{url}?{q}"
    r = Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )
    ctx = ssl.create_default_context()
    try:
        with urlopen(r, context=ctx, timeout=120) as res:
            return json.loads(res.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code} {path}: {body[:2000]}", file=sys.stderr)
        raise


def fetch_paged(
    path_template: str, limit: int = 100, extra: dict = None
) -> list:
    items = []
    skip = 0
    extra = extra or {}
    while True:
        params = {"limit": str(limit), "skip": str(skip), **extra}
        data = req(path_template, params)
        batch = data.get("items", [])
        items.extend(batch)
        if len(batch) < limit:
            break
        skip += limit
    return items


def main():
    p = f"/spaces/{SPACE}/environments/{ENV}"
    out_path = os.path.normpath(OUT)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    print("Fetching content types…", file=sys.stderr)
    ct = req(f"{p}/content_types", {})
    # single response has items
    citems = ct.get("items", [])

    print("Fetching locales…", file=sys.stderr)
    loc = req(f"{p}/locales", {})
    litems = loc.get("items", [])

    print("Fetching entries (paginated)…", file=sys.stderr)
    # CMA entry/asset collection max per page is 100
    entries = fetch_paged(f"{p}/entries", limit=100)

    print("Fetching assets (paginated)…", file=sys.stderr)
    assets = fetch_paged(f"{p}/assets", limit=100)

    bundle = {
        "spaceId": SPACE,
        "environmentId": ENV,
        "contentTypes": citems,
        "locales": litems,
        "entries": entries,
        "assets": assets,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "written": out_path,
                "contentTypes": len(citems),
                "locales": len(litems),
                "entries": len(entries),
                "assets": len(assets),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
