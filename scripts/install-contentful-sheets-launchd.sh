#!/usr/bin/env bash
# One-time: register a macOS LaunchAgent to run the Contentful → Google Sheets
# sync every Monday at 06:00 (local). Edit the plist to change the day/time.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="${ROOT}/launchd/com.prd-ticket-agent.contentful-sheets-sync.plist"
DEST="${HOME}/Library/LaunchAgents/com.prd-ticket-agent.contentful-sheets-sync.plist"
if [[ ! -f "$PLIST_SRC" ]]; then
  echo "Missing $PLIST_SRC" >&2
  exit 1
fi
sed "s|__REPO_ROOT__|${ROOT}|g" "$PLIST_SRC" > "$DEST"
chmod +x "${ROOT}/scripts/run_contentful_sheets_weekly.sh" "${ROOT}/sheets" "${ROOT}/get-csv" 2>/dev/null || true
plutil -lint "$DEST" >/dev/null
launchctl unload "$DEST" 2>/dev/null || true
launchctl load -w "$DEST"
echo "Installed: $DEST"
echo "Run once now: launchctl start com.prd-ticket-agent.contentful-sheets-sync"
echo "Logs: /tmp/contentful-sheets-stdout.log / /tmp/contentful-sheets-stderr.log"
