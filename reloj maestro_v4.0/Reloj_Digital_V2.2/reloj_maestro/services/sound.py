"""Aviso sonoro local para cuando la alarma se dispara en la PC."""

from __future__ import annotations

import sys
import threading


class AlarmSound:
    """Reproduce un patrón de pitidos hasta que se detiene.

    Usa ``winsound`` (Windows). En otros sistemas no hace nada, pero la alerta
    visual sigue funcionando.
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = bool(enabled)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = bool(value)
        if not self._enabled:
            self.stop()

    @property
    def playing(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if not self._enabled:
            return
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop,
                name="reloj-alarma-sonido",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        if sys.platform != "win32":
            return
        try:
            import winsound
        except ImportError:
            return

        while not self._stop.is_set():
            try:
                winsound.Beep(1100, 300)
                if self._stop.wait(0.12):
                    break
                winsound.Beep(1500, 300)
                if self._stop.wait(0.22):
                    break
            except RuntimeError:
                # Sin altavoz/beep disponible: un aviso simple y espera.
                try:
                    winsound.MessageBeep()
                except RuntimeError:
                    pass
                self._stop.wait(1.0)
