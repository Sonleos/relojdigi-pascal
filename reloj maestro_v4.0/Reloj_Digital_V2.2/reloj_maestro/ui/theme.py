"""Tokens de diseño y gestión del modo claro/oscuro.

Todos los colores se declaran como pares ``(claro, oscuro)``. CustomTkinter
los resuelve automáticamente al cambiar de apariencia, así que los paneles no
necesitan reconstruirse ni repintarse a mano.

Para personalizar el estilo de la aplicación (por ejemplo, adaptarlo a los
colores de un instituto), basta con editar los diccionarios ``LIGHT`` y
``DARK``. Los widgets solo usan los nombres semánticos definidos más abajo.
"""

from __future__ import annotations

import customtkinter as ctk

from ..config import APPEARANCE_DARK, APPEARANCE_LIGHT, APPEARANCES

# ---------------------------------------------------------------------------
# Paletas base
# ---------------------------------------------------------------------------
LIGHT = {
    "bg": "#F3F6F9",
    "surface": "#FFFFFF",
    "surface_alt": "#F7F9FC",
    "surface_hover": "#EDF2F7",
    "border": "#DCE4EC",
    "border_strong": "#C4D0DC",
    "text": "#17212B",
    "muted": "#5E6E7E",
    "dim": "#95A3B1",
    "accent": "#1B5E86",
    "accent_hover": "#154B6C",
    "accent_soft": "#E9F2F8",
    "on_accent": "#FFFFFF",
    "success": "#1F7A4D",
    "success_hover": "#17603C",
    "success_soft": "#E6F4EC",
    "warning": "#A96500",
    "warning_soft": "#FFF3DF",
    "danger": "#B23A32",
    "danger_hover": "#922E27",
    "danger_soft": "#FBEAE8",
    "on_danger": "#FFFFFF",
    "clock_text": "#122A3A",
    "input_bg": "#FFFFFF",
    "log_bg": "#F7F9FC",
    "log_text": "#334155",
    "switch_track": "#CBD5E1",
    "switch_knob": "#FFFFFF",
    "switch_knob_hover": "#F1F5F9",
}

DARK = {
    "bg": "#0D1319",
    "surface": "#141C24",
    "surface_alt": "#1A242E",
    "surface_hover": "#22303C",
    "border": "#2A3947",
    "border_strong": "#3A4C5D",
    "text": "#E7EEF5",
    "muted": "#9AAABB",
    "dim": "#6C7D8D",
    "accent": "#5AA9D6",
    "accent_hover": "#77BCE2",
    "accent_soft": "#17303F",
    "on_accent": "#07141D",
    "success": "#4CD18E",
    "success_hover": "#6ADFA3",
    "success_soft": "#12352A",
    "warning": "#F0B354",
    "warning_soft": "#382A12",
    "danger": "#F27A70",
    "danger_hover": "#F79A92",
    "danger_soft": "#3A1C1B",
    "on_danger": "#1A0A09",
    "clock_text": "#EAF2F8",
    "input_bg": "#101820",
    "log_bg": "#0B1218",
    "log_text": "#C3D0DC",
    "switch_track": "#33465A",
    "switch_knob": "#E9F1F8",
    "switch_knob_hover": "#F4FAFF",
}


def _pair(name: str) -> tuple[str, str]:
    return (LIGHT[name], DARK[name])


# ---------------------------------------------------------------------------
# Colores semánticos
# ---------------------------------------------------------------------------
BG = _pair("bg")
SURFACE = _pair("surface")
SURFACE_ALT = _pair("surface_alt")
SURFACE_HOVER = _pair("surface_hover")
BORDER = _pair("border")
BORDER_STRONG = _pair("border_strong")
TEXT = _pair("text")
MUTED = _pair("muted")
DIM = _pair("dim")
ACCENT = _pair("accent")
ACCENT_HOVER = _pair("accent_hover")
ACCENT_SOFT = _pair("accent_soft")
ON_ACCENT = _pair("on_accent")
SUCCESS = _pair("success")
SUCCESS_HOVER = _pair("success_hover")
SUCCESS_SOFT = _pair("success_soft")
WARNING = _pair("warning")
WARNING_SOFT = _pair("warning_soft")
DANGER = _pair("danger")
DANGER_HOVER = _pair("danger_hover")
DANGER_SOFT = _pair("danger_soft")
ON_DANGER = _pair("on_danger")
CLOCK_TEXT = _pair("clock_text")
INPUT_BG = _pair("input_bg")
LOG_BG = _pair("log_bg")
LOG_TEXT = _pair("log_text")
SWITCH_TRACK = _pair("switch_track")
SWITCH_KNOB = _pair("switch_knob")
SWITCH_KNOB_HOVER = _pair("switch_knob_hover")

# ---------------------------------------------------------------------------
# Tipografía
# ---------------------------------------------------------------------------
FONT_UI = "Segoe UI"
FONT_DISPLAY = "Segoe UI"
FONT_MONO = "Consolas"

FONT_LOGO = (FONT_UI, 13, "bold")
FONT_BRAND = (FONT_UI, 18, "bold")
FONT_TITLE = (FONT_UI, 16, "bold")
FONT_SECTION = (FONT_UI, 10, "bold")
FONT_LABEL = (FONT_UI, 11)
FONT_BODY = (FONT_UI, 12)
FONT_SMALL = (FONT_UI, 10)
FONT_BUTTON = (FONT_UI, 11, "bold")
FONT_BUTTON_SMALL = (FONT_UI, 10, "bold")
FONT_CLOCK = (FONT_DISPLAY, 40, "bold")
FONT_ALARM_TIME = (FONT_DISPLAY, 17, "bold")
FONT_ALERT_TIME = (FONT_DISPLAY, 28, "bold")

