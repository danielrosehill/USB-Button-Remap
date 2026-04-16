#!/usr/bin/env bash
# Launch the PyQt6 GUI. Uses the system python (/usr/bin/python3) because
# python3-pyqt6 and python3-evdev are installed via apt, not pip/brew.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec /usr/bin/python3 "$REPO_ROOT/gui/usb_button_remap.py" "$@"
