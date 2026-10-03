import json

from flask import Flask

from nova_backend.routes.tool_approval_routes import register_tool_approval_routes
from nova_backend.services.model_tool_runtime_service import (
    execute_structured_call,
    run_responses_tool_loop,
    should_offer_model_tools,
)
from nova_backend.services.provider_tool_schema import to_openai_responses_tools
from nova_backend.services.python_runner_service import PythonRunnerService
from nova_backend.services.tool_executor import ToolExecutor
from nova_backend.services.tool_registry import ToolRegistry as ModelToolRegistry
from nova_backend.tools.base import NovaTool
from nova_backend.tools.registry import ToolRegistry as ExecutableRegistry


class ReadFixture(NovaTool):
    name = "fixture_read"
    description = "Read a fixture value for tests."

    def run(self, key: str):
        return {"ok": True, "value": key}


class WriteFixture(NovaTool):
    name = "fixture_write"
    description = "Write a fixture value for tests."
    requires_confirmation = True

    def __init__(self):
        self.calls = []

    def run(self, value: str):
        self.calls.append(value)
        return {"ok": True, "value": value}


class UnimplementedFixture(NovaTool):
    name = "fixture_missing"
    description = "Not implemented."


class InvalidSchemaFixture(NovaTool):
    name = "fixture_invalid_schema"
    description = "Has an unsafe permissive schema."

    def run(self, key: str):
        return {"ok": True}

    def parameter_schema(self):
        return {"type": "object", "properties": {"key": {"type": "string"}}, "additionalProperties": True}


class FailingFixture(NovaTool):
    name = "fixture_failure"
    description = "Fail safely for tests."

    def run(self, key: str):
        raise RuntimeError("provider token-secret must not reach the model")


class ImplicitWriteFixture(NovaTool):
    name = "fixture_implicit_write"
    description = "Mutates state without a legacy confirmation flag."
    risk_level = "medium"

    def run(self, value: str):
        return {"ok": True, "value": value}


def _runtime(tmp_path, tools):
    executable = ExecutableRegistry()
    for tool in tools:
        executable.register(tool)
    executor = ToolExecutor(
        nova_tool_registry=executable,
        python_runner=PythonRunnerService(sandbox_dir=tmp_path / "sandbox"),
    )
    registry = ModelToolRegistry(tool_executor=executor, nova_tool_registry=executable)
    return registry, executor, executable


def test_model_discovery_exports_only_implemented_available_schema_tools(tmp_path):
    registry, _, _ = _runtime(tmp_path, [ReadFixture(), UnimplementedFixture(), InvalidSchemaFixture()])
    tools = registry.get_model_tool_definitions("chat")
    assert [tool["name"] for tool in tools] == ["fixture_read"]
    assert tools[0]["parameters"]["required"] == ["key"]
    assert "class" not in tools[0]
    assert "module" not in tools[0]
    assert "fixture_missing" not in registry.get_available_tools()
    assert "fixture_invalid_schema" not in registry.get_available_tools()


def test_blocked_command_tools_are_not_discovered(tmp_path):
    registry, _, executable = _runtime(tmp_path, [ReadFixture()])
    from nova_backend.tools.shell_command_tool import ShellCommandTool

    executable.register(ShellCommandTool())
    registry = ModelToolRegistry(tool_executor=registry.tool_executor, nova_tool_registry=executable)
    assert "shell_command" not in {tool["name"] for tool in registry.get_model_tool_definitions()}


def test_provider_schema_is_derived_from_canonical_definition(tmp_path):
    registry, _, _ = _runtime(tmp_path, [ReadFixture()])
    provider_tool = to_openai_responses_tools(registry.get_model_tool_definitions())[0]
    assert provider_tool["type"] == "function"
    assert provider_tool["name"] == "fixture_read"
    assert provider_tool["parameters"]["required"] == ["key"]


def test_schema_validation_rejects_missing_wrong_and_unknown_arguments(tmp_path):
    registry, executor, _ = _runtime(tmp_path, [ReadFixture()])
    for arguments in ({}, {"key": 3}, {"key": "x", "extra": True}):
        result = execute_structured_call(
            {"tool_name": "fixture_read", "arguments": arguments, "call_id": "c"},
            registry=registry,
            executor=executor,
            surface="chat",
            session_id="s",
            owner_id="u",
        )
        assert result["ok"] is False
        assert result["error_category"] == "invalid_tool_input"


def test_unknown_and_unavailable_tools_fail_safely(tmp_path):
    registry, executor, _ = _runtime(tmp_path, [ReadFixture()])
    result = execute_structured_call(
        {"tool_name": "fixture_missing", "arguments": {}, "call_id": "c"},
        registry=registry,
        executor=executor,
        surface="chat",
        session_id="s",
        owner_id="u",
    )
    assert result["status"] == "unavailable"


def test_read_only_structured_tool_executes_and_returns_envelope(tmp_path):
    registry, executor, _ = _runtime(tmp_path, [ReadFixture()])
    result = execute_structured_call(
        {"tool_name": "fixture_read", "arguments": '{"key":"value"}', "call_id": "c"},
        registry=registry,
        executor=executor,
        surface="chat",
        session_id="s",
        owner_id="u",
    )
    assert result["ok"] is True
    assert result["data"]["value"] == "value"
    assert result["retryable"] is False


def test_tool_failure_has_a_safe_structured_result(tmp_path):
    registry, executor, _ = _runtime(tmp_path, [FailingFixture()])
    result = execute_structured_call(
        {"tool_name": "fixture_failure", "arguments": {"key": "value"}, "call_id": "c"},
        registry=registry,
        executor=executor,
        surface="chat",
        session_id="s",
        owner_id="u",
    )
    assert result["ok"] is False
    assert result["error_category"] == "tool_failed"
    assert "token-secret" not in json.dumps(result)


