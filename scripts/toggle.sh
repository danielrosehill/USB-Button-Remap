#!/usr/bin/env bash
# Toggle the USB button mapping between f13 and Ctrl+Alt+Space (combo).
#
# Reads the current target from /etc/keyd/usb-button.conf and flips it.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_PATH=/etc/keyd/usb-button.conf

CURRENT="$(awk -F '=' '/^[[:space:]]*[0-9a-zA-Z_]+[[:space:]]*=/ && !/^\[/ {
  gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2; exit
}' "$CONFIG_PATH" 2>/dev/null || true)"

case "$CURRENT" in
  f13) NEXT=combo ;;
  *)   NEXT=f13 ;;
esac

echo "current: ${CURRENT:-<unset>}  ->  next: $NEXT"
exec "$REPO_ROOT/scripts/apply.sh" "$NEXT"
