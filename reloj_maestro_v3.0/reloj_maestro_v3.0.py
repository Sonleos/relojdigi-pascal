"""
╔══════════════════════════════════════════════════════════╗
║         RELOJ MAESTRO  —  Panel de Control  v2.0         ║
║       Control serial de alarmas sobre Arduino Uno        ║
╚══════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
import serial
from serial.tools import list_ports
import threading
import time
from datetime import datetime, timedelta
from tkinter import messagebox
import os
import sys

# ══════════════════════════════════════════════════════════
#  UTILIDADES
# ══════════════════════════════════════════════════════════

def resolver_ruta(ruta: str) -> str:
    """Ruta absoluta compatible con PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, ruta)

def bit_read(valor: int, bit: int) -> bool:
    return bool((valor >> bit) & 1)

# ══════════════════════════════════════════════════════════
#  PALETA DE COLORES
# ══════════════════════════════════════════════════════════

C = {
    "cyan"    : "#05DCF8",
    "cyan_dim": "#0A6E7A",
    "green"   : "#00E566",
    "red"     : "#E03030",
    "amber"   : "#FFAA00",
    "white"   : "#E0E0F0",
    "bg_root" : "#08080F",
    "bg_panel": "#0E0E1A",
    "bg_card" : "#13131F",
    "bg_input": "#0A0A16",
    "border"  : "#1C1C2E",
    "muted"   : "#444466",
    "accent1" : "#1F538D",
}

# ══════════════════════════════════════════════════════════
#  ESTADO DE LA APLICACIÓN
# ══════════════════════════════════════════════════════════

class AppState:
    MAX_ALARMAS = 7

    def __init__(self):
        self.arduino: serial.Serial | None = None
        self.escuchando: bool = False
        self.alarmas: list[dict] = []
        self.alerta_abierta: bool = False
        self.log_visible: bool = True
        self.ultima_sync: datetime | None = None

estado = AppState()

# ══════════════════════════════════════════════════════════
#  CONFIGURACIÓN VENTANA RAÍZ
# ══════════════════════════════════════════════════════════

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Reloj Maestro  —  Panel de Control  v2.0")
app.configure(fg_color=C["bg_root"])

try:
    app.iconbitmap(resolver_ruta("Reloj_Maestro.ico"))
except Exception:
    pass

W, H = 1180, 800
app.update_idletasks()
sx, sy = app.winfo_screenwidth(), app.winfo_screenheight()
app.geometry(f"{W}x{H}+{(sx - W) // 2}+{(sy - H) // 2}")
app.minsize(1060, 720)
app.resizable(True, True)

DIAS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
DIAS_LARGOS = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]

# ══════════════════════════════════════════════════════════
#  WIDGETS COMPARTIDOS — declarados aquí, construidos abajo
# ══════════════════════════════════════════════════════════
# (se declaran en el orden en que se necesitan globalmente)
lbl_reloj       = None
lbl_dia         = None
lbl_proxima     = None
lbl_conn_estado = None
combo_puertos   = None
combo_hora      = None
combo_min       = None
periodo_var     = None
combo_dur       = None
dias_vars       = []
scroll_alarmas  = None
lbl_counter     = None
txt_log         = None
lbl_status_bar  = None
lbl_sync_bar    = None
frame_right     = None
btn_toggle_log  = None

# ══════════════════════════════════════════════════════════
#  CONSTRUCCIÓN DE UI
# ══════════════════════════════════════════════════════════

def _kw_frame(**kw):
    return dict(fg_color=C["bg_panel"], corner_radius=12,
                border_width=1, border_color=C["border"], **kw)

