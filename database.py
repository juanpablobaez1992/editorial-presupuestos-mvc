from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "editorial.db"


def get_connection() -> sqlite3.Connection:
    """Devuelve una conexion SQLite lista para usar con filas tipo diccionario."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database() -> None:
    """Crea las tablas necesarias y deja la configuracion base inicializada."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS presupuestos (
                id TEXT PRIMARY KEY,
                nombre_proyecto TEXT NOT NULL,
                cliente TEXT NOT NULL,
                fecha TEXT NOT NULL,
                notas TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS escenarios (
                id TEXT PRIMARY KEY,
                presupuesto_id TEXT NOT NULL,
                nombre TEXT NOT NULL,
                cantidad_copias INTEGER NOT NULL,
                porcentaje_ganancia REAL NOT NULL,
                tipo_de_cambio_snapshot REAL NOT NULL,
                orden INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (presupuesto_id) REFERENCES presupuestos (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                escenario_id TEXT NOT NULL,
                nombre TEXT NOT NULL,
                monto REAL NOT NULL,
                nota TEXT,
                orden INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (escenario_id) REFERENCES escenarios (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_presupuestos_fecha ON presupuestos (fecha DESC);
            CREATE INDEX IF NOT EXISTS idx_presupuestos_nombre ON presupuestos (nombre_proyecto);
            CREATE INDEX IF NOT EXISTS idx_presupuestos_cliente ON presupuestos (cliente);
            CREATE INDEX IF NOT EXISTS idx_escenarios_presupuesto ON escenarios (presupuesto_id, orden);
            CREATE INDEX IF NOT EXISTS idx_items_escenario ON items (escenario_id, orden);
            """
        )

        defaults = {
            "tipo_de_cambio": "1400",
            "tarifa_edicion_por_pagina": "800",
            "tarifa_escaneo_por_pagina": "500",
            "preset_isbn": "50000",
            "preset_banner": "70000",
            "preset_diseno_tapas": "50000",
        }
        connection.executemany(
            """
            INSERT INTO configuracion (clave, valor)
            VALUES (?, ?)
            ON CONFLICT(clave) DO NOTHING
            """,
            defaults.items(),
        )


__all__ = ["DB_PATH", "get_connection", "init_database"]
