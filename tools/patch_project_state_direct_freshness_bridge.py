from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "# NOVA_PROJECT_STATE_CURRENT_MEMORY_DIRECT_RECALL_20260701"
bridge_marker = "# NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702"

if bridge_marker in text:
    print("direct freshness bridge already installed")
    raise SystemExit(0)

if marker not in text:
    raise SystemExit("direct project-state recall marker not found")

bridge = r'''
# NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702
# Fresh exact project-state recall bridge.
# Preserves route_taken=project_state_current_memory_direct_recall while sourcing answer text
# from the Project Brain context builder / freshness snapshot path.
try:
    from flask import jsonify as _nova_project_state_direct_fresh_jsonify_20260702
    from flask import request as _nova_project_state_direct_fresh_request_20260702

    def _nova_project_state_direct_fresh_text_20260702(value):
        return str(value or "").strip().lower()

    def _nova_project_state_direct_fresh_is_exact_prompt_20260702(user_text):
        normalized = _nova_project_state_direct_fresh_text_20260702(user_text)
        normalized = normalized.rstrip(" ?!.")
        return normalized in {
            "what are we working on now",
            "what are we working on",
        }

    @app.before_request
    def _nova_project_state_direct_freshness_bridge_20260702():
        try:
            if _nova_project_state_direct_fresh_request_20260702.path != "/api/chat":
                return None

            if _nova_project_state_direct_fresh_request_20260702.method != "POST":
                return None

            payload = _nova_project_state_direct_fresh_request_20260702.get_json(silent=True) or {}
            user_text = (
                payload.get("message")
                or payload.get("text")
                or payload.get("content")
                or ""
            )

            if not _nova_project_state_direct_fresh_is_exact_prompt_20260702(user_text):
                return None

            from nova_backend.services.project_brain_context_builder import (
                build_current_project_answer,
            )

            answer = build_current_project_answer()
            session_id = payload.get("session_id") or payload.get("active_session_id") or ""

            debug = {
                "route": "project_state_current_memory_direct_recall",
                "route_taken": "project_state_current_memory_direct_recall",
                "project_state_direct_freshness_bridge": True,
                "source": "project_brain_context_builder",
            }

            response_json = {
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
                        "route": "project_state_current_memory_direct_recall",
                        "source": "project_brain_context_builder",
                    },
                },
                "debug": debug,
            }

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

text = text.replace(marker, bridge + "\n" + marker, 1)
path.write_text(text, encoding="utf-8")
print("installed direct project-state freshness bridge before stale direct recall guard")
