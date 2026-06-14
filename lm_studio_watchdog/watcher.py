from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from .config import AppConfig
from .scanner import iter_project_files


LogFn = Callable[[str, str], None]
PipelineFn = Callable[[str], object]
ConfigFn = Callable[[], AppConfig]


@dataclass(frozen=True, slots=True)
class WatcherStatus:
    running: bool
    started_at: str | None
    last_run_at: str | None
    last_change_at: str | None


class PollingWatcher:
    def __init__(self, get_config: ConfigFn, run_pipeline: PipelineFn, log: LogFn) -> None:
        self._get_config = get_config
        self._run_pipeline = run_pipeline
        self._log = log
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._started_at: str | None = None
        self._last_run_at: str | None = None
        self._last_change_at: str | None = None

    def start(self) -> bool:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False

            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop, name="project-watcher", daemon=True)
            self._started_at = timestamp()
            self._thread.start()
            return True

    def stop(self) -> bool:
        with self._lock:
            if not self._thread or not self._thread.is_alive():
                return False
            self._stop_event.set()
            thread = self._thread

        thread.join(timeout=5)
        return True

    def status(self) -> WatcherStatus:
        with self._lock:
            running = bool(self._thread and self._thread.is_alive())
            return WatcherStatus(
                running=running,
                started_at=self._started_at,
                last_run_at=self._last_run_at,
                last_change_at=self._last_change_at,
            )

    def _set_last_run(self) -> None:
        with self._lock:
            self._last_run_at = timestamp()

    def _set_last_change(self) -> None:
        with self._lock:
            self._last_change_at = timestamp()

    def _loop(self) -> None:
        self._log("info", "Watcher started.")
        last_snapshot = self._snapshot()
        self._set_last_run()
        self._run_pipeline("watcher initial run")

        while not self._stop_event.is_set():
            config = self._get_config()
            interval = max(0.5, float(config.poll_interval_seconds))
            if self._stop_event.wait(interval):
                break

            current_snapshot = self._snapshot()
            changes = compare_snapshots(last_snapshot, current_snapshot)
            if not changes:
                continue

            self._set_last_change()
            preview = ", ".join(changes[:5])
            suffix = "" if len(changes) <= 5 else f" (+{len(changes) - 5} more)"
            self._log("info", f"Change detected: {preview}{suffix}")

            debounce = max(0.1, float(config.debounce_seconds))
            if self._stop_event.wait(debounce):
                break

            current_snapshot = self._snapshot()
            self._set_last_run()
            self._run_pipeline("watcher change")
            last_snapshot = current_snapshot

        self._log("info", "Watcher stopped.")

    def _snapshot(self) -> dict[str, tuple[int, int]]:
        config = self._get_config()
        if not config.project_root.strip():
            return {}

        root = config.project_path
        if not root.exists() or not root.is_dir():
            return {}

        snapshot: dict[str, tuple[int, int]] = {}
        try:
            records = list(iter_project_files(config))
        except OSError:
            return {}

        for record in records:
            try:
                stat = Path(record.absolute_path).stat()
            except OSError:
                continue
            snapshot[record.relative_path] = (stat.st_mtime_ns, stat.st_size)
        return snapshot


def compare_snapshots(
    before: dict[str, tuple[int, int]],
    after: dict[str, tuple[int, int]],
) -> list[str]:
    changes: list[str] = []
    before_keys = set(before)
    after_keys = set(after)

    for path in sorted(after_keys - before_keys):
        changes.append(f"created {path}")
    for path in sorted(before_keys - after_keys):
        changes.append(f"deleted {path}")
    for path in sorted(before_keys & after_keys):
        if before[path] != after[path]:
            changes.append(f"modified {path}")

    return changes


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
