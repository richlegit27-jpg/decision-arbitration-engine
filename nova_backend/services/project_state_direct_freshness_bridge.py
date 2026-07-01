"""Project-state direct freshness bridge helpers.

Keeps exact project-state recall behavior fresh while moving the
decision/response construction out of app.py.
"""

ROUTE = "project_state_current_memory_direct_recall"
SOURCE = "project_brain_context_builder"


def _clean_text(value):
    return str(value or "").strip().lower()


def is_exact_project_state_prompt(user_text):
    normalized = _clean_text(user_text).rstrip(" ?!.")
    return normalized in {
        "what are we working on now",
        "what are we working on",
    }


def build_project_state_direct_fresh_response(payload):
    payload = payload or {}
    user_text = (
        payload.get("message")
        or payload.get("text")
        or payload.get("content")
        or ""
    )

    if not is_exact_project_state_prompt(user_text):
        return None

    from nova_backend.services.project_brain_context_builder import (
        build_current_project_answer,
    )

    answer = build_current_project_answer()
    session_id = payload.get("session_id") or payload.get("active_session_id") or ""

    debug = {
        "route": ROUTE,
        "route_taken": ROUTE,
        "project_state_direct_freshness_bridge": True,
        "source": SOURCE,
    }

    return {
        "ok": True,
        "text": answer,
        "content": answer,
        "session_id": session_id,
        "active_session_id": session_id,
        "assistant_message": {
            "role": "assistant",
            "text": answer,
            "content": answer,
            "attachments": [],
            "meta": {
                "route": ROUTE,
                "source": SOURCE,
            },
        },
        "debug": debug,
    }
