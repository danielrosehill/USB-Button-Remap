# USB-Button-Remap

Remap a generic single-button USB HID device (vendor `5131:2019`) on Linux using [`keyd`](https://github.com/rvaiya/keyd). Works on Wayland (tested on Ubuntu 25.10 / KDE Plasma).

Current mapping: **button → `Ctrl+Alt+Space`** — bind that combo to whatever you want in KDE, your window manager, or an app. Change the target in `usb-button.conf` if you prefer something else (e.g. `f13` for a collision-free function key).

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
2 = C-A-space
```

The `[ids]` section scopes the remap to this USB device only — your regular `2` key on the main keyboard is untouched.

keyd modifier syntax: `C-` = Ctrl, `A-` = Alt, `M-` = Super/Meta, `S-` = Shift. So `C-A-space` emits `Ctrl+Alt+Space` on press.

### Enable

```bash
sudo systemctl enable --now keyd
```

After editing the config, restart (keyd does not support reload):

```bash
sudo systemctl restart keyd
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

Press the button. You should see the configured key combo emitted by the keyd virtual keyboard.

## Alternative mappings

Swap the RHS of `2 =` to pick a different target:

| Target | Config |
|---|---|
| `Ctrl+Alt+Space` | `2 = C-A-space` |
| `F13` (collision-free function key) | `2 = f13` |
| `Super+Space` | `2 = M-space` |
| Single key, e.g. `pause` | `2 = pause` |
| Multi-step macro | `2 = macro(C-c 200 C-v)` |

## Why keyd (vs udev hwdb / input-remapper / xmodmap)

- **Works on Wayland** — `xmodmap` and `setxkbmap` don't.
- **Device-scoped** — `[ids]` restricts the remap to a specific vendor:product, so it doesn't leak to your main keyboard.
- **System-wide** — runs as a daemon, active on the TTY and across all user sessions.
- **Declarative** — a two-line config vs. a udev hwdb entry that needs scancode hex.

## Files

- [`usb-button.conf`](./usb-button.conf) — the keyd config, ready to drop into `/etc/keyd/`.
