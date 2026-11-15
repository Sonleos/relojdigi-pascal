/*
  Reloj Maestro - Firmware de referencia v2.0
  ===========================================
  Este sketch es una REFERENCIA para el protocolo documentado en
  docs/PROTOCOLO_ARDUINO.md. Adáptalo a tu hardware real (pines, módulo
  de reloj y tipo de relé/zumbador).

  Hardware asumido:
    - Arduino Uno/Nano.
    - Relé, zumbador o sirena en PIN_SIRENA (por defecto D8).
    - RTC DS3231 por I2C (A4 = SDA, A5 = SCL). Si no tienes RTC, pon
      USE_RTC 0: el reloj se sincroniza desde la PC y se desvía con el
      tiempo, pero las alarmas siguen guardadas en EEPROM.
    - Memoria EEPROM interna para conservar hasta 12 alarmas apagando
      y encendiendo el Arduino.

  Comandos (una línea por comando, 9600 baudios):
    PING                          -> READY:2.0
    F:AAAA:MM:DD                  -> fija la fecha (solo v2)
    S:HH:MM:SS:A|P:D              -> fija la hora (D: domingo=1 ... sábado=7)
    A:ID:HH:MM:A|P:DURACION:MASK  -> crea/actualiza alarma
    D:ID                          -> elimina alarma
    E:ID:0|1                      -> desactiva/activa alarma
    C                             -> borra todas las alarmas
    T:SEGUNDOS                    -> prueba la sirena
    X                             -> detiene la sirena

  Respuestas:
    READY:2.0
    INFO:HH:MM:SS:A|P:D           -> cada segundo
    ALERTA:ALARMA_ACTIVA          -> al dispararse una alarma
    ACK:... / ERR:...
*/

#include <EEPROM.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

// ------------------------- Configuración -------------------------
#define PIN_SIRENA 8
#define SIRENA_ACTIVA_ALTO 1      // 1 = HIGH enciende; 0 = LOW enciende
#define USE_RTC 1                 // 1 = DS3231/DS1307 con RTClib
#define MAX_ALARMAS 12
#define MAX_DURACION 3600
#define BAUDIOS 9600

#if USE_RTC
#include <RTClib.h>
RTC_DS3231 rtc;  // Cambia a RTC_DS1307 si usas ese módulo.
bool rtcOk = false;
#else
const bool rtcOk = false;
#endif

// ------------------------- Estructuras ---------------------------
struct Alarma {
  uint8_t id;
  uint8_t hora;      // 0..23
  uint8_t minuto;    // 0..59
  uint16_t duracion; // segundos
  uint8_t dias;      // bit0 domingo ... bit6 sábado
  uint8_t activa;
};

struct Memoria {
  uint8_t magic;
  uint8_t version;
  uint8_t count;
  Alarma alarmas[MAX_ALARMAS];
  uint8_t checksum;
};

struct HoraActual {
  uint8_t hora;
  uint8_t minuto;
  uint8_t segundo;
  uint8_t dia;  // 0 = domingo ... 6 = sábado
};

Memoria mem;
uint32_t ultimoDisparo[MAX_ALARMAS];
uint32_t sirenaFin = 0;
bool sirenaActiva = false;
uint32_t ultimoInfoMillis = 0;

// Reloj por software (se usa si no hay RTC o si el RTC falla).
uint8_t swHora = 0;
uint8_t swMinuto = 0;
uint8_t swSegundo = 0;
uint8_t swDia = 0;
uint32_t swUltimoMillis = 0;

char comando[64];
uint8_t comandoLen = 0;

// ------------------------- EEPROM -------------------------------
uint8_t calcularChecksum() {
  const uint8_t *p = (const uint8_t *)&mem;
  uint8_t sum = 0;
  for (size_t i = 0; i < offsetof(Memoria, checksum); ++i) {
    sum ^= p[i];
  }
  return sum;
}

void guardarMemoria() {
  mem.checksum = calcularChecksum();
  EEPROM.put(0, mem);
}

