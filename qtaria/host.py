#!/usr/bin/env python3
"""
Native messaging host for Chrome extension.
Chrome communicates via stdin/stdout with length-prefixed JSON messages.
"""
import json
import os
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTTP_PORT = 16800


def _read_msg():
    raw = sys.stdin.buffer.read(4)
    if not raw or len(raw) < 4:
        return None
    length = struct.unpack("=I", raw)[0]
    if length == 0:
        return None
    return json.loads(sys.stdin.buffer.read(length))


def _write_msg(msg):
    data = json.dumps(msg).encode()
    sys.stdout.buffer.write(struct.pack("=I", len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def _is_running():
    try:
        req = urllib.request.Request(f"http://localhost:{HTTP_PORT}/ping")
        with urllib.request.urlopen(req, timeout=1):
            return True
    except Exception:
        return False


def _launch_qtaria():
    python = sys.executable or "python3"
    subprocess.Popen(
        [python, "-m", "qtaria"],
        cwd=PROJECT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _send_url(url):
    data = json.dumps({"url": url}).encode()
    req = urllib.request.Request(
        f"http://localhost:{HTTP_PORT}/add",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def main():
    msg = _read_msg()
    if msg is None:
        return

    url = msg.get("url", "")
    if not url:
        _write_msg({"ok": False, "error": "No URL provided"})
        return

    if not _is_running():
        _launch_qtaria()
        for _ in range(30):
            time.sleep(0.5)
            if _is_running():
                break
        else:
            _write_msg({
                "ok": False,
                "error": "QtAria did not start. "
                         "Run 'python3 -m qtaria' manually to see errors.",
            })
            return

    try:
        _send_url(url)
        _write_msg({"ok": True})
    except urllib.error.HTTPError as e:
        _write_msg({"ok": False, "error": f"QtAria rejected the URL (HTTP {e.code})"})
    except urllib.error.URLError as e:
        _write_msg({"ok": False, "error": f"Cannot reach QtAria: {e.reason}"})
    except Exception as e:
        _write_msg({"ok": False, "error": f"Unexpected error: {e}"})


if __name__ == "__main__":
    main()
