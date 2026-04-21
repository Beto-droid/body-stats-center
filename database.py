"""
SQLite database for Mi Scale measurements.
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "mi_scale.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS measurements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    weight_kg       REAL NOT NULL,
    impedance       INTEGER NOT NULL,
    bmi             REAL,
    fat_percent     REAL,
    muscle_mass_kg  REAL,
    bone_mass_kg    REAL,
    water_percent   REAL,
    visceral_fat    REAL,
    bmr_kcal        INTEGER,
    lean_mass_kg    REAL,
    protein_percent REAL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


CREATE_GYM_SQL = """
CREATE TABLE IF NOT EXISTS gym_sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    exercise     TEXT NOT NULL,
    category     TEXT NOT NULL,
    sets         INTEGER NOT NULL,
    reps         INTEGER NOT NULL,
    weight_kg    REAL NOT NULL,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS cardio_sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    type         TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    distance_km  REAL,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS food_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    food_name    TEXT NOT NULL,
    quantity_g   REAL NOT NULL,
    calories     REAL NOT NULL,
    protein_g    REAL NOT NULL,
    carbs_g      REAL NOT NULL,
    fat_g        REAL NOT NULL
);
"""

def init_db() -> None:
    with _connect() as conn:
        conn.execute(CREATE_TABLE_SQL)
        for stmt in CREATE_GYM_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(stmt)


def save_measurement(
    timestamp: str,
    weight_kg: float,
    impedance: int,
    bmi: float,
    fat_percent: float,
    muscle_mass_kg: float,
    bone_mass_kg: float,
    water_percent: float,
    visceral_fat: float,
    bmr_kcal: int,
    lean_mass_kg: float,
    protein_percent: float,
) -> None:
    sql = """
    INSERT INTO measurements (
        timestamp, weight_kg, impedance,
        bmi, fat_percent, muscle_mass_kg, bone_mass_kg,
        water_percent, visceral_fat, bmr_kcal, lean_mass_kg, protein_percent
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _connect() as conn:
        conn.execute(sql, (
            timestamp, weight_kg, impedance,
            bmi, fat_percent, muscle_mass_kg, bone_mass_kg,
            water_percent, visceral_fat, bmr_kcal, lean_mass_kg, protein_percent,
        ))


def get_measurements_last_days(days: int = 30) -> list[dict]:
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    sql = "SELECT * FROM measurements WHERE timestamp >= ? ORDER BY timestamp ASC"
    with _connect() as conn:
        rows = conn.execute(sql, (since,)).fetchall()
    return [dict(r) for r in rows]


def get_latest_measurement() -> dict | None:
    sql = "SELECT * FROM measurements ORDER BY timestamp DESC LIMIT 1"
    with _connect() as conn:
        row = conn.execute(sql).fetchone()
    return dict(row) if row else None


def get_daily_averages() -> list[dict]:
    """Returns one averaged row per day for all recorded days."""
    sql = """
    SELECT
        date(timestamp) AS day,
        round(avg(weight_kg), 2)       AS weight_kg,
        round(avg(bmi), 1)             AS bmi,
        round(avg(fat_percent), 1)     AS fat_percent,
        round(avg(muscle_mass_kg), 1)  AS muscle_mass_kg,
        round(avg(bone_mass_kg), 2)    AS bone_mass_kg,
        round(avg(water_percent), 1)   AS water_percent,
        round(avg(visceral_fat), 1)    AS visceral_fat,
        round(avg(bmr_kcal), 0)        AS bmr_kcal,
        round(avg(lean_mass_kg), 1)    AS lean_mass_kg,
        round(avg(protein_percent), 1) AS protein_percent,
        count(*)                       AS readings
    FROM measurements
    GROUP BY date(timestamp)
    ORDER BY day ASC
    """
    with _connect() as conn:
        rows = conn.execute(sql).fetchall()
    # rename 'day' -> 'timestamp' so charts work the same way
    return [{**dict(r), "timestamp": r["day"]} for r in rows]


def get_all_measurements() -> list[dict]:
    sql = "SELECT * FROM measurements ORDER BY timestamp ASC"
    with _connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


# ── Gym ───────────────────────────────────────────────────────────────────────

def log_gym_session(date: str, exercise: str, category: str, sets: int, reps: int, weight_kg: float, notes: str = "") -> None:
    sql = "INSERT INTO gym_sessions (date, exercise, category, sets, reps, weight_kg, notes) VALUES (?, ?, ?, ?, ?, ?, ?)"
    with _connect() as conn:
        conn.execute(sql, (date, exercise, category, sets, reps, weight_kg, notes))


def get_gym_sessions(days: int = 30) -> list[dict]:
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    sql = "SELECT * FROM gym_sessions WHERE date >= ? ORDER BY date DESC, id DESC"
    with _connect() as conn:
        rows = conn.execute(sql, (since,)).fetchall()
    return [dict(r) for r in rows]


def get_exercise_history(exercise: str) -> list[dict]:
    sql = "SELECT date, max(weight_kg) as max_kg, sum(sets*reps*weight_kg) as volume FROM gym_sessions WHERE exercise=? GROUP BY date ORDER BY date ASC"
    with _connect() as conn:
        rows = conn.execute(sql, (exercise,)).fetchall()
    return [dict(r) for r in rows]


def delete_gym_session(session_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM gym_sessions WHERE id = ?", (session_id,))


# ── Cardio ────────────────────────────────────────────────────────────────────

def log_cardio(date: str, type_: str, duration_min: int, distance_km: float | None, notes: str = "") -> None:
    sql = "INSERT INTO cardio_sessions (date, type, duration_min, distance_km, notes) VALUES (?, ?, ?, ?, ?)"
    with _connect() as conn:
        conn.execute(sql, (date, type_, duration_min, distance_km, notes))


def get_cardio_sessions(days: int = 30) -> list[dict]:
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    sql = "SELECT * FROM cardio_sessions WHERE date >= ? ORDER BY date DESC"
    with _connect() as conn:
        rows = conn.execute(sql, (since,)).fetchall()
    return [dict(r) for r in rows]


def delete_cardio_session(session_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM cardio_sessions WHERE id = ?", (session_id,))


# ── Nutrition ─────────────────────────────────────────────────────────────────

def log_food(date: str, food_name: str, quantity_g: float, calories: float, protein_g: float, carbs_g: float, fat_g: float) -> None:
    sql = "INSERT INTO food_log (date, food_name, quantity_g, calories, protein_g, carbs_g, fat_g) VALUES (?, ?, ?, ?, ?, ?, ?)"
    with _connect() as conn:
        conn.execute(sql, (date, food_name, quantity_g, calories, protein_g, carbs_g, fat_g))


def get_food_log(days: int = 7) -> list[dict]:
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    sql = "SELECT * FROM food_log WHERE date >= ? ORDER BY date DESC, id DESC"
    with _connect() as conn:
        rows = conn.execute(sql, (since,)).fetchall()
    return [dict(r) for r in rows]


def get_daily_nutrition(days: int = 30) -> list[dict]:
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    sql = """
    SELECT date,
        round(sum(calories), 0) as calories,
        round(sum(protein_g), 1) as protein_g,
        round(sum(carbs_g), 1) as carbs_g,
        round(sum(fat_g), 1) as fat_g
    FROM food_log WHERE date >= ?
    GROUP BY date ORDER BY date ASC
    """
    with _connect() as conn:
        rows = conn.execute(sql, (since,)).fetchall()
    return [dict(r) for r in rows]


def delete_food_entry(entry_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM food_log WHERE id = ?", (entry_id,))

