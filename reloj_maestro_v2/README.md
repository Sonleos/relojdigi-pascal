# Terminal de Control - Reloj Maestro

Esta aplicación de escritorio, desarrollada en Python utilizando la biblioteca **CustomTkinter**, actúa como la interfaz de control principal para un sistema de **Reloj Maestro** basado en hardware (Arduino). Permite la monitorización en tiempo real del tiempo del sistema, el control de conexiones seriales, la programación avanzada de alarmas semanales y el registro de eventos en una bitácora local.

---

## Características Principales y Arquitectura de la Interfaz

La aplicación se compone de un entorno dinámico dividido estratégicamente en tres bloques visuales principales para maximizar la legibilidad y usabilidad:

```
+-------------------------------------------------------------+
|  [BLOQUE SUPERIOR]                                          |
|  +------------------------+  +----------------------------+ |
|  |     RELOJ DIGITAL      |  |     CONEXIÓN SERIAL        | |
|  |      Y ESTADO          |  | (Puertos/Botones/Terminal) | |
|  +------------------------+  +----------------------------+ |
+-------------------------------------------------------------+
|  [BLOQUE CENTRAL]                                           |
|  +--------------------------------------------------------+ |
|  |             CONFIGURACIÓN DE ALARMAS                   | |
|  +--------------------------------------------------------+ |
+-------------------------------------------------------------+
|  [BLOQUE INFERIOR (Layout Variable)]                         |
|  +------------------------+  +----------------------------+ |
|  |                        |  |                            | |
|  |    MIS ALARMAS         |  |   LOG DE ACTIVIDAD         | |
|  |    PROGRAMADAS         |  |   (Ocultable)              | |
|  |                        |  |                            | |
|  +------------------------+  +----------------------------+ |
+-------------------------------------------------------------+

```

1. **Bloque Superior (Reloj y Controles Seriales):**
* **Panel LCD Digital:** Diseñado sobre un fondo oscuro (`#050505`) con tipografía monoespaciada de alta visibilidad (`Consolas`) en color cian brillante (`#05DCF8`). Muestra la hora exacta del Arduino en formato `HH:MM:SS AM/PM`, el día de la semana actual y un indicador de estado del hardware en tiempo real (Conectando, Online u Offline).
* **Panel de Comunicación Serial:** Incluye un menú desplegable inteligente con escaneo automatizado en segundo plano para seleccionar los puertos COM disponibles, junto con controles directos para conectar, desconectar, recargar la búsqueda y forzar la sincronización horaria de la PC al microcontrolador.


2. **Bloque Central (Formulario de Configuración):**
* Un panel unificado que agrupa de forma lineal la selección de hora, minuto, período (AM/PM) y la duración de activación de la sirena (de 5 a 60 segundos).
* **Matriz de Selección Semanal:** Sistema de checkboxes individuales para mapear los 7 días de la semana, traduciendo la selección del usuario en máscaras de bits (`Bitmask`) optimizadas para el envío de datos binarios y almacenamiento compacto.


3. **Bloque Inferior (Mapeo de Datos Dinámico):**
* **Lista de Alarmas Guardadas:** Contenedor interactivo (`CTkScrollableFrame`) con scroll vertical nativo. Cada alarma se renderiza en una tarjeta individual (`CTkFrame`) que expone los días de ejecución resaltados visualmente en cian (`#05DCF8`), la duración de la sirena, un interruptor (`CTkSwitch`) para habilitar/deshabilitar la alarma al vuelo y un botón de eliminación inmediata (`🗑️`).
* **Log de Actividad Terminal:** Cuadro de texto interactivo en modo lectura encargado de imprimir marcas de tiempo (`[HH:MM:SS]`) por cada interacción, comandos de transmisión (`TX ➔`), comandos de recepción (`RX 🚨`) o alertas críticas del sistema.



---

## Registro Detallado de Actualizaciones Recientes (Log de Cambios de la Interfaz)

Se han implementado optimizaciones críticas en la experiencia de usuario y en el comportamiento adaptativo de los layouts. A continuación se enumeran **todas** las actualizaciones aplicadas:

