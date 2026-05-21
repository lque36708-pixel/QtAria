import sys
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox

from . import config as cfg
from .aria2c import Aria2c
from .httpd import Server
from .gui import StartupDialog, DownloadWindow


def main():
    conf = cfg.load()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("QtAria")

    dialog = StartupDialog(conf["connections"])
    if dialog.exec() != StartupDialog.Accepted:
        return

    connections = dialog.value()
    conf["connections"] = connections
    cfg.save(conf)

    aria2 = Aria2c(port=conf["rpc_port"], secret=conf["rpc_secret"])
    ok = aria2.start_daemon(
        connections=connections, download_dir=conf["download_dir"]
    )
    if not ok:
        QMessageBox.warning(None, "QtAria", "Could not connect to aria2c.\n"
                             "Make sure aria2 is installed.")

    httpd = Server(host="localhost", port=conf["http_port"])
    httpd.start()

    _closing = False

    def _on_window_closed(obj=None):
        nonlocal _closing
        if _closing:
            return
        for w in app.topLevelWidgets():
            if isinstance(w, DownloadWindow):
                return
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
        gid = aria2.add_uri(url)
        if gid is None:
            QMessageBox.warning(None, "QtAria",
                                "aria2c is not responding.")
            return
        if isinstance(gid, dict) and "_error" in gid:
            QMessageBox.warning(None, "QtAria", gid["_error"])
            return
        win = DownloadWindow(gid, url, aria2, conf["download_dir"])
        win.set_on_add_url(open_add_url_dialog)
        win.destroyed.connect(_on_window_closed)
        win.show()

    def poll_queue():
        item = httpd.get_url()
        if item:
            url, _ = item
            _add_download(url)

    timer = QTimer()
    timer.timeout.connect(poll_queue)
    timer.start(500)

    app.aboutToQuit.connect(aria2.stop_daemon)

    sys.exit(app.exec())
