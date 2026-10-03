from __future__ import annotations

import json
import io
import socket
import urllib.request

import pytest
from flask import Flask
from flask import session as flask_session

from nova_backend.services.chat.handle import chat_handle
from nova_backend.services.intent_service import IntentService
from nova_backend.services.planner.decision_service import DecisionService
from nova_backend.services.video_generation_service import (
    VideoGenerationError,
    VideoGenerationService,
    safe_video_error,
)
from nova_backend.services.luma_video_provider import LumaVideoProvider
from nova_backend.services.session_service import SessionService


class ImmediateExecutor:
    def submit(self, callback, *args):
        callback(*args)


class DeferredExecutor:
    def submit(self, callback, *args):
        self.callback = callback
        self.args = args

    def run(self):
        self.callback(*self.args)


class FakeProvider:
    name = "test-provider"

    def __init__(self, result=None, error=None):
        self.result = result or {
            "video_bytes": b"\x00\x00\x00\x10ftypisom\x00\x00\x02\x00",
            "mime_type": "video/mp4",
            "duration_seconds": 2,
            "resolution": "test",
        }
        self.error = error
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.result


class FakeArtifacts:
    def __init__(self):
        self.items = []

    def save_artifact(self, item, owner_id=None):
        result = {**item, "id": f"artifact-{len(self.items) + 1}", "owner_id": owner_id}
        self.items.append(result)
        return result


class FailingArtifacts:
    def save_artifact(self, item, owner_id=None):
        raise OSError("disk failure with internal path")


class FakeSessions:
    def __init__(self):
        self.messages = {}

    def replace_message(self, session_id, message_id, message, user_id=""):
        self.messages[(user_id, session_id, message_id)] = dict(message)
        return dict(message)


class FakeUploadOwnership:
    def __init__(self, mapping=None):
        self.mapping = mapping or {}

    def belongs_to_user(self, filename, owner_id):
        return self.mapping.get(filename) == owner_id


class OwnedSessionLookup:
    def get_session(self, session_id, user_id=""):
        if session_id == "session-a" and user_id == "user-a":
            return {"id": session_id}
        return None


class AsyncFakeProvider:
    name = "luma"

    def __init__(self):
        self.submissions = []
        self.polls = 0

    def submit_generation(self, prompt, **kwargs):
        self.submissions.append((prompt, kwargs))
        return {"id": "provider-job-1", "state": "queued"}

    def get_generation(self, generation_id):
        self.polls += 1
        if self.polls == 1:
            return {"id": generation_id, "state": "processing"}
        return {"id": generation_id, "state": "completed", "output": [{"type": "video", "url": "https://storage.cdn-luma.com/video.mp4"}]}

    def download_video(self, url, *, max_bytes):
        assert url == "https://storage.cdn-luma.com/video.mp4"
        assert max_bytes > 0
        return b"\x00\x00\x00\x10ftypisom\x00\x00\x02\x00", "video/mp4"


class AsyncFailProvider(AsyncFakeProvider):
    def get_generation(self, generation_id):
        self.polls += 1
        return {
            "id": generation_id, "state": "failed",
            "failure_code": "content_moderated", "failure_reason": "Request blocked by safety review",
        }


class BudgetSubmitProvider(AsyncFakeProvider):
    def submit_generation(self, prompt, **kwargs):
        self.submissions.append((prompt, kwargs))
        raise VideoGenerationError("budget_exhausted", "RATE_LIMIT.BUDGET.EXCEEDED: Not enough credits to continue.")


def make_service(tmp_path, provider=None):
    artifacts = FakeArtifacts()
    sessions = FakeSessions()
    service = VideoGenerationService(
        tmp_path / "jobs.json",
        tmp_path / "uploads",
        provider=provider,
        artifact_service=artifacts,
        session_service=sessions,
        executor=ImmediateExecutor(),
    )
    return service, artifacts, sessions


