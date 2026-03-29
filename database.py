from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "editorial.db"


PROJECT_TYPE_DEFAULTS = {
    "novela": {
        "nombre": "Novela",
        "descripcion": "Tirada literaria clasica con foco en edicion interior y tapa editorial.",
        "payload_json": """
        {
            "notas": "Preset orientado a narrativa larga, con foco en lectura corrida y presentacion editorial clasica.",
            "escenarios": [
                {
                    "nombre": "100 copias",
                    "cantidad_copias": 100,
                    "porcentaje_ganancia": 45,
                    "items": [
                        {"nombre": "Impresion", "monto": 0, "nota": "Cotizado manualmente en https://print.livriz.com"},
                        {"nombre": "Edicion interior", "monto": 96000, "nota": "120 pags x tarifa base"},
                        {"nombre": "Diseno tapas", "monto": 50000, "nota": "Preset base de diseno de tapas."},
                        {"nombre": "ISBN", "monto": 50000, "nota": "Preset base de registro editorial."},
                        {"nombre": "Banner", "monto": 70000, "nota": "Preset base de pieza promocional."}
                    ]
                }
            ]
        }
        """.strip(),
    },
    "poesia": {
        "nombre": "Poesia",
        "descripcion": "Formato breve, tiradas cuidadas y costos editoriales mas contenidos.",
        "payload_json": """
        {
            "notas": "Preset pensado para libros breves, con menor volumen de paginas y foco en presentacion cuidada.",
            "escenarios": [
                {
                    "nombre": "80 copias",
                    "cantidad_copias": 80,
                    "porcentaje_ganancia": 42,
                    "items": [
                        {"nombre": "Impresion", "monto": 0, "nota": "Cotizado manualmente en https://print.livriz.com"},
                        {"nombre": "Edicion interior", "monto": 64000, "nota": "80 pags x tarifa base"},
                        {"nombre": "Diseno tapas", "monto": 50000, "nota": "Preset base de diseno de tapas."},
                        {"nombre": "ISBN", "monto": 50000, "nota": "Preset base de registro editorial."}
                    ]
                }
            ]
        }
        """.strip(),
    },
    "institucional": {
        "nombre": "Libro institucional",
        "descripcion": "Proyecto con mayor peso visual, piezas promocionales y dos escalas de tirada.",
        "payload_json": """
        {
            "notas": "Preset para libros institucionales con fuerte presencia de diseno, piezas promocionales y comparacion de tiradas.",
            "escenarios": [
                {
                    "nombre": "150 copias",
                    "cantidad_copias": 150,
                    "porcentaje_ganancia": 48,
                    "items": [
                        {"nombre": "Impresion", "monto": 0, "nota": "Cotizado manualmente en https://print.livriz.com"},
                        {"nombre": "Edicion interior", "monto": 144000, "nota": "180 pags x tarifa base"},
                        {"nombre": "Diseno tapas", "monto": 50000, "nota": "Preset base de diseno de tapas."},
                        {"nombre": "Banner", "monto": 70000, "nota": "Preset base de pieza promocional."},
                        {"nombre": "ISBN", "monto": 50000, "nota": "Preset base de registro editorial."}
                    ]
                },
                {
                    "nombre": "300 copias",
                    "cantidad_copias": 300,
                    "porcentaje_ganancia": 48,
                    "items": [
                        {"nombre": "Impresion", "monto": 0, "nota": "Cotizado manualmente en https://print.livriz.com"},
                        {"nombre": "Edicion interior", "monto": 144000, "nota": "180 pags x tarifa base"},
                        {"nombre": "Diseno tapas", "monto": 50000, "nota": "Preset base de diseno de tapas."},
                        {"nombre": "Banner", "monto": 70000, "nota": "Preset base de pieza promocional."},
                        {"nombre": "ISBN", "monto": 50000, "nota": "Preset base de registro editorial."}
                    ]
                }
            ]
        }
        """.strip(),
    },
    "catalogo": {
        "nombre": "Catalogo",
        "descripcion": "Produccion visual, mayor carga de diseno y comparacion rapida por volumen.",
        "payload_json": """
        {
            "notas": "Preset para catalogos o libros visuales con fuerte presencia grafica y trabajo de piezas complementarias.",
            "escenarios": [
                {
                    "nombre": "50 copias",
                    "cantidad_copias": 50,
                    "porcentaje_ganancia": 50,
                    "items": [
                        {"nombre": "Impresion", "monto": 0, "nota": "Cotizado manualmente en https://print.livriz.com"},
                        {"nombre": "Edicion interior", "monto": 128000, "nota": "160 pags x tarifa base"},
                        {"nombre": "Diseno tapas", "monto": 50000, "nota": "Preset base de diseno de tapas."},
                        {"nombre": "Banner", "monto": 70000, "nota": "Preset base de pieza promocional."},
                        {"nombre": "ISBN", "monto": 50000, "nota": "Preset base de registro editorial."}
                    ]
                },
                {
                    "nombre": "120 copias",
                    "cantidad_copias": 120,
                    "porcentaje_ganancia": 50,
                    "items": [
                        {"nombre": "Impresion", "monto": 0, "nota": "Cotizado manualmente en https://print.livriz.com"},
                        {"nombre": "Edicion interior", "monto": 128000, "nota": "160 pags x tarifa base"},
                        {"nombre": "Diseno tapas", "monto": 50000, "nota": "Preset base de diseno de tapas."},
                        {"nombre": "Banner", "monto": 70000, "nota": "Preset base de pieza promocional."},
                        {"nombre": "ISBN", "monto": 50000, "nota": "Preset base de registro editorial."}
                    ]
                }
            ]
        }
        """.strip(),
    },
}


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

            CREATE TABLE IF NOT EXISTS auth_intentos (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS presupuesto_versiones (
                id TEXT PRIMARY KEY,
                presupuesto_id TEXT NOT NULL,
                version_num INTEGER NOT NULL,
                evento TEXT NOT NULL,
                resumen_cambios TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_by TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (presupuesto_id) REFERENCES presupuestos (id) ON DELETE CASCADE,
                UNIQUE (presupuesto_id, version_num)
            );

            CREATE TABLE IF NOT EXISTS tipos_proyecto_preset (
                clave TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_presupuestos_fecha ON presupuestos (fecha DESC);
            CREATE INDEX IF NOT EXISTS idx_presupuestos_nombre ON presupuestos (nombre_proyecto);
            CREATE INDEX IF NOT EXISTS idx_presupuestos_cliente ON presupuestos (cliente);
            CREATE INDEX IF NOT EXISTS idx_escenarios_presupuesto ON escenarios (presupuesto_id, orden);
            CREATE INDEX IF NOT EXISTS idx_items_escenario ON items (escenario_id, orden);
            CREATE INDEX IF NOT EXISTS idx_auth_intentos_usuario_ip ON auth_intentos (username, ip_address, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_presupuesto_versiones_presupuesto ON presupuesto_versiones (presupuesto_id, version_num DESC);
            """
        )

        _migrar_presupuestos(connection)

        defaults = {
            "tipo_de_cambio": "1400",
            "tarifa_edicion_por_pagina": "800",
            "tarifa_escaneo_por_pagina": "500",
            "preset_isbn": "50000",
            "preset_banner": "70000",
            "preset_diseno_tapas": "50000",
            "auth_totp_enabled": "0",
        }
        connection.executemany(
            """
            INSERT INTO configuracion (clave, valor)
            VALUES (?, ?)
            ON CONFLICT(clave) DO NOTHING
            """,
            defaults.items(),
        )

        connection.executemany(
            """
            INSERT INTO tipos_proyecto_preset (clave, nombre, descripcion, payload_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(clave) DO NOTHING
            """,
            [
                (clave, data["nombre"], data["descripcion"], data["payload_json"])
                for clave, data in PROJECT_TYPE_DEFAULTS.items()
            ],
        )


def _migrar_presupuestos(connection: sqlite3.Connection) -> None:
    columnas = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(presupuestos)").fetchall()
    }
    if "tipo_proyecto_clave" not in columnas:
        connection.execute("ALTER TABLE presupuestos ADD COLUMN tipo_proyecto_clave TEXT")


__all__ = ["DB_PATH", "PROJECT_TYPE_DEFAULTS", "get_connection", "init_database"]