def _build_top_bar():
    """Barra superior: reloj grande + panel de conexión."""
    global lbl_reloj, lbl_dia, lbl_proxima, lbl_conn_estado
    global combo_puertos, btn_toggle_log

    top = ctk.CTkFrame(app, **_kw_frame(height=195))
    top.pack(fill="x", padx=16, pady=(14, 8))
    top.pack_propagate(False)

    # ── Columna izquierda: Reloj ───────────────────────────
    col_reloj = ctk.CTkFrame(top, fg_color="transparent")
    col_reloj.pack(side="left", fill="both", expand=True, padx=(24, 12), pady=14)

    lbl_reloj = ctk.CTkLabel(col_reloj, text="--:--:-- --",
                            font=("Consolas", 64, "bold"), text_color=C["cyan"])
    lbl_reloj.pack(anchor="w")

    lbl_dia = ctk.CTkLabel(col_reloj, text="─── Desconectado ───",
                            font=("Consolas", 14), text_color=C["muted"])
    lbl_dia.pack(anchor="w", pady=(0, 4))

    row_sub = ctk.CTkFrame(col_reloj, fg_color="transparent")
    row_sub.pack(anchor="w", fill="x")

    lbl_proxima = ctk.CTkLabel(row_sub, text="Próxima alarma: —",
                                font=("Consolas", 12), text_color=C["amber"])
    lbl_proxima.pack(side="left")

    lbl_conn_estado = ctk.CTkLabel(row_sub, text="● DESCONECTADO",
                                    font=("Consolas", 12, "bold"), text_color=C["red"])
    lbl_conn_estado.pack(side="right", padx=(0, 4))

    # ── Separador vertical ─────────────────────────────────
    ctk.CTkFrame(top, fg_color=C["border"], width=1).pack(
        side="left", fill="y", pady=18)

    # ── Columna derecha: Conexión serial ───────────────────
    col_conn = ctk.CTkFrame(top, fg_color="transparent", width=430)
    col_conn.pack(side="right", fill="y", padx=(12, 20), pady=14)
    col_conn.pack_propagate(False)

    ctk.CTkLabel(col_conn, text="CONEXIÓN SERIAL  ·  Arduino Uno",
                font=("Consolas", 12, "bold"), text_color=C["cyan"]).pack(anchor="w")

    # Port selector
    row_p = ctk.CTkFrame(col_conn, fg_color="transparent")
    row_p.pack(fill="x", pady=(8, 0))
    ctk.CTkLabel(row_p, text="Puerto COM:", font=("Consolas", 11), width=90).pack(side="left")
    combo_puertos = ctk.CTkComboBox(row_p, values=["Buscando…"], width=260,
                                    font=("Consolas", 12), border_color=C["border"],
                                    fg_color=C["bg_input"])
    combo_puertos.pack(side="right", expand=True, fill="x")

    # Buttons 2x2 + toggle
    grid = ctk.CTkFrame(col_conn, fg_color="transparent")
    grid.pack(fill="both", expand=True, pady=(8, 0))

    _BKW = dict(font=("Consolas", 11, "bold"), height=32, corner_radius=8)

    ctk.CTkButton(grid, text="⚡  Conectar",
                fg_color="#0A4A0A", hover_color="#0D6B0D",
                    command=conectar, **_BKW).grid(row=0, column=0, padx=3, pady=3, sticky="nsew")

    ctk.CTkButton(grid, text="✖  Desconectar",
                fg_color="#4A0A0A", hover_color="#6B0D0D",
                    command=desconectar, **_BKW).grid(row=0, column=1, padx=3, pady=3, sticky="nsew")

    ctk.CTkButton(grid, text="🔄  Buscar puertos",
                fg_color=C["bg_input"], hover_color="#1C1C30",
                    command=lambda: buscar_puertos(forzar=True), **_BKW
                ).grid(row=1, column=0, padx=3, pady=3, sticky="nsew")

    ctk.CTkButton(grid, text="⏰  Sincronizar",
                fg_color=C["bg_input"], hover_color="#1C1C30",
                    command=sincronizar, **_BKW
                ).grid(row=1, column=1, padx=3, pady=3, sticky="nsew")

    btn_toggle_log = ctk.CTkButton(grid, text="👁  Ocultar log",
                                    fg_color="#111122", hover_color="#1C1C30",
                                    command=toggle_log, **_BKW)
    btn_toggle_log.grid(row=2, column=0, columnspan=2, padx=3, pady=3, sticky="nsew")

    grid.rowconfigure((0, 1, 2), weight=1)
    grid.columnconfigure((0, 1), weight=1)


