import os
import subprocess
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QDesktopServices, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QLineEdit,
)

from .aria2c import Aria2c

CONNECTION_PRESETS = {
    1: ("Normal", "1 thread, basic download"),
    4: ("Balanced", "4 threads, balanced speed & resources"),
    8: ("Fast", "8 threads, fast download"),
    16: ("Extreme", "16 threads, not recommended"),
}
SNAP_VALUES = [1, 4, 8, 16]


def _fmt_size(b):
    if b < 0:
        return "?"
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def _fmt_speed(bps):
    return _fmt_size(bps) + "/s"


def _fmt_eta(secs):
    if secs < 0 or secs > 86400 * 7:
        return "∞"
    secs = int(secs)
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


class StartupDialog(QDialog):
    def __init__(self, current=4, download_dir="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("QtAria Setup")
        self.setFixedSize(460, 280)
        self._value = current
        self._download_dir = download_dir
        self._setup_ui()
        self._set_value(current)

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(6)

        title = QLabel("Connection threads per download:")
        title.setStyleSheet("font-size: 13px;")
        layout.addWidget(title)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(3)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(1)
        self.slider.valueChanged.connect(self._on_change)
        layout.addWidget(self.slider)

        tick_layout = QHBoxLayout()
        tick_layout.setContentsMargins(3, 0, 3, 0)
        for v in SNAP_VALUES:
            lbl = QLabel(str(v))
            lbl.setAlignment(Qt.AlignCenter)
            tick_layout.addWidget(lbl)
        layout.addLayout(tick_layout)

        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        self.lbl_name = QLabel()
        self.lbl_name.setFont(font)
        self.lbl_name.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_name)

        self.lbl_hint = QLabel()
        self.lbl_hint.setAlignment(Qt.AlignCenter)
        self.lbl_hint.setStyleSheet("color: #888;")
        layout.addWidget(self.lbl_hint)

        # Directory chooser
        dir_layout = QHBoxLayout()
        dir_layout.setContentsMargins(0, 8, 0, 0)
        dir_label = QLabel("Download to:")
        dir_label.setStyleSheet("font-size: 12px;")
        dir_layout.addWidget(dir_label)

        self.lbl_dir = QLabel(self._download_dir)
        self.lbl_dir.setStyleSheet("color: #555;")
        self.lbl_dir.setWordWrap(True)
        dir_layout.addWidget(self.lbl_dir, 1)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(browse_btn)
        layout.addLayout(dir_layout)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        self.start_btn = QPushButton("Start")
        self.start_btn.setDefault(True)
        self.start_btn.clicked.connect(self.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.start_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _browse_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Download Directory", self._download_dir
        )
        if path:
            self._download_dir = path
            self.lbl_dir.setText(path)

    def _set_value(self, v):
        idx = SNAP_VALUES.index(v) if v in SNAP_VALUES else 1
        self.slider.setValue(idx)
        self._on_change(idx)

    def _on_change(self, idx):
        val = SNAP_VALUES[idx]
        self._value = val
        name, hint = CONNECTION_PRESETS[val]
        self.lbl_name.setText(name)
        self.lbl_hint.setText(hint)
        self.start_btn.setText(f"Start  ({val} threads)")

    def value(self):
        return self._value

    def download_dir(self):
        return self._download_dir


