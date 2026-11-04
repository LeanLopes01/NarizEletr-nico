"""Diretrizes e Analisador de Dados do Nariz Eletronico v0.4.3.

Integra os algoritmos e parametros de:
  - Sistema gas/v0.4.3/MainTodosJunto.py
  - Sistema gas/v0.4.3/mainGraficos3por3.py
  - Sistema gas/v0.4.3/mainGraficosQuadrados.py
"""
from __future__ import annotations

import os
import re
from pathlib import Path
import numpy as np
import pandas as pd

# --- DIRETRIZES GLOBAIS DO NARIZ ELETRONICO v0.4.3 ---
GAS_INFO: dict[str, str] = {
    "E": "Ethyl Alcohol",
    "P": "Isopropyl Alcohol",
    "A": "Acetone",
    "AR": "Clean Air",
}

GAS_LABELS_PT: dict[str, str] = {
    "A": "A — Acetone (Acetona)",
    "E": "E — Ethyl Alcohol (Alcool Etilico)",
    "P": "P — Isopropyl Alcohol (Alcool Isopropilico)",
    "AR": "AR — Ar Limpo / Referencia",
}

GAS_CODES_3X3: list[str] = ["E", "P", "A"]
GAS_CODES_ALL: list[str] = ["A", "E", "P", "AR"]

CONFIG_IDS: list[int] = [0, 1, 2, 3, 4]
CONFIG_NAMES: dict[int, str] = {
    0: "Default",
    1: "Config V",
    2: "Config A",
    3: "Config X",
    4: "Config O",
}

SENSORES: list[str] = ["MQ2", "MQ3", "MQ5"]
SENSOR_PINS: dict[str, str] = {
    "MQ2": "MQ2(A0)",
    "MQ3": "MQ3(A1)",
    "MQ5": "MQ5(A2)",
}
REPETICOES: list[str] = ["R1", "R2", "R3"]
CONCENTRACOES: list[int] = [100, 200]

# Paletas cientificas/industriais de alto contraste
CORES_SENSORES: dict[str, str] = {
    "MQ2": "#38bdf8",  # Ciano Industrial
    "MQ3": "#34d399",  # Verde Esmeralda
    "MQ5": "#f59e0b",  # Ambar / Ouro
}
CORES_NEON: dict[str, str] = {
    "R1": "#f43f5e",   # Rosa/Vermelho Neon
    "R2": "#38bdf8",   # Azul Ciano
    "R3": "#10b981",   # Verde
}
CORES_CONFIG: dict[int, str] = {
    0: "#f8fafc",      # Default (Branco/Cinza claro no tema escuro)
    1: "#ef4444",      # Config V (Vermelho)
    2: "#38bdf8",      # Config A (Azul)
    3: "#10b981",      # Config X (Verde)
    4: "#f59e0b",      # Config O (Ambar)
}
CORES_GASES: dict[str, str] = {
    "A": "#f43f5e",
    "E": "#38bdf8",
    "P": "#10b981",
    "AR": "#94a3b8",
}


def default_v043_data_dir() -> Path:
    """Localiza automaticamente a pasta de dados do v0.4.3 ou cria pasta local ./dados."""
    here = Path(__file__).resolve().parent.parent
    candidate_v043 = here.parent / "Sistema gás" / "v0.4.3" / "dados"
    if candidate_v043.exists():
        return candidate_v043
    local_dados = here / "dados"
    local_dados.mkdir(parents=True, exist_ok=True)
    return local_dados


def format_v043_filename(gas: str, config_id: int, rep: str, conc: int) -> str:
    """Gera o nome de arquivo padrao v0.4.3: ex. A0-R1-100.csv."""
    return f"{gas.upper()}{int(config_id)}-{rep.upper()}-{int(conc)}.csv"


