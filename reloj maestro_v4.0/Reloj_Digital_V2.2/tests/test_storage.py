from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reloj_maestro.domain.models import Alarm, Settings
from reloj_maestro.services.storage import ConfigStore


class StorageTests(unittest.TestCase):
    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            store = ConfigStore(path)
            alarms = [
                Alarm(id=1, hour=7, minute=30, duration=10, days=0b1),
                Alarm(id=2, hour=19, minute=0, duration=30, days=0b1111110, enabled=False),
            ]
            settings = Settings(time_format="24h", sound_enabled=False, last_port="COM3")
            store.save(alarms, settings)

            loaded_alarms, loaded_settings = store.load()
            self.assertEqual(loaded_alarms, alarms)
            self.assertEqual(loaded_settings, settings)

    def test_corrupt_file_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            path.write_text("{esto no es json", encoding="utf-8")
            store = ConfigStore(path)

            alarms, settings = store.load()
            self.assertEqual(alarms, [])
            self.assertEqual(settings, Settings())
            self.assertTrue(list(Path(folder).glob("config.bad_*.json")))

    def test_duplicate_ids_are_repaired(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            payload = {
                "version": 1,
                "settings": {},
                "alarms": [
                    {"id": 1, "hour": 7, "minute": 0, "duration": 10, "days": 1, "enabled": True},
                    {"id": 1, "hour": 8, "minute": 0, "duration": 10, "days": 1, "enabled": True},
                ],
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            alarms, _ = ConfigStore(path).load()
            self.assertEqual(len(alarms), 2)
            self.assertEqual(len({alarm.id for alarm in alarms}), 2)

    def test_invalid_alarm_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            payload = {
                "version": 1,
                "settings": {},
                "alarms": [
                    {"id": 1, "hour": 99, "minute": 0, "duration": 10, "days": 1, "enabled": True},
                    {"id": 2, "hour": 7, "minute": 0, "duration": 10, "days": 1, "enabled": True},
                ],
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            alarms, _ = ConfigStore(path).load()
            self.assertEqual([alarm.id for alarm in alarms], [2])


if __name__ == "__main__":
    unittest.main()
