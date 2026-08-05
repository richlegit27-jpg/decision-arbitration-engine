from nova_backend.services.tool_executor import ToolExecutor


class FakeActionRouter:
    def __init__(self):
        self.calls = []

    def execute(self, tool_name, payload):
        self.calls.append(
            {
                "tool_name": tool_name,
                "payload": payload,
            }
        )

        return {
            "ok": True,
            "action": tool_name,
            "payload": payload,
        }


def assert_true(name, condition, detail=None):
    if not condition:
        raise AssertionError(
            f"{name} FAILED"
            + (f" {detail}" if detail is not None else "")
        )

    print(f"PASS {name}")


def main():
    router = FakeActionRouter()
    executor = ToolExecutor(action_router=router)

    internal_result = executor.run(
        "session.rename",
        {
            "session_id": "session_test",
            "title": "Renamed",
        },
    )

    assert_true(
        "internal_tool_executes",
        internal_result.get("ok") is True
        and internal_result.get("tool") == "session.rename"
        and internal_result.get("action") == "session.rename",
        internal_result,
    )

    assert_true(
        "internal_router_called",
        len(router.calls) == 1
        and router.calls[0]["tool_name"] == "session.rename",
        router.calls,
    )

    missing_router = ToolExecutor().run(
        "session.rename",
        {
            "session_id": "session_test",
            "title": "Renamed",
        },
    )

    assert_true(
        "missing_router_safe",
        missing_router.get("ok") is False
        and "not configured" in missing_router.get("error", "").lower(),
        missing_router,
    )

    confirmation = executor.run(
        "email.send",
        {
            "to": "person@example.com",
            "subject": "Test",
            "body": "Hello",
        },
    )

    assert_true(
        "external_confirmation_required",
        confirmation.get("ok") is False
        and confirmation.get("requires_confirmation") is True,
        confirmation,
    )

    planned_tool = executor.run(
        "email.send",
        {
            "to": "person@example.com",
            "subject": "Test",
            "body": "Hello",
        },
        confirm=True,
    )

    assert_true(
        "planned_external_tool_safe",
        planned_tool.get("ok") is False
        and planned_tool.get("implemented") is False,
        planned_tool,
    )

    unknown = executor.run("missing.tool", {})

    assert_true(
        "unknown_tool_safe",
        unknown.get("ok") is False
        and "not registered" in unknown.get("error", "").lower(),
        unknown,
    )

    intent_result = executor.auto_decide_and_run(
        "rename",
        {
            "session_id": "session_test",
            "title": "Renamed Again",
        },
    )

    assert_true(
        "intent_mapping_executes",
        intent_result.get("ok") is True
        and intent_result.get("tool") == "session.rename",
        intent_result,
    )

    missing_intent = executor.auto_decide_and_run(
        "missing_intent",
        {},
    )

    assert_true(
        "unknown_intent_safe",
        missing_intent.get("ok") is False
        and "no tool mapped" in missing_intent.get("error", "").lower(),
        missing_intent,
    )

    print()
    print("NOVA TOOL EXECUTOR SMOKE PASSED")


if __name__ == "__main__":
    main()