from pathlib import Path

service_path = Path("nova_backend/services/project_state_direct_freshness_bridge.py")

service_code = r'''
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
'''

service_path.write_text(service_code.lstrip(), encoding="utf-8")

app_path = Path("app.py")
text = app_path.read_text(encoding="utf-8")

start_marker = "# NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702"
next_marker = "# NOVA_PROJECT_STATE_CURRENT_MEMORY_DIRECT_RECALL_20260701"

start = text.find(start_marker)
end = text.find(next_marker)

if start == -1:
    raise SystemExit("direct freshness bridge marker not found")

if end == -1 or end <= start:
    raise SystemExit("next project-state direct recall marker not found after bridge")

replacement = r'''
# NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702
# Fresh exact project-state recall bridge.
# Thin app.py adapter; decision and response construction live in service layer.
try:
    from flask import jsonify as _nova_project_state_direct_fresh_jsonify_20260702
    from flask import request as _nova_project_state_direct_fresh_request_20260702

    @app.before_request
    def _nova_project_state_direct_freshness_bridge_20260702():
        try:
            if _nova_project_state_direct_fresh_request_20260702.path != "/api/chat":
                return None

            if _nova_project_state_direct_fresh_request_20260702.method != "POST":
                return None

            payload = _nova_project_state_direct_fresh_request_20260702.get_json(silent=True) or {}

            from nova_backend.services.project_state_direct_freshness_bridge import (
                build_project_state_direct_fresh_response,
            )

            response_json = build_project_state_direct_fresh_response(payload)
            if not response_json:
                return None

            return _nova_project_state_direct_fresh_jsonify_20260702(response_json)

        except Exception as exc:
            try:
                print("[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702] failed:", exc)
            except Exception:
                pass
            return None

    print("[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702] installed")
except Exception as _nova_project_state_direct_freshness_bridge_error_20260702:
    print("[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702] failed:", _nova_project_state_direct_freshness_bridge_error_20260702)


'''

text = text[:start] + replacement.lstrip() + "\n" + text[end:]
app_path.write_text(text, encoding="utf-8")

print("extracted direct freshness bridge helpers into service layer")
