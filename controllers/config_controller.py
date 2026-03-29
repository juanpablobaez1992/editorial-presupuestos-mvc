from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from models.config_model import actualizar_configuracion, obtener_configuracion
from models.schemas import ConfiguracionUpdate
from views import templates


router = APIRouter()


@router.get("/config", response_class=HTMLResponse)
async def ver_configuracion(request: Request):
    configuracion = obtener_configuracion()
    return templates.TemplateResponse(
        request,
        "config.html",
        {
            "request": request,
            "configuracion": configuracion,
        },
    )


@router.put("/config")
async def guardar_configuracion(datos: ConfiguracionUpdate):
    configuracion = actualizar_configuracion(datos)
    return JSONResponse(
        {
            "ok": True,
            "configuracion": configuracion,
        }
    )
