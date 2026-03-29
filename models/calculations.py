from __future__ import annotations

import unicodedata
from typing import Any


def normalizar_texto(texto: str) -> str:
    """Quita acentos y pasa a minusculas para comparaciones internas."""
    texto_normalizado = unicodedata.normalize("NFD", texto or "")
    sin_acentos = "".join(char for char in texto_normalizado if unicodedata.category(char) != "Mn")
    return sin_acentos.lower().strip()


def es_item_impresion(nombre: str) -> bool:
    return "impres" in normalizar_texto(nombre)


def calcular_subtotal(items: list[dict[str, Any]]) -> float:
    return round(sum(float(item["monto"]) for item in items), 2)


def calcular_total(subtotal: float, porcentaje_ganancia: float) -> float:
    return round(subtotal + (subtotal * porcentaje_ganancia / 100), 2)


def calcular_precio_por_ejemplar(total: float, cantidad_copias: int) -> float:
    if cantidad_copias <= 0:
        raise ValueError("La cantidad de copias debe ser mayor a cero.")
    return round(total / cantidad_copias, 2)


def calcular_precio_usd(total: float, tipo_de_cambio: float) -> float:
    if tipo_de_cambio <= 0:
        raise ValueError("El tipo de cambio debe ser mayor a cero.")
    return round(total / tipo_de_cambio, 2)


def calcular_ganancia_neta(total: float, monto_impresion: float) -> float:
    return round(total - monto_impresion, 2)


def obtener_monto_impresion(items: list[dict[str, Any]]) -> float:
    for item in items:
        if es_item_impresion(str(item.get("nombre", ""))):
            return round(float(item.get("monto", 0)), 2)
    return 0.0


def calcular_escenario_completo(escenario: dict[str, Any], tipo_de_cambio: float | None = None) -> dict[str, float]:
    items = escenario["items"]
    subtotal = calcular_subtotal(items)
    total = calcular_total(subtotal, float(escenario["porcentaje_ganancia"]))
    cambio = float(tipo_de_cambio or escenario["tipo_de_cambio_snapshot"])
    impresion = obtener_monto_impresion(items)
    return {
        "subtotal": subtotal,
        "total": total,
        "precio_por_ejemplar": calcular_precio_por_ejemplar(total, int(escenario["cantidad_copias"])),
        "precio_usd": calcular_precio_usd(total, cambio),
        "ganancia_neta_pesos": calcular_ganancia_neta(total, impresion),
    }


if __name__ == "__main__":
    escenario_demo = {
        "cantidad_copias": 50,
        "porcentaje_ganancia": 45,
        "tipo_de_cambio_snapshot": 1400,
        "items": [
            {"nombre": "Impresion", "monto": 374302.0},
            {"nombre": "Edicion interior", "monto": 80000.0},
            {"nombre": "Diseno tapas", "monto": 50000.0},
        ],
    }
    resultado = calcular_escenario_completo(escenario_demo)
    assert resultado["subtotal"] == 504302.0
    assert resultado["total"] == 731237.9
    assert resultado["precio_por_ejemplar"] == round(resultado["total"] / 50, 2)
    assert resultado["precio_usd"] == round(resultado["total"] / 1400, 2)
    assert resultado["ganancia_neta_pesos"] == round(resultado["total"] - 374302.0, 2)
