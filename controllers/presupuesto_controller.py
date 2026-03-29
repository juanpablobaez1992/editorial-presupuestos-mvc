from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from models import presupuesto_model
from models.calculations import calcular_escenario_completo
from models.config_model import obtener_catalogo_presets, obtener_configuracion
from models.schemas import CalculoEscenarioRequest, PresupuestoCreate, PresupuestoUpdate
from services.export_service import generar_excel_presupuesto
from views import templates


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, q: str = Query(default="")):
    presupuestos = presupuesto_model.obtener_todos(q or None)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "presupuestos": presupuestos,
            "busqueda": q,
        },
    )


@router.get("/presupuestos/nuevo", response_class=HTMLResponse)
async def formulario_nuevo_presupuesto(request: Request):
    configuracion = obtener_configuracion()
    presets_costos = obtener_catalogo_presets(configuracion)
    presupuesto_inicial = {
        "nombre_proyecto": "",
        "cliente": "",
        "fecha": date.today().isoformat(),
        "notas": "",
        "escenarios": [
            {
                "nombre": "Escenario 1",
                "cantidad_copias": 50,
                "porcentaje_ganancia": 45,
                "tipo_de_cambio_snapshot": configuracion["tipo_de_cambio"],
                "items": [
                    {
                        "nombre": "Impresion",
                        "monto": 0,
                        "nota": "Cotizado manualmente en https://print.livriz.com",
                    },
                    {
                        "nombre": "Edicion interior",
                        "monto": 0,
                        "nota": "",
                    },
                ],
            }
        ],
    }
    return templates.TemplateResponse(
        request,
        "presupuesto_form.html",
        {
            "request": request,
            "modo": "crear",
            "presupuesto": presupuesto_inicial,
            "configuracion": configuracion,
            "presets_costos": presets_costos,
        },
    )


@router.post("/presupuestos")
async def crear_presupuesto(datos: PresupuestoCreate):
    nuevo = presupuesto_model.crear(datos)
    return JSONResponse(
        {
            "ok": True,
            "presupuesto": nuevo,
            "redirect_url": f"/presupuestos/{nuevo['id']}",
        }
    )


@router.get("/presupuestos/{presupuesto_id}", response_class=HTMLResponse)
async def ver_presupuesto(request: Request, presupuesto_id: str):
    presupuesto = presupuesto_model.obtener_por_id(presupuesto_id)
    if presupuesto is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")
    return templates.TemplateResponse(
        request,
        "presupuesto_detail.html",
        {
            "request": request,
            "presupuesto": presupuesto,
        },
    )


@router.get("/presupuestos/{presupuesto_id}/editar", response_class=HTMLResponse)
async def editar_presupuesto(request: Request, presupuesto_id: str):
    presupuesto = presupuesto_model.obtener_por_id(presupuesto_id)
    if presupuesto is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")
    configuracion = obtener_configuracion()
    presets_costos = obtener_catalogo_presets(configuracion)
    return templates.TemplateResponse(
        request,
        "presupuesto_form.html",
        {
            "request": request,
            "modo": "editar",
            "presupuesto": presupuesto,
            "configuracion": configuracion,
            "presets_costos": presets_costos,
        },
    )


@router.put("/presupuestos/{presupuesto_id}")
async def actualizar_presupuesto(presupuesto_id: str, datos: PresupuestoUpdate):
    actualizado = presupuesto_model.actualizar(presupuesto_id, datos)
    if actualizado is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")
    return JSONResponse(
        {
            "ok": True,
            "presupuesto": actualizado,
            "redirect_url": f"/presupuestos/{presupuesto_id}",
        }
    )


@router.delete("/presupuestos/{presupuesto_id}")
async def eliminar_presupuesto(presupuesto_id: str):
    eliminado = presupuesto_model.eliminar(presupuesto_id)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")
    return JSONResponse({"ok": True, "redirect_url": "/"})


@router.post("/presupuestos/{presupuesto_id}/duplicar")
async def duplicar_presupuesto(presupuesto_id: str):
    duplicado = presupuesto_model.duplicar(presupuesto_id)
    if duplicado is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")
    return JSONResponse(
        {
            "ok": True,
            "presupuesto": duplicado,
            "redirect_url": f"/presupuestos/{duplicado['id']}",
        }
    )


@router.get("/presupuestos/{presupuesto_id}/export")
async def exportar_presupuesto(presupuesto_id: str):
    presupuesto = presupuesto_model.obtener_por_id(presupuesto_id)
    if presupuesto is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")

    archivo = generar_excel_presupuesto(presupuesto)
    nombre = presupuesto["nombre_proyecto"].replace(" ", "_").lower()
    headers = {
        "Content-Disposition": f'attachment; filename="{nombre or "presupuesto"}.xlsx"'
    }
    return StreamingResponse(
        archivo,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/api/calcular")
async def api_calcular(datos: CalculoEscenarioRequest):
    return JSONResponse(calcular_escenario_completo(datos.model_dump()))
