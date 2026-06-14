from __future__ import annotations

import json
import mimetypes
import socket
import threading
import time
import webbrowser
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import __version__
from .config import AppConfig, load_config, save_config
from .pipeline import PipelineResult, run_pipeline
from .presets import preset_payload
from .watcher import PollingWatcher


STATIC_DIR = Path(__file__).resolve().parent / "static"


class LogBuffer:
    def __init__(self, limit: int = 1000) -> None:
        self._limit = limit
        self._items: list[dict[str, Any]] = []
        self._next_id = 1
        self._lock = threading.Lock()

    def add(self, level: str, message: str) -> None:
        with self._lock:
            entry = {
                "id": self._next_id,
                "time": time.strftime("%H:%M:%S"),
                "level": level,
                "message": message,
            }
            self._next_id += 1
            self._items.append(entry)
            if len(self._items) > self._limit:
                self._items = self._items[-self._limit :]

    def after(self, last_id: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            return [item for item in self._items if int(item["id"]) > last_id]


class AppState:
    def __init__(self) -> None:
        self.config = load_config()
        self.logs = LogBuffer()
        self._lock = threading.RLock()
        self._pipeline_lock = threading.Lock()
        self.last_result: PipelineResult | None = None
        self.watcher = PollingWatcher(self.get_config, self.run_pipeline, self.log)
        self.log("info", "Application ready.")

    def log(self, level: str, message: str) -> None:
        self.logs.add(level, message)
        print(f"[{level.upper()}] {message}", flush=True)

    def get_config(self) -> AppConfig:
        with self._lock:
            return AppConfig.from_dict(self.config.to_dict())

    def update_config(self, payload: dict[str, Any]) -> AppConfig:
        with self._lock:
            self.config.update_from_dict(payload)
            path = save_config(self.config)
            updated = AppConfig.from_dict(self.config.to_dict())
        self.log("info", f"Settings saved: {path}")
        return updated

    def run_pipeline(self, reason: str = "manual run") -> PipelineResult:
        if not self._pipeline_lock.acquire(blocking=False):
            result = PipelineResult(False, messages=["Pipeline is already running."])
            self.log("warning", "Pipeline skipped: another run is active.")
            return result

        try:
            self.log("info", f"Pipeline started ({reason}).")
            result = run_pipeline(self.get_config(), logger=lambda msg: self.log("info", msg))
            self.last_result = result
            if result.ok:
                self.log("info", "Pipeline finished successfully.")
            else:
                self.log("error", "Pipeline finished with errors.")
            return result
        finally:
            self._pipeline_lock.release()

    def state_payload(self) -> dict[str, Any]:
        watcher_status = self.watcher.status()
        result = self.last_result
        return {
            "version": __version__,
            "config": self.get_config().to_dict(),
            "watcher": asdict(watcher_status),
            "last_result": asdict(result) if result else None,
            "presets": preset_payload(),
        }


class WatchDogHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], handler_class: type[BaseHTTPRequestHandler]):
        super().__init__(server_address, handler_class)
        self.state = AppState()


class RequestHandler(BaseHTTPRequestHandler):
    server: WatchDogHTTPServer

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_static_file(STATIC_DIR / "index.html")
            return
        if parsed.path.startswith("/static/"):
            relative = parsed.path.removeprefix("/static/").strip("/")
            self.send_static_file(STATIC_DIR / relative)
            return
        if parsed.path == "/api/state":
            self.send_json(self.server.state.state_payload())
            return
        if parsed.path == "/api/logs":
            query = parse_qs(parsed.query)
            after = int(query.get("after", ["0"])[0] or 0)
            self.send_json({"logs": self.server.state.logs.after(after)})
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "Route not found.")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/config":
            payload = self.read_json()
            if payload is None:
                return
            if self.server.state.watcher.status().running:
                self.send_error_json(HTTPStatus.CONFLICT, "Stop the watcher before changing settings.")
                return
            config = self.server.state.update_config(payload)
            self.send_json({"ok": True, "config": config.to_dict()})
            return

        if parsed.path == "/api/run":
            result = self.server.state.run_pipeline("manual run")
            self.send_json({"ok": result.ok, "result": asdict(result)})
            return

        if parsed.path == "/api/watch/start":
            started = self.server.state.watcher.start()
            self.send_json({"ok": True, "started": started, "watcher": asdict(self.server.state.watcher.status())})
            return

        if parsed.path == "/api/watch/stop":
            stopped = self.server.state.watcher.stop()
            self.send_json({"ok": True, "stopped": stopped, "watcher": asdict(self.server.state.watcher.status())})
            return

        if parsed.path == "/api/dialog/project":
            self.handle_folder_dialog()
            return

        if parsed.path == "/api/dialog/conversation":
            self.handle_file_dialog()
            return

        if parsed.path == "/api/shutdown":
            self.send_json({"ok": True})
            threading.Thread(target=self.shutdown_server, daemon=True).start()
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "Route not found.")

    def read_json(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}

        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Invalid JSON.")
            return None

        if not isinstance(data, dict):
            self.send_error_json(HTTPStatus.BAD_REQUEST, "JSON body must be an object.")
            return None
        return data

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"ok": False, "error": message}, status=status)

    def send_static_file(self, path: Path) -> None:
        try:
            resolved = path.resolve()
            static_root = STATIC_DIR.resolve()
            resolved.relative_to(static_root)
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return

        if not resolved.exists() or not resolved.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        data = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_folder_dialog(self) -> None:
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected = filedialog.askdirectory(title="Select project folder")
            root.destroy()
            self.send_json({"ok": True, "path": selected})
        except Exception as exc:
            self.server.state.log("error", f"Folder dialog failed: {exc}")
            self.send_json({"ok": False, "error": str(exc)})

    def handle_file_dialog(self) -> None:
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected = filedialog.askopenfilename(
                title="Select LM Studio conversation JSON",
                filetypes=[("Conversation JSON", "*.conversation.json"), ("JSON files", "*.json"), ("All files", "*.*")],
            )
            root.destroy()
            self.send_json({"ok": True, "path": selected})
        except Exception as exc:
            self.server.state.log("error", f"File dialog failed: {exc}")
            self.send_json({"ok": False, "error": str(exc)})

    def shutdown_server(self) -> None:
        self.server.state.log("info", "Shutting down application.")
        self.server.state.watcher.stop()
        self.server.shutdown()


def find_available_port(host: str, preferred: int) -> int:
    if preferred == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])

    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise OSError(f"No available port found from {preferred} to {preferred + 49}.")


def run_web_app(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> str:
    active_port = find_available_port(host, port)
    server = WatchDogHTTPServer((host, active_port), RequestHandler)
    url = f"http://{host}:{active_port}/"

    print("=" * 72, flush=True)
    print("LM Studio Watch Dog", flush=True)
    print(f"URL: {url}", flush=True)
    print("=" * 72, flush=True)

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.state.log("info", "Keyboard interrupt received.")
    finally:
        server.state.watcher.stop()
        server.server_close()

    return url
