# USB-Button-Remap

Remap a cheap AliExpress single-button USB HID device (default: `5131:2019`) on Linux using [`keyd`](https://github.com/rvaiya/keyd). Works on Wayland (tested on Ubuntu 25.10 / KDE Plasma).

Use case: a one-button USB puck pressed to trigger speech-to-text / transcription. Default target is **`F13`** (collision-free — no normal keyboard has it). A toggle script switches to **`Ctrl+Alt+Space`** if you need a modifier combo instead.

See [`docs/rationale.md`](./docs/rationale.md) for why keyd over input-remapper and why F13.

## Device

```
$ lsusb | grep 5131
Bus 001 Device 016: ID 5131:2019
```

Out of the box it sends `KEY_2` on its keyboard interface. Confirm with:

```bash
sudo evtest /dev/input/by-id/usb-5131_2019-event-kbd
```

If your device differs, set `DEVICE_ID` and `SOURCE_KEY` in `.env` (see below).

## Install

### From the .deb (recommended)

Download the latest `usb-button-remap_*.deb` from [Releases](https://github.com/danielrosehill/USB-Button-Remap/releases), then:

```bash
sudo apt install ./usb-button-remap_1.0.0.deb
```

This pulls in `keyd`, `python3-pyqt6`, `python3-evdev`, `polkitd`, enables keyd, and installs three commands on your PATH:

- `usb-button-remap` — launch the GUI
- `usb-button-apply <target> [--device VID:PID] [--source-key KEY]` — apply from CLI
- `usb-button-toggle` — flip between F13 and Ctrl+Alt+Space

Add yourself to the `input` group so the GUI can read evdev:

```bash
sudo usermod -aG input "$USER"   # log out/in afterwards
```

### From source (dev)

```bash
sudo apt install keyd python3-pyqt6 python3-evdev
sudo systemctl enable --now keyd
```

Then run `./scripts/gui.sh` or `./scripts/apply.sh` from the repo checkout.

## Configure

```bash
cp .env.example .env
# edit .env if your device isn't 5131:2019 / KEY_2
```

Apply the default (F13) mapping:

```bash
./scripts/apply.sh
```

Or pick a target:

```bash
./scripts/apply.sh f13                       # default — collision-free function key
./scripts/apply.sh combo                     # Ctrl+Alt+Space
./scripts/apply.sh "C-A-space"               # raw keyd RHS
./scripts/apply.sh "macro(C-c 200 C-v)"      # multi-step macro
```

Toggle between F13 and the combo:

```bash
./scripts/toggle.sh
```

Both scripts write `/etc/keyd/usb-button.conf`, restart `keyd`, and confirm the device matched in the journal.

## How it works

`scripts/apply.sh` renders this config from your `.env`:

```ini
[ids]
${DEVICE_ID}

[main]
${SOURCE_KEY} = ${TARGET}
```

The `[ids]` section scopes the remap to one `vendor:product` — your real keyboard is untouched. keyd modifier syntax: `C-` = Ctrl, `A-` = Alt, `M-` = Super, `S-` = Shift. See `man keyd` for layers, macros, and overloads.

## Verify

```bash
sudo keyd monitor
```

Press the button; you should see the configured key emitted by the keyd virtual keyboard.

Match log:

```bash
sudo journalctl -u keyd -n 20 | grep "$DEVICE_ID"
# DEVICE: match    5131:2019:...  /etc/keyd/usb-button.conf  (HID 5131:2019)
```

## GUI

A PyQt6 wizard for the same workflow, for when you don't want to edit `.env` by hand.

```bash
sudo apt install python3-pyqt6 python3-evdev   # one-time
./scripts/gui.sh
```

What it does:

1. **Scans `/dev/input/*`** and scores each device by "is-this-a-simple-button" heuristics — few distinct keys, no mouse (`EV_REL`) or tablet (`EV_ABS`) axes, no LEDs. Likely button candidates sort to the top; your real keyboard and mouse are dimmed at the bottom.
2. **Optional press-to-detect** — like `xev` inline. Briefly stops keyd (polkit prompt), listens on plausible devices, captures the first keypress, auto-fills the device `vendor:product` and source key, then restarts keyd.
3. **Target chooser** — F13, Ctrl+Alt+Space, or a custom keyd expression.
4. **Apply** — writes `.env`, runs `scripts/apply.sh` via `pkexec`, shows the keyd journal match.

The GUI is a thin frontend over the same `apply.sh` / `toggle.sh` used from the CLI — no separate code path for the mapping logic.

Your user must be in the `input` group to read evdev devices without root:

```bash
groups | tr ' ' '\n' | grep -q '^input$' || sudo usermod -aG input "$USER"
# then log out / back in
```

## Files

- [`usb-button.conf`](./usb-button.conf) — reference config (committed default: F13).
- [`.env.example`](./.env.example) — device ID and source key. Copy to `.env` and edit.
- [`scripts/apply.sh`](./scripts/apply.sh) — render config from `.env`, deploy, restart keyd.
- [`scripts/toggle.sh`](./scripts/toggle.sh) — flip between F13 and `Ctrl+Alt+Space`.
- [`scripts/gui.sh`](./scripts/gui.sh) — launcher for the PyQt6 GUI.
- [`gui/usb_button_remap.py`](./gui/usb_button_remap.py) — GUI source.
- [`docs/rationale.md`](./docs/rationale.md) — why keyd, not input-remapper; why F13.
