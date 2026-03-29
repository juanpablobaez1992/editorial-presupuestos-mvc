from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient


def test_healthcheck_responde_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "status": "healthy"}


def test_formulario_muestra_presets_inteligentes(client: TestClient) -> None:
    response = client.get("/presupuestos/nuevo")

    assert response.status_code == 200
    html = response.text
    assert "Presets inteligentes" in html
    assert "ISBN" in html
    assert "Banner" in html
    assert "Diseno tapas" in html


def test_crear_presupuesto_con_presets_y_escenarios(client: TestClient) -> None:
    payload = {
        "nombre_proyecto": "Libro con presets",
        "cliente": "Cliente Demo",
        "fecha": date(2026, 3, 28).isoformat(),
        "notas": "Incluye presets de tapa, banner e ISBN",
        "escenarios": [
            {
                "nombre": "40 copias",
                "cantidad_copias": 40,
                "porcentaje_ganancia": 45,
                "tipo_de_cambio_snapshot": 1400,
                "items": [
                    {"nombre": "Impresion", "monto": 120000, "nota": None},
                    {"nombre": "ISBN", "monto": 50000, "nota": "Preset base de registro editorial."},
                    {"nombre": "Banner", "monto": 70000, "nota": "Preset base de pieza promocional."},
                    {"nombre": "Diseno tapas", "monto": 50000, "nota": "Preset base de diseño de tapas."},
                ],
            },
            {
                "nombre": "80 copias",
                "cantidad_copias": 80,
                "porcentaje_ganancia": 45,
                "tipo_de_cambio_snapshot": 1400,
                "items": [
                    {"nombre": "Impresion", "monto": 180000, "nota": None},
                    {"nombre": "ISBN", "monto": 50000, "nota": "Preset base de registro editorial."},
                ],
            },
        ],
    }

    response = client.post("/presupuestos", json=payload)

    assert response.status_code == 200
    body = response.json()["presupuesto"]
    assert body["escenario_referencia_nombre"] == "40 copias"
    assert body["escenarios"][0]["items"][0]["nota"] == "Cotizado manualmente en https://print.livriz.com"


def test_validacion_exige_impresion_en_cada_escenario(client: TestClient) -> None:
    payload = {
        "nombre_proyecto": "Invalido",
        "cliente": "Cliente Demo",
        "fecha": date(2026, 3, 28).isoformat(),
        "notas": None,
        "escenarios": [
            {
                "nombre": "Sin impresion",
                "cantidad_copias": 20,
                "porcentaje_ganancia": 40,
                "tipo_de_cambio_snapshot": 1400,
                "items": [
                    {"nombre": "ISBN", "monto": 50000, "nota": "Preset"},
                ],
            }
        ],
    }

    response = client.post("/presupuestos", json=payload)

    assert response.status_code == 422
    assert "Impresion" in response.text


def test_validacion_rechaza_nombres_duplicados_de_escenarios(client: TestClient) -> None:
    payload = {
        "nombre_proyecto": "Invalido",
        "cliente": "Cliente Demo",
        "fecha": date(2026, 3, 28).isoformat(),
        "notas": None,
        "escenarios": [
            {
                "nombre": "Mismo",
                "cantidad_copias": 20,
                "porcentaje_ganancia": 40,
                "tipo_de_cambio_snapshot": 1400,
                "items": [{"nombre": "Impresion", "monto": 1000, "nota": None}],
            },
            {
                "nombre": "Mismo",
                "cantidad_copias": 30,
                "porcentaje_ganancia": 40,
                "tipo_de_cambio_snapshot": 1400,
                "items": [{"nombre": "Impresion", "monto": 1000, "nota": None}],
            },
        ],
    }

    response = client.post("/presupuestos", json=payload)

    assert response.status_code == 422
    assert "unicos" in response.text
