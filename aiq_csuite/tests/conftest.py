"""Test-wide isolation.

`config` resolves DB_PATH from `AIQ_SQLITE_PATH` **at import time**, so the variable has
to be set before any test module imports config (directly, or via app/db/assessment_
profiles). A module-level assignment inside a single test file is not enough: whichever
test module pytest collects first wins, and a new file sorting ahead of it silently sends
every write to the real instance database.

conftest.py is imported before any test module, which makes this the only safe place for
it. Do not move it.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_TEST_DB_DIR = tempfile.mkdtemp(prefix="aiq_tests_")
os.environ["AIQ_SQLITE_PATH"] = os.path.join(_TEST_DB_DIR, "aiq_tests.db")
# Never let a test run reach a real Postgres, whatever is in the developer's .env.
os.environ.pop("DATABASE_URL", None)


def pytest_report_header(config):  # pragma: no cover - diagnostic only
    return f"aiq: test sqlite -> {os.environ['AIQ_SQLITE_PATH']}"
