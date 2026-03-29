from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from controllers.config_controller import router as config_router
from controllers.presupuesto_controller import router as presupuesto_router
from controllers.system_controller import router as system_router
from database import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(
    title="Sistema de Presupuestos Editorial",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(system_router)
app.include_router(presupuesto_router)
app.include_router(config_router)
