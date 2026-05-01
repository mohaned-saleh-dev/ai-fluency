#!/usr/bin/env bash
# AiQ — persistent SQLite on YOUR Mac + free public HTTPS tunnel.
#
# What you get:
#   • Sessions / admin data live under ~/.aiq_csuite/ (when AIQ_STORE_DATA_IN_HOME=1, the default here).
#   • A shareable https://*.trycloudflare.com (or ngrok) URL while this script runs.
#
# One-time: brew install cloudflared
#
# Run:
#   cd aiq_csuite && ./scripts/run_local_persistent_tunnel.sh
#
# Stop: Ctrl+C — Flask is stopped too (FLASK_DEBUG=0, single process).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-5020}"
PY="${PYTHON:-python3}"
TARGET="http://127.0.0.1:${PORT}"

export AIQ_STORE_DATA_IN_HOME="${AIQ_STORE_DATA_IN_HOME:-1}"
export FLASK_DEBUG="${FLASK_DEBUG:-0}"

cleanup() {
  if [[ -n "${FLASK_PID:-}" ]] && kill -0 "$FLASK_PID" 2>/dev/null; then
    echo ""
    echo "Stopping Flask (pid ${FLASK_PID})..."
    kill "$FLASK_PID" 2>/dev/null || true
    wait "$FLASK_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " AiQ — local persistent DB + public tunnel"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " SQLite + orchestrator JSON:  ~/.aiq_csuite/  (AIQ_STORE_DATA_IN_HOME=1)"
echo " Local app:                   http://127.0.0.1:${PORT}"
echo " Tunnel → same routes:        /  |  /admin  |  /orchestrator"
echo ""

"$PY" app.py &
FLASK_PID=$!

echo -n "Waiting for Flask"
ready=0
for _ in $(seq 1 80); do
  if curl -sf "${TARGET}/api/health" >/dev/null 2>&1; then
    ready=1
    echo " — ready."
    break
  fi
  echo -n "."
  sleep 0.25
done

if [[ "$ready" != "1" ]]; then
  echo ""
  echo "Flask did not start on ${PORT}. Free the port or check errors above."
  exit 1
fi

echo ""
echo "Starting tunnel → ${TARGET}"
echo ""

if command -v cloudflared >/dev/null 2>&1; then
  cloudflared tunnel --url "${TARGET}"
elif command -v ngrok >/dev/null 2>&1; then
  ngrok http "${PORT}"
elif command -v npx >/dev/null 2>&1; then
  npx --yes localtunnel --port "${PORT}"
else
  echo "Install a tunnel tool, then run this script again:"
  echo "  brew install cloudflared"
  echo "Or: https://ngrok.com/download"
  exit 1
fi
