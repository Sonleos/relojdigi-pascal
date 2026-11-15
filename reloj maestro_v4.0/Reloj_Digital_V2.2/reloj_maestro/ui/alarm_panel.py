"""Formulario de programación y lista de alarmas."""

from __future__ import annotations

from datetime import datetime, timedelta
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from ..config import DEFAULT_DURATION, DURATION_OPTIONS, TIME_FORMAT_12, TIME_FORMAT_24
from ..domain.models import (
    Alarm,
    AlarmValidationError,
    DAY_NAMES,
    format_time,
    from_hour24,
    mask_from_bools,
    mask_to_bools,
    to_hour24,
    validate_alarm_fields,
)
from .components import section_title
from .theme import (
    ACCENT,
    BORDER,
    CARD,
    CHECKBOX,
    DANGER_QUIET_BUTTON,
    DIM,
    FONT_ALARM_TIME,
    FONT_BODY,
    FONT_LABEL,
    FONT_SMALL,
    MUTED,
    OPTION_MENU,
    PAD_CARD,
    PRIMARY_BUTTON,
    QUIET_BUTTON,
    RADIO,
    SCROLL,
    SECONDARY_BUTTON,
    SURFACE,
    SURFACE_ALT,
    SWITCH,
    TEXT,
    WARNING,
)


