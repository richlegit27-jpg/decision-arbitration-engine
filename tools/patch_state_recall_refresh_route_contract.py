from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_state_recall_refresh.py")
SMOKE = Path("tools/nova_project_brain_state_recall_refresh_smoke.py")

text = SERVICE.read_text(encoding="utf-8-sig")

old = r'''
def should_refresh_project_state_answer(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False

    debug = payload.get("debug")
    if not isinstance(debug, dict):
        debug = {}

    route = (
        payload.get("route")
        or payload.get("route_taken")
        or debug.get("route_taken")
        or debug.get("route")
        or ""
    )

    if route == PROJECT_STATE_ROUTE:
        return True

    assistant_message = payload.get("assistant_message")
    assistant_text = ""
    if isinstance(assistant_message, dict):
        assistant_text = _clean(
            assistant_message.get("text")
            or assistant_message.get("content")
            or assistant_message.get("message")
        )

    combined = "\n".join([
        _clean(payload.get("text")),
        _clean(payload.get("answer")),
        _clean(payload.get("message")),
        assistant_text,
    ])

    return answer_has_stale_cleanup(combined)
'''

new = r'''
def should_refresh_project_state_answer(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False

    debug = payload.get("debug")
    if not isinstance(debug, dict):
        debug = {}

    route = (
        payload.get("route")
        or payload.get("route_taken")
        or debug.get("route_taken")
        or debug.get("route")
        or ""
    )

    intent = _clean(
        payload.get("intent")
        or debug.get("intent")
        or debug.get("command_intent")
    )

    delegated = bool(
        payload.get("compact_project_context_delegated")
        or debug.get("compact_project_context_delegated")
    )

    # Critical route contract:
    # State Recall Refresh may only repair true direct project-state recall.
    # Broad Project Brain paraphrases must stay on project_brain_general_intelligence,
    # even if their answer text mentions stale cleanup risk.
    if route != PROJECT_STATE_ROUTE:
        return False

    if delegated or intent == "general_project_answer":
        return False

    return True
'''

if old not in text:
    raise SystemExit("target should_refresh_project_state_answer block not found")

SERVICE.write_text(text.replace(old, new), encoding="utf-8")

smoke_text = SMOKE.read_text(encoding="utf-8-sig")

insert = r'''
        general_payload = {
            "debug": {
                "route_taken": "project_brain_general_intelligence",
                "compact_project_context_delegated": True,
            },
            "route": "project_brain_general_intelligence",
            "intent": "general_project_answer",
            "compact_project_context_delegated": True,
            "assistant_message": {
                "text": "Remaining risk: Start Project Brain cleanup/consolidation",
                "content": "Remaining risk: Start Project Brain cleanup/consolidation",
            },
            "text": "Remaining risk: Start Project Brain cleanup/consolidation",
        }

        general_refreshed = refresh_project_state_payload(general_payload, memory_path=memory_path)
        assert_true("general intelligence route untouched", general_refreshed == general_payload, general_refreshed)
'''

anchor = r'''
        normal_payload = {
            "debug": {"route_taken": "chat"},
            "assistant_message": {"text": "normal chat"},
            "text": "normal chat",
        }
'''

if "general intelligence route untouched" not in smoke_text:
    if anchor not in smoke_text:
        raise SystemExit("smoke anchor not found")
    smoke_text = smoke_text.replace(anchor, insert + "\n" + anchor)

SMOKE.write_text(smoke_text, encoding="utf-8")

print("patched State Recall Refresh route contract")
