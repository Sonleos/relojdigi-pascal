import customtkinter as ctk
import serial
from serial.tools import list_ports
import threading
import time
import json
import os
import sys
from datetime import datetime
from tkinter import messagebox

# ========================================================
# RUTA DE RECURSOS (para PyInstaller)
# ========================================================
def resolver_ruta(ruta_relativa):
    """Determina la ruta absoluta para recursos, necesaria para PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, ruta_relativa)
    return os.path.join(os.path.abspath("."), ruta_relativa)

ARCHIVO_ALARMAS = "alarmas.json"

# ==========================================
# ESTADO
# ==========================================
class AppState:
    def __init__(self):
        self.arduino = None
        self.ultima_sync = None
        self.escuchando = False
        self.conectando = False   
        self.alarmas = []
        self.ultimo_segundo_local = -1

estado = AppState()

# ==========================================
# PERSISTENCIA DE ALARMAS (JSON)
# ==========================================
def guardar_alarmas_json():
    """Guarda la lista de alarmas en disco para persistir entre sesiones."""
    try:
        with open(ARCHIVO_ALARMAS, "w", encoding="utf-8") as f:
            json.dump(estado.alarmas, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] No se pudieron guardar las alarmas: {e}")

def cargar_alarmas_json():
    """Carga las alarmas guardadas al iniciar la aplicación."""
    if not os.path.exists(ARCHIVO_ALARMAS):
        return
    try:
        with open(ARCHIVO_ALARMAS, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, list):
            estado.alarmas = datos
            print(f"[INFO] {len(estado.alarmas)} alarma(s) cargadas desde disco.")
    except Exception as e:
        print(f"[WARN] No se pudieron cargar las alarmas: {e}")

# ========================================================
# ADAPTACIÓN MULTIPLATAFORMA: DETECCIÓN DE FUENTES NATIVAS
# ========================================================
if sys.platform == "darwin":       # para macOS
    FUENTE_MONO = "Menlo"
elif sys.platform == "win32":     #  para Windows
    FUENTE_MONO = "Consolas"
else:                             # Linux (para Ubuntu, Fedora, etc.)
    FUENTE_MONO = "DejaVu Sans Mono"

# ==========================================
# CONFIGURACIÓN DE VENTANA RESPONSIVA
# ==========================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

app = ctk.CTk()
app.title("Terminal de Control - Reloj Maestro")

try:
    app.iconbitmap(resolver_ruta('Reloj_Maestro.ico'))
except Exception as e:
    print(f"[INFO] Icono no encontrado: {e}")

app.update_idletasks()
window_width, window_height = 1100, 780
x = (app.winfo_screenwidth() - window_width) // 2
y = (app.winfo_screenheight() - window_height) // 2
app.geometry(f"{window_width}x{window_height}+{x}+{y}")

app.resizable(True, True) 
app.minsize(1100, 780)

# ==========================================
# BLOQUE SUPERIOR: RELOJ Y BOTONES
# ==========================================
frame_superior = ctk.CTkFrame(app, fg_color="transparent")
frame_superior.pack(side="top", fill="x", padx=20, pady=(15, 5))

# Columna Izquierda: Reloj e indicador de puerto
panel_reloj = ctk.CTkFrame(frame_superior, fg_color="transparent")
panel_reloj.pack(side="left", fill="both", expand=True, padx=(0, 15))

frameDisplay = ctk.CTkFrame(panel_reloj, fg_color="#050505", border_width=4, border_color="#00FF66")
frameDisplay.pack(fill="x", pady=(0, 8))

relojLabel = ctk.CTkLabel(frameDisplay, text="--:--:-- --", font=(FUENTE_MONO, 58, "bold"), text_color="#00FF66")
relojLabel.pack(pady=(15, 2), padx=(10, 0))

diaLabel = ctk.CTkLabel(frameDisplay, text="---", font=(FUENTE_MONO, 18, "bold"), text_color="#88FF88")
diaLabel.pack(pady=2, padx=(10, 0))

# Etiqueta para mostrar la cuenta regresiva de la próxima alarma
proximaAlarmaLabel = ctk.CTkLabel(frameDisplay, text="🔔 Calculando próxima alarma...", font=(FUENTE_MONO, 13, "italic"), text_color="#88FF88")
proximaAlarmaLabel.pack(pady=(2, 6), padx=(10, 0))

estadoConexion = ctk.CTkLabel(frameDisplay, text="● DESCONECTADO", font=(FUENTE_MONO, 14, "bold"), text_color="#A12424")
estadoConexion.pack(pady=(2, 12), padx=(10, 0))

frameConexion = ctk.CTkFrame(panel_reloj)
frameConexion.pack(fill="x")
ctk.CTkLabel(frameConexion, text="Puerto:", font=(FUENTE_MONO, 13, "bold")).pack(side="left", padx=15, pady=8)
comboPuertos = ctk.CTkComboBox(frameConexion, values=["Buscando..."], width=180)
comboPuertos.pack(side="left", padx=5, pady=8)

# Columna Derecha: Matriz de botones
panel_botones = ctk.CTkFrame(frame_superior, fg_color="transparent")
panel_botones.pack(side="right", fill="both", padx=(15, 0))

fila1 = ctk.CTkFrame(panel_botones, fg_color="transparent")
fila1.pack(fill="x", pady=(22, 0))
ctk.CTkButton(fila1, text="🔄 Buscar Puertos", command=lambda: buscar_puertos(), width=170, height=45).pack(side="left", padx=8)
ctk.CTkButton(fila1, text="🔌 Conectar", command=lambda: conectar(), fg_color="#00AA00", hover_color="#007700", width=170, height=45).pack(side="left", padx=8)

fila2 = ctk.CTkFrame(panel_botones, fg_color="transparent")
fila2.pack(fill="x", pady=(18, 0))
ctk.CTkButton(fila2, text="⏰ Sincronizar", command=lambda: sincronizar_automatico(), width=170, height=45).pack(side="left", padx=8)
ctk.CTkButton(fila2, text="⏻ Desconectar", command=lambda: desconectar(), fg_color="#A12424", hover_color="#7A1B1B", width=170, height=45).pack(side="left", padx=8)

fila3 = ctk.CTkFrame(panel_botones, fg_color="transparent")
fila3.pack(fill="x", pady=(18, 0))
ctk.CTkButton(fila3, text="📤   Reenviar Alarmas al Arduino", command=lambda: reenviar_todas_alarmas(),
              fg_color="#1f538d", hover_color="#153B64", width=360, height=35).pack(side="left", padx=8)

# ==========================================
# BLOQUE CENTRAL: CONFIGURACIÓN DE ALARMAS
# ==========================================
frameAlarma = ctk.CTkFrame(app)
frameAlarma.pack(fill="x", padx=20, pady=(5, 10))

ctk.CTkLabel(frameAlarma, text="CONFIGURACIÓN DE ALARMAS", font=(FUENTE_MONO, 14, "bold"), text_color="#00FF66").pack(pady=(10, 5), padx=15, anchor="w")

frameConfigLineal = ctk.CTkFrame(frameAlarma, fg_color="transparent")
frameConfigLineal.pack(fill="x", padx=15, pady=5)

ctk.CTkLabel(frameConfigLineal, text="Hora:").pack(side="left", padx=4)
comboHora = ctk.CTkOptionMenu(frameConfigLineal, values=[f"{i:02d}" for i in range(1, 13)], width=85)
comboHora.set("07")
comboHora.pack(side="left", padx=5)

ctk.CTkLabel(frameConfigLineal, text="Minuto:").pack(side="left", padx=4)
comboMinuto = ctk.CTkOptionMenu(frameConfigLineal, values=[f"{i:02d}" for i in range(60)], width=85)
comboMinuto.set("30")
comboMinuto.pack(side="left", padx=5)

periodoVar = ctk.StringVar(value="AM")
ctk.CTkRadioButton(frameConfigLineal, text="AM", variable=periodoVar, value="AM", width=65).pack(side="left", padx=15)
ctk.CTkRadioButton(frameConfigLineal, text="PM", variable=periodoVar, value="PM", width=65).pack(side="left", padx=15)

ctk.CTkLabel(frameConfigLineal, text="Duración Sirena (seg):").pack(side="left", padx=15)
comboDuracion = ctk.CTkOptionMenu(frameConfigLineal, values=["5", "10", "15", "30", "60"], width=85)
comboDuracion.set("10")
comboDuracion.pack(side="left", padx=5)

frameDiasYGuardar = ctk.CTkFrame(frameAlarma, fg_color="transparent")
frameDiasYGuardar.pack(fill="x", padx=15, pady=(5, 15))

dias_nombres = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
dias_vars = [ctk.BooleanVar(value=True) for _ in range(7)]

frameCheckboxes = ctk.CTkFrame(frameDiasYGuardar, fg_color="transparent")
frameCheckboxes.pack(side="left")

for i, nombre in enumerate(dias_nombres):
    ctk.CTkCheckBox(frameCheckboxes, text=nombre, variable=dias_vars[i], width=70, font=(FUENTE_MONO, 12)).pack(side="left", padx=4)

ctk.CTkButton(frameDiasYGuardar, text="💾 Guardar Alarma",
              command=lambda: agregar_nueva_alarma_formulario(),
              fg_color="#1f538d", hover_color="#153B64", width=180, height=35).pack(side="right", padx=(0, 5))

# ==========================================
# BLOQUE INFERIOR: LISTA DE ALARMAS
# ==========================================
frame_lista_completa = ctk.CTkFrame(app, fg_color="transparent")
frame_lista_completa.pack(side="top", fill="both", expand=True, padx=20, pady=(5, 5))

frame_header_lista = ctk.CTkFrame(frame_lista_completa, fg_color="transparent")
frame_header_lista.pack(fill="x", pady=(0, 5))

ctk.CTkLabel(frame_header_lista, text="MIS ALARMAS PROGRAMADAS",
             font=(FUENTE_MONO, 14, "bold"), text_color="#00FF66").pack(side="left")

lbl_contador = ctk.CTkLabel(frame_header_lista, text="(0 alarmas)",
                            font=(FUENTE_MONO, 12), text_color="gray")
lbl_contador.pack(side="left", padx=10)

ctk.CTkButton(frame_header_lista, text="🗑️ Borrar Todas",
              fg_color="#A12424", hover_color="#7A1B1B", width=140, height=28,
              command=lambda: borrar_todas_alarmas()).pack(side="right")

scroll_alarmas = ctk.CTkScrollableFrame(frame_lista_completa, fg_color="#101010",
                                        border_width=1, border_color="#333333")
scroll_alarmas.pack(fill="both", expand=True)

# BLOQUE DE CONSOLA DE DIAGNÓSTICO SERIAL
frame_consola = ctk.CTkFrame(app, fg_color="transparent")
frame_consola.pack(side="bottom", fill="x", padx=20, pady=(5, 15))

ctk.CTkLabel(frame_consola, text="CONSOLA DE TELEMETRÍA SERIAL (DIAGNÓSTICO)", font=(FUENTE_MONO, 11, "bold"), text_color="gray").pack(anchor="w")
consola_serial = ctk.CTkTextbox(frame_consola, height=80, fg_color="#050505", text_color="#00FF66", font=(FUENTE_MONO, 11))
consola_serial.pack(fill="x", pady=(2, 0))
consola_serial.insert("0.0", "--- Monitor Serial Inicializado. Esperando Conexión... ---\n")
consola_serial.configure(state="disabled")

# ==========================================
# LÓGICA DE ACTUALIZACIÓN DE LA LISTA
# ==========================================
def escribir_consola(texto):
    """Introduce líneas de registros de datos de forma segura en la caja de texto."""
    consola_serial.configure(state="normal")
    consola_serial.insert("end", f"{texto}\n")
    consola_serial.see("end")
    consola_serial.configure(state="disabled")

def actualizar_lista_visual():
    for w in scroll_alarmas.winfo_children():
        w.destroy()

    total = len(estado.alarmas)
    lbl_contador.configure(text=f"({total} alarma{'s' if total != 1 else ''})")

    if not estado.alarmas:
        ctk.CTkLabel(scroll_alarmas, text="No hay alarmas configuradas en el sistema.",
                     font=(FUENTE_MONO, 14), text_color="gray").pack(pady=30)
        actualizar_proxima_alarma_ui()
        return

    for al in estado.alarmas:
        fila = ctk.CTkFrame(scroll_alarmas, fg_color="#1a1a1a", height=65)
        fila.pack(fill="x", pady=4, padx=5)
        fila.pack_propagate(False)

        ctk.CTkLabel(fila, text="⏰", font=(FUENTE_MONO, 22)).pack(side="left", padx=(20, 5))
        ctk.CTkLabel(fila, text=f"{al['hora']}:{al['min']}",
                     font=(FUENTE_MONO, 26, "bold"), text_color="#ffffff").pack(side="left", padx=5)
        ctk.CTkLabel(fila, text=al['periodo'],
                     font=(FUENTE_MONO, 14, "bold"), text_color="#888888").pack(side="left", padx=(2, 20), pady=(6, 0))
        ctk.CTkLabel(fila, text=f"• Duración: {al['duracion']}s",
                     font=(FUENTE_MONO, 12), text_color="gray").pack(side="left", padx=10)

        frame_dias_lista = ctk.CTkFrame(fila, fg_color="transparent")
        frame_dias_lista.pack(side="left", expand=True, anchor="center")

        for i, letra in enumerate(["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]):
            activo = bitRead(al["dias"], i)
            ctk.CTkLabel(frame_dias_lista, text=letra,
                         text_color="#00FF66" if activo else "#444444",
                         font=(FUENTE_MONO, 13, "bold") if activo else (FUENTE_MONO, 13)
                         ).pack(side="left", padx=10)

        ctk.CTkButton(fila, text="🗑️", fg_color="#A12424", hover_color="#7A1B1B",
                      width=40, height=35,
                      command=lambda a_id=al['id']: boton_eliminar_alarma(a_id)).pack(side="right", padx=20)

        switch_var = ctk.BooleanVar(value=al["activa"])
        ctk.CTkSwitch(fila, text="", variable=switch_var, width=45,
                      command=lambda a_id=al['id'], var=switch_var: switch_activar_alarma(a_id, var)
                      ).pack(side="right", padx=10)
    
    actualizar_proxima_alarma_ui()

def bitRead(valor, bit):
    return (valor >> bit) & 0x01

def boton_eliminar_alarma(id_alarma):
    estado.alarmas = [a for a in estado.alarmas if a["id"] != id_alarma]
    if estado.arduino and estado.arduino.is_open:
        enviar(f"D:{id_alarma}")
    guardar_alarmas_json()
    actualizar_lista_visual()

def borrar_todas_alarmas():
    if not estado.alarmas:
        return
    if messagebox.askyesno("Confirmar", "¿Eliminar TODAS las alarmas? Esta acción no se puede deshacer."):
        estado.alarmas.clear()
        if estado.arduino and estado.arduino.is_open:
            enviar("CLEARALL")
        guardar_alarmas_json()
        actualizar_lista_visual()

def switch_activar_alarma(id_alarma, var_estado):
    nuevo_estado = var_estado.get()
    for al in estado.alarmas:
        if al["id"] == id_alarma:
            al["activa"] = nuevo_estado
            break
    if estado.arduino and estado.arduino.is_open:
        enviar(f"T:{id_alarma}:{'1' if nuevo_estado else '0'}")
    guardar_alarmas_json()
    actualizar_proxima_alarma_ui()

# ==========================================
# GESTIÓN SERIAL Y CONEXIÓN
# ==========================================
def buscar_puertos():
    puertos = [p.device for p in list_ports.comports()] or ["No se encontraron puertos"]
    comboPuertos.configure(values=puertos)
    comboPuertos.set(puertos[0])

def _ui_conexion(texto, color):
    app.after(0, lambda: estadoConexion.configure(text=texto, text_color=color))

def tarea_conectar(puerto):
    if not puerto or "No se encontraron" in puerto:
        _ui_conexion("● Selecciona un puerto", "orange")
        estado.conectando = False
        return

    _ui_conexion("● Conectando...", "orange")
    try:
        conn = serial.Serial(puerto, 9600, timeout=1)
        time.sleep(1.0)
        estado.arduino = conn
        _ui_conexion(f"● ONLINE - {puerto}", "#00FF66")
        estado.escuchando = True
        app.after(0, escribir_consola, f"[SISTEMA] Conectado exitosamente al puerto {puerto}")
        threading.Thread(target=hilo_lector_serial, daemon=True).start()
        app.after(0, sincronizar_automatico)
    except Exception as e:
        _ui_conexion("● Error de conexión", "#A12424")
        app.after(0, escribir_consola, f"[ERROR] Falló la apertura del puerto serial: {e}")
        print(f"[ERROR] Conexión fallida en {puerto}: {e}")
    finally:
        estado.conectando = False 

def conectar():
    if estado.arduino is not None or estado.conectando:
        return
    estado.conectando = True
    puerto = comboPuertos.get()
    threading.Thread(target=tarea_conectar, args=(puerto,), daemon=True).start()

def _limpiar_interfaz():
    estadoConexion.configure(text="● DESCONECTADO", text_color="#A12424")
    app.after(0, desactivar_alerta_visual)

def desconectar():
    estado.escuchando = False
    if estado.arduino:
        try:
            estado.arduino.close()
        except Exception:
            pass
        estado.arduino = None
        app.after(0, escribir_consola, "[SISTEMA] Puerto serial desconectado voluntariamente.")
    _limpiar_interfaz()

def enviar(comando):
    if estado.arduino is None:
        return
    try:
        estado.arduino.write((comando + "\n").encode())
        print(f"[TX] {comando}")
        app.after(0, escribir_consola, f"[TX] -> {comando}")
    except Exception as e:
        print(f"[ERROR] Al enviar '{comando}': {e}")
        app.after(0, escribir_consola, f"[ERR] Error crítico de transmisión: {e}")
        app.after(0, desconectar)

def sincronizar_automatico():
    ahora = datetime.now()
    hora12 = ahora.hour % 12 or 12   
    ampm = "P" if ahora.hour >= 12 else "A"
    dia = ahora.weekday() + 2          
    if dia > 7:
        dia = 1
    enviar(f"S:{hora12:02d}:{ahora.minute:02d}:{ahora.second:02d}:{ampm}:{dia}")

def reenviar_todas_alarmas():
    if not estado.arduino or not estado.arduino.is_open:
        messagebox.showwarning("Sin conexión", "No hay conexión activa con el Arduino.")
        return
    if not estado.alarmas:
        messagebox.showinfo("Info", "No hay alarmas guardadas para enviar.")
        return

    def _tarea():
        enviar("CLEARALL")
        time.sleep(0.15)
        for al in estado.alarmas:
            letra = "P" if al["periodo"] == "PM" else "A"
            activa = "1" if al["activa"] else "0"
            enviar(f"A:{int(al['hora'])}:{int(al['min'])}:{letra}:{al['duracion']}:{al['dias']}:{activa}")
            time.sleep(0.05)
        n = len(estado.alarmas)
        app.after(0, lambda: messagebox.showinfo("Reenvío completado",
                                                 f"{n} alarma(s) reenviada(s) al Arduino."))

    threading.Thread(target=_tarea, daemon=True).start()

def agregar_nueva_alarma_formulario():
    hora = comboHora.get()
    minuto = comboMinuto.get()
    periodo = periodoVar.get()
    duracion = comboDuracion.get()

    mascara = sum(1 << i for i, v in enumerate(dias_vars) if v.get())

    if mascara == 0:
        messagebox.showwarning("Atención", "Selecciona al menos un día de la semana.")
        return

    nueva_id = max((a["id"] for a in estado.alarmas), default=0) + 1
    nueva_al = {
        "id": nueva_id, "hora": hora, "min": minuto, "periodo": periodo,
        "duracion": duracion, "dias": mascara, "activa": True
    }
    estado.alarmas.append(nueva_al)
    guardar_alarmas_json()      
    actualizar_lista_visual()

    letra = "P" if periodo == "PM" else "A"
    cmd = f"A:{int(hora)}:{int(minuto)}:{letra}:{duracion}:{mascara}:1"

    if estado.arduino and estado.arduino.is_open:
        enviar(cmd)
        messagebox.showinfo("Éxito", "Alarma guardada y enviada al reloj.")
    else:
        messagebox.showinfo("Guardado Local", "Alarma guardada localmente (Arduino desconectado).")

# ========================================================
# QUEUE DE LECTURA SERIAL EN HILO SEPARADO [CORREGIDO]
# ========================================================
def hilo_lector_serial():
    while estado.escuchando:
        arduino_local = estado.arduino
        if arduino_local is None:
            break
        try:
            if arduino_local.in_waiting > 0:
                linea = arduino_local.readline().decode('utf-8', errors='ignore').strip()
                print(f"[RX] {linea}")  # Se mantiene visible en la terminal interna de VS Code
                
                # Árbol selectivo: Cada tipo de mensaje se maneja de forma exclusiva
                if linea.startswith("INFO:"):
                    app.after(0, actualizar_reloj_desde_arduino, linea)
                elif linea.startswith("ALERTA:1"):
                    app.after(0, activar_alerta_visual)
                elif linea.startswith("ALERTA:0"):
                    app.after(0, desactivar_alerta_visual)
                elif linea:  # Cualquier otra respuesta o confirmación del hardware
                    app.after(0, escribir_consola, f"[RX] <- {linea}")
        except Exception as e:
            print(f"[ERROR] Lector serial: {e}")
            app.after(0, escribir_consola, f"[ERR] Pérdida de comunicación física: {e}")
            app.after(0, desconectar)  
            break
        time.sleep(0.01)

def actualizar_reloj_desde_arduino(linea):
    try:
        partes = linea.split(":")
        if len(partes) < 6:
            return
        h, m, s = int(partes[1]), int(partes[2]), int(partes[3])
        p = "PM" if partes[4] == "P" else "AM"
        
        # Actualizar visualizadores de la GUI
        relojLabel.configure(text=f"{h:02d}:{m:02d}:{s:02d} {p}")
        
        dias_full = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
        dia_idx = int(partes[5]) - 1
        if 0 <= dia_idx < 7:
            diaLabel.configure(text=dias_full[dia_idx])
            
        # Imprime la telemetría limpia del segundo sin duplicar tramas crudas
        tiempo_str = f"{h:02d}:{m:02d}:{s:02d} {p}"
        escribir_consola(f"[RELOJ-ARDUINO] {tiempo_str} - Señal de hardware activa")
    except Exception as e:
        print(f"[ERROR] Parseando INFO: {e}")

# ========================================================
# GESTIÓN DE MODO DE ALERTA VISUAL
# ========================================================
def activar_alerta_visual():
    """Modifica drásticamente el marco del reloj para advertir que la sirena física está pitando."""
    frameDisplay.configure(border_color="#FF3333")  # Borde rojo neón
    relojLabel.configure(text_color="#FF3333")     # Números rojos
    diaLabel.configure(text_color="#FFAAAA")
    estadoConexion.configure(text="🚨 ¡SIRENA DE ALARMA ACTIVA!", text_color="#FF3333")

def desactivar_alerta_visual():
    """Restaura los colores verde neón originales cuando la alarma termina."""
    frameDisplay.configure(border_color="#00FF66")
    relojLabel.configure(text_color="#00FF66")
    diaLabel.configure(text_color="#88FF88")
    if estado.arduino:
        puerto = comboPuertos.get()
        estadoConexion.configure(text=f"● ONLINE - {puerto}", text_color="#00FF66")
    else:
        estadoConexion.configure(text="● DESCONECTADO", text_color="#A12424")

# ========================================================
# LÓGICA MATEMÁTICA DE PRÓXIMA ALARMA
# ========================================================
def calcular_tiempo_proxima_alarma():
    """Analiza las alarmas guardadas, cruza datos con el calendario y calcula los minutos restantes."""
    if not estado.alarmas:
        return "No hay alarmas configuradas"
    
    ahora = datetime.now()
    dia_actual_idx = (ahora.weekday() + 1) % 7  # Traducir a 0=Dom, 1=Lun...
    minutos_ahora = ahora.hour * 60 + ahora.minute
    
    mejor_alarma = None
    minimos_minutos_falta = float('inf')
    
    for al in estado.alarmas:
        if not al.get("activa", True):
            continue
            
        h = int(al["hora"])
        if al["periodo"] == "PM" and h != 12:
            h += 12
        if al["periodo"] == "AM" and h == 12:
            h = 0
        minutos_alarma = h * 60 + int(al["min"])
        
        for d in range(8):  
            dia_evaluar = (dia_actual_idx + d) % 7
            
            if (al["dias"] >> dia_evaluar) & 1:
                if d == 0:  # Es hoy
                    if minutos_alarma > minutos_ahora:
                        faltan = minutos_alarma - minutos_ahora
                    else:
                        continue  
                elif d == 7:  # Mismo día, pero la siguiente semana
                    if minutos_alarma <= minutos_ahora:
                        faltan = 7 * 24 * 60 - (minutos_ahora - minutos_alarma)
                    else:
                        continue
                else:  # Un día del futuro intermedio
                    faltan = (24 * 60 - minutos_ahora) + (d - 1) * 24 * 60 + minutos_alarma
                    
                if faltan < minimos_minutos_falta:
                    minimos_minutos_falta = faltan
                    mejor_alarma = al
                    
    if mejor_alarma:
        horas_restantes = minimos_minutos_falta // 60
        mins_restantes = minimos_minutos_falta % 60
        tiempo_str = f"{horas_restantes}h {mins_restantes}m" if horas_restantes > 0 else f"{mins_restantes} min"
        return f"🔔 Próxima: {mejor_alarma['hora']}:{mejor_alarma['min']} {mejor_alarma['periodo']} (en {tiempo_str})"
    
    return "No hay alarmas activas programadas"

def actualizar_proxima_alarma_ui():
    texto = calcular_tiempo_proxima_alarma()
    proximaAlarmaLabel.configure(text=texto)

# ========================================================
# BUCLE DE RELOJ LOCAL EN SEGUNDO PLANO [CORREGIDO]
# ========================================================
def bucle_reloj_local():
    """Muestra la hora de la computadora sólo si el Arduino está desconectado."""
    ahora = datetime.now()
    hora12 = ahora.hour % 12 or 12
    ampm = "PM" if ahora.hour >= 12 else "AM"
    
    if estado.arduino is None:
        relojLabel.configure(text=f"{hora12:02d}:{ahora.minute:02d}:{ahora.second:02d} {ampm}")
        
        dias_full = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
        dia_idx = (ahora.weekday() + 1) % 7
        diaLabel.configure(text=dias_full[dia_idx])
        
        if ahora.second != estado.ultimo_segundo_local:
            estado.ultimo_segundo_local = ahora.second
            tiempo_str = f"{hora12:02d}:{ahora.minute:02d}:{ahora.second:02d} {ampm}"
            escribir_consola(f"[DEBUG-LOCAL] {tiempo_str} - Sistema Offline (Esperando hardware...)")
    
    actualizar_proxima_alarma_ui()
    app.after(500, bucle_reloj_local)

# ==========================================
# ARRANQUE DE LA APLICACIÓN
# ==========================================
cargar_alarmas_json()   
buscar_puertos()
actualizar_lista_visual()
bucle_reloj_local()  
app.mainloop()