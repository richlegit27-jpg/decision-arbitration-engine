from __future__ import annotations

from nova_backend.services.autonomy_plan_adapter import (
    build_autonomy_plan_response,
    extract_autonomy_plan_input,
)


class FakeSessionService:
    def __init__(self):
        self.active_session_id = "active_autonomy_plan_adapter_smoke"
        self.sessions = {}

    def add_message(self, session_id, message):
        self.sessions.setdefault(session_id, {"id": session_id, "messages": []})
        self.sessions[session_id]["messages"].append(message)

    def get_session(self, session_id):
        return self.sessions.get(session_id)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def assert_contains(name, text, needles):
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise AssertionError(f"{name} FAILED. Missing {missing}. Text was:\n{text}")
    print(f"PASS {name}")


def main():
    assert_true(
        "extract autonomy-plan prefix",
        extract_autonomy_plan_input("autonomy-plan: improve mobile session restore") == "improve mobile session restore",
    )
    assert_true(
        "extract autonomy plan prefix",
        extract_autonomy_plan_input("autonomy plan: improve memory recall") == "improve memory recall",
    )
    assert_true(
        "ignore normal chat",
        extract_autonomy_plan_input("hello nova") is None,
    )

    session_service = FakeSessionService()

    response = build_autonomy_plan_response(
        {
            "message": "autonomy-plan: improve mobile session restore",
            "session_id": "autonomy_plan_adapter_smoke",
        },
        session_service,
    )

    assert_true("adapter response exists", isinstance(response, dict))
    assert_true("adapter ok", response.get("ok") is True)
    assert_true("adapter session id", response.get("session_id") == "autonomy_plan_adapter_smoke")

    debug = response.get("debug") or {}
    assert_true("adapter route", debug.get("route") == "autonomy_plan_command", debug)
    assert_true("adapter debug mode", debug.get("mode") == "proposal_only", debug)
    assert_true("adapter marker", debug.get("adapter") == "autonomy_plan_adapter", debug)

    assistant = response.get("assistant_message") or {}
    text = assistant.get("text") or assistant.get("content") or ""

    assert_true(
        "assistant meta route",
        (assistant.get("meta") or {}).get("route") == "autonomy_plan_command",
    )
    assert_true(
        "assistant meta mode",
        (assistant.get("meta") or {}).get("mode") == "patch_proposal_only",
    )

    assert_contains(
        "adapter autonomy-plan response",
        text,
        [
            "Nova supervised patch proposal",
            "Goal:",
            "Mode: proposal_only",
            "Likely files:",
            "Risks:",
            "Smallest safe patch strategy:",
            "Tests:",
            "Rollback plan:",
        ],
    )

    stored = session_service.get_session("autonomy_plan_adapter_smoke")
    assert_true("session stored", isinstance(stored, dict))
    assert_true("session message count", len(stored.get("messages") or []) == 2)

    normal = build_autonomy_plan_response({"message": "normal chat"}, session_service)
    assert_true("normal chat not hijacked", normal is None)

    print("NOVA AUTONOMY PLAN ADAPTER SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
