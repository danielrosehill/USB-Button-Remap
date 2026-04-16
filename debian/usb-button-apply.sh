#!/bin/bash
# CLI wrapper: apply a keyd mapping for the USB button (installed).
if [ "$EUID" -ne 0 ]; then
    exec pkexec /opt/usb-button-remap/scripts/apply.sh "$@"
fi
exec /opt/usb-button-remap/scripts/apply.sh "$@"
