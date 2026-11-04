/*
 * ============================================================================
 * NARIZ ELETRÔNICO v0.4.3 — FIRMWARE ARDUINO UNO R3 (ATmega328P @ 16 MHz)
 * Baseado em: Sistema gás/v0.4.2/megaPyhtonSerial/megaPyhtonSerial.ino
 * Adaptado para Arduino UNO R3 com diretrizes analíticas v0.4.3.
 * ============================================================================
 *
 * MAPEAMENTO DE PINOS (ARDUINO UNO R3):
 *   Relés (Válvulas e Bomba):
 *     D6 -> V1 (Válvula 1 - Ar Limpo / Purga)
 *     D7 -> V2 (Válvula 2 - Gás / Amostra)
 *     D8 -> V3 (Válvula 3 - Exaustão / Saída)
 *     D9 -> BOMBA (Bomba de Vácuo / Fluxo)
 *
 *   Sensores de Gás MOS (ADC 10 bits, 0..1023 -> 0..5 V):
 *     A0 -> MQ2(A0)
 *     A1 -> MQ3(A1)
 *     A2 -> MQ5(A2)
 *
 *   Sensor Ambiental HDC1080 (I2C endereço 0x40):
 *     A4 -> SDA
 *     A5 -> SCL
 *
 * COMANDOS SERIAIS (115200 bps, terminados por '\n'):
 *   START                  -> Inicia o ciclo de 6 etapas (Etapa 0 a Etapa 5)
 *   STOP                   -> Interrompe o ciclo e aplica Etapa 5
 *   RESET                  -> Reinicia contadores e aplica Etapa 5
 *   SHOW                   -> Exibe as durações configuradas das Etapas 0 a 5 (ms)
 *   SET <etapa> <tempo_ms> -> Define a duração da etapa (0..5) em milissegundos
 *   STATUS                 -> Retorna estado resumido para o dashboard Python
 *   PING                   -> Retorna PONG
 *   IDENT                  -> Retorna HELLO,UNO_V043,3
 * ============================================================================
 */

#include <Arduino.h>
#include <Wire.h>

#if __has_include("ClosedCube_HDC1080.h")
  #include "ClosedCube_HDC1080.h"
  #define HAS_CLOSEDCUBE_LIB 1
#else
  #define HAS_CLOSEDCUBE_LIB 0
  // Driver I2C compatível caso a biblioteca ClosedCube_HDC1080 não esteja instalada
  class ClosedCube_HDC1080 {
  private:
    uint8_t _addr = 0x40;
    uint16_t readReg16(uint8_t reg) {
      Wire.beginTransmission(_addr);
      Wire.write(reg);
      if (Wire.endTransmission() != 0) return 0;
      delay(15);
      if (Wire.requestFrom(_addr, (uint8_t)2) != 2) return 0;
      uint16_t msb = Wire.read();
      uint16_t lsb = Wire.read();
      return (msb << 8) | lsb;
    }
  public:
    void begin(uint8_t address = 0x40) {
      _addr = address;
      Wire.beginTransmission(_addr);
      Wire.write(0x02); // Registrador de configuração
      Wire.write(0x10); // Temperatura e Umidade em 14 bits
      Wire.write(0x00);
      Wire.endTransmission();
      delay(15);
    }
    float readTemperature() {
      uint16_t raw = readReg16(0x00);
      if (raw == 0) return 25.0f;
      return ((float)raw / 65536.0f) * 165.0f - 40.0f;
    }
    float readHumidity() {
      uint16_t raw = readReg16(0x01);
      if (raw == 0) return 50.0f;
      return ((float)raw / 65536.0f) * 100.0f;
    }
  };
#endif

ClosedCube_HDC1080 hdc1080;
bool hdc1080Disponivel = false;

// ---------- PINOS (ARDUINO UNO) ----------
#define RELAY_COUNT 4
#define PIN_V1    6
#define PIN_V2    7
#define PIN_V3    8
#define PIN_BOMBA 9
const uint8_t relayPins[RELAY_COUNT] = {PIN_V1, PIN_V2, PIN_V3, PIN_BOMBA}; // V1, V2, V3, BOMBA

#define V1    0
#define V2    1
#define V3    2
#define BOMBA 3

#define GAS_PINS_COUNT 3
const uint8_t gasPins[GAS_PINS_COUNT] = {A0, A1, A2}; // MQ2(A0), MQ3(A1), MQ5(A2)

// ---------- VARIÁVEIS ----------
volatile int gasReadings[GAS_PINS_COUNT] = {0, 0, 0};
float tempReading = 25.0;
float humReading  = 50.0;

volatile bool cicloAtivo      = false;
volatile bool cicloFinalizado = false;

unsigned long tempoTotal       = 0;
unsigned long ultimaLeituraSec = 0;

// Durações das etapas (ms): Etapa 0 a Etapa 5
unsigned long stageDurations[6] = {0UL, 10000UL, 10000UL, 10000UL, 10000UL, 10000UL};

