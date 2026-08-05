from nova_backend.services.tool_registry import ToolRegistry


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def run(self, tool_name, payload, confirm=False):
        self.calls.append(
            {
                "tool_name": tool_name,
                "payload": payload,
                "confirm": confirm,
            }
        )

        return {
            "ok": True,
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
    executor = FakeExecutor()
    registry = ToolRegistry(tool_executor=executor)

    available = registry.get_available_tools()

    assert_true(
        "available_tools",
        "chat.send" in available
        and "email.send" in available
        and "calendar.create" in available,
        available,
    )

    assert_true(
        "resolve_direct_name",
        registry.resolve_tool_name("session.rename")
        == "session.rename",
    )

    assert_true(
        "resolve_alias",
        registry.resolve_tool_name("rename")
        == "session.rename",
    )

    assert_true(
        "unknown_tool",
        registry.resolve_tool_name("missing.tool") == "",
    )

    assert_true(
        "confirmation_metadata",
        registry.requires_confirmation("email.send") is True
        and registry.requires_confirmation("chat.send") is False,
    )

    result = registry.execute(
        "rename",
        {
            "session_id": "session_test",
            "title": "Renamed",
        },
    )

    assert_true(
        "execute_alias",
        result.get("ok") is True
        and result.get("tool") == "session.rename",
        result,
    )

    result = registry.execute(
        "email",
        {
            "to": "person@example.com",
            "subject": "Test",
            "body": "Hello",
        },
        confirm=True,
    )

    assert_true(
        "execute_confirmation_forwarded",
        result.get("ok") is True
        and result.get("tool") == "email.send"
        and result.get("confirm") is True,
        result,
    )

    missing = registry.execute("missing.tool", {})

    assert_true(
        "execute_unknown_tool_safe",
        missing.get("ok") is False
        and "not registered" in missing.get("error", "").lower(),
        missing,
    )

    unconfigured = ToolRegistry().execute("chat", {})

    assert_true(
        "executor_not_configured_safe",
        unconfigured.get("ok") is False
        and "not configured" in unconfigured.get("error", "").lower(),
        unconfigured,
    )

    print()
    print("NOVA TOOL REGISTRY SMOKE PASSED")


if __name__ == "__main__":
    main()