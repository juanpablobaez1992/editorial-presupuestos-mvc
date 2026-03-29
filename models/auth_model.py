from __future__ import annotations

import hmac
from typing import Any

from pwdlib import PasswordHash

from database import get_connection
from settings import get_settings
from models.schemas import CredencialesAdminUpdate, PasswordAdminUpdate


password_hasher = PasswordHash.recommended()


def obtener_credenciales_admin() -> dict[str, str]:
    settings = get_settings()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT clave, valor
            FROM configuracion
            WHERE clave IN ('auth_admin_username', 'auth_password_hash')
            """
        )
        data = {row["clave"]: row["valor"] for row in cursor.fetchall()}

    username = data.get("auth_admin_username", settings.auth_admin_username)
    password_hash = data.get("auth_password_hash", settings.auth_password_hash)
    origen = "base_de_datos" if "auth_admin_username" in data and "auth_password_hash" in data else "entorno"
    return {
        "username": username,
        "password_hash": password_hash,
        "origen": origen,
    }


def limpiar_intentos_vencidos() -> None:
    settings = get_settings()
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM auth_intentos
            WHERE created_at < datetime('now', ?)
            """,
            (f"-{settings.login_lockout_minutes} minutes",),
        )


def contar_intentos_recientes(username: str, ip_address: str) -> int:
    settings = get_settings()
    limpiar_intentos_vencidos()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM auth_intentos
            WHERE username = ? AND ip_address = ? AND created_at >= datetime('now', ?)
            """,
            (username, ip_address, f"-{settings.login_lockout_minutes} minutes"),
        ).fetchone()
    return int(row["total"]) if row else 0


def registrar_intento_fallido(username: str, ip_address: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO auth_intentos (id, username, ip_address)
            VALUES (lower(hex(randomblob(16))), ?, ?)
            """,
            (username, ip_address),
        )


def limpiar_intentos_fallidos(username: str, ip_address: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM auth_intentos
            WHERE username = ? AND ip_address = ?
            """,
            (username, ip_address),
        )


def obtener_estado_bloqueo(username: str, ip_address: str) -> dict[str, Any]:
    settings = get_settings()
    total = contar_intentos_recientes(username, ip_address)
    restantes = max(settings.login_max_attempts - total, 0)
    return {
        "bloqueado": total >= settings.login_max_attempts,
        "intentos_fallidos": total,
        "intentos_restantes": restantes,
        "ventana_minutos": settings.login_lockout_minutes,
    }


def autenticar_usuario(username: str, password: str, ip_address: str) -> dict[str, Any]:
    settings = get_settings()
    credenciales = obtener_credenciales_admin()
    username_normalizado = username.strip()
    estado = obtener_estado_bloqueo(username_normalizado, ip_address)
    if estado["bloqueado"]:
        return {
            "ok": False,
            "mensaje": (
                f"Acceso bloqueado temporalmente por demasiados intentos fallidos. "
                f"Espera {settings.login_lockout_minutes} minutos."
            ),
            **estado,
        }

    usuario_valido = hmac.compare_digest(
        username_normalizado.casefold(),
        credenciales["username"].casefold(),
    )
    password_valida = password_hasher.verify(password, credenciales["password_hash"])

    if not (usuario_valido and password_valida):
        registrar_intento_fallido(username_normalizado, ip_address)
        nuevo_estado = obtener_estado_bloqueo(username_normalizado, ip_address)
        mensaje = "Usuario o contraseña incorrectos."
        if not nuevo_estado["bloqueado"] and nuevo_estado["intentos_restantes"] > 0:
            mensaje += f" Intentos restantes: {nuevo_estado['intentos_restantes']}."
        else:
            mensaje = (
                f"Acceso bloqueado temporalmente por demasiados intentos fallidos. "
                f"Espera {settings.login_lockout_minutes} minutos."
            )
        return {
            "ok": False,
            "mensaje": mensaje,
            **nuevo_estado,
        }

    limpiar_intentos_fallidos(username_normalizado, ip_address)
    return {
        "ok": True,
        "mensaje": "Autenticacion correcta.",
        "usuario": credenciales["username"],
    }


def obtener_estado_credenciales() -> dict[str, str]:
    credenciales = obtener_credenciales_admin()
    return {
        "username": credenciales["username"],
        "origen": credenciales["origen"],
    }


def actualizar_credenciales_admin(datos: CredencialesAdminUpdate) -> dict[str, str]:
    credenciales = obtener_credenciales_admin()
    password_actual_valida = password_hasher.verify(datos.current_password, credenciales["password_hash"])
    if not password_actual_valida:
        raise ValueError("La contrasena actual no es correcta.")

    nuevo_hash = password_hasher.hash(datos.nueva_password)
    with get_connection() as connection:
        connection.executemany(
            """
            INSERT INTO configuracion (clave, valor, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(clave) DO UPDATE SET
                valor = excluded.valor,
                updated_at = CURRENT_TIMESTAMP
            """,
            [
                ("auth_admin_username", datos.nuevo_username),
                ("auth_password_hash", nuevo_hash),
            ],
        )
        connection.execute("DELETE FROM auth_intentos")

    return obtener_estado_credenciales()


def actualizar_password_admin(datos: PasswordAdminUpdate) -> dict[str, str]:
    credenciales = obtener_credenciales_admin()
    password_actual_valida = password_hasher.verify(datos.current_password, credenciales["password_hash"])
    if not password_actual_valida:
        raise ValueError("La contrasena actual no es correcta.")

    nuevo_hash = password_hasher.hash(datos.nueva_password)
    with get_connection() as connection:
        connection.executemany(
            """
            INSERT INTO configuracion (clave, valor, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(clave) DO UPDATE SET
                valor = excluded.valor,
                updated_at = CURRENT_TIMESTAMP
            """,
            [
                ("auth_admin_username", credenciales["username"]),
                ("auth_password_hash", nuevo_hash),
            ],
        )
        connection.execute("DELETE FROM auth_intentos")

    return obtener_estado_credenciales()