void cargarMemoria() {
  EEPROM.get(0, mem);
  if (mem.magic != 0xA5 || mem.version != 2 || mem.count > MAX_ALARMAS ||
      mem.checksum != calcularChecksum()) {
    memset(&mem, 0, sizeof(mem));
    mem.magic = 0xA5;
    mem.version = 2;
    mem.count = 0;
    guardarMemoria();
  }
  for (uint8_t i = 0; i < MAX_ALARMAS; ++i) {
    ultimoDisparo[i] = 0;
  }
}

// ------------------------- Reloj --------------------------------
uint8_t diaSemana(int y, int m, int d) {
  // Sakamoto: 0 = domingo ... 6 = sábado.
  static const int t[] = {0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4};
  if (m < 3) {
    y -= 1;
  }
  int w = (y + y / 4 - y / 100 + y / 400 + t[m - 1] + d) % 7;
  if (w < 0) {
    w += 7;
  }
  return (uint8_t)w;
}

HoraActual leerHora() {
  HoraActual t;
#if USE_RTC
  if (rtcOk) {
    DateTime ahora = rtc.now();
    t.hora = ahora.hour();
    t.minuto = ahora.minute();
    t.segundo = ahora.second();
    t.dia = ahora.dayOfTheWeek();
    return t;
  }
#endif
  t.hora = swHora;
  t.minuto = swMinuto;
  t.segundo = swSegundo;
  t.dia = swDia;
  return t;
}

void ajustarHora(uint8_t hora, uint8_t minuto, uint8_t segundo, uint8_t dia) {
#if USE_RTC
  if (rtcOk) {
    DateTime actual = rtc.now();
    rtc.adjust(DateTime(actual.year(), actual.month(), actual.day(), hora, minuto, segundo));
  }
#endif
  swHora = hora;
  swMinuto = minuto;
  swSegundo = segundo;
  swDia = dia;
  swUltimoMillis = millis();
}

void ajustarFecha(int year, int month, int day) {
#if USE_RTC
  if (rtcOk) {
    DateTime actual = rtc.now();
    rtc.adjust(DateTime(year, month, day, actual.hour(), actual.minute(), actual.second()));
  }
#endif
  swDia = diaSemana(year, month, day);
}

void actualizarRelojSoftware() {
  uint32_t ahora = millis();
  while (ahora - swUltimoMillis >= 1000UL) {
    swUltimoMillis += 1000UL;
    if (++swSegundo >= 60) {
      swSegundo = 0;
      if (++swMinuto >= 60) {
        swMinuto = 0;
        if (++swHora >= 24) {
          swHora = 0;
          swDia = (swDia + 1) % 7;
        }
      }
    }
  }
}

// ------------------------- Sirena -------------------------------
void apagarSirena() {
  digitalWrite(PIN_SIRENA, SIRENA_ACTIVA_ALTO ? LOW : HIGH);
  sirenaActiva = false;
}

void encenderSirena(uint16_t segundos) {
  if (segundos == 0) {
    return;
  }
  digitalWrite(PIN_SIRENA, SIRENA_ACTIVA_ALTO ? HIGH : LOW);
  sirenaActiva = true;
  sirenaFin = millis() + ((uint32_t)segundos * 1000UL);
}

void actualizarSirena() {
  if (sirenaActiva && (int32_t)(millis() - sirenaFin) >= 0) {
    apagarSirena();
  }
}

// ------------------------- Alarmas ------------------------------
int buscarAlarma(uint8_t id) {
  for (uint8_t i = 0; i < mem.count; ++i) {
    if (mem.alarmas[i].id == id) {
      return (int)i;
    }
  }
  return -1;
}

void limpiarClavesDisparo() {
  for (uint8_t i = 0; i < MAX_ALARMAS; ++i) {
    ultimoDisparo[i] = 0;
  }
}

