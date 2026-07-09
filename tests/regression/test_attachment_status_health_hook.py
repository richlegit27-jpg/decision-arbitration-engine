# NOVA_ATTACHMENT_STATUS_HEALTH_HOOK_TEST_20260705

import importlib

from nova_backend.services.attachment_pipeline_status import (
    get_attachment_pipeline_status,
)


def test_attachment_pipeline_status_service_returns_safe_flags():
    status = get_attachment_pipeline_status()

    assert "ready" in status
    assert status["debug_routes_require_env"] is True
    assert status["debug_env"] == "NOVA_DEBUG_ROUTES=1"

    pipeline = status["attachment_pipeline"]

    assert pipeline["upload_response_normalizer"] is True
    assert pipeline["payload_normalizer"] is True
    assert pipeline["hydrator"] is True
    assert pipeline["context_builder"] is True
    assert pipeline["intent_guard"] is True
    assert "web_guard" in pipeline

    text = str(status)

    assert "attachment_context_preview" not in text
    assert "extracted_text" not in text
    assert "attachment_summary" not in text


def test_api_health_includes_attachment_pipeline_flags():
    app_module = importlib.import_module("app")
    client = app_module.app.test_client()

    response = client.get("/api/health")

    assert response.status_code in {200, 503}

    data = response.get_json(silent=True) or {}

    assert "attachment_pipeline_ready" in data
    assert "attachment_pipeline" in data
    assert data["attachment_debug_routes_require_env"] is True

    pipeline = data["attachment_pipeline"]

    assert pipeline["upload_response_normalizer"] is True
    assert pipeline["payload_normalizer"] is True
    assert pipeline["hydrator"] is True
    assert pipeline["context_builder"] is True
    assert pipeline["intent_guard"] is True


def test_api_health_attachment_flags_do_not_expose_file_content():
    app_module = importlib.import_module("app")
    client = app_module.app.test_client()

    response = client.get("/api/health")
    text = response.get_data(as_text=True)

    assert "attachment_context_preview" not in text
    assert "extracted_text" not in text
    assert "attachment_summary" not in text
