from __future__ import annotations

import hmac
from typing import Any

from pwdlib import PasswordHash

from database import get_connection
from settings import get_settings


password_hasher = PasswordHash.recommended()


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
        settings.auth_admin_username.casefold(),
    )
    password_valida = password_hasher.verify(password, settings.auth_password_hash)

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
        "usuario": settings.auth_admin_username,
    }
