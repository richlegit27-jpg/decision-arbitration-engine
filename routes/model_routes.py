from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.config import APP_TITLE, APP_VERSION, AVAILABLE_MODELS, DEFAULT_MODEL

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/health", response_class=JSONResponse)
async def health():
    return {
        "ok": True,
        "app": APP_TITLE,
        "version": APP_VERSION,
        "default_model": DEFAULT_MODEL,
        "models": AVAILABLE_MODELS,
    }


@router.get("/models", response_class=JSONResponse)
async def list_models():
    return {
        "ok": True,
        "default_model": DEFAULT_MODEL,
        "models": AVAILABLE_MODELS,
    }