def create(service, owner="user-a", session="session-a", message="message-a", project="project-a"):
    return service.create_job(
        prompt="A small cabin beside a lake",
        owner_id=owner,
        session_id=session,
        assistant_message_id=message,
        project_id=project,
    )


def test_video_command_is_explicit_and_does_not_trigger_from_discussion():
    intent = IntentService()
    assert intent.detect("/video a cabin at sunset")["route"] == "video_generation"
    assert intent.detect("How does video generation work?")["route"] != "video_generation"
    assert intent.detect("/video")["route"] == "video_generation"
    decision_service = DecisionService(type("Chat", (), {"_load_execution_state": lambda self, _sid: {}})())
    assert decision_service._decide_route("/video a cabin", session_id="s")["route"] == "video_generation"
    assert decision_service._decide_route("we should continue the project", session_id="s")["route"] != "video_generation"


def test_chat_command_to_completed_video_dogfood_uses_persisted_conversation(tmp_path):
    app = Flask(__name__)
    app.secret_key = "test-only"
    with app.test_request_context("/api/chat", method="POST"):
        flask_session["nova_user_id"] = "user-a"
        sessions = SessionService(tmp_path / "sessions.json")
        chat_session = sessions.create_session(user_id="user-a")
        artifacts = FakeArtifacts()
        provider = FakeProvider()
        video = VideoGenerationService(
            tmp_path / "jobs.json", tmp_path / "uploads", provider=provider,
            artifact_service=artifacts, session_service=sessions, executor=ImmediateExecutor(),
        )

        class ChatHarness:
            video_generation_service = video
            project_workspace_service = type(
                "ProjectContext", (), {"get_active_project": lambda self: {"id": "project-a"}}
            )()

            @staticmethod
            def safe_str(value):
                return str(value or "")

            @staticmethod
            def _build_user_message(text, attachments=None):
                return {"role": "user", "text": text, "attachments": attachments or []}

            @staticmethod
            def _build_assistant_message(text, meta=None):
                return {"role": "assistant", "text": text, "content": text, "meta": meta or {}}

            def _finalize_response(self, *, session_id, user_msg, assistant_msg, **kwargs):
                sessions.append_message(session_id, user_msg, user_id="user-a")
                sessions.append_message(session_id, assistant_msg, user_id="user-a")
                return {"ok": True, "session_id": session_id, "assistant_message": assistant_msg}

        decision = DecisionService(type("Chat", (), {"_load_execution_state": lambda self, _sid: {}})())._decide_route(
            "/video a small cabin beside a lake", session_id=chat_session["id"]
        )
        response = chat_handle(
            ChatHarness(),
            user_text="/video a small cabin beside a lake",
            session_id=chat_session["id"],
            decision=decision,
        )
        job_id = response["video_job"]["id"]
        assert response["assistant_message"]["meta"]["video_status"] == "queued"

        finished = video.get_job(job_id, "user-a")
        assert finished["status"] == "completed"
        assert finished["artifact_id"]
        persisted = sessions.get_session(chat_session["id"])
        assistant = next(message for message in persisted["messages"] if message.get("id") == response["assistant_message"]["id"])
        assert assistant["meta"]["video_status"] == "completed"
        assert assistant["attachments"][0]["url"].endswith("/content")
        assert artifacts.items[0]["session_id"] == chat_session["id"]
        assert artifacts.items[0]["owner_id"] == "user-a"
        assert artifacts.items[0]["project_id"] == "project-a"


