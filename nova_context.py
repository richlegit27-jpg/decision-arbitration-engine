from __future__ import annotations

import os
import threading
from datetime import UTC, datetime
from typing import Any

from openai import OpenAI

from auth_utils import DEV_BYPASS_AUTH, normalize_username
from services_agent import (
    agent_brain_prompt_impl,
    background_agent_worker_impl,
    ensure_agent_thread_impl,
    run_agent_step_for_session_impl,
)
from services_ai import (
    autonomous_loop_refine as ai_autonomous_loop_refine,
    call_model as ai_call_model,
)
from services_memory_relevance import (
    extract_memory_impl,
    get_relevant_memory_impl,
    get_user_memory_items_impl,
)
from services_reply import generate_reply_impl
from services_sessions import (
    add_message_impl,
    ensure_session_impl,
    get_owned_session_or_404_impl,
    get_user_sessions_impl,
)
from services_web import (
    is_web as web_is_web,
    search_web_for_query,
    wants_web_search,
)
from storage import (
    load_memory,
    load_sessions,
    load_users,
    save_memory as storage_save_memory,
    save_sessions as storage_save_sessions,
    save_users as storage_save_users,
)

DEFAULT_MODEL = (os.getenv("OPENAI_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY", "") or "").strip()
TAVILY_API_KEY = (os.getenv("TAVILY_API_KEY") or "").strip()

OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

LAST_ROUTER_META: dict[str, Any] = {
    "mode": "general",
    "intent": "default",
    "confidence": 1.0,
}

STATE_LOCK = threading.RLock()

AGENT_STATE: dict[str, Any] = {
    "enabled": False,
    "interval_seconds": 20,
    "last_tick_at": None,
    "last_error": "",
    "last_summary": "",
    "thread_started": False,
}

USERS: dict[str, dict[str, Any]] = load_users()
MEMORY_ITEMS: list[dict[str, Any]] = load_memory()
SESSIONS: dict[str, dict[str, Any]] = load_sessions()


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def save_users() -> None:
    storage_save_users(USERS)


def save_memory() -> None:
    storage_save_memory(MEMORY_ITEMS)


def save_sessions() -> None:
    storage_save_sessions(SESSIONS)


def get_user_memory_items(username: str) -> list[dict[str, Any]]:
    return get_user_memory_items_impl(
        username=username,
        memory_items=MEMORY_ITEMS,
        normalize_username_func=normalize_username,
    )


def extract_memory(text: str) -> dict[str, Any] | None:
    return extract_memory_impl(
        text=text,
        clean_text_func=clean_text,
        now_iso_func=now_iso,
    )


def get_relevant_memory(username: str, user_text: str) -> list[dict[str, Any]]:
    return get_relevant_memory_impl(
        username=username,
        user_text=user_text,
        memory_items=MEMORY_ITEMS,
        normalize_username_func=normalize_username,
        clean_text_func=clean_text,
    )


def ensure_session(session_id: str | None, username: str) -> str:
    return ensure_session_impl(
        session_id=session_id,
        username=username,
        sessions=SESSIONS,
        state_lock=STATE_LOCK,
        dev_bypass_auth=DEV_BYPASS_AUTH,
        last_router_meta=LAST_ROUTER_META,
        save_sessions_func=save_sessions,
        normalize_username_func=normalize_username,
        now_iso_func=now_iso,
        clean_text_func=clean_text,
    )


def get_user_sessions(username: str) -> list[dict[str, Any]]:
    return get_user_sessions_impl(
        username=username,
        sessions=SESSIONS,
        state_lock=STATE_LOCK,
        dev_bypass_auth=DEV_BYPASS_AUTH,
        normalize_username_func=normalize_username,
    )


def get_owned_session_or_404(
    session_id: str,
    username: str,
    jsonify_func,
) -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
    return get_owned_session_or_404_impl(
        session_id=session_id,
        username=username,
        sessions=SESSIONS,
        state_lock=STATE_LOCK,
        dev_bypass_auth=DEV_BYPASS_AUTH,
        normalize_username_func=normalize_username,
        jsonify_func=jsonify_func,
    )


def add_message(
    session_id: str,
    role: str,
    content: str,
    web_results: list[dict[str, Any]] | None = None,
    web_provider: str = "",
) -> dict[str, Any]:
    return add_message_impl(
        session_id=session_id,
        role=role,
        content=content,
        sessions=SESSIONS,
        state_lock=STATE_LOCK,
        save_sessions_func=save_sessions,
        now_iso_func=now_iso,
        web_results=web_results,
        web_provider=web_provider,
    )


def is_web() -> bool:
    return web_is_web(TAVILY_API_KEY)


def call_model(text: str, context: str = "") -> str:
    return ai_call_model(
        text=text,
        context=context,
        openai_client=OPENAI_CLIENT,
        default_model=DEFAULT_MODEL,
    )


def autonomous_loop_refine(user_text: str, base_answer: str, context: str = "") -> str:
    return ai_autonomous_loop_refine(
        user_text=user_text,
        base_answer=base_answer,
        context=context,
        call_model_func=call_model,
    )


def generate_reply(username: str, user_text: str, session_id: str) -> tuple[str, list[dict[str, Any]], str]:
    return generate_reply_impl(
        username=username,
        user_text=user_text,
        session_id=session_id,
        sessions=SESSIONS,
        state_lock=STATE_LOCK,
        save_sessions_func=save_sessions,
        wants_web_search_func=wants_web_search,
        search_web_for_query_func=search_web_for_query,
        tavily_api_key=TAVILY_API_KEY,
        get_relevant_memory_func=get_relevant_memory,
        call_model_func=call_model,
        clean_text_func=clean_text,
    )


def agent_brain_prompt(session_obj: dict[str, Any], username: str) -> str:
    return agent_brain_prompt_impl(
        session_obj=session_obj,
        username=username,
        get_relevant_memory_func=get_relevant_memory,
    )


def run_agent_step_for_session(session_id: str) -> str:
    return run_agent_step_for_session_impl(
        session_id=session_id,
        sessions=SESSIONS,
        agent_state=AGENT_STATE,
        state_lock=STATE_LOCK,
        save_sessions_func=save_sessions,
        normalize_username_func=normalize_username,
        get_relevant_memory_func=get_relevant_memory,
        call_model_func=call_model,
        autonomous_loop_refine_func=autonomous_loop_refine,
        add_message_func=add_message,
        now_iso_func=now_iso,
    )


def background_agent_worker() -> None:
    background_agent_worker_impl(
        sessions=SESSIONS,
        agent_state=AGENT_STATE,
        state_lock=STATE_LOCK,
        run_agent_step_for_session_func=run_agent_step_for_session,
        now_iso_func=now_iso,
    )


def ensure_agent_thread() -> None:
    ensure_agent_thread_impl(
        agent_state=AGENT_STATE,
        worker_target=background_agent_worker,
    )