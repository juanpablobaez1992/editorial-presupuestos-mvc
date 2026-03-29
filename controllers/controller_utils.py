from __future__ import annotations

from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse


def obtener_ip_cliente(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "desconocido"


def obtener_usuario_sesion(request: Request) -> str | None:
    user = request.session.get("auth_user")
    if not user:
        return None
    return str(user)


def construir_contexto(request: Request, **kwargs):
    return {
        "request": request,
        "auth_user": obtener_usuario_sesion(request),
        **kwargs,
    }


def obtener_next_seguro(next_url: str | None) -> str:
    if not next_url or not next_url.startswith("/"):
        return "/"
    if next_url.startswith("//"):
        return "/"
    return next_url


def exigir_login_html(request: Request):
    auth_user = obtener_usuario_sesion(request)
    if auth_user:
        return auth_user
    destino = obtener_next_seguro(str(request.url.path))
    if request.url.query:
        destino = f"{destino}?{request.url.query}"
    return RedirectResponse(url=f"/login?next={quote(destino)}", status_code=303)


def exigir_login_api(request: Request) -> str:
    auth_user = obtener_usuario_sesion(request)
    if auth_user:
        return auth_user
    raise HTTPException(status_code=401, detail="Sesion expirada o no autenticada.")