def _build_body():
    """Panel central: formulario + lista de alarmas (izq) / log terminal (der)."""
    global combo_hora, combo_min, periodo_var, combo_dur, dias_vars
    global scroll_alarmas, lbl_counter, txt_log
    global lbl_status_bar, lbl_sync_bar, frame_right

    body = ctk.CTkFrame(app, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=16, pady=(0, 14))

    # ── Panel izquierdo ────────────────────────────────────
    left = ctk.CTkFrame(body, **_kw_frame())
    left.pack(side="left", fill="both", expand=True, padx=(0, 8))

    # Formulario nueva alarma
    form = ctk.CTkFrame(left, fg_color=C["bg_input"],
                        corner_radius=10, border_width=1, border_color=C["border"])
    form.pack(fill="x", padx=12, pady=(12, 6))

    ctk.CTkLabel(form, text="➕  CONFIGURAR NUEVA ALARMA",
                font=("Consolas", 12, "bold"), text_color=C["cyan"]
                ).pack(anchor="w", padx=16, pady=(10, 6))

    # Fila hora / minuto / AM-PM / duración
    row_t = ctk.CTkFrame(form, fg_color="transparent")
    row_t.pack(fill="x", padx=16, pady=(0, 4))

    OPT = dict(font=("Consolas", 13), dropdown_font=("Consolas", 13),
            width=78, height=34, fg_color=C["bg_card"],
            
            button_color=C["cyan_dim"], button_hover_color=C["cyan_dim"])

    for label, widget_factory in [
        ("Hora:",    lambda: (setattr_and_return("combo_hora",
                            ctk.CTkOptionMenu(row_t,
                                                values=[f"{i:02d}" for i in range(1, 13)],
                                                **OPT)))),
        ("Min:",     lambda: (setattr_and_return("combo_min",
                            ctk.CTkOptionMenu(row_t,
                                                values=[f"{i:02d}" for i in range(60)],
                                                **OPT)))),
    ]:
        ctk.CTkLabel(row_t, text=label, font=("Consolas", 12), width=45).pack(side="left", padx=(0, 2))
        widget_factory().pack(side="left", padx=3)

    # AM / PM
    periodo_var = ctk.StringVar(value="AM")
    rframe = ctk.CTkFrame(row_t, fg_color="transparent")
    rframe.pack(side="left", padx=14)
    for val in ("AM", "PM"):
        ctk.CTkRadioButton(rframe, text=val, variable=periodo_var, value=val,
                            font=("Consolas", 12)).pack(side="left", padx=5)

    # Duración
    ctk.CTkLabel(row_t, text="Sirena:", font=("Consolas", 12)).pack(side="left", padx=(14, 2))
    combo_dur = ctk.CTkOptionMenu(row_t, values=["5", "10", "15", "30", "60"], **OPT)
    combo_dur.set("10")
    combo_dur.pack(side="left", padx=3)

    ctk.CTkLabel(row_t, text="seg", font=("Consolas", 11), text_color=C["muted"]
                ).pack(side="left", padx=2)

    # Días de la semana + botón guardar
    row_d = ctk.CTkFrame(form, fg_color="transparent")
    row_d.pack(fill="x", padx=16, pady=(4, 12))

    dias_vars = [ctk.BooleanVar(value=True) for _ in DIAS]
    for i, nombre in enumerate(DIAS):
        ctk.CTkCheckBox(row_d, text=nombre, variable=dias_vars[i],
                        font=("Consolas", 11), width=62,
                        checkbox_width=17, checkbox_height=17,
                        checkmark_color=C["cyan"],
                        fg_color=C["cyan_dim"]).pack(side="left", padx=2)

    ctk.CTkButton(row_d, text="💾  Guardar Alarma",
                fg_color=C["accent1"], hover_color="#163B6A",
                font=("Consolas", 12, "bold"), width=180, height=34, corner_radius=8,
                command=agregar_alarma).pack(side="right", padx=(10, 0))

    # Encabezado lista de alarmas
    hdr = ctk.CTkFrame(left, fg_color="transparent")
    hdr.pack(fill="x", padx=12, pady=(6, 2))
    ctk.CTkLabel(hdr, text="ALARMAS PROGRAMADAS",
                font=("Consolas", 12, "bold"), text_color=C["cyan"]).pack(side="left", padx=4)
    lbl_counter = ctk.CTkLabel(hdr, text="0 / 7",
                                font=("Consolas", 11), text_color=C["muted"])
    lbl_counter.pack(side="right", padx=8)

    # Lista scrollable
    scroll_alarmas = ctk.CTkScrollableFrame(left, fg_color="#07070F",
                                            corner_radius=10,
                                            border_width=1, border_color=C["border"])
    scroll_alarmas.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ── Panel derecho: Log ─────────────────────────────────
    frame_right = ctk.CTkFrame(body, **_kw_frame(width=380))
    frame_right.pack(side="right", fill="both", padx=(8, 0))
    frame_right.pack_propagate(False)

    hdr_log = ctk.CTkFrame(frame_right, fg_color="transparent")
    hdr_log.pack(fill="x", padx=12, pady=(12, 4))
    ctk.CTkLabel(hdr_log, text="LOG  /  TERMINAL",
                font=("Consolas", 12, "bold"), text_color=C["cyan"]).pack(side="left")
    ctk.CTkButton(hdr_log, text="🗑  Limpiar", width=80, height=26,
                fg_color=C["bg_input"], hover_color="#1C1C30",
                font=("Consolas", 10), corner_radius=6,
                command=limpiar_log).pack(side="right")

    txt_log = ctk.CTkTextbox(frame_right, fg_color="#040408",
                            text_color=C["cyan"],
                            font=("Consolas", 11),
                            border_width=1, border_color=C["border"],
                            wrap="word")
    txt_log.pack(fill="both", expand=True, padx=12, pady=(0, 6))
    txt_log.configure(state="disabled")

    # Status bar dentro del panel log
    bar = ctk.CTkFrame(frame_right, fg_color=C["bg_input"],
                        corner_radius=6, border_width=1, border_color=C["border"], height=26)
    bar.pack(fill="x", padx=12, pady=(0, 12))
    bar.pack_propagate(False)

    lbl_status_bar = ctk.CTkLabel(bar, text="Sistema listo",
                                font=("Consolas", 10), text_color="#555577")
    lbl_status_bar.pack(side="left", padx=8, pady=3)

    lbl_sync_bar = ctk.CTkLabel(bar, text="Sync: —",
                                font=("Consolas", 10), text_color="#555577")
    lbl_sync_bar.pack(side="right", padx=8, pady=3)


