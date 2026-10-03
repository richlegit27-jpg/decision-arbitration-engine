import ast
import logging
from pathlib import Path

import pytest
from flask import Flask
from flask import session

from nova_backend.routes.mission_routes import register_mission_routes
from nova_backend.routes.tool_approval_routes import register_tool_approval_routes
from nova_backend.services.tool_executor import ToolExecutor
from nova_backend.tools.file_write_tool import FileWriteTool
from nova_backend.tools.file_delete_tool import FileDeleteTool
from nova_backend.tools.pending_tool_approval_service import PendingToolApprovalService
from nova_backend.tools.registry import ToolRegistry
from nova_backend.services.web_service import WebService


def test_legacy_mission_api_is_retired_without_mutating_shared_state():
    app = Flask(__name__)
    app.secret_key = "test"
    calls = []
    class Orchestrator:
        def run_mission(self, payload):
            calls.append(payload)
            return {"ok": True}
    register_mission_routes(app, mission_orchestrator=Orchestrator())
    client = app.test_client()
    for method, path in (
        ("get", "/api/missions"),
        ("get", "/api/missions/m1"),
        ("post", "/api/missions/m1/start"),
        ("post", "/api/missions/m1/advance"),
        ("post", "/api/missions/m1/status"),
    ):
        response = getattr(client, method)(path, json={"status": "completed"})
        assert response.status_code == 410
        assert response.get_json()["error"] == "legacy_missions_disabled"
    with client.session_transaction() as browser_session:
        browser_session["nova_user_id"] = "user-b"
    cross_user = client.get("/api/missions/m1")
    assert cross_user.status_code == 410
    assert calls == []


def test_pending_tool_approval_is_owner_scoped():
    pending = PendingToolApprovalService()
    assert pending.set_pending("s1", {"tool": "file_write", "payload": {}}, owner_id="user-a")["ok"]
    assert pending.get_pending("s1", owner_id="user-b") is None
    assert pending.approve("s1", owner_id="user-b")["ok"] is False
    assert pending.get_pending("s1", owner_id="user-a") is not None
    assert pending.deny("s1", owner_id="user-a")["ok"] is True
    assert pending.get_pending("s1", owner_id="user-a") is None