def test_mocked_generation_completes_persists_artifact_and_session(tmp_path):
    provider = FakeProvider()
    service, artifacts, sessions = make_service(tmp_path, provider)
    job = create(service)

    assert job["status"] == "queued"
    complete = service.get_job(job["id"], "user-a")
    assert complete["status"] == "completed"
    assert complete["duration_seconds"] == 2
    assert complete["artifact_id"] == "artifact-1"
    assert artifacts.items[0]["owner_id"] == "user-a"
    assert artifacts.items[0]["project_id"] == "project-a"
    message = sessions.messages[("user-a", "session-a", "message-a")]
    assert message["attachments"][0]["url"].endswith("/content")
    assert message["meta"]["video_status"] == "completed"

    reloaded = VideoGenerationService(
        tmp_path / "jobs.json", tmp_path / "uploads", provider=provider,
        artifact_service=artifacts, session_service=sessions, executor=ImmediateExecutor(),
    )
    assert reloaded.get_job(job["id"], "user-a")["status"] == "completed"
    assert len(artifacts.items) == 1
    path = reloaded.content_path(job["id"], "user-a")
    assert path and path.read_bytes().startswith(b"\x00\x00\x00\x10ftyp")


def test_job_exposes_queued_then_generating_then_completed(tmp_path):
    provider = FakeProvider()
    executor = DeferredExecutor()
    service = VideoGenerationService(
        tmp_path / "jobs.json", tmp_path / "uploads", provider=provider,
        artifact_service=FakeArtifacts(), executor=executor,
    )
    provider.service = service
    original_generate = provider.generate

    def inspect_generating(prompt):
        active = service._find(next(iter(service._read()["jobs"]))["id"])
        assert active["status"] == "generating"
        return original_generate(prompt)

    provider.generate = inspect_generating
    job = create(service)
    assert job["status"] == "queued"
    executor.run()
    assert service.get_job(job["id"], "user-a")["status"] == "completed"


def test_job_and_video_content_are_owner_scoped(tmp_path):
    service, _, _ = make_service(tmp_path, FakeProvider())
    job = create(service)
    assert service.get_job(job["id"], "user-b") is None
    assert service.content_path(job["id"], "user-b") is None
    assert service.content_path(job["id"], "") is None


def test_provider_safety_failure_is_safe_and_creates_no_artifact(tmp_path):
    service, artifacts, sessions = make_service(
        tmp_path, FakeProvider(error=VideoGenerationError("safety", "raw moderation JSON secret"))
    )
    job = create(service)
    failed = service.get_job(job["id"], "user-a")
    assert failed["status"] == "failed"
    assert failed["error_category"] == "safety_rejected"
    assert "safety system" in failed["user_error"]
    assert "raw moderation JSON" not in failed["user_error"]
    assert artifacts.items == []
    persisted = sessions.messages[("user-a", "session-a", "message-a")]
    assert "raw moderation JSON" not in persisted["text"]


def test_invalid_output_fails_without_artifact_or_path(tmp_path):
    service, artifacts, _ = make_service(
        tmp_path,
        FakeProvider(result={"video_bytes": b"not mp4", "mime_type": "video/mp4"}),
    )
    job = create(service)
    failed = service.get_job(job["id"], "user-a")
    assert failed["status"] == "failed"
    assert failed["error_category"] == "generation_failed"
    assert service.content_path(job["id"], "user-a") is None
    assert artifacts.items == []


def test_artifact_storage_failure_is_reported_as_failure_and_output_removed(tmp_path):
    service = VideoGenerationService(
        tmp_path / "jobs.json", tmp_path / "uploads", provider=FakeProvider(),
        artifact_service=FailingArtifacts(), executor=ImmediateExecutor(),
    )
    job = create(service)
    result = service.get_job(job["id"], "user-a")
    assert result["status"] == "failed"
    assert result["error_category"] == "storage_failure"
    assert result["assistant_message"]["text"].startswith("Nova generated the video but couldn't save it")
    assert "disk failure" not in result["assistant_message"]["text"]
    assert service.content_path(job["id"], "user-a") is None


def test_no_provider_reports_configuration_required_without_fake_success(tmp_path):
    service, artifacts, _ = make_service(tmp_path, None)
    job = create(service)
    assert job["status"] == "failed"
    assert job["error_category"] == "provider_configuration_required"
    assert "provider must be configured" in job["user_error"]
    assert artifacts.items == []


