from __future__ import annotations

import pytest

from models.calculations import (
    calcular_escenario_completo,
    calcular_precio_por_ejemplar,
    calcular_precio_usd,
)


def test_calcular_escenario_completo_devuelve_metricas_correctas() -> None:
    escenario = {
        "cantidad_copias": 50,
        "porcentaje_ganancia": 45,
        "tipo_de_cambio_snapshot": 1400,
        "items": [
            {"nombre": "Impresion", "monto": 374302.0},
            {"nombre": "Edicion interior", "monto": 80000.0},
            {"nombre": "Diseno tapas", "monto": 50000.0},
        ],
    }

    resultado = calcular_escenario_completo(escenario)

    assert resultado == {
        "subtotal": 504302.0,
        "total": 731237.9,
        "precio_por_ejemplar": 14624.76,
        "precio_usd": 522.31,
        "ganancia_neta_pesos": 356935.9,
    }


def test_calcular_precio_por_ejemplar_rechaza_cero_copias() -> None:
    with pytest.raises(ValueError, match="cantidad de copias"):
        calcular_precio_por_ejemplar(1000, 0)


def test_calcular_precio_usd_rechaza_tipo_cambio_invalido() -> None:
    with pytest.raises(ValueError, match="tipo de cambio"):
        calcular_precio_usd(1000, 0)
