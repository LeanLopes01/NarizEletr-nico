"""Workers de comunicacao Serial e Simulacao em QThread para o Arduino UNO v0.4.3."""
from __future__ import annotations

import math
import queue
import random
import time
from threading import Event

from .protocol import DEFAULT_STAGE_DURATIONS_INO_MS, parse_line
from .qt_compat import QThread, Signal


class TransportWorker(QThread):
    received = Signal(dict)
    connected = Signal()
    disconnected = Signal(str)

    def __init__(self):
        super().__init__()
        self._commands: queue.Queue[str] = queue.Queue()
        self._stopping = Event()

    def send(self, command: str):
        self._commands.put(command)

    def stop(self):
        self._stopping.set()

    def _read_commands(self):
        while True:
            try:
                yield self._commands.get_nowait()
            except queue.Empty:
                return


class SerialWorker(TransportWorker):
    """Comunicacao UART 115200 8N1 com o Arduino UNO (firmware megaPyhtonSerial adaptado)."""

    def __init__(self, port: str, baudrate: int = 115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate

    def run(self):
        import serial

        conn = None
        why = "Porta serial desconectada."
        try:
            conn = serial.Serial(self.port, self.baudrate, timeout=0.08, write_timeout=0.5)
            # Arduino UNO R3 reinicia automaticamente ao abrir a porta serial (DTR).
            start = time.monotonic()
            while time.monotonic() - start < 2.2 and not self._stopping.is_set():
                raw = conn.readline()
                if raw:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        self._emit_parsed(line)
                else:
                    time.sleep(0.04)

            if self._stopping.is_set():
                return

            self.connected.emit()
            # Solicita a configuracao atual de tempos ao conectar
            try:
                conn.write(b"SHOW\n")
                conn.flush()
            except Exception:
                pass

            while not self._stopping.is_set():
                for command in self._read_commands():
                    cmd_bytes = (command.strip() + "\n").encode("ascii", errors="ignore")
                    conn.write(cmd_bytes)
                    conn.flush()
                    time.sleep(0.03)

                raw = conn.readline()
                if raw:
                    if not raw.endswith(b"\n"):
                        continue
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        self._emit_parsed(line)
        except Exception as exc:
            why = f"Falha serial ({self.port}): {exc}"
        finally:
            if conn is not None:
                try:
                    conn.write(b"STOP\n")
                    conn.flush()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
            self.disconnected.emit(why)

    def _emit_parsed(self, line: str):
        try:
            event = parse_line(line)
            self.received.emit(event)
        except ValueError:
            self.received.emit({"type": "INFO", "message": line})


class SimulationWorker(TransportWorker):
    """Simulador fiel ao firmware Arduino UNO (megaPyhtonSerial.ino) com 6 etapas (E0..E5)."""

    # Perfis tipicos de resposta (base_adc, delta_max_adc) para MQ2, MQ3, MQ5 por gas
    GAS_PROFILES = {
        "A": ((210, 145), (412, 265), (328, 170)),   # Acetone
        "E": ((215, 115), (420, 320), (335, 150)),   # Ethyl Alcohol
        "P": ((212, 130), (415, 290), (330, 195)),   # Isopropyl Alcohol
        "AR": ((208, 8), (408, 10), (325, 7)),       # Clean Air
    }

    def __init__(self, gas_code: str = "A"):
        super().__init__()
        self.gas_code = gas_code if gas_code in self.GAS_PROFILES else "A"

    def set_gas_profile(self, gas_code: str):
        if gas_code in self.GAS_PROFILES:
            self.gas_code = gas_code

    def run(self):
        self.connected.emit()
        self._emit_line("Tempo(s),MQ2(A0),MQ3(A1),MQ5(A2),Temperatura(C),Umidade(%)")
        self._emit_line("Sistema pronto. Use comandos: START, STOP, RESET, SHOW, SET <etapa> <tempo_ms>")

        stage_durations = list(DEFAULT_STAGE_DURATIONS_INO_MS)
        ciclo_ativo = False
        ciclo_finalizado = False
        current_stage = 0
        tempo_total = 0
        last_stage_time = time.monotonic()
        ultima_leitura_sec = 0.0

        # Estado continuo dos sensores simulados para transicoes suaves entre etapas
        profile = self.GAS_PROFILES.get(self.gas_code, self.GAS_PROFILES["A"])
        current_adc = [float(p[0]) for p in profile]
        temp_c = 29.24
        hum_pct = 52.80
        pressao_hpa = 942.60

        while not self._stopping.is_set():
            now = time.monotonic()

            for raw_cmd in self._read_commands():
                cmd = raw_cmd.strip()
                if not cmd:
                    continue

                if cmd.upper().startswith("SET"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            etapa = int(parts[1])
                            tempo_ms = int(parts[2])
                            if 0 <= etapa < 6 and tempo_ms >= 0:
                                stage_durations[etapa] = tempo_ms
                                self._emit_line(f"Etapa {etapa} tempo atualizado para {tempo_ms} ms")
                            else:
                                self._emit_line("Erro: etapa deve ser 0 a 5")
                        except ValueError:
                            self._emit_line("Uso: SET <etapa> <tempo_ms>")
                    else:
                        self._emit_line("Uso: SET <etapa> <tempo_ms>")

                elif cmd.upper() == "SHOW":
                    self._emit_line("Tempos atuais (ms):")
                    for i in range(6):
                        self._emit_line(f"Etapa {i}: {stage_durations[i]}")

                elif cmd.upper().startswith("START") and not ciclo_ativo:
                    profile = self.GAS_PROFILES.get(self.gas_code, self.GAS_PROFILES["A"])
                    current_adc = [float(p[0]) + random.uniform(-2, 2) for p in profile]
                    ciclo_ativo = True
                    ciclo_finalizado = False
                    current_stage = 0
                    tempo_total = 0
                    last_stage_time = now
                    ultima_leitura_sec = now - 1.0  # Emite t=0 imediatamente
                    self._emit_stage(current_stage)
                    self._emit_line("CICLO STARTED")

                elif cmd.upper() == "STOP":
                    ciclo_ativo = False
                    ciclo_finalizado = True
                    self._emit_stage(5)
                    self._emit_line("CICLO STOPPED")

                elif cmd.upper() == "RESET":
                    ciclo_ativo = False
                    ciclo_finalizado = False
                    current_stage = 0
                    tempo_total = 0
                    self._emit_stage(5)
                    self._emit_line("RESET")

                elif cmd.upper() == "PING":
                    self._emit_line("PONG")

                elif cmd.upper() == "IDENT":
                    self._emit_line("HELLO,UNO_V043_SIM,3")

            if ciclo_ativo and not ciclo_finalizado:
                # Avanca etapas (incluindo etapas com 0 ms)
                while (
                    ciclo_ativo
                    and not ciclo_finalizado
                    and (now - last_stage_time) * 1000.0 >= stage_durations[current_stage]
                ):
                    current_stage += 1
                    last_stage_time = now
                    if current_stage < 6:
                        self._emit_stage(current_stage)
                    else:
                        self._emit_stage(5)
                        ciclo_ativo = False
                        ciclo_finalizado = True
                        self._emit_line("CICLO FINALIZADO")

                # Emite leitura CSV a cada 1s com tempoTotal crescente
                if ciclo_ativo and not ciclo_finalizado and (now - ultima_leitura_sec >= 1.0):
                    ultima_leitura_sec = now
                    profile = self.GAS_PROFILES.get(self.gas_code, self.GAS_PROFILES["A"])
                    stage_dur_s = max(1.0, stage_durations[current_stage] / 1000.0)

                    adc_int = []
                    for i, (base, delta_max) in enumerate(profile):
                        if current_stage in (0, 1):
                            # Limpeza inicial / Baseline
                            target = base
                            tau = max(2.5, stage_dur_s * 0.25)
                        elif current_stage == 2:
                            # Exposicao ao gas
                            target = base + delta_max
                            tau = max(2.0, stage_dur_s * 0.32)
                        elif current_stage == 3:
                            # Camara fechada / Retencao
                            target = base + delta_max * 0.96
                            tau = max(4.0, stage_dur_s * 0.5)
                        elif current_stage == 4:
                            # Exaustao / Recuperacao
                            target = base + delta_max * 0.12
                            tau = max(3.0, stage_dur_s * 0.35)
                        else:
                            # Etapa 5 final
                            target = base
                            tau = max(2.0, stage_dur_s * 0.3)

                        alpha = 1.0 - math.exp(-1.0 / tau)
                        current_adc[i] += (target - current_adc[i]) * alpha
                        noisy = current_adc[i] + random.gauss(0, 1.4)
                        adc_int.append(max(0, min(1023, int(round(noisy)))))

                    temp_c += random.gauss(0, 0.015)
                    temp_c = max(22.0, min(35.0, temp_c))
                    hum_pct += random.gauss(0, 0.03)
                    hum_pct = max(35.0, min(75.0, hum_pct))
                    pressao_hpa += random.gauss(0, 0.02)

                    line = f"{tempo_total},{adc_int[0]},{adc_int[1]},{adc_int[2]},{temp_c:.2f},{hum_pct:.2f},{pressao_hpa:.2f}"
                    self._emit_line(line)
                    tempo_total += 1

            time.sleep(0.02)

        self.disconnected.emit("Modo simulacao encerrado.")

    def _emit_stage(self, etapa: int):
        if etapa == 5:
            self._emit_line("Etapa 5 (final) - tudo desligado")
        else:
            self._emit_line(f"Etapa {etapa}")

    def _emit_line(self, text: str):
        try:
            self.received.emit(parse_line(text))
        except ValueError:
            self.received.emit({"type": "INFO", "message": text})
