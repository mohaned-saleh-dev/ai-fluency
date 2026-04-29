#!/usr/bin/env python3
"""
Puts index.html + entries_readable.csv in ~/Downloads/Hosty-contentful-bundle/
(override with HOSTY_BUNDLE_DIR). Picks the newest entries_readable*.csv in the repo
or in Downloads if the repo copy is missing.
On macOS, opens that folder in Finder.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
REPO_CSV = ROOT / "contentful-export" / "entries_readable.csv"
_DLS = Path.home() / "Downloads"
_DEFAULT_OUT = _DLS / "Hosty-contentful-bundle"


def _newest_glob(d: Path, pattern: str) -> Optional[Path]:
    matches = list(d.glob(pattern))
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def _find_csv() -> Optional[Path]:
    if REPO_CSV.is_file():
        return REPO_CSV
    return _newest_glob(_DLS, "entries_readable*.csv")


def main() -> None:
    csv_in = _find_csv()
    if not csv_in:
        print("No CSV found.", file=sys.stderr)
        print("Either run: ./get-csv", file=sys.stderr)
        print("Or put a file like entries_readable.csv in your Downloads folder.", file=sys.stderr)
        sys.exit(1)

    out = Path(
        os.environ.get("HOSTY_BUNDLE_DIR", str(_DEFAULT_OUT))
    ).expanduser()

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.is_dir():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    dst = out / "entries_readable.csv"
    shutil.copy2(csv_in, dst)
    mtime = datetime.fromtimestamp(
        dst.stat().st_mtime, tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")
    (out / "index.html").write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Contentful export</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
    a {{ color: #1a4fd6; font-weight: 600; }}
  </style>
</head>
<body>
  <h1>Contentful — readable export</h1>
  <p>Generated: {mtime}</p>
  <p><a href="entries_readable.csv" download>Download entries_readable.csv</a></p>
  <p>Open the CSV in Excel, Google Sheets, or any spreadsheet app.</p>
</body>
</html>
""",
        encoding="utf-8",
    )
    here = out.resolve()
    (out / "FOLDER_TO_UPLOAD.txt").write_text(
        f"""This folder (not just one file) is what you upload to Hosty: Folder mode.

Path on your Mac:
{here}

The CSV you used: {csv_in}
""",
        encoding="utf-8",
    )
    print("Built:", here)
    print("Upload this folder in Hosty (Folder).")
    if sys.platform == "darwin":
        subprocess.run(["open", str(here)], check=False)


if __name__ == "__main__":
    main()
