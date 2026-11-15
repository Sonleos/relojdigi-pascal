"""Constantes, rutas y paleta visual de la aplicación."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Identidad de la aplicación
# ---------------------------------------------------------------------------
APP_NAME = "Reloj Maestro"
APP_TITLE = "Terminal de Control - Reloj Maestro"
APP_VERSION = "2.2"

ICON_FILENAME = "Reloj_Maestro.ico"
CONFIG_FILENAME = "reloj_maestro_config.json"
LOG_FILENAME = "reloj_maestro.log"

# ---------------------------------------------------------------------------
# Comunicación serial
# ---------------------------------------------------------------------------
SERIAL_BAUDRATE = 9600
SERIAL_READ_TIMEOUT = 0.2
SERIAL_BOOT_DELAY = 1.8       # tiempo de arranque del Arduino tras abrir el puerto
SERIAL_HANDSHAKE_TIMEOUT = 2.0
SERIAL_WRITE_TIMEOUT = 1.0
PORT_SCAN_INTERVAL_MS = 5000  # reescaneo de puertos mientras no hay conexión

# ---------------------------------------------------------------------------
# Reloj, alarmas y alertas
# ---------------------------------------------------------------------------
CLOCK_TICK_MS = 500
SCHEDULER_TICK_MS = 250
SERIAL_POLL_MS = 50
ALARM_GRACE_SECONDS = 10      # margen para disparar si el PC estuvo ocupado/suspendido
ALERT_DEDUPE_SECONDS = 90     # evita alerta doble (PC + Arduino)
HARDWARE_INFO_STALE_SECONDS = 3.0
TIME_SYNC_INTERVAL_SECONDS = 30 * 60
MAX_HARDWARE_ALARMS = 12      # límite del firmware de referencia v2

DURATION_OPTIONS = ("5", "10", "15", "30", "60", "120")
DEFAULT_DURATION = "10"

TIME_FORMAT_12 = "12h"
TIME_FORMAT_24 = "24h"
TIME_FORMATS = (TIME_FORMAT_12, TIME_FORMAT_24)

APPEARANCE_LIGHT = "light"
APPEARANCE_DARK = "dark"
APPEARANCES = (APPEARANCE_LIGHT, APPEARANCE_DARK)

# ---------------------------------------------------------------------------
# Bitácora
# ---------------------------------------------------------------------------
MAX_LOG_LINES = 500
LOG_MAX_BYTES = 1_000_000
LOG_BACKUPS = 2

# ---------------------------------------------------------------------------
# Rutas (compatibles con PyInstaller)
# ---------------------------------------------------------------------------
def resource_path(relative: str) -> Path:
    """Ruta absoluta de un recurso empaquetado con PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / relative
    return Path(__file__).resolve().parent.parent / relative


def app_dir() -> Path:
    """Carpeta donde vive el ejecutable (o el proyecto en modo fuente)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _is_writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".reloj_maestro_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


_data_dir_cache: Path | None = None


def data_dir() -> Path:
    """Carpeta de datos: junto al .exe y, si no se puede escribir, en %APPDATA%."""
    global _data_dir_cache
    if _data_dir_cache is not None:
        return _data_dir_cache

    preferred = app_dir()
    if _is_writable(preferred):
        _data_dir_cache = preferred
        return preferred

    fallback = Path(os.environ.get("APPDATA", Path.home())) / "RelojMaestro"
    if _is_writable(fallback):
        _data_dir_cache = fallback
        return fallback

    temp = Path(tempfile.gettempdir()) / "RelojMaestro"
    try:
        temp.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    _data_dir_cache = temp
    return temp


def config_path() -> Path:
    return data_dir() / CONFIG_FILENAME


def log_path() -> Path:
    return data_dir() / LOG_FILENAME
