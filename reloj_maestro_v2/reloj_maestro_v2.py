import customtkinter as ctk
import serial
from serial.tools import list_ports
import threading
import time
from datetime import datetime
from tkinter import messagebox
import os
import sys

# ========================================================
# ENTORNO ADICIONAL PARA EL ICONO
# ========================================================
def resolver_ruta(ruta_relativa):
    """ Determina la ruta absoluta para recursos, necesaria para PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, ruta_relativa)
    return os.path.join(os.path.abspath("."), ruta_relativa)

# ==========================================
# ESTADO Y ALARMAS
# ==========================================
class AppState:
    def __init__(self):
        self.arduino = None
        self.ultima_sync = None
        self.escuchando = False
        self.alarmas = []
        self.alerta_abierta = False
        self.log_visible = True  # <--- Nuevo control de estado para la terminal

estado = AppState()

# ==========================================
# CONFIGURACIÓN DE VENTANA
# ==========================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Terminal de Control - Reloj Maestro")

try:
    ruta_icono = resolver_ruta('Reloj_Maestro.ico')
    app.iconbitmap(ruta_icono)
except Exception as e:
    print(f"Aviso: No se pudo cargar el icono visual de la ventana: {e}")

app.update_idletasks()
window_width = 1100  
window_height = 750  
x = (app.winfo_screenwidth() - window_width) // 2
y = (app.winfo_screenheight() - window_height) // 2
app.geometry(f"{window_width}x{window_height}+{x}+{y}")

app.resizable(True, True) 
app.minsize(1050, 700)

# ==========================================
# FUNCIONES DE INTERFAZ DINÁMICA
# ==========================================
def toggle_log():
    """ Oculta o muestra el panel lateral derecho del log y adapta la ventana """
    if estado.log_visible:
        panel_bitacora.pack_forget()  # Oculta el panel
        btn_toggle_log.configure(text="Mostrar Terminal", fg_color="#2b2b2b", hover_color="#333333")
        estado.log_visible = False
    else:
        # Vuelve a inyectar el panel a la derecha
        panel_bitacora.pack(side="right", fill="both", padx=(10, 0))
        btn_toggle_log.configure(text="Ocultar Terminal", fg_color="#444444", hover_color="#555555")
        estado.log_visible = True

# ==========================================
# BLOQUE SUPERIOR: RELOJ Y CONTROLES SERIALES
# ==========================================
frame_superior = ctk.CTkFrame(app, fg_color="transparent")
frame_superior.pack(side="top", fill="x", padx=20, pady=(15, 5))

# Panel de Reloj LCD Digital
panel_reloj = ctk.CTkFrame(frame_superior, fg_color="transparent")
panel_reloj.pack(side="left", fill="both", expand=True, padx=(0, 10))

frameDisplay = ctk.CTkFrame(panel_reloj, fg_color="#050505", border_width=2, border_color="#062AF8")
frameDisplay.pack(fill="both", expand=True)

relojLabel = ctk.CTkLabel(frameDisplay, text="--:--:-- --", font=("Consolas", 54, "bold"), text_color="#05DCF8")
relojLabel.pack(pady=(15, 2), padx=10, fill="x")

diaLabel = ctk.CTkLabel(frameDisplay, text="---", font=("Consolas", 16, "bold"), text_color="#88FF88")
diaLabel.pack(pady=2, padx=10, fill="x")

estadoConexion = ctk.CTkLabel(frameDisplay, text="● DESCONECTADO", font=("Consolas", 13, "bold"), text_color="#A12424")
estadoConexion.pack(pady=(2, 12), padx=10, fill="x")

# Panel de Comunicación
panel_comunicaciones = ctk.CTkFrame(frame_superior, width=380)
panel_comunicaciones.pack(side="right", fill="both", padx=(10, 0))
panel_comunicaciones.pack_propagate(False)

ctk.CTkLabel(panel_comunicaciones, text="CONEXIÓN SERIAL Hardware", font=("Consolas", 13, "bold"), text_color="#05DCF8").pack(pady=(10, 5), padx=15, anchor="w")

frameSelectorPort = ctk.CTkFrame(panel_comunicaciones, fg_color="transparent")
frameSelectorPort.pack(fill="x", padx=15, pady=5)
ctk.CTkLabel(frameSelectorPort, text="Puerto:", font=("Consolas", 12)).pack(side="left", padx=(0, 5))
comboPuertos = ctk.CTkComboBox(frameSelectorPort, values=["Buscando..."], width=240)
comboPuertos.pack(side="right", fill="x", expand=True)

# Grid Interno de botones de control (Ahora con 3 filas)
frameGridBotones = ctk.CTkFrame(panel_comunicaciones, fg_color="transparent")
frameGridBotones.pack(fill="both", expand=True, padx=15, pady=(5, 10))

btn_conectar = ctk.CTkButton(frameGridBotones, text="🔌 Conectar", command=lambda: conectar(), fg_color="#00AA00", hover_color="#007700", font=("Consolas", 12, "bold"))
btn_conectar.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")

btn_desconectar = ctk.CTkButton(frameGridBotones, text="⏻ Desconectar", command=lambda: desconectar(), fg_color="#A12424", hover_color="#7A1B1B", font=("Consolas", 12, "bold"))
btn_desconectar.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")

btn_buscar = ctk.CTkButton(frameGridBotones, text="🔄 Recargar", command=lambda: buscar_puertos(forzar=True), font=("Consolas", 12))
btn_buscar.grid(row=1, column=0, padx=4, pady=4, sticky="nsew")

btn_sync = ctk.CTkButton(frameGridBotones, text="⏰ Sincronizar", command=lambda: sincronizar_automatico(), font=("Consolas", 12))
btn_sync.grid(row=1, column=1, padx=4, pady=4, sticky="nsew")

# <--- NUEVO BOTÓN PARA MOSTRAR/OCULTAR LOG --->
btn_toggle_log = ctk.CTkButton(frameGridBotones, text="👁️ Ocultar Terminal", command=toggle_log, fg_color="#444444", hover_color="#555555", font=("Consolas", 12, "bold"))
btn_toggle_log.grid(row=2, column=0, columnspan=2, padx=4, pady=4, sticky="nsew")

frameGridBotones.rowconfigure((0, 1, 2), weight=1)
frameGridBotones.columnconfigure((0, 1), weight=1)

# ==========================================
# BLOQUE CENTRAL: CONFIGURACIÓN DE ALARMAS
# ==========================================
frameAlarma = ctk.CTkFrame(app)
frameAlarma.pack(fill="x", padx=20, pady=10)

ctk.CTkLabel(frameAlarma, text="CONFIGURACIÓN DE ALARMAS", font=("Consolas", 13, "bold"), text_color="#05DCF8").pack(pady=(10, 5), padx=15, anchor="w")

frameConfigLineal = ctk.CTkFrame(frameAlarma, fg_color="transparent")
frameConfigLineal.pack(fill="x", padx=15, pady=5)

ctk.CTkLabel(frameConfigLineal, text="Hora:").pack(side="left", padx=4)
comboHora = ctk.CTkOptionMenu(frameConfigLineal, values=[f"{i:02d}" for i in range(1, 13)], width=80)
comboHora.set("07")
comboHora.pack(side="left", padx=5)

ctk.CTkLabel(frameConfigLineal, text="Minuto:").pack(side="left", padx=4)
comboMinuto = ctk.CTkOptionMenu(frameConfigLineal, values=[f"{i:02d}" for i in range(60)], width=80)
comboMinuto.set("30")
comboMinuto.pack(side="left", padx=5)

periodoVar = ctk.StringVar(value="AM")
ctk.CTkRadioButton(frameConfigLineal, text="AM", variable=periodoVar, value="AM", width=60).pack(side="left", padx=10)
ctk.CTkRadioButton(frameConfigLineal, text="PM", variable=periodoVar, value="PM", width=60).pack(side="left", padx=5)

ctk.CTkLabel(frameConfigLineal, text="Duración Sirena (seg):").pack(side="left", padx=20)
comboDuracion = ctk.CTkOptionMenu(frameConfigLineal, values=["5", "10", "15", "30", "60"], width=80)
comboDuracion.set("10")
comboDuracion.pack(side="left", padx=5)

# Línea de selección de días semanales
frameDiasYGuardar = ctk.CTkFrame(frameAlarma, fg_color="transparent")
frameDiasYGuardar.pack(fill="x", padx=15, pady=(5, 12))

dias_nombres = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
dias_vars = [ctk.BooleanVar(value=True) for _ in range(7)]

frameCheckboxes = ctk.CTkFrame(frameDiasYGuardar, fg_color="transparent")
frameCheckboxes.pack(side="left")

for i, nombre in enumerate(dias_nombres):
    ctk.CTkCheckBox(frameCheckboxes, text=nombre, variable=dias_vars[i], width=65, font=("Consolas", 11)).pack(side="left", padx=2)

btn_guardar = ctk.CTkButton(frameDiasYGuardar, text="💾 Guardar Alarma", command=lambda: agregar_nueva_alarma_formulario(), 
                            fg_color="#1f538d", hover_color="#153B64", width=170, height=32, font=("Consolas", 12, "bold"))
btn_guardar.pack(side="right", padx=(0, 5))

# ==========================================
# BLOQUE INFERIOR: ALARMAS Y BITÁCORA LOG
# ==========================================
frame_inferior_split = ctk.CTkFrame(app, fg_color="transparent")
frame_inferior_split.pack(side="bottom", fill="both", expand=True, padx=20, pady=(5, 15))

# Lista de Alarmas
panel_lista_alarmas = ctk.CTkFrame(frame_inferior_split)
panel_lista_alarmas.pack(side="left", fill="both", expand=True, padx=(0, 10))

ctk.CTkLabel(panel_lista_alarmas, text="MIS ALARMAS PROGRAMADAS", font=("Consolas", 13, "bold"), text_color="#05DCF8").pack(pady=(10, 5), padx=15, anchor="w")

scroll_alarmas = ctk.CTkScrollableFrame(panel_lista_alarmas, fg_color="#101010", border_width=1, border_color="#222222")
scroll_alarmas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

# Terminal Log
panel_bitacora = ctk.CTkFrame(frame_inferior_split, width=380)
panel_bitacora.pack(side="right", fill="both", padx=(10, 0))
panel_bitacora.pack_propagate(False)

ctk.CTkLabel(panel_bitacora, text="LOG DE ACTIVIDAD TERMINAL", font=("Consolas", 13, "bold"), text_color="#05DCF8").pack(pady=(10, 5), padx=15, anchor="w")

txtLog = ctk.CTkTextbox(panel_bitacora, fg_color="#050505", text_color="#05DCF8", font=("Consolas", 11), border_width=1, border_color="#222222")
txtLog.pack(fill="both", expand=True, padx=10, pady=(0, 10))

def registrar_log(mensaje):
    timestamp = datetime.now().strftime("%H:%M:%S")
    txtLog.configure(state="normal")
    txtLog.insert("end", f"[{timestamp}] {mensaje}\n")
    txtLog.see("end")
    txtLog.configure(state="disabled")

# ==========================================
# GESTIÓN Y MONITOREO DE ALARMAS LOCALES
# ==========================================
def monitor_alarmas_locales():
    ahora = datetime.now()
    if ahora.second == 0:
        hora_actual = ahora.strftime("%I") 
        min_actual = ahora.strftime("%M")  
        per_actual = ahora.strftime("%p")  
        
        idx_dia_ui = (ahora.weekday() + 1) % 7 
        
        for al in estado.alarmas:
            if al["activa"]:
                if bitRead(al["dias"], idx_dia_ui): 
                    if al["hora"] == hora_actual and al["min"] == min_actual and al["periodo"] == per_actual:
                        if not estado.alerta_abierta:
                            registrar_log(f"⏰ ACTIVADO LOCAL: {hora_actual}:{min_actual} {per_actual}")
                            mostrar_alerta_emergente(origen_local=True)
                            
    app.after(1000, monitor_alarmas_locales)


def mostrar_alerta_emergente(origen_local=False):
    if estado.alerta_abierta:
        return
    
    estado.alerta_abierta = True
    
    ventana_alerta = ctk.CTkToplevel(app)
    ventana_alerta.title("Activación de Alarma")
    ventana_alerta.geometry("450x220")
    ventana_alerta.resizable(False, False)
    ventana_alerta.attributes("-topmost", True)
    
    x_alerta = app.winfo_x() + (app.winfo_width() // 2) - 225
    y_alerta = app.winfo_y() + (app.winfo_height() // 2) - 110
    ventana_alerta.geometry(f"450x220+{x_alerta}+{y_alerta}")

    frame_interior = ctk.CTkFrame(ventana_alerta, border_width=2, border_color="#289740")
    frame_interior.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(frame_interior, text="🔔 ALARMA EN EJECUCIÓN", font=("Consolas", 24, "bold"), text_color="#33FF5F").pack(pady=(20, 5))
    
    mensaje_detalle = "La alarma programada fue emitida de forma local\npor el software de la PC." if origen_local else "El reloj/Arduino está reproduciendo la alarma\nen sus paneles físicos."
    ctk.CTkLabel(frame_interior, text=mensaje_detalle, font=("Consolas", 14)).pack(pady=10)
    
    def cerrar_alerta():
        estado.alerta_abierta = False
        ventana_alerta.destroy()
        
    ventana_alerta.protocol("WM_DELETE_WINDOW", cerrar_alerta)
    
    ctk.CTkButton(frame_interior, text="De acuerdo", fg_color="#289740", hover_color="#0F461B",
                command=cerrar_alerta).pack(pady=(10, 15))


# ==========================================
# LÓGICA DE ACTUALIZACIÓN DE LA LISTA
# ==========================================
def actualizar_lista_visual():
    for widget in scroll_alarmas.winfo_children():
        widget.destroy()

    if not estado.alarmas:
        lbl = ctk.CTkLabel(scroll_alarmas, text="No hay alarmas configuradas en el sistema.", font=("Consolas", 13), text_color="gray")
        lbl.pack(pady=30)
        return

    for al in estado.alarmas:
        fila = ctk.CTkFrame(scroll_alarmas, fg_color="#161616", height=60)
        fila.pack(fill="x", pady=3, padx=5)
        fila.pack_propagate(False)

        ctk.CTkLabel(fila, text="⏰", font=("Consolas", 18)).pack(side="left", padx=(15, 5))
        ctk.CTkLabel(fila, text=f"{al['hora']}:{al['min']}", font=("Consolas", 22, "bold"), text_color="#ffffff").pack(side="left", padx=5)
        ctk.CTkLabel(fila, text=al['periodo'], font=("Consolas", 13, "bold"), text_color="#888888").pack(side="left", padx=(2, 15), pady=(4, 0))
        ctk.CTkLabel(fila, text=f"• {al['duracion']}s", font=("Consolas", 11), text_color="gray").pack(side="left", padx=5)

        frame_dias_lista = ctk.CTkFrame(fila, fg_color="transparent")
        frame_dias_lista.pack(side="left", expand=True, anchor="center")
        
        dias_letras = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
        for i, letra in enumerate(dias_letras):
            activo = bitRead(al["dias"], i)
            color_letra = "#05DCF8" if activo else "#444444"
            font_letra = ("Consolas", 11, "bold") if activo else ("Consolas", 11)
            l = ctk.CTkLabel(frame_dias_lista, text=letra, text_color=color_letra, font=font_letra)
            l.pack(side="left", padx=6)

        btn_borrar = ctk.CTkButton(fila, text="🗑️", fg_color="#A12424", hover_color="#7A1B1B", width=35, height=30,
            command=lambda a_id=al['id']: boton_eliminar_alarma(a_id))
        btn_borrar.pack(side="right", padx=15)

        switch_var = ctk.BooleanVar(value=al["activa"])
        sw = ctk.CTkSwitch(fila, text="", variable=switch_var, width=40,
            command=lambda a_id=al['id'], var=switch_var: switch_activar_alarma(a_id, var))
        sw.pack(side="right", padx=5)

def bitRead(valor, bit):
    return (valor >> bit) & 0x01

def boton_eliminar_alarma(id_alarma):
    estado.alarmas = [a for a in estado.alarmas if a["id"] != id_alarma]
    registrar_log(f"Alarma local ID {id_alarma} eliminada.")
    actualizar_lista_visual()

def switch_activar_alarma(id_alarma, var_estado):
    nuevo_estado = var_estado.get()
    for al in estado.alarmas:
        if al["id"] == id_alarma:
            al["activa"] = nuevo_estado
            registrar_log(f"Alarma ID {id_alarma} modificada a activa={nuevo_estado}")
            break

# ==========================================
# GESTIÓN SERIAL Y CONEXIÓN
# ==========================================
def buscar_puertos(forzar=False):
    if estado.arduino and not forzar: 
        return
    
    puertos_encontrados = [p.device for p in list_ports.comports()]
    puertos = puertos_encontrados if puertos_encontrados else ["No se encontraron puertos"]
        
    if comboPuertos.cget("values") != puertos:
        comboPuertos.configure(values=puertos)
        if comboPuertos.get() not in puertos:
            comboPuertos.set(puertos[0])
            
    if forzar:
        if puertos_encontrados:
            lista_str = "\n".join(f"• {p}" for p in puertos_encontrados)
            messagebox.showinfo("Búsqueda de Puertos", f"Se han encontrado los puertos:\n\n{lista_str}")
        else:
            messagebox.showwarning("Búsqueda de Puertos", "No se encontró ningún puerto COM conectado.")
            
    if not estado.arduino and not forzar:
        app.after(2000, lambda: buscar_puertos())

def tarea_conectar():
    puerto = comboPuertos.get()
    if "No se encontraron" in puerto:
        estadoConexion.configure(text="● Selecciona un puerto válido", text_color="orange")
        return
    
    estadoConexion.configure(text="● Conectando...", text_color="orange")
    try:
        nuevo = serial.Serial(puerto, 9600, timeout=1)
        time.sleep(1.0) 
        estado.arduino = nuevo
        estadoConexion.configure(text=f"● ONLINE - {puerto}", text_color="#00FF66")
        estado.escuchando = True
        
        threading.Thread(target=hilo_lector_serial, daemon=True).start()
        registrar_log(f"Conexión exitosa establecida en {puerto}")
        sincronizar_automatico()
    except Exception as e:
        estadoConexion.configure(text="● Error de conexión", text_color="#A12424")
        registrar_log(f"Fallo de apertura serial: {str(e)}")

def conectar():
    if estado.arduino is None:
        threading.Thread(target=tarea_conectar, daemon=True).start()

def deactivate_interfaz_desconexion(): 
    estadoConexion.configure(text="● DESCONECTADO", text_color="#A12424")
    relojLabel.configure(text="--:--:-- --")
    diaLabel.configure(text="---")
    registrar_log("Puerto Serial Cerrado / Desconectado.")

def desconectar():
    estado.escuchando = False
    if estado.arduino:
        try: 
            estado.arduino.close()
        except: 
            pass
        estado.arduino = None
    deactivate_interfaz_desconexion()

def enviar(comando):
    if estado.arduino is None: return
    try: 
        estado.arduino.write((comando + "\n").encode())
        registrar_log(f"TX ➔ {comando}")
    except: 
        desconectar()

def sincronizar_automatico():
    ahora = datetime.now()
    hora12 = ahora.hour % 12
    if hora12 == 0: hora12 = 12
    ampm = "P" if ahora.hour >= 12 else "A"
    dia = ahora.weekday() + 2
    if dia > 7: dia = 1
    comando = f"S:{hora12:02d}:{ahora.minute:02d}:{ahora.second:02d}:{ampm}:{dia}"
    enviar(comando)

def agregar_nueva_alarma_formulario():
    hora = comboHora.get()
    minuto = comboMinuto.get()
    periodo = periodoVar.get()
    duracion = comboDuracion.get()

    mascara = 0
    for i, var in enumerate(dias_vars):
        if var.get(): mascara |= (1 << i)

    if mascara == 0:
        messagebox.showwarning("Atención", "Selecciona al menos un día de la semana.")
        return

    nueva_id = max([a["id"] for a in estado.alarmas], default=0) + 1
    nueva_al = {"id": nueva_id, "hora": hora, "min": minuto, "periodo": periodo, "duracion": duracion, "dias": mascara, "activa": True}
    
    estado.alarmas.append(nueva_al)
    actualizar_lista_visual()

    letra_periodo = "P" if periodo == "PM" else "A"
    comando_alarma = f"A:{int(hora)}:{int(minuto)}:{letra_periodo}:{duracion}:{mascara}"
    
    if estado.arduino and estado.arduino.is_open:
        enviar(comando_alarma)
        registrar_log(f"Nueva Alarma Guardada: {hora}:{minuto} {periodo}")
    else:
        registrar_log(f"Alarma guardada localmente (Sin Hardware vinculado)")
        messagebox.showwarning("Guardado Local", "Alarma guardada en la interfaz.\nNota: El Arduino está desconectado, se emitirá la alarma localmente.")

def hilo_lector_serial():
    while estado.escuchando and estado.arduino:
        try:
            if estado.arduino.in_waiting > 0:
                linea = estado.arduino.readline().decode('utf-8', errors='ignore').strip()
                
                if linea.startswith("INFO:"):
                    app.after(0, actualizar_reloj_desde_arduino, linea)
                
                elif linea.startswith("ALERTA:ALARMA_ACTIVA"):
                    registrar_log("RX 🚨 ALERTA: Sirena en curso en Hardware.")
                    app.after(0, lambda: mostrar_alerta_emergente(origen_local=False))
                    
        except:
            app.after(0, desconectar)
            break
        time.sleep(0.01)

def actualizar_reloj_desde_arduino(linea):
    
    try:
        partes = linea.split(":")
        if len(partes) < 6: return
        h, m, s = int(partes[1]), int(partes[2]), int(partes[3])
        p = "PM" if partes[4] == "P" else "AM"
        relojLabel.configure(text=f"{h:02d}:{m:02d}:{s:02d} {p}")
        dias = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
        dia_idx = int(partes[5]) - 1
        if 0 <= dia_idx < 7: diaLabel.configure(text=dias[dia_idx])
    except:
        pass

# ==========================================
# INICIO DE APLICACIÓN
# ==========================================
buscar_puertos() 
actualizar_lista_visual() 
monitor_alarmas_locales() 
registrar_log("Terminal iniciada. Monitoreo local activo.")
app.mainloop()