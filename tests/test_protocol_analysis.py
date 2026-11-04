import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from desktop.analysis import (
    CONFIG_NAMES,
    GAS_INFO,
    SENSORES,
    AnalisadorGases,
    cycle_features,
    format_v043_filename,
    realtime_metrics,
)
from desktop.protocol import STAGE_NAMES, parse_line
from desktop.storage import Storage
from desktop.version import get_local_version, is_newer_version, parse_version_tuple


class ProtocolTests(unittest.TestCase):
    def test_parse_legacy_sensor_values(self):
        d = parse_line("DATA,100,1,1,2,5000,0,1,1,200,300,400,500")
        self.assertEqual(d["adc"], [200, 300, 400, 500])
        self.assertEqual(d["phase"], 2)
        self.assertEqual(d["gas"], 1)

    def test_parse_legacy_status(self):
        self.assertEqual(parse_line("STATUS,5,1,2,3,900,25,4")["repeats"], 4)

    def test_parse_v042_mega_python_serial_csv(self):
        d = parse_line("12,218,438,352,29.24,52.96")
        self.assertEqual(d["type"], "READING")
        self.assertEqual(d["tempo_s"], 12)
        self.assertEqual(d["adc"], [218, 438, 352])
        self.assertAlmostEqual(d["temp"], 29.24)
        self.assertAlmostEqual(d["hum"], 52.96)

    def test_parse_v042_stages_and_events(self):
        st = parse_line("Etapa 2")
        self.assertEqual(st["type"], "STAGE")
        self.assertEqual(st["stage"], 2)
        self.assertEqual(
            st["relays"],
            {"V1": "HIGH", "V2": "LOW", "V3": "LOW", "BOMBA": "LOW"},
        )
        self.assertIn(2, STAGE_NAMES)

        su = parse_line("Etapa 1 tempo atualizado para 60000 ms")
        self.assertEqual(su["type"], "STAGE_TIME")
        self.assertEqual(su["stage"], 1)
        self.assertEqual(su["duration_ms"], 60000)

        sh = parse_line("Etapa 4: 60000")
        self.assertEqual(sh["type"], "STAGE_TIME")
        self.assertEqual(sh["stage"], 4)
        self.assertEqual(sh["duration_ms"], 60000)

        self.assertEqual(parse_line("CICLO STARTED")["name"], "STARTED")
        self.assertEqual(parse_line("CICLO STOPPED")["name"], "STOPPED")
        self.assertEqual(parse_line("CICLO FINALIZADO")["name"], "FINISHED")
        self.assertEqual(parse_line("RESET")["name"], "RESET")
        self.assertEqual(
            parse_line("Tempo(s),MQ2(A0),MQ3(A1),MQ5(A2),Temperatura(C),Umidade(%)")["type"],
            "HEADER",
        )

    def test_reject_malformed(self):
        for line in ["DATA,4,2", "DATA,100,1,1,2,5000,0,1,1,1024,2,3,4", "GARBAGE"]:
            with self.assertRaises(ValueError):
                parse_line(line)