class AnalisadorGases:
    """Analisador completo de sinais e matrizes do Nariz Eletronico v0.4.3."""

    def __init__(self, volume_recipiente: int = 200, concentracao_padrao: int = 100):
        self.volume_recipiente = volume_recipiente
        self.concentracao_padrao = concentracao_padrao
        self.total_linhas_lidas = 0
        self.total_arquivos_lidos = 0

    def extrair_concentracao(self, filename: str) -> int:
        match = re.search(r"-(\d+)\.csv$", filename, re.IGNORECASE)
        return int(match.group(1)) if match else self.concentracao_padrao

    @staticmethod
    def converter_adc_para_tensao(valor_adc: float | np.ndarray | pd.Series):
        return (valor_adc / 1023.0) * 5.0

    def _ler_csv_flexivel(self, filepath: str | Path) -> pd.DataFrame:
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
            first_line = f.readline()
        sep = ";" if ";" in first_line else ","
        df = pd.read_csv(filepath, delimiter=sep)
        self.total_linhas_lidas += len(df)
        self.total_arquivos_lidos += 1

        df.columns = [c.strip() for c in df.columns]
        mapeamento = {
            "MQ2(A0)": "MQ2",
            "MQ3(A1)": "MQ3",
            "MQ5(A2)": "MQ5",
            "adc0": "MQ2",
            "adc1": "MQ3",
            "adc2": "MQ5",
            "Tempo(s)": "tempo",
            "tempo_s": "tempo",
            "Temperatura(C)": "Temperatura",
            "temp": "Temperatura",
            "Umidade(%)": "Umidade",
            "hum": "Umidade",
            "Pressao(hPa)": "Pressao",
            "pressao": "Pressao",
        }
        df = df.rename(columns={k: v for k, v in mapeamento.items() if k in df.columns})

        for col in SENSORES:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df[f"{col}_V"] = self.converter_adc_para_tensao(df[col])

        for col_amb in ("Tempo", "tempo", "Pressao", "Temperatura", "Umidade"):
            if col_amb in df.columns:
                df[col_amb] = pd.to_numeric(df[col_amb], errors="coerce")

        return df.dropna(how="all")

    def carregar_dados(
        self, pasta_base: str | Path, gas: str, config: int, concentracao_alvo: int
    ) -> tuple[dict[str, pd.DataFrame] | None, pd.DataFrame | None]:
        dfs_dict: dict[str, pd.DataFrame] = {}
        pasta_config = Path(pasta_base) / str(config)
        if not pasta_config.exists():
            return None, None

        for rep in REPETICOES:
            prefixo = f"{gas}{config}-{rep}-"
            try:
                arquivos = [
                    f.name
                    for f in pasta_config.iterdir()
                    if f.is_file() and f.name.upper().startswith(prefixo.upper()) and f.name.lower().endswith(".csv")
                ]
                arquivo_valido = next(
                    (f for f in arquivos if self.extrair_concentracao(f) == int(concentracao_alvo)),
                    None,
                )
                if arquivo_valido:
                    df = self._ler_csv_flexivel(pasta_config / arquivo_valido)
                    if not df.empty:
                        dfs_dict[rep] = df
            except Exception:
                continue

        if not dfs_dict:
            return None, None

        min_len = min(len(df) for df in dfs_dict.values())
        if min_len == 0:
            return None, None

        dfs_truncados = {rep: df.head(min_len).reset_index(drop=True) for rep, df in dfs_dict.items()}
        df_concat = pd.concat(list(dfs_truncados.values()))
        df_media = df_concat.groupby(df_concat.index).mean(numeric_only=True)

        for col in SENSORES:
            if col in df_media.columns and f"{col}_V" not in df_media.columns:
                df_media[f"{col}_V"] = self.converter_adc_para_tensao(df_media[col])

        return dfs_truncados, df_media

    @staticmethod
    def suavizar(df: pd.DataFrame, janela: int = 5) -> pd.DataFrame:
        janela = max(1, int(janela))
        if janela <= 1 or df.empty:
            return df.copy()
        df_suave = df.copy()
        for col in df_suave.columns:
            if col != "tempo" and pd.api.types.is_numeric_dtype(df_suave[col]):
                df_suave[col] = df_suave[col].rolling(window=janela, center=True, min_periods=1).mean()
        return df_suave

    def calcular_metricas_avancadas(
        self,
        df_media: pd.DataFrame,
        sensor: str,
        dfs_individuais: dict[str, pd.DataFrame] | None = None,
        baseline_limit_s: float = 60.0,
    ) -> dict:
        col_v = f"{sensor}_V"
        if df_media is None or df_media.empty or col_v not in df_media.columns:
            return {}

        tempo = (
            df_media["tempo"].to_numpy(dtype=float)
            if "tempo" in df_media.columns
            else np.arange(len(df_media), dtype=float)
        )
        sinal = df_media[col_v].to_numpy(dtype=float)
        valid = np.isfinite(tempo) & np.isfinite(sinal)
        if not np.any(valid):
            return {}
        tempo = tempo[valid]
        sinal = sinal[valid]

        mask_base = tempo <= baseline_limit_s
        v_baseline = float(np.min(sinal[mask_base])) if np.any(mask_base) else float(np.min(sinal))
        v_max = float(np.max(sinal))
        idx_max = int(np.argmax(sinal))
        t_max = float(tempo[idx_max])
        diferencial = v_max - v_baseline

        if len(sinal) >= 2:
            # Garante passo nao-zero para np.gradient
            dt = np.diff(tempo)
            if np.all(dt > 0):
                gradiente = np.gradient(sinal, tempo)
            else:
                gradiente = np.gradient(sinal)
            taxa_maxima = float(np.max(gradiente))
        else:
            taxa_maxima = 0.0

        # Tempo de subida (10% -> 90%)
        limiar_10 = v_baseline + 0.10 * diferencial
        limiar_90 = v_baseline + 0.90 * diferencial
        tempo_subida = None
        if diferencial > 1e-4 and idx_max > 0:
            sinal_ate_pico = sinal[: idx_max + 1]
            tempo_ate_pico = tempo[: idx_max + 1]
            i10 = np.where(sinal_ate_pico >= limiar_10)[0]
            i90 = np.where(sinal_ate_pico >= limiar_90)[0]
            if len(i10) > 0 and len(i90) > 0 and i90[0] >= i10[0]:
                tempo_subida = float(tempo_ate_pico[i90[0]] - tempo_ate_pico[i10[0]])

        # Tempo de descida / recuperacao (90% -> 10% pos-pico)
        tempo_descida = None
        if diferencial > 1e-4 and idx_max < len(sinal) - 1:
            sinal_pos = sinal[idx_max:]
            tempo_pos = tempo[idx_max:]
            r90 = np.where(sinal_pos <= limiar_90)[0]
            r10 = np.where(sinal_pos <= limiar_10)[0]
            if len(r90) > 0 and len(r10) > 0 and r10[0] >= r90[0]:
                tempo_descida = float(tempo_pos[r10[0]] - tempo_pos[r90[0]])

        # Area sob a curva relativa (AUC em V*s)
        if len(sinal) >= 2:
            _trapz = getattr(np, "trapezoid", None) or getattr(np, "trapz")
            auc_vs = float(_trapz(np.abs(sinal - v_baseline), tempo))
        else:
            auc_vs = 0.0

        # Erro multiplicativo entre repeticoes no pico (%)
        erro_mult = None
        if dfs_individuais:
            valores_pico = []
            for df_ind in dfs_individuais.values():
                if col_v in df_ind.columns and len(df_ind) > idx_max:
                    valores_pico.append(float(df_ind[col_v].iloc[idx_max]))
            if len(valores_pico) > 1:
                media_p = float(np.mean(valores_pico))
                if abs(media_p) > 1e-9:
                    erro_mult = float((np.std(valores_pico, ddof=1) / media_p) * 100.0)

        return {
            "Sensor": sensor,
            "V_baseline (V)": v_baseline,
            "V_max Abs (V)": v_max,
            "V_max Relativo (V)": diferencial,
            "Tempo V_max (s)": t_max,
            "Taxa Max (V/s)": taxa_maxima,
            "Tempo Subida (s)": tempo_subida,
            "Tempo Descida (s)": tempo_descida,
            "AUC (V·s)": auc_vs,
            "Erro Mult. (%)": erro_mult,
        }

    def gerar_matriz_completa(self, pasta_base: str | Path, concentracao_alvo: int, janela: int = 5) -> pd.DataFrame:
        dados_matriz = []
        for config_id in CONFIG_IDS:
            for gas in GAS_CODES_3X3:
                _, df_media = self.carregar_dados(pasta_base, gas, config_id, concentracao_alvo)
                if df_media is not None:
                    df_media = self.suavizar(df_media, janela=janela)
                    for sensor in SENSORES:
                        m = self.calcular_metricas_avancadas(df_media, sensor)
                        if m:
                            dados_matriz.append(
                                {
                                    "Config": CONFIG_NAMES[config_id],
                                    "Sensor": sensor,
                                    "Gas": GAS_INFO.get(gas, gas),
                                    "Vmax_Relativo": m["V_max Relativo (V)"],
                                }
                            )
        df = pd.DataFrame(dados_matriz)
        if not df.empty:
            return df.pivot_table(index=["Config", "Sensor"], columns="Gas", values="Vmax_Relativo").reset_index()
        return pd.DataFrame()

    def gerar_tabelas_comparativas(
        self, pasta_base: str | Path, concentracao_alvo: int, janela: int = 5
    ) -> dict[str, pd.DataFrame]:
        """Gera matrizes comparativas por sensor com Vmax Relativo (V) e (% vs Default)."""
        dados: dict[str, dict[str, dict[str, float | str]]] = {
            s: {g: {} for g in GAS_CODES_3X3} for s in SENSORES
        }

        for config_id in CONFIG_IDS:
            config_name = CONFIG_NAMES[config_id]
            for gas in GAS_CODES_3X3:
                _, df_media = self.carregar_dados(pasta_base, gas, config_id, concentracao_alvo)
                if df_media is not None:
                    df_media = self.suavizar(df_media, janela=janela)
                    for sensor in SENSORES:
                        m = self.calcular_metricas_avancadas(df_media, sensor)
                        if m:
                            dados[sensor][gas][config_name] = round(m["V_max Relativo (V)"], 2)

        baseline_name = CONFIG_NAMES[0]  # 'Default'
        for sensor in SENSORES:
            for gas in GAS_CODES_3X3:
                row_data = dados[sensor][gas]
                val_base = row_data.get(baseline_name)
                for cfg_name in list(row_data.keys()):
                    val_atual = float(row_data[cfg_name])
                    if isinstance(val_base, (int, float)) and val_base > 0.0:
                        pct = (val_atual / float(val_base)) * 100.0
                        row_data[cfg_name] = f"{val_atual:.2f} V ({pct:.1f}%)"
                    elif cfg_name == baseline_name:
                        row_data[cfg_name] = f"{val_atual:.2f} V (100.0%)"
                    else:
                        row_data[cfg_name] = f"{val_atual:.2f} V (N/A)"

        dfs_finais: dict[str, pd.DataFrame] = {}
        for sensor in SENSORES:
            df = pd.DataFrame.from_dict(dados[sensor], orient="index")
            df.index = df.index.map(lambda g: GAS_INFO.get(g, g))
            cols_existentes = [CONFIG_NAMES[i] for i in CONFIG_IDS if CONFIG_NAMES[i] in df.columns]
            if cols_existentes:
                df = df[cols_existentes]
            df = df.reset_index().rename(columns={"index": "Gas"})
            dfs_finais[sensor] = df

        return dfs_finais


