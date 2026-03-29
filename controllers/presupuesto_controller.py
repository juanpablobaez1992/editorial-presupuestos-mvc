from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse

from controllers.controller_utils import construir_contexto, exigir_login_api, exigir_login_html
from models import presupuesto_model
from models.calculations import calcular_escenario_completo
from models.config_model import obtener_catalogo_presets, obtener_configuracion
from models.project_template_model import obtener_tipos_proyecto
from models.schemas import CalculoEscenarioRequest, PresupuestoCreate, PresupuestoUpdate
from services.export_service import generar_excel_presupuesto, generar_pdf_presupuesto
from views import templates


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, q: str = Query(default="")):
    auth_guard = exigir_login_html(request)
    if isinstance(auth_guard, RedirectResponse):
        return auth_guard
    presupuestos = presupuesto_model.obtener_todos(q or None)
    metricas = presupuesto_model.calcular_metricas_dashboard(presupuestos)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        construir_contexto(
            request,
            presupuestos=presupuestos,
            metricas=metricas,
            busqueda=q,
        ),
    )


@router.get("/presupuestos/nuevo", response_class=HTMLResponse)
async def formulario_nuevo_presupuesto(request: Request):
    auth_guard = exigir_login_html(request)
    if isinstance(auth_guard, RedirectResponse):
        return auth_guard
    configuracion = obtener_configuracion()
    presets_costos = obtener_catalogo_presets(configuracion)
    tipos_proyecto = obtener_tipos_proyecto()
    presupuesto_inicial = {
        "nombre_proyecto": "",
        "cliente": "",
        "fecha": date.today().isoformat(),
        "notas": "",
        "tipo_proyecto_clave": None,
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
        construir_contexto(
            request,
            modo="crear",
            presupuesto=presupuesto_inicial,
            configuracion=configuracion,
            presets_costos=presets_costos,
            tipos_proyecto=tipos_proyecto,
        ),
    )


@router.post("/presupuestos")
async def crear_presupuesto(request: Request, datos: PresupuestoCreate):
    usuario = exigir_login_api(request)
    nuevo = presupuesto_model.crear(datos, usuario=usuario)
    return JSONResponse(
        {
            "ok": True,
            "presupuesto": nuevo,
            "redirect_url": f"/presupuestos/{nuevo['id']}",
        }
    )


@router.get("/presupuestos/{presupuesto_id}", response_class=HTMLResponse)
async def ver_presupuesto(request: Request, presupuesto_id: str):
    auth_guard = exigir_login_html(request)
    if isinstance(auth_guard, RedirectResponse):
        return auth_guard
    presupuesto = presupuesto_model.obtener_por_id(presupuesto_id, incluir_versiones=True)
    if presupuesto is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")
    return templates.TemplateResponse(
        request,
        "presupuesto_detail.html",
        construir_contexto(
            request,
            presupuesto=presupuesto,
        ),
    )


@router.get("/presupuestos/{presupuesto_id}/editar", response_class=HTMLResponse)
async def editar_presupuesto(request: Request, presupuesto_id: str):
    auth_guard = exigir_login_html(request)
    if isinstance(auth_guard, RedirectResponse):
        return auth_guard
    presupuesto = presupuesto_model.obtener_por_id(presupuesto_id)
    if presupuesto is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")
    configuracion = obtener_configuracion()
    presets_costos = obtener_catalogo_presets(configuracion)
    tipos_proyecto = obtener_tipos_proyecto()
    return templates.TemplateResponse(
        request,
        "presupuesto_form.html",
        construir_contexto(
            request,
            modo="editar",
            presupuesto=presupuesto,
            configuracion=configuracion,
            presets_costos=presets_costos,
            tipos_proyecto=tipos_proyecto,
        ),
    )


@router.put("/presupuestos/{presupuesto_id}")
async def actualizar_presupuesto(request: Request, presupuesto_id: str, datos: PresupuestoUpdate):
    usuario = exigir_login_api(request)
    actualizado = presupuesto_model.actualizar(presupuesto_id, datos, usuario=usuario)
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
async def eliminar_presupuesto(request: Request, presupuesto_id: str):
    exigir_login_api(request)
    eliminado = presupuesto_model.eliminar(presupuesto_id)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")
    return JSONResponse({"ok": True, "redirect_url": "/"})


@router.post("/presupuestos/{presupuesto_id}/duplicar")
async def duplicar_presupuesto(request: Request, presupuesto_id: str):
    usuario = exigir_login_api(request)
    duplicado = presupuesto_model.duplicar(presupuesto_id, usuario=usuario)
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
async def exportar_presupuesto(request: Request, presupuesto_id: str):
    exigir_login_api(request)
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


@router.get("/presupuestos/{presupuesto_id}/export/pdf")
async def exportar_presupuesto_pdf(request: Request, presupuesto_id: str):
    exigir_login_api(request)
    presupuesto = presupuesto_model.obtener_por_id(presupuesto_id)
    if presupuesto is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")

    archivo = generar_pdf_presupuesto(presupuesto)
    nombre = presupuesto["nombre_proyecto"].replace(" ", "_").lower()
    headers = {
        "Content-Disposition": f'attachment; filename="{nombre or "presupuesto"}.pdf"'
    }
    return StreamingResponse(
        archivo,
        headers=headers,
        media_type="application/pdf",
    )


@router.post("/api/calcular")
async def api_calcular(request: Request, datos: CalculoEscenarioRequest):
    exigir_login_api(request)
    return JSONResponse(calcular_escenario_completo(datos.model_dump()))


@router.post("/presupuestos/{presupuesto_id}/versiones/{version_id}/restaurar")
async def restaurar_version_presupuesto(request: Request, presupuesto_id: str, version_id: str):
    usuario = exigir_login_api(request)
    presupuesto = presupuesto_model.restaurar_version(presupuesto_id, version_id, usuario=usuario)
    if presupuesto is None:
        raise HTTPException(status_code=404, detail="Version o presupuesto no encontrado.")
    return JSONResponse(
        {
            "ok": True,
            "presupuesto": presupuesto,
            "redirect_url": f"/presupuestos/{presupuesto_id}",
        }
    )
