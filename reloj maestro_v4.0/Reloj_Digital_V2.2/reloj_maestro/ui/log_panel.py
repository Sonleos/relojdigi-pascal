"""Panel de bitácora con límite de líneas y acceso al archivo."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

import customtkinter as ctk

from ..config import MAX_LOG_LINES
from .components import section_title
from .theme import (
    CARD,
    FONT_MONO,
    FONT_SMALL,
    LOG_TEXTBOX,
    PAD_CARD,
    QUIET_BUTTON,
    SECONDARY_BUTTON,
)


class LogPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_clear: Callable[[], None] | None = None,
        on_open_folder: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, **CARD)
        self._on_clear = on_clear
        self._max_lines = MAX_LOG_LINES

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD_CARD, pady=(PAD_CARD, 6))
        header.grid_columnconfigure(0, weight=1)

        section_title(header, "Registro de actividad").grid(row=0, column=0, sticky="w")

        if on_open_folder is not None:
            ctk.CTkButton(
                header,
                text="Abrir carpeta",
                width=86,
                height=26,
                font=FONT_SMALL,
                command=on_open_folder,
                **QUIET_BUTTON,
            ).grid(row=0, column=1, padx=(4, 4))

        ctk.CTkButton(
            header,
            text="Limpiar",
            width=62,
            height=26,
            font=FONT_SMALL,
            command=self._clear,
            **SECONDARY_BUTTON,
        ).grid(row=0, column=2)

        self.text = ctk.CTkTextbox(
            self,
            font=(FONT_MONO, 10),
            wrap="word",
            state="disabled",
            **LOG_TEXTBOX,
        )
        self.text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    # ------------------------------------------------------------------
    def append(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.text.configure(state="normal")
        self.text.insert("end", f"[{timestamp}] {message}\n")

        try:
            line_count = int(self.text.index("end-1c").split(".")[0])
            if line_count > self._max_lines:
                self.text.delete("1.0", f"{line_count - self._max_lines + 1}.0")
        except (ValueError, IndexError):
            pass

        self.text.see("end")
        self.text.configure(state="disabled")

    def _clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        if self._on_clear is not None:
            self._on_clear()
