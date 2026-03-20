from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from core.security import require_session_user
from core.state import APP_STATE, get_app_state, update_app_state
from services.chat_service import (
    create_chat_record,
    create_message_with_context,
    delete_all_messages_for_all_chats,
    delete_all_messages_for_chat,
    delete_chat_record,
    list_all_messages,
    list_chats,
    list_messages_for_chat,
)
from services.file_service import delete_upload, list_uploads, save_upload

router = APIRouter(prefix="/api", tags=["chat"])


def _require_auth(request: Request) -> dict:
    try:
        return require_session_user(request)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/state", response_class=JSONResponse)
async def state_view(request: Request):
    user = _require_auth(request)

    return {
        "ok": True,
        "state": get_app_state(),
        "user": user,
    }


@router.post("/state", response_class=JSONResponse)
async def state_update(request: Request):
    user = _require_auth(request)

    body = await request.json()

    state = update_app_state(
        active_chat_id=body.get("active_chat_id", APP_STATE.get("active_chat_id")),
        selected_model=body.get("selected_model", APP_STATE.get("selected_model")),
        user=APP_STATE.get("user"),
        theme=body.get("theme", APP_STATE.get("theme")),
    )

    return {
        "ok": True,
        "state": state,
        "user": user,
    }


@router.get("/chats", response_class=JSONResponse)
async def get_chats(request: Request):
    _require_auth(request)

    return {
        "chats": list_chats(),
    }


@router.post("/chats", response_class=JSONResponse)
async def post_chat(request: Request):
    _require_auth(request)

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    chat = create_chat_record(title=body.get("title"))
    return chat


@router.delete("/chats/{chat_id}", response_class=JSONResponse)
async def remove_chat(chat_id: int, request: Request):
    _require_auth(request)
    return delete_chat_record(chat_id)


@router.get("/messages", response_class=JSONResponse)
async def get_all_messages(request: Request):
    _require_auth(request)

    return {
        "messages": list_all_mes
sages(),
    }


@router.get("/chats/{chat_id}/messages", response_class=JSONResponse)
async def get_chat_messages(chat_id: int, request: Request):
    _require_auth(request)

    return {
        "chat_id": chat_id,
        "messages": list_messages_for_chat(chat_id),
    }


@router.post("/messages", response_class=JSONResponse)
async def post_message(request: Request):
    _require_auth(request)

    body = await request.json()

    try:
        result = create_message_with_context(
            chat_id=int(body.get("chat_id", 1)),
            role=str(body.get("role", "user")),
            content=str(body.get("content", "")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result


@router.delete("/messages", response_class=JSONResponse)
async def delete_all_messages(request: Request):
    _require_auth(request)
    return delete_all_messages_for_all_chats()


@router.delete("/chats/{chat_id}/messages", response_class=JSONResponse)
async def delete_chat_messages(chat_id: int, request: Request):
    _require_auth(request)
    return delete_all_messages_for_chat(chat_id)


@router.get("/uploads", response_class=JSONResponse)
async def uploads_list(request: Request):
    _require_auth(request)

    return {
        "ok": True,
        "items": list_uploads(),
    }


@router.post("/uploads", response_class=JSONResponse)
async def uploads_create(request: Request, file: UploadFile = File(...)):
    _require_auth(request)

    try:
        item = save_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc

    return {
        "ok": True,
        "item": item,
    }


@router.delete("/uploads/{upload_id}", response_class=JSONResponse)
async def uploads_remove(upload_id: int, request: Request):
    _require_auth(request)

    try:
        result = delete_upload(upload_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return result