import json

import pytest
import werkzeug
from flask import Flask, session

from nova_backend.services.memory_route_service import MemoryRouteService
from nova_backend.services.memory_service import MemoryService


@pytest.fixture
def memory_api(tmp_path, monkeypatch):
    # This repository pins Flask 2.2 while the available Werkzeug removed
    # __version__; Flask's test client still reads it during construction.
    monkeypatch.setattr(werkzeug, "__version__", "test", raising=False)
    app = Flask(__name__)
    app.secret_key = "test-memory-api-secret"
    service = MemoryService(str(tmp_path / "memory.json"))
    MemoryRouteService(service).install_routes(app)
    return app, service, tmp_path / "memory.json"


def _add_for(app, service, owner_id, text, **fields):
    with app.test_request_context():
        session["nova_user_id"] = owner_id
        return service.add_memory({"text": text, **fields})


def _as_user(client, owner_id):
    with client.session_transaction() as browser_session:
        browser_session["nova_user_id"] = owner_id


def _stored(path):
    return json.loads(path.read_text(encoding="utf-8"))["memory"]


def test_anonymous_memory_reads_and_mutations_are_rejected(memory_api):
    app, service, path = memory_api
    own = _add_for(app, service, "user-a", "A private fact")
    client = app.test_client()
    before = path.read_bytes()

    assert client.get("/api/memory").status_code == 401
    for endpoint, payload in (
        ("/api/memory/add", {"text": "anonymous write"}),
        ("/api/memory/update", {"id": own["id"], "text": "changed"}),
        ("/api/memory/delete", {"id": own["id"]}),
        ("/api/memory/pin", {"id": own["id"]}),
        ("/api/memory/clear", {}),
        ("/api/memory/cleanup", {}),
        ("/api/memory/promote", {}),
        ("/api/memory/cleanup-promote", {}),
    ):
        response = client.post(endpoint, json=payload)
        assert response.status_code == 401, (endpoint, response.get_json())

    assert path.read_bytes() == before


def test_authenticated_memory_list_is_owner_scoped_and_hides_legacy(memory_api):
    app, service, path = memory_api
    user_a = _add_for(app, service, "user-a", "A memory")
    _add_for(app, service, "user-b", "B memory")
    stored = _stored(path)
    stored.extend([
        {"id": "legacy-memory", "text": "unowned legacy", "fact_key": "old-fact"},
        {"id": "legacy-memory-duplicate", "text": "another old record", "fact_key": "old-fact"},
    ])
    path.write_text(json.dumps({"memory": stored}), encoding="utf-8")

    client_a = app.test_client()
    _as_user(client_a, "user-a")
    response = client_a.get("/api/memory")
    assert response.status_code == 200
    visible = response.get_json()["data"]["memory"]
    assert [item["id"] for item in visible] == [user_a["id"]]

    with app.test_request_context():
        session["nova_user_id"] = "user-a"
        assert service.get("legacy-memory") is None


def test_user_cannot_retrieve_update_or_delete_another_users_memory(memory_api):
    app, service, _path = memory_api
    user_b = _add_for(app, service, "user-b", "B private fact")
    client_a = app.test_client()
    _as_user(client_a, "user-a")

    assert all(
        item["id"] != user_b["id"]
        for item in client_a.get("/api/memory").get_json()["data"]["memory"]
    )
    update = client_a.post(
        "/api/memory/update",
        json={"id": user_b["id"], "text": "tampered", "user_id": "user-b"},
    )
    delete = client_a.post(
        "/api/memory/delete",
        json={"id": user_b["id"], "user_id": "user-b"},
    )
    pin = client_a.post(
        "/api/memory/pin",
        json={"id": user_b["id"], "pinned": True},
    )
    assert update.status_code == 404
    assert delete.status_code == 200
    assert delete.get_json()["data"]["deleted"] is False
    assert pin.status_code == 404

    with app.test_request_context():
        session["nova_user_id"] = "user-b"
        assert service.get(user_b["id"])["text"] == "B private fact"


def test_update_and_clear_preserve_other_owners_and_legacy_records(memory_api):
    app, service, path = memory_api
    user_a = _add_for(app, service, "user-a", "A original")
    user_b = _add_for(app, service, "user-b", "B preserved")
    stored = _stored(path)
    stored.extend([
        {"id": "legacy-memory", "text": "unowned legacy", "fact_key": "old-fact"},
        {"id": "legacy-memory-duplicate", "text": "another old record", "fact_key": "old-fact"},
    ])
    path.write_text(json.dumps({"memory": stored}), encoding="utf-8")

    client_a = app.test_client()
    _as_user(client_a, "user-a")
    updated = client_a.post(
        "/api/memory/update",
        json={"id": user_a["id"], "text": "A updated", "kind": "fact"},
    )
    assert updated.status_code == 200
    by_id = {item["id"]: item for item in _stored(path)}
    assert by_id[user_a["id"]]["text"] == "A updated"
    assert by_id[user_b["id"]]["text"] == "B preserved"
    assert by_id["legacy-memory"]["text"] == "unowned legacy"
    assert by_id["legacy-memory-duplicate"]["text"] == "another old record"

    cleared = client_a.post("/api/memory/clear", json={})
    assert cleared.status_code == 200
    by_id = {item["id"]: item for item in _stored(path)}
    assert user_a["id"] not in by_id
    assert by_id[user_b["id"]]["text"] == "B preserved"
    assert by_id["legacy-memory"]["text"] == "unowned legacy"
    assert by_id["legacy-memory-duplicate"]["text"] == "another old record"


def test_authenticated_owner_can_add_update_pin_and_delete_memory(memory_api):
    app, _service, _path = memory_api
    client = app.test_client()
    _as_user(client, "user-a")

    added = client.post(
        "/api/memory/add",
        json={"text": "A preference", "kind": "preference", "owner_id": "user-b"},
    )
    assert added.status_code == 200
    item = added.get_json()["data"]["item"]
    assert item["owner_id"] == "user-a"

    updated = client.post(
        "/api/memory/update",
        json={"id": item["id"], "text": "A corrected preference"},
    )
    assert updated.status_code == 200
    pinned = client.post("/api/memory/pin", json={"id": item["id"], "pinned": True})
    assert pinned.status_code == 200
    assert pinned.get_json()["data"]["item"]["pinned"] is True

    deleted = client.post("/api/memory/delete", json={"id": item["id"]})
    assert deleted.status_code == 200
    assert deleted.get_json()["data"]["deleted"] is True
    assert client.get("/api/memory").get_json()["data"]["memory"] == []


def test_service_mutations_require_authenticated_owner(memory_api):
    _app, service, _path = memory_api
    with pytest.raises(PermissionError):
        service.add_memory({"text": "anonymous"})
    with pytest.raises(PermissionError):
        service.delete_memory("some-memory")
    with pytest.raises(PermissionError):
        service.clear()
