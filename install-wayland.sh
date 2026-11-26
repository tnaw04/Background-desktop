#!/usr/bin/env bash
# Install the looping background and its GNOME Shell extension for the current user.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
UUID=eyes-desktop@local
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$UUID"
PYTHON="$ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON=python3
fi

if ! gnome-shell --version | grep -Eq '^GNOME Shell 46(\.|$)'; then
    echo "Eyes Desktop requires GNOME Shell 46." >&2
    exit 1
fi

BUILD="$(mktemp -d)"
trap 'rm -rf -- "$BUILD"' EXIT
"$PYTHON" "$ROOT/tools/render_wayland.py" "$BUILD/wallpaper.webm" --assets "$BUILD/frames" "$@"

# Reload the extension so it reads the replacement frames.
gnome-extensions disable "$UUID" 2>/dev/null || true
install -d -- "$DEST/frames"
install -m 644 -- "$ROOT/wayland/extension.js" "$ROOT/wayland/metadata.json" "$BUILD/wallpaper.webm" "$DEST"
install -m 644 -- "$BUILD"/frames/* "$DEST/frames"
if [ "${XDG_SESSION_TYPE:-}" = wayland ] && gnome-extensions enable "$UUID" 2>/dev/null; then
    "$ROOT/stop.sh"
    gnome-extensions info "$UUID"
else
    # GNOME discovers extensions installed on disk when the next session starts.
    gjs -c '
        const settings = new imports.gi.Gio.Settings({schema_id: "org.gnome.shell"});
        const uuid = "eyes-desktop@local";
        const enabled = settings.get_strv("enabled-extensions");
        if (!enabled.includes(uuid))
            settings.set_strv("enabled-extensions", [...enabled, uuid]);
        const disabled = settings.get_strv("disabled-extensions");
        if (disabled.includes(uuid))
            settings.set_strv("disabled-extensions", disabled.filter(id => id !== uuid));
        imports.gi.Gio.Settings.sync();
    '
    echo "Eyes Desktop is installed. Log out and select Ubuntu (Wayland) at login to load it."
fi
