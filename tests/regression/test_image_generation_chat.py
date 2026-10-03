import base64
from types import SimpleNamespace

from nova_backend.services.chat_service import ChatService
from nova_backend.services.image_generation_error_service import (
    image_generation_failure_message,
)


class _Sessions:
    def __init__(self):
        self.messages = []

    def append_message(self, session_id, message):
        self.messages.append((session_id, message))

    def get_session(self, session_id):
        return {"id": session_id}


class _Artifacts:
    def create(self, artifact):
        return {"id": "artifact-1", **artifact}


def _service(tmp_path):
    service = object.__new__(ChatService)
    service.image_model = "test-image-model"
    service.image_size = "1024x1024"
    service.uploads_dir = str(tmp_path)
    service.sessions = _Sessions()
    service.artifacts = _Artifacts()
    service._get_session_payload = lambda session_id: {"id": session_id}
    return service


def test_blocked_image_error_is_safe_and_persisted(tmp_path, monkeypatch, caplog):
    from nova_backend.services import model_gateway_service

    error = RuntimeError(
        'Error code: 400 - {"moderation_blocked":true,'
        '"safety_violations":["detail"],"request_id":"secret-request-id"}'
    )
    calls = []

    def blocked_generation(**kwargs):
        calls.append(kwargs)
        raise error

    monkeypatch.setattr(
        model_gateway_service, "images_generate_create", blocked_generation
    )
    service = _service(tmp_path)

    result = service._handle_image_generation("/image baby gangster", "session-1")

    visible = result["assistant_message"]["text"]
    assert result["ok"] is False
    assert visible == (
        "Nova couldn't generate that image because the request was blocked "
        "by the image safety system. Try changing the description and "
        "generate it again."
    )
    assert "moderation_blocked" not in visible
    assert "secret-request-id" not in visible
    assert "secret-request-id" in caplog.text
    assert calls == [{"model": "test-image-model", "prompt": "/image baby gangster", "size": "1024x1024"}]
    assert service.sessions.messages[0][1]["text"] == visible


def test_successful_image_output_and_metadata_survive_service_response(
    tmp_path, monkeypatch
):
    from nova_backend.services import model_gateway_service

    png_data = b"\x89PNG\r\n\x1a\nimage-data"
    encoded = base64.b64encode(png_data).decode("ascii")
    monkeypatch.setattr(
        model_gateway_service,
        "images_generate_create",
        lambda **kwargs: SimpleNamespace(
            data=[SimpleNamespace(b64_json=encoded, url=None)]
        ),
    )
    service = _service(tmp_path)

    result = service._handle_image_generation("sea house", "session-2")

    assistant = result["assistant_message"]
    assert result["ok"] is True
    assert result["image_url"].startswith("/api/uploads/generated_")
    assert assistant["image_url"] == result["image_url"]
    assert assistant["attachments"][0]["url"] == result["image_url"]
    assert assistant["meta"]["source"] == "image_generation"
    assert result["saved_artifact"]["image_url"] == result["image_url"]
    assert service.sessions.messages[0][1]["attachments"] == assistant["attachments"]


def test_provider_network_failure_is_humanized(tmp_path, monkeypatch):
    from nova_backend.services import model_gateway_service

    monkeypatch.setattr(
        model_gateway_service,
        "images_generate_create",
        lambda **kwargs: (_ for _ in ()).throw(ConnectionError("private endpoint")),
    )
    result = _service(tmp_path)._handle_image_generation("sea house", "session-3")

    assert result["assistant_message"]["text"] == (
        "Nova couldn't reach the image service right now. Please try again shortly."
    )
    assert "private endpoint" not in result["assistant_message"]["text"]


def test_image_failure_classifier_covers_rate_limit_auth_timeout_and_unknown():
    rate_limit = SimpleNamespace(status_code=429, code="rate_limit", body="")
    auth = SimpleNamespace(status_code=401, code="invalid_api_key", body="")
    timeout = TimeoutError("request timed out")
    unknown = RuntimeError("provider returned opaque failure")

    assert "too many requests" in image_generation_failure_message(rate_limit)
    assert "configuration needs attention" in image_generation_failure_message(auth)
    assert "timed out" in image_generation_failure_message(timeout)
    assert "opaque failure" not in image_generation_failure_message(unknown)
