from __future__ import annotations

import unittest
from datetime import datetime

from reloj_maestro.domain.models import (
    ALL_DAYS_MASK,
    WEEKDAY_MASK,
    Alarm,
    AlarmValidationError,
    bit_read,
    day_index,
    describe_days,
    format_time,
    format_timedelta,
    from_hour24,
    mask_from_bools,
    mask_to_bools,
    to_hour24,
)


class DayMaskTests(unittest.TestCase):
    def test_day_index_sunday_is_zero(self) -> None:
        self.assertEqual(day_index(datetime(2026, 11, 8)), 0)  # domingo
        self.assertEqual(day_index(datetime(2026, 11, 9)), 1)  # lunes

    def test_mask_roundtrip(self) -> None:
        values = [True, False, True, False, True, False, True]
        mask = mask_from_bools(values)
        self.assertEqual(mask_to_bools(mask), values)
        self.assertTrue(bit_read(mask, 0))
        self.assertFalse(bit_read(mask, 1))

    def test_describe_days(self) -> None:
        self.assertEqual(describe_days(ALL_DAYS_MASK), "Todos los días")
        self.assertEqual(describe_days(WEEKDAY_MASK), "Lunes a viernes")
        self.assertEqual(describe_days(0b1000001), "Fin de semana")


class TimeFormatTests(unittest.TestCase):
    def test_12h_conversion(self) -> None:
        self.assertEqual(format_time(0, 5, "12h"), "12:05 AM")
        self.assertEqual(format_time(12, 0, "12h"), "12:00 PM")
        self.assertEqual(format_time(13, 30, "12h"), "01:30 PM")
        self.assertEqual(from_hour24(19), (7, "PM"))
        self.assertEqual(to_hour24(12, "AM"), 0)
        self.assertEqual(to_hour24(12, "PM"), 12)

    def test_24h_format(self) -> None:
        self.assertEqual(format_time(0, 5, "24h"), "00:05")
        self.assertEqual(format_time(19, 30, "24h"), "19:30")

    def test_timedelta(self) -> None:
        self.assertEqual(format_timedelta(__import__("datetime").timedelta(seconds=3661)), "01:01:01")
        self.assertEqual(
            format_timedelta(__import__("datetime").timedelta(days=1, seconds=61)),
            "1d 00:01:01",
        )


class AlarmTests(unittest.TestCase):
    def test_due_with_grace(self) -> None:
        alarm = Alarm(id=1, hour=7, minute=30, duration=10, days=0b1)  # domingo
        self.assertTrue(alarm.is_due(datetime(2026, 11, 8, 7, 30, 0), grace_seconds=10))
        self.assertTrue(alarm.is_due(datetime(2026, 11, 8, 7, 30, 9), grace_seconds=10))
        self.assertFalse(alarm.is_due(datetime(2026, 11, 8, 7, 30, 11), grace_seconds=10))
        self.assertFalse(alarm.is_due(datetime(2026, 11, 9, 7, 30, 0), grace_seconds=10))

    def test_disabled_never_due(self) -> None:
        alarm = Alarm(id=1, hour=7, minute=30, days=ALL_DAYS_MASK, enabled=False)
        self.assertFalse(alarm.is_due(datetime(2026, 11, 8, 7, 30, 0)))

    def test_fire_key_prevents_duplicate(self) -> None:
        alarm = Alarm(id=1, hour=7, minute=30, days=ALL_DAYS_MASK)
        now = datetime(2026, 11, 8, 7, 30, 2)
        self.assertFalse(alarm.was_fired(now))
        alarm.mark_fired(now)
        self.assertTrue(alarm.was_fired(now))
        self.assertFalse(alarm.was_fired(datetime(2026, 11, 9, 7, 30, 2)))

    def test_next_occurrence(self) -> None:
        monday = 1 << 1
        alarm = Alarm(id=1, hour=7, minute=30, days=monday)
        self.assertEqual(
            alarm.next_occurrence(datetime(2026, 11, 8, 8, 0)),  # domingo
            datetime(2026, 11, 9, 7, 30),
        )
        self.assertEqual(
            alarm.next_occurrence(datetime(2026, 11, 9, 7, 29)),
            datetime(2026, 11, 9, 7, 30),
        )
        self.assertEqual(
            alarm.next_occurrence(datetime(2026, 11, 9, 7, 31)),
            datetime(2026, 11, 16, 7, 30),
        )

    def test_invalid_fields(self) -> None:
        with self.assertRaises(AlarmValidationError):
            Alarm(id=1, hour=24, minute=0)
        with self.assertRaises(AlarmValidationError):
            Alarm(id=1, hour=7, minute=60)
        with self.assertRaises(AlarmValidationError):
            Alarm(id=1, hour=7, minute=0, days=0)
        with self.assertRaises(AlarmValidationError):
            Alarm(id=1, hour=7, minute=0, duration=0)

    def test_serialization_roundtrip(self) -> None:
        alarm = Alarm(id=3, hour=19, minute=5, duration=30, days=0b101, enabled=False)
        restored = Alarm.from_dict(alarm.to_dict())
        self.assertEqual(restored, alarm)

    def test_legacy_dict(self) -> None:
        alarm = Alarm.from_dict(
            {
                "id": 1,
                "hora": "12",
                "min": "05",
                "periodo": "AM",
                "duracion": "10",
                "dias": 127,
                "activa": True,
            }
        )
        self.assertEqual(alarm.hour, 0)
        self.assertEqual(alarm.minute, 5)


if __name__ == "__main__":
    unittest.main()