@pytest.mark.parametrize(
    ("error", "category"),
    [
        (ConnectionError("socket closed"), "provider_unavailable"),
        (TimeoutError("request timed out"), "timeout"),
        (VideoGenerationError("rate_limit", "429"), "rate_limited"),
        (VideoGenerationError("authentication", "key invalid"), "provider_configuration"),
    ],
)
def test_provider_error_categories_are_humanized(error, category):
    actual_category, message = safe_video_error(error)
    assert actual_category == category
    assert message
    assert "429" not in message
    assert "socket closed" not in message


def test_restart_marks_unfinished_jobs_interrupted_instead_of_retrying(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps({"jobs": [{
        "id": "video_pending", "owner_id": "user-a", "status": "generating"
    }]}), encoding="utf-8")
    service = VideoGenerationService(jobs_file, tmp_path / "uploads", provider=FakeProvider())
    job = service.get_job("video_pending", "user-a")
    assert job["status"] == "failed"
    assert job["error_category"] == "interrupted"
    assert "restarted" in job["user_error"]


def test_status_and_content_routes_require_owner(tmp_path):
    service, _, _ = make_service(tmp_path, FakeProvider())
    job = create(service)
    app = Flask(__name__)
    app.secret_key = "test-only"
    service.install_routes(app)
    client = app.test_client()

    assert client.get(f"/api/video/jobs/{job['id']}").status_code == 401
    with client.session_transaction() as session:
        session["nova_user_id"] = "user-b"
    assert client.get(f"/api/video/jobs/{job['id']}").status_code == 404
    with client.session_transaction() as session:
        session["nova_user_id"] = "user-a"
    assert client.get(f"/api/video/jobs/{job['id']}").status_code == 200
    content = client.get(f"/api/video/jobs/{job['id']}/content")
    assert content.status_code == 200
    assert content.mimetype == "video/mp4"


class MockHTTPResponse:
    def __init__(self, payload, status=201, content_type="application/json"):
        self.payload = payload
        self.status = status
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        return self.payload if size < 0 else self.payload[:size]


