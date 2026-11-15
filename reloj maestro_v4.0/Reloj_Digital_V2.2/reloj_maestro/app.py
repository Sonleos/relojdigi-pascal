"""Controlador principal y punto de entrada de Reloj Maestro."""

from __future__ import annotations

import os
import queue
import threading
import time
import traceback
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from .config import (
    APPEARANCE_LIGHT,
    APP_TITLE,
    APP_VERSION,
    CLOCK_TICK_MS,
    ICON_FILENAME,
    MAX_HARDWARE_ALARMS,
    PORT_SCAN_INTERVAL_MS,
    SCHEDULER_TICK_MS,
    SERIAL_POLL_MS,
    TIME_FORMAT_24,
    TIME_FORMAT_12,
    TIME_SYNC_INTERVAL_SECONDS,
    log_path,
    resource_path,
)
from .domain.models import (
    Alarm,
    AlarmValidationError,
    DAY_NAMES_LONG,
    bit_read,
    day_index,
    format_time,
    format_timedelta,
    validate_alarm_fields,
)
from .domain.scheduler import AlarmScheduler
from .protocol.arduino import (
    EventType,
    FirmwareMode,
    build_alarm_legacy,
    build_alarm_v2,
    build_clear,
    build_date_sync,
    build_stop_siren,
    build_test_siren,
    build_time_sync,
    mode_label,
)
from .services.activity_log import ActivityLog
from .services.serial_link import PortInfo, SerialLink
from .services.sound import AlarmSound
from .services.storage import ConfigStore
from .ui.alert_dialog import AlertManager
from .ui.main_window import MainWindow
from .ui.theme import BG, appearance_from_label, appearance_label, apply_appearance


