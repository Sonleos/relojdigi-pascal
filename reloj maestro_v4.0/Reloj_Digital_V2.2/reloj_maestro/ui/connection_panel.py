"""Panel de conexión serial, sincronización y prueba de sirena."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ..protocol.arduino import FirmwareMode, mode_label
from ..services.serial_link import PortInfo
from .components import section_title, status_pill
from .theme import (
    ACCENT,
    ACCENT_HOVER,
    CARD,
    COMBOBOX,
    DANGER,
    DANGER_BUTTON,
    DANGER_HOVER,
    DANGER_SOFT,
    DIM,
    FONT_BUTTON,
    FONT_LABEL,
    FONT_SMALL,
    MUTED,
    ON_ACCENT,
    ON_DANGER,
    PAD_CARD,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    SUCCESS,
    SUCCESS_SOFT,
    SURFACE_ALT,
    SURFACE_HOVER,
    WARNING,
    WARNING_SOFT,
)


class ConnectionPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_connect: Callable[[], None],
        on_disconnect: Callable[[], None],
        on_refresh: Callable[[], None],
        on_sync: Callable[[], None],
        on_test: Callable[[], None],
        on_stop: Callable[[], None],
    ) -> None:
        super().__init__(master, **CARD)
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._on_refresh = on_refresh
        self._on_sync = on_sync
        self._on_test = on_test
        self._on_stop = on_stop

        self._ports: list[PortInfo] = []
        self._port_map: dict[str, str] = {}
        self._state = "offline"
        self._mode = FirmwareMode.UNKNOWN

        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD_CARD, pady=(PAD_CARD, 4))
        header.grid_columnconfigure(0, weight=1)

        section_title(header, "Hardware").grid(row=0, column=0, sticky="w")

        self.status_pill = status_pill(header, "DESCONECTADO", DANGER, DANGER_SOFT, width=106)
        self.status_pill.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            self,
            text="Puerto serial",
            font=FONT_SMALL,
            text_color=MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=PAD_CARD, pady=(2, 2))

        port_row = ctk.CTkFrame(self, fg_color="transparent")
        port_row.grid(row=2, column=0, sticky="ew", padx=PAD_CARD)
        port_row.grid_columnconfigure(0, weight=1)

        self.combo_ports = ctk.CTkComboBox(
            port_row,
            values=["Buscando..."],
            state="readonly",
            command=self._on_port_selected,
            height=32,
            font=FONT_LABEL,
            **COMBOBOX,
        )
        self.combo_ports.grid(row=0, column=0, sticky="ew")

        self.btn_refresh = ctk.CTkButton(
            port_row,
            text="Actualizar",
            width=82,
            height=32,
            font=FONT_SMALL,
            command=self._on_refresh,
            **SECONDARY_BUTTON,
        )
        self.btn_refresh.grid(row=0, column=1, padx=(8, 0))

        self.port_detail = ctk.CTkLabel(
            self,
            text="Conecta el Arduino por USB y actualiza la lista.",
            font=FONT_SMALL,
            text_color=MUTED,
            anchor="w",
            justify="left",
            wraplength=300,
        )
        self.port_detail.grid(row=3, column=0, sticky="ew", padx=PAD_CARD, pady=(4, 8))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=4, column=0, sticky="ew", padx=PAD_CARD)
        buttons.grid_columnconfigure((0, 1), weight=1)

        self.btn_connect = ctk.CTkButton(
            buttons,
            text="Conectar",
            command=self._on_connect,
            font=FONT_BUTTON,
            height=32,
            **PRIMARY_BUTTON,
        )
        self.btn_connect.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=3)

        self.btn_disconnect = ctk.CTkButton(
            buttons,
            text="Desconectar",
            command=self._on_disconnect,
            font=FONT_BUTTON,
            height=32,
            **SECONDARY_BUTTON,
        )
        self.btn_disconnect.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=3)

        self.btn_sync = ctk.CTkButton(
            buttons,
            text="Sincronizar",
            command=self._on_sync,
            font=FONT_BUTTON,
            height=32,
            **SECONDARY_BUTTON,
        )
        self.btn_sync.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=3)

        self.btn_test = ctk.CTkButton(
            buttons,
            text="Probar sirena",
            command=self._on_test,
            font=FONT_BUTTON,
            height=32,
            **SECONDARY_BUTTON,
        )
        self.btn_test.grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=3)

        self.btn_stop = ctk.CTkButton(
            buttons,
            text="Detener sirena",
            command=self._on_stop,
            font=FONT_BUTTON,
            height=32,
            **DANGER_BUTTON,
        )
        self.btn_stop.grid(row=2, column=0, columnspan=2, sticky="ew", pady=3)

        self.firmware_label = ctk.CTkLabel(
            self,
            text="Firmware: —",
            font=FONT_SMALL,
            text_color=MUTED,
            anchor="w",
        )
        self.firmware_label.grid(row=5, column=0, sticky="ew", padx=PAD_CARD, pady=(6, 0))

        self.detail_label = ctk.CTkLabel(
            self,
            text="La prueba y la parada de sirena requieren firmware v2.",
            font=FONT_SMALL,
            text_color=MUTED,
            anchor="w",
            justify="left",
            wraplength=300,
        )
        self.detail_label.grid(row=6, column=0, sticky="ew", padx=PAD_CARD, pady=(0, PAD_CARD))

        self.set_state("offline")

    # ------------------------------------------------------------------
    def selected_port(self) -> str:
        value = self.combo_ports.get().strip()
        if value.startswith("Sin ") or value.startswith("Buscando"):
            return ""
        return self._port_map.get(value, value)

    def set_ports(self, ports: list[PortInfo], preferred_device: str = "") -> None:
        self._ports = list(ports)
        self._port_map = {}
        displays: list[str] = []

        for port in ports:
            display = port.device
            if port.description and port.description.lower() != "n/a":
                display = f"{port.device} · {port.description}"
            self._port_map[display] = port.device
            displays.append(display)

        if not displays:
            self.combo_ports.configure(values=["Sin puertos"])
            self.combo_ports.set("Sin puertos")
            self.port_detail.configure(text="No se encontraron puertos COM conectados.")
            return

        self.combo_ports.configure(values=displays)

        current = self.combo_ports.get()
        selected = ""
        if current in displays:
            selected = current
        elif preferred_device:
            selected = next((item for item, device in self._port_map.items() if device == preferred_device), "")
        if not selected:
            likely = next((port for port in ports if port.is_likely_arduino), None)
            candidate = likely or ports[0]
            selected = next(item for item, device in self._port_map.items() if device == candidate.device)

        self.combo_ports.set(selected)
        self._on_port_selected(selected)

    def _on_port_selected(self, value: str) -> None:
        device = self._port_map.get(value)
        port = next((item for item in self._ports if item.device == device), None)
        if port is None:
            self.port_detail.configure(text="Selecciona el puerto del Arduino.")
            return
        description = port.description or "Sin descripción"
        hint = " · compatible con Arduino" if port.is_likely_arduino else ""
        self.port_detail.configure(text=f"{description}{hint}")

    # ------------------------------------------------------------------
    def set_state(self, state: str, detail: str = "", mode: FirmwareMode | None = None) -> None:
        self._state = state
        if mode is not None:
            self._mode = mode
        elif state != "online":
            self._mode = FirmwareMode.UNKNOWN

        colors = {
            "offline": ("DESCONECTADO", DANGER, DANGER_SOFT),
            "disconnected": ("DESCONECTADO", DANGER, DANGER_SOFT),
            "connecting": ("CONECTANDO", WARNING, WARNING_SOFT),
            "online": ("CONECTADO", SUCCESS, SUCCESS_SOFT),
            "error": ("ERROR", DANGER, DANGER_SOFT),
        }
        text, fg, bg = colors.get(state, colors["offline"])
        self.status_pill.configure(text=text, text_color=fg, fg_color=bg)

        busy = state in ("connecting", "online")
        self.btn_connect.configure(state="disabled" if busy else "normal")
        if busy:
            self.btn_connect.configure(
                fg_color=SURFACE_ALT,
                hover_color=SURFACE_ALT,
                text_color=DIM,
            )
        else:
            self.btn_connect.configure(
                fg_color=ACCENT,
                hover_color=ACCENT_HOVER,
                text_color=ON_ACCENT,
            )
        self.btn_disconnect.configure(state="normal" if busy else "disabled")
        self.combo_ports.configure(state="disabled" if busy else "readonly")
        self.btn_refresh.configure(state="disabled" if busy else "normal")

        online = state == "online"
        self.btn_sync.configure(state="normal" if online else "disabled")
        can_control = online and self._mode == FirmwareMode.V2
        self.btn_test.configure(state="normal" if can_control else "disabled")
        self.btn_stop.configure(state="normal" if can_control else "disabled")
        if can_control:
            self.btn_stop.configure(
                fg_color=DANGER,
                hover_color=DANGER_HOVER,
                text_color=ON_DANGER,
            )
        else:
            self.btn_stop.configure(
                fg_color=SURFACE_ALT,
                hover_color=SURFACE_ALT,
                text_color=DIM,
            )

        if online:
            self.firmware_label.configure(text=mode_label(self._mode), text_color=SUCCESS)
        else:
            self.firmware_label.configure(text="Firmware: —", text_color=MUTED)

        if detail:
            self.detail_label.configure(text=detail, text_color=MUTED)
        elif self._mode == FirmwareMode.LEGACY:
            self.detail_label.configure(
                text="Firmware legacy: borrar, editar y detener la sirena no están disponibles.",
                text_color=WARNING,
            )
        elif online:
            self.detail_label.configure(
                text="Hora y alarmas sincronizadas con el hardware.",
                text_color=MUTED,
            )
        else:
            self.detail_label.configure(
                text="La prueba y la parada de sirena requieren firmware v2.",
                text_color=DIM,
            )

    def set_scanning(self, scanning: bool) -> None:
        if self._state in ("connecting", "online"):
            return
        self.btn_refresh.configure(state="disabled" if scanning else "normal")
