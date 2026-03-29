from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

import database


def _payload_presupuesto_demo() -> dict:
    return {
        "nombre_proyecto": "Libro con historial",
        "cliente": "Cliente Demo",
        "fecha": date(2026, 3, 28).isoformat(),
        "notas": "Version inicial",
        "escenarios": [
            {
                "nombre": "50 copias",
                "cantidad_copias": 50,
                "porcentaje_ganancia": 45,
                "tipo_de_cambio_snapshot": 1400,
                "items": [
                    {"nombre": "Impresion", "monto": 120000, "nota": None},
                    {"nombre": "ISBN", "monto": 50000, "nota": "Preset base de registro editorial."},
                ],
            }
        ],
    }


def test_healthcheck_responde_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "status": "healthy"}


def test_rutas_privadas_redirigen_a_login_sin_sesion(client: TestClient) -> None:
    response = client.get("/presupuestos/nuevo", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_mi_cuenta_redirige_a_login_sin_sesion(client: TestClient) -> None:
    response = client.get("/mi-cuenta", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_formulario_muestra_presets_inteligentes(authenticated_client: TestClient) -> None:
    response = authenticated_client.get("/presupuestos/nuevo")

    assert response.status_code == 200
    html = response.text
    assert "Presets inteligentes" in html
    assert "ISBN" in html
    assert "Banner" in html
    assert "Diseno tapas" in html


def test_config_muestra_panel_de_credenciales(authenticated_client: TestClient) -> None:
    response = authenticated_client.get("/config")

    assert response.status_code == 200
    html = response.text
    assert "Cambiar credenciales" in html
    assert "Usuario activo" in html
    assert "Entorno" in html


def test_mi_cuenta_muestra_formulario_de_password(authenticated_client: TestClient) -> None:
    response = authenticated_client.get("/mi-cuenta")

    assert response.status_code == 200
    html = response.text
    assert "Actualizar contrasena" in html
    assert "Guardar nueva contrasena" in html


def test_crear_presupuesto_con_presets_y_escenarios(authenticated_client: TestClient) -> None:
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

    response = authenticated_client.post("/presupuestos", json=payload)

    assert response.status_code == 200
    body = response.json()["presupuesto"]
    assert body["escenario_referencia_nombre"] == "40 copias"
    assert body["escenarios"][0]["items"][0]["nota"] == "Cotizado manualmente en https://print.livriz.com"


def test_crear_presupuesto_registra_version_inicial(authenticated_client: TestClient) -> None:
    response = authenticated_client.post("/presupuestos", json=_payload_presupuesto_demo())

    assert response.status_code == 200
    presupuesto_id = response.json()["presupuesto"]["id"]

    with database.get_connection() as connection:
        versiones = connection.execute(
            """
            SELECT version_num, evento, resumen_cambios, created_by
            FROM presupuesto_versiones
            WHERE presupuesto_id = ?
            ORDER BY version_num ASC
            """,
            (presupuesto_id,),
        ).fetchall()

    assert len(versiones) == 1
    assert versiones[0]["version_num"] == 1
    assert versiones[0]["evento"] == "creacion"
    assert versiones[0]["created_by"] == "admin"
    assert "Version inicial" in versiones[0]["resumen_cambios"]


def test_detalle_muestra_historial_de_versiones(authenticated_client: TestClient) -> None:
    crear = authenticated_client.post("/presupuestos", json=_payload_presupuesto_demo())
    presupuesto_id = crear.json()["presupuesto"]["id"]

    response = authenticated_client.get(f"/presupuestos/{presupuesto_id}")

    assert response.status_code == 200
    html = response.text
    assert "Historial" in html
    assert "Version 1" in html
    assert "Actual" in html


def test_actualizar_presupuesto_registra_nueva_version_con_cambios(authenticated_client: TestClient) -> None:
    crear = authenticated_client.post("/presupuestos", json=_payload_presupuesto_demo())
    presupuesto_id = crear.json()["presupuesto"]["id"]
    payload = _payload_presupuesto_demo()
    payload["cliente"] = "Cliente Actualizado"
    payload["escenarios"][0]["cantidad_copias"] = 80
    payload["escenarios"][0]["items"][0]["monto"] = 160000

    response = authenticated_client.put(f"/presupuestos/{presupuesto_id}", json=payload)

    assert response.status_code == 200
    with database.get_connection() as connection:
        versiones = connection.execute(
            """
            SELECT version_num, evento, resumen_cambios, created_by
            FROM presupuesto_versiones
            WHERE presupuesto_id = ?
            ORDER BY version_num ASC
            """,
            (presupuesto_id,),
        ).fetchall()

    assert len(versiones) == 2
    assert versiones[1]["version_num"] == 2
    assert versiones[1]["evento"] == "actualizacion"
    assert versiones[1]["created_by"] == "admin"
    assert "cliente" in versiones[1]["resumen_cambios"].lower() or "copias" in versiones[1]["resumen_cambios"].lower()


def test_validacion_exige_impresion_en_cada_escenario(authenticated_client: TestClient) -> None:
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

    response = authenticated_client.post("/presupuestos", json=payload)

    assert response.status_code == 422
    assert "Impresion" in response.text


def test_validacion_rechaza_nombres_duplicados_de_escenarios(authenticated_client: TestClient) -> None:
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

    response = authenticated_client.post("/presupuestos", json=payload)

    assert response.status_code == 422
    assert "unicos" in response.text


def test_restaurar_version_revierte_el_presupuesto(authenticated_client: TestClient) -> None:
    crear = authenticated_client.post("/presupuestos", json=_payload_presupuesto_demo())
    presupuesto_id = crear.json()["presupuesto"]["id"]

    payload_editado = _payload_presupuesto_demo()
    payload_editado["cliente"] = "Cliente Editado"
    payload_editado["notas"] = "Version editada"
    payload_editado["escenarios"][0]["cantidad_copias"] = 90
    payload_editado["escenarios"][0]["items"][0]["monto"] = 180000
    actualizar = authenticated_client.put(f"/presupuestos/{presupuesto_id}", json=payload_editado)
    assert actualizar.status_code == 200

    with database.get_connection() as connection:
        version_inicial = connection.execute(
            """
            SELECT id
            FROM presupuesto_versiones
            WHERE presupuesto_id = ? AND version_num = 1
            """,
            (presupuesto_id,),
        ).fetchone()

    restaurar = authenticated_client.post(
        f"/presupuestos/{presupuesto_id}/versiones/{version_inicial['id']}/restaurar"
    )

    assert restaurar.status_code == 200
    presupuesto = restaurar.json()["presupuesto"]
    assert presupuesto["cliente"] == "Cliente Demo"
    assert presupuesto["notas"] == "Version inicial"
    assert presupuesto["escenarios"][0]["cantidad_copias"] == 50

    with database.get_connection() as connection:
        versiones = connection.execute(
            """
            SELECT version_num, evento, resumen_cambios
            FROM presupuesto_versiones
            WHERE presupuesto_id = ?
            ORDER BY version_num ASC
            """,
            (presupuesto_id,),
        ).fetchall()

    assert len(versiones) == 3
    assert versiones[2]["evento"] == "restauracion"
    assert "version 1" in versiones[2]["resumen_cambios"].lower()


def test_login_bloquea_ruta_api_sin_sesion(client: TestClient) -> None:
    response = client.post(
        "/api/calcular",
        json={
            "nombre": "Escenario 1",
            "cantidad_copias": 10,
            "porcentaje_ganancia": 20,
            "tipo_de_cambio_snapshot": 1400,
            "items": [{"nombre": "Impresion", "monto": 1000, "nota": None}],
        },
    )

    assert response.status_code == 401


def test_login_bloquea_temporalmente_tras_intentos_fallidos(client: TestClient) -> None:
    for _ in range(5):
        response = client.post(
            "/login",
            data={
                "username": "admin",
                "password": "incorrecta",
                "next": "/",
            },
        )

    assert response.status_code == 401
    assert "bloqueado temporalmente" in response.text


def test_config_permite_actualizar_credenciales_y_reingresar(authenticated_client: TestClient) -> None:
    response = authenticated_client.put(
        "/config/credenciales",
        json={
            "current_password": "Admin123!!",
            "nuevo_username": "admin_firmamento",
            "nueva_password": "ClaveFuerte2026!",
            "confirmar_password": "ClaveFuerte2026!",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["credenciales"]["username"] == "admin_firmamento"
    assert body["credenciales"]["origen"] == "base_de_datos"

    logout_response = authenticated_client.post("/logout", follow_redirects=False)
    assert logout_response.status_code == 303

    old_login_response = authenticated_client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!!",
            "next": "/",
        },
    )
    assert old_login_response.status_code == 401

    new_login_response = authenticated_client.post(
        "/login",
        data={
            "username": "admin_firmamento",
            "password": "ClaveFuerte2026!",
            "next": "/",
        },
        follow_redirects=False,
    )
    assert new_login_response.status_code == 303
    assert new_login_response.headers["location"] == "/"


def test_config_rechaza_cambio_de_credenciales_con_password_actual_incorrecta(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.put(
        "/config/credenciales",
        json={
            "current_password": "NoEsLaActual123!",
            "nuevo_username": "admin_firmamento",
            "nueva_password": "ClaveFuerte2026!",
            "confirmar_password": "ClaveFuerte2026!",
        },
    )

    assert response.status_code == 400
    assert "actual" in response.text


def test_mi_cuenta_permite_cambiar_solo_password_y_reingresar(authenticated_client: TestClient) -> None:
    response = authenticated_client.put(
        "/mi-cuenta/password",
        json={
            "current_password": "Admin123!!",
            "nueva_password": "OtraClave2026!",
            "confirmar_password": "OtraClave2026!",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["credenciales"]["username"] == "admin"
    assert body["credenciales"]["origen"] == "base_de_datos"

    logout_response = authenticated_client.post("/logout", follow_redirects=False)
    assert logout_response.status_code == 303

    old_login_response = authenticated_client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!!",
            "next": "/",
        },
    )
    assert old_login_response.status_code == 401

    new_login_response = authenticated_client.post(
        "/login",
        data={
            "username": "admin",
            "password": "OtraClave2026!",
            "next": "/",
        },
        follow_redirects=False,
    )
    assert new_login_response.status_code == 303
    assert new_login_response.headers["location"] == "/"


def test_mi_cuenta_rechaza_password_actual_incorrecta(authenticated_client: TestClient) -> None:
    response = authenticated_client.put(
        "/mi-cuenta/password",
        json={
            "current_password": "NoEsLaActual123!",
            "nueva_password": "OtraClave2026!",
            "confirmar_password": "OtraClave2026!",
        },
    )

    assert response.status_code == 400
    assert "actual" in response.text