def setattr_and_return(name, widget):
    """Helper para asignar widgets globales en expresiones lambda."""
    globals()[name] = widget
    if name == "combo_hora":
        widget.set("07")
    elif name == "combo_min":
        widget.set("30")
    return widget


# ══════════════════════════════════════════════════════════
#  LOG
# ══════════════════════════════════════════════════════════

PREFIJOS = {
    "TX"  : "➔  ",
    "RX"  : "←  ",
    "OK"  : "✓  ",
    "ERR" : "✗  ",
    "WARN": "⚠  ",
}

def registrar_log(mensaje: str, nivel: str = "INFO"):
    if txt_log is None:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    prefijo = PREFIJOS.get(nivel, "   ")
    txt_log.configure(state="normal")
    txt_log.insert("end", f"[{ts}] {prefijo}{mensaje}\n")
    txt_log.see("end")
    txt_log.configure(state="disabled")
    if lbl_status_bar:
        lbl_status_bar.configure(text=mensaje[:52])

def limpiar_log():
    if txt_log is None:
        return
    txt_log.configure(state="normal")
    txt_log.delete("1.0", "end")
    txt_log.configure(state="disabled")

def toggle_log():
    global frame_right
    if estado.log_visible:
        frame_right.pack_forget()
        btn_toggle_log.configure(text="👁  Mostrar log")
        estado.log_visible = False
    else:
        frame_right.pack(side="right", fill="both", padx=(8, 0))
        frame_right.pack_propagate(False)
        btn_toggle_log.configure(text="👁  Ocultar log")
        estado.log_visible = True

# ══════════════════════════════════════════════════════════
#  LISTA VISUAL DE ALARMAS
# ══════════════════════════════════════════════════════════

