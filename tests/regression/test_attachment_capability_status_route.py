# NOVA_ATTACHMENT_CAPABILITY_STATUS_ROUTE_TEST_20260705

import importlib


def test_attachment_status_route_returns_capability_flags():
    app_module = importlib.import_module("app")
    client = app_module.app.test_client()

    response = client.get("/api/attachment/status")

    assert response.status_code == 200

    data = response.get_json(silent=True) or {}

    assert data["ok"] is True
    assert "ready" in data
    assert data["debug_routes_require_env"] is True
    assert data["debug_env"] == "NOVA_DEBUG_ROUTES=1"

    pipeline = data["attachment_pipeline"]

    assert pipeline["upload_response_normalizer"] is True
    assert pipeline["payload_normalizer"] is True
    assert pipeline["hydrator"] is True
    assert pipeline["context_builder"] is True
    assert pipeline["intent_guard"] is True

    # Web guard may be false only on branches without ChatService web methods.
    assert "web_guard" in pipeline


def test_attachment_status_route_does_not_expose_file_contents():
    app_module = importlib.import_module("app")
    client = app_module.app.test_client()

    response = client.get("/api/attachment/status")
    text = response.get_data(as_text=True)

    assert "attachment_context_preview" not in text
    assert "extracted_text" not in text
    assert "attachment_summary" not in text
