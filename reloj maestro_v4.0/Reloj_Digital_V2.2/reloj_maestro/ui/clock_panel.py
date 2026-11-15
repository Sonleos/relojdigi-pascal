"""Tarjeta del reloj: muestra la hora del hardware o la hora local."""

from __future__ import annotations

import time
from datetime import datetime, timedelta

import customtkinter as ctk

from ..config import HARDWARE_INFO_STALE_SECONDS, TIME_FORMAT_12, TIME_FORMAT_24
from ..domain.models import format_date_es
from ..protocol.arduino import ClockInfo
from .components import section_title, status_pill
from .theme import (
    CARD,
    CLOCK_TEXT,
    FONT_BODY,
    FONT_CLOCK,
    MUTED,
    PAD_CARD,
    SUCCESS,
    SUCCESS_SOFT,
    WARNING,
    WARNING_SOFT,
)


class ClockPanel(ctk.CTkFrame):
    def __init__(self, master, time_format: str = TIME_FORMAT_12) -> None:
        super().__init__(master, **CARD)
        self._time_format = time_format
        self._hardware_base: datetime | None = None
        self._hardware_at: float | None = None
        self._last_render: tuple | None = None

        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD_CARD, pady=(PAD_CARD, 0))
        header.grid_columnconfigure(0, weight=1)

        section_title(header, "Hora actual").grid(row=0, column=0, sticky="w")

        self.source_label = status_pill(header, "RELOJ PC", WARNING, WARNING_SOFT, width=104)
        self.source_label.grid(row=0, column=1, sticky="e")

        self.time_label = ctk.CTkLabel(
            self,
            text="--:--:--",
            font=FONT_CLOCK,
            text_color=CLOCK_TEXT,
            anchor="w",
        )
        self.time_label.grid(row=1, column=0, sticky="ew", padx=PAD_CARD, pady=(0, 0))

        self.date_label = ctk.CTkLabel(
            self,
            text="---",
            font=FONT_BODY,
            text_color=MUTED,
            anchor="w",
        )
        self.date_label.grid(row=2, column=0, sticky="ew", padx=PAD_CARD, pady=(0, PAD_CARD))

    # ------------------------------------------------------------------
    def set_time_format(self, time_format: str) -> None:
        if time_format == self._time_format:
            return
        self._time_format = time_format
        self._last_render = None
        self.tick(datetime.now())

    # ------------------------------------------------------------------
    def show_hardware_time(self, info: ClockInfo, received_at: float | None = None) -> None:
        """Guarda la última hora del Arduino y la interpola para que no se congele."""
        now = datetime.now()
        base = datetime.combine(now.date(), now.time()).replace(
            hour=info.hour24,
            minute=info.minute,
            second=info.second,
            microsecond=0,
        )
        # Ajuste de medianoche: la hora del hardware debe quedar cerca de la local.
        if base - now > timedelta(hours=12):
            base -= timedelta(days=1)
        elif now - base > timedelta(hours=12):
            base += timedelta(days=1)

        self._hardware_base = base
        self._hardware_at = received_at if received_at is not None else time.monotonic()
        self.tick(now)

    def reset_hardware(self) -> None:
        self._hardware_base = None
        self._hardware_at = None
        self._last_render = None
        self.tick(datetime.now())

    # ------------------------------------------------------------------
    def tick(self, now: datetime | None = None) -> None:
        now = now or datetime.now()
        source = "pc"
        display = now

        if self._hardware_base is not None and self._hardware_at is not None:
            elapsed = time.monotonic() - self._hardware_at
            if 0 <= elapsed <= HARDWARE_INFO_STALE_SECONDS:
                display = self._hardware_base + timedelta(seconds=elapsed)
                source = "hardware"

        key = (display.strftime("%H:%M:%S"), display.date(), self._time_format, source)
        if key == self._last_render:
            return
        self._last_render = key

        if self._time_format == TIME_FORMAT_24:
            time_text = display.strftime("%H:%M:%S")
        else:
            time_text = display.strftime("%I:%M:%S %p")

        self.time_label.configure(text=time_text)

        if source == "hardware":
            self.source_label.configure(text="HARDWARE", text_color=SUCCESS, fg_color=SUCCESS_SOFT)
            detail = "sincronizado con el reloj maestro"
        else:
            self.source_label.configure(text="RELOJ PC", text_color=WARNING, fg_color=WARNING_SOFT)
            detail = "sin hardware: usando la hora del sistema"
        self.date_label.configure(text=f"{format_date_es(display)}  ·  {detail}")