def actualizar_lista_visual():
    for w in scroll_alarmas.winfo_children():
        w.destroy()

    total = len(estado.alarmas)
    lbl_counter.configure(text=f"{total} / {AppState.MAX_ALARMAS}")
    _actualizar_proxima()

    if total == 0:
        ctk.CTkLabel(scroll_alarmas,
                     text="Sin alarmas configuradas.\nAgrega una usando el formulario.",
                     font=("Consolas", 13), text_color=C["muted"],
                     justify="center").pack(pady=50)
        return

    alarmas_ord = sorted(estado.alarmas,
                         key=lambda a: (0 if a["periodo"] == "AM" else 1,
                                        int(a["hora"]) % 12,
                                        int(a["min"])))
    for al in alarmas_ord:
        _tarjeta_alarma(al)


def _tarjeta_alarma(al: dict):
    activa = al["activa"]
    color_acento = C["cyan"] if activa else C["muted"]

    card = ctk.CTkFrame(scroll_alarmas, fg_color=C["bg_card"],
                         corner_radius=10, border_width=1,
                         border_color=C["border"] if activa else "#0F0F1A",
                         height=72)
    card.pack(fill="x", pady=4, padx=4)
    card.pack_propagate(False)

    # Barra de acento izquierda
    ctk.CTkFrame(card, fg_color=color_acento, width=4,
                  corner_radius=2).pack(side="left", fill="y", padx=(6, 0), pady=10)

    # Icono
    ctk.CTkLabel(card, text="⏰",
                 font=("Segoe UI Emoji", 20)).pack(side="left", padx=(12, 6))

    # Hora
    text_hora = f"{int(al['hora']):02d}:{int(al['min']):02d}"
    ctk.CTkLabel(card, text=text_hora,
                 font=("Consolas", 30, "bold"),
                 text_color=C["white"] if activa else C["muted"]
                 ).pack(side="left")

    ctk.CTkLabel(card, text=al["periodo"],
                 font=("Consolas", 12), text_color="#666688"
                 ).pack(side="left", pady=(10, 0), padx=(4, 10))

    # Badge duración
    ctk.CTkLabel(card,
                 text=f"{al['duracion']}s",
                 font=("Consolas", 10), text_color="#555577",
                 fg_color="#0C0C18", corner_radius=4,
                 width=34, height=18).pack(side="left", padx=4)

    # Días
    f_dias = ctk.CTkFrame(card, fg_color="transparent")
    f_dias.pack(side="left", expand=True, padx=10)
    for i, d in enumerate(DIAS):
        on = bit_read(al["dias"], i)
        ctk.CTkLabel(f_dias, text=d,
                     font=("Consolas", 10, "bold" if on else "normal"),
                     text_color=C["cyan"] if on else "#2A2A40",
                     width=30).pack(side="left", padx=2)

    # Controles
    ctrl = ctk.CTkFrame(card, fg_color="transparent")
    ctrl.pack(side="right", padx=12)

    sw_var = ctk.BooleanVar(value=activa)
    ctk.CTkSwitch(ctrl, text="", variable=sw_var, width=44,
                   progress_color=C["cyan_dim"],
                   command=lambda aid=al["id"], v=sw_var: _toggle_alarma(aid, v)
                   ).pack()

    ctk.CTkButton(ctrl, text="✕", width=30, height=22, corner_radius=6,
                   fg_color="#3A1010", hover_color="#5A1818",
                   font=("Consolas", 11, "bold"),
                   command=lambda aid=al["id"]: _borrar_alarma(aid)
                   ).pack(pady=(4, 0))


