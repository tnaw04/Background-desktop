#!/usr/bin/env bash
# Start the eye wallpaper in the background (stops a running copy first).
# Extra arguments go to eyes.py, e.g. ./start.sh --theme light
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="${XDG_CACHE_HOME:-$HOME/.cache}/eyes-desktop.log"
WAYLAND_VIDEO="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/eyes-desktop@local/wallpaper.webm"
if [ "$#" -eq 0 ] && [ "${XDG_SESSION_TYPE:-}" = wayland ] && [ -f "$WAYLAND_VIDEO" ]; then
    echo "GNOME manages Eyes Desktop on Wayland. To enable it: gnome-extensions enable eyes-desktop@local"
    exit 0
fi
mkdir -p "$(dirname "$LOG")"

pkill -f "$DIR/eyes.py" 2>/dev/null
nohup python3 "$DIR/eyes.py" "$@" >"$LOG" 2>&1 &
echo "eyes-desktop started (log: $LOG)"
