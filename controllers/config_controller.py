from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi import HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from controllers.controller_utils import construir_contexto, exigir_login_api, exigir_login_html
from models.auth_model import actualizar_credenciales_admin, obtener_estado_credenciales
from models.config_model import actualizar_configuracion, obtener_configuracion
from models.schemas import ConfiguracionUpdate, CredencialesAdminUpdate
from views import templates


router = APIRouter()


@router.get("/config", response_class=HTMLResponse)
async def ver_configuracion(request: Request):
    auth_guard = exigir_login_html(request)
    if isinstance(auth_guard, RedirectResponse):
        return auth_guard
    configuracion = obtener_configuracion()
    credenciales = obtener_estado_credenciales()
    return templates.TemplateResponse(
        request,
        "config.html",
        construir_contexto(
            request,
            configuracion=configuracion,
            credenciales=credenciales,
        ),
    )


@router.put("/config")
async def guardar_configuracion(request: Request, datos: ConfiguracionUpdate):
    exigir_login_api(request)
    configuracion = actualizar_configuracion(datos)
    return JSONResponse(
        {
            "ok": True,
            "configuracion": configuracion,
        }
    )


@router.put("/config/credenciales")
async def guardar_credenciales(request: Request, datos: CredencialesAdminUpdate):
    exigir_login_api(request)
    try:
        credenciales = actualizar_credenciales_admin(datos)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    request.session["auth_user"] = credenciales["username"]
    return JSONResponse(
        {
            "ok": True,
            "credenciales": credenciales,
        }
    )
