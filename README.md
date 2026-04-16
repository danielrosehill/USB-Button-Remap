# USB-Button-F13-Remap

Remap a generic single-button USB HID device (vendor `5131:2019`) to emit `F13` on Linux, using [`keyd`](https://github.com/rvaiya/keyd). Works on Wayland (tested on Ubuntu 25.10 / KDE Plasma).

F13 is a handy target: no normal keyboard has it, so it won't collide with anything, and KDE / most apps will happily accept it as a shortcut.

## The device

A generic "USB button" HID device identifying as `5131:2019`. Out of the box it sends `KEY_2` (HID usage `0x7001f`) on its keyboard interface when pressed.

```
$ lsusb | grep 5131
Bus 001 Device 016: ID 5131:2019
```

This vendor/product pair is used by various cheap single-button / footswitch / macro-pad devices. If yours reports a different key, adjust the config accordingly.

## Identify what your button sends

```bash
sudo evtest /dev/input/by-id/usb-5131_2019-event-kbd
```

Press the button. You'll see something like:

```
Event: time ..., type 1 (EV_KEY), code 3 (KEY_2), value 1
Event: time ..., type 1 (EV_KEY), code 3 (KEY_2), value 0
```

The `KEY_*` name is what you'll remap.

## Remap with keyd

### Install

```bash
# Debian/Ubuntu
sudo apt install keyd
# or build from source: https://github.com/rvaiya/keyd
```

### Config

Drop this at `/etc/keyd/usb-button.conf`:

```ini
[ids]
5131:2019

[main]
2 = f13
```

The `[ids]` section scopes the remap to this USB device only — your regular `2` key on the main keyboard is untouched.

### Enable

```bash
sudo systemctl enable --now keyd
```

Verify keyd matched the device:

```bash
sudo journalctl -u keyd -n 20 | grep 5131
# DEVICE: match    5131:2019:... /etc/keyd/usb-button.conf (HID 5131:2019)
```

### Verify the remap

```bash
sudo keyd monitor
```

Press the button. You should see:

```
keyd virtual keyboard   0fac:0ade:...   f13 down
keyd virtual keyboard   0fac:0ade:...   f13 up
```

## Using F13

- **KDE**: System Settings → Shortcuts → add a custom shortcut, press the button to bind F13.
- **Apps**: most apps accept F13 in their keybinding dialogs directly.
- **Scripts**: bind via your window manager / compositor as if it were any other key.

## Why keyd (vs udev hwdb / input-remapper / xmodmap)

- **Works on Wayland** — `xmodmap` and `setxkbmap` don't.
- **Device-scoped** — `[ids]` restricts the remap to a specific vendor:product, so it doesn't leak to your main keyboard.
- **System-wide** — runs as a daemon, active on the TTY and across all user sessions.
- **Declarative** — a two-line config vs. a udev hwdb entry that needs scancode hex.

## Files

- [`usb-button.conf`](./usb-button.conf) — the keyd config, ready to drop into `/etc/keyd/`.
