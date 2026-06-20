# Reloj Maestro - Terminal de Control (V2.0)

Esta aplicación de escritorio, desarrollada en Python utilizando la biblioteca **CustomTkinter**, actúa como la interfaz de control principal (`Frontend`) para un sistema de **Reloj Maestro** basado en hardware (Arduino). Permite la monitorización en tiempo real del tiempo del sistema, el control de conexiones seriales, la programación avanzada de alarmas semanales mediante máscaras de bits, la redundancia local de eventos y el registro detallado de operaciones en una bitácora o terminal integrada.

---

## Características Principales y Arquitectura de la Interfaz

La aplicación se compone de un entorno dinámico dividido estratégicamente en tres bloques visuales principales para maximizar la legibilidad y la usabilidad en entornos de supervisión:

```
+-------------------------------------------------------------+
|  [BLOQUE SUPERIOR]                                          |
|  +------------------------+  +----------------------------+ |
|  |     RELOJ DIGITAL      |  |     CONEXIÓN SERIAL        | |
|  |       Y ESTADO         |  | (Puertos/Botones/Terminal) | |
|  +------------------------+  +----------------------------+ |
+-------------------------------------------------------------+
|  [BLOQUE CENTRAL]                                           |
|  +--------------------------------------------------------+ |
|  |             CONFIGURACIÓN DE ALARMAS                   | |
|  +--------------------------------------------------------+ |
+-------------------------------------------------------------+
|  [BLOQUE INFERIOR (Layout Variable)]                        |
|  +------------------------+  +----------------------------+ |
|  |                        |  |                            | |
|  |     MIS ALARMAS        |  |     LOG DE ACTIVIDAD       | |
|  |     PROGRAMADAS        |  |       (Ocultable)          | |
|  |                        |  |                            | |
|  +------------------------+  +----------------------------+ |
+-------------------------------------------------------------+

```

1. **Bloque Superior (Reloj y Controles Seriales):**
* **Panel LCD Digital:** Diseñado sobre un fondo oscuro (`#050505`) con una tipografía monoespaciada de alta visibilidad (`Consolas`) en color cian brillante (`#05DCF8`). Muestra la hora exacta dictada por el hardware en formato `HH:MM:SS AM/PM`, el día de la semana actual y un indicador de estado del canal serial (`● DESCONECTADO`, `● Conectando...` u `● ONLINE - [PUERTO]`).
* **Panel de Comunicación Serial:** Incluye un menú desplegable dinámico que interactúa con un escaneo automatizado en segundo plano para seleccionar los puertos COM activos, junto con controles directos para establecer la conexión, interrupción del canal, recarga manual del bus y sincronización forzada de la hora del sistema operativo hacia el hardware.


2. **Bloque Central (Formulario de Configuración):**
* Un panel unificado que agrupa de forma lineal la selección de hora, minuto, período (AM/PM) y la duración de activación de la sirena física (con intervalos seleccionables de 5 a 60 segundos).
* **Matriz de Selección Semanal:** Sistema de casillas de verificación individuales para mapear los 7 días de la semana, traduciendo de manera inmediata la selección del usuario en máscaras de bits (`Bitmask`) optimizadas para el envío eficiente de datos binarios a través del puerto serial.


3. **Bloque Inferior (Mapeo de Datos Dinámico):**
* **Lista de Alarmas Guardadas:** Contenedor interactivo (`CTkScrollableFrame`) con desplazamiento vertical nativo. Cada alarma se renderiza en una tarjeta individual (`CTkFrame`) que expone los días de ejecución resaltados visualmente en cian (`#05DCF8`), la duración de la sirena, un interruptor (`CTkSwitch`) para habilitar o deshabilitar la regla de tiempo en caliente y un botón de eliminación inmediata (`🗑️`).
* **Log de Actividad Terminal:** Cuadro de texto interactivo de alta capacidad en modo lectura, encargado de imprimir marcas de tiempo (`[HH:MM:SS]`) por cada interacción, comandos de transmisión (`TX ➔`), comandos de recepción de tramas (`RX 🚨`) o excepciones críticas del sistema.



---

## Protocolo de Comunicación Serial (Trama de Datos)

La comunicación bidireccional asíncrona entre la Terminal de Control (Python) y el Reloj Maestro (Arduino) se rige bajo un protocolo estricto basado en cadenas de texto formateadas con delimitadores de dos puntos (`:`) y finalizadas en salto de línea (`\n`):

### Transmisión (TX: Python ➔ Arduino)

* **Sincronización Horaria (`S`):** Sincroniza el RTC (Real Time Clock) del hardware con la hora local de la PC.
* *Formato:* `S:{HH}:{MM}:{SS}:{A/P}:{D}`
* *Ejemplo:* `S:07:30:00:A:2` (Establece el reloj del hardware a las 07:30:00 AM, Lunes).


* **Configuración de Alarma (`A`):** Envía los parámetros de una alarma para su procesamiento.
* *Formato:* `A:{Hora_12h}:{Minuto}:{A/P}:{Duración}:{Mascara_Bits}`
* *Ejemplo:* `A:12:15:P:10:62` (Alarma a las 12:15 PM, duración de 10s, activa de lunes a viernes - Bitmask `62`).



### Recepción (RX: Arduino ➔ Python)

