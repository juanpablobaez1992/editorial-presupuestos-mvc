from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from controllers.auth_controller import router as auth_router
from controllers.config_controller import router as config_router
from controllers.presupuesto_controller import router as presupuesto_router
from controllers.system_controller import router as system_router
from database import init_database
from settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()
    init_database()
    yield


settings = get_settings()
app = FastAPI(
    title="Sistema de Presupuestos Editorial",
    lifespan=lifespan,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    session_cookie=settings.session_cookie_name,
    max_age=settings.session_max_age_seconds,
    same_site="strict",
    https_only=settings.session_secure_cookies,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth_router)
app.include_router(system_router)
app.include_router(presupuesto_router)
app.include_router(config_router)
