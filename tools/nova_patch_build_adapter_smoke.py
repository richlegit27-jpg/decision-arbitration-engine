from __future__ import annotations

from nova_backend.services.patch_build_adapter import (
    build_patch_build_response,
    extract_patch_build_input,
)


class FakeSessionService:
    def __init__(self):
        self.active_session_id = "active_patch_build_adapter_smoke"
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
        "extract patch-build prefix",
        extract_patch_build_input("patch-build: improve mobile session restore") == "improve mobile session restore",
    )
    assert_true(
        "extract patch build prefix",
        extract_patch_build_input("patch build: improve memory recall") == "improve memory recall",
    )
    assert_true(
        "ignore normal chat",
        extract_patch_build_input("hello nova") is None,
    )

    session_service = FakeSessionService()

    response = build_patch_build_response(
        {
            "message": "patch-build: improve mobile session restore",
            "session_id": "patch_build_adapter_smoke",
        },
        session_service,
    )

    assert_true("adapter response exists", isinstance(response, dict))
    assert_true("adapter ok", response.get("ok") is True)
    assert_true("adapter session id", response.get("session_id") == "patch_build_adapter_smoke")

    debug = response.get("debug") or {}
    assert_true("adapter route", debug.get("route") == "patch_build_command", debug)
    assert_true("adapter mode", debug.get("mode") == "instructions_only", debug)
    assert_true("adapter marker", debug.get("adapter") == "patch_build_adapter", debug)

    assistant = response.get("assistant_message") or {}
    text = assistant.get("text") or assistant.get("content") or ""

    assert_true(
        "assistant meta route",
        (assistant.get("meta") or {}).get("route") == "patch_build_command",
    )
    assert_true(
        "assistant meta mode",
        (assistant.get("meta") or {}).get("mode") == "instructions_only",
    )

    assert_contains(
        "adapter patch-build response",
        text,
        [
            "Nova supervised patch build",
            "Goal:",
            "Mode: instructions_only",
            "Safety rules:",
            "Files to change:",
            "PowerShell patch steps:",
            "Compile checks:",
            "Smokes:",
            "Commit commands:",
            "Rollback commands:",
        ],
    )

    stored = session_service.get_session("patch_build_adapter_smoke")
    assert_true("session stored", isinstance(stored, dict))
    assert_true("session message count", len(stored.get("messages") or []) == 2)

    normal = build_patch_build_response({"message": "normal chat"}, session_service)
    assert_true("normal chat not hijacked", normal is None)

    print("NOVA PATCH BUILD ADAPTER SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
