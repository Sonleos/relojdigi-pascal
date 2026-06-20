#include <EEPROM.h>
#include <avr/wdt.h>
#include <avr/pgmspace.h>

// Ajustado para mantener estabilidad visual frente a la carga serial en Proteus
constexpr unsigned long PERIODO_DISPLAY = 1500UL; // 1500 microsegundos para multiplexado
constexpr byte DIAS_SEMANA = 7;

const byte pinesSegmentos[7] = {13, 12, 11, 10, 9, 8, 7};
const byte pinesComunes[6]   = {5, 4, 3, 2, A1, A2};
const byte pinAM             = A3;
const byte pinPM             = A4;
const byte pinAlarmaArduino  = A0;

const byte FIRMA_EEPROM = 0x58;

struct Configuracion {
  byte firma;
  byte alarmaHora;
  byte alarmaMinuto;
  bool alarmaPM;
  byte alarmaDuracion;
  byte alarmaDias;
  bool alarmaHabilitada;
};

Configuracion config;

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

char bufferSerial[64];
byte indiceBuffer = 0;

const byte digitos7Seg[10] PROGMEM = {
  0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F
};

// ==========================================
// FUNCIONES DE CONFIGURACIÓN Y EEPROM
// ==========================================
void cargarConfiguracion() {
  EEPROM.get(0, config);
  if (config.firma != FIRMA_EEPROM) {
    config.firma = FIRMA_EEPROM;
    config.alarmaHora = 7;
    config.alarmaMinuto = 30;
    config.alarmaPM = false;
    config.alarmaDuracion = 10;
    config.alarmaDias = 0x7F; // Todos los días activos por defecto
    config.alarmaHabilitada = true;
    EEPROM.put(0, config);
  }
}

void guardarConfiguracion() {
  EEPROM.put(0, config);
}

// ==========================================
// LÓGICA DEL RELOJ Y ALARMA
// ==========================================
void verificarAlarma() {
  if (!relojSincronizado || !config.alarmaHabilitada) return;
  
  byte bitHoy = diaSemana - 1;
  bool diaPermitido = bitRead(config.alarmaDias, bitHoy);

  if (diaPermitido && horas == config.alarmaHora && minutos == config.alarmaMinuto && esPM == config.alarmaPM) {
    if (segundos < config.alarmaDuracion) {
      if (!alarmaActiva) {
        alarmaActiva = true;
        Serial.println(F("ALERTA:ALARMA_ACTIVA")); // Dispara el Pop-up en Python
      }
    } else {
      alarmaActiva = false;
    }
  } else {
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
    verificarAlarma();
  }
}

void actualizarAlarma() {
  digitalWrite(pinAlarmaArduino, alarmaActiva ? HIGH : LOW);
}

// ==========================================
// CONTROL DEL DISPLAY DE 7 SEGMENTOS
// ==========================================
void apagarDisplays() {
  for (byte i = 0; i < 6; i++) digitalWrite(pinesComunes[i], LOW);
}

void mostrarDigito(byte valor) {
  byte patron = pgm_read_byte(&digitos7Seg[valor]);
  for (byte i = 0; i < 7; i++) {
    digitalWrite(pinesSegmentos[i], bitRead(patron, i));
  }
}

void multiplexarDisplays() {
  apagarDisplays();
  
  byte valorAMostrar = 0;
  switch (displayActivo) {
    case 0: valorAMostrar = horas / 10; break;
    case 1: valorAMostrar = horas % 10; break;
    case 2: valorAMostrar = minutos / 10; break;
    case 3: valorAMostrar = minutos % 10; break;
    case 4: valorAMostrar = segundos / 10; break;
    case 5: valorAMostrar = segundos % 10; break;
  }
  
  mostrarDigito(valorAMostrar);
  digitalWrite(pinesComunes[displayActivo], HIGH);
  
  displayActivo++;
  if (displayActivo >= 6) displayActivo = 0;
}

// ==========================================
// RECEPCIÓN SERIAL (COMUNICACIÓN CON PYTHON)
// ==========================================
void procesarComando() {
  if (bufferSerial[0] == 'S') { // Sincronizar -> S:HH:MM:SS:A/P:DIA
    int h, m, s, d;
    char p;
    if (sscanf(bufferSerial, "S:%d:%d:%d:%c:%d", &h, &m, &s, &p, &d) == 5) {
      horas = h;
      minutos = m;
      segundos = s;
      esPM = (p == 'P');
      diaSemana = d;
      relojSincronizado = true;
    }
  } 
  else if (bufferSerial[0] == 'A') { // Guardar Alarma -> A:HH:MM:A/P:DUR:MASCARA
    int h, m, dur, masc;
    char p;
    if (sscanf(bufferSerial, "A:%d:%d:%c:%d:%d", &h, &m, &p, &dur, &masc) == 5) {
      config.alarmaHora = h;
      config.alarmaMinuto = m;
      config.alarmaPM = (p == 'P');
      config.alarmaDuracion = dur;
      config.alarmaDias = masc;
      config.alarmaHabilitada = true;
      guardarConfiguracion();
    }
  }
}

void leerSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (indiceBuffer > 0) {
        bufferSerial[indiceBuffer] = '\0';
        procesarComando();
        indiceBuffer = 0;
      }
    } else if (indiceBuffer < 63) {
      bufferSerial[indiceBuffer++] = c;
    }
  }
}

// ==========================================
// ESTRUCTURAS OBLIGATORIAS DE ARDUINO
// ==========================================
void setup() {
  Serial.begin(9600);
  
  for (byte i = 0; i < 7; i++) pinMode(pinesSegmentos[i], OUTPUT);
  for (byte i = 0; i < 6; i++) pinMode(pinesComunes[i], OUTPUT);
  
  pinMode(pinAM, OUTPUT);
  pinMode(pinPM, OUTPUT);
  pinMode(pinAlarmaArduino, OUTPUT);
  
  cargarConfiguracion();
}

void loop() {
  unsigned long ahoraMicros = micros();
  
  // Muestreo del multiplexado basado en tiempo de microsegundos
  if (ahoraMicros - ultimoMultiplex >= PERIODO_DISPLAY) {
    ultimoMultiplex = ahoraMicros;
    multiplexarDisplays();
  }
  
  // Estado de luces indicadoras AM/PM
  digitalWrite(pinAM, (!esPM && relojSincronizado) ? HIGH : LOW);
  digitalWrite(pinPM, (esPM && relojSincronizado) ? HIGH : LOW);
  
  // Reloj interno por segundo de ejecución
  unsigned long ahoraMillis = millis();
  if (ahoraMillis - ultimoSegundo >= 1000) {
    ultimoSegundo = ahoraMillis;
    avanzarUnSegundo();
    
    // Envío constante de información hacia la interfaz de Python
    if (relojSincronizado) {
      Serial.print(F("INFO:"));
      Serial.print(horas); Serial.print(F(":"));
      Serial.print(minutos); Serial.print(F(":"));
      Serial.print(segundos); Serial.print(F(":"));
      Serial.print(esPM ? F("P") : F("A")); Serial.print(F(":"));
      Serial.println(diaSemana);
    }
  }
  
  leerSerial();
  actualizarAlarma();
}