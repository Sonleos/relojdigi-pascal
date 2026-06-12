#include <EEPROM.h>
#include <avr/wdt.h>
#include <avr/pgmspace.h>

// Configuración de tiempos no bloqueantes
constexpr unsigned long PERIODO_DISPLAY = 1500UL; // Microsegundos para multiplexado
constexpr byte DIAS_SEMANA = 7;

// Definición de Pines del Hardware
const byte pinesSegmentos[7] = {13, 12, 11, 10, 9, 8, 7};
const byte pinesComunes[6]   = {5, 4, 3, 2, A1, A2};
const byte pinAM             = A3;
const byte pinPM             = A4;
const byte pinAlarmaArduino  = A0;

const byte FIRMA_EEPROM = 0x58; // Identificador de memoria limpia

// Estructura individual para soporte de MULTI-ALARMAS (Sincronizado con Python)
struct Alarma {
  byte id;
  byte hora;
  byte minuto;
  bool esPM;
  byte duracion;
  byte dias;
  bool activa;
};

Alarma alarmas[15]; // Capacidad para hasta 15 alarmas simultáneas
byte totalAlarmas = 0;

// Variables globales del Reloj
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

// Buffer serial asíncrono (Previene congelamientos)
char bufferSerial[64];
byte indiceBuffer = 0;

// Patrones de bits para Display 7 Segmentos (Cátodo Común / Ánodo Común estándar)
const byte digitos7Seg[10] PROGMEM = {
  0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F
};

void setup() {
  Serial.begin(9600);
  
  // Configurar pines como salidas
  for (byte i = 0; i < 7; i++) pinMode(pinesSegmentos[i], OUTPUT);
  for (byte i = 0; i < 6; i++) pinMode(pinesComunes[i], OUTPUT);
  pinMode(pinAM, OUTPUT);
  pinMode(pinPM, OUTPUT);
  pinMode(pinAlarmaArduino, OUTPUT);
  
  apagarDisplays();
  digitalWrite(pinAlarmaArduino, LOW);
  
  cargarConfiguracion(); // Recuperar alarmas desde la EEPROM física
}

void loop() {
  unsigned long ahoraMili = millis();
  unsigned long ahoraMicro = micros();
  
  // 1. MOTOR DEL RELOJ: Avanza segundo a segundo de forma no bloqueante
  if (ahoraMili - ultimoSegundo >= 1000UL) {
    ultimoSegundo = ahoraMili;
    avanzarUnSegundo();
    
    // Si la PC ya sincronizó el reloj, le transmitimos el tiempo segundo a segundo
    if (relojSincronizado) {
      Serial.print(F("INFO:"));
      Serial.print(horas); Serial.print(F(":"));
      Serial.print(minutos); Serial.print(F(":"));
      Serial.print(segundos); Serial.print(F(":"));
      Serial.print(esPM ? F("P") : F("A")); Serial.print(F(":"));
      Serial.println(diaSemana);
    }
  }
  
  // 2. MULTIPLEXADO: Actualiza los displays de 7 segmentos velozmente sin retrasar al procesador
  if (ahoraMicro - ultimoMultiplex >= PERIODO_DISPLAY) {
    ultimoMultiplex = ahoraMicro;
    actualizarDisplay();
  }
  
  // 3. SALIDA FÍSICA: Activa o desactiva el pin de la Sirena/Relé
  digitalWrite(pinAlarmaArduino, alarmaActiva ? HIGH : LOW);
  
  // 4. LECTOR SERIAL REVOLUCIONADO: Escucha comandos sin usar delay() ni ciclos forcing
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (indiceBuffer > 0) {
        bufferSerial[indiceBuffer] = '\0';
        procesarComando(); // Procesa el comando recibido de Python
        indiceBuffer = 0;
      }
    } else if (indiceBuffer < sizeof(bufferSerial) - 1) {
      bufferSerial[indiceBuffer++] = c;
    }
  }
}

// ========================================================
// LÓGICA DE ALMACENAMIENTO (EEPROM)
// ========================================================
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

// ========================================================
// PROCESADOR DE COMANDOS SERIALES (Python -> Arduino)
// ========================================================
void procesarComando() {
  // Comando S: Sincronizar Tiempo (S:HH:MM:SS:P/A:DIA)
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
  // Comando A: Agregar Alarma (A:H:M:P:DUR:DIAS:ACT)
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
  // Comando T: Cambiar estado Activo/Inactivo (T:ID:0/1)
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
  // Comando D: Eliminar Alarma (D:ID)
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
  // Comando CLEARALL: Vaciar memoria
  else if (strcmp(bufferSerial, "CLEARALL") == 0) {
    totalAlarmas = 0;
    guardarAlarmasEEPROM();
    alarmaActiva = false;
  }
}

// ========================================================
// CRONÓMETRO INTERNO Y CONTROL DE SIRENA
// ========================================================
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
  verificarAlarma(); // Comprobar la matriz de alarmas cada segundo
}

void verificarAlarma() {
  if (!relojSincronizado) {
    alarmaActiva = false;
    return;
  }
  
  byte bitHoy = diaSemana - 1;
  bool encenderSirena = false;

  // Analizar si la hora actual coincide con alguna de las alarmas de la lista
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

// ========================================================
// CONTROL GRÁFICO (Multiplexado de 7 Segmentos)
// ========================================================
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
  apagarDisplays(); // Apaga el display anterior para evitar fantasmas

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
  digitalWrite(pinesComunes[displayActivo], HIGH); // Enciende el dígito correspondiente

  // Manejo de luces indicadoras AM/PM
  digitalWrite(pinAM, !esPM ? HIGH : LOW);
  digitalWrite(pinPM, esPM ? HIGH : LOW);
}