def test_approval_routes_require_login_and_owned_session(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test"

    class Sessions:
        def get_session(self, session_id, user_id=""):
            return {"id": session_id} if session_id == "owned" and user_id == "user-a" else None

    class Chat:
        session_service = Sessions()

        def approve_pending_tool(self, **kwargs):
            return {"ok": True, "owner_id": kwargs["owner_id"]}

        def deny_pending_tool(self, **kwargs):
            return {"ok": True, "owner_id": kwargs["owner_id"]}

    register_tool_approval_routes(app, Chat())
    client = app.test_client()
    assert client.post("/api/tools/approve", json={"session_id": "owned"}).status_code == 401
    assert client.post("/api/tools/deny", json={"session_id": "owned"}).status_code == 401
    assert client.get("/api/tools/pending?session_id=owned").status_code == 401
    with client.session_transaction() as browser_session:
        browser_session["nova_user_id"] = "user-a"
    assert client.post("/api/tools/approve", json={"session_id": "other"}).status_code == 404
    response = client.post("/api/tools/approve", json={"session_id": "owned"})
    assert response.status_code == 200
    assert response.get_json()["owner_id"] == "user-a"
    assert client.post("/api/tools/deny", json={"session_id": "other"}).status_code == 404
    denied = client.post("/api/tools/deny", json={"session_id": "owned"})
    assert denied.status_code == 200
    assert denied.get_json()["owner_id"] == "user-a"
    pending = client.get("/api/tools/pending?session_id=owned")
    assert pending.status_code == 200
    assert pending.get_json()["pending"] is None


def test_tool_executor_requires_approval_and_blocks_paths_outside_sandbox(tmp_path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    registry = ToolRegistry()
    registry.register(FileWriteTool())
    executor = ToolExecutor(nova_tool_registry=registry, python_runner=__import__(
        "nova_backend.services.python_runner_service", fromlist=["PythonRunnerService"]
    ).PythonRunnerService(sandbox_dir=sandbox))

    blocked_approval = executor.run("file_write", {"path": "note.txt", "content": "safe"})
    assert blocked_approval["status"] == "approval_required"
    written = executor.run("file_write", {"path": "note.txt", "content": "safe"}, confirm=True)
    assert written["ok"] is True
    assert (sandbox / "note.txt").read_text(encoding="utf-8") == "safe"

    outside = executor.run("file_write", {"path": str(tmp_path / "outside.txt"), "content": "bad"}, confirm=True)
    assert outside["status"] == "blocked"
    assert not (tmp_path / "outside.txt").exists()
    traversal = executor.run("file_write", {"path": "../traversal.txt", "content": "bad"}, confirm=True)
    assert traversal["status"] == "blocked"
    assert not (tmp_path / "traversal.txt").exists()
    link = sandbox / "escape-link"
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except (OSError, NotImplementedError):
        link = None
    if link is not None:
        symlink_escape = executor.run("file_write", {"path": "escape-link/through-link.txt", "content": "bad"}, confirm=True)
        assert symlink_escape["status"] == "blocked"
        assert not (tmp_path / "through-link.txt").exists()
    terminal = executor.run("terminal_execute", {"command": "whoami"}, confirm=True)
    assert terminal["status"] == "blocked"
    python = executor.run("python_run", {"path": "ok.txt"}, confirm=True)
    assert python["status"] == "blocked"

    delete_registry = ToolRegistry()
    delete_registry.register(FileDeleteTool())
    delete_executor = ToolExecutor(nova_tool_registry=delete_registry, python_runner=executor.python_runner)
    target = sandbox / "remove.txt"
    target.write_text("keep until approved", encoding="utf-8")
    assert delete_executor.run("file_delete", {"path": "remove.txt"})["status"] == "approval_required"
    assert target.exists()
    assert delete_executor.run("file_delete", {"path": "remove.txt"}, confirm=True)["ok"] is True
    assert not target.exists()


def test_tool_execution_logs_do_not_include_arguments_or_file_contents(tmp_path, caplog):
    registry = ToolRegistry()
    registry.register(FileWriteTool())
    from nova_backend.services.python_runner_service import PythonRunnerService
    executor = ToolExecutor(nova_tool_registry=registry, python_runner=PythonRunnerService(sandbox_dir=tmp_path / "sandbox"))
    caplog.set_level(logging.INFO, logger="nova.tools")
    secret = "private file contents and token-secret-123"
    executor.run("file_write", {"path": "private.txt", "content": secret}, confirm=True)
    assert "tool execution started" in caplog.text
    assert "tool execution finished" in caplog.text
    assert "private file contents" not in caplog.text
    assert "token-secret-123" not in caplog.text


def test_tool_metadata_exposes_schema_and_risk_contract():
    metadata = FileWriteTool().get_metadata()
    assert metadata["implemented"] is True
    assert metadata["requires_approval"] is True
    assert metadata["risk_class"] == "WRITE"
    assert {"path", "content", "append"}.issubset(metadata["parameter_schema"]["properties"])
    assert metadata["parameter_schema"]["properties"]["append"]["type"] == "boolean"


def test_memory_tools_use_the_application_memory_service(monkeypatch):
    import sys
    from types import SimpleNamespace
    from nova_backend.tools.memory_read_tool import MemoryReadTool
    from nova_backend.tools.memory_tool import MemoryWriteTool
    from nova_backend.tools.memory_delete_tool import MemoryDeleteTool

    class CanonicalMemory:
        def all(self):
            return [{"id": "owned", "text": "project preference", "owner_id": "user-a"}]

        def add_memory(self, item):
            return {"ok": True, "owner_id": "user-a", **item}

        def delete_memory(self, memory_id):
            return memory_id == "owned"

    canonical = CanonicalMemory()
    monkeypatch.setitem(sys.modules, "app", SimpleNamespace(memory_service=canonical))
    assert MemoryReadTool().run(query="project")[0]["owner_id"] == "user-a"
    assert MemoryWriteTool().run(content="a preference")["owner_id"] == "user-a"
    assert MemoryDeleteTool().run(memory_id="owned")["ok"] is True


def test_memory_tools_share_real_owner_scoped_service(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from nova_backend.services.memory_service import MemoryService
    from nova_backend.tools.memory_read_tool import MemoryReadTool
    from nova_backend.tools.memory_tool import MemoryWriteTool
    from nova_backend.tools.memory_delete_tool import MemoryDeleteTool

    app = Flask("canonical_memory_tools")
    app.secret_key = "test"
    service = MemoryService(str(tmp_path / "memories.json"))
    monkeypatch.setitem(sys.modules, "app", SimpleNamespace(memory_service=service))
    with app.test_request_context("/"):
        session["nova_user_id"] = "user-a"
        written = MemoryWriteTool().run(content="A private preference")
        memory_id = written["item"]["id"] if "item" in written else written["id"]
        assert any(item.get("id") == memory_id for item in MemoryReadTool().run(query="preference"))
    with app.test_request_context("/"):
        session["nova_user_id"] = "user-b"
        assert all(item.get("id") != memory_id for item in MemoryReadTool().run(query="preference"))
        assert MemoryDeleteTool().run(memory_id=memory_id)["ok"] is False
    with app.test_request_context("/"):
        session["nova_user_id"] = "user-a"
        assert MemoryDeleteTool().run(memory_id=memory_id)["ok"] is True


def test_web_fetch_rejects_non_public_addresses_and_redirects(monkeypatch):
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 80))])
    with pytest.raises(ValueError):
        WebService._validate_public_fetch_url("http://example.test/")
    for url in ("http://127.0.0.1/", "http://10.1.2.3/", "http://169.254.1.2/", "file:///etc/passwd"):
        with pytest.raises(ValueError):
            WebService._validate_public_fetch_url(url)

    service = WebService()
    calls = []

    class Response:
        status_code = 302
        headers = {"Location": "http://127.0.0.1/private"}
        url = "https://public.example/"
        text = ""

        def close(self):
            pass

        def raise_for_status(self):
            pass

    monkeypatch.setattr(service, "_validate_public_fetch_url", lambda url: (_ for _ in ()).throw(ValueError("private blocked")) if "127.0.0.1" in url else None)
    monkeypatch.setattr("nova_backend.services.web_service.requests.get", lambda *args, **kwargs: calls.append(args[0]) or Response())
    result = service.fetch("https://public.example/")
    assert result["ok"] is False
    assert result["error"] == "web_fetch_failed"
    assert calls == ["https://public.example/"]


