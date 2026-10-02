from nova_backend.services.auth_context import project_api_auth_required
import ast
from pathlib import Path
from flask import Flask, session
from nova_backend.services.project_workspace_service import ProjectWorkspaceService


ROOT = Path(__file__).resolve().parents[1]


def test_project_api_requires_authenticated_owner_for_project_routes():
    assert project_api_auth_required("/api/projects") is True
    assert project_api_auth_required("/api/projects/") is True
    assert project_api_auth_required("/api/projects/project-1/execution") is True
    assert project_api_auth_required("/api/projects/new", "user-1") is False
    assert project_api_auth_required("/api/projects/project-1", "user-1") is False


def test_project_auth_guard_does_not_block_unrelated_public_routes():
    assert project_api_auth_required("/") is False
    assert project_api_auth_required("/api/planner/plan") is False
    assert project_api_auth_required("/api/projects-archive") is False


def test_flask_app_installs_guard_for_project_api_requests():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8-sig"))
    guard = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "nova_project_api_auth_guard"
    )
    assert any(
        (
            isinstance(decorator, ast.Attribute)
            and decorator.attr == "before_request"
        )
        or (
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr == "before_request"
        )
        for decorator in guard.decorator_list
    )
    assert any(
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "project_api_auth_required"
        for call in ast.walk(guard)
    )


def test_ownerless_legacy_projects_are_not_exposed_to_authenticated_users():
    app = Flask("project_owner_scope_test")
    app.secret_key = "unit-test-session-key"
    service = ProjectWorkspaceService.__new__(ProjectWorkspaceService)
    with app.test_request_context("/"):
        session["nova_user_id"] = "user-a"
        assert service._same_project_owner({"owner_id": "user-a"}) is True
        assert service._same_project_owner({"owner_id": "user-b"}) is False
        assert service._same_project_owner({"owner_id": ""}) is False

    with app.test_request_context("/"):
        assert service._same_project_owner({"owner_id": ""}) is True
