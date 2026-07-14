from app import app


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


print("=" * 80)
print("NOVA PHASE4G NORMAL CHAT AUTONOMY CARRYOVER SMOKE")
print("=" * 80)

from flask import Response
import json

from app import _nova_phase4g_normal_chat_carryover_guard_20260701


payload = {
    "ok": True,
    "session_id": "phase4g_test_session",
    "active_session_id": "phase4g_test_session",
    "assistant_message": {
        "role": "assistant",
        "text": "Nova Autonomy Task Brief: old execution context leaked.",
        "content": "Nova Autonomy Task Brief: old execution context leaked.",
    },
    "text": "Nova Autonomy Task Brief: old execution context leaked.",
    "debug": {
        "route": "autonomy_task_brief",
        "route_taken": "autonomy_task_brief",
    },
}


with app.test_request_context(
    "/api/chat",
    method="POST",
    json={
        "message": "hi",
        "session_id": "phase4g_test_session",
    },
):
    response = Response(
        json.dumps(payload),
        content_type="application/json",
    )

    fixed = _nova_phase4g_normal_chat_carryover_guard_20260701(response)

    body = fixed.get_json()

    text = str(
        body.get("assistant_message", {}).get("text")
        or body.get("text")
        or ""
    ).lower()

    require(
        "nova autonomy task brief" not in text,
        "autonomy bleed removed from greeting response",
    )

    require(
        "normal chat" in text,
        "normal chat recovery answer applied",
    )


print()
print("=" * 80)
print("NOVA PHASE4G NORMAL CHAT AUTONOMY CARRYOVER SMOKE PASSED")
print("=" * 80)