def test_luma_adapter_requires_key_and_maps_text_request():
    missing = LumaVideoProvider(api_key="")
    with pytest.raises(VideoGenerationError) as error:
        missing.submit_generation("a cabin")
    assert error.value.category == "configuration"

    seen = {}

    def opener(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return MockHTTPResponse(b'{"id":"182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e","state":"queued"}')

    provider = LumaVideoProvider(api_key="test-key", opener=opener)
    result = provider.submit_generation("A cabin", model="ray-3.2", aspect_ratio="9:16")
    assert result["id"] == "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"
    assert seen["request"].full_url.endswith("/v1/generations")
    assert seen["request"].get_header("Authorization") == "Bearer test-key"
    payload = json.loads(seen["request"].data.decode("utf-8"))
    assert payload == {
        "prompt": "A cabin", "model": "ray-3.2", "type": "video", "aspect_ratio": "9:16",
        "video": {"resolution": "720p", "duration": "5s"},
    }
    with pytest.raises(VideoGenerationError) as unsupported:
        provider.submit_generation("A cabin", model="ray-2")
    assert unsupported.value.category == "invalid_input"


def test_luma_adapter_maps_image_keyframe_and_rejects_untrusted_reference():
    seen = {}

    def opener(request, timeout):
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return MockHTTPResponse(b'{"id":"182bd5e5-6e1a-4fe4-a799-aa6d9a6ab270"}')

    provider = LumaVideoProvider(api_key="test-key", opener=opener)
    provider.submit_generation("Animate this", image_url="https://nova.example/api/video/reference/x")
    assert seen["payload"]["video"]["start_frame"] == {
        "url": "https://nova.example/api/video/reference/x"
    }
    with pytest.raises(VideoGenerationError):
        provider.submit_generation("Animate this", image_url="http://127.0.0.1/private.png")


@pytest.mark.parametrize(
    ("status", "body", "category"),
    [
        (401, b'{"detail":"unauthorized"}', "authentication"),
        (429, b'{"detail":"rate limited"}', "rate_limit"),
        (402, b'{"detail":"RATE_LIMIT.BUDGET.EXCEEDED: Not enough credits to continue."}', "budget_exhausted"),
        (400, b'{"detail":"moderation blocked"}', "safety"),
    ],
)
def test_luma_http_errors_are_classified_without_provider_calls(status, body, category):
    from urllib.error import HTTPError

    def opener(request, timeout):
        raise HTTPError(request.full_url, status, "provider error", {}, io.BytesIO(body))

    provider = LumaVideoProvider(api_key="test-key", opener=opener)
    with pytest.raises(VideoGenerationError) as error:
        provider.submit_generation("A cabin")
    assert error.value.category == category


def test_luma_rejects_malformed_generation_response():
    provider = LumaVideoProvider(
        api_key="test-key",
        opener=lambda *_args, **_kwargs: MockHTTPResponse(b'{"state":"queued"}'),
    )
    with pytest.raises(VideoGenerationError) as error:
        provider.submit_generation("A cabin")
    assert error.value.category == "invalid_response"


def test_image_video_uses_owned_upload_signed_reference_and_durable_artifact(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    image = b"\x89PNG\r\n\x1a\n" + b"fake-png-data"
    (uploads / "owned.png").write_bytes(image)
    provider = AsyncFakeProvider()
    artifacts = FakeArtifacts()
    sessions = FakeSessions()
    waits = []
    service = VideoGenerationService(
        tmp_path / "jobs.json", uploads, provider=provider,
        artifact_service=artifacts, session_service=sessions,
        upload_ownership_service=FakeUploadOwnership({"owned.png": "user-a"}),
        reference_signing_key="test-secret-key", public_url="https://nova.example",
        executor=ImmediateExecutor(), poll_wait=waits.append,
    )
    job = service.create_job(
        prompt="Move the camera toward the house", owner_id="user-a", session_id="session-a",
        assistant_message_id="message-a", attachments=[{
            "file_url": "/api/uploads/owned.png", "filename": "owned.png", "mime_type": "image/png"
        }], model="ray-3.2",
    )
    completed = service.get_job(job["id"], "user-a")
    assert completed["status"] == "completed"
    assert completed["model"] == "ray-3.2"
    assert provider.polls == 2
    assert provider.submissions[0][1]["image_url"].startswith("https://nova.example/api/video/reference/")
    assert waits == [2.0]
    persisted = json.loads((tmp_path / "jobs.json").read_text(encoding="utf-8"))["jobs"][0]
    assert persisted["provider_job_id"] == "provider-job-1"
    assert persisted["source_image"] == {"filename": "owned.png", "mime_type": "image/png"}
    assert "signature=" not in json.dumps(persisted)
    assert artifacts.items[0]["meta"]["provider"] == "luma"
    assert artifacts.items[0]["meta"]["model"] == "ray-3.2"
    assert service.content_path(job["id"], "user-a").read_bytes().startswith(b"\x00\x00\x00\x10ftyp")

    app = Flask(__name__)
    app.secret_key = "test-only"
    service.install_routes(app)
    client = app.test_client()
    signed = provider.submissions[0][1]["image_url"]
    parsed = __import__("urllib.parse", fromlist=["urlsplit"]).urlsplit(signed)
    assert client.get(parsed.path + "?" + parsed.query).data == image
    assert client.get(parsed.path + "?expires=1&signature=bad").status_code == 404


def test_image_video_rejects_cross_user_upload_without_provider_call(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "other.png").write_bytes(b"\x89PNG\r\n\x1a\nopaque")
    provider = AsyncFakeProvider()
    service = VideoGenerationService(
        tmp_path / "jobs.json", uploads, provider=provider,
        upload_ownership_service=FakeUploadOwnership({"other.png": "user-b"}),
        reference_signing_key="test-secret-key", public_url="https://nova.example",
        executor=ImmediateExecutor(),
    )
    job = service.create_job(
        prompt="Animate", owner_id="user-a", session_id="session-a", assistant_message_id="message-a",
        attachments=[{"file_url": "/api/uploads/other.png", "filename": "other.png", "mime_type": "image/png"}],
    )
    assert job["status"] == "failed"
    assert job["error_category"] == "image_ownership"
    assert "raw" not in str(job["user_error"]).lower()
    assert provider.submissions == []


def test_video_job_rejects_conversation_owned_by_another_user(tmp_path):
    provider = AsyncFakeProvider()
    service = VideoGenerationService(
        tmp_path / "jobs.json", tmp_path / "uploads", provider=provider,
        session_service=OwnedSessionLookup(), executor=ImmediateExecutor(),
    )
    job = service.create_job(
        prompt="A cabin", owner_id="user-a", session_id="session-b", assistant_message_id="message-a",
    )
    assert job["status"] == "failed"
    assert job["error_category"] == "conversation_unavailable"
    assert provider.submissions == []


def test_image_video_requires_public_https_endpoint_before_provider_use(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "owned.png").write_bytes(b"\x89PNG\r\n\x1a\nopaque")
    provider = AsyncFakeProvider()
    service = VideoGenerationService(
        tmp_path / "jobs.json", uploads, provider=provider,
        upload_ownership_service=FakeUploadOwnership({"owned.png": "user-a"}),
        reference_signing_key="test-secret-key", public_url="http://localhost:5000",
        executor=ImmediateExecutor(),
    )
    job = service.create_job(
        prompt="Animate", owner_id="user-a", session_id="session-a", assistant_message_id="message-a",
        attachments=[{"file_url": "/api/uploads/owned.png", "filename": "owned.png", "mime_type": "image/png"}],
    )
    assert job["status"] == "failed"
    assert job["error_category"] == "provider_configuration"
    assert provider.submissions == []


def test_video_intent_accepts_explicit_and_image_animation_requests(tmp_path):
    decision = DecisionService(type("Chat", (), {"_load_execution_state": lambda self, _sid: {}})())
    image = [{"filename": "source.png", "mime_type": "image/png"}]
    assert decision._decide_route("Animate this. Slowly move the camera.", attachments=image, session_id="s")["route"] == "video_generation"
    assert decision._decide_route("What is in this image?", attachments=image, session_id="s")["route"] != "video_generation"


def test_luma_download_validates_public_provider_host_mime_and_size(monkeypatch):
    provider = LumaVideoProvider(api_key="test-key")
    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("8.8.8.8", 443))],
    )

    class DownloadOpener:
        def open(self, request, timeout):
            assert request.full_url.startswith("https://video-bucket.s3.amazonaws.com/")
            assert timeout > 0
            return MockHTTPResponse(b"video-bytes", content_type="video/mp4")

    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: DownloadOpener())
    content, mime = provider.download_video(
        "https://video-bucket.s3.amazonaws.com/output.mp4?signature=provider",
        max_bytes=100,
    )
    assert content == b"video-bytes"
    assert mime == "video/mp4"
    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("127.0.0.1", 443))],
    )
    with pytest.raises(VideoGenerationError) as private:
        provider.download_video("https://video-bucket.s3.amazonaws.com/private.mp4", max_bytes=100)
    assert private.value.category == "invalid_response"
    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("8.8.8.8", 443))],
    )

    class BadMimeOpener:
        def open(self, request, timeout):
            return MockHTTPResponse(b"text", content_type="text/html")

    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: BadMimeOpener())
    with pytest.raises(VideoGenerationError):
        provider.download_video("https://video-bucket.s3.amazonaws.com/output.mp4", max_bytes=100)

    class OversizedOpener:
        def open(self, request, timeout):
            return MockHTTPResponse(b"x" * 101, content_type="video/mp4")

    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: OversizedOpener())
    with pytest.raises(VideoGenerationError):
        provider.download_video("https://video-bucket.s3.amazonaws.com/output.mp4", max_bytes=100)


