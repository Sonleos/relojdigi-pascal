# Reloj Maestro - Terminal de Control (V2.0)

Esta es la interfaz gráfica de usuario (GUI) desarrollada en Python utilizando la librería CustomTkinter. Funciona como el centro de control remoto para un sistema de cronómetro y sirenas automatizadas gestionado por un microcontrolador Arduino.

Este Permite sincronizar la hora en tiempo real, configurar un calendario de alarmas semanales y monitorear el estado del reloj mediante comunicación serial.

## Novedades y Mejoras de la Versión 2.0

La versión 2.0 representa una reoptimización completa del backend gráfico y del sistema de comunicación, enfocada en la estabilidad, persistencia y portabilidad multiplataforma.

A continuación se detallan los cambios clave realizados

### 1. Interfaz Responsiva y Multiplataforma

 1. Maximizado Habilitado Se eliminó la restricción que impedía expandir la aplicación (`app.resizable(True, True)`). Ahora los usuarios pueden maximizar la ventana a pantalla completa.
 2. Layout Elástico Se rediseñó la distribución del espacio usando propiedades adaptativas (`fill=both`, `expand=True`). Al agrandar la ventana, la lista inferior se estira verticalmente para mostrar decenas de alarmas de manera simultánea sin amontonarse.
 3. Protección de Diseño Mínimo Se fijó un límite inferior de redimensión mediante `app.minsize(1100, 710)`. Esto garantiza que, aunque el usuario intente achicar la ventana, los componentes gráficos nunca se encimarán ni se volverán ilegibles.

### 2. Persistencia de Datos (Base de Datos Local JSON)

 1. Historial Protegido En versiones anteriores, cerrar la interfaz de Python borraba las alarmas en pantalla. Ahora se integró el archivo automatizado `alarmas.json`.
 2. Guardado y Carga Automática Al abrir la aplicación, el sistema lee `alarmas.json` para restaurar la lista visual. Al agregar, eliminar o modificar un interruptor, el archivo en disco se actualiza de inmediato de forma invisible para el usuario.

### 3. Optimización de la Arquitectura Concurrente (Hilos de Fondo)

 1. - Interfaz Fluida - Los procesos pesados de escaneo de puertos y conexión ahora corren en hilos secundarios dedicados (`threading.Thread`). La ventana de Python sigue respondiendo clics y arrastres aun si el puerto serial tarda en responder.
 2. - Manejo Seguro de Hilos - Se implementó el método seguro `app.after()` de Tkinter. Todas las modificaciones visuales disparadas desde la lectura del Arduino se programan en la cola del hilo principal, erradicando los cierres inesperados (crashes) por concurrencia.
 3. - Protección Anti-Doble-Clic - Se añadió la bandera interna `estado.conectando` para bloquear peticiones simultáneas de conexión si el usuario pulsa repetidamente el botón Conectar (Esta decisión se tom´para evitar Bugs).

### 4. Rediseño del Protocolo Serial (Python ⇄ Arduino)

Se estandarizó la cadena de texto de control serial para permitir un control granular de las alarmas a través de identificadores únicos (`id`)

 Comando Serial  Acción  Formato del Mensaje
 ---  ---  ---  --- 
 S  Sincronizar hora  `SHHMMSSPERIODODIA`  `S123000P2` (1230 PM, Lunes) 
 A  AñadirEnviar alarma  `AHHMMPERIODODURACIONDIAS_MASKACTIVA`  `A0730A10621` (730 AM, 10s sirena, Lun-Vie, Activa) 
 T  Alternar estado (Toggle)  `TIDESTADO`  `T30` (Apagar temporalmente la alarma ID 3) 
 D  Borrar alarma (Delete)  `DID`  `D5` (Eliminar permanentemente la alarma ID 5) 
 CLEARALL  Limpiar memoria  `CLEARALL`  `CLEARALL` (Vacía por completo las alarmas en el Arduino) 

 -- Nota El parámetro `DIAS_MASK` ahora envía la selección de días compactada en un solo número entero (máscara de bits de 7 posiciones), reduciendo el consumo de búfer en el Arduino.

### 5. Compatibilidad para Compilación Estática

 Resolución Dinámica de Rutas Se añadió la función contenedora `resolver_ruta()`. Esta evalúa si el script corre en entorno de desarrollo o empaquetado bajo el directorio temporal de PyInstaller (`sys._MEIPASS`), permitiendo que el icono institucional (`Reloj_Maestro.ico`) se cargue correctamente en cualquier computadora sin rutas absolutas rotas.

---

## Requisitos del Sistema

Para ejecutar el código fuente o modificar el entorno de desarrollo, asegúrate de contar con

1. Python 3.10 o superior (Recomendado Python 3.123.14).
2. Dependencias del entorno Instala los módulos necesarios mediante la terminal ejecutando
```bash
pip install customtkinter pyserial

```

---

## Instrucciones de Operación de la Interfaz

1. Selección del Canal Conecta tu Arduino por USB. No presiones "Conectar" de inmediato. Abre el menú desplegable Puerto, selecciona manualmente el puerto correspondiente (ej. `COM3` en Windows o `devttyUSB0` en Linux) y presiona "Conectar".

2. Sincronización Una vez establecida la conexión, la interfaz enviará la hora exacta de tu computadora al reloj de forma automática. El panel verde se iluminará en estado ONLINE y el segundero comenzará su marcha continua.

3. Programación Semanal Selecciona la hora, minutos, periodo (AMPM), la duración en segundos que debe sonar la sirena, y marca los días de la semana deseados. Al pulsar "Guardar Alarma", esta se registrará en tu PC y se transmitirá inmediatamente al Arduino.

4. Respaldo Rápido Si desconectas el hardware o deseas clonar la configuración en otro dispositivo, el botón Reenviar Alarmas al Arduino vaciará la memoria del chip y volverá a inyectar toda tu base de datos local en segundos.