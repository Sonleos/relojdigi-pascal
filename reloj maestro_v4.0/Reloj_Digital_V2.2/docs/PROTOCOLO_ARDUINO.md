# Protocolo Arduino — Reloj Maestro v2.2

Documento de referencia del enlace serie entre la aplicación de PC y el
firmware del Arduino. El puerto se abre a **9600 baudios, 8N1**, con una línea
de texto por comando y terminación `\n`.

La aplicación soporta dos generaciones de firmware y detecta cuál está
conectada en cada conexión.

| Modo | Detección | Capacidades |
| --- | --- | --- |
| `legacy` | Sin respuesta a `PING` | Sincronizar hora y añadir alarmas |
| `v2` | Responde `READY:...` / `PONG` | Todo: crear, editar, borrar, activar, probar y detener la sirena |

---

## 1. Handshake y detección de modo

Al abrir el puerto la app espera **1,8 s** (el Arduino se reinicia al abrir el
puerto por DTR) y envía:

```
PING
```

- Si el firmware responde `READY:2.0` (o cualquier línea que empiece por
  `READY`, o `PONG`) en menos de **2 s**, se usa el modo **v2**.
- Si no hay respuesta, se asume **legacy**. La app sigue funcionando, pero
  avisa de que los borrados, ediciones y desactivaciones no se propagan y que
  la sirena no se puede detener remotamente.

El firmware de referencia también envía `READY:2.0` de forma espontánea al
arrancar; cualquiera de los dos caminos activa el modo v2.

---

## 2. Comandos PC → Arduino

### 2.1 Comunes a legacy y v2

| Comando | Ejemplo | Significado |
| --- | --- | --- |
| `S:HH:MM:SS:A\|P:D` | `S:07:45:00:A:3` | Fija la hora. `HH` en 12 h (01–12), `A`/`P` = AM/PM. `D` = día con **domingo = 1 … sábado = 7**. |
| `A:HH:MM:A\|P:DURACION:MASK` | `A:06:30:A:10:62` | Añade una alarma (formato legacy, sin identificador). |

En modo legacy el Arduino no distingue alarmas por ID: cada `A:` se añade a su
lista interna. Por eso editar, borrar o desactivar en la PC no se refleja en el
hardware hasta reiniciarlo o volver a sincronizar manualmente.

### 2.2 Solo firmware v2

| Comando | Ejemplo | Significado |
| --- | --- | --- |
| `A:ID:HH:MM:A\|P:DURACION:MASK` | `A:3:06:30:A:10:62` | Crea o actualiza la alarma con ese `ID` (1–255). Si ya existe, la reemplaza. Duración en segundos. |
| `D:ID` | `D:3` | Borra la alarma con ese ID. |
| `E:ID:0\|1` | `E:3:0` | Desactiva (`0`) o activa (`1`) la alarma. |
| `C` | `C` | Borra **todas** las alarmas del Arduino. |
| `F:AAAA:MM:DD` | `F:2026:11:07` | Fija la fecha del RTC (año 2000–2099). |
| `T:SEGUNDOS` | `T:5` | Enciende la sirena durante N segundos (prueba). |
| `X` | `X` | Detiene la sirena inmediatamente. |
| `PING` | `PING` | Handshake. El firmware responde `READY:2.0`. |

### 2.3 Máscara de días (`MASK`)

Entero de 7 bits, **bit 0 = domingo** y **bit 6 = sábado**:

| Día | Bit | Valor |
| --- | --- | --- |
| Domingo | 0 | 1 |
| Lunes | 1 | 2 |
| Martes | 2 | 4 |
| Miércoles | 3 | 8 |
| Jueves | 4 | 16 |
| Viernes | 5 | 32 |
| Sábado | 6 | 64 |

Ejemplos:

| Días | Máscara |
| --- | --- |
| Todos | `127` |
| Lunes a viernes | `62` |
| Sábado y domingo | `65` |
| Solo domingo | `1` |
| Solo miércoles | `8` |

> Cuidado: la hora de sincronización usa `D` con domingo = 1, mientras que la
> máscara de alarmas usa bits con domingo = bit 0. Son dos convenciones
> distintas heredadas del firmware original.

### 2.4 Límites del firmware de referencia

- Máximo **12 alarmas** simultáneas (`MAX_ALARMAS`).
- Duración entre **1 y 3600 s**.
- ID entre **1 y 255**.
- Al superar las 12 alarmas el firmware responde `ERR:FULL` a la nueva.
- La app avisa cuando hay más de 12 alarmas activas, aunque las guarda todas
  en disco.

---

## 3. Mensajes Arduino → PC