* **Latido de Datos (`INFO`):** Trama enviada por el hardware cada segundo para refrescar la interfaz.
* *Formato:* `INFO:{HH}:{MM}:{SS}:{P}:{D}`


* **Disparo de Alerta (`ALERTA`):** Notificación activa enviada por el microcontrolador cuando la sirena física entra en ejecución.
* *Formato:* `ALERTA:ALARMA_ACTIVA`



---

## Registro Detallado de Actualizaciones Recientes (Log de Cambios - V2.0)

Se han implementado optimizaciones críticas en la experiencia de usuario, el control de concurrencia y el comportamiento adaptativo de los layouts en la última revisión del software:

### 1. Sistema Adaptativo de Interfaz (Función Toggle para el Log)

* **Comportamiento:** Se ha incorporado la capacidad de ocultar por completo el panel **"LOG DE ACTIVIDAD TERMINAL"** sin alterar las dimensiones generales configuradas de la ventana principal y evitando corrimientos o errores visuales en el resto de los elementos contenedores.
* **Redistribución Dinámica:** Al ocultarse el log mediante la desvinculación segura de su empaquetado (`pack_forget`), el componente adyacente **"MIS ALARMAS PROGRAMADAS"** expande sus dimensiones automáticamente ocupando el 100% de la anchura disponible en el bloque inferior, optimizando el espacio visual para mostrar alarmas complejas sin comprimir sus elementos internos.
* **Restauración:** Al volver a activarse, el layout recalcula la interfaz e inyecta la terminal en su posición lateral derecha original de manera inmediata.

### 2. Nuevo Botón de Control de Estado de Interfaz

* **Adición:** Se insertó el widget `btn_toggle_log` en la cuadrícula de botones del panel de comunicaciones (`frameGridBotones`), ocupando de manera extendida las dos columnas del grid (`columnspan=2`) en una nueva fila creada exclusivamente para esta función (`row=2`).
* **Estados Visuales del Botón:**
* *Estado Visible (Terminal Abierta):* Texto *"👁️ Ocultar Terminal"*, color de fondo gris medio (`#444444`) y color de resaltado (`#555555`).
* *Estado Oculto (Terminal Cerrada):* Texto *"👁️ Mostrar Terminal"*, color de fondo oscuro integrado con el fondo general (`#2b2b2b`) y color de resaltado (`#333333`).



### 3. Mutación del Estado de la Aplicación (`AppState`)

* **Propiedad `estado.log_visible`:** Se añadió un booleano de control de flujo dentro del constructor global de estados de la aplicación. Esto asegura que la lógica interna del software conozca en todo momento el estado del renderizado de la terminal, garantizando estabilidad en el flujo de hilos secundarios al interactuar con componentes dinámicos de la interfaz gráfica.

### 4. Robustez de Rutas de Recursos (`PyInstaller` Ready)

* **Función `resolver_ruta`:** Implementación de un entorno de aislamiento para recursos estáticos (`.ico`, imágenes). Detecta automáticamente si el software se ejecuta en un script de desarrollo aislado o empaquetado en un binario ejecutable congelado mediante PyInstaller (`sys._MEIPASS`), evitando cierres inesperados por rutas relativas rotas en entornos de producción.

### 5. Multi-Hilos en Conexión e Interacciones Concurrentes

* **Asincronía en UI:** La tarea de conexión física serial (`tarea_conectar`) ahora es delegada por completo a un hilo secundario (`threading.Thread`) en modo `daemon=True`. Esto elimina por completo el congelamiento momentáneo (*Lag/Freeze*) de la ventana gráfica principal de CustomTkinter mientras se inicializa, negocia y estabiliza el puerto COM del Hardware.

### 6. Sistema Inteligente de Ventanas Emergentes Modales (`CTkToplevel`)

* **Ventana Alerta Duplicada Protegida:** Se agregó la bandera de estado `estado.alerta_abierta`. Si una alarma se activa localmente por software y simultáneamente el hardware envía la trama `ALERTA:ALARMA_ACTIVA`, la interfaz intercepta la segunda solicitud bloqueando la duplicación de ventanas molestas en la pantalla del usuario.
* **Geometría Relativa Dinámica:** Las alertas flotantes calculan matemáticamente su posicionamiento basándose en las coordenadas virtuales (`winfo_x`, `winfo_y`, `winfo_width`, `winfo_height`) de la aplicación principal para centrar de forma milimétrica la advertencia emergente justo sobre la vista del usuario, de forma independiente a la resolución de pantalla del sistema operativo.

---

## Requisitos e Instalación

Para ejecutar este entorno de control es necesario contar con Python 3.8 o superior e instalar las dependencias requeridas a través del gestor de paquetes de Python:

```bash
pip install customtkinter pyserial

```

### Inicialización del Sistema

Para ejecutar la aplicación de control principal en modo de desarrollo:

```bash
python reloj_maestro_v2.py

```

### Compilación a Ejecutable (.EXE)

Si se desea generar el archivo ejecutable autocontenido para entornos de producción en Windows, ejecute el comando de PyInstaller incluyendo el recurso del ícono mapeado en el código:

```bash
pyinstaller --noconfirm --onedir --windowed --add-data "Reloj_Maestro.ico;." --icon="Reloj_Maestro.ico" "reloj_maestro_v2.py"

```