### 1. Sistema Adaptativo de Interfaz (Función Toggle para el Log)

* **Comportamiento:** Se ha incorporado la capacidad de ocultar por completo el panel **"LOG DE ACTIVIDAD TERMINAL"** sin alterar las dimensiones generales configuradas de la ventana principal y evitando corrimientos o bugs visuales en el resto de los frames.
* **Redistribución:** Al ocultarse el log mediante la desvinculación segura de su empaquetado (`pack_forget`), el componente adyacente **"MIS ALARMAS PROGRAMADAS"** expande sus dimensiones automáticamente al 100% de la anchura disponible en el bloque inferior, optimizando el espacio visual para mostrar alarmas sin comprimir sus elementos internos.
* **Restauración:** Al volver a activarse, el layout recalcula la interfaz e inyecta la terminal en su posición lateral derecha original de manera inmediata.

### 2. Nuevo Botón de Control de Estado de Interfaz

* **Adición:** Se insertó el widget `btn_toggle_log` en la cuadrícula de botones del panel de comunicaciones (`frameGridBotones`), ocupando de manera extendida las dos columnas del grid (`columnspan=2`) en una nueva fila creada exclusivamente para esta función (`row=2`).
* **Estados Visuales del Botón:**
* **Estado Visible (Terminal Abierta):** Texto *"👁️ Ocultar Terminal"*, color de fondo gris medio (`#444444`) y color de resaltado (`#555555`).
* **Estado Oculto (Terminal Cerrada):** Texto *"👁️ Mostrar Terminal"*, color de fondo oscuro integrado con el fondo general (`#2b2b2b`) y color de resaltado (`#333333`).



### 3. Mutación del Estado de la Aplicación (`AppState`)

* **Propiedad `estado.log_visible`:** Se añadió un booleano de control de flujo dentro del constructor global de estados de la aplicación. Esto asegura que la lógica del software conozca en todo momento el estado del renderizado de la terminal, evitando colisiones lógicas al intentar registrar logs en segundo plano mientras el componente está desmontado.

### 4. Robustez de Rutas de Recursos (`PyInstaller` Ready)

* **Función `resolver_ruta`:** Implementación de un entorno de aislamiento para recursos estáticos (`.ico`, imágenes). Detecta automáticamente si el software se ejecuta en un script de desarrollo o compilado en un binario ejecutable congelado mediante PyInstaller (`sys._MEIPASS`), evitando cierres inesperados por rutas relativas rotas en entornos de producción.

### 5. Multi-Hilos en Conexión e Interacciones Concurrentes

* **Asincronía en UI:** La tarea de conexión física serial (`tarea_conectar`) ahora es delegada por completo a un hilo esclavo (`threading.Thread`) en modo `daemon=True`. Esto elimina por completo el molesto congelamiento momentáneo (*Lag/Freeze*) de la ventana gráfica de CustomTkinter mientras se inicializa y estabiliza el puerto COM de Hardware.

### 6. Sistema Inteligente de Ventanas Emergentes Modales (`CTkToplevel`)

* **Ventana Alerta Duplicada Protegida:** Se agregó la bandera de estado `estado.alerta_abierta`. Si una alarma se activa localmente por software y simultáneamente el hardware envía la trama `ALERTA:ALARMA_ACTIVA`, la interfaz intercepta la segunda solicitud bloqueando la duplicación de ventanas molestas en la pantalla del usuario.
* **Geometría Relativa Dinámica:** Las alertas flotantes ya no se abren en posiciones aleatorias de la pantalla del sistema operativo. Se programó un cálculo matemático dinámico basado en las coordenadas (`winfo_x`, `winfo_y`, `winfo_width`, `winfo_height`) de la aplicación principal para centrar de forma milimétrica la advertencia emergente justo sobre la vista del usuario.

---

## Requisitos e Instalación

Para ejecutar este entorno de control es necesario contar con Python 3.8+ e instalar las dependencias requeridas mediante `pip`:

```bash
pip install customtkinter pyserial

```

Para inicializar la aplicación de control:

```bash
python main.py

```