| Mensaje | Ejemplo | Significado |
| --- | --- | --- |
| `READY:VERSION` | `READY:2.0` | Firmware v2 listo / handshake. |
| `PONG` | `PONG` | Respuesta alternativa al handshake. |
| `INFO:HH:MM:SS:A\|P:D` | `INFO:07:45:12:A:3` | Hora actual, una vez por segundo. 12 h; domingo = 1 … sábado = 7. |
| `ALERTA:ALARMA_ACTIVA` | `ALERTA:ALARMA_ACTIVA` | Una alarma se disparó (formato legacy). |
| `ALERTA:ID:n` | `ALERTA:ID:3` | Alarma con ID 3 disparada (v2). |
| `ACK:...` | `ACK:A` | Comando aceptado. |
| `ERR:...` | `ERR:FULL` | Comando rechazado. Códigos: `PARSE`, `RANGE`, `FULL`, `NOTFOUND`, `CMD`. |

La app tolera también `ALERTA:3` como alias de `ALERTA:ID:3`.

Cualquier línea desconocida se registra en la bitácora en nivel `DEBUG` y no
interrumpe la conexión.

---

## 4. Secuencia de sincronización

Al conectar (o al pulsar **Sincronizar**), la app hace, en este orden:

1. `S:...` — hora actual.
2. `F:...` — fecha (solo v2).
3. `C` — limpia la lista del Arduino (solo v2).
4. `A:ID:...` — reenvía todas las alarmas activas (solo v2).
5. En legacy: envía un `A:...` por alarma activa y muestra el aviso de
   limitaciones.

La operación completa se repite cada **30 minutos** para corregir deriva del
reloj del Arduino. La app también sincroniza tras cualquier alta, edición,
borrado o cambio de estado, y al conectar.

En modo **v2** la sincronización es idempotente: `C` + lista completa deja el
hardware exactamente igual que la PC (el Arduino es la fuente de verdad entre
sincronizaciones y dispara aunque la PC esté apagada).

---

## 5. Alertas y antiduplicados

La alarma puede llegar por dos vías:

- **PC:** el planificador local dispara a la hora exacta (tolerancia 10 s).
- **Arduino:** envía `ALERTA:...` cuando la sirena se enciende.

Para no mostrar dos diálogos por la misma alarma, `AlertManager` deduplica
alertas de la misma alarma durante **90 s**. Si la alerta no trae ID, la app
intenta identificarla con la última trama `INFO` (máximo 5 s de antigüedad) y,
si no, por hora/minuto actuales.

---

## 6. Formato del firmware de referencia

Sketch: [`arduino/reloj_maestro_reference/reloj_maestro_reference.ino`](../arduino/reloj_maestro_reference/reloj_maestro_reference.ino)

- Arduino Uno/Nano, sirena en **D8** (configurable con `PIN_SIRENA`).
- RTC DS3231/DS1307 por I2C (A4/A5). Si no hay RTC, poner `USE_RTC 0`; el reloj
  se mantiene por software y se resincroniza desde la PC.
- Alarmas guardadas en **EEPROM** con magic `0xA5`, versión 2 y checksum XOR.
  Sobreviven a apagones.
- La sirena se apaga sola al cumplirse la duración.
- `SIRENA_ACTIVA_ALTO` permite relé activo por nivel alto o bajo.

Antes de usarlo en producción, adapta:

1. Pin y polaridad de la sirena/relé.
2. Módulo RTC (o desactívalo).
3. Límite de alarmas si tu EEPROM es más pequeña.

### Compilación

1. Abre el `.ino` en Arduino IDE.
2. Instala `RTClib` (Adafruit) si usas RTC.
3. Selecciona placa y puerto, y sube el sketch.
4. Conecta desde la app: debe aparecer **Firmware v2**.

---

## 7. Problemas frecuentes

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| Se detecta `legacy` con firmware nuevo | `PING` no llegó a tiempo | Pulsa **Sincronizar** o reconecta; revisa que el monitor serie esté cerrado. |
| `ERR:FULL` | Más de 12 alarmas activas | Desactiva o borra alarmas. |
| La sirena no se detiene | Modo legacy | Reinicia el Arduino; actualiza a firmware v2. |
| Hora desfasada | RTC sin pila o `USE_RTC 0` | La app resincroniza cada 30 min; revisa la pila del RTC. |
| No aparecen puertos COM | Driver CH340/CP210x ausente | Instala el driver del clon de Arduino. |

---

## 8. Ejemplo de sesión

```
PC  → PING
ARD ← READY:2.0
PC  → S:07:45:00:A:6
ARD ← ACK:S
PC  → F:2026:11:07
ARD ← ACK:F
PC  → C
ARD ← ACK:C
PC  → A:1:06:30:A:10:62
ARD ← ACK:A
ARD ← INFO:07:45:01:A:6
...
ARD ← ALERTA:ID:1
PC  → X
ARD ← ACK:X
```