unsigned long lastStageTime = 0;
uint8_t currentStage        = 0;

// Flags de sincronização com a ISR do Timer1 (250 ms)
volatile bool gasReadFlag     = false;
volatile uint8_t gasIndexISR  = 0;
volatile uint8_t gasISRCount  = 0;
volatile bool tempHumFlag     = false;

// Protótipos
void aplicarEtapa(uint8_t etapa);
void atualizarSensoresImediato();
bool verificarHDC1080();

// ---------- SETUP ----------
void setup() {
  Serial.begin(115200);
  while (!Serial) {}

  Serial.println(F("Tempo(s),MQ2(A0),MQ3(A1),MQ5(A2),Temperatura(C),Umidade(%)"));

  Wire.begin();
  hdc1080Disponivel = verificarHDC1080();
  if (hdc1080Disponivel) {
    hdc1080.begin(0x40);
  }

  for (int i = 0; i < RELAY_COUNT; i++) {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], HIGH);
  }

  // Configura Timer1 do ATmega328P (Arduino UNO) para 250 ms
  // 16 MHz / prescaler 64 = 250.000 Hz -> 62.500 contagens = 250 ms
  noInterrupts();
  TCCR1A = 0;
  TCCR1B = (1 << WGM12);
  TCCR1B |= (1 << CS11) | (1 << CS10); // prescaler = 64
  TCNT1  = 0;
  OCR1A  = 62499;
  TIMSK1 |= (1 << OCIE1A);
  interrupts();

  lastStageTime = millis();

  Serial.println(F("Sistema pronto. Use comandos: START, STOP, RESET, SHOW, SET <etapa> <tempo_ms>"));
}

bool verificarHDC1080() {
  Wire.beginTransmission(0x40);
  return (Wire.endTransmission() == 0);
}

void atualizarSensoresImediato() {
  for (uint8_t i = 0; i < GAS_PINS_COUNT; i++) {
    gasReadings[i] = analogRead(gasPins[i]);
  }
  if (hdc1080Disponivel && verificarHDC1080()) {
    float t = hdc1080.readTemperature();
    float h = hdc1080.readHumidity();
    if (!isnan(t) && t > -35.0f && t < 120.0f) tempReading = t;
    if (!isnan(h) && h >= 0.0f && h <= 100.0f) humReading = h;
  }
}

// ---------- ISR Timer1 (250 ms) ----------
ISR(TIMER1_COMPA_vect) {
  if (cicloAtivo && !cicloFinalizado) {
    gasReadFlag = true;
    gasIndexISR = (gasIndexISR + 1) % GAS_PINS_COUNT;

    gasISRCount++;
    if (gasISRCount >= GAS_PINS_COUNT) {
      gasISRCount = 0;
      tempHumFlag = true;
    }
  }
}

