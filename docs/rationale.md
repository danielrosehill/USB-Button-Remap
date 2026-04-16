# Rationale: why keyd, not input-remapper

The goal of this setup is to remap a cheap AliExpress single-button USB HID device so a button press triggers a speech-to-text / transcription hotkey. Requirements that drove the tool choice:

1. **Map as deep in the system / as close to the kernel as possible** — fewer userspace layers between the physical press and the emitted keycode.
2. **Survive everything** — active at the TTY, at the display-manager login screen, across Wayland and X11 sessions, after suspend/resume, without per-user session setup.
3. **Device-scoped** — must not affect the real keyboard's `2` key.
4. **Versionable** — plain-text config that fits in a repo.

Both [`keyd`](https://github.com/rvaiya/keyd) and [`input-remapper`](https://github.com/sezanzeb/input-remapper) ultimately use the same Linux kernel primitives — `evdev` to read the physical device, `uinput` to inject synthesized events. Neither runs in the kernel. The difference is how much userspace sits between those two interfaces, and when that userspace comes up in the boot sequence.

## keyd

- Small C daemon. Path from press to synthesized key is: evdev read → keyd rules → uinput write. No Python, no GTK, no DBus, no X11/Wayland assumptions.
- Runs as a **system** `systemd` unit started at boot, before any user session. Mappings are live at the TTY and at SDDM/GDM, not just after login.
- `[ids]` section scopes the remap to a specific `vendor:product`. The real keyboard's `2` is untouched.
- Declarative two-line config at `/etc/keyd/*.conf`. Trivial to check into git.
- Supports layers, macros, chording, timeouts, and per-app overlays when you need them; you only pay for the complexity you use.

Trade-offs:

- No GUI. Syntax (`C-A-space`, `macro(...)`, overloads) has to be read from the man page.
- `systemctl reload keyd` is not supported; use `restart`.
- Smaller community than input-remapper, single main maintainer.

## input-remapper

- GUI-first. Click a device, press the button, pick a target key or combo. Zero syntax to memorize.
- Rich feature set: key-to-mouse, gamepad remapping, per-preset autoload.
- Packaged in Ubuntu's default repos; large user community.

Trade-offs relevant to the stated goals:

- Per-user. The helper that applies presets runs in the user session; mappings are **not** active at the TTY or at the login screen. For a transcription button on a desktop that's always logged in, fine — but it's further from "deep in the system."
- Longer userspace path: Python helper → DBus → service → uinput. More moving parts, more failure modes (stuck helper after suspend, preset not auto-loaded, GUI and service fighting over the device).
- Config lives in `~/.config/input-remapper-2/` as JSON. Versionable, but not as direct to deploy as a single file under `/etc/`.

## Conclusion

For a single button that must fire reliably every time, ideally before a user session even exists, keyd is the right tool. It runs earlier, it runs as root system-wide, and it has the shorter userspace path to `uinput`. input-remapper's strengths — GUI, game controllers, per-app presets — aren't relevant to this workflow.

## One practical note on the target key

`F13` is the preferred target here because it doesn't exist on normal keyboards, so it can't collide with any existing shortcut in KDE, the IME, or an app. `Ctrl+Alt+Space` is available as an alternative for cases where the consuming app insists on a modifier combo; flip between the two with `scripts/toggle.sh`.
