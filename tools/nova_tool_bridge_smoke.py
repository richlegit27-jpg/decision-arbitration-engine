from nova_backend.services.tool_bridge import ToolBridge


class FakeRegistry:
    def __init__(self):
        self.calls = []

    def execute(
        self,
        tool_name,
        payload=None,
        confirm=False,
    ):
        self.calls.append(
            {
                "tool_name": tool_name,
                "payload": payload,
                "confirm": confirm,
            }
        )

        return {
            "ok": True,
            "source": "registry",
            "tool": tool_name,
            "payload": payload,
            "confirm": confirm,
        }


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def run(
        self,
        tool_name,
        payload=None,
        confirm=False,
    ):
        self.calls.append(
            {
                "tool_name": tool_name,
                "payload": payload,
                "confirm": confirm,
            }
        )

        return {
            "ok": True,
            "source": "executor",
            "tool": tool_name,
            "payload": payload,
            "confirm": confirm,
        }


def assert_true(name, condition, detail=None):
    if not condition:
        raise AssertionError(
            f"{name} FAILED"
            + (f" {detail}" if detail is not None else "")
        )

    print(f"PASS {name}")


def main():
    registry = FakeRegistry()
    executor = FakeExecutor()

    bridge = ToolBridge(
        tool_registry=registry,
        tool_executor=executor,
    )

    result = bridge.run_tool(
        "email.send",
        {
            "to": "person@example.com",
        },
        confirm=True,
    )

    assert_true(
        "registry_first_delegation",
        result.get("ok") is True
        and result.get("source") == "registry"
        and result.get("confirm") is True,
        result,
    )

    assert_true(
        "executor_not_called_when_registry_exists",
        executor.calls == [],
        executor.calls,
    )

    executor_only = ToolBridge(
        tool_executor=executor,
    )

    result = executor_only.run_tool(
        "session.rename",
        {
            "session_id": "session_test",
            "title": "Renamed",
        },
    )

    assert_true(
        "executor_fallback",
        result.get("ok") is True
        and result.get("source") == "executor"
        and result.get("tool") == "session.rename",
        result,
    )

    result = bridge.auto_route(
        "rename",
        {
            "session_id": "session_test",
            "title": "Renamed Again",
        },
    )

    assert_true(
        "intent_mapping",
        result.get("ok") is True
        and result.get("tool") == "session.rename",
        result,
    )

    result = bridge.auto_route(
        "email",
        {
            "to": "person@example.com",
        },
        confirm=True,
    )

    assert_true(
        "confirmation_forwarded",
        result.get("ok") is True
        and result.get("confirm") is True,
        result,
    )

    missing_intent = bridge.auto_route(
        "missing_intent",
        {},
    )

    assert_true(
        "unknown_intent_safe",
        missing_intent.get("ok") is False
        and "no tool mapping" in missing_intent.get("error", "").lower(),
        missing_intent,
    )

    unconfigured = ToolBridge().run_tool(
        "chat.send",
        {},
    )

    assert_true(
        "unconfigured_bridge_safe",
        unconfigured.get("ok") is False
        and "not configured" in unconfigured.get("error", "").lower(),
        unconfigured,
    )

    print()
    print("NOVA TOOL BRIDGE SMOKE PASSED")


if __name__ == "__main__":
    main()