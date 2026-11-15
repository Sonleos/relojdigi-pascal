"""Ventana de alerta y control de alertas duplicadas."""

from __future__ import annotations

import time
from typing import Callable

import customtkinter as ctk

from ..config import ALERT_DEDUPE_SECONDS
from ..domain.models import Alarm
from ..services.sound import AlarmSound
from .theme import (
    BG,
    CARD,
    DANGER_BUTTON,
    DIM,
    FONT_ALERT_TIME,
    FONT_BODY,
    FONT_BUTTON,
    FONT_SMALL,
    FONT_TITLE,
    MUTED,
    PAD_CARD,
    SECONDARY_BUTTON,
    TEXT,
    WARNING,
)


class AlertWindow(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        time_label: str,
        detail: str,
        source: str,
        on_stop: Callable[[], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._on_close = on_close

        self.title("Alarma activada")
        self.geometry("480x300")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.transient(master)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        frame = ctk.CTkFrame(
            self,
            **{**CARD, "border_color": WARNING, "border_width": 1},
        )
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            frame,
            text="ALARMA ACTIVADA",
            font=FONT_TITLE,
            text_color=WARNING,
        ).pack(pady=(24, 2))

        ctk.CTkLabel(
            frame,
            text=time_label,
            font=FONT_ALERT_TIME,
            text_color=TEXT,
        ).pack(pady=(4, 2))

        ctk.CTkLabel(
            frame,
            text=detail,
            font=FONT_BODY,
            text_color=MUTED,
            justify="center",
        ).pack(pady=(0, 2))

        ctk.CTkLabel(
            frame,
            text=f"Origen: {source}",
            font=FONT_SMALL,
            text_color=DIM,
        ).pack()

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(pady=(18, PAD_CARD))

        ctk.CTkButton(
            buttons,
            text="Detener sirena",
            command=on_stop,
            font=FONT_BUTTON,
            width=150,
            height=36,
            **DANGER_BUTTON,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            buttons,
            text="Cerrar",
            command=on_close,
            font=FONT_BUTTON,
            width=96,
            height=36,
            **SECONDARY_BUTTON,
        ).pack(side="left", padx=6)

        self.update_idletasks()
        self._center_on(master)

    def _center_on(self, master) -> None:
        try:
            master.update_idletasks()
            width = self.winfo_width()
            height = self.winfo_height()
            x = master.winfo_x() + (master.winfo_width() - width) // 2
            y = master.winfo_y() + (master.winfo_height() - height) // 2
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass
        self.lift()


class AlertManager:
    """Abre una sola alerta y descarta duplicados PC/Arduino."""

    def __init__(
        self,
        master,
        sound: AlarmSound,
        on_stop_siren: Callable[[], None],
        logger: Callable[[str], None],
    ) -> None:
        self._master = master
        self._sound = sound
        self._on_stop_siren = on_stop_siren
        self._logger = logger
        self._window: AlertWindow | None = None
        self._last_shown_at: float = 0.0

    @property
    def active(self) -> bool:
        return self._window is not None

    def show(self, alarm: Alarm | None, source: str, time_label: str) -> bool:
        if self._window is not None:
            return False

        now = time.monotonic()
        if now - self._last_shown_at < ALERT_DEDUPE_SECONDS:
            return False
        self._last_shown_at = now

        detail = alarm.days_label if alarm is not None else "Alarma reportada por el hardware"
        self._sound.start()
        self._window = AlertWindow(
            self._master,
            time_label=time_label,
            detail=detail,
            source=source,
            on_stop=self._stop,
            on_close=self._close,
        )
        return True

    def _stop(self) -> None:
        try:
            self._on_stop_siren()
        finally:
            self._close()

    def _close(self) -> None:
        self._sound.stop()
        window = self._window
        self._window = None
        if window is not None:
            try:
                window.destroy()
            except Exception:
                pass

    def destroy(self) -> None:
        self._close()
