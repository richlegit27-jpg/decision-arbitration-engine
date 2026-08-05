from nova_backend.services.tool_runtime_factory import (
    build_tool_runtime,
)


class FakeSessionService:
    def __init__(self):
        self.calls = []

    def rename_session(self, session_id, title):
        self.calls.append(
            {
                "action": "rename",
                "session_id": session_id,
                "title": title,
            }
        )

        return {
            "ok": True,
            "session_id": session_id,
            "title": title,
        }

    def pin_session(self, session_id, pinned=True):
        self.calls.append(
            {
                "action": "pin",
                "session_id": session_id,
                "pinned": pinned,
            }
        )

        return {
            "ok": True,
            "session_id": session_id,
            "pinned": pinned,
        }

    def delete_session(self, session_id):
        self.calls.append(
            {
                "action": "delete",
                "session_id": session_id,
            }
        )

        return {
            "ok": True,
            "session_id": session_id,
            "deleted": True,
        }


class FakeChatService:
    def __init__(self):
        self.calls = []

    def handle(
        self,
        user_text,
        session_id=None,
        attachments=None,
    ):
        self.calls.append(
            {
                "user_text": user_text,
                "session_id": session_id,
                "attachments": attachments or [],
            }
        )

        return {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": f"echo: {user_text}",
            },
            "session_id": session_id,
        }


class FakeAttachmentService:
    def __init__(self):
        self.calls = []

    def upload(self, file):
        self.calls.append(
            {
                "action": "upload",
                "file": file,
            }
        )

        return {
            "ok": True,
            "file": file,
        }

    def analyze(self, file_id):
        self.calls.append(
            {
                "action": "analyze",
                "file_id": file_id,
            }
        )

        return {
            "ok": True,
            "file_id": file_id,
            "analysis": "complete",
        }


def assert_true(name, condition, detail=None):
    if not condition:
        raise AssertionError(
            f"{name} FAILED"
            + (f" {detail}" if detail is not None else "")
        )

    print(f"PASS {name}")


def main():
    missing = build_tool_runtime()

    assert_true(
        "missing_dependencies_safe",
        missing.get("ok") is False
        and set(missing.get("missing_dependencies") or [])
        == {
            "session_service",
            "chat_service",
            "attachment_service",
        },
        missing,
    )

    session_service = FakeSessionService()
    chat_service = FakeChatService()
    attachment_service = FakeAttachmentService()

    runtime = build_tool_runtime(
        session_service=session_service,
        chat_service=chat_service,
        attachment_service=attachment_service,
    )

    assert_true(
        "runtime_builds",
        runtime.get("ok") is True
        and runtime.get("action_router") is not None
        and runtime.get("tool_executor") is not None
        and runtime.get("tool_registry") is not None
        and runtime.get("tool_bridge") is not None,
        runtime,
    )

    bridge = runtime["tool_bridge"]

    rename_result = bridge.auto_route(
        "rename",
        {
            "session_id": "session_test",
            "title": "Renamed",
        },
    )

    assert_true(
        "rename_full_chain",
        rename_result.get("ok") is True
        and rename_result.get("tool") == "session.rename"
        and rename_result.get("title") == "Renamed",
        rename_result,
    )

    chat_result = bridge.run_tool(
        "chat",
        {
            "text": "hello",
            "session_id": "session_test",
            "attachments": [],
        },
    )

    assert_true(
        "chat_alias_full_chain",
        chat_result.get("ok") is True
        and chat_result.get("tool") == "chat.send"
        and (
            chat_result.get("assistant_message") or {}
        ).get("text") == "echo: hello",
        chat_result,
    )

    analyze_result = bridge.auto_route(
        "analyze",
        {
            "file_id": "file_test",
        },
    )

    assert_true(
        "attachment_analyze_full_chain",
        analyze_result.get("ok") is True
        and analyze_result.get("tool") == "attachment.analyze"
        and analyze_result.get("analysis") == "complete",
        analyze_result,
    )

    confirmation = bridge.auto_route(
        "email",
        {
            "to": "person@example.com",
            "subject": "Test",
            "body": "Hello",
        },
    )

    assert_true(
        "planned_external_confirmation",
        confirmation.get("ok") is False
        and confirmation.get("requires_confirmation") is True,
        confirmation,
    )

    planned = bridge.auto_route(
        "email",
        {
            "to": "person@example.com",
            "subject": "Test",
            "body": "Hello",
        },
        confirm=True,
    )

    assert_true(
        "planned_external_not_implemented",
        planned.get("ok") is False
        and planned.get("implemented") is False,
        planned,
    )

    print()
    print("NOVA TOOL RUNTIME FACTORY SMOKE PASSED")


if __name__ == "__main__":
    main()