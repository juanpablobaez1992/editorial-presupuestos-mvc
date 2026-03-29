from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from database import get_connection
from models.calculations import calcular_escenario_completo
from models.schemas import PresupuestoCreate, PresupuestoUpdate


def obtener_todos(busqueda: str | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT id, nombre_proyecto, cliente, fecha, notas, tipo_proyecto_clave
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


def obtener_por_id(presupuesto_id: str, incluir_versiones: bool = False) -> dict[str, Any] | None:
    with get_connection() as connection:
        presupuesto_row = connection.execute(
            """
            SELECT id, nombre_proyecto, cliente, fecha, notas, tipo_proyecto_clave
            FROM presupuestos
            WHERE id = ?
            """,
            (presupuesto_id,),
        ).fetchone()
        if presupuesto_row is None:
            return None

        presupuesto = dict(presupuesto_row)
        presupuesto["escenarios"] = _obtener_escenarios(connection, presupuesto_id)
        if incluir_versiones:
            presupuesto["versiones"] = _obtener_versiones(connection, presupuesto_id)
        return _hidratar_presupuesto(presupuesto)


def obtener_versiones(presupuesto_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        return _obtener_versiones(connection, presupuesto_id)


def calcular_metricas_dashboard(presupuestos: list[dict[str, Any]]) -> dict[str, Any]:
    hoy = date.today()
    total = len(presupuestos)
    presupuestos_mes = [
        presupuesto
        for presupuesto in presupuestos
        if _parse_date(presupuesto["fecha"]).year == hoy.year and _parse_date(presupuesto["fecha"]).month == hoy.month
    ]
    ticket_promedio = round(
        sum(float(presupuesto["total_ars_referencia"]) for presupuesto in presupuestos) / total,
        2,
    ) if total else 0.0
    clientes = [presupuesto["cliente"].strip() for presupuesto in presupuestos if presupuesto.get("cliente")]
    conteo_clientes = Counter(clientes)
    cliente_top = conteo_clientes.most_common(1)[0] if conteo_clientes else None

    presupuestos_dobles = [presupuesto for presupuesto in presupuestos if int(presupuesto["cantidad_escenarios"]) == 2]
    porcentaje_dobles = round((len(presupuestos_dobles) / total) * 100, 2) if total else 0.0

    copias_base = [
        int(presupuesto.get("escenario_referencia_cantidad_copias") or 0)
        for presupuesto in presupuestos
        if int(presupuesto.get("escenario_referencia_cantidad_copias") or 0) > 0
    ]
    promedio_copias_base = round(sum(copias_base) / len(copias_base), 2) if copias_base else 0.0

    tipos = [presupuesto.get("tipo_proyecto_clave") or "sin_tipo" for presupuesto in presupuestos]
    tipo_top = Counter(tipos).most_common(1)[0] if tipos else None

    return {
        "total_presupuestos": total,
        "presupuestos_mes_actual": len(presupuestos_mes),
        "ticket_promedio_ars": ticket_promedio,
        "clientes_unicos": len(set(clientes)),
        "cliente_top_nombre": cliente_top[0] if cliente_top else "Sin datos",
        "cliente_top_cantidad": cliente_top[1] if cliente_top else 0,
        "porcentaje_dos_escenarios": porcentaje_dobles,
        "promedio_copias_base": promedio_copias_base,
        "tipo_proyecto_top": tipo_top[0] if tipo_top else "sin_tipo",
        "tipo_proyecto_top_cantidad": tipo_top[1] if tipo_top else 0,
    }


def crear(
    datos: PresupuestoCreate,
    usuario: str | None = None,
    evento: str = "creacion",
    resumen_cambios: str | None = None,
) -> dict[str, Any]:
    presupuesto_id = str(uuid4())
    snapshot = _snapshot_desde_datos(datos)
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO presupuestos (id, nombre_proyecto, cliente, fecha, notas, tipo_proyecto_clave)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                presupuesto_id,
                datos.nombre_proyecto,
                datos.cliente,
                datos.fecha.isoformat(),
                datos.notas,
                datos.tipo_proyecto_clave,
            ),
        )
        _guardar_escenarios(connection, presupuesto_id, datos.escenarios)
        _registrar_version(
            connection,
            presupuesto_id=presupuesto_id,
            snapshot=snapshot,
            evento=evento,
            resumen_cambios=resumen_cambios or _resumir_cambios_version(None, snapshot, evento),
            usuario=usuario,
        )
    return obtener_por_id(presupuesto_id)  # type: ignore[return-value]


