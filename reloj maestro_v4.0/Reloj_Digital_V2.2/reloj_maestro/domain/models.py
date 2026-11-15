"""Modelos de alarmas, días de la semana y ajustes de la aplicación."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from ..config import APPEARANCE_LIGHT, APPEARANCES, TIME_FORMAT_12, TIME_FORMAT_24

# Los nombres están ordenados de domingo a sábado para que el índice coincida
# con la máscara de bits que entiende el Arduino (bit 0 = domingo).
DAY_NAMES = ("Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb")
DAY_NAMES_LONG = (
    "Domingo",
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
)
MONTH_NAMES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

ALL_DAYS_MASK = 0b1111111
WEEKDAY_MASK = 0b0111110  # lunes a viernes
WEEKEND_MASK = 0b1000001  # domingo y sábado

MIN_DURATION = 1
MAX_DURATION = 3600


class AlarmValidationError(ValueError):
    """Datos de alarma inválidos."""


# ---------------------------------------------------------------------------
# Utilidades de días
# ---------------------------------------------------------------------------
def day_index(value: datetime | date) -> int:
    """Índice de día con domingo = 0 ... sábado = 6."""
    return (value.weekday() + 1) % 7


def bit_read(value: int, bit: int) -> bool:
    return bool((int(value) >> int(bit)) & 0x01)


def mask_from_bools(values: Iterable[bool]) -> int:
    mask = 0
    for index, enabled in enumerate(values):
        if enabled:
            mask |= 1 << index
    return mask


def mask_to_bools(mask: int) -> list[bool]:
    return [bit_read(mask, index) for index in range(7)]


def describe_days(mask: int) -> str:
    mask = int(mask) & ALL_DAYS_MASK
    if mask == ALL_DAYS_MASK:
        return "Todos los días"
    if mask == WEEKDAY_MASK:
        return "Lunes a viernes"
    if mask == WEEKEND_MASK:
        return "Fin de semana"
    return ", ".join(DAY_NAMES[index] for index in range(7) if bit_read(mask, index))


def format_date_es(value: datetime | date) -> str:
    return f"{DAY_NAMES_LONG[day_index(value)]}, {value.day:02d} de {MONTH_NAMES[value.month - 1]} de {value.year}"


# ---------------------------------------------------------------------------
# Conversión horaria
# ---------------------------------------------------------------------------
def to_hour24(hour12: int, period: str) -> int:
    if not 1 <= int(hour12) <= 12:
        raise AlarmValidationError("La hora debe estar entre 1 y 12.")
    period = str(period).upper()
    if period not in ("AM", "PM"):
        raise AlarmValidationError("El período debe ser AM o PM.")
    hour24 = int(hour12) % 12
    return hour24 + 12 if period == "PM" else hour24


def from_hour24(hour24: int) -> tuple[int, str]:
    if not 0 <= int(hour24) <= 23:
        raise AlarmValidationError("La hora debe estar entre 0 y 23.")
    hour24 = int(hour24)
    period = "PM" if hour24 >= 12 else "AM"
    hour12 = hour24 % 12
    if hour12 == 0:
        hour12 = 12
    return hour12, period


def format_time(hour24: int, minute: int, time_format: str = TIME_FORMAT_12) -> str:
    validate_time(hour24, minute)
    if time_format == TIME_FORMAT_24:
        return f"{hour24:02d}:{minute:02d}"
    hour12, period = from_hour24(hour24)
    return f"{hour12:02d}:{minute:02d} {period}"


def validate_time(hour24: int, minute: int) -> None:
    if not isinstance(hour24, int) or not 0 <= hour24 <= 23:
        raise AlarmValidationError("La hora debe estar entre 0 y 23.")
    if not isinstance(minute, int) or not 0 <= minute <= 59:
        raise AlarmValidationError("El minuto debe estar entre 0 y 59.")


def validate_alarm_fields(hour: int, minute: int, duration: int, days: int) -> None:
    validate_time(hour, minute)
    if not isinstance(duration, int) or not MIN_DURATION <= duration <= MAX_DURATION:
        raise AlarmValidationError(f"La duración debe estar entre {MIN_DURATION} y {MAX_DURATION} segundos.")
    if not isinstance(days, int) or not 0 < days < 128:
        raise AlarmValidationError("Selecciona al menos un día de la semana.")


def format_timedelta(delta: timedelta) -> str:
    total = max(0, int(delta.total_seconds()))
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days:
        return f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# ---------------------------------------------------------------------------
# Alarma
# ---------------------------------------------------------------------------
@dataclass
class Alarm:
    """Alarma semanal recurrente.

    ``hour`` se guarda en formato 24 h (0-23) para simplificar comparaciones;
    la interfaz y el protocolo convierten a 12 h cuando es necesario.
    """

    id: int
    hour: int
    minute: int
    duration: int = 10
    days: int = ALL_DAYS_MASK
    enabled: bool = True
    last_fired: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, int) or self.id < 1:
            raise AlarmValidationError("El identificador de la alarma debe ser positivo.")
        validate_alarm_fields(self.hour, self.minute, self.duration, self.days)
        if not isinstance(self.enabled, bool):
            raise AlarmValidationError("El estado de la alarma debe ser booleano.")

    # -- Presentación -------------------------------------------------------
    @property
    def hour12(self) -> int:
        return from_hour24(self.hour)[0]

    @property
    def period(self) -> str:
        return from_hour24(self.hour)[1]

    def time_label(self, time_format: str = TIME_FORMAT_12) -> str:
        return format_time(self.hour, self.minute, time_format)

    @property
    def days_label(self) -> str:
        return describe_days(self.days)

    # -- Lógica -------------------------------------------------------------
    def matches_day(self, value: datetime) -> bool:
        return bit_read(self.days, day_index(value))

    def is_due(self, value: datetime, grace_seconds: int = 10) -> bool:
        """True si la alarma debe dispararse en ``value``.

        Se acepta un margen de ``grace_seconds`` para no perder la alarma si
        el bucle de la interfaz llegó unos segundos tarde.
        """
        return bool(
            self.enabled
            and self.matches_day(value)
            and self.hour == value.hour
            and self.minute == value.minute
            and 0 <= value.second < grace_seconds
        )

    def fire_key(self, value: datetime) -> str:
        return f"{value:%Y-%m-%d} {self.hour:02d}:{self.minute:02d}"

    def was_fired(self, value: datetime) -> bool:
        return self.last_fired == self.fire_key(value)

    def mark_fired(self, value: datetime) -> None:
        self.last_fired = self.fire_key(value)

    def next_occurrence(self, after: datetime) -> datetime | None:
        """Próxima fecha/hora en que sonará la alarma, o ``None`` si está apagada."""
        if not self.enabled:
            return None
        # 8 días cubren cualquier combinación de días, incluso el mismo día.
        for offset in range(0, 8):
            current_date = (after + timedelta(days=offset)).date()
            if not bit_read(self.days, day_index(current_date)):
                continue
            candidate = datetime(
                current_date.year,
                current_date.month,
                current_date.day,
                self.hour,
                self.minute,
            )
            if candidate >= after:
                return candidate
        return None

    # -- Serialización ------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "hour": self.hour,
            "minute": self.minute,
            "duration": self.duration,
            "days": self.days,
            "enabled": self.enabled,
            "last_fired": self.last_fired,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Alarm":
        """Crea una alarma desde JSON.

        Acepta también el formato "legacy" de la versión monolítica
        (``hora``/``min``/``periodo``/``dias``/``activa``) para facilitar
        una posible migración manual.
        """
        if "hour" in data:
            return cls(
                id=int(data["id"]),
                hour=int(data["hour"]),
                minute=int(data["minute"]),
                duration=int(data.get("duration", 10)),
                days=int(data.get("days", ALL_DAYS_MASK)),
                enabled=bool(data.get("enabled", True)),
                last_fired=data.get("last_fired"),
            )

        hour24 = to_hour24(int(data["hora"]), str(data.get("periodo", "AM")))
        return cls(
            id=int(data["id"]),
            hour=hour24,
            minute=int(data.get("min", data.get("minuto", 0))),
            duration=int(data.get("duracion", 10)),
            days=int(data.get("dias", ALL_DAYS_MASK)),
            enabled=bool(data.get("activa", True)),
            last_fired=data.get("last_fired"),
        )


# ---------------------------------------------------------------------------
# Ajustes persistidos
# ---------------------------------------------------------------------------
@dataclass
class Settings:
    time_format: str = TIME_FORMAT_12
    sound_enabled: bool = True
    last_port: str = ""
    appearance: str = APPEARANCE_LIGHT

    def __post_init__(self) -> None:
        if self.time_format not in (TIME_FORMAT_12, TIME_FORMAT_24):
            self.time_format = TIME_FORMAT_12
        if self.appearance not in APPEARANCES:
            self.appearance = APPEARANCE_LIGHT

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_format": self.time_format,
            "sound_enabled": self.sound_enabled,
            "last_port": self.last_port,
            "appearance": self.appearance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Settings":
        if not isinstance(data, dict):
            return cls()
        return cls(
            time_format=str(data.get("time_format", TIME_FORMAT_12)),
            sound_enabled=bool(data.get("sound_enabled", True)),
            last_port=str(data.get("last_port", "")),
            appearance=str(data.get("appearance", APPEARANCE_LIGHT)),
        )
