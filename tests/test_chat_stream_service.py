import json

from flask import Flask, jsonify

from nova_backend.services.chat_stream_service import ChatStreamService


def _events(response):
    body = "".join(
        chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
        for chunk in response.response
    )
    return [
        json.loads(block.removeprefix("data: "))
        for block in body.strip().split("\n\n")
    ]


def test_chat_stream_emits_response_before_single_completion_event():
    app = Flask(__name__)
    service = ChatStreamService()

    with app.test_request_context("/api/chat/stream", method="POST"):
        response = service.stream(
            lambda: jsonify(
                {
                    "ok": True,
                    "assistant_message": {
                        "text": "A real\nresponse",
                        "attachments": [{"id": "artifact-1"}],
                        "meta": {"route": "video_generation", "video_job_id": "video-1", "video_status": "queued"},
                    },
                }
            )
        )
        events = _events(response)

    types = [event["type"] for event in events]
    assert types[:2] == ["token", "token"]
    assert types[-2:] == ["message", "done"]
    assert types.count("done") == 1
    assert "debug" not in types
    assert "".join(event.get("content", "") for event in events if event["type"] == "token").strip() == "A real\nresponse"
    assert events[-1]["attachments"] == [{"id": "artifact-1"}]
    assert events[-1]["assistant_message"]["meta"]["video_job_id"] == "video-1"


def test_chat_stream_propagates_api_failure_without_reporting_success():
    app = Flask(__name__)
    service = ChatStreamService()

    with app.test_request_context("/api/chat/stream", method="POST"):
        response = service.stream(
            lambda: (jsonify({"ok": False, "error": "insufficient credits"}), 402)
        )
        events = _events(response)

    assert [event["type"] for event in events] == ["error", "done"]
    assert events[0]["content"] == "insufficient credits"
    assert not any(event["type"] in {"token", "message"} for event in events)


def test_chat_stream_reports_empty_or_exceptional_results_as_errors():
    app = Flask(__name__)
    service = ChatStreamService()

    with app.test_request_context("/api/chat/stream", method="POST"):
        empty = _events(service.stream(lambda: jsonify({"ok": True})))
        failed = _events(service.stream(lambda: (_ for _ in ()).throw(RuntimeError("provider unavailable"))))

    assert [event["type"] for event in empty] == ["error", "done"]
    assert [event["type"] for event in failed] == ["error", "done"]
    assert failed[0]["content"] == "provider unavailable"