def test_submitted_provider_job_id_resumes_polling_without_resubmission(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps({"jobs": [{
        "id": "video_resume", "owner_id": "user-a", "session_id": "session-a",
        "assistant_message_id": "message-a", "project_id": "project-a", "provider": "luma",
        "model": "ray-3.2", "prompt": "A cabin", "status": "generating",
        "provider_job_id": "provider-job-already-created", "aspect_ratio": "16:9",
        "resolution": "720p", "duration_option": "5s", "duration_seconds": 5,
        "materialized": False,
    }]}), encoding="utf-8")
    provider = AsyncFakeProvider()
    service = VideoGenerationService(
        jobs_file, tmp_path / "uploads", provider=provider,
        artifact_service=FakeArtifacts(), session_service=FakeSessions(),
        executor=ImmediateExecutor(), poll_wait=lambda _seconds: None,
    )
    recovered = service.get_job("video_resume", "user-a")
    assert recovered["status"] == "completed"
    assert provider.submissions == []
    assert service._find("video_resume")["provider_job_id"] == "provider-job-already-created"


def test_duplicate_idempotent_submission_reuses_one_paid_provider_job(tmp_path):
    provider = AsyncFakeProvider()
    service = VideoGenerationService(
        tmp_path / "jobs.json", tmp_path / "uploads", provider=provider,
        executor=DeferredExecutor(), poll_wait=lambda _seconds: None,
    )
    first = service.create_job(
        prompt="A cabin", owner_id="user-a", session_id="session-a",
        assistant_message_id="message-first", idempotency_key="request-123",
    )
    duplicate = service.create_job(
        prompt="A cabin", owner_id="user-a", session_id="session-a",
        assistant_message_id="message-retry", idempotency_key="request-123",
    )
    assert duplicate["id"] == first["id"]
    assert duplicate["assistant_message_id"] == "message-first"
    assert provider.submissions == []
    assert len(json.loads((tmp_path / "jobs.json").read_text())["jobs"]) == 1
    service._executor.run()
    assert len(provider.submissions) == 1