def actualizar(presupuesto_id: str, datos: PresupuestoUpdate, usuario: str | None = None) -> dict[str, Any] | None:
    snapshot_nuevo = _snapshot_desde_datos(datos)
    with get_connection() as connection:
        existe = connection.execute(
            "SELECT 1 FROM presupuestos WHERE id = ?",
            (presupuesto_id,),
        ).fetchone()
        if existe is None:
            return None

        snapshot_anterior = _obtener_snapshot_actual(connection, presupuesto_id)
        connection.execute(
            """
            UPDATE presupuestos
            SET nombre_proyecto = ?, cliente = ?, fecha = ?, notas = ?, tipo_proyecto_clave = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                datos.nombre_proyecto,
                datos.cliente,
                datos.fecha.isoformat(),
                datos.notas,
                datos.tipo_proyecto_clave,
                presupuesto_id,
            ),
        )
        connection.execute("DELETE FROM escenarios WHERE presupuesto_id = ?", (presupuesto_id,))
        _guardar_escenarios(connection, presupuesto_id, datos.escenarios)
        _registrar_version(
            connection,
            presupuesto_id=presupuesto_id,
            snapshot=snapshot_nuevo,
            evento="actualizacion",
            resumen_cambios=_resumir_cambios_version(snapshot_anterior, snapshot_nuevo, "actualizacion"),
            usuario=usuario,
        )
    return obtener_por_id(presupuesto_id)


def restaurar_version(
    presupuesto_id: str,
    version_id: str,
    usuario: str | None = None,
) -> dict[str, Any] | None:
    with get_connection() as connection:
        presupuesto_row = connection.execute(
            "SELECT 1 FROM presupuestos WHERE id = ?",
            (presupuesto_id,),
        ).fetchone()
        if presupuesto_row is None:
            return None

        version_row = connection.execute(
            """
            SELECT id, version_num, snapshot_json
            FROM presupuesto_versiones
            WHERE id = ? AND presupuesto_id = ?
            """,
            (version_id, presupuesto_id),
        ).fetchone()
        if version_row is None:
            return None

        snapshot = json.loads(version_row["snapshot_json"])
        datos = PresupuestoUpdate(**snapshot)
        connection.execute(
            """
            UPDATE presupuestos
            SET nombre_proyecto = ?, cliente = ?, fecha = ?, notas = ?, tipo_proyecto_clave = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                datos.nombre_proyecto,
                datos.cliente,
                datos.fecha.isoformat(),
                datos.notas,
                datos.tipo_proyecto_clave,
                presupuesto_id,
            ),
        )
        connection.execute("DELETE FROM escenarios WHERE presupuesto_id = ?", (presupuesto_id,))
        _guardar_escenarios(connection, presupuesto_id, datos.escenarios)
        _registrar_version(
            connection,
            presupuesto_id=presupuesto_id,
            snapshot=snapshot,
            evento="restauracion",
            resumen_cambios=f"Restaurado desde la version {version_row['version_num']}.",
            usuario=usuario,
        )
    return obtener_por_id(presupuesto_id, incluir_versiones=True)


def eliminar(presupuesto_id: str) -> bool:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM presupuestos WHERE id = ?", (presupuesto_id,))
        return cursor.rowcount > 0


