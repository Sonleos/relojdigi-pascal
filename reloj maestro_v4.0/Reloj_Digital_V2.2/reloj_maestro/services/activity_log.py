"""Bitácora en archivo con rotación sencilla."""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

from ..config import LOG_BACKUPS, LOG_MAX_BYTES


class ActivityLog:
    """Escribe la bitácora en disco sin bloquear ni romper la interfaz."""

    def __init__(self, path: Path, max_bytes: int = LOG_MAX_BYTES, backups: int = LOG_BACKUPS) -> None:
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.backups = max(1, int(backups))
        self._lock = threading.Lock()

    def write(self, message: str, level: str = "INFO") -> None:
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S} [{level}] {message}\n"
        with self._lock:
            try:
                self._rotate_if_needed()
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
            except OSError:
                pass

    def _rotate_if_needed(self) -> None:
        try:
            if not self.path.exists() or self.path.stat().st_size < self.max_bytes:
                return
        except OSError:
            return

        # reloj_maestro.log.2 -> reloj_maestro.log.3, etc.
        for index in range(self.backups - 1, 0, -1):
            source = self.path.with_name(f"{self.path.name}.{index}")
            target = self.path.with_name(f"{self.path.name}.{index + 1}")
            if source.exists():
                try:
                    if target.exists():
                        target.unlink()
                    source.replace(target)
                except OSError:
                    pass

        first = self.path.with_name(f"{self.path.name}.1")
        try:
            if first.exists():
                first.unlink()
            self.path.replace(first)
        except OSError:
            pass
