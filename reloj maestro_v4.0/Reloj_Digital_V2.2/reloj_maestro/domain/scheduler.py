"""Planificador de alarmas independiente de la interfaz gráfica."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterable

from ..config import ALARM_GRACE_SECONDS
from .models import Alarm

AlarmProvider = Callable[[], Iterable[Alarm]]
AlarmCallback = Callable[[Alarm, datetime], None]
ClockProvider = Callable[[], datetime]


class AlarmScheduler:
    """Comprueba las alarmas y evita disparos duplicados.

    No usa ``after`` ni hilos: recibe un "tick" periódico desde el controlador.
    Así se puede probar con fechas simuladas y no acumula deriva.
    """

    def __init__(
        self,
        alarms: AlarmProvider,
        on_fired: AlarmCallback,
        grace_seconds: int = ALARM_GRACE_SECONDS,
        clock: ClockProvider = datetime.now,
    ) -> None:
        self._alarms = alarms
        self._on_fired = on_fired
        self._grace_seconds = grace_seconds
        self._clock = clock

    def tick(self, now: datetime | None = None) -> list[Alarm]:
        now = now or self._clock()
        fired: list[Alarm] = []
        for alarm in list(self._alarms()):
            if alarm.enabled and alarm.is_due(now, self._grace_seconds) and not alarm.was_fired(now):
                alarm.mark_fired(now)
                fired.append(alarm)
                self._on_fired(alarm, now)
        return fired

    def next_occurrence(self, now: datetime | None = None) -> tuple[Alarm, datetime] | None:
        now = now or self._clock()
        best: tuple[Alarm, datetime] | None = None
        for alarm in self._alarms():
            candidate = alarm.next_occurrence(now)
            if candidate is None:
                continue
            if best is None or candidate < best[1]:
                best = (alarm, candidate)
        return best
