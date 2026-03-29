from __future__ import annotations

from models.schemas import ConfiguracionResponse, ConfiguracionUpdate
from database import get_connection


def obtener_configuracion() -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT clave, valor FROM configuracion WHERE clave IN (?, ?, ?, ?, ?, ?)",
            (
                "tipo_de_cambio",
                "tarifa_edicion_por_pagina",
                "tarifa_escaneo_por_pagina",
                "preset_isbn",
                "preset_banner",
                "preset_diseno_tapas",
            ),
        )
        data = {row["clave"]: float(row["valor"]) for row in cursor.fetchall()}

    configuracion = ConfiguracionResponse(
        tipo_de_cambio=data.get("tipo_de_cambio", 1400),
        tarifa_edicion_por_pagina=data.get("tarifa_edicion_por_pagina", 800),
        tarifa_escaneo_por_pagina=data.get("tarifa_escaneo_por_pagina", 500),
        preset_isbn=data.get("preset_isbn", 50000),
        preset_banner=data.get("preset_banner", 70000),
        preset_diseno_tapas=data.get("preset_diseno_tapas", 50000),
    )
    return configuracion.model_dump()


def obtener_catalogo_presets(configuracion: dict | None = None) -> list[dict]:
    config = configuracion or obtener_configuracion()
    return [
        {
            "clave": "isbn",
            "nombre": "ISBN",
            "monto": config["preset_isbn"],
            "nota": "Preset base de registro editorial.",
            "descripcion": "Inserta o actualiza el costo base de ISBN.",
        },
        {
            "clave": "banner",
            "nombre": "Banner",
            "monto": config["preset_banner"],
            "nota": "Preset base de pieza promocional.",
            "descripcion": "Inserta o actualiza el costo base de banner.",
        },
        {
            "clave": "diseno_tapas",
            "nombre": "Diseno tapas",
            "monto": config["preset_diseno_tapas"],
            "nota": "Preset base de diseño de tapas.",
            "descripcion": "Inserta o actualiza el costo base de diseño de tapas.",
        },
    ]


def actualizar_configuracion(datos: ConfiguracionUpdate) -> dict:
    payload = {
        "tipo_de_cambio": datos.tipo_de_cambio,
        "tarifa_edicion_por_pagina": datos.tarifa_edicion_por_pagina,
        "tarifa_escaneo_por_pagina": datos.tarifa_escaneo_por_pagina,
        "preset_isbn": datos.preset_isbn,
        "preset_banner": datos.preset_banner,
        "preset_diseno_tapas": datos.preset_diseno_tapas,
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
