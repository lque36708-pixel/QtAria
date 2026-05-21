import json
import os

CONFIG_DIR = os.path.expanduser("~/.config/qtaria")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
ARIA2_DIR = os.path.expanduser("~/Downloads")
OLD_ARIA2_DIR = os.path.expanduser("~/Downloads/QtAria")  # migrate from old default

DEFAULT_CONFIG = {
    "connections": 4,
    "download_dir": ARIA2_DIR,
    "rpc_port": 6800,
    "rpc_secret": "qtaria",
    "http_port": 16800,
}


def ensure_dirs():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(ARIA2_DIR, exist_ok=True)


def load():
    ensure_dirs()
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            saved = json.load(f)
        cfg = {**cfg, **saved}
        # migrate old download dir
        if cfg.get("download_dir") == OLD_ARIA2_DIR:
            cfg["download_dir"] = ARIA2_DIR
            save(cfg)
    return cfg


def save(cfg):
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
