"""Protocolo serial para o Nariz Eletronico v0.4.3 (Arduino UNO / megaPyhtonSerial).

Suporta tanto o protocolo nativo do firmware Arduino UNO (baseado em megaPyhtonSerial.ino):
  - Leituras CSV 1 Hz: Tempo(s),MQ2(A0),MQ3(A1),MQ5(A2),Temperatura(C),Umidade(%)[,Pressao(hPa)]
  - Eventos de etapa:  "Etapa 0" .. "Etapa 5 (final) - tudo desligado"
  - Confirmacoes SET:  "Etapa <n> tempo atualizado para <ms> ms"
  - Resposta SHOW:     "Etapa <n>: <ms>"
  - Eventos de ciclo:  "CICLO STARTED", "CICLO STOPPED", "CICLO FINALIZADO", "RESET"
  - Comandos host:     START, STOP, RESET, SHOW, SET <etapa> <tempo_ms>, STATUS, PING, IDENT
quanto mensagens estruturadas (DATA, STATUS, EVENT, ACK, ERR, HELLO, PONG).
"""
from __future__ import annotations

import re

# Mapeamento das 6 etapas do megaPyhtonSerial.ino
STAGE_NAMES: dict[int, str] = {
    0: "Etapa 0 — Preparacao Inicial",
    1: "Etapa 1 — Limpeza / Baseline (Ar)",
    2: "Etapa 2 — Exposicao ao Gas (Amostra)",
    3: "Etapa 3 — Camara Fechada (Retencao)",
    4: "Etapa 4 — Exaustao / Recuperacao",
    5: "Etapa 5 — Final / Tudo Desligado",
}

STAGE_SHORT_NAMES: dict[int, str] = {
    0: "E0: Prep",
    1: "E1: Baseline",
    2: "E2: Exposicao",
    3: "E3: Retencao",
    4: "E4: Purga",
    5: "E5: Final",
}

# Nivel logico enviado aos pinos do Arduino UNO (D6=V1, D7=V2, D8=V3, D9=BOMBA)
# conforme aplicarEtapa() de megaPyhtonSerial.ino:
STAGE_RELAY_LEVELS: dict[int, dict[str, str]] = {
    0: {"V1": "LOW",  "V2": "LOW",  "V3": "LOW",  "BOMBA": "LOW"},
    1: {"V1": "LOW",  "V2": "HIGH", "V3": "LOW",  "BOMBA": "LOW"},
    2: {"V1": "HIGH", "V2": "LOW",  "V3": "LOW",  "BOMBA": "LOW"},
    3: {"V1": "HIGH", "V2": "HIGH", "V3": "HIGH", "BOMBA": "HIGH"},
    4: {"V1": "LOW",  "V2": "HIGH", "V3": "HIGH", "BOMBA": "HIGH"},
    5: {"V1": "LOW",  "V2": "LOW",  "V3": "LOW",  "BOMBA": "LOW"},
}

# Duracoes padrao das 6 etapas (ms):
# - Preset Oficial Bancada v0.4.3 (190 s total: E1=60s baseline, E2=30s exposicao, E3=30s, E4=60s, E5=10s)
DEFAULT_STAGE_DURATIONS_V043_MS: list[int] = [0, 60000, 30000, 30000, 60000, 10000]
# - Preset Firmware megaPyhtonSerial.ino (50 s total)
DEFAULT_STAGE_DURATIONS_INO_MS: list[int] = [0, 10000, 10000, 10000, 10000, 10000]
# - Preset Teste Rapido (15 s total)
DEFAULT_STAGE_DURATIONS_FAST_MS: list[int] = [0, 3000, 3000, 3000, 3000, 3000]

_RE_SET_ACK = re.compile(r"^Etapa\s+(\d+)\s+tempo\s+atualizado\s+para\s+(\d+)\s*ms", re.IGNORECASE)
_RE_SHOW_LINE = re.compile(r"^Etapa\s+(\d+)\s*:\s*(\d+)\s*$", re.IGNORECASE)
_RE_STAGE_CHANGE = re.compile(r"^Etapa\s+(\d+)\b", re.IGNORECASE)


def adc_to_voltage(adc_value: float | int) -> float:
    """Converte leitura ADC 10 bits (0..1023) para Tensao (0..5.0 V) conforme v0.4.3."""
    return (float(adc_value) / 1023.0) * 5.0


