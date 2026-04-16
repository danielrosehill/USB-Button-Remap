#!/usr/bin/python3
"""USB Button Remap — GUI frontend for the keyd-based button remap in this repo.

Flow:
  1. Scan input devices, score each by "is-this-a-simple-button" heuristic.
  2. Optionally, press-to-detect (stops keyd briefly, listens on plausible
     devices, captures first keypress, restarts keyd).
  3. Choose target: F13 (default), Ctrl+Alt+Space, or custom keyd RHS.
  4. Apply — writes .env, invokes scripts/apply.sh via pkexec.

Runs as the user (requires membership in the `input` group to read
/dev/input/event*). Privileged steps (systemctl, writing /etc/keyd/) are
delegated to pkexec prompts.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import evdev
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QRadioButton, QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
APPLY_SCRIPT = REPO_ROOT / "scripts" / "apply.sh"
TOGGLE_SCRIPT = REPO_ROOT / "scripts" / "toggle.sh"
ENV_FILE = REPO_ROOT / ".env"
KEYD_CONFIG = Path("/etc/keyd/usb-button.conf")


# ---------------------------------------------------------------- scoring

@dataclass
class Candidate:
    path: str
    name: str
    vendor: int
    product: int
    key_count: int
    has_rel: bool
    has_abs: bool
    has_leds: bool
    score: int = 0

    @property
    def vid_pid(self) -> str:
        return f"{self.vendor:04x}:{self.product:04x}"

    def display(self) -> str:
        flags = []
        if self.has_rel: flags.append("mouse-axis")
        if self.has_abs: flags.append("tablet/touch-axis")
        if self.has_leds: flags.append("leds")
        flag_str = f"  [{', '.join(flags)}]" if flags else ""
        return f"{self.name}  ·  {self.vid_pid}  ·  {self.key_count} keys{flag_str}"


def scan_devices() -> list[Candidate]:
    """Return evdev devices, scored: higher = more likely to be a simple button.

    Heuristics for a cheap single-button HID puck:
      - Few distinct keys in EV_KEY capabilities (1–8 is the sweet spot).
      - No EV_REL (not a mouse), no EV_ABS (not a tablet/touchpad).
      - No LEDs (full keyboards have Caps/Num/Scroll lock LEDs).
      - Non-zero vendor (exclude synthetic kernel devices like power button).
    """
    out: list[Candidate] = []
    for path in evdev.list_devices():
        try:
            d = evdev.InputDevice(path)
        except (PermissionError, OSError):
            continue
        try:
            if d.info.vendor == 0:
                continue
            caps = d.capabilities()
            keys = caps.get(evdev.ecodes.EV_KEY, [])
            has_rel = evdev.ecodes.EV_REL in caps
            has_abs = evdev.ecodes.EV_ABS in caps
            has_leds = evdev.ecodes.EV_LED in caps

            score = 100
            score -= min(len(keys), 90)   # each capability-key costs a point
            if has_rel: score -= 60
            if has_abs: score -= 60
            if has_leds: score -= 30
            if 1 <= len(keys) <= 8: score += 40  # sweet-spot bonus

            out.append(Candidate(
                path=path, name=d.name, vendor=d.info.vendor,
                product=d.info.product, key_count=len(keys),
                has_rel=has_rel, has_abs=has_abs, has_leds=has_leds,
                score=score,
            ))
        finally:
            d.close()
    return sorted(out, key=lambda c: -c.score)


# ---------------------------------------------------------------- capture

class CaptureThread(QThread):
    captured = pyqtSignal(str, str, int)  # device_path, key_name, key_code

    def __init__(self, device_path: str, parent=None):
        super().__init__(parent)
        self.device_path = device_path
        self._stop = False

    def run(self):
        try:
            d = evdev.InputDevice(self.device_path)
        except Exception:
            return
        try:
            try:
                d.grab()
            except Exception:
                pass  # another process (keyd?) still holds it — keep going ungrabbed
            for event in d.read_loop():
                if self._stop:
                    return
                if event.type == evdev.ecodes.EV_KEY and event.value == 1:
                    name = evdev.ecodes.keys.get(event.code, f"KEY_{event.code}")
                    if isinstance(name, list):
                        name = name[0]
                    self.captured.emit(self.device_path, str(name), event.code)
                    return
        finally:
            try: d.ungrab()
            except Exception: pass
            try: d.close()
            except Exception: pass

    def stop(self):
        self._stop = True


# ---------------------------------------------------------------- main window

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USB Button Remap")
        self.resize(760, 620)

        self.selected: Candidate | None = None
        self.source_key: str = "2"
        self._capture_threads: list[CaptureThread] = []
        self._capture_consumed = False

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.page_device = self._build_device_page()
        self.page_target = self._build_target_page()
        self.page_result = self._build_result_page()
        self.stack.addWidget(self.page_device)
        self.stack.addWidget(self.page_target)
        self.stack.addWidget(self.page_result)

        self.refresh_devices()

    # -------- page 1: device selection --------

    def _build_device_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        title = QLabel("1. Pick your USB button")
        f = QFont(); f.setPointSize(14); f.setBold(True); title.setFont(f)
        layout.addWidget(title)

        hint = QLabel(
            "Devices are sorted by how likely they are to be a single-button HID puck. "
            "Fewer keys + no mouse/tablet axes + no LEDs ranks higher. "
            "Your regular keyboard and mouse will appear near the bottom."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        self.device_list = QListWidget()
        self.device_list.itemSelectionChanged.connect(self._on_device_selected)
        layout.addWidget(self.device_list, stretch=1)

        row = QHBoxLayout()
        refresh = QPushButton("Refresh list")
        refresh.clicked.connect(self.refresh_devices)
        detect = QPushButton("Detect by pressing the button…")
        detect.clicked.connect(self.start_capture)
        row.addWidget(refresh); row.addStretch(); row.addWidget(detect)
        layout.addLayout(row)

        self.capture_status = QLabel("")
        self.capture_status.setStyleSheet("color: #888;")
        self.capture_status.setWordWrap(True)
        layout.addWidget(self.capture_status)

        nav = QHBoxLayout(); nav.addStretch()
        nxt = QPushButton("Next →"); nxt.clicked.connect(self._goto_target)
        nav.addWidget(nxt)
        layout.addLayout(nav)

        return w

    def refresh_devices(self):
        self.device_list.clear()
        for c in scan_devices():
            it = QListWidgetItem(c.display())
            it.setData(Qt.ItemDataRole.UserRole, c)
            # dim devices that are clearly not buttons (mouse/tablet)
            if c.has_rel or c.has_abs or c.has_leds:
                it.setForeground(Qt.GlobalColor.gray)
            self.device_list.addItem(it)

    def _on_device_selected(self):
        row = self.device_list.currentRow()
        if row < 0: return
        self.selected = self.device_list.item(row).data(Qt.ItemDataRole.UserRole)

    def start_capture(self):
        # Confirm: keyd will be stopped briefly so it releases its grab.
        confirm = QMessageBox.question(
            self, "Detect key",
            "This will briefly stop keyd, listen for the next keypress on likely "
            "button devices, then restart keyd.\n\n"
            "You may see a polkit prompt to authorize stopping/starting keyd.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Ok:
            return

        self.capture_status.setText("Stopping keyd…")
        QApplication.processEvents()

        rc = subprocess.run(
            ["pkexec", "systemctl", "stop", "keyd"],
            capture_output=True, text=True,
        ).returncode
        if rc != 0:
            self.capture_status.setText("Could not stop keyd (pkexec cancelled?). Aborting.")
            return

        self.capture_status.setText("Press your USB button now…")
        self._capture_consumed = False
        self._capture_threads = []
        for i in range(self.device_list.count()):
            c: Candidate = self.device_list.item(i).data(Qt.ItemDataRole.UserRole)
            # Only listen on plausible button devices — skip mice/tablets/full keyboards
            if c.has_rel or c.has_abs: continue
            if c.key_count > 40: continue
            t = CaptureThread(c.path, self)
            t.captured.connect(self._on_any_captured)
            t.start()
            self._capture_threads.append(t)

    def _on_any_captured(self, device_path: str, key_name: str, key_code: int):
        if self._capture_consumed:
            return
        self._capture_consumed = True

        for t in self._capture_threads:
            t.stop()

        subprocess.run(["pkexec", "systemctl", "start", "keyd"],
                       capture_output=True, text=True)

        # Find the candidate
        cand = None
        for i in range(self.device_list.count()):
            c: Candidate = self.device_list.item(i).data(Qt.ItemDataRole.UserRole)
            if c.path == device_path:
                cand = c
                self.device_list.setCurrentRow(i)
                break
        if cand is None:
            self.capture_status.setText(f"Captured {key_name}, but could not map it back to a device.")
            return

        self.selected = cand
        self.source_key = self._keyd_key_name(key_name)
        self.capture_status.setText(
            f"✔ Detected: {cand.name}  ·  {cand.vid_pid}  ·  "
            f"key {key_name}  (keyd name: {self.source_key})"
        )

    @staticmethod
    def _keyd_key_name(ev_name: str) -> str:
        s = ev_name
        if s.startswith("KEY_"):
            s = s[4:]
        return s.lower()

    def _goto_target(self):
        if self.selected is None:
            row = self.device_list.currentRow()
            if row < 0:
                QMessageBox.warning(self, "Pick a device",
                                    "Select a device from the list or use Detect.")
                return
            self.selected = self.device_list.item(row).data(Qt.ItemDataRole.UserRole)

        self.summary_label.setText(
            f"Device: {self.selected.name}  ({self.selected.vid_pid})\n"
            f"Source key: {self.source_key}"
        )
        self._load_current_config()
        self.stack.setCurrentWidget(self.page_target)

    # -------- page 2: target --------

    def _build_target_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        title = QLabel("2. Choose the target key")
        f = QFont(); f.setPointSize(14); f.setBold(True); title.setFont(f)
        layout.addWidget(title)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #666;")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.current_label = QLabel("")
        self.current_label.setStyleSheet("color: #888; font-family: monospace;")
        self.current_label.setWordWrap(True)
        layout.addWidget(self.current_label)

        box = QGroupBox("Target")
        gl = QVBoxLayout(box)
        self.rb_f13 = QRadioButton("F13 — collision-free function key (recommended)")
        self.rb_combo = QRadioButton("Ctrl+Alt+Space — for apps that need a modifier combo")
        self.rb_custom = QRadioButton("Custom keyd expression")
        self.custom_edit = QLineEdit()
        self.custom_edit.setPlaceholderText("e.g.  M-space   or   macro(C-c 200 C-v)")
        self.custom_edit.setEnabled(False)
        self.rb_custom.toggled.connect(self.custom_edit.setEnabled)

        self.bg = QButtonGroup(self)
        self.bg.addButton(self.rb_f13); self.bg.addButton(self.rb_combo); self.bg.addButton(self.rb_custom)
        self.rb_f13.setChecked(True)

        gl.addWidget(self.rb_f13); gl.addWidget(self.rb_combo)
        gl.addWidget(self.rb_custom); gl.addWidget(self.custom_edit)
        layout.addWidget(box)

        nav = QHBoxLayout()
        back = QPushButton("← Back")
        back.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_device))
        apply_btn = QPushButton("Apply")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self.apply_mapping)
        nav.addWidget(back); nav.addStretch(); nav.addWidget(apply_btn)
        layout.addLayout(nav)
        layout.addStretch()
        return w

    def _chosen_target(self) -> str:
        if self.rb_f13.isChecked(): return "f13"
        if self.rb_combo.isChecked(): return "C-A-space"
        return self.custom_edit.text().strip() or "f13"

    def apply_mapping(self):
        if not self.selected:
            QMessageBox.warning(self, "No device", "Pick a device first."); return

        target = self._chosen_target()
        try:
            ENV_FILE.write_text(
                f"DEVICE_ID={self.selected.vid_pid}\nSOURCE_KEY={self.source_key}\n"
            )
        except Exception as e:
            QMessageBox.critical(self, "Could not write .env", str(e)); return

        p = subprocess.run(
            ["pkexec", str(APPLY_SCRIPT), target],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        out = (p.stdout or "") + (p.stderr or "")
        self.result_text.setPlainText(
            f"Target: {target}\n"
            f"Device: {self.selected.vid_pid}  ·  source key: {self.source_key}\n"
            f"Exit: {p.returncode}\n"
            f"---\n{out}"
        )
        self._load_current_config()
        self.stack.setCurrentWidget(self.page_result)

    # -------- page 3: result --------

    def _build_result_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        title = QLabel("3. Applied")
        f = QFont(); f.setPointSize(14); f.setBold(True); title.setFont(f)
        layout.addWidget(title)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("monospace"))
        layout.addWidget(self.result_text, stretch=1)

        nav = QHBoxLayout()
        toggle = QPushButton("Toggle F13 ↔ Ctrl+Alt+Space")
        toggle.clicked.connect(self.toggle_mapping)
        restart = QPushButton("Start over")
        restart.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_device))
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        nav.addWidget(toggle); nav.addWidget(restart); nav.addStretch(); nav.addWidget(close)
        layout.addLayout(nav)
        return w

    def toggle_mapping(self):
        p = subprocess.run(
            ["pkexec", str(TOGGLE_SCRIPT)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        self.result_text.setPlainText(
            f"Exit: {p.returncode}\n---\n{(p.stdout or '') + (p.stderr or '')}"
        )
        self._load_current_config()

    def _load_current_config(self):
        try:
            txt = KEYD_CONFIG.read_text().strip()
            self.current_label.setText(f"Current /etc/keyd/usb-button.conf:\n{txt}")
        except Exception:
            self.current_label.setText("Current /etc/keyd/usb-button.conf: (not readable)")


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