// ---------- LOOP ----------
void loop() {
  // --------- COMANDOS SERIAL ---------
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.startsWith("SET")) {
      int etapa = -1;
      unsigned long tempo = 0;
      if (sscanf(cmd.c_str(), "SET %d %lu", &etapa, &tempo) == 2) {
        if (etapa >= 0 && etapa < 6) {
          stageDurations[etapa] = tempo;
          Serial.print(F("Etapa "));
          Serial.print(etapa);
          Serial.print(F(" tempo atualizado para "));
          Serial.print(tempo);
          Serial.println(F(" ms"));
        } else {
          Serial.println(F("Erro: etapa deve ser 0 a 5"));
        }
      } else {
        Serial.println(F("Uso: SET <etapa> <tempo_ms>"));
      }
    }
    else if (cmd == "SHOW") {
      Serial.println(F("Tempos atuais (ms):"));
      for (int i = 0; i < 6; i++) {
        Serial.print(F("Etapa "));
        Serial.print(i);
        Serial.print(F(": "));
        Serial.println(stageDurations[i]);
      }
    }
    else if (cmd == "START" && !cicloAtivo) {
      atualizarSensoresImediato();
      cicloAtivo = true;
      cicloFinalizado = false;
      currentStage = 0;
      unsigned long agora = millis();
      lastStageTime = agora;
      ultimaLeituraSec = agora - 1000UL; // Envia leitura t=0 imediatamente
      tempoTotal = 0;
      aplicarEtapa(currentStage);
      Serial.println(F("CICLO STARTED"));
    }
    else if (cmd == "STOP") {
      cicloAtivo = false;
      cicloFinalizado = true;
      aplicarEtapa(5);
      Serial.println(F("CICLO STOPPED"));
    }
    else if (cmd == "RESET") {
      cicloAtivo = false;
      cicloFinalizado = false;
      currentStage = 0;
      tempoTotal = 0;
      aplicarEtapa(5);
      Serial.println(F("RESET"));
    }
    else if (cmd == "IDENT") {
      Serial.println(F("HELLO,UNO_V043,3"));
    }
    else if (cmd == "PING") {
      Serial.println(F("PONG"));
    }
    else if (cmd == "STATUS") {
      Serial.print(F("STATUS,"));
      Serial.print(cicloAtivo ? 1 : 0); Serial.print(',');
      Serial.print(currentStage); Serial.print(',');
      Serial.print(tempoTotal);
      for (int i = 0; i < 6; i++) {
        Serial.print(',');
        Serial.print(stageDurations[i]);
      }
      Serial.println();
    }
  }

  // --------- LEITURA DE SENSORES ---------
  static uint8_t nextToRead = 0;
  if (gasReadFlag) {
    uint8_t idx = nextToRead % GAS_PINS_COUNT;
    gasReadings[idx] = analogRead(gasPins[idx]);
    nextToRead = (nextToRead + 1) % GAS_PINS_COUNT;
    gasReadFlag = false;
  }

  if (tempHumFlag) {
    if (hdc1080Disponivel && verificarHDC1080()) {
      float t = hdc1080.readTemperature();
      float h = hdc1080.readHumidity();
      if (!isnan(t) && t > -35.0f && t < 120.0f) tempReading = t;
      if (!isnan(h) && h >= 0.0f && h <= 100.0f) humReading = h;
    }
    tempHumFlag = false;
  }

  // --------- CONTROLE DE ETAPAS ---------
  if (cicloAtivo && !cicloFinalizado) {
    unsigned long agora = millis();
    while (cicloAtivo && !cicloFinalizado && (agora - lastStageTime >= stageDurations[currentStage])) {
      currentStage++;
      lastStageTime = agora;

      if (currentStage < 6) {
        aplicarEtapa(currentStage);
      } else {
        aplicarEtapa(5);
        cicloAtivo = false;
        cicloFinalizado = true;
        Serial.println(F("CICLO FINALIZADO"));
      }
    }

    // Envia dados CSV a cada 1s: Tempo(s),MQ2(A0),MQ3(A1),MQ5(A2),Temperatura(C),Umidade(%)
    if (cicloAtivo && !cicloFinalizado && (agora - ultimaLeituraSec >= 1000UL)) {
      ultimaLeituraSec = agora;
      Serial.print(tempoTotal);      Serial.print(',');
      Serial.print(gasReadings[0]);  Serial.print(',');
      Serial.print(gasReadings[1]);  Serial.print(',');
      Serial.print(gasReadings[2]);  Serial.print(',');
      Serial.print(tempReading, 2);  Serial.print(',');
      Serial.println(humReading, 2);
      tempoTotal++;
    }
  }

  delay(1);
}

// ---------- CONTROLE DE RELÉS ----------
void aplicarEtapa(uint8_t etapa) {
  switch (etapa) {
    case 0:
      digitalWrite(relayPins[V1], LOW);
      digitalWrite(relayPins[V2], LOW);
      digitalWrite(relayPins[V3], LOW);
      digitalWrite(relayPins[BOMBA], LOW);
      Serial.println(F("Etapa 0"));
      break;

    case 1:
      digitalWrite(relayPins[V1], LOW);
      digitalWrite(relayPins[V2], HIGH);
      digitalWrite(relayPins[V3], LOW);
      digitalWrite(relayPins[BOMBA], LOW);
      Serial.println(F("Etapa 1"));
      break;

    case 2:
      digitalWrite(relayPins[V1], HIGH);
      digitalWrite(relayPins[V2], LOW);
      digitalWrite(relayPins[V3], LOW);
      digitalWrite(relayPins[BOMBA], LOW);
      Serial.println(F("Etapa 2"));
      break;

    case 3:
      digitalWrite(relayPins[V1], HIGH);
      digitalWrite(relayPins[V2], HIGH);
      digitalWrite(relayPins[V3], HIGH);
      digitalWrite(relayPins[BOMBA], HIGH);
      Serial.println(F("Etapa 3"));
      break;

    case 4:
      digitalWrite(relayPins[V1], LOW);
      digitalWrite(relayPins[V2], HIGH);
      digitalWrite(relayPins[V3], HIGH);
      digitalWrite(relayPins[BOMBA], HIGH);
      Serial.println(F("Etapa 4"));
      break;

    case 5:
      digitalWrite(relayPins[V1], LOW);
      digitalWrite(relayPins[V2], LOW);
      digitalWrite(relayPins[V3], LOW);
      digitalWrite(relayPins[BOMBA], LOW);
      Serial.println(F("Etapa 5 (final) - tudo desligado"));
      break;

    default:
      digitalWrite(relayPins[V1], LOW);
      digitalWrite(relayPins[V2], LOW);
      digitalWrite(relayPins[V3], LOW);
      digitalWrite(relayPins[BOMBA], LOW);
      Serial.println(F("Etapa desconhecida - tudo desligado"));
      break;
  }
}
