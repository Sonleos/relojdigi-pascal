"""Ventana principal: compone los paneles y la barra de estado."""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from ..config import APP_NAME, APP_VERSION, TIME_FORMAT_12, TIME_FORMAT_24
from ..domain.models import Settings
from .alarm_panel import AlarmForm, AlarmListPanel
from .clock_panel import ClockPanel
from .connection_panel import ConnectionPanel
from .log_panel import LogPanel
from .theme import (
    ACCENT,
    BORDER,
    FONT_BRAND,
    FONT_LOGO,
    FONT_SMALL,
    GAP,
    MUTED,
    ON_ACCENT,
    PAD_CARD,
    PAD_PAGE,
    RADIUS_CARD,
    SECONDARY_BUTTON,
    SEGMENTED,
    SURFACE,
    SWITCH,
    TEXT,
    WARNING,
    appearance_label,
)

if TYPE_CHECKING:
    from ..app import AppController


class MainWindow:
    def __init__(self, root: ctk.CTk, controller: "AppController", settings: Settings) -> None:
        self.root = root
        self.controller = controller
        self.settings = settings
        self._log_visible = True

        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_divider()
        self._build_content()
        self._build_status_bar()
        self.set_time_format(settings.time_format)
        self.set_sound(settings.sound_enabled)
        self.set_appearance(settings.appearance)

    # ------------------------------------------------------------------
    def _build_header(self) -> None:
        header = ctk.CTkFrame(self.root, fg_color=SURFACE, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="ew", padx=PAD_PAGE, pady=(11, 10))
        inner.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkFrame(inner, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w")

        logo = ctk.CTkFrame(brand, width=34, height=34, fg_color=ACCENT, corner_radius=9)
        logo.pack(side="left", padx=(0, 12))
        logo.pack_propagate(False)
        ctk.CTkLabel(
            logo,
            text="RM",
            font=FONT_LOGO,
            text_color=ON_ACCENT,
        ).pack(expand=True)

        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side="left")
        ctk.CTkLabel(
            brand_text,
            text=APP_NAME,
            font=FONT_BRAND,
            text_color=TEXT,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand_text,
            text=f"Control de alarmas y hardware · versión {APP_VERSION}",
            font=FONT_SMALL,
            text_color=MUTED,
            anchor="w",
        ).pack(anchor="w")

        controls = ctk.CTkFrame(inner, fg_color="transparent")
        controls.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            controls,
            text="Tema",
            font=FONT_SMALL,
            text_color=MUTED,
        ).pack(side="left", padx=(0, 5))

        self.appearance_var = ctk.StringVar(value=appearance_label(self.settings.appearance))
        self.appearance_seg = ctk.CTkSegmentedButton(
            controls,
            values=["Claro", "Oscuro"],
            variable=self.appearance_var,
            command=self._on_appearance,
            width=106,
            height=30,
            font=FONT_SMALL,
            **SEGMENTED,
        )
        self.appearance_seg.pack(side="left", padx=(0, 14))

        ctk.CTkLabel(
            controls,
            text="Formato",
            font=FONT_SMALL,
            text_color=MUTED,
        ).pack(side="left", padx=(0, 5))

        self.time_format_var = ctk.StringVar(value="12 h")
        self.time_format_seg = ctk.CTkSegmentedButton(
            controls,
            values=["12 h", "24 h"],
            variable=self.time_format_var,
            command=self._on_time_format,
            width=98,
            height=30,
            font=FONT_SMALL,
            **SEGMENTED,
        )
        self.time_format_seg.pack(side="left", padx=(0, 14))

        self.sound_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            controls,
            text="Sonido",
            variable=self.sound_var,
            width=82,
            height=24,
            font=FONT_SMALL,
            command=self._on_sound,
            **SWITCH,
        ).pack(side="left", padx=(0, 14))

        self.btn_log = ctk.CTkButton(
            controls,
            text="Ocultar bitácora",
            command=self.toggle_log,
            font=FONT_SMALL,
            width=116,
            height=30,
            **SECONDARY_BUTTON,
        )
        self.btn_log.pack(side="left")

    def _build_divider(self) -> None:
        ctk.CTkFrame(
            self.root,
            height=1,
            fg_color=BORDER,
            corner_radius=0,
        ).grid(row=1, column=0, sticky="ew")

    def _build_content(self) -> None:
        content = ctk.CTkFrame(self.root, fg_color="transparent")
        content.grid(row=2, column=0, sticky="nsew", padx=PAD_PAGE, pady=(GAP, GAP))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=0, minsize=340)
        content.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(content, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, GAP))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        self.clock = ClockPanel(left, time_format=self.settings.time_format)
        self.clock.grid(row=0, column=0, sticky="ew", pady=(0, GAP))

        self.form = AlarmForm(
            left,
            on_save=self.controller.on_save_alarm,
            on_cancel=self.controller.on_cancel_edit,
            time_format=self.settings.time_format,
        )
        self.form.grid(row=1, column=0, sticky="ew", pady=(0, GAP))

        self.alarms = AlarmListPanel(
            left,
            on_toggle=self.controller.on_toggle_alarm,
            on_edit=self.controller.on_edit_alarm,
            on_delete=self.controller.on_delete_alarm,
        )
        self.alarms.grid(row=2, column=0, sticky="nsew")

        right = ctk.CTkFrame(content, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        self.connection = ConnectionPanel(
            right,
            on_connect=self.controller.on_connect_clicked,
            on_disconnect=self.controller.on_disconnect_clicked,
            on_refresh=self.controller.on_refresh_ports_clicked,
            on_sync=self.controller.on_sync_clicked,
            on_test=self.controller.on_test_siren_clicked,
            on_stop=self.controller.on_stop_siren_clicked,
        )
        self.connection.grid(row=0, column=0, sticky="ew", pady=(0, GAP))

        self.log = LogPanel(
            right,
            on_clear=self.controller.on_clear_log,
            on_open_folder=self.controller.on_open_log_folder,
        )
        self.log.grid(row=1, column=0, sticky="nsew")

    def _build_status_bar(self) -> None:
        bar = ctk.CTkFrame(
            self.root,
            fg_color=SURFACE,
            corner_radius=RADIUS_CARD,
            border_width=1,
            border_color=BORDER,
        )
        bar.grid(row=3, column=0, sticky="ew", padx=PAD_PAGE, pady=(0, GAP))
        bar.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="ew", padx=PAD_CARD, pady=7)
        inner.grid_columnconfigure(0, weight=1)

        self.next_alarm_label = ctk.CTkLabel(
            inner,
            text="Sin alarmas activas",
            font=(FONT_SMALL[0], 11, "bold"),
            text_color=TEXT,
            anchor="w",
        )
        self.next_alarm_label.grid(row=0, column=0, sticky="w")

        self.sync_status_label = ctk.CTkLabel(
            inner,
            text="Última sincronización: —",
            font=FONT_SMALL,
            text_color=MUTED,
            anchor="e",
        )
        self.sync_status_label.grid(row=0, column=1, sticky="e")

    # ------------------------------------------------------------------
    def _on_appearance(self, value: str) -> None:
        self.controller.on_appearance_change(value)

    def _on_time_format(self, value: str) -> None:
        self.controller.on_time_format_change(value)

    def _on_sound(self) -> None:
        self.controller.on_sound_change(bool(self.sound_var.get()))

    def set_appearance(self, appearance: str) -> None:
        value = appearance_label(appearance)
        self.appearance_var.set(value)
        try:
            self.appearance_seg.set(value)
        except Exception:
            pass

    def set_time_format(self, time_format: str) -> None:
        value = "24 h" if time_format == TIME_FORMAT_24 else "12 h"
        self.time_format_var.set(value)
        try:
            self.time_format_seg.set(value)
        except Exception:
            pass
        self.clock.set_time_format(time_format)
        self.form.set_time_format(time_format)

    def set_sound(self, enabled: bool) -> None:
        self.sound_var.set(bool(enabled))

    def set_next_alarm(self, text: str, urgent: bool = False) -> None:
        self.next_alarm_label.configure(
            text=text,
            text_color=WARNING if urgent else TEXT,
        )

    def set_sync_label(self, text: str) -> None:
        self.sync_status_label.configure(text=text)

    def toggle_log(self) -> None:
        if self._log_visible:
            self.log.grid_remove()
            self.btn_log.configure(text="Ver bitácora")
            self._log_visible = False
        else:
            self.log.grid()
            self.btn_log.configure(text="Ocultar bitácora")
            self._log_visible = True

    @property
    def log_visible(self) -> bool:
        return self._log_visible
