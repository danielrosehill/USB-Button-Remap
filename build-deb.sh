#!/bin/bash
# Build the .deb package for USB Button Remap.
# Usage: ./build-deb.sh
set -e

VERSION="1.0.0"
PKG_NAME="usb-button-remap"
BUILD_DIR="$(mktemp -d)"
PKG_DIR="$BUILD_DIR/${PKG_NAME}_${VERSION}"

echo "Building ${PKG_NAME} ${VERSION}..."

# Directory structure
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/opt/usb-button-remap/gui"
mkdir -p "$PKG_DIR/opt/usb-button-remap/scripts"
mkdir -p "$PKG_DIR/opt/usb-button-remap/docs"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/doc/$PKG_NAME"

# DEBIAN control
cat > "$PKG_DIR/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pyqt6, python3-evdev, polkitd | policykit-1
Recommends: keyd, systemd
Maintainer: Daniel Rosehill <daniel@danielrosehill.co.il>
Homepage: https://github.com/danielrosehill/USB-Button-Remap
Description: Remap a cheap USB HID button to F13 or Ctrl+Alt+Space via keyd
 Maps a single-button USB HID device (default vendor 5131:2019) to a
 collision-free F13 keycode or to Ctrl+Alt+Space, using keyd as the
 remap layer. Designed for AliExpress-style one-button pucks used to
 trigger speech-to-text / transcription apps.
 .
 Includes a PyQt6 GUI wizard that scans /dev/input/*, scores devices
 by "is-this-a-simple-button" heuristics, and offers an xev-style
 press-to-detect step. CLI wrappers usb-button-apply and
 usb-button-toggle let you set or flip the mapping from a terminal.
EOF

# Post-install
cat > "$PKG_DIR/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
case "$1" in
    configure)
        systemctl enable --now keyd >/dev/null 2>&1 || true
        if ! getent group input | grep -q "\b${SUDO_USER:-$USER}\b" 2>/dev/null; then
            echo ""
            echo "Note: add yourself to the 'input' group so the GUI can read evdev devices:"
            echo "  sudo usermod -aG input \$USER"
            echo "  (log out and back in for the group to apply)"
            echo ""
        fi
        echo "USB Button Remap installed."
        echo "  Run the GUI:        usb-button-remap"
        echo "  Apply from CLI:     usb-button-apply f13      (or: combo)"
        echo "  Toggle F13 <-> combo: usb-button-toggle"
        ;;
esac
exit 0
EOF
chmod 755 "$PKG_DIR/DEBIAN/postinst"

# Pre-removal: clean up generated config
cat > "$PKG_DIR/DEBIAN/prerm" <<'EOF'
#!/bin/bash
set -e
case "$1" in
    remove|purge)
        # Leave /etc/keyd/usb-button.conf in place by default — it's user config.
        # Purge removes /etc/usb-button-remap/ in the postrm.
        :
        ;;
esac
exit 0
EOF
chmod 755 "$PKG_DIR/DEBIAN/prerm"

cat > "$PKG_DIR/DEBIAN/postrm" <<'EOF'
#!/bin/bash
set -e
case "$1" in
    purge)
        rm -rf /etc/usb-button-remap
        ;;
esac
exit 0
EOF
chmod 755 "$PKG_DIR/DEBIAN/postrm"

# App files
cp gui/usb_button_remap.py "$PKG_DIR/opt/usb-button-remap/gui/"
cp scripts/apply.sh "$PKG_DIR/opt/usb-button-remap/scripts/"
cp scripts/toggle.sh "$PKG_DIR/opt/usb-button-remap/scripts/"
cp usb-button.conf "$PKG_DIR/opt/usb-button-remap/"
cp .env.example "$PKG_DIR/opt/usb-button-remap/"
cp docs/rationale.md "$PKG_DIR/opt/usb-button-remap/docs/"
cp README.md "$PKG_DIR/opt/usb-button-remap/"
chmod 755 "$PKG_DIR/opt/usb-button-remap/scripts/apply.sh"
chmod 755 "$PKG_DIR/opt/usb-button-remap/scripts/toggle.sh"
chmod 755 "$PKG_DIR/opt/usb-button-remap/gui/usb_button_remap.py"

# Launcher wrappers in /usr/bin
cp debian/usb-button-remap.sh   "$PKG_DIR/usr/bin/usb-button-remap"
cp debian/usb-button-apply.sh   "$PKG_DIR/usr/bin/usb-button-apply"
cp debian/usb-button-toggle.sh  "$PKG_DIR/usr/bin/usb-button-toggle"
chmod 755 "$PKG_DIR/usr/bin/usb-button-remap"
chmod 755 "$PKG_DIR/usr/bin/usb-button-apply"
chmod 755 "$PKG_DIR/usr/bin/usb-button-toggle"

# Desktop entry
cp debian/usb-button-remap.desktop "$PKG_DIR/usr/share/applications/"

# Docs
cp README.md "$PKG_DIR/usr/share/doc/$PKG_NAME/"
cp docs/rationale.md "$PKG_DIR/usr/share/doc/$PKG_NAME/"

# Build
dpkg-deb --root-owner-group --build "$PKG_DIR"

DEB_FILE="${PKG_NAME}_${VERSION}.deb"
mv "$PKG_DIR.deb" "./$DEB_FILE"
rm -rf "$BUILD_DIR"

echo ""
echo "Built: ./$DEB_FILE"
echo ""
echo "Install with:"
echo "  sudo apt install ./$DEB_FILE"
