from __future__ import annotations

import unittest
from datetime import datetime

from reloj_maestro.domain.models import Alarm
from reloj_maestro.domain.scheduler import AlarmScheduler


class SchedulerTests(unittest.TestCase):
    def test_fires_once_and_respects_grace(self) -> None:
        alarms = [Alarm(id=1, hour=7, minute=30, days=0b1)]
        fired: list[Alarm] = []
        scheduler = AlarmScheduler(lambda: alarms, lambda alarm, now: fired.append(alarm), grace_seconds=10)

        scheduler.tick(datetime(2026, 11, 8, 7, 29, 59))
        self.assertEqual(fired, [])

        scheduler.tick(datetime(2026, 11, 8, 7, 30, 5))
        self.assertEqual(len(fired), 1)

        scheduler.tick(datetime(2026, 11, 8, 7, 30, 6))
        self.assertEqual(len(fired), 1)

    def test_disabled_does_not_fire(self) -> None:
        alarms = [Alarm(id=1, hour=7, minute=30, days=0b1, enabled=False)]
        fired: list[Alarm] = []
        scheduler = AlarmScheduler(lambda: alarms, lambda alarm, now: fired.append(alarm))
        scheduler.tick(datetime(2026, 11, 8, 7, 30, 1))
        self.assertEqual(fired, [])

    def test_next_occurrence_earliest(self) -> None:
        alarms = [
            Alarm(id=1, hour=8, minute=0, days=0b1),  # domingo
            Alarm(id=2, hour=7, minute=0, days=0b10),  # lunes
        ]
        scheduler = AlarmScheduler(lambda: alarms, lambda alarm, now: None)
        result = scheduler.next_occurrence(datetime(2026, 11, 8, 6, 0))
        self.assertIsNotNone(result)
        alarm, when = result  # type: ignore[misc]
        self.assertEqual(alarm.id, 1)
        self.assertEqual(when, datetime(2026, 11, 8, 8, 0))

    def test_no_next_occurrence(self) -> None:
        scheduler = AlarmScheduler(lambda: [], lambda alarm, now: None)
        self.assertIsNone(scheduler.next_occurrence(datetime(2026, 11, 8, 6, 0)))


if __name__ == "__main__":
    unittest.main()