def test_budget_exhaustion_is_persisted_as_terminal_and_human_readable(tmp_path):
    service, _artifacts, _sessions = make_service(
        tmp_path, FakeProvider(error=VideoGenerationError("budget_exhausted", "RATE_LIMIT.BUDGET.EXCEEDED"))
    )
    created = create(service)
    failed = service.get_job(created["id"], "user-a")
    persisted = service._find(created["id"])
    assert failed["status"] == "failed"
    assert persisted["status"] == "failed"
    assert persisted["error_category"] == "provider_budget_exhausted"
    assert "doesn't have enough credits" in persisted["user_error"]
    assert "RATE_LIMIT.BUDGET.EXCEEDED" not in persisted["user_error"]


def test_budget_failure_does_not_poll_or_resubmit_provider_job(tmp_path):
    provider = BudgetSubmitProvider()
    service, _artifacts, _sessions = make_service(tmp_path, provider)
    created = create(service)
    assert created["status"] == "queued"
    failed = service.get_job(created["id"], "user-a")
    assert failed["status"] == "failed"
    assert failed["error_category"] == "provider_budget_exhausted"
    assert provider.polls == 0
    assert len(provider.submissions) == 1
    service.get_job(created["id"], "user-a")
    assert provider.polls == 0
    assert len(provider.submissions) == 1


def test_async_provider_safety_failure_has_no_artifact_and_human_message(tmp_path):
    provider = AsyncFailProvider()
    service, artifacts, sessions = make_service(tmp_path, provider)
    job = create(service)
    failed = service.get_job(job["id"], "user-a")
    assert failed["status"] == "failed"
    assert failed["error_category"] == "safety_rejected"
    assert "video safety system" in failed["user_error"]
    assert artifacts.items == []
    assert "safety review" not in sessions.messages[("user-a", "session-a", "message-a")]["text"]