class DownloadWindow(QWidget):
    def __init__(self, gid, url, aria2: Aria2c, download_dir: str):
        super().__init__()
        self.gid = gid
        self.url = url
        self.aria2 = aria2
        self.download_dir = download_dir
        self.paused = False
        self.completed = False
        self._explicit_close = False
        self._filename = url.split("/")[-1] or "unknown"
        self._on_add_url = None

        self.setWindowTitle(f"QtAria — {self._filename}")
        self.setMinimumSize(420, 180)
        self._setup_ui()
        self._update_info("Starting...", 0)

        self.timer = QTimer()
        self.timer.timeout.connect(self._poll)
        self.timer.start(1000)

    def set_on_add_url(self, cb):
        self._on_add_url = cb

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(4)

        self.lbl_file = QLabel(self._filename)
        f = self.lbl_file.font()
        f.setPointSize(11)
        f.setBold(True)
        self.lbl_file.setFont(f)
        layout.addWidget(self.lbl_file)

        self.lbl_url = QLabel(f'<a href="{self.url}">{self.url}</a>')
        self.lbl_url.setOpenExternalLinks(True)
        self.lbl_url.setWordWrap(True)
        self.lbl_url.setStyleSheet("color: #555;")
        layout.addWidget(self.lbl_url)

        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFixedHeight(22)
        layout.addWidget(self.progress)

        self.lbl_info = QLabel()
        layout.addWidget(self.lbl_info)

        btn_layout = QHBoxLayout()
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._do_cancel)
        self.btn_open = QPushButton("Open Folder")
        self.btn_open.clicked.connect(self._open_folder)
        self.btn_add = QPushButton("+ Add URL")
        self.btn_add.clicked.connect(self._do_add_url)

        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_open)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_add)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _update_info(self, text, pct=None):
        if pct is not None:
            self.progress.setValue(pct)
            self.progress.setFormat(f"{pct}%")
        self.lbl_info.setText(text)

    def _poll(self):
        if self.completed:
            self.timer.stop()
            return

        s = self.aria2.tell_status(self.gid)
        if s is None:
            self._update_info("Connecting...")
            return
        if isinstance(s, dict) and "_error" in s:
            self._update_info(f"Error: {s['_error']}")
            return

        total = int(s.get("totalLength", 0))
        completed = int(s.get("completedLength", 0))
        speed = int(s.get("downloadSpeed", 0))
        state = s.get("status", "")

        if total > 0:
            pct = min(int(completed / total * 100), 100)
            self.progress.setValue(pct)
            self.progress.setFormat(f"{pct}%")
        else:
            pct = 0

        size_str = f"{_fmt_size(completed)} / {_fmt_size(total)}"
        speed_str = _fmt_speed(speed)

        if state == "complete":
            self.completed = True
            self._update_info(f"Completed  —  {size_str}", 100)
            self.progress.setStyleSheet("QProgressBar::chunk { background: #4caf50; }")
            self.btn_pause.setEnabled(False)
            self.btn_cancel.setText("Close")
            self.btn_cancel.clicked.disconnect()
            self.btn_cancel.clicked.connect(self.close)
            self._notify()
            self.timer.stop()
        elif state == "error":
            err = s.get("errorMessage", "Unknown error")
            self._update_info(f"Error: {err}", pct)
        elif state == "paused":
            self.paused = True
            self.btn_pause.setText("Resume")
            self._update_info(f"Paused  —  {size_str}", pct)
        elif state in ("active", "waiting"):
            self.paused = False
            self.btn_pause.setText("Pause")
            if speed > 0 and total > 0:
                eta = (total - completed) / speed
                self._update_info(
                    f"Speed: {speed_str}  |  ETA: {_fmt_eta(eta)}  |  {size_str}", pct
                )
            else:
                self._update_info(f"Speed: {speed_str}  |  {size_str}", pct)
        else:
            self._update_info(f"Status: {state}  |  {size_str}", pct)

    def _toggle_pause(self):
        if self.paused:
            self.aria2.unpause(self.gid)
        else:
            self.aria2.pause(self.gid)

    def _do_cancel(self):
        self.aria2.remove(self.gid)
        self._explicit_close = True
        self.close()

    def _open_folder(self):
        QDesktopServices.openUrl(
            "file:///" + os.path.abspath(self.download_dir)
        )

    def _do_add_url(self):
        if self._on_add_url:
            self._on_add_url()

    def _notify(self):
        try:
            subprocess.run(
                [
                    "notify-send",
                    "QtAria — Download Complete",
                    self._filename,
                    "-i",
                    "dialog-information",
                ],
                timeout=2,
            )
        except Exception:
            pass

    def closeEvent(self, event):
        if self.completed or self._explicit_close:
            event.accept()
            return
        reply = QMessageBox.question(
            self,
            "Cancel Download?",
            "Are you sure you want to cancel this download?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.aria2.remove(self.gid)
            event.accept()
        else:
            event.ignore()
