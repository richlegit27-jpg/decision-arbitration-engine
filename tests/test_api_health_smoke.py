from __future__ import annotations

from fastapi.testclient import TestClient

from app import app


def test_api_health_endpoint_smoke() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200

    payload = response.json()

    assert isinstance(payload, dict)
    assert payload.get("ok") is True