def parse_line(text: str) -> dict:
    """Interpreta uma linha recebida da serial do Arduino UNO."""
    clean = text.strip()
    if not clean:
        raise ValueError("Linha vazia")

    # 1. Eventos e mensagens de controle do megaPyhtonSerial.ino
    if clean.startswith("Tempo(s),MQ2(A0)") or clean.startswith("Tempo(s);MQ2(A0)"):
        return {"type": "HEADER", "raw": clean}

    if clean.startswith("Sistema pronto") or clean.startswith("Tempos atuais"):
        return {"type": "INFO", "message": clean}

    if clean == "CICLO STARTED":
        return {"type": "EVENT", "name": "STARTED", "args": []}

    if clean == "CICLO STOPPED":
        return {"type": "EVENT", "name": "STOPPED", "args": []}

    if clean == "CICLO FINALIZADO":
        return {"type": "EVENT", "name": "FINISHED", "args": []}

    if clean == "RESET":
        return {"type": "EVENT", "name": "RESET", "args": []}

    m_set = _RE_SET_ACK.match(clean)
    if m_set:
        stage = int(m_set.group(1))
        ms = int(m_set.group(2))
        return {"type": "STAGE_TIME", "stage": stage, "duration_ms": ms, "message": clean}

    m_show = _RE_SHOW_LINE.match(clean)
    if m_show:
        stage = int(m_show.group(1))
        ms = int(m_show.group(2))
        return {"type": "STAGE_TIME", "stage": stage, "duration_ms": ms, "message": clean}

    m_stage = _RE_STAGE_CHANGE.match(clean)
    if m_stage:
        stage = int(m_stage.group(1))
        return {
            "type": "STAGE",
            "stage": stage,
            "stage_name": STAGE_NAMES.get(stage, f"Etapa {stage}"),
            "relays": STAGE_RELAY_LEVELS.get(stage, STAGE_RELAY_LEVELS[5]),
            "message": clean,
        }

    if clean.startswith("Erro:") or clean.startswith("Uso:"):
        return {"type": "ERR", "message": clean}

    # 2. Linha CSV de leitura do megaPyhtonSerial.ino:
    # Formato: Tempo(s),MQ2(A0),MQ3(A1),MQ5(A2),Temperatura(C),Umidade(%)[,Pressao(hPa)]
    parts = [p.strip() for p in (clean.split(";") if ";" in clean and "," not in clean else clean.split(","))]
    kind = parts[0] if parts else ""

    if len(parts) in (6, 7) and (kind.isdigit() or (kind.startswith("-") and kind[1:].isdigit())):
        try:
            tempo_s = int(parts[0])
            mq2 = int(float(parts[1]))
            mq3 = int(float(parts[2]))
            mq5 = int(float(parts[3]))
            temp = float(parts[4])
            hum = float(parts[5])
            pressao = float(parts[6]) if len(parts) == 7 else 942.5
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Leitura CSV invalida: {text!r}") from exc

        if tempo_s < 0 or any(not 0 <= v <= 1023 for v in (mq2, mq3, mq5)):
            raise ValueError(f"Valores fora da faixa ADC (0..1023): {text!r}")

        return {
            "type": "READING",
            "tempo_s": tempo_s,
            "ms": tempo_s * 1000,
            "mq2": mq2,
            "mq3": mq3,
            "mq5": mq5,
            "mq2_v": adc_to_voltage(mq2),
            "mq3_v": adc_to_voltage(mq3),
            "mq5_v": adc_to_voltage(mq5),
            "temp": temp,
            "hum": hum,
            "pressao": pressao,
            "adc": [mq2, mq3, mq5],
        }

    # 3. Mensagens estruturadas (STATUS, DATA, EVENT, ACK, ERR, HELLO, PONG)
    try:
        if kind == "DATA" and len(parts) in (12, 13):
            numbers = [int(v) for v in parts[1:]]
            adc_vals = numbers[8:]
            if not 0 <= numbers[3] <= 5 or any(not 0 <= n <= 1023 for n in adc_vals):
                raise ValueError("valores fora da faixa ADC/fase")
            mq2 = adc_vals[0]
            mq3 = adc_vals[1] if len(adc_vals) > 1 else 0
            mq5 = adc_vals[2] if len(adc_vals) > 2 else 0
            return {
                "type": "DATA",
                "ms": numbers[0],
                "tempo_s": numbers[0] // 1000,
                "run_id": numbers[1],
                "cycle": numbers[2],
                "phase": numbers[3],
                "phase_ms": numbers[4],
                "air": numbers[5],
                "gas": numbers[6],
                "outlet": numbers[7],
                "adc": adc_vals,
                "mq2": mq2,
                "mq3": mq3,
                "mq5": mq5,
                "mq2_v": adc_to_voltage(mq2),
                "mq3_v": adc_to_voltage(mq3),
                "mq5_v": adc_to_voltage(mq5),
                "temp": 25.0,
                "hum": 50.0,
                "pressao": 942.5,
            }
        if kind == "STATUS":
            if len(parts) == 10:
                # STATUS,<cicloAtivo>,<currentStage>,<tempoTotal>,<s0>,<s1>,<s2>,<s3>,<s4>,<s5>
                n = [int(v) for v in parts[1:]]
                return {
                    "type": "STATUS",
                    "running": bool(n[0]),
                    "stage": n[1],
                    "phase": n[1],
                    "tempo_s": n[2],
                    "stage_durations_ms": n[3:9],
                }
            if len(parts) == 8:
                n = [int(v) for v in parts[1:]]
                return {
                    "type": "STATUS",
                    "run_id": n[0],
                    "running": bool(n[1]),
                    "cycle": n[2],
                    "phase": n[3],
                    "phase_ms": n[4],
                    "duration": n[5],
                    "repeats": n[6],
                }
        if kind == "EVENT" and len(parts) >= 2:
            return {"type": "EVENT", "name": parts[1], "args": parts[2:]}
        if kind == "ACK" and len(parts) >= 2:
            return {"type": "ACK", "name": parts[1], "args": parts[2:]}
        if kind == "ERR" and len(parts) >= 2:
            return {"type": "ERR", "message": ",".join(parts[1:])}
        if kind == "HELLO" and len(parts) == 3:
            return {"type": "HELLO", "protocol": parts[1], "channels": int(parts[2])}
        if kind == "PONG":
            return {"type": "PONG"}
    except (ValueError, IndexError) as exc:
        raise ValueError(f"Mensagem invalida: {text!r}") from exc

    raise ValueError(f"Mensagem desconhecida/incompleta: {text!r}")