bool guardarAlarma(uint8_t id, uint8_t hora, uint8_t minuto, uint16_t duracion, uint8_t dias) {
  if (id == 0 || hora > 23 || minuto > 59 || duracion == 0 ||
      duracion > MAX_DURACION || dias == 0 || dias > 0x7F) {
    return false;
  }

  int idx = buscarAlarma(id);
  if (idx < 0) {
    if (mem.count >= MAX_ALARMAS) {
      return false;
    }
    idx = mem.count;
    mem.count++;
  }

  mem.alarmas[idx].id = id;
  mem.alarmas[idx].hora = hora;
  mem.alarmas[idx].minuto = minuto;
  mem.alarmas[idx].duracion = duracion;
  mem.alarmas[idx].dias = dias;
  mem.alarmas[idx].activa = 1;
  limpiarClavesDisparo();
  guardarMemoria();
  return true;
}

bool borrarAlarma(uint8_t id) {
  int idx = buscarAlarma(id);
  if (idx < 0) {
    return false;
  }
  for (uint8_t i = (uint8_t)idx; i + 1 < mem.count; ++i) {
    mem.alarmas[i] = mem.alarmas[i + 1];
  }
  mem.count--;
  limpiarClavesDisparo();
  guardarMemoria();
  return true;
}

bool activarAlarma(uint8_t id, bool activa) {
  int idx = buscarAlarma(id);
  if (idx < 0) {
    return false;
  }
  mem.alarmas[idx].activa = activa ? 1 : 0;
  limpiarClavesDisparo();
  guardarMemoria();
  return true;
}

void limpiarAlarmas() {
  mem.count = 0;
  limpiarClavesDisparo();
  guardarMemoria();
}

void revisarAlarmas(const HoraActual &t) {
  for (uint8_t i = 0; i < mem.count; ++i) {
    Alarma &a = mem.alarmas[i];
    if (!a.activa) {
      continue;
    }
    if ((a.dias & (1 << t.dia)) == 0) {
      continue;
    }
    if (a.hora != t.hora || a.minuto != t.minuto) {
      continue;
    }

    uint32_t clave = ((uint32_t)t.dia * 1440UL) + ((uint32_t)t.hora * 60UL) + t.minuto + 1UL;
    if (ultimoDisparo[i] == clave) {
      continue;
    }
    ultimoDisparo[i] = clave;

    encenderSirena(a.duracion);
    Serial.println(F("ALERTA:ALARMA_ACTIVA"));
  }
}

// ------------------------- Salida INFO --------------------------
void enviarInfo(const HoraActual &t) {
  uint32_t ahora = millis();
  if (ahora - ultimoInfoMillis < 1000UL) {
    return;
  }
  ultimoInfoMillis = ahora;

  int hora12 = t.hora % 12;
  if (hora12 == 0) {
    hora12 = 12;
  }
  char periodo = (t.hora >= 12) ? 'P' : 'A';
  char buf[32];
  snprintf(buf, sizeof(buf), "INFO:%02d:%02d:%02d:%c:%d",
           hora12, (int)t.minuto, (int)t.segundo, periodo, (int)t.dia + 1);
  Serial.println(buf);
}

