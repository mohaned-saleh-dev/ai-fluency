#!/bin/bash
# Installs the Contentful article downloader as a per-user launchd service (Gunicorn).
# Usage: ./scripts/install-macos-launchd.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_BASE="$(basename "$ROOT")"
AGENT="com.prd-ticket-agent.contentful-portal"
PLIST_SRC="$ROOT/launchd/${AGENT}.plist"
DEST_DIR="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs"
PLIST_DEST="${DEST_DIR}/${AGENT}.plist"
mkdir -p "$DEST_DIR" "$LOG_DIR"

if [[ ! -f "$PLIST_SRC" ]]; then
  echo "Missing $PLIST_SRC" >&2
  exit 1
fi
sed -e "s|__REPO_ROOT__|${ROOT}|g" -e "s|__LOG_DIR__|${LOG_DIR}|g" "$PLIST_SRC" > "$PLIST_DEST"
chmod +x "$ROOT/scripts/gunicorn_contentful_portal.sh"

# Reload if already loaded
if launchctl list 2>/dev/null | grep -q "$AGENT"; then
  echo "Unloading existing $AGENT…"
  launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi
launchctl load -w "$PLIST_DEST" 2>/dev/null || launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST"

echo "Installed: $PLIST_DEST"
echo "  Label:  $AGENT"
echo "  App:    http://127.0.0.1:5050/  (or your LAN IP :5050)"
echo "  Logs:   $LOG_DIR/contentful-portal.log"
echo "  Stop:   launchctl unload \"$PLIST_DEST\""
