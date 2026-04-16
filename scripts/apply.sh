#!/usr/bin/env bash
# Apply a keyd mapping for the USB button.
#
# Usage:
#   ./scripts/apply.sh                    # defaults to f13
#   ./scripts/apply.sh f13
#   ./scripts/apply.sh combo              # alias for C-A-space (Ctrl+Alt+Space)
#   ./scripts/apply.sh "C-A-space"        # raw keyd RHS
#   ./scripts/apply.sh "macro(C-c 200 C-v)"
#
# Reads DEVICE_ID and SOURCE_KEY from ./.env (or .env.example as fallback).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a; . "$REPO_ROOT/.env"; set +a
elif [[ -f "$REPO_ROOT/.env.example" ]]; then
  set -a; . "$REPO_ROOT/.env.example"; set +a
fi

DEVICE_ID="${DEVICE_ID:-5131:2019}"
SOURCE_KEY="${SOURCE_KEY:-2}"

TARGET_INPUT="${1:-f13}"
case "$TARGET_INPUT" in
  f13)   TARGET="f13" ;;
  combo) TARGET="C-A-space" ;;
  *)     TARGET="$TARGET_INPUT" ;;
esac

CONFIG_PATH=/etc/keyd/usb-button.conf

sudo tee "$CONFIG_PATH" >/dev/null <<EOF
[ids]
$DEVICE_ID

[main]
$SOURCE_KEY = $TARGET
EOF

sudo systemctl restart keyd

echo "keyd: $DEVICE_ID  $SOURCE_KEY -> $TARGET"
sudo journalctl -u keyd -n 20 --no-pager | grep -E "match.*$DEVICE_ID" \
  || echo "(device $DEVICE_ID not currently connected — config staged, will apply on plug-in)"
