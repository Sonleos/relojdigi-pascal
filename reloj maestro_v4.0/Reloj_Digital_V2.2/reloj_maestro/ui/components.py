"""Componentes visuales compartidos por los paneles."""

from __future__ import annotations

import customtkinter as ctk

from .theme import ACCENT, FONT_SECTION, MUTED, RADIUS_CONTROL


class SectionTitle(ctk.CTkFrame):
    """Encabezado de tarjeta con una pequeña marca de acento."""

    def __init__(self, master, text: str) -> None:
        super().__init__(master, fg_color="transparent")
        marker = ctk.CTkFrame(self, width=3, height=14, fg_color=ACCENT, corner_radius=2)
        marker.pack(side="left", padx=(0, 8))
        marker.pack_propagate(False)
        self.label = ctk.CTkLabel(
            self,
            text=text.upper(),
            font=FONT_SECTION,
            text_color=MUTED,
            anchor="w",
        )
        self.label.pack(side="left")

    def set_text(self, text: str) -> None:
        self.label.configure(text=text.upper())


def section_title(master, text: str) -> SectionTitle:
    return SectionTitle(master, text)


def status_pill(master, text: str, text_color, background, width: int = 96) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        master,
        text=text,
        font=FONT_SECTION,
        text_color=text_color,
        fg_color=background,
        corner_radius=RADIUS_CONTROL,
        width=width,
        height=24,
    )
