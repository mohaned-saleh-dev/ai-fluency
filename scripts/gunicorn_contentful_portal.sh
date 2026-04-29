#!/bin/bash
# Gunicorn entry for launchd: keeps cwd + PYTHONPATH correct for contentful_portal
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"
export PORT="${PORT:-5050}"
exec /usr/bin/python3 -m gunicorn \
  -b "0.0.0.0:${PORT}" \
  -w 1 \
  --threads 2 \
  --timeout 300 \
  "contentful_portal.app:app"