def _actualizar_proxima():
    """Calcula y muestra cuánto falta para la próxima alarma."""
    if not estado.alarmas:
        if lbl_proxima:
            lbl_proxima.configure(text="Próxima alarma: —")
        return

    ahora = datetime.now()
    candidatas = []

    for al in estado.alarmas:
        if not al["activa"]:
            continue
        h24 = int(al["hora"]) % 12 + (12 if al["periodo"] == "PM" else 0)
        ts = ahora.replace(hour=h24, minute=int(al["min"]), second=0, microsecond=0)
        delta = (ts - ahora).total_seconds()
        if delta <= 0:
            delta += 86400
        candidatas.append((delta, al))

    if not candidatas:
        lbl_proxima.configure(text="Próxima alarma: — (todas inactivas)")
        return

    candidatas.sort(key=lambda x: x[0])
    delta, al = candidatas[0]
    hh = int(delta // 3600)
    mm = int((delta % 3600) // 60)
    tiempo = f"{hh}h {mm}m" if hh > 0 else f"{mm}m"
    lbl_proxima.configure(
        text=f"Próxima: {int(al['hora']):02d}:{int(al['min']):02d} {al['periodo']}  (en {tiempo})"
    )


# ══════════════════════════════════════════════════════════
#  CRUD ALARMAS
# ══════════════════════════════════════════════════════════

def agregar_alarma():
    if len(estado.alarmas) >= AppState.MAX_ALARMAS:
        messagebox.showerror(
            "Límite alcanzado",
            f"Máximo {AppState.MAX_ALARMAS} alarmas.\n"
            "Elimina una existente para agregar otra."
        )
        return

    mascara = sum(1 << i for i, v in enumerate(dias_vars) if v.get())
    if mascara == 0:
        messagebox.showwarning("Sin días", "Selecciona al menos un día de la semana.")
        return

    hora     = combo_hora.get()
    minuto   = combo_min.get()
    periodo  = periodo_var.get()
    duracion = combo_dur.get()

    ids_usados = {a["id"] for a in estado.alarmas}
    id_libre = next(r for r in range(AppState.MAX_ALARMAS) if r not in ids_usados)

    nueva = {
        "id": id_libre, "hora": hora, "min": minuto,
        "periodo": periodo, "duracion": duracion,
        "dias": mascara, "activa": True
    }
    estado.alarmas.append(nueva)
    actualizar_lista_visual()

    letra_p = "P" if periodo == "PM" else "A"
    cmd = f"A:{id_libre}:{int(hora)}:{int(minuto)}:{letra_p}:{duracion}:{mascara}"

    if estado.arduino and estado.arduino.is_open:
        _enviar(cmd, "OK")
        registrar_log(f"Alarma guardada en ranura {id_libre + 1} → {hora}:{minuto} {periodo}", "OK")
    else:
        registrar_log(
            f"Alarma guardada localmente (ranura {id_libre + 1}) — Arduino desconectado", "WARN")
        messagebox.showwarning(
            "Guardado local",
            "Alarma guardada en la interfaz.\n"
            "Conéctate al Arduino y presiona Sincronizar para cargarla."
        )


def _borrar_alarma(id_alarma: int):
    _enviar(f"A:OFF:{id_alarma}")
    estado.alarmas = [a for a in estado.alarmas if a["id"] != id_alarma]
    actualizar_lista_visual()
    registrar_log(f"Alarma ID {id_alarma} eliminada", "WARN")


def _toggle_alarma(id_alarma: int, var: ctk.BooleanVar):
    nuevo = var.get()
    for al in estado.alarmas:
        if al["id"] == id_alarma:
            al["activa"] = nuevo
            cmd = f"A:ON:{id_alarma}" if nuevo else f"A:OFF:{id_alarma}"
            _enviar(cmd)
            registrar_log(f"Alarma {id_alarma + 1} → {'activada' if nuevo else 'desactivada'}")
            actualizar_lista_visual()
            break


# ══════════════════════════════════════════════════════════
#  SERIAL
# ══════════════════════════════════════════════════════════

def buscar_puertos(forzar: bool = False):
    if estado.arduino and not forzar:
        return
    dispositivos = [p.device for p in list_ports.comports()]
    opciones = dispositivos if dispositivos else ["Sin puertos COM"]

    if combo_puertos.cget("values") != opciones:
        combo_puertos.configure(values=opciones)
        if combo_puertos.get() not in opciones:
            combo_puertos.set(opciones[0])

    if forzar:
        if dispositivos:
            messagebox.showinfo("Puertos detectados",
                                "Puertos COM disponibles:\n\n" +
                                "\n".join(f"  •  {p}" for p in dispositivos))
        else:
            messagebox.showwarning("Sin puertos", "No se detectó ningún puerto COM.")

    if not estado.arduino:
        app.after(2500, buscar_puertos)


def _hilo_conectar():
    puerto = combo_puertos.get()
    if "Sin" in puerto or not puerto:
        app.after(0, lambda: lbl_conn_estado.configure(
            text="● Puerto no válido", text_color=C["amber"]))
        return

    app.after(0, lambda: lbl_conn_estado.configure(
        text="● Conectando…", text_color=C["amber"]))

    try:
        conn = serial.Serial(puerto, 115200, timeout=1)
        time.sleep(1.0)
        estado.arduino = conn
        estado.escuchando = True
        app.after(0, lambda: lbl_conn_estado.configure(
            text=f"● {puerto}  ONLINE", text_color=C["green"]))
        threading.Thread(target=_hilo_lector, daemon=True).start()
        registrar_log(f"Conectado a {puerto} @ 115200 bps", "OK")
        app.after(0, sincronizar)
    except Exception as exc:
        app.after(0, lambda: lbl_conn_estado.configure(
            text="● Error al conectar", text_color=C["red"]))
        registrar_log(f"Fallo de conexión: {exc}", "ERR")


def conectar():
    if estado.arduino is None:
        threading.Thread(target=_hilo_conectar, daemon=True).start()


def desconectar():
    estado.escuchando = False
    if estado.arduino:
        try:
            estado.arduino.close()
        except Exception:
            pass
        estado.arduino = None
    lbl_conn_estado.configure(text="● DESCONECTADO", text_color=C["red"])
    lbl_reloj.configure(text="--:--:-- --")
    lbl_dia.configure(text="─── Desconectado ───")
    registrar_log("Puerto serial cerrado", "WARN")


def _enviar(comando: str, nivel: str = "TX"):
    if not estado.arduino:
        return
    try:
        estado.arduino.write((comando + "\n").encode())
        registrar_log(f"{comando}", nivel if nivel != "INFO" else "TX")
    except Exception:
        app.after(0, desconectar)


def sincronizar():
    ahora = datetime.now()
    h12   = ahora.hour % 12 or 12
    ampm  = "P" if ahora.hour >= 12 else "A"
    # weekday(): 0=lun…6=dom → Arduino: 1=dom…7=sáb
    dia   = (ahora.weekday() + 2) % 7 or 7
    cmd   = f"S:{h12:02d}:{ahora.minute:02d}:{ahora.second:02d}:{ampm}:{dia}"
    _enviar(cmd)
    estado.ultima_sync = ahora
    if lbl_sync_bar:
        lbl_sync_bar.configure(text=f"Sync: {ahora.strftime('%H:%M:%S')}")


# ══════════════════════════════════════════════════════════
#  HILO LECTOR SERIAL
# ══════════════════════════════════════════════════════════

def _hilo_lector():
    while estado.escuchando and estado.arduino:
        try:
            if estado.arduino.in_waiting > 0:
                linea = estado.arduino.readline().decode("utf-8", errors="ignore").strip()
                if not linea:
                    continue
                if linea.startswith("INFO:"):
                    app.after(0, _procesar_info, linea)
                elif "ALARMA_ACTIVA" in linea or "ALARMA_ENCENDIDA" in linea:
                    app.after(0, lambda: registrar_log(
                        "🚨 Alarma en curso en el Arduino", "WARN"))
                    app.after(0, lambda: _mostrar_alerta(origen_local=False))
                else:
                    app.after(0, lambda l=linea: registrar_log(f"← {l}", "RX"))
        except Exception:
            app.after(0, desconectar)
            break
        time.sleep(0.01)


def _procesar_info(linea: str):
    try:
        p = linea.split(":")
        if len(p) < 6:
            return

        h, m, s = int(p[1]), int(p[2]), int(p[3])
        per = "PM" if p[4] == "P" else "AM"
        lbl_reloj.configure(text=f"{h:02d}:{m:02d}:{s:02d} {per}")

        dia_idx = int(p[5]) - 1
        if 0 <= dia_idx < 7:
            lbl_dia.configure(text=DIAS_LARGOS[dia_idx])

        # Carga de alarmas iniciales desde Arduino
        if len(p) >= 48 and not estado.alarmas:
            idx = 6
            for i in range(7):
                if p[idx + 5] == "1":
                    estado.alarmas.append({
                        "id"     : i,
                        "hora"   : f"{int(p[idx]):02d}",
                        "min"    : f"{int(p[idx + 1]):02d}",
                        "periodo": "PM" if p[idx + 2] == "P" else "AM",
                        "duracion": p[idx + 3],
                        "dias"   : int(p[idx + 4]),
                        "activa" : True,
                    })
                idx += 6
            actualizar_lista_visual()
            registrar_log(
                f"{len(estado.alarmas)} alarma(s) cargadas desde el Arduino", "OK")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════
#  MONITOR LOCAL + ALERTA EMERGENTE
# ══════════════════════════════════════════════════════════

def _monitor_local():
    ahora   = datetime.now()
    if ahora.second == 0:
        h_str   = ahora.strftime("%I")   # "07"
        m_str   = ahora.strftime("%M")
        p_str   = ahora.strftime("%p")   # "AM" / "PM"
        dia_idx = (ahora.weekday() + 1) % 7

        for al in estado.alarmas:
            if (al["activa"]
                    and bit_read(al["dias"], dia_idx)
                    and al["hora"] == h_str
                    and al["min"]  == m_str
                    and al["periodo"] == p_str
                    and not estado.alerta_abierta):
                registrar_log(f"⏰ Alarma local disparada: {h_str}:{m_str} {p_str}", "WARN")
                _mostrar_alerta(origen_local=True)

    app.after(1000, _monitor_local)


def _mostrar_alerta(origen_local: bool = False):
    if estado.alerta_abierta:
        return
    estado.alerta_abierta = True

    popup = ctk.CTkToplevel(app)
    popup.title("¡ALARMA!")
    popup.geometry("500x260")
    popup.resizable(False, False)
    popup.attributes("-topmost", True)
    popup.grab_set()

    cx = app.winfo_x() + app.winfo_width()  // 2 - 250
    cy = app.winfo_y() + app.winfo_height() // 2 - 130
    popup.geometry(f"500x260+{cx}+{cy}")
    popup.configure(fg_color=C["bg_root"])

    border = ctk.CTkFrame(popup, fg_color=C["bg_panel"],
                           border_width=2, border_color=C["cyan"], corner_radius=14)
    border.pack(fill="both", expand=True, padx=8, pady=8)

    ctk.CTkLabel(border, text="🔔  ALARMA ACTIVADA",
                 font=("Consolas", 28, "bold"), text_color=C["cyan"]
                 ).pack(pady=(24, 4))

    ts = datetime.now().strftime("%H:%M:%S")
    ctk.CTkLabel(border, text=ts,
                 font=("Consolas", 18, "bold"), text_color=C["amber"]
                 ).pack(pady=2)

    detalle = ("Alerta disparada localmente.\nVerifica la conexión con el Arduino."
               if origen_local else
               "El Arduino está ejecutando la alarma\nen el timbre físico.")
    ctk.CTkLabel(border, text=detalle,
                 font=("Consolas", 12), text_color="#AAAACC", justify="center"
                 ).pack(pady=(6, 0))

    def cerrar():
        estado.alerta_abierta = False
        popup.destroy()

    popup.protocol("WM_DELETE_WINDOW", cerrar)

    ctk.CTkButton(border, text="   Entendido   ",
                   fg_color="#0A4A0A", hover_color="#0D6B0D",
                   font=("Consolas", 14, "bold"), height=40, corner_radius=10,
                   command=cerrar).pack(pady=(14, 22))


# ══════════════════════════════════════════════════════════
#  RELOJ LOCAL (cuando no hay Arduino)
# ══════════════════════════════════════════════════════════

def _tick_local():
    if not estado.arduino:
        ahora = datetime.now()
        h12   = ahora.hour % 12 or 12
        per   = "PM" if ahora.hour >= 12 else "AM"
        lbl_reloj.configure(text=f"{h12:02d}:{ahora.minute:02d}:{ahora.second:02d} {per}")
        lbl_dia.configure(text=DIAS_LARGOS[ahora.weekday()])
    app.after(1000, _tick_local)


# ══════════════════════════════════════════════════════════
#  ARRANQUE
# ══════════════════════════════════════════════════════════

_build_top_bar()
_build_body()

buscar_puertos()
actualizar_lista_visual()
_monitor_local()
_tick_local()
registrar_log("Reloj Maestro v2.0 iniciado", "OK")

app.mainloop()