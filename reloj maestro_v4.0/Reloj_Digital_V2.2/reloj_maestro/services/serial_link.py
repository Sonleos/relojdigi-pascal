"""Enlace serial con el Arduino.

El hilo lector nunca toca Tkinter: publica eventos en una ``queue.Queue`` que
el controlador consume desde el hilo principal.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass

import serial
from serial.tools import list_ports

from ..config import (
    SERIAL_BAUDRATE,
    SERIAL_BOOT_DELAY,
    SERIAL_HANDSHAKE_TIMEOUT,
    SERIAL_READ_TIMEOUT,
    SERIAL_WRITE_TIMEOUT,
)
from ..protocol.arduino import EventType, FirmwareMode, build_ping, parse_line

_ARDUINO_HINTS = (
    "arduino",
    "ch340",
    "ch341",
    "cp210",
    "ftdi",
    "usb serial",
    "usb-serial",
    "silicon labs",
    "wch",
    "atmega",
    "elegoo",
)


@dataclass(frozen=True)
class PortInfo:
    device: str
    description: str = ""
    hwid: str = ""

    @property
    def display(self) -> str:
        return self.device

    @property
    def is_likely_arduino(self) -> bool:
        text = f"{self.description} {self.hwid}".lower()
        return any(hint in text for hint in _ARDUINO_HINTS)


class SerialLink:
    """Conexión serial con lectura en segundo plano y cola de eventos."""

    def __init__(self) -> None:
        self.events: queue.Queue[tuple] = queue.Queue()
        self._serial: serial.Serial | None = None
        self._lock = threading.RLock()
        self._open_lock = threading.Lock()
        self._reader: threading.Thread | None = None
        self._stop = threading.Event()
        self._handshake = threading.Event()
        self._opening = False
        self._mode = FirmwareMode.UNKNOWN

    # -- Estado -------------------------------------------------------------
    @property
    def connected(self) -> bool:
        with self._lock:
            return bool(self._serial and self._serial.is_open)

    @property
    def opening(self) -> bool:
        return self._opening

    @property
    def mode(self) -> FirmwareMode:
        return self._mode

    # -- Puertos ------------------------------------------------------------
    @staticmethod
    def list_ports() -> list[PortInfo]:
        try:
            found = [
                PortInfo(
                    device=port.device,
                    description=port.description or "",
                    hwid=port.hwid or "",
                )
                for port in list_ports.comports()
            ]
        except Exception:
            return []
        # Los puertos con pinta de Arduino primero, luego por nombre.
        found.sort(key=lambda item: (not item.is_likely_arduino, item.device))
        return found

    # -- Conexión -----------------------------------------------------------
    def open(self, port: str) -> bool:
        """Abre el puerto, saluda al firmware y determina el modo.

        Es bloqueante (espera el reinicio del Arduino). Debe llamarse desde un
        hilo de trabajo, nunca desde el hilo de Tkinter.
        """
        if not self._open_lock.acquire(blocking=False):
            return False

        try:
            if self.connected:
                return False

            self.close(emit=False)
            self._opening = True
            self._emit_status("connecting", port)

            try:
                device = serial.Serial(
                    port=port,
                    baudrate=SERIAL_BAUDRATE,
                    timeout=SERIAL_READ_TIMEOUT,
                    write_timeout=SERIAL_WRITE_TIMEOUT,
                )
            except Exception as exc:
                self._emit_status("error", str(exc))
                return False

            with self._lock:
                self._serial = device

            self._stop.clear()
            self._handshake.clear()
            self._mode = FirmwareMode.UNKNOWN

            self._reader = threading.Thread(
                target=self._read_loop,
                name="reloj-serial-reader",
                daemon=True,
            )
            self._reader.start()

            # El Arduino se reinicia al abrir el puerto (DTR). Damos tiempo a
            # que arranque y luego intentamos el saludo del protocolo v2.
            if self._stop.wait(SERIAL_BOOT_DELAY):
                return False
            self.send(build_ping(), quiet=True)
            if self._handshake.wait(SERIAL_HANDSHAKE_TIMEOUT):
                self._mode = FirmwareMode.V2
            elif self._stop.is_set():
                return False
            else:
                self._mode = FirmwareMode.LEGACY

            self._emit_status("online", self._mode.value)
            return True
        finally:
            self._opening = False
            self._open_lock.release()

    def close(self, emit: bool = True) -> None:
        self._stop.set()

        with self._lock:
            device = self._serial
            self._serial = None

        if device is not None:
            try:
                device.close()
            except Exception:
                pass

        reader = self._reader
        if reader is not None and reader is not threading.current_thread():
            reader.join(timeout=1.0)
        self._reader = None
        self._mode = FirmwareMode.UNKNOWN
        self._opening = False

        if emit:
            self._emit_status("offline", "Desconectado")

    # -- Envío --------------------------------------------------------------
    def send(self, command: str, quiet: bool = False) -> bool:
        with self._lock:
            device = self._serial

        if device is None or not device.is_open:
            self.events.put(("tx_error", command, "Sin conexión serial"))
            return False

        try:
            device.write((command + "\n").encode("ascii", errors="ignore"))
            device.flush()
            if not quiet:
                self.events.put(("tx", command))
            return True
        except Exception as exc:
            self.events.put(("tx_error", command, str(exc)))
            return False

    # -- Hilo lector --------------------------------------------------------
    def _read_loop(self) -> None:
        current = None
        failure: str | None = None

        with self._lock:
            current = self._serial

        try:
            while not self._stop.is_set() and current is not None:
                try:
                    raw = current.readline()
                except (serial.SerialException, OSError) as exc:
                    if not self._stop.is_set():
                        failure = str(exc)
                    break

                if not raw:
                    continue

                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                event = parse_line(line)
                if event.type == EventType.READY:
                    self._handshake.set()
                    self._mode = FirmwareMode.V2
                self.events.put(("line", line, event))
        finally:
            with self._lock:
                if self._serial is current:
                    self._serial = None
            if not self._stop.is_set():
                self._emit_status("disconnected", failure or "Conexión perdida")

    # -- Eventos ------------------------------------------------------------
    def _emit_status(self, state: str, detail: str) -> None:
        self.events.put(("status", state, detail, self._mode))


__all__ = ["SerialLink", "PortInfo"]
