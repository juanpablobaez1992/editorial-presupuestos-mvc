from __future__ import annotations

from models.schemas import ConfiguracionResponse, ConfiguracionUpdate
from database import get_connection


def obtener_configuracion() -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT clave, valor FROM configuracion WHERE clave IN (?, ?, ?)",
            (
                "tipo_de_cambio",
                "tarifa_edicion_por_pagina",
                "tarifa_escaneo_por_pagina",
            ),
        )
        data = {row["clave"]: float(row["valor"]) for row in cursor.fetchall()}

    configuracion = ConfiguracionResponse(
        tipo_de_cambio=data.get("tipo_de_cambio", 1400),
        tarifa_edicion_por_pagina=data.get("tarifa_edicion_por_pagina", 800),
        tarifa_escaneo_por_pagina=data.get("tarifa_escaneo_por_pagina", 500),
    )
    return configuracion.model_dump()


def actualizar_configuracion(datos: ConfiguracionUpdate) -> dict:
    payload = {
        "tipo_de_cambio": datos.tipo_de_cambio,
        "tarifa_edicion_por_pagina": datos.tarifa_edicion_por_pagina,
        "tarifa_escaneo_por_pagina": datos.tarifa_escaneo_por_pagina,
    }
    with get_connection() as connection:
        connection.executemany(
            """
            INSERT INTO configuracion (clave, valor, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(clave) DO UPDATE SET
                valor = excluded.valor,
                updated_at = CURRENT_TIMESTAMP
            """,
            [(clave, str(valor)) for clave, valor in payload.items()],
        )
    return obtener_configuracion()