class AppController:
    def __init__(self, root: ctk.CTk) -> None:
        self.root = root

        self.store = ConfigStore()
        self.activity = ActivityLog(log_path())
        self.alarms, self.settings = self.store.load()

        # Aplicar el tema antes de crear la primera tarjeta para evitar
        # parpadeos y que todos los colores se resuelvan con la paleta correcta.
        apply_appearance(self.settings.appearance)
        self.root.configure(fg_color=BG)

        self.sound = AlarmSound(self.settings.sound_enabled)
        self.link = SerialLink()
        self.scheduler = AlarmScheduler(lambda: self.alarms, self._on_alarm_fired)

        self.window = MainWindow(root, self, self.settings)
        self.alerts = AlertManager(root, self.sound, self._stop_siren_command, self.log)

        self._closing = False
        self._connected = False
        self._scanning = False
        self._scan_manual_pending = False
        self._legacy_warned = False
        self._save_error_shown = False
        self._last_info = None
        self._last_info_at: float | None = None
        self._last_sync: datetime | None = None

        self._init_ui()
        self._start_loops()

        self.log(f"Terminal iniciada · Reloj Maestro v{APP_VERSION}")
        self.log(f"Configuración: {self.store.path}")
        self.log(f"Bitácora: {self.activity.path}")
        if self.alarms:
            self.log(f"{len(self.alarms)} alarma(s) cargada(s) desde disco.")
        else:
            self.log("No hay alarmas guardadas. Configura la primera.")

        self._scan_ports(manual=False)

    # ------------------------------------------------------------------
    # Inicialización
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        self.window.alarms.render(self.alarms, self.settings.time_format)
        self.window.clock.tick(datetime.now())
        self.window.set_sync_label("Última sincronización: —")
        self._update_next_alarm(datetime.now())

    def _start_loops(self) -> None:
        self.root.after(SCHEDULER_TICK_MS, self._tick_scheduler)
        self.root.after(CLOCK_TICK_MS, self._tick_clock)
        self.root.after(SERIAL_POLL_MS, self._poll_serial)
        self.root.after(PORT_SCAN_INTERVAL_MS, self._periodic_scan)

    # ------------------------------------------------------------------
    # Bucles periódicos
    # ------------------------------------------------------------------
    def _tick_scheduler(self) -> None:
        if self._closing:
            return
        try:
            if self.scheduler.tick():
                self._save()
        except Exception:
            self.activity.write(traceback.format_exc(), "ERROR")
        finally:
            if not self._closing:
                self.root.after(SCHEDULER_TICK_MS, self._tick_scheduler)

    def _tick_clock(self) -> None:
        if self._closing:
            return
        now = datetime.now()
        try:
            self.window.clock.tick(now)
            self._update_next_alarm(now)
            self._maybe_periodic_time_sync(now)
        finally:
            if not self._closing:
                self.root.after(CLOCK_TICK_MS, self._tick_clock)

    def _poll_serial(self) -> None:
        if self._closing:
            return
        while True:
            try:
                event = self.link.events.get_nowait()
            except queue.Empty:
                break
            try:
                self._handle_event(event)
            except Exception:
                self.activity.write(traceback.format_exc(), "ERROR")
        if not self._closing:
            self.root.after(SERIAL_POLL_MS, self._poll_serial)

    def _periodic_scan(self) -> None:
        if self._closing:
            return
        if not self._connected:
            self._scan_ports(manual=False)
        self.root.after(PORT_SCAN_INTERVAL_MS, self._periodic_scan)

    # ------------------------------------------------------------------
    # Alarmas
    # ------------------------------------------------------------------
    def _on_alarm_fired(self, alarm: Alarm, now: datetime) -> None:
        label = alarm.time_label(self.settings.time_format)
        if self.alerts.show(alarm, "PC (respaldo local)", label):
            self.log(f"⏰ Alarma local: {label} · {alarm.days_label}")
        else:
            self.activity.write(f"Alarma local duplicada ignorada: {label}", "DEBUG")

    def on_save_alarm(self, hour: int, minute: int, duration: int, days: int) -> None:
        try:
            validate_alarm_fields(hour, minute, duration, days)
        except AlarmValidationError as exc:
            messagebox.showwarning("Datos inválidos", str(exc), parent=self.root)
            return

        editing_id = self.window.form.editing_id
        if editing_id is not None:
            alarm = self._find_alarm(editing_id)
            if alarm is None:
                self.window.form.reset()
                self.log("La alarma que intentabas editar ya no existe.")
                return
            alarm.hour = hour
            alarm.minute = minute
            alarm.duration = duration
            alarm.days = days
            alarm.last_fired = None
            action = "edit"
        else:
            new_id = max((item.id for item in self.alarms), default=0) + 1
            alarm = Alarm(
                id=new_id,
                hour=hour,
                minute=minute,
                duration=duration,
                days=days,
                enabled=True,
            )
            self.alarms.append(alarm)
            action = "add"

        self._save()
        self.log(f"Alarma {'actualizada' if action == 'edit' else 'guardada'}: "
                 f"{alarm.time_label(self.settings.time_format)} · {alarm.days_label}")

        self.window.form.reset()
        self._refresh_alarms()
        self._update_next_alarm(datetime.now())
        self._sync_after_change(action, alarm)

    def on_edit_alarm(self, alarm_id: int) -> None:
        alarm = self._find_alarm(alarm_id)
        if alarm is not None:
            self.window.form.start_edit(alarm)

    def on_cancel_edit(self) -> None:
        self.window.form.reset()

    def on_toggle_alarm(self, alarm_id: int, enabled: bool) -> None:
        alarm = self._find_alarm(alarm_id)
        if alarm is None:
            return
        alarm.enabled = bool(enabled)
        self._save()
        self.root.after_idle(self._refresh_alarms)
        self._update_next_alarm(datetime.now())
        self.log(
            f"Alarma {'activada' if alarm.enabled else 'desactivada'}: "
            f"{alarm.time_label(self.settings.time_format)}"
        )
        self._sync_after_change("enable" if alarm.enabled else "disable", alarm)

    def on_delete_alarm(self, alarm_id: int) -> None:
        alarm = self._find_alarm(alarm_id)
        if alarm is None:
            return
        self.alarms = [item for item in self.alarms if item.id != alarm_id]
        if self.window.form.editing_id == alarm_id:
            self.window.form.reset()
        self._save()
        self.root.after_idle(self._refresh_alarms)
        self._update_next_alarm(datetime.now())
        self.log(
            f"Alarma eliminada: {alarm.time_label(self.settings.time_format)} · {alarm.days_label}"
        )
        self._sync_after_change("delete", alarm)

    def _find_alarm(self, alarm_id: int) -> Alarm | None:
        return next((alarm for alarm in self.alarms if alarm.id == alarm_id), None)

    def _refresh_alarms(self) -> None:
        self.window.alarms.render(self.alarms, self.settings.time_format)

    def _update_next_alarm(self, now: datetime) -> None:
        next_alarm = self.scheduler.next_occurrence(now)
        if next_alarm is None:
            self.window.set_next_alarm("Sin alarmas activas", urgent=False)
            return

        alarm, when = next_alarm
        days = (when.date() - now.date()).days
        if days == 0:
            prefix = "Hoy"
        elif days == 1:
            prefix = "Mañana"
        else:
            prefix = DAY_NAMES_LONG[day_index(when)]

        delta = when - now
        label = alarm.time_label(self.settings.time_format)
        self.window.set_next_alarm(
            f"Próxima alarma: {prefix} {label} · en {format_timedelta(delta)}",
            urgent=delta.total_seconds() <= 300,
        )

    def _find_alarm_for_alert(self, event, now: datetime) -> Alarm | None:
        if event.alarm_id is not None:
            alarm = self._find_alarm(event.alarm_id)
            if alarm is not None:
                return alarm

        info = self._last_info
        if info is not None and self._last_info_at is not None:
            if time.monotonic() - self._last_info_at <= 5.0:
                for alarm in self.alarms:
                    if (
                        alarm.enabled
                        and alarm.hour == info.hour24
                        and alarm.minute == info.minute
                        and bit_read(alarm.days, info.day_index)
                    ):
                        return alarm

        for alarm in self.alarms:
            if alarm.enabled and alarm.hour == now.hour and alarm.minute == now.minute:
                return alarm
        return None

    # ------------------------------------------------------------------
    # Hardware
    # ------------------------------------------------------------------
    def on_connect_clicked(self) -> None:
        if self._connected or self.link.opening:
            return
        port = self.window.connection.selected_port()
        if not port:
            self.log("Selecciona un puerto COM válido antes de conectar.")
            return

        self.settings.last_port = port
        self._save()
        self.window.connection.set_state("connecting", f"Abriendo {port}...")
        self.log(f"Conectando a {port}...")
        threading.Thread(
            target=self._connect_worker,
            args=(port,),
            name="reloj-serial-open",
            daemon=True,
        ).start()

    def _connect_worker(self, port: str) -> None:
        try:
            self.link.open(port)
        except Exception as exc:
            self.link.events.put(("status", "error", str(exc), FirmwareMode.UNKNOWN))

    def on_disconnect_clicked(self) -> None:
        if not self._connected and not self.link.opening:
            return
        self.log("Desconectando hardware...")
        self.link.close()

    def on_refresh_ports_clicked(self) -> None:
        self._scan_ports(manual=True)

    def on_sync_clicked(self) -> None:
        if not self._connected:
            self.log("Conecta el Arduino para sincronizar.")
            return
        self._sync_hardware(full=True, reason="manual")

    def on_test_siren_clicked(self) -> None:
        if not self._connected:
            self.log("Conecta el Arduino para probar la sirena.")
            return
        if self.link.mode != FirmwareMode.V2:
            self.log("La prueba remota de sirena requiere firmware v2.")
            return
        self.link.send(build_test_siren(5))
        self.log("🔔 Prueba de sirena enviada (5 s).")

    def on_stop_siren_clicked(self) -> None:
        self._stop_siren_command()

    def _stop_siren_command(self) -> None:
        if self._connected and self.link.mode == FirmwareMode.V2:
            self.link.send(build_stop_siren())
            self.log("⏹ Orden de parada enviada al hardware.")
        elif self._connected:
            self.log("El firmware legacy no permite detener la sirena remotamente.")
        else:
            self.log("Sirena local detenida (hardware desconectado).")
        self.sound.stop()

    def _sync_hardware(self, full: bool = True, reason: str = "") -> None:
        if not self._connected:
            return
        now = datetime.now()
        self.link.send(build_time_sync(now))

        enabled = [alarm for alarm in self.alarms if alarm.enabled]
        if self.link.mode == FirmwareMode.V2:
            self.link.send(build_date_sync(now))
            self.link.send(build_clear())
            for alarm in enabled:
                self.link.send(build_alarm_v2(alarm))
            if len(enabled) > MAX_HARDWARE_ALARMS:
                self.log(
                    f"Aviso: el firmware de referencia admite {MAX_HARDWARE_ALARMS} alarmas; "
                    f"se enviaron {len(enabled)}."
                )
        else:
            for alarm in enabled:
                self.link.send(build_alarm_legacy(alarm))
            self._warn_legacy()

        self._last_sync = now
        self.window.set_sync_label(f"Última sincronización: {now:%H:%M:%S}")
        suffix = f" ({reason})" if reason else ""
        self.log(f"Sincronización completada{suffix}: {len(enabled)} alarma(s) enviada(s).")

    def _sync_after_change(self, action: str, alarm: Alarm | None) -> None:
        if not self._connected:
            self.log("Cambio guardado localmente; se enviará al conectar el Arduino.")
            return

        if self.link.mode == FirmwareMode.V2:
            self._sync_hardware(full=True, reason="cambio")
            return

        # Firmware legacy: solo se pueden añadir alarmas, no borrarlas ni editarlas.
        if action in ("add", "edit", "enable") and alarm is not None and alarm.enabled:
            self.link.send(build_alarm_legacy(alarm))
            self.log("Alarma enviada al hardware legacy.")
        if action in ("edit", "delete", "disable"):
            self._warn_legacy()

    def _warn_legacy(self) -> None:
        if self._legacy_warned:
            return
        self._legacy_warned = True
        self.log(
            "Firmware legacy: las alarmas borradas, editadas o desactivadas pueden "
            "permanecer en el Arduino hasta reiniciarlo."
        )

    def _maybe_periodic_time_sync(self, now: datetime) -> None:
        if not self._connected:
            return
        if self._last_sync is not None:
            elapsed = (now - self._last_sync).total_seconds()
            if elapsed < TIME_SYNC_INTERVAL_SECONDS:
                return
        if self.link.send(build_time_sync(now)):
            self._last_sync = now
            self.window.set_sync_label(f"Última sincronización: {now:%H:%M:%S}")
            self.activity.write("Sincronización periódica de hora enviada.", "DEBUG")

    # ------------------------------------------------------------------
    # Eventos del enlace serial
    # ------------------------------------------------------------------
    def _handle_event(self, event: tuple) -> None:
        tag = event[0]
        if tag == "status":
            self._handle_status(event[1], event[2], event[3])
        elif tag == "line":
            self._handle_line(event[2])
        elif tag == "tx":
            self.log(f"TX ➔ {event[1]}")
        elif tag == "tx_error":
            self.log(f"No se pudo enviar '{event[1]}': {event[2]}")
        elif tag == "ports":
            self._handle_ports(event[1], event[2])

    def _handle_status(self, state: str, detail: str, mode: FirmwareMode) -> None:
        if state == "connecting":
            self._connected = False
            self.window.connection.set_state("connecting", f"Abriendo {detail}...")
        elif state == "online":
            self._connected = True
            self._last_info = None
            self._last_info_at = None
            self.window.connection.set_state("online", "", mode)
            self.log(f"Hardware conectado · {mode_label(mode)}")
            self._sync_hardware(full=True, reason="conexión")
        elif state in ("offline", "disconnected"):
            self._connected = False
            self.window.connection.set_state("offline", detail if state == "disconnected" else "")
            self.window.clock.reset_hardware()
            self._last_info = None
            self._last_info_at = None
            self.log("Hardware desconectado." if state == "offline" else f"Conexión perdida: {detail}")
        elif state == "error":
            self._connected = False
            self.window.connection.set_state("error", detail)
            self.log(f"Error de conexión: {detail}")

    def _handle_line(self, event) -> None:
        if event.type == EventType.INFO:
            self._last_info = event.info
            self._last_info_at = time.monotonic()
            if event.info is not None:
                self.window.clock.show_hardware_time(event.info, self._last_info_at)
        elif event.type == EventType.ALERT:
            self._handle_hardware_alert(event)
        elif event.type == EventType.READY:
            self.activity.write(f"Handshake: {event.raw}", "DEBUG")
        elif event.type == EventType.ACK:
            self.activity.write(f"ACK: {event.raw}", "DEBUG")
        elif event.type == EventType.ERROR:
            self.log(f"Hardware: {event.raw}")
        else:
            self.activity.write(f"RX desconocido: {event.raw}", "DEBUG")

    def _handle_hardware_alert(self, event) -> None:
        now = datetime.now()
        alarm = self._find_alarm_for_alert(event, now)
        label = (
            alarm.time_label(self.settings.time_format)
            if alarm is not None
            else format_time(now.hour, now.minute, self.settings.time_format)
        )
        if self.alerts.show(alarm, "Arduino (hardware)", label):
            self.log(f"🚨 Alerta del hardware: {label}")
            if alarm is not None:
                alarm.mark_fired(now)
                self._save()
        else:
            self.activity.write(f"Alerta de hardware duplicada ignorada: {event.raw}", "DEBUG")

    def _handle_ports(self, ports: list[PortInfo], manual: bool) -> None:
        self._scanning = False
        self.window.connection.set_scanning(False)
        if self._connected:
            return
        self.window.connection.set_ports(ports, self.settings.last_port)
        if manual:
            if ports:
                self.log("Puertos encontrados: " + ", ".join(port.device for port in ports))
            else:
                self.log("No se encontraron puertos COM.")
        self._scan_manual_pending = False

    def _scan_ports(self, manual: bool) -> None:
        if self._connected:
            if manual:
                self.log("Desconecta el Arduino para actualizar la lista de puertos.")
            return
        if self._scanning:
            self._scan_manual_pending = self._scan_manual_pending or manual
            return

        self._scanning = True
        self._scan_manual_pending = manual
        self.window.connection.set_scanning(True)

        def worker() -> None:
            ports = SerialLink.list_ports()
            self.link.events.put(("ports", ports, self._scan_manual_pending))

        threading.Thread(
            target=worker,
            name="reloj-port-scanner",
            daemon=True,
        ).start()

    # ------------------------------------------------------------------
    # Ajustes, bitácora y cierre
    # ------------------------------------------------------------------
    def on_appearance_change(self, label: str) -> None:
        appearance = appearance_from_label(label)
        if appearance == self.settings.appearance:
            return
        self.settings.appearance = appearance
        apply_appearance(appearance)
        self.root.configure(fg_color=BG)
        self.window.set_appearance(appearance)
        self._save()
        self.log(f"Tema visual cambiado a {appearance_label(appearance).lower()}.")

    def on_time_format_change(self, value: str) -> None:
        time_format = TIME_FORMAT_24 if value.replace(" ", "") == "24h" else TIME_FORMAT_12
        if time_format == self.settings.time_format:
            return
        self.settings.time_format = time_format
        self._save()
        self.window.set_time_format(time_format)
        self._refresh_alarms()
        self._update_next_alarm(datetime.now())

    def on_sound_change(self, enabled: bool) -> None:
        self.settings.sound_enabled = bool(enabled)
        self.sound.enabled = bool(enabled)
        self._save()
        self.log(f"Sonido local {'activado' if enabled else 'desactivado'}.")

    def on_clear_log(self) -> None:
        self.activity.write("Bitácora limpiada por el usuario.", "INFO")
        self.window.log.append("Bitácora limpiada.")

    def on_open_log_folder(self) -> None:
        folder = self.activity.path.parent
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(folder))  # type: ignore[attr-defined]
            else:
                self.log(f"Carpeta de datos: {folder}")
        except Exception as exc:
            self.log(f"No se pudo abrir la carpeta: {exc}")

    def _save(self) -> None:
        try:
            self.store.save(self.alarms, self.settings)
            self._save_error_shown = False
        except OSError as exc:
            self.activity.write(f"No se pudo guardar la configuración: {exc}", "ERROR")
            if not self._save_error_shown:
                self._save_error_shown = True
                self.log(f"⚠ No se pudo guardar la configuración: {exc}")

    def log(self, message: str, level: str = "INFO") -> None:
        self.activity.write(message, level)
        if hasattr(self, "window"):
            self.window.log.append(message)

    def on_close(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.log("Cerrando terminal...")
        try:
            self.alerts.destroy()
        except Exception:
            pass
        self.sound.stop()
        try:
            self.link.close(emit=False)
        except Exception:
            pass
        self._save()
        self.root.after(100, self.root.destroy)


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def configure_window(root: ctk.CTk) -> None:
    """Ajusta tamaño, posición y límites mínimos según la pantalla."""
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    width = min(1180, max(980, int(screen_width * 0.86)))
    height = min(860, max(630, int(screen_height * 0.86)))
    x = max(0, (screen_width - width) // 2)
    # Desplazar un poco hacia arriba para no invadir la barra de tareas.
    y = max(0, (screen_height - height) // 2 - 24)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.minsize(980, 630)


def main() -> None:
    apply_appearance(APPEARANCE_LIGHT)
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title(APP_TITLE)
    root.configure(fg_color=BG)

    try:
        root.iconbitmap(str(resource_path(ICON_FILENAME)))
    except Exception:
        pass

    configure_window(root)

    try:
        controller = AppController(root)
    except Exception:
        details = traceback.format_exc()
        try:
            ActivityLog(log_path()).write(details, "FATAL")
        except Exception:
            pass
        messagebox.showerror(
            "Error al iniciar",
            "No se pudo iniciar la aplicación.\n\n"
            "Se guardó el detalle en la bitácora.\n\n"
            + details[-1200:],
            parent=root,
        )
        root.destroy()
        return

    def report_callback_exception(exc_type, exc_value, exc_tb) -> None:
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        controller.activity.write(details, "ERROR")
        messagebox.showerror(
            "Error inesperado",
            "Ocurrió un error en la interfaz. Revisa la bitácora para más detalles.",
            parent=root,
        )

    root.report_callback_exception = report_callback_exception
    root.protocol("WM_DELETE_WINDOW", controller.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
