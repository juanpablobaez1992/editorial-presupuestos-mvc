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
    activar_totp,
    autenticar_usuario,
    actualizar_password_admin,
    desactivar_totp,
    obtener_estado_credenciales,
    obtener_estado_totp,
    preparar_totp,
    verificar_totp,
)
from models.schemas import (
    PasswordAdminUpdate,
    TotpActivacionRequest,
    TotpCodigoRequest,
    TotpDesactivacionRequest,
)
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
    next_seguro = obtener_next_seguro(next)
    resultado = autenticar_usuario(username, password, obtener_ip_cliente(request))
    if not resultado["ok"]:
        return templates.TemplateResponse(
            request,
            "login.html",
            construir_contexto(
                request,
                next=next_seguro,
                error=resultado["mensaje"],
                auth_settings={
                    "login_max_attempts": settings.login_max_attempts,
                    "login_lockout_minutes": settings.login_lockout_minutes,
                },
            ),
            status_code=401,
        )

    request.session.clear()
    if resultado.get("requiere_totp"):
        request.session["pending_auth_user"] = resultado["usuario"]
        request.session["pending_auth_next"] = next_seguro
        return RedirectResponse(url=f"/login/2fa?next={next_seguro}", status_code=303)

    request.session["auth_user"] = resultado["usuario"]
    return RedirectResponse(url=next_seguro, status_code=303)


@router.get("/login/2fa", response_class=HTMLResponse)
async def ver_login_totp(request: Request, next: str = "/"):
    pending_user = request.session.get("pending_auth_user")
    if not pending_user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request,
        "login_totp.html",
        construir_contexto(
            request,
            next=obtener_next_seguro(request.session.get("pending_auth_next") or next),
            pending_user=str(pending_user),
            error=None,
        ),
    )


@router.post("/login/2fa", response_class=HTMLResponse)
async def login_totp(
    request: Request,
    codigo: str = Form(...),
    next: str = Form(default="/"),
):
    pending_user = request.session.get("pending_auth_user")
    next_seguro = obtener_next_seguro(request.session.get("pending_auth_next") or next)
    if not pending_user:
        return RedirectResponse(url="/login", status_code=303)

    try:
        datos = TotpCodigoRequest(codigo=codigo)
    except Exception as error:
        return templates.TemplateResponse(
            request,
            "login_totp.html",
            construir_contexto(
                request,
                next=next_seguro,
                pending_user=str(pending_user),
                error=str(error).split("Value error, ")[-1],
            ),
            status_code=400,
        )

    if not verificar_totp(datos):
        return templates.TemplateResponse(
            request,
            "login_totp.html",
            construir_contexto(
                request,
                next=next_seguro,
                pending_user=str(pending_user),
                error="El codigo TOTP no es valido.",
            ),
            status_code=401,
        )

    request.session.clear()
    request.session["auth_user"] = str(pending_user)
    return RedirectResponse(url=next_seguro, status_code=303)


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
    totp = obtener_estado_totp()
    return templates.TemplateResponse(
        request,
        "account.html",
        construir_contexto(
            request,
            credenciales=credenciales,
            totp=totp,
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


@router.post("/mi-cuenta/2fa/preparar")
async def preparar_totp_mi_cuenta(request: Request):
    exigir_login_api(request)
    estado = preparar_totp()
    return JSONResponse({"ok": True, "totp": estado})


@router.put("/mi-cuenta/2fa/activar")
async def activar_totp_mi_cuenta(request: Request, datos: TotpActivacionRequest):
    exigir_login_api(request)
    try:
        estado = activar_totp(datos)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return JSONResponse({"ok": True, "totp": estado})


@router.put("/mi-cuenta/2fa/desactivar")
async def desactivar_totp_mi_cuenta(request: Request, datos: TotpDesactivacionRequest):
    exigir_login_api(request)
    try:
        estado = desactivar_totp(datos)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return JSONResponse({"ok": True, "totp": estado})