def test_public_web_fetch_uses_mocked_network_and_reports_failure_truthfully(monkeypatch):
    import socket
    import requests

    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))])
    service = WebService()

    class Response:
        status_code = 200
        headers = {}
        url = "https://public.example/"
        text = "<html><title>Public page</title><body>Useful public content</body></html>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr("nova_backend.services.web_service.requests.get", lambda *args, **kwargs: Response())
    assert service.fetch("https://public.example/")["ok"] is True

    failed = WebService()
    monkeypatch.setattr("nova_backend.services.web_service.requests.get", lambda *args, **kwargs: (_ for _ in ()).throw(requests.ConnectionError("secret host details")))
    result = failed.fetch("https://public.example/failure")
    assert result["ok"] is False
    assert result["error"] == "web_fetch_failed"
    assert "secret host details" not in str(result)


def test_tool_registry_rejects_duplicate_names_and_hides_unimplemented_tools():
    from nova_backend.services.tool_registry import ToolRegistry as UnifiedRegistry

    registry = ToolRegistry()
    registry.register(FileWriteTool())
    with pytest.raises(ValueError):
        class DuplicateWrite(FileWriteTool):
            name = "file_write"
        registry.register(DuplicateWrite())

    unified = UnifiedRegistry(nova_tool_registry=registry)
    assert "file_write" in unified.get_available_tools()
    assert "email.send" not in unified.get_available_tools()
    assert "calendar.create" not in unified.get_available_tools()
    metadata = unified.get_tool("file_write")
    assert metadata["implemented"] is True
    assert metadata["parameter_schema"]["type"] == "object"
    assert metadata["risk_class"] == "WRITE"


def test_pending_approvals_do_not_survive_service_restart():
    first = PendingToolApprovalService()
    first.set_pending("s", {"tool": "file_write"}, owner_id="a")
    second = PendingToolApprovalService()
    assert second.get_pending("s", owner_id="a") is None


def test_production_web_fetch_route_requires_server_authentication():
    root = Path(__file__).resolve().parents[2]
    tree = ast.parse((root / "app.py").read_text(encoding="utf-8-sig"))
    route = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "api_web_fetch")
    source_calls = [node for node in ast.walk(route) if isinstance(node, ast.Call)]
    assert any(isinstance(call.func, ast.Name) and call.func.id == "get_current_user_id" for call in source_calls)
    assert any(isinstance(call.func, ast.Name) and call.func.id == "jsonify" for call in source_calls)


def test_web_fetch_route_rejects_anonymous_and_propagates_fetch_failure(monkeypatch):
    import app as nova_app

    calls = []
    monkeypatch.setattr(nova_app.web_service, "fetch", lambda url: calls.append(url) or {"ok": False, "error": "web_fetch_failed"})
    client = nova_app.app.test_client()
    anonymous = client.post("/api/web/fetch", json={"url": "https://public.example/"})
    assert anonymous.status_code == 401
    assert anonymous.get_json()["ok"] is False
    assert calls == []

    with client.session_transaction() as browser_session:
        browser_session["nova_user_id"] = "user-a"
    failed = client.post("/api/web/fetch", json={"url": "https://public.example/"})
    assert failed.status_code == 502
    assert failed.get_json()["ok"] is False
    assert len(calls) == 1
