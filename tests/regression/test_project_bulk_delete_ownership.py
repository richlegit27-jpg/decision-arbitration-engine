import json

import pytest
from flask import Flask, session

from nova_backend.services.project_workspace_service import ProjectWorkspaceService


@pytest.fixture
def workspace(tmp_path):
    service = ProjectWorkspaceService(data_dir=tmp_path)
    return service


def test_bulk_delete_removes_only_authenticated_owners_projects(workspace):
    app = Flask(__name__)
    app.secret_key = "test-key"

    with app.test_request_context("/"):
        session["nova_user_id"] = "user-a"
        own = workspace.create_project(title="A project")

    stored = json.loads(workspace.projects_file.read_text(encoding="utf-8-sig"))
    stored.append({"id": "project-b", "owner_id": "user-b", "title": "B project"})
    stored.append({"id": "legacy", "owner_id": "", "title": "Legacy project"})
    workspace._save_projects(stored)

    with app.test_request_context("/"):
        session["nova_user_id"] = "user-a"
        assert workspace.delete_all_projects() == 1
        assert workspace.list_projects() == []

    remaining = json.loads(workspace.projects_file.read_text(encoding="utf-8-sig"))
    assert {item["id"] for item in remaining} == {"project-b", "legacy"}
    assert own["id"] not in {item["id"] for item in remaining}


def test_bulk_delete_requires_authenticated_owner(workspace):
    app = Flask(__name__)
    app.secret_key = "test-key"

    with app.test_request_context("/"):
        with pytest.raises(PermissionError, match="Authentication required"):
            workspace.delete_all_projects()
