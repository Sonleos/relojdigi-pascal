"""Persistencia de alarmas y ajustes en un archivo JSON."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import config_path
from ..domain.models import Alarm, AlarmValidationError, Settings


class ConfigStore:
    """Guarda la configuración de forma atómica y tolerante a archivos corruptos."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else config_path()

    # -- Lectura ------------------------------------------------------------
    def load(self) -> tuple[list[Alarm], Settings]:
        if not self.path.exists():
            return [], Settings()

        try:
            raw: Any = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            self._quarantine()
            return [], Settings()

        if not isinstance(raw, dict):
            self._quarantine()
            return [], Settings()

        settings = Settings.from_dict(raw.get("settings"))
        alarms: list[Alarm] = []
        used_ids: set[int] = set()
        next_id = 1

        for item in raw.get("alarms", []):
            if not isinstance(item, dict):
                continue
            try:
                alarm = Alarm.from_dict(item)
            except (KeyError, TypeError, ValueError, AlarmValidationError):
                continue

            # Reparar identificadores duplicados o inválidos.
            if alarm.id in used_ids:
                while next_id in used_ids:
                    next_id += 1
                alarm.id = next_id
            used_ids.add(alarm.id)
            alarms.append(alarm)

        alarms.sort(key=lambda alarm: (alarm.hour, alarm.minute, alarm.id))
        return alarms, settings

    # -- Escritura ----------------------------------------------------------
    def save(self, alarms: list[Alarm], settings: Settings) -> None:
        payload = {
            "version": 1,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "settings": settings.to_dict(),
            "alarms": [alarm.to_dict() for alarm in alarms],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(self.path.name + ".tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp_path, self.path)

    # -- Utilidades ---------------------------------------------------------
    def _quarantine(self) -> None:
        """Renombra un archivo inválido para no perderlo ni bloquear el arranque."""
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            bad_path = self.path.with_name(f"{self.path.stem}.bad_{stamp}.json")
            self.path.replace(bad_path)
        except OSError:
            pass
