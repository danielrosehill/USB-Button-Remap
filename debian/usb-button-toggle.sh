#!/bin/bash
# CLI wrapper: toggle the USB button between F13 and Ctrl+Alt+Space (installed).
if [ "$EUID" -ne 0 ]; then
    exec pkexec /opt/usb-button-remap/scripts/toggle.sh "$@"
fi
exec /opt/usb-button-remap/scripts/toggle.sh "$@"
