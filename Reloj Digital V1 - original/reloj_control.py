import customtkinter as ctk
import serial
from serial.tools import list_ports
import threading
import time
from datetime import datetime
from tkinter import messagebox
# ========================================================
# INICIO - ENTORNO ADICIONAL PARA EL ICONO
# ========================================================
import os
import sys

def resolver_ruta(ruta_relativa):
    """ Determina la ruta absoluta para recursos, necesaria para PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, ruta_relativa)
    return os.path.join(os.path.abspath("."), ruta_relativa)
# ========================================================
# FIN - ENTORNO ADICIONAL PARA EL ICONO
# ========================================================

# ==========================================
# ESTADO Y ALARMAS (INICIA VACÍO)
# ==========================================
class AppState:
    def __init__(self):
        self.arduino = None
        self.ultima_sync = None
        self.escuchando = False
        # Se eliminaron las alarmas por defecto para iniciar desde cero
        self.alarmas = []

estado = AppState()

# ==========================================
# CONFIGURACIÓN DE VENTANA
# ==========================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

app = ctk.CTk()
app.title("Terminal de Control - Reloj Maestro")

# ========================================================
# INICIO - ASIGNACIÓN DEL ICONO A LA VENTANA
# ========================================================
try:
    # Se busca el archivo 'Reloj_Maestro.ico' usando la función de mapeo temporal
    ruta_icono = resolver_ruta('Reloj_Maestro.ico')
    app.iconbitmap(ruta_icono)
except Exception as e:
    print(f"Aviso: No se pudo cargar el icono visual de la ventana: {e}")
# ========================================================
# FIN - ASIGNACIÓN DEL ICONO A LA VENTANA
# ========================================================

app.update_idletasks()
window_width = 1100  
window_height = 680  
x = (app.winfo_screenwidth() - window_width) // 2
y = (app.winfo_screenheight() - window_height) // 2
app.geometry(f"{window_width}x{window_height}+{x}+{y}")
app.resizable(False, False)

# ==========================================
# BLOQUE SUPERIOR: RELOJ Y MATRIZ DE BOTONES
# ==========================================
frame_superior = ctk.CTkFrame(app, fg_color="transparent")
frame_superior.pack(side="top", fill="x", padx=20, pady=(15, 5))

# Columna Izquierda: Reloj e indicador de puerto compacto
panel_reloj = ctk.CTkFrame(frame_superior, fg_color="transparent")
panel_reloj.pack(side="left", fill="both", expand=True, padx=(0, 15))

frameDisplay = ctk.CTkFrame(panel_reloj, fg_color="#050505", border_width=4, border_color="#00FF66")
frameDisplay.pack(fill="x", pady=(0, 8))

relojLabel = ctk.CTkLabel(frameDisplay, text="--:--:-- --", font=("Consolas", 58, "bold"), text_color="#00FF66")
relojLabel.pack(pady=(20, 2), padx=(10, 0))

diaLabel = ctk.CTkLabel(frameDisplay, text="---", font=("Consolas", 18, "bold"), text_color="#88FF88")
diaLabel.pack(pady=2, padx=(10, 0))

estadoConexion = ctk.CTkLabel(frameDisplay, text="● DESCONECTADO", font=("Consolas", 14, "bold"), text_color="#A12424")
estadoConexion.pack(pady=(2, 12), padx=(10, 0))

# Cuadro de puerto serie reducido en tamaño
frameConexion = ctk.CTkFrame(panel_reloj)
frameConexion.pack(fill="x")
ctk.CTkLabel(frameConexion, text="Puerto:", font=("Consolas", 13, "bold")).pack(side="left", padx=15, pady=8)
comboPuertos = ctk.CTkComboBox(frameConexion, values=["Buscando..."], width=180) # Tamaño reducido
comboPuertos.pack(side="left", padx=5, pady=8)


# Columna Derecha: Matriz 2x2 alineada con el reloj
panel_botones_2x2 = ctk.CTkFrame(frame_superior, fg_color="transparent")
panel_botones_2x2.pack(side="right", fill="both", padx=(15, 0))

# Fila 1: Buscar y Conectar
fila1 = ctk.CTkFrame(panel_botones_2x2, fg_color="transparent")
fila1.pack(fill="x", pady=(22, 0)) 
ctk.CTkButton(fila1, text="🔄 Buscar Puertos", command=lambda: buscar_puertos(), width=170, height=45).pack(side="left", padx=8)
ctk.CTkButton(fila1, text="🔌 Conectar", command=lambda: conectar(), fg_color="#00AA00", hover_color="#007700", width=170, height=45).pack(side="left", padx=8)

# Fila 2: Sincronizar y Desconectar
fila2 = ctk.CTkFrame(panel_botones_2x2, fg_color="transparent")
fila2.pack(fill="x", pady=(32, 0)) 
ctk.CTkButton(fila2, text="⏰ Sincronizar", command=lambda: sincronizar_automatico(), width=170, height=45).pack(side="left", padx=8)
ctk.CTkButton(fila2, text="⏻ Desconectar", command=lambda: desconectar(), fg_color="#A12424", hover_color="#7A1B1B", width=170, height=45).pack(side="left", padx=8)


# ==========================================
# BLOQUE CENTRAL: CONFIGURACIÓN DE ALARMAS
# ==========================================
frameAlarma = ctk.CTkFrame(app)
frameAlarma.pack(fill="x", padx=20, pady=15)

ctk.CTkLabel(frameAlarma, text="CONFIGURACIÓN DE ALARMAS", font=("Consolas", 14, "bold"), text_color="#00FF66").pack(pady=(10, 5), padx=15, anchor="w")

frameConfigLineal = ctk.CTkFrame(frameAlarma, fg_color="transparent")
frameConfigLineal.pack(fill="x", padx=15, pady=5)

ctk.CTkLabel(frameConfigLineal, text="Hora:").pack(side="left", padx=4)
comboHora = ctk.CTkOptionMenu(frameConfigLineal, values=[f"{i:02d}" for i in range(1,13)], width=85)
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
comboDuracion = ctk.CTkOptionMenu(frameConfigLineal, values=["5","10","15","30","60"], width=85)
comboDuracion.set("10")
comboDuracion.pack(side="left", padx=5)

# Línea 2: Días y Botón Guardar Alarma
frameDiasYGuardar = ctk.CTkFrame(frameAlarma, fg_color="transparent")
frameDiasYGuardar.pack(fill="x", padx=15, pady=(5, 15))

dias_nombres = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
dias_vars = [ctk.BooleanVar(value=True) for _ in range(7)]

frameCheckboxes = ctk.CTkFrame(frameDiasYGuardar, fg_color="transparent")
frameCheckboxes.pack(side="left")

for i, nombre in enumerate(dias_nombres):
    ctk.CTkCheckBox(frameCheckboxes, text=nombre, variable=dias_vars[i], width=70, font=("Consolas", 12)).pack(side="left", padx=4)

btn_guardar = ctk.CTkButton(frameDiasYGuardar, text="💾 Guardar Alarma", command=lambda: agregar_nueva_alarma_formulario(), 
                             fg_color="#1f538d", hover_color="#153B64", width=180, height=35)
btn_guardar.pack(side="right", padx=(0, 5))


# ==========================================
# BLOQUE INFERIOR: PANEL PANORÁMICO
# ==========================================
frame_lista_completa = ctk.CTkFrame(app, fg_color="transparent")
frame_lista_completa.pack(side="bottom", fill="both", expand=True, padx=20, pady=(5, 20))

ctk.CTkLabel(frame_lista_completa, text="MIS ALARMAS PROGRAMADAS", font=("Consolas", 14, "bold"), text_color="#00FF66").pack(pady=(0, 5), anchor="w")

scroll_alarmas = ctk.CTkScrollableFrame(frame_lista_completa, fg_color="#101010", border_width=1, border_color="#333333")
scroll_alarmas.pack(fill="both", expand=True)


# ==========================================
# LÓGICA DE ACTUALIZACIÓN DE LA LISTA
# ==========================================
def actualizar_lista_visual():
    for widget in scroll_alarmas.winfo_children():
        widget.destroy()

    if not estado.alarmas:
        lbl = ctk.CTkLabel(scroll_alarmas, text="No hay alarmas configuradas en el sistema.", font=("Consolas", 14), text_color="gray")
        lbl.pack(pady=30)
        return

    for al in estado.alarmas:
        fila = ctk.CTkFrame(scroll_alarmas, fg_color="#1a1a1a", height=65)
        fila.pack(fill="x", pady=4, padx=5)
        fila.pack_propagate(False)

        lbl_icono = ctk.CTkLabel(fila, text="⏰", font=("Consolas", 22))
        lbl_icono.pack(side="left", padx=(20, 5))

        lbl_hora = ctk.CTkLabel(fila, text=f"{al['hora']}:{al['min']}", font=("Consolas", 26, "bold"), text_color="#ffffff")
        lbl_hora.pack(side="left", padx=5)
        
        lbl_per = ctk.CTkLabel(fila, text=al['periodo'], font=("Consolas", 14, "bold"), text_color="#888888")
        lbl_per.pack(side="left", padx=(2, 20), pady=(6,0))

        lbl_dur = ctk.CTkLabel(fila, text=f"• Duración: {al['duracion']}s", font=("Consolas", 12), text_color="gray")
        lbl_dur.pack(side="left", padx=10)

        frame_dias_lista = ctk.CTkFrame(fila, fg_color="transparent")
        frame_dias_lista.pack(side="left", expand=True, anchor="center")
        
        dias_letras = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
        for i, letra in enumerate(dias_letras):
            activo = bitRead(al["dias"], i)
            color_letra = "#00FF66" if activo else "#444444"
            font_letra = ("Consolas", 13, "bold") if activo else ("Consolas", 13)
            
            l = ctk.CTkLabel(frame_dias_lista, text=letra, text_color=color_letra, font=font_letra)
            l.pack(side="left", padx=10)

        btn_borrar = ctk.CTkButton(fila, text="🗑️", fg_color="#A12424", hover_color="#7A1B1B", width=40, height=35,
                                   command=lambda a_id=al['id']: boton_eliminar_alarma(a_id))
        btn_borrar.pack(side="right", padx=20)

        switch_var = ctk.BooleanVar(value=al["activa"])
        sw = ctk.CTkSwitch(fila, text="", variable=switch_var, width=45,
                           command=lambda a_id=al['id'], var=switch_var: switch_activar_alarma(a_id, var))
        sw.pack(side="right", padx=10)

def bitRead(valor, bit):
    return (valor >> bit) & 0x01

def boton_eliminar_alarma(id_alarma):
    estado.alarmas = [a for a in estado.alarmas if a["id"] != id_alarma]
    actualizar_lista_visual()
    print(f"Eliminar alarma ID: {id_alarma}")

def switch_activar_alarma(id_alarma, var_estado):
    nuevo_estado = var_estado.get()
    for al in estado.alarmas:
        if al["id"] == id_alarma:
            al["activa"] = nuevo_estado
            break
    print(f"Alarma {id_alarma} cambiada a estado: {nuevo_estado}")

# ==========================================
# GESTIÓN SERIAL Y CONEXIÓN
# ==========================================
def buscar_puertos():
    puertos = [p.device for p in list_ports.comports()] or ["No se encontraron puertos"]
    comboPuertos.configure(values=puertos)
    comboPuertos.set(puertos[0])

def tarea_conectar():
    puerto = comboPuertos.get()
    if "No se encontraron" in puerto:
        estadoConexion.configure(text="● Selecciona un puerto", text_color="orange")
        return
    estadoConexion.configure(text="● Conectando...", text_color="orange")
    try:
        nuevo = serial.Serial(puerto, 9600, timeout=1)
        time.sleep(1.0) 
        estado.arduino = nuevo
        estadoConexion.configure(text=f"● ONLINE - {puerto}", text_color="#00FF66")
        estado.escuchando = True
        threading.Thread(target=hilo_lector_serial, daemon=True).start()
        sincronizar_automatico()
    except Exception as e:
        estadoConexion.configure(text="● Error de conexión", text_color="#A12424")

def conectar():
    if estado.arduino is None:
        threading.Thread(target=tarea_conectar, daemon=True).start()

def deactivate_interfaz_desconexion(): # Nota: Corregido error tipográfico implícito en tu llamada
    estadoConexion.configure(text="● DESCONECTADO", text_color="#A12424")
    relojLabel.configure(text="--:--:-- --")
    diaLabel.configure(text="---")

def desconectar():
    estado.escuchando = False
    if estado.arduino:
        try: estado.arduino.close()
        except: pass
        estado.arduino = None
    deactivate_interfaz_desconexion()

def enviar(comando):
    if estado.arduino is None: return
    try: estado.arduino.write((comando + "\n").encode())
    except: desconectar()

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

    # ==========================================
    # ENVIAR COMANDO REAL AL ARDUINO
    # ==========================================
    letra_periodo = "P" if periodo == "PM" else "A"
    comando_alarma = f"A:{int(hora)}:{int(minuto)}:{letra_periodo}:{duracion}:{mascara}"
    
    if estado.arduino and estado.arduino.is_open:
        enviar(comando_alarma)
        messagebox.showinfo("Éxito", "Alarma guardada y enviada al reloj.")
    else:
        messagebox.showinfo("Guardado Local", "Alarma guardada en la interfaz (Arduino desconectado).")

def hilo_lector_serial():
    while estado.escuchando and estado.arduino:
        try:
            if estado.arduino.in_waiting > 0:
                linea = estado.arduino.readline().decode('utf-8', errors='ignore').strip()
                if linea.startswith("INFO:"):
                    app.after(0, actualizar_reloj_desde_arduino, linea)
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
app.mainloop()