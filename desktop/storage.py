"""Persistencia local SQLite e exportacao CSV no padrao v0.4.3."""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Storage:
    def __init__(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sample_name TEXT NOT NULL,
                operator TEXT,
                notes TEXT,
                started_at_utc TEXT NOT NULL,
                finished_at_utc TEXT,
                phase_duration_s INTEGER NOT NULL,
                repetitions INTEGER NOT NULL,
                status TEXT NOT NULL,
                mode TEXT NOT NULL,
                gas_code TEXT DEFAULT 'A',
                config_id INTEGER DEFAULT 0,
                rep_code TEXT DEFAULT 'R1',
                concentration_ppm INTEGER DEFAULT 100,
                volume_ml INTEGER DEFAULT 200,
                stage_durations_json TEXT DEFAULT '[0,60000,30000,30000,60000,10000]'
            );
            CREATE TABLE IF NOT EXISTS readings(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                captured_at_utc TEXT NOT NULL,
                arduino_ms INTEGER NOT NULL,
                run_id INTEGER NOT NULL,
                cycle INTEGER NOT NULL,
                phase INTEGER NOT NULL,
                phase_ms INTEGER NOT NULL,
                air INTEGER NOT NULL,
                gas INTEGER NOT NULL,
                outlet INTEGER NOT NULL,
                adc0 INTEGER NOT NULL,
                adc1 INTEGER NOT NULL,
                adc2 INTEGER NOT NULL,
                adc3 INTEGER NOT NULL,
                tempo_s INTEGER DEFAULT 0,
                temp_c REAL DEFAULT 25.0,
                hum_pct REAL DEFAULT 50.0,
                pressao_hpa REAL DEFAULT 942.5
            );
            CREATE INDEX IF NOT EXISTS idx_readings_session ON readings(session_id, id);
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id),
                captured_at_utc TEXT NOT NULL,
                event TEXT NOT NULL
            );
            """
        )
        self._ensure_columns()
        self.db.commit()
        self._pending = 0

    def _ensure_columns(self):
        """Garante migracao suave caso o banco ja exista de versao anterior."""
        cur = self.db.execute("PRAGMA table_info(sessions)")
        sess_cols = {row[1] for row in cur.fetchall()}
        for col, col_def in [
            ("gas_code", "TEXT DEFAULT 'A'"),
            ("config_id", "INTEGER DEFAULT 0"),
            ("rep_code", "TEXT DEFAULT 'R1'"),
            ("concentration_ppm", "INTEGER DEFAULT 100"),
            ("volume_ml", "INTEGER DEFAULT 200"),
            ("stage_durations_json", "TEXT DEFAULT '[0,60000,30000,30000,60000,10000]'"),
        ]:
            if col not in sess_cols:
                self.db.execute(f"ALTER TABLE sessions ADD COLUMN {col} {col_def}")

        cur = self.db.execute("PRAGMA table_info(readings)")
        read_cols = {row[1] for row in cur.fetchall()}
        for col, col_def in [
            ("tempo_s", "INTEGER DEFAULT 0"),
            ("temp_c", "REAL DEFAULT 25.0"),
            ("hum_pct", "REAL DEFAULT 50.0"),
            ("pressao_hpa", "REAL DEFAULT 942.5"),
        ]:
            if col not in read_cols:
                self.db.execute(f"ALTER TABLE readings ADD COLUMN {col} {col_def}")

    def begin(
        self,
        sample: str,
        operator: str = "",
        notes: str = "",
        duration: int = 190,
        repetitions: int = 1,
        mode: str = "SERIAL",
        *,
        gas_code: str = "A",
        config_id: int = 0,
        rep_code: str = "R1",
        concentration_ppm: int = 100,
        volume_ml: int = 200,
        stage_durations_ms: list[int] | None = None,
    ) -> int:
        stages_json = json.dumps(stage_durations_ms or [0, 60000, 30000, 30000, 60000, 10000])
        cur = self.db.execute(
            """INSERT INTO sessions
            (sample_name, operator, notes, started_at_utc, phase_duration_s,
             repetitions, status, mode, gas_code, config_id, rep_code,
             concentration_ppm, volume_ml, stage_durations_json)
             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                sample,
                operator,
                notes,
                timestamp(),
                duration,
                repetitions,
                "EM_EXECUCAO",
                mode,
                gas_code,
                int(config_id),
                rep_code,
                int(concentration_ppm),
                int(volume_ml),
                stages_json,
            ),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def reading(self, session_id: int, data: dict, current_stage: int = 1):
        tempo_s = int(data.get("tempo_s", data.get("ms", 0) // 1000))
        ms = int(data.get("ms", tempo_s * 1000))
        run_id = int(data.get("run_id", 1))
        cycle = int(data.get("cycle", 1))
        phase = int(data.get("phase", current_stage))
        phase_ms = int(data.get("phase_ms", 0))
        air = int(data.get("air", 1 if phase in (1, 4) else 0))
        gas = int(data.get("gas", 1 if phase == 2 else 0))
        outlet = int(data.get("outlet", 1 if phase in (1, 2) else 0))

        adc = list(data.get("adc", [data.get("mq2", 0), data.get("mq3", 0), data.get("mq5", 0)]))
        while len(adc) < 4:
            adc.append(0)

        temp_c = float(data.get("temp", 25.0))
        hum_pct = float(data.get("hum", 50.0))
        pressao_hpa = float(data.get("pressao", 942.5))

        self.db.execute(
            """INSERT INTO readings
            (session_id,captured_at_utc,arduino_ms,run_id,cycle,phase,phase_ms,
             air,gas,outlet,adc0,adc1,adc2,adc3,tempo_s,temp_c,hum_pct,pressao_hpa)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                session_id,
                timestamp(),
                ms,
                run_id,
                cycle,
                phase,
                phase_ms,
                air,
                gas,
                outlet,
                int(adc[0]),
                int(adc[1]),
                int(adc[2]),
                int(adc[3]),
                tempo_s,
                temp_c,
                hum_pct,
                pressao_hpa,
            ),
        )
        self._pending += 1
        if self._pending >= 10:
            self.flush()

    def event(self, session_id: int | None, name: str):
        self.db.execute(
            "INSERT INTO events(session_id,captured_at_utc,event) VALUES (?,?,?)",
            (session_id, timestamp(), name),
        )

    def finish(self, session_id: int, status: str):
        self.db.execute(
            """UPDATE sessions SET status=?, finished_at_utc=? WHERE id=?""",
            (status, timestamp(), session_id),
        )
        self.flush()

    def flush(self):
        self.db.commit()
        self._pending = 0

    def export_v043_csv(self, session_id: int, destination: str | Path):
        """Exporta o ensaio no formato exato dos analisadores do Sistema gas/v0.4.3 (separador ';')."""
        self.flush()
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        sql = """SELECT tempo_s, adc0, adc1, adc2, temp_c, hum_pct, pressao_hpa
                 FROM readings WHERE session_id=? ORDER BY id"""
        rows = self.db.execute(sql, (session_id,)).fetchall()
        with open(destination, "w", newline="", encoding="utf-8") as f:
            out = csv.writer(f, delimiter=";")
            out.writerow(
                [
                    "Tempo(s)",
                    "MQ2(A0)",
                    "MQ3(A1)",
                    "MQ5(A2)",
                    "Temperatura(C)",
                    "Umidade(%)",
                    "Pressao(hPa)",
                ]
            )
            for tempo_s, mq2, mq3, mq5, temp_c, hum_pct, pressao_hpa in rows:
                out.writerow(
                    [
                        int(tempo_s),
                        int(mq2),
                        int(mq3),
                        int(mq5),
                        round(float(temp_c), 2),
                        round(float(hum_pct), 2),
                        round(float(pressao_hpa), 2),
                    ]
                )

    def export_csv(self, session_id: int, destination: str | Path):
        """Exporta CSV completo (compativel com v0.4.3 e testes unitarios)."""
        self.flush()
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        sql = """SELECT captured_at_utc, arduino_ms, run_id, cycle, phase, phase_ms,
                        air, gas, outlet, adc0, adc1, adc2, adc3,
                        tempo_s, temp_c, hum_pct, pressao_hpa
                 FROM readings WHERE session_id=? ORDER BY id"""
        with open(destination, "w", newline="", encoding="utf-8-sig") as f:
            out = csv.writer(f)
            out.writerow(
                [
                    "captured_at_utc",
                    "arduino_ms",
                    "run_id",
                    "cycle",
                    "phase",
                    "phase_ms",
                    "air",
                    "gas",
                    "outlet",
                    "adc0",
                    "adc1",
                    "adc2",
                    "adc3",
                    "Tempo(s)",
                    "Temperatura(C)",
                    "Umidade(%)",
                    "Pressao(hPa)",
                ]
            )
            out.writerows(self.db.execute(sql, (session_id,)))

    def close(self):
        self.flush()
        self.db.close()
