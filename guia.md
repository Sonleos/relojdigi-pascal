# -- CADA CARPETA ES UNA VERSIÓN DISTINTA DEL RELOJ MAESTRO --

# Documentación Técnica: Proyecto "Reloj Maestro"

**Módulo:** Terminal de Control (Software de Escritorio)
**Tecnología:** Python 3, CustomTkinter, PySerial
**Institución Académica:** I.U.T. "PASCAL"

## 1. Descripción General del Sistema

La **Terminal de Control del Reloj Maestro** es una aplicación de escritorio diseñada para gestionar, monitorear y sincronizar un sistema de alarmas basado en hardware (Arduino). Actúa como la interfaz principal (`Frontend`) interactuando bidireccionalmente con el microcontrolador a través de comunicación serial.

El sistema permite establecer la hora del hardware, programar rutinas de alarmas semanales y mantener un registro (log) de todos los eventos del sistema. Además, cuenta con un sistema de redundancia local que activa alertas en pantalla de forma independiente si el hardware falla o se desconecta.

## 2. Arquitectura de la Interfaz (CustomTkinter)

La interfaz gráfica (GUI) está construida de manera modular y dividida en tres bloques principales:

| Bloque | Componentes Principales | Función |
| --- | --- | --- |
| **Superior** | Reloj Digital y Panel Serial | Muestra la hora real dictada por el Arduino. Gestiona la búsqueda de puertos COM, conexión/desconexión y sincronización manual. |
| **Central** | Formulario de Configuración | Permite seleccionar hora, minuto, AM/PM, duración de la sirena y los días de ejecución (de domingo a sábado). |
| **Inferior** | Lista de Alarmas y Terminal | Muestra visualmente las alarmas guardadas (con opciones de activar/desactivar y borrar) y un *Log* de eventos en tiempo real. |

## 3. Protocolo de Comunicación Bidireccional (Serial)

El corazón del proyecto es la forma en que Python y Arduino "hablan" entre sí. Se ha establecido un protocolo basado en cadenas de texto (*strings*) delimitadas por dos puntos (`:`).

### Transmisión (TX) - De Python a Arduino

* **Comando de Sincronización de Hora:** `S:{hora}:{minuto}:{segundo}:{AM/PM}:{dia_semana}`
* *Ejemplo:* `S:10:30:00:A:2` (Establece el reloj en 10:30:00 AM, Lunes).


* **Comando de Nueva Alarma:** `A:{hora}:{minuto}:{AM/PM}:{duracion}:{mascara_dias}`
* *Ejemplo:* `A:07:00:A:15:62` (Alarma a las 7:00 AM por 15 seg. El `62` es la representación decimal de los bits activados para los días de semana).



### Recepción (RX) - De Arduino a Python

* **Latido de Tiempo (Heartbeat):** `INFO:{hora}:{minuto}:{segundo}:{AM/PM}:{dia_semana}`
* Actualiza el reloj digital en pantalla en tiempo real.


* **Disparador de Alerta:** `ALERTA:ALARMA_ACTIVA`
* Desencadena la función `mostrar_alerta_emergente()` en Python, notificando al usuario que la sirena física está sonando.



## 4. Lógica Clave del Código Fuente

### 4.1 Manejo de Estado (`AppState`)

Para evitar el uso de variables globales desordenadas, el código encapsula todo el estado de la aplicación en la clase `AppState`. Esto incluye el objeto de la conexión serial (`self.arduino`), la lista de alarmas en memoria (`self.alarmas`) y banderas booleanas para la interfaz.

### 4.2 Hilos de Ejecución (Threading)

La función `hilo_lector_serial()` corre en un hilo secundario (daemon). Esto es vital porque leer el puerto serial (`estado.arduino.readline()`) es una operación de bloqueo. Si se hiciera en el hilo principal, la interfaz gráfica se congelaría completamente.

### 4.3 Máscara de Bits para Días de la Semana

En lugar de enviar un arreglo pesado de 7 elementos booleanos al Arduino, Python condensa los días seleccionados en un solo número entero (1 byte) utilizando operadores bit a bit (`|` y `<<`).
La función auxiliar `bitRead(valor, bit)` permite luego a la interfaz gráfica desempaquetar este número para mostrar correctamente en pantalla qué días están activos.

### 4.4 Resiliencia y Redundancia Local

La función `monitor_alarmas_locales()` se ejecuta cíclicamente cada segundo (`app.after(1000, ...)`). Su propósito es verificar si la hora de la computadora coincide con alguna alarma guardada. Si el Arduino se desconecta o sufre un corte de energía, Python actuará como respaldo, emitiendo la alerta en el monitor de la computadora para que el evento no pase desapercibido.

### 4.5 Preparación para Producción

El código incluye la función `resolver_ruta()`, que utiliza la variable `sys._MEIPASS`. Esto significa que el código ya está preparado para ser compilado en un ejecutable cerrado (`.exe`) mediante PyInstaller, permitiendo empaquetar el ícono `Reloj_Maestro.ico` dentro del mismo archivo sin que se rompa la ruta al ejecutarlo en otras computadoras.

---