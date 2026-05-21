import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request

RPC_PORT = 6800
RPC_SECRET = "qtaria"


class Aria2c:
    def __init__(self, port=RPC_PORT, secret=RPC_SECRET):
        self.base = f"http://localhost:{port}/jsonrpc"
        self.secret = secret
        self.proc = None
        self.port = port

    def _call(self, method, params=None):
        if params is None:
            params = []
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": [f"token:{self.secret}", *params],
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            self.base,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read())
                if "error" in result:
                    return {"_error": result["error"]["message"]}
                return result.get("result")
        except (urllib.error.URLError, ConnectionRefusedError):
            return None
        except socket.timeout:
            return {"_error": "aria2c timed out"}
        except (json.JSONDecodeError, ValueError):
            return {"_error": "invalid response from aria2c"}
        except OSError as e:
            return {"_error": f"system error: {e}"}

    def add_uri(self, uri, options=None):
        opts = options or {}
        return self._call("aria2.addUri", [[uri], opts])

    def tell_status(self, gid):
        return self._call("aria2.tellStatus", [gid])

    def tell_active(self):
        return self._call("aria2.tellActive")

    def tell_waiting(self, offset=0, num=100):
        return self._call("aria2.tellWaiting", [offset, num])

    def pause(self, gid):
        return self._call("aria2.pause", [gid])

    def unpause(self, gid):
        return self._call("aria2.unpause", [gid])

    def remove(self, gid):
        return self._call("aria2.remove", [gid])

    def get_global_stat(self):
        return self._call("aria2.getGlobalStat")

    def start_daemon(self, connections=4, download_dir=None):
        cmd = [
            "aria2c",
            "--enable-rpc",
            f"--rpc-listen-port={self.port}",
            f"--rpc-secret={self.secret}",
            "--continue=true",
            f"--dir={download_dir or os.path.expanduser('~/Downloads')}",
            f"--split={connections}",
            f"--max-connection-per-server={connections}",
            "--console-log-level=error",
            "--summary-interval=0",
        ]
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            return "aria2c_not_found"
        except OSError as e:
            return f"spawn_error: {e}"
        for _ in range(20):
            if self._call("aria2.getGlobalStat") is not None:
                return True
            time.sleep(0.3)
        return False

    def stop_daemon(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
            self.proc = None

    def is_ready(self):
        return self._call("aria2.getGlobalStat") is not None
