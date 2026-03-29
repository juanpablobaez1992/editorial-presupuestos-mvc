from __future__ import annotations

import json

from database import get_connection


def obtener_tipos_proyecto() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT clave, nombre, descripcion, payload_json
            FROM tipos_proyecto_preset
            ORDER BY nombre ASC
            """
        ).fetchall()

    tipos = []
    for row in rows:
        tipos.append(
            {
                "clave": row["clave"],
                "nombre": row["nombre"],
                "descripcion": row["descripcion"],
                "payload": json.loads(row["payload_json"]),
            }
        )
    return tipos


def obtener_tipo_proyecto_por_clave(clave: str | None) -> dict | None:
    if not clave:
        return None
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT clave, nombre, descripcion, payload_json
            FROM tipos_proyecto_preset
            WHERE clave = ?
            """,
            (clave.strip().lower(),),
        ).fetchone()
    if row is None:
        return None
    return {
        "clave": row["clave"],
        "nombre": row["nombre"],
        "descripcion": row["descripcion"],
        "payload": json.loads(row["payload_json"]),
    }
