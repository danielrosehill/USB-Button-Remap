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

```bash
sudo apt install keyd
sudo systemctl enable --now keyd
```

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

## Files

- [`usb-button.conf`](./usb-button.conf) — reference config (committed default: F13).
- [`.env.example`](./.env.example) — device ID and source key. Copy to `.env` and edit.
- [`scripts/apply.sh`](./scripts/apply.sh) — render config from `.env`, deploy, restart keyd.
- [`scripts/toggle.sh`](./scripts/toggle.sh) — flip between F13 and `Ctrl+Alt+Space`.
- [`docs/rationale.md`](./docs/rationale.md) — why keyd, not input-remapper; why F13.
