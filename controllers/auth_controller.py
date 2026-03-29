from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from controllers.controller_utils import (
    construir_contexto,
    exigir_login_api,
    exigir_login_html,
    obtener_ip_cliente,
    obtener_next_seguro,
    obtener_usuario_sesion,
)
from models.auth_model import (
    autenticar_usuario,
    actualizar_password_admin,
    obtener_estado_credenciales,
)
from models.schemas import PasswordAdminUpdate
from settings import get_settings
from views import templates


router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def ver_login(request: Request, next: str = "/"):
    auth_user = obtener_usuario_sesion(request)
    if auth_user:
        return RedirectResponse(url=obtener_next_seguro(next), status_code=303)
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "login.html",
        construir_contexto(
            request,
            next=obtener_next_seguro(next),
            error=None,
            auth_settings={
                "login_max_attempts": settings.login_max_attempts,
                "login_lockout_minutes": settings.login_lockout_minutes,
            },
        ),
    )


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/"),
):
    settings = get_settings()
    resultado = autenticar_usuario(username, password, obtener_ip_cliente(request))
    if not resultado["ok"]:
        return templates.TemplateResponse(
            request,
            "login.html",
            construir_contexto(
                request,
                next=obtener_next_seguro(next),
                error=resultado["mensaje"],
                auth_settings={
                    "login_max_attempts": settings.login_max_attempts,
                    "login_lockout_minutes": settings.login_lockout_minutes,
                },
            ),
            status_code=401,
        )

    request.session.clear()
    request.session["auth_user"] = resultado["usuario"]
    response = RedirectResponse(url=obtener_next_seguro(next), status_code=303)
    return response


@router.post("/logout")
async def logout(request: Request):
    maybe_redirect = exigir_login_html(request)
    if isinstance(maybe_redirect, RedirectResponse):
        return maybe_redirect
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/mi-cuenta", response_class=HTMLResponse)
async def ver_mi_cuenta(request: Request):
    auth_guard = exigir_login_html(request)
    if isinstance(auth_guard, RedirectResponse):
        return auth_guard
    credenciales = obtener_estado_credenciales()
    return templates.TemplateResponse(
        request,
        "account.html",
        construir_contexto(
            request,
            credenciales=credenciales,
        ),
    )


@router.put("/mi-cuenta/password")
async def guardar_password_mi_cuenta(request: Request, datos: PasswordAdminUpdate):
    exigir_login_api(request)
    try:
        credenciales = actualizar_password_admin(datos)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    request.session["auth_user"] = credenciales["username"]
    return JSONResponse(
        {
            "ok": True,
            "credenciales": credenciales,
        }
    )
