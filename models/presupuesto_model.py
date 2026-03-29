from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any
from uuid import uuid4

from database import get_connection
from models.calculations import calcular_escenario_completo
from models.schemas import PresupuestoCreate, PresupuestoUpdate


def obtener_todos(busqueda: str | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT id, nombre_proyecto, cliente, fecha, notas
        FROM presupuestos
    """
    parametros: list[Any] = []
    if busqueda:
        query += " WHERE nombre_proyecto LIKE ? OR cliente LIKE ?"
        termino = f"%{busqueda.strip()}%"
        parametros.extend([termino, termino])
    query += " ORDER BY date(fecha) DESC, created_at DESC"

    with get_connection() as connection:
        presupuestos = [dict(row) for row in connection.execute(query, parametros).fetchall()]
        if not presupuestos:
            return []

        escenarios_por_presupuesto = _obtener_escenarios_por_presupuestos(
            connection,
            [presupuesto["id"] for presupuesto in presupuestos],
        )

    resultados = []
    for presupuesto in presupuestos:
        presupuesto["escenarios"] = escenarios_por_presupuesto.get(presupuesto["id"], [])
        resultados.append(_hidratar_presupuesto(presupuesto))
    return resultados


def obtener_por_id(presupuesto_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        presupuesto_row = connection.execute(
            """
            SELECT id, nombre_proyecto, cliente, fecha, notas
            FROM presupuestos
            WHERE id = ?
            """,
            (presupuesto_id,),
        ).fetchone()
        if presupuesto_row is None:
            return None

        presupuesto = dict(presupuesto_row)
        presupuesto["escenarios"] = _obtener_escenarios(connection, presupuesto_id)
        return _hidratar_presupuesto(presupuesto)


def crear(datos: PresupuestoCreate) -> dict[str, Any]:
    presupuesto_id = str(uuid4())
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO presupuestos (id, nombre_proyecto, cliente, fecha, notas)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                presupuesto_id,
                datos.nombre_proyecto,
                datos.cliente,
                datos.fecha.isoformat(),
                datos.notas,
            ),
        )
        _guardar_escenarios(connection, presupuesto_id, datos.escenarios)
    return obtener_por_id(presupuesto_id)  # type: ignore[return-value]


def actualizar(presupuesto_id: str, datos: PresupuestoUpdate) -> dict[str, Any] | None:
    with get_connection() as connection:
        existe = connection.execute(
            "SELECT 1 FROM presupuestos WHERE id = ?",
            (presupuesto_id,),
        ).fetchone()
        if existe is None:
            return None

        connection.execute(
            """
            UPDATE presupuestos
            SET nombre_proyecto = ?, cliente = ?, fecha = ?, notas = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                datos.nombre_proyecto,
                datos.cliente,
                datos.fecha.isoformat(),
                datos.notas,
                presupuesto_id,
            ),
        )
        connection.execute("DELETE FROM escenarios WHERE presupuesto_id = ?", (presupuesto_id,))
        _guardar_escenarios(connection, presupuesto_id, datos.escenarios)
    return obtener_por_id(presupuesto_id)


def eliminar(presupuesto_id: str) -> bool:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM presupuestos WHERE id = ?", (presupuesto_id,))
        return cursor.rowcount > 0


def duplicar(presupuesto_id: str) -> dict[str, Any] | None:
    original = obtener_por_id(presupuesto_id)
    if original is None:
        return None

    payload = PresupuestoCreate(
        nombre_proyecto=f"{original['nombre_proyecto']} (Copia)",
        cliente=original["cliente"],
        fecha=date.today(),
        notas=original.get("notas"),
        escenarios=[
            {
                "nombre": escenario["nombre"],
                "cantidad_copias": escenario["cantidad_copias"],
                "porcentaje_ganancia": escenario["porcentaje_ganancia"],
                "tipo_de_cambio_snapshot": escenario["tipo_de_cambio_snapshot"],
                "items": [
                    {
                        "nombre": item["nombre"],
                        "monto": item["monto"],
                        "nota": item.get("nota"),
                    }
                    for item in escenario["items"]
                ],
            }
            for escenario in original["escenarios"]
        ],
    )
    return crear(payload)