class AlarmForm(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_save: Callable[[int, int, int, int], None],
        on_cancel: Callable[[], None],
        time_format: str = TIME_FORMAT_12,
    ) -> None:
        super().__init__(master, **CARD)
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._time_format = time_format
        self._editing_id: int | None = None

        self.grid_columnconfigure(0, weight=1)

        # Cabecera ----------------------------------------------------------
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD_CARD, pady=(10, 0))
        header.grid_columnconfigure(0, weight=1)

        self.title_row = section_title(header, "Nueva alarma")
        self.title_row.grid(row=0, column=0, sticky="w")

        self.mode_label = ctk.CTkLabel(
            header,
            text="",
            font=FONT_SMALL,
            text_color=WARNING,
            anchor="e",
        )
        self.mode_label.grid(row=0, column=1, sticky="e", padx=(8, 8))

        self.btn_cancel = ctk.CTkButton(
            header,
            text="Cancelar",
            command=self._cancel,
            font=FONT_SMALL,
            width=82,
            height=30,
            **SECONDARY_BUTTON,
        )
        self.btn_cancel.grid(row=0, column=2, padx=(0, 8))
        self.btn_cancel.grid_remove()

        self.btn_save = ctk.CTkButton(
            header,
            text="Guardar alarma",
            command=self._save,
            font=FONT_SMALL,
            width=128,
            height=30,
            **PRIMARY_BUTTON,
        )
        self.btn_save.grid(row=0, column=3)

        # Hora y duración ---------------------------------------------------
        fields = ctk.CTkFrame(self, fg_color="transparent")
        fields.grid(row=1, column=0, sticky="ew", padx=PAD_CARD, pady=(6, 0))
        fields.grid_columnconfigure(1, weight=1)

        time_group = ctk.CTkFrame(fields, fg_color="transparent")
        time_group.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            time_group,
            text="Hora",
            font=FONT_SMALL,
            text_color=MUTED,
            anchor="w",
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 3))

        self.combo_hour = ctk.CTkOptionMenu(
            time_group,
            values=[f"{hour:02d}" for hour in range(1, 13)],
            width=68,
            height=30,
            font=FONT_LABEL,
            dynamic_resizing=False,
            **OPTION_MENU,
        )
        self.combo_hour.grid(row=1, column=0)

        ctk.CTkLabel(
            time_group,
            text=":",
            font=(FONT_BODY[0], 14, "bold"),
            text_color=MUTED,
        ).grid(row=1, column=1, padx=3)

        self.combo_minute = ctk.CTkOptionMenu(
            time_group,
            values=[f"{minute:02d}" for minute in range(60)],
            width=68,
            height=30,
            font=FONT_LABEL,
            dynamic_resizing=False,
            **OPTION_MENU,
        )
        self.combo_minute.grid(row=1, column=2)

        self.period_frame = ctk.CTkFrame(time_group, fg_color="transparent")
        self.period_frame.grid(row=1, column=3, padx=(12, 0))

        self.period_var = ctk.StringVar(value="AM")
        ctk.CTkRadioButton(
            self.period_frame,
            text="AM",
            variable=self.period_var,
            value="AM",
            width=52,
            font=FONT_SMALL,
            **RADIO,
        ).pack(side="left")
        ctk.CTkRadioButton(
            self.period_frame,
            text="PM",
            variable=self.period_var,
            value="PM",
            width=52,
            font=FONT_SMALL,
            **RADIO,
        ).pack(side="left", padx=(2, 0))

        duration_group = ctk.CTkFrame(fields, fg_color="transparent")
        duration_group.grid(row=0, column=1, sticky="w", padx=(28, 0))

        ctk.CTkLabel(
            duration_group,
            text="Duración",
            font=FONT_SMALL,
            text_color=MUTED,
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 3))

        self.combo_duration = ctk.CTkOptionMenu(
            duration_group,
            values=list(DURATION_OPTIONS),
            width=84,
            height=30,
            font=FONT_LABEL,
            dynamic_resizing=False,
            **OPTION_MENU,
        )
        self.combo_duration.grid(row=1, column=0)

        ctk.CTkLabel(
            duration_group,
            text="segundos",
            font=FONT_SMALL,
            text_color=MUTED,
        ).grid(row=1, column=1, padx=(6, 0))

        # Días --------------------------------------------------------------
        days_row = ctk.CTkFrame(self, fg_color="transparent")
        days_row.grid(row=2, column=0, sticky="ew", padx=PAD_CARD, pady=(8, 10))

        ctk.CTkLabel(
            days_row,
            text="Días",
            font=FONT_SMALL,
            text_color=MUTED,
        ).pack(side="left", padx=(0, 8))

        self.day_vars: list[ctk.BooleanVar] = []
        for name in DAY_NAMES:
            var = ctk.BooleanVar(value=True)
            self.day_vars.append(var)
            ctk.CTkCheckBox(
                days_row,
                text=name,
                variable=var,
                width=52,
                font=FONT_SMALL,
                checkbox_width=16,
                checkbox_height=16,
                **CHECKBOX,
            ).pack(side="left", padx=2)

        self._set_default_values()

    # -- API pública --------------------------------------------------------
    @property
    def editing_id(self) -> int | None:
        return self._editing_id

    def set_time_format(self, time_format: str) -> None:
        if time_format == self._time_format:
            return
        try:
            hour24 = self._read_hour24()
        except (TypeError, ValueError):
            hour24 = 7
        self._time_format = time_format
        self._rebuild_hour_options()
        self._set_hour24(hour24)
        if self._editing_id is not None:
            self.mode_label.configure(text=self._current_time_label())

    def start_edit(self, alarm: Alarm) -> None:
        self._editing_id = alarm.id
        self.title_row.set_text("Editar alarma")
        self.mode_label.configure(text=alarm.time_label(self._time_format))
        self.btn_save.configure(text="Actualizar")
        self.btn_cancel.grid()
        self._set_hour24(alarm.hour)
        self.combo_minute.set(f"{alarm.minute:02d}")
        self.combo_duration.set(str(alarm.duration))
        for var, enabled in zip(self.day_vars, mask_to_bools(alarm.days)):
            var.set(enabled)
        self.combo_hour.focus_set()

    def reset(self) -> None:
        self._editing_id = None
        self.title_row.set_text("Nueva alarma")
        self.mode_label.configure(text="")
        self.btn_save.configure(text="Guardar alarma")
        self.btn_cancel.grid_remove()
        self._set_default_values()

    # -- Internos -----------------------------------------------------------
    def _set_default_values(self) -> None:
        hour, minute = self._next_round_time()
        self._set_hour24(hour)
        self.combo_minute.set(f"{minute:02d}")
        self.combo_duration.set(DEFAULT_DURATION)
        for var in self.day_vars:
            var.set(True)

    @staticmethod
    def _next_round_time() -> tuple[int, int]:
        now = datetime.now().replace(second=0, microsecond=0)
        minutes = (now.minute // 5 + 1) * 5
        if minutes >= 60:
            target = now.replace(minute=0) + timedelta(hours=1)
        else:
            target = now.replace(minute=minutes)
        return target.hour, target.minute

    def _read_hour24(self) -> int:
        value = self.combo_hour.get()
        if self._time_format == TIME_FORMAT_24:
            return int(value)
        return to_hour24(int(value), self.period_var.get())

    def _set_hour24(self, hour24: int) -> None:
        if self._time_format == TIME_FORMAT_24:
            self.combo_hour.set(f"{hour24:02d}")
            return
        hour12, period = from_hour24(hour24)
        self.combo_hour.set(f"{hour12:02d}")
        self.period_var.set(period)

    def _rebuild_hour_options(self) -> None:
        if self._time_format == TIME_FORMAT_24:
            self.combo_hour.configure(values=[f"{hour:02d}" for hour in range(24)])
            self.period_frame.grid_remove()
        else:
            self.combo_hour.configure(values=[f"{hour:02d}" for hour in range(1, 13)])
            self.period_frame.grid()
            self.period_frame.grid(row=1, column=3, padx=(12, 0))

    def _current_time_label(self) -> str:
        try:
            hour = self._read_hour24()
            minute = int(self.combo_minute.get())
        except (TypeError, ValueError):
            return ""
        return format_time(hour, minute, self._time_format)

    def _save(self) -> None:
        try:
            hour = self._read_hour24()
            minute = int(self.combo_minute.get())
            duration = int(self.combo_duration.get())
            days = mask_from_bools(var.get() for var in self.day_vars)
            validate_alarm_fields(hour, minute, duration, days)
        except (TypeError, ValueError, AlarmValidationError) as exc:
            messagebox.showwarning(
                "Datos incompletos",
                str(exc) or "Revisa la hora, la duración y los días.",
                parent=self.winfo_toplevel(),
            )
            return

        self._on_save(hour, minute, duration, days)

    def _cancel(self) -> None:
        self.reset()
        self._on_cancel()


class AlarmListPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_toggle: Callable[[int, bool], None],
        on_edit: Callable[[int], None],
        on_delete: Callable[[int], None],
    ) -> None:
        super().__init__(master, **CARD)
        self._on_toggle = on_toggle
        self._on_edit = on_edit
        self._on_delete = on_delete

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD_CARD, pady=(PAD_CARD, 6))
        header.grid_columnconfigure(0, weight=1)

        section_title(header, "Alarmas programadas").grid(row=0, column=0, sticky="w")

        self.count_label = ctk.CTkLabel(
            header,
            text="",
            font=FONT_SMALL,
            text_color=MUTED,
            anchor="e",
        )
        self.count_label.grid(row=0, column=1, sticky="e")

        self.scroll = ctk.CTkScrollableFrame(self, **SCROLL)
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    # ------------------------------------------------------------------
    def render(self, alarms: list[Alarm], time_format: str) -> None:
        for widget in self.scroll.winfo_children():
            widget.destroy()

        active = sum(1 for alarm in alarms if alarm.enabled)
        if alarms:
            inactive = len(alarms) - active
            active_text = "1 activa" if active == 1 else f"{active} activas"
            inactive_text = "1 desactivada" if inactive == 1 else f"{inactive} desactivadas"
            self.count_label.configure(text=f"{active_text} · {inactive_text}")
        else:
            self.count_label.configure(text="")

        if not alarms:
            ctk.CTkLabel(
                self.scroll,
                text="No hay alarmas programadas.\nCrea la primera con el formulario de arriba.",
                font=FONT_BODY,
                text_color=MUTED,
                justify="center",
            ).pack(pady=18)
            return

        ordered = sorted(alarms, key=lambda alarm: (not alarm.enabled, alarm.hour, alarm.minute, alarm.id))
        for alarm in ordered:
            self._build_row(alarm, time_format)

    # ------------------------------------------------------------------
    def _build_row(self, alarm: Alarm, time_format: str) -> None:
        row = ctk.CTkFrame(
            self.scroll,
            fg_color=SURFACE if alarm.enabled else SURFACE_ALT,
            corner_radius=10,
            border_width=1,
            border_color=BORDER,
        )
        row.pack(fill="x", padx=4, pady=3)
        row.grid_columnconfigure(2, weight=1)

        ctk.CTkFrame(
            row,
            width=3,
            height=26,
            fg_color=ACCENT if alarm.enabled else BORDER,
            corner_radius=2,
        ).grid(row=0, column=0, sticky="ns", padx=(10, 8), pady=7)

        time_color = TEXT if alarm.enabled else DIM
        ctk.CTkLabel(
            row,
            text=alarm.time_label(time_format),
            font=FONT_ALARM_TIME,
            text_color=time_color,
            width=104,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        days_frame = ctk.CTkFrame(row, fg_color="transparent")
        days_frame.grid(row=0, column=2, sticky="w")
        for index, name in enumerate(DAY_NAMES):
            enabled_day = bool((alarm.days >> index) & 0x01)
            if alarm.enabled and enabled_day:
                color, font = ACCENT, (FONT_SMALL[0], 10, "bold")
            elif enabled_day:
                color, font = MUTED, FONT_SMALL
            else:
                color, font = DIM, FONT_SMALL
            ctk.CTkLabel(
                days_frame,
                text=name,
                text_color=color,
                font=font,
            ).pack(side="left", padx=2)

        ctk.CTkLabel(
            row,
            text=f"{alarm.duration} s",
            font=FONT_SMALL,
            text_color=MUTED if alarm.enabled else DIM,
            width=46,
            anchor="e",
        ).grid(row=0, column=3, padx=(8, 4))

        switch_var = ctk.BooleanVar(value=alarm.enabled)
        ctk.CTkSwitch(
            row,
            text="",
            variable=switch_var,
            width=40,
            **SWITCH,
            command=lambda alarm_id=alarm.id, var=switch_var: self._on_toggle(alarm_id, var.get()),
        ).grid(row=0, column=4, padx=4)

        ctk.CTkButton(
            row,
            text="Editar",
            width=62,
            height=28,
            font=FONT_SMALL,
            command=lambda alarm_id=alarm.id: self._on_edit(alarm_id),
            **QUIET_BUTTON,
        ).grid(row=0, column=5, padx=(4, 2))

        ctk.CTkButton(
            row,
            text="Eliminar",
            width=68,
            height=28,
            font=FONT_SMALL,
            command=lambda current=alarm: self._confirm_delete(current, time_format),
            **DANGER_QUIET_BUTTON,
        ).grid(row=0, column=6, padx=(2, 10))

    def _confirm_delete(self, alarm: Alarm, time_format: str) -> None:
        if messagebox.askyesno(
            "Eliminar alarma",
            f"¿Eliminar la alarma de las {alarm.time_label(time_format)}?\n\n{alarm.days_label}",
            parent=self.winfo_toplevel(),
        ):
            self._on_delete(alarm.id)
