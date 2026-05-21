import json
import queue
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


class _Handler(BaseHTTPRequestHandler):
    request_queue = None

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        data = json.loads(body)
        url = data.get("url", "")
        filename = data.get("filename", "")
        if url:
            self.__class__.request_queue.put((url, filename))
        self._ok()

    def do_GET(self):
        if urlparse(self.path).path == "/ping":
            self._ok()
        else:
            self.send_response(404)
            self.end_headers()

    def _ok(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())

    def log_message(self, fmt, *args):
        pass


def run(host, port, q):
    _Handler.request_queue = q
    server = HTTPServer((host, port), _Handler)
    server.serve_forever()


class Server:
    def __init__(self, host="localhost", port=16800):
        self.host = host
        self.port = port
        self.queue = queue.Queue()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(
            target=run, args=(self.host, self.port, self.queue), daemon=True
        )
        self.thread.start()

    def get_url(self, timeout=0.3):
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None
