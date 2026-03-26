from __future__ import annotations

import time
import uuid
from typing import Any, Callable


def ensure_session_impl(
    session_id: str | None,
    username: str,
    sessions: dict[str, dict[str, Any]],
    state_lock: Any,
    dev_bypass_auth: bool,
    last_router_meta: dict[str, Any],
    save_sessions_func: Callable[[], None],
    normalize_username_func: Callable[[str], str],
    now_iso_func: Callable[[], str],
    clean_text_func: Callable[[Any], str],
) -> str:
    sid = clean_text_func(session_id) or str(uuid.uuid4())
    username = normalize_username_func(username or "dev")

    with state_lock:
        if sid not in sessions:
            sessions[sid] = {
                "id": sid,
                "user": username,
                "title": "New Chat",
                "messages": [],
                "created_at": now_iso_func(),
                "updated_at": now_iso_func(),
                "router_meta": dict(last_router_meta),
                "last_web_results": [],
                "agent_enabled": False,
                "agent_goal": "",
                "agent_status": "idle",
                "agent_last_run_at": None,
                "agent_last_output": "",
                "pinned": False,
            }
            save_sessions_func()
        else:
            owner = normalize_username_func(str(sessions[sid].get("user", "")))
            if owner != username and not dev_bypass_auth:
                raise PermissionError("Session does not belong to current user.")

    return sid


def get_user_sessions_impl(
    username: str,
    sessions: dict[str, dict[str, Any]],
    state_lock: Any,
    dev_bypass_auth: bool,
    normalize_username_func: Callable[[str], str],
) -> list[dict[str, Any]]:
    username = normalize_username_func(username or "dev")

    with state_lock:
        if dev_bypass_auth and username == "dev":
            items = list(sessions.values())
        else:
            items = [
                session_obj
                for session_obj in sessions.values()
                if normalize_username_func(str(session_obj.get("user", ""))) == username
            ]

    items.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
    return items


def get_owned_session_or_404_impl(
    session_id: str,
    username: str,
    sessions: dict[str, dict[str, Any]],
    state_lock: Any,
    dev_bypass_auth: bool,
    normalize_username_func: Callable[[str], str],
    jsonify_func: Callable[[dict[str, Any]], Any],
) -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
    with state_lock:
        session_obj = sessions.get(session_id)

    if not session_obj:
        return None, (jsonify_func({"ok": False, "error": "Session not found"}), 404)

    if dev_bypass_auth:
        return session_obj, None

    owner = normalize_username_func(str(session_obj.get("user", "")))
    if owner != normalize_username_func(username or ""):
        return None, (jsonify_func({"ok": False, "error": "Forbidden"}), 403)

    return session_obj, None


def add_message_impl(
    session_id: str,
    role: str,
    content: str,
    sessions: dict[str, dict[str, Any]],
    state_lock: Any,
    save_sessions_func: Callable[[], None],
    now_iso_func: Callable[[], str],
    web_results: list[dict[str, Any]] | None = None,
    web_provider: str = "",
) -> dict[str, Any]:
    message = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "timestamp": int(time.time()),
        "web_results": web_results or [],
        "web_provider": web_provider or "",
    }

    with state_lock:
        session_obj = sessions.get(session_id)
        if not session_obj:
            raise KeyError(f"Session not found: {session_id}")

        session_obj.setdefault("messages", []).append(message)
        session_obj["updated_at"] = now_iso_func()

        if session_obj.get("title") in ("", "New Chat") and role == "user" and content.strip():
            session_obj["title"] = content.strip()[:60]

        if web_results is not None:
            session_obj["last_web_results"] = web_results

        save_sessions_func()

    return message