def realtime_metrics(
    times: list[float],
    adc_series: dict[str, list[int]],
    janela: int = 5,
    baseline_limit_s: float = 60.0,
) -> list[dict]:
    """Calcula metricas em tempo real durante a aquisicao para MQ2, MQ3 e MQ5."""
    if not times:
        return [
            {
                "Sensor": f"{s} (A{i})",
                "ADC Atual": None,
                "V Atual (V)": None,
                "V_baseline (V)": None,
                "V_max Abs (V)": None,
                "ΔV Relativo (V)": None,
                "Taxa Max (V/s)": None,
                "AUC (V·s)": None,
            }
            for i, s in enumerate(SENSORES)
        ]

    df = pd.DataFrame({"tempo": times})
    for s in SENSORES:
        vals = adc_series.get(s, [])
        df[s] = vals[: len(times)]
        df[f"{s}_V"] = AnalisadorGases.converter_adc_para_tensao(df[s])

    analisador = AnalisadorGases()
    df_suave = analisador.suavizar(df, janela=janela)
    out = []
    for i, s in enumerate(SENSORES):
        m = analisador.calcular_metricas_avancadas(df_suave, s, baseline_limit_s=baseline_limit_s)
        last_adc = int(df[s].iloc[-1]) if len(df) else None
        last_v = float(df[f"{s}_V"].iloc[-1]) if len(df) else None
        out.append(
            {
                "Sensor": f"{s} (A{i})",
                "ADC Atual": last_adc,
                "V Atual (V)": last_v,
                "V_baseline (V)": m.get("V_baseline (V)"),
                "V_max Abs (V)": m.get("V_max Abs (V)"),
                "ΔV Relativo (V)": m.get("V_max Relativo (V)"),
                "Taxa Max (V/s)": m.get("Taxa Max (V/s)"),
                "AUC (V·s)": m.get("AUC (V·s)"),
            }
        )
    return out


