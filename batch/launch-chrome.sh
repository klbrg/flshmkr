#!/usr/bin/env bash
# Launch Chrome with the DevTools remote-debugging port open so the batch
# reader (cdp_read.py) can pull the open chapter.
#
# Uses a DEDICATED profile by default, kept separate from your everyday
# browser. Reason: --remote-debugging-port lets any local process drive the
# browser and read its logged-in sessions, so you don't want that on your
# daily profile. One-time cost: log in to O'Reilly once in this profile.
#
# Usage:
#   ./launch-chrome.sh [url]
#
# Env overrides:
#   FLSHMKR_CHROME_PROFILE  profile dir (default ~/.flshmkr-chrome)
#   FLSHMKR_DEBUG_PORT      debug port  (default 9222)
set -euo pipefail

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE="${FLSHMKR_CHROME_PROFILE:-$HOME/.flshmkr-chrome}"
PORT="${FLSHMKR_DEBUG_PORT:-9222}"
URL="${1:-https://learning.oreilly.com/}"

if curl -s "http://localhost:${PORT}/json/version" >/dev/null 2>&1; then
  echo "Debug Chrome already running on port ${PORT}."
  exit 0
fi

mkdir -p "$PROFILE"
echo "Launching Chrome (profile: $PROFILE, debug port: $PORT)"
"$CHROME" \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check \
  "$URL" >/dev/null 2>&1 &
echo "Open your chapter, then in Claude Code say: batch the open chapter"
