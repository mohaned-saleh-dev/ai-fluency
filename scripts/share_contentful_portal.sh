#!/usr/bin/env bash
# Start the Contentful article downloader and (optionally) a Cloudflare quick tunnel.
# The most reliable access for teammates is the LAN address printed here (same Wi-Fi).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT="${PORT:-5050}"
export PORT

if ! command -v python3 >/dev/null; then
  echo "python3 is required" >&2
  exit 1
fi

echo "Starting app on 0.0.0.0:$PORT …"
python3 -m contentful_portal >>/tmp/contentful_portal.log 2>&1 &
APP_PID=$!
sleep 1
for i in 1 2 3 4 5 6 7 8; do
  if curl -sf "http://127.0.0.1:$PORT/api/health" >/dev/null; then
    break
  fi
  sleep 0.5
done

# Primary IPv4 (same logic as the app, best-effort)
IP="$(python3 -c "import os,socket
if os.environ.get('PORTAL_LAN_IP'):
 print(os.environ['PORTAL_LAN_IP']); raise SystemExit
try:
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.settimeout(0.5); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()
except OSError: print('127.0.0.1')")"
echo ""
echo "==========  USE THIS ON OFFICE WI-FI (most reliable)  =========="
echo "  http://$IP:$PORT/"
echo "  Send teammates this exact URL while they are on the same network."
echo "=================================================================="
echo ""
echo "App log: /tmp/contentful_portal.log   (pid $APP_PID)"
echo "Stop app:  kill $APP_PID"
echo ""

if [[ "${1:-}" == "--tunnel" ]]; then
  if ! command -v cloudflared >/dev/null; then
    echo "cloudflared not found. Install: brew install cloudflare/cloudflare/cloudflared" >&2
    exit 1
  fi
  # IPv4-only edge can help on some corporate networks; QUIC is default
  export TUNNEL_EDGE_IP_VERSION="${TUNNEL_EDGE_IP_VERSION:-4}"
  echo "Starting Cloudflare quick tunnel (public; ephemeral URL)…"
  exec cloudflared tunnel --url "http://127.0.0.1:$PORT"
else
  echo "Optional: run with --tunnel  to also get a public trycloudflare.com link"
  echo "  $0 --tunnel"
  wait $APP_PID
fi
