from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from controllers.controller_utils import (
    construir_contexto,
    exigir_login_html,
    obtener_ip_cliente,
    obtener_next_seguro,
    obtener_usuario_sesion,
)
from models.auth_model import autenticar_usuario
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