# ---------------------------------------------------------------------------
# Espaciado y radios
# ---------------------------------------------------------------------------
RADIUS_CARD = 14
RADIUS_CONTROL = 8
PAD_PAGE = 20
PAD_CARD = 14
GAP = 12

# ---------------------------------------------------------------------------
# Estilos reutilizables para widgets
# ---------------------------------------------------------------------------
CARD = {
    "fg_color": SURFACE,
    "corner_radius": RADIUS_CARD,
    "border_width": 1,
    "border_color": BORDER,
}

PRIMARY_BUTTON = {
    "fg_color": ACCENT,
    "hover_color": ACCENT_HOVER,
    "text_color": ON_ACCENT,
    "text_color_disabled": DIM,
    "corner_radius": RADIUS_CONTROL,
    "border_width": 0,
}

SECONDARY_BUTTON = {
    "fg_color": SURFACE_ALT,
    "hover_color": SURFACE_HOVER,
    "text_color": TEXT,
    "text_color_disabled": DIM,
    "corner_radius": RADIUS_CONTROL,
    "border_width": 1,
    "border_color": BORDER,
}

QUIET_BUTTON = {
    "fg_color": "transparent",
    "hover_color": SURFACE_HOVER,
    "text_color": MUTED,
    "text_color_disabled": DIM,
    "corner_radius": RADIUS_CONTROL,
    "border_width": 0,
}

DANGER_BUTTON = {
    "fg_color": DANGER,
    "hover_color": DANGER_HOVER,
    "text_color": ON_DANGER,
    "text_color_disabled": DIM,
    "corner_radius": RADIUS_CONTROL,
    "border_width": 0,
}

DANGER_QUIET_BUTTON = {
    "fg_color": "transparent",
    "hover_color": DANGER_SOFT,
    "text_color": DANGER,
    "text_color_disabled": DIM,
    "corner_radius": RADIUS_CONTROL,
    "border_width": 1,
    "border_color": BORDER,
}

INPUT = {
    "fg_color": INPUT_BG,
    "border_color": BORDER,
    "border_width": 1,
    "text_color": TEXT,
    "text_color_disabled": DIM,
    "corner_radius": RADIUS_CONTROL,
}

# CTkOptionMenu no admite borde propio; el combo sí.
OPTION_MENU = {
    "fg_color": INPUT_BG,
    "text_color": TEXT,
    "text_color_disabled": DIM,
    "corner_radius": RADIUS_CONTROL,
    "button_color": SURFACE_ALT,
    "button_hover_color": SURFACE_HOVER,
    "dropdown_fg_color": SURFACE,
    "dropdown_hover_color": SURFACE_HOVER,
    "dropdown_text_color": TEXT,
}

COMBOBOX = {
    **OPTION_MENU,
    "border_color": BORDER,
    "border_width": 1,
}

SEGMENTED = {
    "selected_color": ACCENT,
    "selected_hover_color": ACCENT_HOVER,
    "unselected_color": SURFACE_ALT,
    "unselected_hover_color": SURFACE_HOVER,
    "text_color": TEXT,
    "text_color_disabled": DIM,
    "border_width": 0,
    "corner_radius": RADIUS_CONTROL,
}

SWITCH = {
    "progress_color": ACCENT,
    "fg_color": SWITCH_TRACK,
    "button_color": SWITCH_KNOB,
    "button_hover_color": SWITCH_KNOB_HOVER,
    "border_color": BORDER,
    "text_color": TEXT,
    "text_color_disabled": DIM,
}

CHECKBOX = {
    "fg_color": ACCENT,
    "hover_color": ACCENT_HOVER,
    "border_color": BORDER_STRONG,
    "checkmark_color": ON_ACCENT,
    "text_color": TEXT,
    "text_color_disabled": DIM,
}

RADIO = {
    "fg_color": ACCENT,
    "hover_color": ACCENT_HOVER,
    "border_color": BORDER_STRONG,
    "text_color": TEXT,
    "text_color_disabled": DIM,
}

SCROLL = {
    "fg_color": SURFACE_ALT,
    "border_width": 0,
    "scrollbar_fg_color": SURFACE_ALT,
    "scrollbar_button_color": BORDER,
    "scrollbar_button_hover_color": BORDER_STRONG,
}

LOG_TEXTBOX = {
    "fg_color": LOG_BG,
    "border_color": BORDER,
    "border_width": 1,
    "text_color": LOG_TEXT,
    "scrollbar_button_color": BORDER,
    "scrollbar_button_hover_color": BORDER_STRONG,
    "corner_radius": RADIUS_CONTROL,
}


# ---------------------------------------------------------------------------
# Apariencia
# ---------------------------------------------------------------------------
APPEARANCE_LABELS = {
    APPEARANCE_LIGHT: "Claro",
    APPEARANCE_DARK: "Oscuro",
}
LABEL_TO_APPEARANCE = {label: value for value, label in APPEARANCE_LABELS.items()}


def normalize_appearance(value: str | None) -> str:
    """Devuelve un modo de apariencia válido (por defecto, claro)."""
    value = (value or "").strip().lower()
    if value in APPEARANCES:
        return value
    return APPEARANCE_LIGHT


def appearance_label(value: str | None) -> str:
    return APPEARANCE_LABELS[normalize_appearance(value)]


def appearance_from_label(label: str | None) -> str:
    return LABEL_TO_APPEARANCE.get((label or "").strip(), APPEARANCE_LIGHT)


def apply_appearance(value: str | None) -> str:
    """Aplica el modo y devuelve el valor normalizado."""
    appearance = normalize_appearance(value)
    ctk.set_appearance_mode(appearance)
    return appearance