def duplicar(presupuesto_id: str, usuario: str | None = None) -> dict[str, Any] | None:
    original = obtener_por_id(presupuesto_id)
    if original is None:
        return None

    payload = PresupuestoCreate(
        nombre_proyecto=f"{original['nombre_proyecto']} (Copia)",
        cliente=original["cliente"],
        fecha=date.today(),
        notas=original.get("notas"),
        tipo_proyecto_clave=original.get("tipo_proyecto_clave"),
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
    return crear(
        payload,
        usuario=usuario,
        evento="duplicado",
        resumen_cambios=f"Duplicado desde el presupuesto {original['nombre_proyecto']}.",
    )


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


def _obtener_versiones(connection, presupuesto_id: str) -> list[dict[str, Any]]:
    versiones = [
        dict(row)
        for row in connection.execute(
            """
            SELECT id, version_num, evento, resumen_cambios, created_by, created_at
            FROM presupuesto_versiones
            WHERE presupuesto_id = ?
            ORDER BY version_num DESC
            """,
            (presupuesto_id,),
        ).fetchall()
    ]
    if not versiones:
        return []

    version_actual = max(version["version_num"] for version in versiones)
    for version in versiones:
        version["es_actual"] = version["version_num"] == version_actual
        version["evento_label"] = _label_evento(version["evento"])
    return versiones


def _registrar_version(
    connection,
    presupuesto_id: str,
    snapshot: dict[str, Any],
    evento: str,
    resumen_cambios: str,
    usuario: str | None,
) -> None:
    siguiente_version = connection.execute(
        """
        SELECT COALESCE(MAX(version_num), 0) + 1 AS siguiente
        FROM presupuesto_versiones
        WHERE presupuesto_id = ?
        """,
        (presupuesto_id,),
    ).fetchone()["siguiente"]
    connection.execute(
        """
        INSERT INTO presupuesto_versiones (
            id, presupuesto_id, version_num, evento, resumen_cambios, snapshot_json, created_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            presupuesto_id,
            siguiente_version,
            evento,
            resumen_cambios,
            json.dumps(snapshot, ensure_ascii=False),
            usuario,
        ),
    )


def _obtener_snapshot_actual(connection, presupuesto_id: str) -> dict[str, Any]:
    version_row = connection.execute(
        """
        SELECT snapshot_json
        FROM presupuesto_versiones
        WHERE presupuesto_id = ?
        ORDER BY version_num DESC
        LIMIT 1
        """,
        (presupuesto_id,),
    ).fetchone()
    if version_row is not None:
        return json.loads(version_row["snapshot_json"])

    presupuesto = {
        "id": presupuesto_id,
        "escenarios": _obtener_escenarios(connection, presupuesto_id),
        **dict(
            connection.execute(
                """
                SELECT id, nombre_proyecto, cliente, fecha, notas, tipo_proyecto_clave
                FROM presupuestos
                WHERE id = ?
                """,
                (presupuesto_id,),
            ).fetchone()
        ),
    }
    return _snapshot_desde_presupuesto(presupuesto)


def _snapshot_desde_datos(datos: PresupuestoCreate | PresupuestoUpdate) -> dict[str, Any]:
    payload = datos.model_dump(mode="json")
    return {
        "nombre_proyecto": payload["nombre_proyecto"],
        "cliente": payload["cliente"],
        "fecha": payload["fecha"],
        "notas": payload.get("notas"),
        "tipo_proyecto_clave": payload.get("tipo_proyecto_clave"),
        "escenarios": [
            {
                "nombre": escenario["nombre"],
                "cantidad_copias": int(escenario["cantidad_copias"]),
                "porcentaje_ganancia": float(escenario["porcentaje_ganancia"]),
                "tipo_de_cambio_snapshot": float(escenario["tipo_de_cambio_snapshot"]),
                "items": [
                    {
                        "nombre": item["nombre"],
                        "monto": float(item["monto"]),
                        "nota": item.get("nota"),
                    }
                    for item in escenario["items"]
                ],
            }
            for escenario in payload["escenarios"]
        ],
    }


def _snapshot_desde_presupuesto(presupuesto: dict[str, Any]) -> dict[str, Any]:
    return {
        "nombre_proyecto": presupuesto["nombre_proyecto"],
        "cliente": presupuesto["cliente"],
        "fecha": presupuesto["fecha"],
        "notas": presupuesto.get("notas"),
        "tipo_proyecto_clave": presupuesto.get("tipo_proyecto_clave"),
        "escenarios": [
            {
                "nombre": escenario["nombre"],
                "cantidad_copias": int(escenario["cantidad_copias"]),
                "porcentaje_ganancia": float(escenario["porcentaje_ganancia"]),
                "tipo_de_cambio_snapshot": float(escenario["tipo_de_cambio_snapshot"]),
                "items": [
                    {
                        "nombre": item["nombre"],
                        "monto": float(item["monto"]),
                        "nota": item.get("nota"),
                    }
                    for item in escenario["items"]
                ],
            }
            for escenario in presupuesto["escenarios"]
        ],
    }


def _resumir_cambios_version(
    snapshot_anterior: dict[str, Any] | None,
    snapshot_nuevo: dict[str, Any],
    evento: str,
) -> str:
    if evento == "creacion":
        return "Version inicial del presupuesto."
    if evento == "duplicado":
        return "Presupuesto generado a partir de una copia."
    if snapshot_anterior is None:
        return "Se genero una nueva version del presupuesto."

    cambios: list[str] = []
    if snapshot_anterior["nombre_proyecto"] != snapshot_nuevo["nombre_proyecto"]:
        cambios.append("Se actualizo el nombre del proyecto")
    if snapshot_anterior["cliente"] != snapshot_nuevo["cliente"]:
        cambios.append("Se modifico el cliente")
    if snapshot_anterior["fecha"] != snapshot_nuevo["fecha"]:
        cambios.append("Se cambio la fecha")
    if (snapshot_anterior.get("notas") or "") != (snapshot_nuevo.get("notas") or ""):
        cambios.append("Se ajustaron las notas")
    if snapshot_anterior.get("tipo_proyecto_clave") != snapshot_nuevo.get("tipo_proyecto_clave"):
        cambios.append("Se cambio el tipo de proyecto")

    escenarios_anteriores = {escenario["nombre"].strip().lower(): escenario for escenario in snapshot_anterior["escenarios"]}
    escenarios_nuevos = {escenario["nombre"].strip().lower(): escenario for escenario in snapshot_nuevo["escenarios"]}

    agregados = [escenario["nombre"] for key, escenario in escenarios_nuevos.items() if key not in escenarios_anteriores]
    quitados = [escenario["nombre"] for key, escenario in escenarios_anteriores.items() if key not in escenarios_nuevos]
    if agregados:
        cambios.append(f"Se agregaron escenarios: {', '.join(agregados[:2])}")
    if quitados:
        cambios.append(f"Se quitaron escenarios: {', '.join(quitados[:2])}")

    for clave in escenarios_anteriores.keys() & escenarios_nuevos.keys():
        anterior = escenarios_anteriores[clave]
        nuevo = escenarios_nuevos[clave]
        if anterior["cantidad_copias"] != nuevo["cantidad_copias"]:
            cambios.append(f"{nuevo['nombre']}: copias {anterior['cantidad_copias']} -> {nuevo['cantidad_copias']}")
        if round(float(anterior["porcentaje_ganancia"]), 2) != round(float(nuevo["porcentaje_ganancia"]), 2):
            cambios.append(
                f"{nuevo['nombre']}: margen {anterior['porcentaje_ganancia']}% -> {nuevo['porcentaje_ganancia']}%"
            )
        total_anterior = calcular_escenario_completo(anterior)["total"]
        total_nuevo = calcular_escenario_completo(nuevo)["total"]
        if round(total_anterior, 2) != round(total_nuevo, 2):
            cambios.append(f"{nuevo['nombre']}: total {int(round(total_anterior))} -> {int(round(total_nuevo))} ARS")
        items_anteriores = {item["nombre"].strip().lower(): item for item in anterior["items"]}
        items_nuevos = {item["nombre"].strip().lower(): item for item in nuevo["items"]}
        if items_anteriores.keys() != items_nuevos.keys():
            cambios.append(f"{nuevo['nombre']}: se ajustaron conceptos del escenario")

    if not cambios:
        return "Se guardo una nueva version sin cambios clave detectados."

    resumen = ". ".join(cambios[:4]).strip()
    if not resumen.endswith("."):
        resumen += "."
    return resumen


def _label_evento(evento: str) -> str:
    labels = {
        "creacion": "Creacion",
        "actualizacion": "Actualizacion",
        "duplicado": "Duplicado",
        "restauracion": "Restauracion",
    }
    return labels.get(evento, "Version")


def _hidratar_presupuesto(presupuesto: dict[str, Any]) -> dict[str, Any]:
    escenarios_calculados = []
    for escenario in presupuesto["escenarios"]:
        calculos = calcular_escenario_completo(escenario)
        escenarios_calculados.append({**escenario, **calculos})

    presupuesto["escenarios"] = escenarios_calculados
    presupuesto["cantidad_escenarios"] = len(escenarios_calculados)
    if "versiones" not in presupuesto:
        presupuesto["versiones"] = []

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


def _parse_date(valor: str) -> date:
    try:
        return datetime.fromisoformat(valor).date()
    except ValueError:
        return date.today()
