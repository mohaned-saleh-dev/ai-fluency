#!/usr/bin/env bash
# Launched by launchd: export Contentful, push to Google Sheet.
# Env: from repo .env and/or launchd.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
if [[ -f .env ]]; then
  set -a
  # shellcheck source=/dev/null
  . ./.env
  set +a
fi
if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python "$REPO_ROOT/scripts/contentful_sheets_sync.py" "$@"
else
  exec python3 "$REPO_ROOT/scripts/contentful_sheets_sync.py" "$@"
fi
