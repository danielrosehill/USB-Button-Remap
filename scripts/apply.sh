#!/usr/bin/env bash
# Apply a keyd mapping for the USB button.
#
# Usage:
#   apply.sh [TARGET] [--device VID:PID] [--source-key KEY]
#
# TARGET:
#   f13              (default — collision-free function key)
#   combo            (alias for C-A-space, i.e. Ctrl+Alt+Space)
#   <raw keyd RHS>   e.g. "C-A-space", "M-space", "macro(C-c 200 C-v)"
#
# Config precedence (highest to lowest):
#   1. --device / --source-key command-line args
#   2. /etc/usb-button-remap/env                   (system-wide, used by the deb)
#   3. $REPO_ROOT/.env                             (dev — repo checkout)
#   4. Built-in defaults (5131:2019, key 2)
#
# After a successful apply, DEVICE_ID and SOURCE_KEY are persisted to
# /etc/usb-button-remap/env so subsequent runs (e.g. toggle.sh) use the
# same device without needing args.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SYS_CONF=/etc/usb-button-remap/env

if [[ -f "$SYS_CONF" ]]; then
  set -a; . "$SYS_CONF"; set +a
elif [[ -f "$REPO_ROOT/.env" ]]; then
  set -a; . "$REPO_ROOT/.env"; set +a
fi

TARGET_INPUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --device)     DEVICE_ID="$2"; shift 2 ;;
    --source-key) SOURCE_KEY="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,20p' "$0"; exit 0 ;;
    *) TARGET_INPUT="$1"; shift ;;
  esac
done

DEVICE_ID="${DEVICE_ID:-5131:2019}"
SOURCE_KEY="${SOURCE_KEY:-2}"
TARGET_INPUT="${TARGET_INPUT:-f13}"

case "$TARGET_INPUT" in
  f13)   TARGET="f13" ;;
  combo) TARGET="C-A-space" ;;
  *)     TARGET="$TARGET_INPUT" ;;
esac

CONFIG_PATH=/etc/keyd/usb-button.conf

# If we're root (e.g. invoked via pkexec) skip sudo; otherwise use sudo.
if [[ $EUID -eq 0 ]]; then SUDO=""; else SUDO="sudo"; fi

$SUDO tee "$CONFIG_PATH" >/dev/null <<EOF
[ids]
$DEVICE_ID

[main]
$SOURCE_KEY = $TARGET
EOF

$SUDO systemctl restart keyd

$SUDO mkdir -p /etc/usb-button-remap
$SUDO tee "$SYS_CONF" >/dev/null <<EOF
DEVICE_ID=$DEVICE_ID
SOURCE_KEY=$SOURCE_KEY
EOF

echo "keyd: $DEVICE_ID  $SOURCE_KEY -> $TARGET"
$SUDO journalctl -u keyd -n 20 --no-pager | grep -E "match.*$DEVICE_ID" \
  || echo "(device $DEVICE_ID not currently connected — config staged, will apply on plug-in)"
