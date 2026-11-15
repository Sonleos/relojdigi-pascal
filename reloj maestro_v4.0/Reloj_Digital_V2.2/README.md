# Reloj Maestro v2.2

Terminal de control de escritorio para programar alarmas semanales de un reloj
digital basado en Arduino. La PC programa y supervisa; el Arduino guarda las
alarmas en EEPROM y dispara la sirena **aunque la PC esté apagada**.

Interfaz oscura en CustomTkinter con:

- Reloj local y hora reportada por el hardware.
- Próxima alarma con cuenta atrás en vivo.
- Alta, edición, activación y borrado de alarmas (con confirmación).
- Sincronización de hora/fecha y de todas las alarmas con el Arduino.
- Prueba y parada remota de la sirena (firmware v2).
- Sonido de alerta local en la PC como respaldo.
- Formato de hora 12 h / 24 h.
- Bitácora en pantalla y en archivo con rotación.

---

## Requisitos

- Windows 10/11 (probado en Windows con Python 3.14).
- Python 3.10 o superior.
- `customtkinter`, `pyserial`, `Pillow` (dependencia de CustomTkinter).
- Arduino con firmware compatible (ver [`docs/PROTOCOLO_ARDUINO.md`](docs/PROTOCOLO_ARDUINO.md)).

Instalación de dependencias:

```powershell
python -m pip install customtkinter pyserial
```

Para empaquetar, además:

```powershell
python -m pip install pyinstaller
```

---

## Ejecución

Desde la carpeta del proyecto:

```powershell
python reloj_maestro_v2.2.py
```

o, equivalentemente:

```powershell
python -m reloj_maestro
```

`reloj_maestro_v2.2.py` es solo un lanzador compatible con PyInstaller.

### Uso básico

1. Selecciona el puerto COM y pulsa **Conectar**.
2. La app detecta el firmware (`legacy` o `v2`) y sincroniza automáticamente.
3. Programa alarmas con hora, duración de la sirena y días de la semana.
4. Usa **Probar sirena** / **Detener** para verificar el hardware.
5. La app resincroniza la hora cada 30 minutos y tras cada cambio.

### Apariencia

El selector **Tema** de la cabecera alterna entre modo **Claro** y **Oscuro** en
caliente, sin reiniciar. La preferencia se guarda en `Settings.appearance` y se
restaura al volver a abrir la aplicación.

- Los tokens de diseño (colores, tipografía, espaciados y estilos de widgets)
  viven en `reloj_maestro/ui/theme.py`.
- Cada color se declara como par `(claro, oscuro)`, por lo que CustomTkinter
  cambia toda la interfaz sin reconstruir paneles.
- Para adaptar la app a los colores de un cliente o instituto basta con editar
  las paletas `LIGHT` y `DARK` de ese archivo; el resto de la interfaz usa
  nombres semánticos (`ACCENT`, `SURFACE`, `TEXT`, etc.).

---

## Estructura del proyecto

```
Reloj_Digital_V2.2/
├─ reloj_maestro_v2.2.py        # lanzador fino (entrada de PyInstaller)
├─ reloj_maestro/
│  ├─ app.py                    # controlador y punto de entrada real
│  ├─ config.py                 # constantes y rutas
│  ├─ domain/
│  │  ├─ models.py              # Alarm, Settings, días y validaciones
│  │  └─ scheduler.py           # disparo sin deriva y próxima alarma
│  ├─ protocol/
│  │  └─ arduino.py             # comandos y parseo legacy/v2
│  ├─ services/
│  │  ├─ storage.py             # JSON atómico + cuarentena de corruptos
│  │  ├─ serial_link.py         # hilo lector, cola de eventos, handshake
│  │  ├─ sound.py               # sonido local de alerta
│  │  └─ activity_log.py        # bitácora rotativa
│  └─ ui/
│     ├─ theme.py               # paletas claro/oscuro, tokens y estilos
│     ├─ components.py          # títulos de sección y píldoras de estado
│     ├─ main_window.py         # ventana, cabecera y barra de estado
│     ├─ clock_panel.py         # reloj y próxima alarma
│     ├─ connection_panel.py    # puerto, estado y sincronización
│     ├─ alarm_panel.py         # formulario y lista de alarmas
│     ├─ log_panel.py           # visor de bitácora
│     └─ alert_dialog.py        # diálogo de alarma y antiduplicados
├─ arduino/
│  └─ reloj_maestro_reference/  # firmware de referencia v2 (EEPROM + RTC)
├─ docs/
│  └─ PROTOCOLO_ARDUINO.md      # protocolo serie completo
├─ tests/                       # 31 pruebas unitarias
├─ backup/                      # copias de los archivos originales
├─ reloj_maestro_v2.2.spec      # configuración de PyInstaller
└─ compilador/                  # script de Inno Setup
```

