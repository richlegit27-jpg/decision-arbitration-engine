from pathlib import Path

path = Path("nova_backend/services/project_state_direct_freshness_bridge.py")

code = r'''
"""Project-state direct freshness bridge helpers.

Keeps project-state recall and adjacent project-status questions fresh while
moving decision/response construction out of app.py.
"""

DIRECT_ROUTE = "project_state_current_memory_direct_recall"
PROJECT_BRAIN_ROUTE = "project_brain_general_intelligence"
SOURCE = "project_brain_context_builder"

DIRECT_PROJECT_STATE_PROMPTS = {
    "what are we working on now",
    "what are we working on",
}

NEXT_MOVE_PROMPTS = {
    "what should we do next",
    "what do we do next",
    "what next",
    "what's next",
    "whats next",
}

CURRENT_BLOCKER_PROMPTS = {
    "what is the current blocker",
    "what's the current blocker",
    "whats the current blocker",
    "current blocker",
}


def _clean_text(value):
    return str(value or "").strip().lower()


def _normalize_prompt(value):
    return _clean_text(value).rstrip(" ?!.")


def classify_project_state_freshness_prompt(user_text):
    normalized = _normalize_prompt(user_text)

    if normalized in DIRECT_PROJECT_STATE_PROMPTS:
        return "direct_project_state"

    if normalized in NEXT_MOVE_PROMPTS:
        return "next_move"

    if normalized in CURRENT_BLOCKER_PROMPTS:
        return "current_blocker"

    return ""


def is_exact_project_state_prompt(user_text):
    return classify_project_state_freshness_prompt(user_text) == "direct_project_state"


def _route_for_intent(intent):
    if intent == "direct_project_state":
        return DIRECT_ROUTE
    return PROJECT_BRAIN_ROUTE


def build_project_state_direct_fresh_response(payload):
    payload = payload or {}
    user_text = (
        payload.get("message")
        or payload.get("text")
        or payload.get("content")
        or ""
    )

    intent = classify_project_state_freshness_prompt(user_text)
    if not intent:
        return None

    from nova_backend.services.project_brain_context_builder import (
        build_current_project_answer,
    )

    answer = build_current_project_answer()
    session_id = payload.get("session_id") or payload.get("active_session_id") or ""
    route = _route_for_intent(intent)

    debug = {
        "route": route,
        "route_taken": route,
        "project_state_direct_freshness_bridge": True,
        "project_state_freshness_intent": intent,
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
                "route": route,
                "source": SOURCE,
                "project_state_freshness_intent": intent,
            },
        },
        "debug": debug,
    }
'''
path.write_text(code.lstrip(), encoding="utf-8")
print("extended project-state freshness bridge to next/blocker prompts")