class AnalysisTests(unittest.TestCase):
    def test_legacy_baseline_and_peak(self):
        rows = [
            {"cycle": 1, "phase": 1, "ms": 100, "adc": [100, 200, 300, 400]},
            {"cycle": 1, "phase": 1, "ms": 200, "adc": [100, 200, 300, 400]},
            {"cycle": 1, "phase": 2, "ms": 300, "adc": [120, 190, 310, 400]},
            {"cycle": 1, "phase": 2, "ms": 400, "adc": [130, 180, 320, 400]},
        ]
        f = cycle_features(rows, 1)
        self.assertEqual(f[0]["baseline_adc"], 100)
        self.assertEqual(f[0]["peak_delta_adc"], 30)
        self.assertEqual(f[0]["peak_change_pct"], 30)
        self.assertEqual(f[1]["peak_delta_adc"], -20)
        self.assertAlmostEqual(f[0]["auc_adc_seconds"], 2.5)
        self.assertIsNone(cycle_features(rows, 2)[0]["baseline_adc"])

    def test_v043_directives_and_metrics(self):
        self.assertEqual(SENSORES, ["MQ2", "MQ3", "MQ5"])
        self.assertIn("E", GAS_INFO)
        self.assertIn("P", GAS_INFO)
        self.assertIn("A", GAS_INFO)
        self.assertEqual(CONFIG_NAMES[0], "Default")
        self.assertEqual(CONFIG_NAMES[1], "Config V")

        analisador = AnalisadorGases()
        v = analisador.converter_adc_para_tensao(pd.Series([0, 511.5, 1023]))
        self.assertAlmostEqual(float(v.iloc[0]), 0.0)
        self.assertAlmostEqual(float(v.iloc[1]), 2.5, places=3)
        self.assertAlmostEqual(float(v.iloc[2]), 5.0)

        tempos = np.arange(0, 190, 1.0)
        tensao = np.where(
            tempos <= 60,
            1.0,
            np.where(
                tempos <= 95,
                1.0 + 2.0 * ((tempos - 60.0) / 35.0),
                3.0 - 1.8 * ((tempos - 95.0) / 95.0),
            ),
        )
        df = pd.DataFrame(
            {
                "tempo": tempos,
                "MQ2_V": tensao,
                "MQ3_V": tensao * 0.8,
                "MQ5_V": tensao * 0.6,
            }
        )
        df_suave = analisador.suavizar(df, janela=5)
        m = analisador.calcular_metricas_avancadas(df_suave, "MQ2", baseline_limit_s=60.0)
        self.assertTrue(bool(m))
        self.assertAlmostEqual(m["V_baseline (V)"], 1.0, places=2)
        self.assertGreater(m["V_max Relativo (V)"], 1.8)
        self.assertGreater(m["AUC (V·s)"], 50.0)
        self.assertIsNotNone(m["Tempo Subida (s)"])

    def test_realtime_metrics_from_buffer(self):
        times = [float(t) for t in range(0, 40)]
        adc_series = {
            "MQ2": [205 if t <= 10 else min(850, 205 + (t - 10) * 18) for t in range(0, 40)],
            "MQ3": [410 for _ in range(0, 40)],
            "MQ5": [320 for _ in range(0, 40)],
        }
        rt = realtime_metrics(times, adc_series, janela=3, baseline_limit_s=10.0)
        self.assertEqual(len(rt), 3)
        self.assertTrue(rt[0]["Sensor"].startswith("MQ2"))
        self.assertGreater(rt[0]["ΔV Relativo (V)"], 1.5)


class StorageTests(unittest.TestCase):
    def test_persistence_and_v043_export(self):
        with tempfile.TemporaryDirectory() as root:
            storage = Storage(Path(root) / "test.sqlite3")
            sid = storage.begin(
                "A0-R1-100",
                "Acetone",
                "Config 0",
                60,
                1,
                "SIMULACAO",
                gas_code="A",
                config_id=0,
                rep_code="R1",
                concentration_ppm=100,
                volume_ml=200,
                stage_durations_ms=[0, 60000, 30000, 30000, 60000, 10000],
            )
            measurement = parse_line("0,218,438,352,29.24,52.96")
            storage.reading(sid, measurement)
            storage.finish(sid, "CONCLUIDO")

            csv_path = Path(root) / "out.csv"
            storage.export_csv(sid, csv_path)
            self.assertIn("adc0,adc1,adc2,adc3", csv_path.read_text(encoding="utf-8-sig"))

            v043_file = Path(root) / "dados" / "0" / format_v043_filename("A", 0, "R1", 100)
            storage.export_v043_csv(sid, v043_file)
            self.assertTrue(v043_file.exists())
            content = v043_file.read_text(encoding="utf-8")
            self.assertIn("Tempo(s);MQ2(A0);MQ3(A1);MQ5(A2);Temperatura(C);Umidade(%);Pressao(hPa)", content)
            self.assertIn("0;218;438;352;29.24;52.96;942.5", content)

            # Verify AnalisadorGases can load the exported v0.4.3 directory
            analisador = AnalisadorGases()
            dfs_dict, df_media = analisador.carregar_dados(Path(root) / "dados", "A", 0, 100)
            self.assertIsNotNone(dfs_dict)
            self.assertIsNotNone(df_media)
            self.assertIn("R1", dfs_dict)
            self.assertEqual(len(df_media), 1)
            storage.close()


class UpdaterAndVersionTests(unittest.TestCase):
    def test_version_parsing_and_comparison(self):
        self.assertEqual(parse_version_tuple("v0.4.3"), (0, 4, 3))
        self.assertEqual(parse_version_tuple("0.4.3.1"), (0, 4, 3, 1))
        self.assertTrue(is_newer_version("0.4.4", "0.4.3"))
        self.assertTrue(is_newer_version("v0.5.0", "0.4.3"))
        self.assertFalse(is_newer_version("0.4.3", "0.4.3"))
        self.assertFalse(is_newer_version("0.4.2", "0.4.3"))
        self.assertEqual(get_local_version(), "0.4.3")


if __name__ == "__main__":
    unittest.main()