### Arquitectura

- **Dominio:** `Alarm`, `Settings`, reglas de días/horas y `AlarmScheduler`.
  Sin dependencias de UI ni de hardware.
- **Protocolo:** funciones puras que construyen comandos y parsean respuestas.
- **Servicios:** persistencia, enlace serie, sonido y bitácora.
- **UI:** paneles de CustomTkinter; no contienen lógica de negocio.
- **Controlador (`AppController`):** conecta todo, consume los eventos del
  hilo serie en el hilo de Tkinter y coordina la sincronización.

El hilo lector del puerto serie nunca toca Tkinter: publica eventos en una
`queue.Queue` que el controlador consume con `after()`.

---

## Datos y bitácora

Por defecto se guardan junto al ejecutable (o junto al proyecto en modo
fuente):

| Archivo | Contenido |
| --- | --- |
| `reloj_maestro_config.json` | Alarmas y ajustes (JSON atómico). |
| `reloj_maestro.log` | Bitácora (`reloj_maestro.log.1`, `.2` al rotar). |

Si esa carpeta no es escribible (por ejemplo, `Program Files`), se usa
automáticamente `%APPDATA%\RelojMaestro`. Como último recurso, la carpeta
temporal del sistema.

Si el JSON está corrupto, se renombra a `reloj_maestro_config.bad_AAAAMMDD_HHMMSS.json`
y la app arranca con configuración vacía en lugar de fallar.

---

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Cubren modelos y validaciones, planificador (disparo único y gracia),
protocolo (comandos, parseo, formatos) y persistencia (guardado atómico,
corrupción y reparación de IDs).

---

## Empaquetado

### PyInstaller

```powershell
python -m PyInstaller reloj_maestro_v2.2.spec --noconfirm
```

Genera `dist/reloj_maestro_v2.2.exe`. El `.spec` ya incluye el icono
`Reloj_Maestro.ico`, los datos de `customtkinter` y el lanzador correcto.

> En instalaciones de Python 3.14 que traen Tcl/Tk dentro de `libtcl*.zip` y
> `libtk*.zip` (por ejemplo, distribuciones portable/zipfs), el `.spec`
> extrae esos archivos automáticamente para que el `.exe` con ventana
> arranque. En instalaciones normales no hace nada especial.

### Instalador

El script de Inno Setup existente está en
`compilador/reloj_digital_v2.2_compilador.iss`. Compílalo con Inno Setup 6
después de generar el `.exe`:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" compilador\reloj_digital_v2.2_compilador.iss
```

Genera `Setup_RelojDigitalV2.2.exe` en el escritorio; cópialo junto al
proyecto si quieres distribuirlo desde ahí.

---

## Compatibilidad de firmware

| Modo | Qué se puede hacer |
| --- | --- |
| `v2` | Sincronizar hora/fecha, crear/editar/borrar/activar alarmas, probar y detener la sirena. |
| `legacy` | Sincronizar hora y **añadir** alarmas. Los borrados, ediciones y desactivaciones no se propagan; la sirena no se puede detener remotamente. La app lo advierte en la bitácora. |

Para aprovechar todas las funciones, usa el firmware de referencia
[`arduino/reloj_maestro_reference/reloj_maestro_reference.ino`](arduino/reloj_maestro_reference/reloj_maestro_reference.ino)
y adapta pines, RTC y polaridad de la sirena a tu montaje.

Detalles completos del protocolo, máscara de días, handshake y ejemplos:
[`docs/PROTOCOLO_ARDUINO.md`](docs/PROTOCOLO_ARDUINO.md).

---

## Limitaciones conocidas

- Las alarmas son **semanales recurrentes**; no hay alarmas de fecha única.
- El firmware de referencia admite **12 alarmas**; la app guarda más, pero
  avisa cuando no caben en el hardware.
- En modo legacy el hardware puede conservar alarmas borradas hasta reiniciar.
- La detección de firmware espera 2 s; si el Arduino tarda más en arrancar,
  puede detectarse como legacy. Reconectar o pulsar **Sincronizar** lo corrige.
- El sonido local depende de los recursos de Windows.
