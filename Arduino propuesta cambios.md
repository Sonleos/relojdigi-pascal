# PROPUESTA DE ACTUALIZACIÓN DE FIRMWARE

## Sistema de Reloj Maestro - Transición a la Versión 2.0 (Arduino)

---

### 1. Resumen Ejecutivo

El presente documento detalla la reingeniería y actualización propuesta para el código del microcontrolador Arduino. La versión base del firmware presentaba severas limitaciones operativas: estaba incompleta (carecía de los ciclos vitales `setup()` y `loop()`), manejaba únicamente **una sola alarma** en memoria y utilizaba esquemas de temporización susceptibles a congelamientos por comunicación serial.

Esta actualización técnica adapta el comportamiento del hardware para que sea 100% compatible con las especificaciones dinámicas de la **Interfaz Gráfica V2.0 en Python**, implementando soporte de multi-alarmas, persistencia indexada en EEPROM y un motor de comunicación asíncrono.

---

### 2. Análisis de Limitaciones Clave en la Versión Anterior

1. **Falta de Estructura de Ejecución:** El código no poseía las funciones nativas de Arduino para inicializar los pines ni para estructurar el ciclo repetitivo de control.
2. **Monoprogramación de Alarmas:** La estructura original solo permitía almacenar y evaluar una alarma a la vez. La terminal en Python requiere la cohabitación de múltiples horarios programados en simultáneo.
3. **Vulnerabilidad en el Multiplexado:** El uso potencial de funciones de lectura serial síncronas o retrasos analógicos interrumpía el refresco continuo de los displays de 7 segmentos, provocando un parpadeo visual severo o el congelamiento total del sistema al recibir ráfagas de datos.

---

### 3. Descripción Detallada de los Cambios Implementados

#### Cambio 1: Transición de Alarma Única a Matriz Dinámica (Multi-Alarmas)

* **Antes:** Se utilizaba una estructura única (`Configuracion`) que sobrescribía los datos del dispositivo cada vez que se enviaba un horario nuevo.
* **Ahora:** Se define la estructura `Alarma` y se declara un arreglo indexado de objetos: `Alarma alarmas[15];`.
* **Detalle Técnico:** Cada elemento de la matriz cuenta con un identificador único numérico (`id`). Esto permite mapear de forma exacta las acciones individuales de la interfaz gráfica, tales como activar/desactivar un interruptor específico o eliminar una fila de la lista visual sin alterar el resto de las alarmas registradas.

#### Cambio 2: Reestructuración del Mapa de Memoria EEPROM

* **Antes:** Se guardaban variables aisladas a partir de la dirección `0`.
* **Ahora:** Se reserva la dirección `0` para la `FIRMA_EEPROM` (verificación de formateo). La dirección `1` almacena un byte dinámico llamado `totalAlarmas`, el cual le indica al microcontrolador cuántos registros válidos existen. A partir de la dirección `2`, se calculan bloques contiguos mediante aritmética de punteros: `addr += sizeof(Alarma);`.
* **Detalle Técnico:** Al encender el equipo, el Arduino inspecciona el byte de la dirección `1`. Si detecta un número válido (entre 0 y 15), realiza un bucle para extraer exclusivamente los bytes correspondientes a las alarmas guardadas, optimizando el tiempo de arranque y evitando lecturas de memoria basura.

#### Cambio 3: Motor de Comunicación Serial Asíncrono (No Bloqueante)

* **Antes:** No se definía un búfer de entrada controlado, lo que forzaba el uso de funciones lentas de lectura de cadenas.
* **Ahora:** Se implementa un arreglo de caracteres global `char bufferSerial[64]` junto con un puntero de posición `indiceBuffer`.
* **Detalle Técnico:** En cada ciclo del `loop()`, el comando `while (Serial.available() > 0)` extrae un solo carácter a la vez. Si no es un salto de línea (`\n` o `\r`), lo almacena en el búfer y libera inmediatamente el procesador para que continúe multiplexando los displays. Solo cuando detecta el fin de la línea, la función `sscanf()` procesa la cadena de manera instantánea en microsegundos, eliminando los retardos en el hardware.

#### Cambio 4: Implementación del Protocolo de Comandos Estructurados V2.0

Para sincronizarse con el backend de Python, se programó un analizador sintáctico en base a las siguientes cabeceras de comunicación serial:

* **`S:` (Sincronizar Tiempo):** Modifica los registros globales de tiempo e inicializa la bandera `relojSincronizado = true`.
* **`A:` (Añadir Alarma):** Inserta un objeto en la matriz de alarmas, calculando el bit de días (`DIAS_MASK`) provisto por Python.
* **`T:` (Alternar Interruptor / Toggle):** Busca el `id` solicitado dentro de la matriz y conmuta su estado (`0` inactivo, `1` activo) sin borrar los datos del horario.
* **`D:` (Eliminar Registro / Delete):** Borra físicamente la alarma desplazando los elementos subsecuentes del arreglo una posición hacia atrás para mantener la integridad de la memoria.
* **`CLEARALL` (Limpiar Todo):** Coloca el contador `totalAlarmas` en `0` y actualiza la EEPROM, ideal para purgas completas del sistema.

#### Cambio 5: Telemetría Activa (Feedback en Tiempo Real hacia Python)

* **Antes:** El Arduino era un receptor pasivo; no informaba su estado interno a la computadora.
* **Ahora:** Al consolidarse el avance de cada segundo (`avanzarUnSegundo()`), si el reloj ya fue sincronizado, el Arduino escribe en el bus serial una cadena formateada con el patrón `INFO:HH:MM:SS:PERIODO:DIA`.
* **Detalle Técnico:** Este cambio es vital para que el hilo lector secundario de Python (`hilo_lector_serial`) capture la ráfaga de datos, parsee las variables de tiempo y actualice dinámicamente los labels gigantes en pantalla, logrando que el segundero de la app avance al unísono con el hardware real.

#### Cambio 6: Lógica de Activación de Sirena basada en Múltiples Criterios

* **Antes:** Se utilizaban banderas individuales (`alarmaYaSunoHoy`) pensadas para un solo evento diario.
* **Ahora:** La función `verificarAlarma()` se ejecuta de manera global cada segundo. Realiza un escaneo por toda la matriz de alarmas activas (`alarmas[i].activa`).
* **Detalle Técnico:** Evalúa simultáneamente tres condiciones: que el bit del día actual esté habilitado en la máscara de bits, que coincidan las horas/minutos/período, y que el segundero actual sea menor a la duración parametrizada (`segundos < alarmas[i].duracion`). Si alguna alarma de la lista cumple los requisitos, la variable general `alarmaActiva` pasa a `true`, encendiendo la sirena en el pin `A0` de forma segura.

#### Cambio 7: Multiplexado de Precisión Basado en Microsegundos

* **Antes:** Se utilizaba una constante global de milisegundos que causaba sutiles parpadeos visuales al haber carga serial pesada.
* **Ahora:** Se migró el control del tiempo visual a microsegundos puros mediante la instrucción `micros()` y la constante `constexpr unsigned long PERIODO_DISPLAY = 1500UL;`.
* **Detalle Técnico:** Al procesar el refresco cada 1500 microsegundos de forma asíncrona dentro del `loop()`, la persistencia de la visión humana percibe los 6 dígitos estables y brillantes, asegurando que ni las comunicaciones seriales entrantes ni la escritura en la EEPROM degraden la calidad visual de la terminal física.

---

### 4. Código Fuente Consolidado del Firmware (V2.0)

El archivo resultante para su compilación e instalación directa a través del entorno de desarrollo es el siguiente:

