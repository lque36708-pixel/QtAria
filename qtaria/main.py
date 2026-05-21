import sys
import traceback
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox

from . import config as cfg
from .aria2c import Aria2c
from .httpd import Server
from .gui import StartupDialog, DownloadWindow


def log(msg):
    print(f"[QtAria] {msg}", file=sys.stderr, flush=True)


def main():
    log("starting")

    conf = cfg.load()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("QtAria")

    # Start HTTP server FIRST so host.py can connect and queue URLs
    # while the user is still on the startup dialog
    httpd = Server(host="localhost", port=conf["http_port"])
    httpd.start()
    log(f"HTTP server on :{conf['http_port']}")

    dialog = StartupDialog(conf["connections"])
    if dialog.exec() != StartupDialog.Accepted:
        return

    connections = dialog.value()
    conf["connections"] = connections
    cfg.save(conf)
    log(f"connections={connections}")

    aria2 = Aria2c(port=conf["rpc_port"], secret=conf["rpc_secret"])
    ok = aria2.start_daemon(
        connections=connections, download_dir=conf["download_dir"]
    )
    if not ok:
        log("aria2c not responding")
        QMessageBox.warning(
            None, "QtAria",
            "aria2c did not start or is not responding.\n"
            "Make sure aria2 is installed:\n"
            "  sudo apt install aria2\n"
            "Downloads will be queued but cannot start.",
        )
    else:
        log("aria2c ready")

    _windows = set()
    _closing = False

    def _on_window_closed(obj=None):
        nonlocal _closing
        if _closing:
            return
        if not _windows:
            _closing = True
            QTimer.singleShot(0, app.quit)

    def open_add_url_dialog():
        url, ok = QInputDialog.getText(
            None, "Add URL", "Enter download URL:",
            QLineEdit.Normal, "",
        )
        if ok and url.strip():
            _add_download(url.strip())

    def _add_download(url):
        log(f"adding download: {url[:80]}")
        gid = aria2.add_uri(url)
        if gid is None:
            log("aria2c not responding")
            QMessageBox.warning(
                None, "QtAria",
                "Cannot connect to aria2c.\n"
                "Make sure aria2 is running:\n"
                "  sudo apt install aria2",
            )
            return
        if isinstance(gid, dict) and "_error" in gid:
            log(f"aria2 error: {gid['_error']}")
            QMessageBox.warning(
                None, "QtAria",
                f"Failed to add download:\n{gid['_error']}",
            )
            return
        log(f"got gid={gid}, creating window")
        try:
            win = DownloadWindow(gid, url, aria2, conf["download_dir"])
            win.set_on_add_url(open_add_url_dialog)
            _windows.add(win)
            win.destroyed.connect(lambda obj=None, w=win: _windows.discard(w))
            win.destroyed.connect(_on_window_closed)
            win.show()
            log("window shown, references held")
        except Exception as e:
            log(f"window creation failed: {e}\n{traceback.format_exc()}")

    def poll_queue():
        while True:
            item = httpd.get_url()
            if not item:
                break
            url, _ = item
            _add_download(url)

    # Schedule queue processing after event loop starts
    # (calling poll_queue directly before app.exec() can prevent windows from appearing)
    QTimer.singleShot(0, poll_queue)

    timer = QTimer()
    timer.timeout.connect(poll_queue)
    timer.start(500)

    app.aboutToQuit.connect(aria2.stop_daemon)
    sys.exit(app.exec())
