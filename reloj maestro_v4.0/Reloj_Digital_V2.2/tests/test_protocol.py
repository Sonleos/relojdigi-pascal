from __future__ import annotations

import unittest
from datetime import datetime

from reloj_maestro.domain.models import Alarm
from reloj_maestro.protocol.arduino import (
    EventType,
    build_alarm_legacy,
    build_alarm_v2,
    build_clear,
    build_date_sync,
    build_delete,
    build_enable,
    build_ping,
    build_stop_siren,
    build_test_siren,
    build_time_sync,
    parse_line,
)


class CommandTests(unittest.TestCase):
    def test_time_sync_sunday_and_monday(self) -> None:
        self.assertEqual(build_time_sync(datetime(2026, 11, 8, 7, 5, 9)), "S:07:05:09:A:1")
        self.assertEqual(build_time_sync(datetime(2026, 11, 9, 19, 5, 9)), "S:07:05:09:P:2")

    def test_alarm_commands(self) -> None:
        alarm = Alarm(id=3, hour=19, minute=5, duration=10, days=0b101)
        self.assertEqual(build_alarm_legacy(alarm), "A:7:05:P:10:5")
        self.assertEqual(build_alarm_v2(alarm), "A:3:7:05:P:10:5")

    def test_date_sync(self) -> None:
        self.assertEqual(build_date_sync(datetime(2026, 11, 7)), "F:2026:11:07")

    def test_control_commands(self) -> None:
        self.assertEqual(build_delete(4), "D:4")
        self.assertEqual(build_enable(4, True), "E:4:1")
        self.assertEqual(build_enable(4, False), "E:4:0")
        self.assertEqual(build_clear(), "C")
        self.assertEqual(build_test_siren(5), "T:5")
        self.assertEqual(build_stop_siren(), "X")
        self.assertEqual(build_ping(), "PING")


class ParserTests(unittest.TestCase):
    def test_info_pm(self) -> None:
        event = parse_line("INFO:07:05:09:P:2")
        self.assertEqual(event.type, EventType.INFO)
        assert event.info is not None
        self.assertEqual(event.info.hour24, 19)
        self.assertEqual(event.info.minute, 5)
        self.assertEqual(event.info.second, 9)
        self.assertEqual(event.info.day_index, 1)

    def test_info_am_sunday(self) -> None:
        event = parse_line("INFO:07:05:09:A:1")
        assert event.info is not None
        self.assertEqual(event.info.hour24, 7)
        self.assertEqual(event.info.day_index, 0)

    def test_info_zero_based_day(self) -> None:
        event = parse_line("INFO:12:00:00:P:0")
        assert event.info is not None
        self.assertEqual(event.info.hour24, 12)
        self.assertEqual(event.info.day_index, 0)

    def test_alerts(self) -> None:
        legacy = parse_line("ALERTA:ALARMA_ACTIVA")
        self.assertEqual(legacy.type, EventType.ALERT)
        self.assertIsNone(legacy.alarm_id)

        with_id = parse_line("ALERTA:ID:4")
        self.assertEqual(with_id.type, EventType.ALERT)
        self.assertEqual(with_id.alarm_id, 4)

        numeric = parse_line("ALERTA:4")
        self.assertEqual(numeric.alarm_id, 4)

    def test_ready_and_acks(self) -> None:
        self.assertEqual(parse_line("READY:2.0").type, EventType.READY)
        self.assertEqual(parse_line("PONG").type, EventType.READY)
        self.assertEqual(parse_line("ACK:A:3").type, EventType.ACK)
        self.assertEqual(parse_line("ERR:RANGE").type, EventType.ERROR)

    def test_malformed(self) -> None:
        self.assertEqual(parse_line("INFO:99:99:99:X:9").type, EventType.UNKNOWN)
        self.assertEqual(parse_line("").type, EventType.UNKNOWN)
        self.assertEqual(parse_line("cualquier cosa").type, EventType.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