def cycle_features(measurements: list[dict], cycle: int = 1) -> list[dict]:
    """Compatibilidade com testes unitarios de extracao por fase."""
    phase1 = [m for m in measurements if m.get("cycle", 1) == cycle and m.get("phase") == 1]
    phase2 = [m for m in measurements if m.get("cycle", 1) == cycle and m.get("phase") == 2]
    num_channels = max((len(m.get("adc", [])) for m in measurements), default=3)
    result = []
    for ch in range(num_channels):
        baseline = None
        delta = None
        relative = None
        auc = None
        if phase1:
            last = phase1[-50:]
            baseline = sum(m["adc"][ch] for m in last if ch < len(m["adc"])) / len(last)
        if baseline is not None and phase2:
            differences = [m["adc"][ch] - baseline for m in phase2 if ch < len(m["adc"])]
            if differences:
                delta = max(differences, key=abs)
                relative = 100.0 * delta / max(abs(baseline), 1.0)
                auc = 0.0
                for before, after in zip(phase2, phase2[1:]):
                    dt = max(0, after["ms"] - before["ms"]) / 1000.0
                    a = abs(before["adc"][ch] - baseline)
                    b = abs(after["adc"][ch] - baseline)
                    auc += (a + b) * 0.5 * dt
        result.append(
            {
                "channel": ch,
                "baseline_adc": baseline,
                "peak_delta_adc": delta,
                "peak_change_pct": relative,
                "auc_adc_seconds": auc,
            }
        )
    return result
