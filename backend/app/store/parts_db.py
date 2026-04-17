"""SQLite-backed store for Part records + many-to-many compatibility table."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

from app.schemas import Part

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "parts.sqlite"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS parts (
    ps_number TEXT PRIMARY KEY,
    appliance_type TEXT NOT NULL,
    brand TEXT,
    name TEXT NOT NULL,
    oem_number TEXT,
    price_usd REAL,
    in_stock INTEGER,
    blob TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_parts_appliance ON parts(appliance_type);
CREATE INDEX IF NOT EXISTS idx_parts_brand ON parts(brand);

CREATE TABLE IF NOT EXISTS compat (
    ps_number TEXT NOT NULL,
    model_number TEXT NOT NULL,
    PRIMARY KEY (ps_number, model_number)
);
CREATE INDEX IF NOT EXISTS idx_compat_model ON compat(model_number);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def upsert_part(part: Part) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO parts (ps_number, appliance_type, brand, name, oem_number,
                               price_usd, in_stock, blob)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ps_number) DO UPDATE SET
                appliance_type=excluded.appliance_type,
                brand=excluded.brand,
                name=excluded.name,
                oem_number=excluded.oem_number,
                price_usd=excluded.price_usd,
                in_stock=excluded.in_stock,
                blob=excluded.blob
            """,
            (
                part.ps_number,
                part.appliance_type,
                part.brand,
                part.name,
                part.oem_number,
                part.price_usd,
                int(part.in_stock) if part.in_stock is not None else None,
                part.model_dump_json(),
            ),
        )
        conn.commit()


def upsert_compat(ps_number: str, model_numbers: Iterable[str]) -> int:
    rows = [(ps_number, m) for m in model_numbers if m]
    if not rows:
        return 0
    with connect() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO compat (ps_number, model_number) VALUES (?, ?)",
            rows,
        )
        conn.commit()
        return len(rows)


def get_part(ps_number: str) -> Part | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT blob FROM parts WHERE ps_number = ?", (ps_number,)
        ).fetchone()
    if row is None:
        return None
    return Part.model_validate_json(row["blob"])


def get_parts(ps_numbers: Iterable[str]) -> dict[str, Part]:
    ids = list(ps_numbers)
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    with connect() as conn:
        rows = conn.execute(
            f"SELECT ps_number, blob FROM parts WHERE ps_number IN ({placeholders})",
            ids,
        ).fetchall()
    return {r["ps_number"]: Part.model_validate_json(r["blob"]) for r in rows}


def check_compat(ps_number: str, model_number: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM compat WHERE ps_number = ? AND model_number = ? LIMIT 1",
            (ps_number, model_number),
        ).fetchone()
    return row is not None


def compat_count(ps_number: str) -> int:
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM compat WHERE ps_number = ?", (ps_number,)
        ).fetchone()
    return int(row["n"])


def total_parts() -> int:
    with connect() as conn:
        return int(conn.execute("SELECT COUNT(*) AS n FROM parts").fetchone()["n"])
