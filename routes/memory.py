from fastapi import APIRouter, Body, HTTPException, Request

from services.auth_service import get_user_by_username
from services.memory_service import (
    create_memory_item,
    delete_all_memory_items,
    delete_memory_item,
    list_memory_items,
)

router = APIRouter(prefix="/api/memory", tags=["memory"])


def get_current_user(request: Request):
    username = (request.cookies.get("nova_username") or "").strip().lower()
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user


@router.get("")
async def list_memory(request: Request):
    user = get_current_user(request)
    items = list_memory_items(user["id"])
    return {"items": items}


@router.post("")
async def create_memory(request: Request, payload: dict = Body(default={})):
    user = get_current_user(request)
    content = str((payload or {}).get("content", "")).strip()

    if not content:
        raise HTTPException(status_code=400, detail="Memory content is required")

    item = create_memory_item(user["id"], content)
    if not item:
        raise HTTPException(status_code=400, detail="Could not create memory item")

    return {"item": item}


@router.delete("/{memory_id}")
async def delete_single_memory(memory_id: int, request: Request):
    user = get_current_user(request)
    ok = delete_memory_item(user["id"], memory_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Memory item not found")

    return {"ok": True}


@router.delete("")
async def delete_all_memory(request: Request):
    user = get_current_user(request)
    delete_all_memory_items(user["id"])
    return {"ok": True}