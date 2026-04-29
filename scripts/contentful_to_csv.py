#!/usr/bin/env python3
"""
Convert contentful-export/space_export.json (CMA-style bundle) to CSVs.
  - contentful-export/entries_full.csv
  - contentful-export/assets_full.csv
  - contentful-export/content_types.csv
  - contentful-export/locales.csv
Assumes the JSON was produced by contentful_mapi_export.py.
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
JSON_IN = os.path.join(ROOT, "contentful-export", "space_export.json")
OUT_DIR = os.path.join(ROOT, "contentful-export")


def j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def main():
    if not os.path.isfile(JSON_IN):
        print(f"Missing {JSON_IN} — run contentful_mapi_export.py first.", file=sys.stderr)
        sys.exit(1)
    with open(JSON_IN, "r", encoding="utf-8") as f:
        bundle = json.load(f)
    os.makedirs(OUT_DIR, exist_ok=True)

    # --- entries ---
    ep = os.path.join(OUT_DIR, "entries_full.csv")
    ecols = [
        "entry_id",
        "content_type",
        "created_at",
        "updated_at",
        "version",
        "published_at",
        "first_published_at",
        "metadata_json",
        "fields_json",
    ]
    with open(ep, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ecols, extrasaction="ignore")
        w.writeheader()
        for e in bundle.get("entries", []):
            s = e.get("sys", {})
            ct = (s.get("contentType") or {}).get("sys", {}).get("id", "")
            w.writerow(
                {
                    "entry_id": s.get("id", ""),
                    "content_type": ct,
                    "created_at": s.get("createdAt", ""),
                    "updated_at": s.get("updatedAt", ""),
                    "version": s.get("version", ""),
                    "published_at": s.get("publishedAt") or "",
                    "first_published_at": s.get("firstPublishedAt") or "",
                    "metadata_json": j(e.get("metadata") or {}),
                    "fields_json": j(e.get("fields") or {}),
                }
            )

    # --- assets ---
    ap = os.path.join(OUT_DIR, "assets_full.csv")
    acols = [
        "asset_id",
        "created_at",
        "updated_at",
        "version",
        "published_at",
        "title_json",
        "description_json",
        "file_json",
        "metadata_json",
    ]
    with open(ap, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=acols, extrasaction="ignore")
        w.writeheader()
        for a in bundle.get("assets", []):
            s = a.get("sys", {})
            fld = a.get("fields") or {}
            w.writerow(
                {
                    "asset_id": s.get("id", ""),
                    "created_at": s.get("createdAt", ""),
                    "updated_at": s.get("updatedAt", ""),
                    "version": s.get("version", ""),
                    "published_at": s.get("publishedAt") or "",
                    "title_json": j(fld.get("title") or {}),
                    "description_json": j(fld.get("description") or {}),
                    "file_json": j(fld.get("file") or {}),
                    "metadata_json": j(a.get("metadata") or {}),
                }
            )

    # --- content types (schema) ---
    cp = os.path.join(OUT_DIR, "content_types.csv")
    ccols = ["type_id", "name", "display_field", "description", "fields_json"]
    with open(cp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ccols, extrasaction="ignore")
        w.writeheader()
        for c in bundle.get("contentTypes", []):
            s = c.get("sys", {})
            w.writerow(
                {
                    "type_id": s.get("id", ""),
                    "name": (c.get("name") or ""),
                    "display_field": (c.get("displayField") or ""),
                    "description": (c.get("description") or "").replace(
                        "\r", " "
                    ),
                    "fields_json": j(c.get("fields") or []),
                }
            )

    # --- locales ---
    lp = os.path.join(OUT_DIR, "locales.csv")
    lcols = ["locale_id", "code", "name", "default", "fallback_code"]
    with open(lp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=lcols, extrasaction="ignore")
        w.writeheader()
        for loc in bundle.get("locales", []):
            s = loc.get("sys", {})
            fb = loc.get("fallbackCode")
            w.writerow(
                {
                    "locale_id": s.get("id", ""),
                    "code": loc.get("code") or loc.get("internal_code") or "",
                    "name": (loc.get("name") or ""),
                    "default": "true" if loc.get("default") else "false",
                    "fallback_code": fb or "",
                }
            )

    print(
        json.dumps(
            {
                "wrote": {
                    "entries_full.csv": len(bundle.get("entries", [])),
                    "assets_full.csv": len(bundle.get("assets", [])),
                    "content_types.csv": len(bundle.get("contentTypes", [])),
                    "locales.csv": len(bundle.get("locales", [])),
                },
                "out_dir": OUT_DIR,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