// ------------------------- Comandos -----------------------------
void procesarComando(char *cmd) {
  while (*cmd == ' ') {
    ++cmd;
  }
  size_t len = strlen(cmd);
  while (len > 0 && cmd[len - 1] == ' ') {
    cmd[--len] = '\0';
  }
  if (len == 0) {
    return;
  }

  if (strcmp(cmd, "PING") == 0) {
    Serial.println(F("READY:2.0"));
    return;
  }

  if (strcmp(cmd, "C") == 0 || strcmp(cmd, "C:") == 0) {
    limpiarAlarmas();
    Serial.println(F("ACK:C"));
    return;
  }

  if (strcmp(cmd, "X") == 0 || strcmp(cmd, "X:") == 0) {
    apagarSirena();
    Serial.println(F("ACK:X"));
    return;
  }

  if (cmd[0] == 'F' && cmd[1] == ':') {
    int year, month, day;
    if (sscanf(cmd, "F:%d:%d:%d", &year, &month, &day) == 3 &&
        year >= 2000 && year <= 2099 && month >= 1 && month <= 12 &&
        day >= 1 && day <= 31) {
      ajustarFecha(year, month, day);
      Serial.println(F("ACK:F"));
    } else {
      Serial.println(F("ERR:RANGE"));
    }
    return;
  }

  if (cmd[0] == 'S' && cmd[1] == ':') {
    int h, m, s, d;
    char p;
    if (sscanf(cmd, "S:%d:%d:%d:%c:%d", &h, &m, &s, &p, &d) == 5 &&
        h >= 1 && h <= 12 && m >= 0 && m <= 59 && s >= 0 && s <= 59 &&
        (p == 'A' || p == 'P') && d >= 1 && d <= 7) {
      int hora24 = (h % 12) + ((p == 'P') ? 12 : 0);
      ajustarHora((uint8_t)hora24, (uint8_t)m, (uint8_t)s, (uint8_t)(d - 1));
      Serial.println(F("ACK:S"));
    } else {
      Serial.println(F("ERR:PARSE"));
    }
    return;
  }

  if (cmd[0] == 'A' && cmd[1] == ':') {
    int id, h, m, duracion, mask;
    char p;
    if (sscanf(cmd, "A:%d:%d:%d:%c:%d:%d", &id, &h, &m, &p, &duracion, &mask) == 6 &&
        id >= 1 && id <= 255 && h >= 1 && h <= 12 && m >= 0 && m <= 59 &&
        (p == 'A' || p == 'P') && duracion > 0 && duracion <= MAX_DURACION &&
        mask >= 1 && mask <= 0x7F) {
      int hora24 = (h % 12) + ((p == 'P') ? 12 : 0);
      if (guardarAlarma((uint8_t)id, (uint8_t)hora24, (uint8_t)m,
                        (uint16_t)duracion, (uint8_t)mask)) {
        Serial.println(F("ACK:A"));
      } else {
        Serial.println(F("ERR:FULL"));
      }
    } else {
      Serial.println(F("ERR:RANGE"));
    }
    return;
  }

  if (cmd[0] == 'D' && cmd[1] == ':') {
    int id;
    if (sscanf(cmd, "D:%d", &id) == 1 && id >= 1 && id <= 255) {
      if (borrarAlarma((uint8_t)id)) {
        Serial.println(F("ACK:D"));
      } else {
        Serial.println(F("ERR:NOTFOUND"));
      }
    } else {
      Serial.println(F("ERR:PARSE"));
    }
    return;
  }

  if (cmd[0] == 'E' && cmd[1] == ':') {
    int id, activa;
    if (sscanf(cmd, "E:%d:%d", &id, &activa) == 2 && id >= 1 && id <= 255) {
      if (activarAlarma((uint8_t)id, activa != 0)) {
        Serial.println(F("ACK:E"));
      } else {
        Serial.println(F("ERR:NOTFOUND"));
      }
    } else {
      Serial.println(F("ERR:PARSE"));
    }
    return;
  }

  if (cmd[0] == 'T' && cmd[1] == ':') {
    int segundos;
    if (sscanf(cmd, "T:%d", &segundos) == 1 &&
        segundos > 0 && segundos <= MAX_DURACION) {
      encenderSirena((uint16_t)segundos);
      Serial.println(F("ACK:T"));
    } else {
      Serial.println(F("ERR:RANGE"));
    }
    return;
  }

  Serial.println(F("ERR:CMD"));
}

void leerSerial() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (comandoLen > 0) {
        comando[comandoLen] = '\0';
        procesarComando(comando);
        comandoLen = 0;
      }
    } else if (comandoLen < sizeof(comando) - 1) {
      comando[comandoLen++] = c;
    }
  }
}

// ------------------------- Setup / loop -------------------------
void setup() {
  Serial.begin(BAUDIOS);
  pinMode(PIN_SIRENA, OUTPUT);
  apagarSirena();
  cargarMemoria();

#if USE_RTC
  rtcOk = rtc.begin();
  if (rtcOk && rtc.lostPower()) {
    // Fecha/hora de compilación como respaldo; la PC la corrige al conectar.
    rtc.adjust(DateTime(__DATE__, __TIME__));
  }
#endif

  Serial.println(F("READY:2.0"));
}

void loop() {
  leerSerial();

  if (!rtcOk) {
    actualizarRelojSoftware();
  }

  HoraActual ahora = leerHora();
  actualizarSirena();
  revisarAlarmas(ahora);
  enviarInfo(ahora);
}
