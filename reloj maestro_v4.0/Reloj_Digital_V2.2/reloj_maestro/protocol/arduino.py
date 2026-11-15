"""Protocolo de comunicación con el Arduino.

Soporta dos modos:

* ``legacy``: solo los comandos de la versión 2.2 (``S:`` y ``A:``).
* ``v2``: protocolo extendido con borrado, habilitación, prueba y parada.

El modo se detecta al conectar: se envía ``PING`` y el firmware v2 responde
``READY:...``. Si no hay respuesta se asume firmware legacy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..domain.models import Alarm, day_index


class FirmwareMode(str, Enum):
    UNKNOWN = "unknown"
    LEGACY = "legacy"
    V2 = "v2"


class EventType(str, Enum):
    INFO = "info"
    ALERT = "alert"
    READY = "ready"
    ACK = "ack"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ClockInfo:
    """Hora reportada por el Arduino (formato 12 h, domingo = 0)."""

    hour: int
    minute: int
    second: int
    period: str
    day_index: int

    @property
    def hour24(self) -> int:
        value = self.hour % 12
        return value + 12 if self.period.upper() == "PM" else value


@dataclass(frozen=True)
class ArduinoEvent:
    type: EventType
    raw: str
    info: ClockInfo | None = None
    alarm_id: int | None = None
    message: str = ""


# ---------------------------------------------------------------------------
# Comandos de salida
# ---------------------------------------------------------------------------
def _hour12_and_period(hour24: int) -> tuple[int, str]:
    period = "P" if hour24 >= 12 else "A"
    hour12 = hour24 % 12
    if hour12 == 0:
        hour12 = 12
    return hour12, period


def _arduino_day(value: datetime) -> int:
    """Día del protocolo: domingo = 1 ... sábado = 7."""
    return day_index(value) + 1


def build_time_sync(value: datetime) -> str:
    hour12, period = _hour12_and_period(value.hour)
    return f"S:{hour12:02d}:{value.minute:02d}:{value.second:02d}:{period}:{_arduino_day(value)}"


def build_date_sync(value: datetime) -> str:
    """Comando v2 para fijar la fecha del RTC (el legacy no lo entiende)."""
    return f"F:{value.year:04d}:{value.month:02d}:{value.day:02d}"


def build_alarm_legacy(alarm: Alarm) -> str:
    hour12, period = _hour12_and_period(alarm.hour)
    return f"A:{hour12}:{alarm.minute:02d}:{period}:{alarm.duration}:{alarm.days}"


def build_alarm_v2(alarm: Alarm) -> str:
    hour12, period = _hour12_and_period(alarm.hour)
    return f"A:{alarm.id}:{hour12}:{alarm.minute:02d}:{period}:{alarm.duration}:{alarm.days}"


def build_delete(alarm_id: int) -> str:
    return f"D:{int(alarm_id)}"


def build_enable(alarm_id: int, enabled: bool) -> str:
    return f"E:{int(alarm_id)}:{1 if enabled else 0}"


def build_clear() -> str:
    return "C"


def build_test_siren(seconds: int) -> str:
    return f"T:{int(seconds)}"


def build_stop_siren() -> str:
    return "X"


def build_ping() -> str:
    return "PING"


# ---------------------------------------------------------------------------
# Parseo de entrada
# ---------------------------------------------------------------------------
def _normalize_period(value: str) -> str | None:
    value = value.strip().upper()
    if value in ("A", "AM"):
        return "AM"
    if value in ("P", "PM"):
        return "PM"
    return None


def _normalize_day(value: int) -> int | None:
    # Firmware legacy: 1 = domingo ... 7 = sábado.
    if 1 <= value <= 7:
        return value - 1
    # Algunos firmwares envían 0 = domingo ... 6 = sábado.
    if value == 0:
        return 0
    return None


def parse_line(raw: str) -> ArduinoEvent:
    line = (raw or "").strip()
    if not line:
        return ArduinoEvent(EventType.UNKNOWN, raw)

    if line == "PONG" or line.startswith("READY"):
        return ArduinoEvent(EventType.READY, line, message=line)

    if line.startswith("INFO:"):
        parts = line.split(":")
        if len(parts) < 6:
            return ArduinoEvent(EventType.UNKNOWN, line)
        try:
            hour = int(parts[1])
            minute = int(parts[2])
            second = int(parts[3])
            period = _normalize_period(parts[4])
            day = _normalize_day(int(parts[5]))
        except (TypeError, ValueError):
            return ArduinoEvent(EventType.UNKNOWN, line)
        if period is None or day is None:
            return ArduinoEvent(EventType.UNKNOWN, line)
        if not (1 <= hour <= 12 and 0 <= minute <= 59 and 0 <= second <= 59):
            return ArduinoEvent(EventType.UNKNOWN, line)
        info = ClockInfo(hour=hour, minute=minute, second=second, period=period, day_index=day)
        return ArduinoEvent(EventType.INFO, line, info=info)

    if line.startswith("ALERTA"):
        alarm_id: int | None = None
        parts = line.split(":")
        # ALERTA:ID:3 / ALERTA:3 / ALERTA:ALARMA_ACTIVA
        if len(parts) >= 3 and parts[1].upper() == "ID":
            try:
                alarm_id = int(parts[2])
            except ValueError:
                alarm_id = None
        elif len(parts) == 2 and parts[1].isdigit():
            alarm_id = int(parts[1])
        return ArduinoEvent(EventType.ALERT, line, alarm_id=alarm_id, message=line)

    if line.startswith("ACK"):
        return ArduinoEvent(EventType.ACK, line, message=line)

    if line.startswith("ERR") or line.startswith("ERROR"):
        return ArduinoEvent(EventType.ERROR, line, message=line)

    return ArduinoEvent(EventType.UNKNOWN, line)


def mode_label(mode: FirmwareMode) -> str:
    return {
        FirmwareMode.V2: "Firmware v2",
        FirmwareMode.LEGACY: "Firmware legacy",
        FirmwareMode.UNKNOWN: "Sin firmware",
    }[mode]
