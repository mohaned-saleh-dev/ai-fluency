#!/usr/bin/env python3
"""One-off migration: local SQLite -> Postgres (Supabase).

Usage:
  DATABASE_URL='postgresql://...' python3 scripts/migrate_sqlite_to_postgres.py
  DATABASE_URL='postgresql://...' python3 scripts/migrate_sqlite_to_postgres.py --sqlite /path/to/aiq_csuite.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DB_PATH, DATABASE_URL
from db import init_db


def _rows(conn: sqlite3.Connection, table: str, cols: str) -> Iterable[sqlite3.Row]:
    return conn.execute(f"SELECT {cols} FROM {table}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", default=str(DB_PATH), help="Path to source sqlite .db file")
    args = ap.parse_args()

    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL is required for Postgres target.")
    try:
        import psycopg2  # type: ignore
    except Exception as e:
        raise SystemExit(
            "psycopg2 is required. Run: pip install -r requirements.txt"
        ) from e
    src = Path(args.sqlite).expanduser().resolve()
    if not src.is_file():
        raise SystemExit(f"SQLite file not found: {src}")

    # Ensure target schema exists.
    init_db()

    sconn = sqlite3.connect(src)
    sconn.row_factory = sqlite3.Row
    pconn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    pcur = pconn.cursor()

    try:
        # sessions
        sess_cols = (
            "id, created_at, started_at, ended_at, target_role, client_seed, "
            "variation_json, last_scores_json, completed, user_agent, client_meta_json"
        )
        n = 0
        for r in _rows(sconn, "sessions", sess_cols):
            pcur.execute(
                """
                INSERT INTO sessions (
                  id, created_at, started_at, ended_at, target_role, client_seed,
                  variation_json, last_scores_json, completed, user_agent, client_meta_json
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO NOTHING
                """,
                tuple(r),
            )
            n += 1
        print(f"sessions scanned: {n}")

        # messages
        msg_cols = "id, session_id, role, content, created_at, flags_json"
        n = 0
        for r in _rows(sconn, "messages", msg_cols):
            pcur.execute(
                """
                INSERT INTO messages (id, session_id, role, content, created_at, flags_json)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO NOTHING
                """,
                tuple(r),
            )
            n += 1
        print(f"messages scanned: {n}")

        # events
        ev_cols = "id, session_id, type, payload_json, created_at"
        n = 0
        for r in _rows(sconn, "events", ev_cols):
            pcur.execute(
                """
                INSERT INTO events (id, session_id, type, payload_json, created_at)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO NOTHING
                """,
                tuple(r),
            )
            n += 1
        print(f"events scanned: {n}")

        pconn.commit()
        print("Migration complete.")
    finally:
        pcur.close()
        pconn.close()
        sconn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
