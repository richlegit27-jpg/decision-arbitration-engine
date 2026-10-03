from __future__ import annotations

import json

import pytest
from flask import Flask
from flask import session as flask_session

from nova_backend.services.chat.handle import chat_handle
from nova_backend.services.intent_service import IntentService
from nova_backend.services.video_generation_service import (
    VideoGenerationError,
    VideoGenerationService,
)
from nova_backend.services.session_service import SessionService


class ImmediateExecutor:
    def submit(self, callback, *args):
        callback(*args)


class FakeProvider:
    name = "test-provider"

    def __init__(self, result=None, error=None):
        self.result = result or {
            "video_bytes": b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00",
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


class FakeSessions:
    def __init__(self):
        self.messages = {}

    def replace_message(self, session_id, message_id, message, user_id=""):
        self.messages[(user_id, session_id, message_id)] = dict(message)
        return dict(message)


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

        decision = IntentService().detect("/video a small cabin beside a lake")
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
    assert path and path.read_bytes().startswith(b"\x00\x00\x00\x18ftyp")


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


def test_no_provider_reports_configuration_required_without_fake_success(tmp_path):
    service, artifacts, _ = make_service(tmp_path, None)
    job = create(service)
    assert job["status"] == "failed"
    assert job["error_category"] == "provider_configuration_required"
    assert "provider must be configured" in job["user_error"]
    assert artifacts.items == []


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
