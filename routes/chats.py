from fastapi import APIRouter, Body, HTTPException, Request

from services.ai_service import generate_reply
from services.auth_service import get_user_by_username
from services.chat_service import (
    add_message,
    clear_chat_messages,
    create_chat,
    delete_chat,
    get_chat,
    list_chats,
    list_messages,
    rename_chat,
)
from services.memory_service import maybe_capture_memory_from_message

router = APIRouter(prefix="/api/chats", tags=["chats"])


def get_current_user(request: Request):
    username = (request.cookies.get("nova_username") or "").strip().lower()
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user


def build_auto_title(text: str) -> str:
    clean = " ".join(str(text or "").strip().split())
    if not clean:
        return "New chat"

    max_length = 48
    title = clean[:max_length].strip(" .,:;!?\n\t-")

    if not title:
        return "New chat"

    return title


def maybe_auto_title_chat(user_id: int, chat_id: int):
    chat = get_chat(user_id, chat_id)
    if not chat:
        return None

    current_title = str(chat.get("title") or "").strip()
    if current_title not in {"", "New chat", "Untitled chat"}:
        return chat

    messages = list_messages(user_id, chat_id) or []
    user_messages = [
        message
        for message in messages
        if str(message.get("role", "")).lower() == "user"
    ]

    if len(user_messages) != 1:
        return chat

    first_user_message = user_messages[0]
    auto_title = build_auto_title(first_user_message.get("content", ""))

    updated_chat = rename_chat(user_id, chat_id, auto_title)
    return updated_chat or chat


@router.get("")
async def get_chats(request: Request):
    user = get_current_user(request)
    chats = list_chats(user["id"])
    return {"items": chats}


@router.post("")
async def create_new_chat(request: Request, payload: dict = Body(default={})):
    user = get_current_user(request)
    title = (payload or {}).get("title", "New chat")
    chat = create_chat(user["id"], title)
    return {"item": chat}


@router.get("/{chat_id}")
async def get_single_chat(chat_id: int, request: Request):
    user = get_current_user(request)
    chat = get_chat(user["id"], chat_id)

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = list_messages(user["id"], chat_id) or []
    return {
        "item": chat,
        "messages": messages,
    }


@router.patch("/{chat_id}")
async def rename_single_chat(chat_id: int, request: Request, payload: dict = Body(default={})):
    user = get_current_user(request)
    title = (payload or {}).get("title", "")
    chat = rename_chat(user["id"], chat_id, title)

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    return {"item": chat}


@router.delete("/{chat_id}")
async def delete_single_chat(chat_id: int, request: Request):
    user = get_current_user(request)
    ok = delete_chat(user["id"], chat_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Chat not found")

    return {"ok": True}


@router.delete("/{chat_id}/messages")
async def clear_single_chat(chat_id: int, request: Request):
    user = get_current_user(request)
    ok = clear_chat_messages(user["id"], chat_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Chat not found")

    return {"ok": True}


@router.get("/{chat_id}/messages")
async def get_single_chat_messages(chat_id: int, request: Request):
    user = get_current_user(request)
    messages = list_messages(user["id"], chat_id)

    if messages is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    return {"items": messages}


@router.post("/{chat_id}/messages")
async def create_single_chat_message(chat_id: int, request: Request, payload: dict = Body(default={})):
    user = get_current_user(request)

    role = (payload or {}).get("role", "user")
    content = (payload or {}).get("content", "")

    message = add_message(user["id"], chat_id, role, content)

    if not message:
        raise HTTPException(status_code=400, detail="Could not create message")

    if str(role).strip().lower() == "user":
        maybe_capture_memory_from_message(user["id"], content)

    updated_chat = maybe_auto_title_chat(user["id"], chat_id)

    return {
        "item": message,
        "chat": updated_chat,
    }


@router.post("/{chat_id}/reply")
async def create_real_ai_reply(chat_id: int, request: Request, payload: dict = Body(default={})):
    user = get_current_user(request)

    chat = get_chat(user["id"], chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    user_content = str((payload or {}).get("content", "")).strip()
    model = str((payload or {}).get("model", "")).strip() or None

    if user_content:
        created_user_message = add_message(user["id"], chat_id, "user", user_content)
        if not created_user_message:
            raise HTTPException(status_code=400, detail="Could not save user message")
        maybe_capture_memory_from_message(user["id"], user_content)

    updated_chat_after_user_message = maybe_auto_title_chat(user["id"], chat_id)

    history = list_messages(user["id"], chat_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    try:
        assistant_text = generate_reply(history, model=model)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"AI reply failed: {error}") from error

    assistant_message = add_message(user["id"], chat_id, "assistant", assistant_text)
    if not assistant_message:
        raise HTTPException(status_code=500, detail="Could not save assistant reply")

    updated_messages = list_messages(user["id"], chat_id) or []
    updated_chat = get_chat(user["id"], chat_id) or updated_chat_after_user_message

    return {
        "item": assistant_message,
        "chat": updated_chat,
        "messages": updated_messages,
    }