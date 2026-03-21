from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from core.security import require_session_user
from services.memory_service import (
    create_memory,
    delete_all_memory,
    delete_memory,
    get_all_memory,
    update_memory,
)

router = APIRouter(prefix="/api/memory", tags=["memory"])


def _require_auth(request: Request) -> dict:
    try:
        return require_session_user(request)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("", response_class=JSONResponse)
async def memory_list(request: Request):
    _require_auth(request)

    return {
        "ok": True,
        "items": get_all_memory(),
    }


@router.post("", response_class=JSONResponse)
async def memory_create(request: Request):
    _require_auth(request)

    body = await request.json()

    text = str(body.get("text", "")).strip()
    category = str(body.get("category", "general")).strip() or "general"
    pinned = bool(body.get("pinned", False))

    if not text:
        raise HTTPException(status_code=400, detail="Memory text is required.")

    item = create_memory(
        text=text,
        category=category,
        pinned=pinned,
    )

    return {
        "ok": True,
        "item": item,
    }


@router.put("/{memory_id}", response_class=JSONResponse)
async def memory_update(memory_id: int, request: Request):
    _require_auth(request)

    body = await request.json()

    try:
        item = update_memory(
            memory_id,
            text=body.get("text"),
            category=body.get("category"),
            pinned=body.get("pinned"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "ok": True,
        "item": item,
    }


@router.delete("/{memory_id}", response_class=JSONResponse)
async def memory_remove(memory_id: int, request: Request):
    _require_auth(request)

    try:
        result = delete_memory(memory_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return result


@router.delete("", response_class=JSONResponse)
async def memory_remove_all(request: Request):
    _require_auth(request)
    return delete_all_memory()