#!/bin/sh
# Fail fast if the app module cannot load (surfaces ImportError in Render logs).
set -e
cd /app

python3 - <<'PY'
import sys
print("Python:", sys.version.split()[0], flush=True)
import app  # noqa: F401
print("app: import OK", flush=True)
PY

# No --preload: safer with gRPC-based Google client after fork on some hosts.
exec gunicorn \
  -b "0.0.0.0:${PORT}" \
  -w 1 \
  -k sync \
  --timeout 300 \
  --graceful-timeout 60 \
  --access-logfile - \
  --error-logfile - \
  "app:app"
