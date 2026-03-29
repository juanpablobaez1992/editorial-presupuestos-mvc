from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse


router = APIRouter()


@router.get("/health")
async def healthcheck():
    return JSONResponse({"ok": True, "status": "healthy"})
