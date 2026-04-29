#!/usr/bin/env python3
"""Pushes the readable table to a Google Sheet. Needs .env (see below). Simpler path: ./get-csv (file only, no Google API)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# noqa: I001 (imports after path)


def _cell(v: Any, cap: int) -> str:
    s = v if v is not None else ""
    if not isinstance(s, str):
        s = str(s)
    if cap > 0 and len(s) > cap:
        return s[: cap - 1] + "…"
    return s


def _matrix(rows: List[dict], cols: List[str], cap: int) -> List[List[str]]:
    if not rows:
        return [["_no_rows_"]]
    header: List[str] = [_cell(c, cap) for c in cols]
    body: List[List[str]] = [
        [_cell(r.get(c), cap) for c in cols] for r in rows
    ]
    return [header, *body]


def _load_bundle(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _run_mapi() -> None:
    mapi = Path(__file__).resolve().parent / "contentful_mapi_export.py"
    r = subprocess.run(
        [sys.executable, str(mapi)],
        cwd=str(ROOT),
        env={**os.environ},
    )
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def _creds_path() -> str:
    p = (os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE") or "").strip() or (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or ""
    ).strip()
    if not p:
        print(
            "Set GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_APPLICATION_CREDENTIALS to the JSON key path",
            file=sys.stderr,
        )
        sys.exit(1)
    if not os.path.isfile(p):
        print(f"Service account file not found: {p}", file=sys.stderr)
        sys.exit(1)
    return p


def _push_gspread(
    data: List[List[str]],
    spreadsheet_id: str,
    title: str,
) -> None:
    import gspread

    p = _creds_path()
    client = gspread.service_account(filename=p)
    sh = client.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        nrows = min(max(len(data), 1000), 10000)
        ncols = min(max(len(data[0]) if data else 1, 26), 200)
        ws = sh.add_worksheet(title=title, rows=nrows, cols=ncols)

    ws.clear()
    total = len(data)
    if total == 0:
        return
    # Chunk updates to stay under request body limits (large text cells)
    size = 5000
    col_count = len(data[0]) if data else 1
    a1 = gspread.utils.rowcol_to_a1(1, col_count) if col_count else "A1"
    col_letter = a1.rstrip("0123456789") or "A"
    s = 0
    while s < total:
        chunk = data[s : s + size]
        r1, r2 = s + 1, s + len(chunk)
        rng = f"A{r1}:{col_letter}{r2}"
        ws.update(rng, chunk, value_input_option="USER_ENTERED")
        s += size


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Contentful MAPI export → same readable table as the portal → Google Sheet"
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Use existing CONTENTFUL export JSON, skip Contentful API",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build rows and print count; do not write to Google",
    )
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    cap = int(
        (os.environ.get("GOOGLE_SHEET_MAX_CELL_CHARS") or "45000").strip() or "45000"
    )

    default_json = (ROOT / "contentful-export" / "space_export.json").resolve()
    json_path = os.environ.get("CONTENTFUL_EXPORT_JSON_PATH")
    if json_path:
        ex_path = Path(os.path.normpath(json_path))
        if not ex_path.is_absolute():
            ex_path = (ROOT / ex_path).resolve()
    else:
        ex_path = default_json

    if not args.skip_export:
        print("Exporting from Contentful…", file=sys.stderr)
        _run_mapi()
    if not ex_path.is_file():
        print(f"Missing export JSON: {ex_path}", file=sys.stderr)
        sys.exit(1)

    from contentful_portal.service import build_rows_from_bundle

    bundle = _load_bundle(ex_path)
    rows, cols, _ = build_rows_from_bundle(bundle)
    matrix = _matrix(rows, cols, cap)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "rows": len(rows),
                    "columns": len(cols),
                    "export_json": str(ex_path),
                },
                indent=2,
            )
        )
        return

    sheet_id = (os.environ.get("GOOGLE_SHEET_ID") or "").strip()
    if not sheet_id:
        print("Set GOOGLE_SHEET_ID to the Google Sheet id from the URL", file=sys.stderr)
        sys.exit(1)
    wname = (os.environ.get("GOOGLE_SHEET_WORKSHEET") or "Contentful").strip() or "Contentful"
    _push_gspread(matrix, sheet_id, wname)
    print(
        json.dumps(
            {
                "ok": True,
                "sheet": f"https://docs.google.com/spreadsheets/d/{sheet_id}",
                "tab": wname,
                "rows": len(matrix) - 1,
                "columns": len(cols),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