def _guardar_escenarios(connection, presupuesto_id: str, escenarios: list) -> None:
    for indice_escenario, escenario in enumerate(escenarios):
        escenario_id = str(uuid4())
        connection.execute(
            """
            INSERT INTO escenarios (
                id, presupuesto_id, nombre, cantidad_copias,
                porcentaje_ganancia, tipo_de_cambio_snapshot, orden
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                escenario_id,
                presupuesto_id,
                escenario.nombre,
                escenario.cantidad_copias,
                escenario.porcentaje_ganancia,
                escenario.tipo_de_cambio_snapshot,
                indice_escenario,
            ),
        )
        for indice_item, item in enumerate(escenario.items):
            connection.execute(
                """
                INSERT INTO items (id, escenario_id, nombre, monto, nota, orden)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    escenario_id,
                    item.nombre,
                    item.monto,
                    item.nota,
                    indice_item,
                ),
            )


def _obtener_escenarios(connection, presupuesto_id: str) -> list[dict[str, Any]]:
    escenarios_por_presupuesto = _obtener_escenarios_por_presupuestos(connection, [presupuesto_id])
    return escenarios_por_presupuesto.get(presupuesto_id, [])


def _obtener_escenarios_por_presupuestos(
    connection,
    presupuesto_ids: list[str],
) -> dict[str, list[dict[str, Any]]]:
    if not presupuesto_ids:
        return {}

    escenarios = [
        dict(row)
        for row in connection.execute(
            """
            SELECT id, presupuesto_id, nombre, cantidad_copias, porcentaje_ganancia, tipo_de_cambio_snapshot, orden
            FROM escenarios
            WHERE presupuesto_id IN ({placeholders})
            ORDER BY orden ASC
            """.format(placeholders=",".join("?" for _ in presupuesto_ids)),
            presupuesto_ids,
        ).fetchall()
    ]
    if not escenarios:
        return {}

    items_por_escenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in connection.execute(
        f"""
        SELECT id, escenario_id, nombre, monto, nota, orden
        FROM items
        WHERE escenario_id IN ({",".join("?" for _ in escenarios)})
        ORDER BY orden ASC
        """,
        [escenario["id"] for escenario in escenarios],
    ).fetchall():
        items_por_escenario[row["escenario_id"]].append(
            {
                "id": row["id"],
                "nombre": row["nombre"],
                "monto": row["monto"],
                "nota": row["nota"],
                "orden": row["orden"],
            }
        )

    escenarios_por_presupuesto: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for escenario in escenarios:
        escenario["items"] = items_por_escenario.get(escenario["id"], [])
        escenarios_por_presupuesto[escenario["presupuesto_id"]].append(escenario)
    return dict(escenarios_por_presupuesto)


def _hidratar_presupuesto(presupuesto: dict[str, Any]) -> dict[str, Any]:
    escenarios_calculados = []
    for escenario in presupuesto["escenarios"]:
        calculos = calcular_escenario_completo(escenario)
        escenarios_calculados.append({**escenario, **calculos})

    presupuesto["escenarios"] = escenarios_calculados
    presupuesto["cantidad_escenarios"] = len(escenarios_calculados)
    if escenarios_calculados:
        escenario_referencia = _seleccionar_escenario_referencia(escenarios_calculados)
        totales_ars = [escenario["total"] for escenario in escenarios_calculados]
        totales_usd = [escenario["precio_usd"] for escenario in escenarios_calculados]
        presupuesto["escenario_referencia_nombre"] = escenario_referencia["nombre"]
        presupuesto["escenario_referencia_cantidad_copias"] = escenario_referencia["cantidad_copias"]
        presupuesto["total_ars_referencia"] = escenario_referencia["total"]
        presupuesto["total_usd_referencia"] = escenario_referencia["precio_usd"]
        presupuesto["total_ars_min"] = min(totales_ars)
        presupuesto["total_ars_max"] = max(totales_ars)
        presupuesto["total_usd_min"] = min(totales_usd)
        presupuesto["total_usd_max"] = max(totales_usd)
    else:
        presupuesto["escenario_referencia_nombre"] = ""
        presupuesto["escenario_referencia_cantidad_copias"] = 0
        presupuesto["total_ars_referencia"] = 0.0
        presupuesto["total_usd_referencia"] = 0.0
        presupuesto["total_ars_min"] = 0.0
        presupuesto["total_ars_max"] = 0.0
        presupuesto["total_usd_min"] = 0.0
        presupuesto["total_usd_max"] = 0.0
    return presupuesto


def _seleccionar_escenario_referencia(escenarios: list[dict[str, Any]]) -> dict[str, Any]:
    return min(
        escenarios,
        key=lambda escenario: (int(escenario["cantidad_copias"]), int(escenario.get("orden", 0))),
    )
