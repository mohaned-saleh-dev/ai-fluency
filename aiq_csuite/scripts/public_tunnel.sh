#!/usr/bin/env bash
# Expose your LOCAL AiQ server (same machine as this script) on the internet.
#
# Prefer the one-shot launcher (starts Flask + tunnel + persistent ~/.aiq_csuite):
#   cd aiq_csuite && ./scripts/run_local_persistent_tunnel.sh
#
# Or two terminals:
# 1) Terminal A — start the app:
#      cd aiq_csuite && python3 app.py
# 2) Terminal B — run this script:
#      ./scripts/public_tunnel.sh
#
# Then open the printed https URL + / for chat and /admin for review.
# Traffic hits YOUR laptop; SQLite stays on YOUR disk (see AIQ_STORE_DATA_IN_HOME in .env).
#
# Requires ONE of: cloudflared (recommended), ngrok, or Node+npx (localtunnel).

set -euo pipefail
PORT="${PORT:-5020}"
TARGET="http://127.0.0.1:${PORT}"

echo "Tunnel target: ${TARGET}"
echo "Start the Flask app first if it is not listening yet."
echo ""

if command -v cloudflared >/dev/null 2>&1; then
  echo "Using Cloudflare Quick Tunnel (free, no signup)."
  exec cloudflared tunnel --url "${TARGET}"
fi

if command -v ngrok >/dev/null 2>&1; then
  echo "Using ngrok."
  exec ngrok http "${PORT}"
fi

if command -v npx >/dev/null 2>&1; then
  echo "Using localtunnel via npx (first run may download packages)."
  exec npx --yes localtunnel --port "${PORT}"
fi

echo "No tunnel tool found. Install one of:"
echo ""
echo "  macOS (recommended):  brew install cloudflared"
echo "  Then run this script again."
echo ""
echo "  Or install ngrok:       https://ngrok.com/download"
echo "  Or install Node.js and use npx localtunnel automatically."
exit 1