def test_write_risk_requires_approval_even_without_legacy_flag(tmp_path):
    registry, executor, _ = _runtime(tmp_path, [ImplicitWriteFixture()])
    result = executor.run("fixture_implicit_write", {"value": "x"})
    assert result["status"] == "approval_required"
    assert registry.get_tool("fixture_implicit_write")["requires_approval"] is True


def test_approval_required_call_is_not_executed_before_owner_scoped_approval(tmp_path):
    writer = WriteFixture()
    registry, executor, _ = _runtime(tmp_path, [writer])
    from nova_backend.tools.pending_tool_approval_service import PendingToolApprovalService
    import nova_backend.services.model_tool_runtime_service as runtime

    original_pending = runtime.pending_tool_approval_service
    pending = PendingToolApprovalService()
    runtime.pending_tool_approval_service = pending
    try:
        result = execute_structured_call(
            {"tool_name": "fixture_write", "arguments": {"value": "safe"}, "call_id": "c"},
            registry=registry,
            executor=executor,
            surface="chat",
            session_id="s",
            owner_id="owner-a",
        )
        assert result["status"] == "approval_required"
        assert writer.calls == []
        assert pending.get_pending("s", owner_id="owner-b") is None
        approved = pending.approve("s", owner_id="owner-a")
        assert approved["ok"] is True
        execution = executor.run("fixture_write", approved["pending"]["payload"], confirm=True)
        assert execution["ok"] is True
        assert writer.calls == ["safe"]
        denied_call = execute_structured_call(
            {"tool_name": "fixture_write", "arguments": {"value": "denied"}, "call_id": "c2"},
            registry=registry,
            executor=executor,
            surface="chat",
            session_id="s2",
            owner_id="owner-a",
        )
        assert denied_call["status"] == "approval_required"
        assert pending.deny("s2", owner_id="owner-a")["ok"] is True
        assert writer.calls == ["safe"]
    finally:
        runtime.pending_tool_approval_service = original_pending


def test_tool_loop_does_not_execute_mutations_before_approval(tmp_path):
    writer = WriteFixture()
    registry, executor, _ = _runtime(tmp_path, [writer])
    calls = 0

    class Response:
        def __init__(self, response_id, outputs):
            self.id = response_id
            self.output = outputs

    def function_call(call_id):
        return {"type": "function_call", "name": "fixture_write", "arguments": '{"value":"x"}', "call_id": call_id}

    def model_call(outputs, previous_id):
        nonlocal calls
        calls += 1
        return Response(f"r{calls + 1}", [function_call(f"call-{calls + 1}")])

    result = run_responses_tool_loop(
        first_response=Response("r1", [function_call("call-1")]),
        model_call=model_call,
        registry=registry,
        executor=executor,
        text_extractor=lambda response: "final",
        surface="chat",
        session_id="s",
        owner_id="u",
        max_rounds=3,
        max_calls=5,
    )
    assert calls == 0
    assert writer.calls == []
    assert result["status"] == "approval_required"


def test_tool_loop_has_a_bounded_number_of_model_rounds(tmp_path):
    registry, executor, _ = _runtime(tmp_path, [ReadFixture()])

    class Response:
        def __init__(self, response_id, outputs):
            self.id = response_id
            self.output = outputs

    rounds = []

    def function_call(call_id):
        return {"type": "function_call", "name": "fixture_read", "arguments": '{"key":"x"}', "call_id": call_id}

    def model_call(outputs, previous_id):
        rounds.append(previous_id)
        return Response(f"r{len(rounds) + 1}", [function_call(f"read-{len(rounds) + 1}")])

    result = run_responses_tool_loop(
        first_response=Response("r1", [function_call("read-1")]),
        model_call=model_call,
        registry=registry,
        executor=executor,
        text_extractor=lambda response: "final",
        surface="chat",
        session_id="s",
        owner_id="u",
        max_rounds=2,
        max_calls=5,
    )
    assert len(rounds) == 2
    assert result["status"] == "limit_reached"


def test_normal_chat_tool_gate_avoids_trivial_catalog_and_accepts_routed_intent():
    assert should_offer_model_tools("Hello, how are you?") is False
    assert should_offer_model_tools("What is the weather?") is False
    assert should_offer_model_tools("anything", {"tool_use": True}) is True
    assert should_offer_model_tools("Please list files") is True


def test_no_tool_calls_returns_normal_model_response(tmp_path):
    registry, executor, _ = _runtime(tmp_path, [ReadFixture()])

    class Response:
        id = "response-final"
        output = [{"type": "message", "content": [{"type": "output_text", "text": "Normal answer."}]}]

    result = run_responses_tool_loop(
        first_response=Response(),
        model_call=lambda *_: (_ for _ in ()).throw(AssertionError("unexpected continuation")),
        registry=registry,
        executor=executor,
        text_extractor=lambda response: "Normal answer.",
        surface="chat",
        session_id="s",
        owner_id="u",
    )
    assert result["status"] == "completed"
    assert result["text"] == "Normal answer."


def test_tool_discovery_api_requires_auth_and_returns_only_safe_metadata(tmp_path):
    app = Flask(__name__)
    app.secret_key = "test"
    registry, _, _ = _runtime(tmp_path, [ReadFixture()])

    class Chat:
        tool_registry = registry

    register_tool_approval_routes(app, Chat())
    client = app.test_client()
    assert client.get("/api/tools").status_code == 401
    with client.session_transaction() as browser_session:
        browser_session["nova_user_id"] = "user-a"
    response = client.get("/api/tools")
    assert response.status_code == 200
    tool = response.get_json()["tools"][0]
    assert "class" not in tool and "module" not in tool