```cpp
#include <EEPROM.h>
#include <avr/wdt.h>
#include <avr/pgmspace.h>

// Tiempos no bloqueantes para el refresco visual
constexpr unsigned long PERIODO_DISPLAY = 1500UL; 
constexpr byte DIAS_SEMANA = 7;

// Definición de Pines de Hardware
const byte pinesSegmentos[7] = {13, 12, 11, 10, 9, 8, 7};
const byte pinesComunes[6]   = {5, 4, 3, 2, A1, A2};
const byte pinAM             = A3;
const byte pinPM             = A4;
const byte pinAlarmaArduino  = A0;

const byte FIRMA_EEPROM = 0x58; 

// Estructura de Datos para Multi-Alarma
struct Alarma {
  byte id;
  byte hora;
  byte minuto;
  bool esPM;
  byte duracion;
  byte dias;
  bool activa;
};

Alarma alarmas[15]; 
byte totalAlarmas = 0;

// Registros de Tiempo Internos
byte horas = 12;
byte minutos = 0;
byte segundos = 0;
bool esPM = false;
byte diaSemana = 1;
bool relojSincronizado = false;

bool alarmaActiva = false;
unsigned long ultimoSegundo = 0;
unsigned long ultimoMultiplex = 0;
byte displayActivo = 0;

// Búfer Serial para Recepción Asíncrona
char bufferSerial[64];
byte indiceBuffer = 0;

const byte digitos7Seg[10] PROGMEM = {
  0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F
};

void setup() {
  Serial.begin(9600);
  
  for (byte i = 0; i < 7; i++) pinMode(pinesSegmentos[i], OUTPUT);
  for (byte i = 0; i < 6; i++) pinMode(pinesComunes[i], OUTPUT);
  pinMode(pinAM, OUTPUT);
  pinMode(pinPM, OUTPUT);
  pinMode(pinAlarmaArduino, OUTPUT);
  
  apagarDisplays();
  digitalWrite(pinAlarmaArduino, LOW);
  
  cargarConfiguracion(); 
}

void loop() {
  unsigned long ahoraMili = millis();
  unsigned long ahoraMicro = micros();
  
  // Motor del tiempo (1 segundo)
  if (ahoraMili - ultimoSegundo >= 1000UL) {
    ultimoSegundo = ahoraMili;
    avanzarUnSegundo();
    
    // Telemetría hacia la GUI en Python
    if (relojSincronizado) {
      Serial.print(F("INFO:"));
      Serial.print(horas); Serial.print(F(":"));
      Serial.print(minutos); Serial.print(F(":"));
      Serial.print(segundos); Serial.print(F(":"));
      Serial.print(esPM ? F("P") : F("A")); Serial.print(F(":"));
      Serial.println(diaSemana);
    }
  }
  
  // Multiplexado del display (1500 microsegundos)
  if (ahoraMicro - ultimoMultiplex >= PERIODO_DISPLAY) {
    ultimoMultiplex = ahoraMicro;
    actualizarDisplay();
  }
  
  // Accionamiento físico de la sirena
  digitalWrite(pinAlarmaArduino, alarmaActiva ? HIGH : LOW);
  
  // Lector Serial No Bloqueante
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (indiceBuffer > 0) {
        bufferSerial[indiceBuffer] = '\0';
        procesarComando(); 
        indiceBuffer = 0;
      }
    } else if (indiceBuffer < sizeof(bufferSerial) - 1) {
      bufferSerial[indiceBuffer++] = c;
    }
  }
}

void cargarConfiguracion() {
  byte firma = EEPROM.read(0);
  if (firma != FIRMA_EEPROM) {
    EEPROM.write(0, FIRMA_EEPROM);
    totalAlarmas = 0;
    EEPROM.write(1, totalAlarmas);
  } else {
    totalAlarmas = EEPROM.read(1);
    if (totalAlarmas > 15) totalAlarmas = 0;
    int addr = 2;
    for (byte i = 0; i < totalAlarmas; i++) {
      EEPROM.get(addr, alarmas[i]);
      addr += sizeof(Alarma);
    }
  }
}

void guardarAlarmasEEPROM() {
  EEPROM.write(1, totalAlarmas);
  int addr = 2;
  for (byte i = 0; i < totalAlarmas; i++) {
    EEPROM.put(addr, alarmas[i]);
    addr += sizeof(Alarma);
  }
}

void procesarComando() {
  // Sincronización (S:HH:MM:SS:P/A:DIA)
  if (bufferSerial[0] == 'S' && bufferSerial[1] == ':') {
    int h, m, s, d;
    char p;
    if (sscanf(bufferSerial, "S:%d:%d:%d:%c:%d", &h, &m, &s, &p, &d) == 5) {
      horas = h;
      minutos = m;
      segundos = s;
      esPM = (p == 'P');
      diaSemana = d;
      relojSincronizado = true;
      verificarAlarma();
    }
  }
  // Añadir Alarma (A:H:M:P:DUR:DIAS:ACT)
  else if (bufferSerial[0] == 'A' && bufferSerial[1] == ':') {
    int h, m, dur, dias, act;
    char p;
    if (sscanf(bufferSerial, "A:%d:%d:%c:%d:%d:%d", &h, &m, &p, &dur, &dias, &act) == 6) {
      if (totalAlarmas < 15) {
        byte maxId = 0;
        for(byte i = 0; i < totalAlarmas; i++) {
          if(alarmas[i].id > maxId) maxId = alarmas[i].id;
        }
        alarmas[totalAlarmas].id = maxId + 1;
        alarmas[totalAlarmas].hora = h;
        alarmas[totalAlarmas].minuto = m;
        alarmas[totalAlarmas].esPM = (p == 'P');
        alarmas[totalAlarmas].duracion = dur;
        alarmas[totalAlarmas].dias = dias;
        alarmas[totalAlarmas].activa = (act == 1);
        totalAlarmas++;
        guardarAlarmasEEPROM();
        verificarAlarma();
      }
    }
  }
  // Modificar Estado Activo (T:ID:0/1)
  else if (bufferSerial[0] == 'T' && bufferSerial[1] == ':') {
    int id, act;
    if (sscanf(bufferSerial, "T:%d:%d", &id, &act) == 2) {
      for (byte i = 0; i < totalAlarmas; i++) {
        if (alarmas[i].id == id) {
          alarmas[i].activa = (act == 1);
          guardarAlarmasEEPROM();
          verificarAlarma();
          break;
        }
      }
    }
  }
  // Eliminar Alarma Individual (D:ID)
  else if (bufferSerial[0] == 'D' && bufferSerial[1] == ':') {
    int id;
    if (sscanf(bufferSerial, "D:%d", &id) == 1) {
      for (byte i = 0; i < totalAlarmas; i++) {
        if (alarmas[i].id == id) {
          for (byte j = i; j < totalAlarmas - 1; j++) {
            alarmas[j] = alarmas[j + 1];
          }
          totalAlarmas--;
          guardarAlarmasEEPROM();
          verificarAlarma();
          break;
        }
      }
    }
  }
  // Reset Completo (CLEARALL)
  else if (strcmp(bufferSerial, "CLEARALL") == 0) {
    totalAlarmas = 0;
    guardarAlarmasEEPROM();
    alarmaActiva = false;
  }
}

void avanzarUnSegundo() {
  segundos++;
  if (segundos >= 60) {
    segundos = 0;
    minutos++;
    if (minutos >= 60) {
      minutos = 0;
      horas++;
      if (horas > 12) horas = 1;
      if (horas == 12) esPM = !esPM;

      if (horas == 12 && !esPM) {
        diaSemana++;
        if (diaSemana > DIAS_SEMANA) diaSemana = 1;
      }
    }
  }
  verificarAlarma(); 
}

void verificarAlarma() {
  if (!relojSincronizado) {
    alarmaActiva = false;
    return;
  }
  
  byte bitHoy = diaSemana - 1;
  bool encenderSirena = false;

  for (byte i = 0; i < totalAlarmas; i++) {
    if (!alarmas[i].activa) continue;

    bool diaPermitido = bitRead(alarmas[i].dias, bitHoy);
    if (diaPermitido && horas == alarmas[i].hora && minutos == alarmas[i].minuto && esPM == alarmas[i].esPM) {
      if (segundos < alarmas[i].duracion) {
        encenderSirena = true;
      }
    }
  }

  alarmaActiva = encenderSirena;
}

void apagarDisplays() {
  for (byte i = 0; i < 6; i++) digitalWrite(pinesComunes[i], LOW);
}

void mostrarDigito(byte valor) {
  byte patron = pgm_read_byte(&digitos7Seg[valor]);
  for (byte i = 0; i < 7; i++) {
    digitalWrite(pinesSegmentos[i], bitRead(patron, i));
  }
}

void actualizarDisplay() {
  apagarDisplays(); 

  displayActivo = (displayActivo + 1) % 6;
  byte valorMostrar = 0;

  switch (displayActivo) {
    case 0: valorMostrar = horas / 10; break;
    case 1: valorMostrar = horas % 10; break;
    case 2: valorMostrar = minutos / 10; break;
    case 3: valorMostrar = minutos % 10; break;
    case 4: valorMostrar = segundos / 10; break;
    case 5: valorMostrar = segundos % 10; break;
  }

  mostrarDigito(valorMostrar);
  digitalWrite(pinesComunes[displayActivo], HIGH); 

  digitalWrite(pinAM, !esPM ? HIGH : LOW);
  digitalWrite(pinPM, esPM ? HIGH : LOW);
}

```

---

### 5. Conclusión e Impacto de la Actualización

Al implementar los cambios descritos, el hardware deja de operar de manera aislada y se convierte en un periférico inteligente subordinado. La arquitectura asíncrona asegura estabilidad crítica en entornos industriales o escolares, garantizando que el reloj físico nunca pierda precisión ni sufra de parpadeos visuales al comunicarse de manera transparente con el software de control central.