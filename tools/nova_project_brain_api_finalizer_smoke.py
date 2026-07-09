
import json

from nova_backend.services.project_brain_api_finalizer import (
    STATE_RECALL_REFRESH_HOOK_NAME,
    install_project_brain_state_recall_refresh_finalizer,
)


class FakeApp:
    def __init__(self):
        self.after_request_funcs = {None: []}


class FakeResponse:
    def __init__(self, data, content_type="application/json"):
        self.headers = {"Content-Type": content_type}
        self._data = data.encode("utf-8") if isinstance(data, str) else data

    def get_data(self, as_text=False):
        if as_text:
            return self._data.decode("utf-8")
        return self._data

    def set_data(self, value):
        self._data = value.encode("utf-8") if isinstance(value, str) else value


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def refresh_payload(payload):
    if payload.get("route") != "project_state_current_memory_direct_recall":
        return payload

    updated = dict(payload)
    updated["text"] = "Current Nova project state. Next move: Project Brain State Recall Refresh v1."
    updated["answer"] = updated["text"]
    updated["assistant_message"] = {
        "text": updated["text"],
        "content": updated["text"],
    }
    return updated


def finalize_session_payload(payload):
    if not isinstance(payload, dict):
        return payload

    session_id = str(
        payload.get("session_id")
        or payload.get("active_session_id")
        or payload.get("requested_session_id")
        or ""
    ).strip()

    if not session_id:
        debug = payload.get("debug")
        if isinstance(debug, dict):
            session_id = str(
                debug.get("requested_session_id")
                or debug.get("session_id")
                or debug.get("active_session_id")
                or ""
            ).strip()

    if not session_id:
        return payload

    updated = dict(payload)
    updated["session_id"] = updated.get("session_id") or session_id
    updated["active_session_id"] = updated.get("active_session_id") or session_id

    debug = updated.get("debug")
    if not isinstance(debug, dict):
        debug = {}

    debug["session_response_finalizer"] = True
    debug["requested_session_id"] = debug.get("requested_session_id") or session_id
    debug["active_session_id"] = debug.get("active_session_id") or session_id
    updated["debug"] = debug
    return updated


def finalize_attachment_payload(payload):
    if not isinstance(payload, dict):
        return payload

    assistant_message = payload.get("assistant_message")
    attachments = payload.get("attachments")

    if not attachments and isinstance(assistant_message, dict):
        attachments = assistant_message.get("attachments")

    if not isinstance(attachments, list):
        return payload

    updated = dict(payload)
    updated["attachments"] = attachments
    updated["session_attachments"] = updated.get("session_attachments") or attachments

    debug = updated.get("debug")
    if not isinstance(debug, dict):
        debug = {}

    debug["attachment_response_finalizer"] = True
    debug["attachment_count"] = len(attachments)
    updated["debug"] = debug
    return updated


def main():
    print("NOVA PROJECT BRAIN API FINALIZER SMOKE")
    print("======================================")

    app = FakeApp()

    def existing_hook(response):
        return response

    existing_hook.__name__ = "existing_hook"
    app.after_request_funcs[None].append(existing_hook)

    result = install_project_brain_state_recall_refresh_finalizer(
        app,
        refresh_project_state_payload=refresh_payload,
        finalize_session_response_payload=finalize_session_payload,
        finalize_attachment_response_payload=finalize_attachment_payload,
    )

    assert_true("installer result", result["installed"] is True, result)
    assert_true("hook inserted first", app.after_request_funcs[None][0].__name__ == STATE_RECALL_REFRESH_HOOK_NAME, app.after_request_funcs)
    assert_true("existing hook preserved", app.after_request_funcs[None][1].__name__ == "existing_hook", app.after_request_funcs)

    second = install_project_brain_state_recall_refresh_finalizer(
        app,
        refresh_project_state_payload=refresh_payload,
        finalize_session_response_payload=finalize_session_payload,
        finalize_attachment_response_payload=finalize_attachment_payload,
    )

    names = [func.__name__ for func in app.after_request_funcs[None]]
    assert_true("installer idempotent", names.count(STATE_RECALL_REFRESH_HOOK_NAME) == 1, names)
    assert_true("hook still final order", names[0] == STATE_RECALL_REFRESH_HOOK_NAME, names)
    assert_true("second install result", second["installed"] is True, second)

    response = FakeResponse(json.dumps({
        "route": "project_state_current_memory_direct_recall",
        "text": "Next move: Start Project Brain cleanup/consolidation",
    }))

    hook = app.after_request_funcs[None][0]
    refreshed_response = hook(response)
    refreshed = json.loads(refreshed_response.get_data(as_text=True))

    assert_true("response refreshed", "Project Brain State Recall Refresh v1" in refreshed["text"], refreshed)
    assert_true("content length set", "Content-Length" in refreshed_response.headers, refreshed_response.headers)

    normal_response = FakeResponse(json.dumps({
        "route": "chat",
        "text": "normal chat",
    }))

    normal_raw_before = normal_response.get_data(as_text=True)
    normal_after = hook(normal_response)
    assert_true("normal response untouched", normal_after.get_data(as_text=True) == normal_raw_before, normal_after.get_data(as_text=True))

    session_response = FakeResponse(json.dumps({
        "route": "chat",
        "text": "normal chat with session",
        "debug": {
            "requested_session_id": "session_abc",
        },
    }))

    session_after = hook(session_response)
    session_payload = json.loads(session_after.get_data(as_text=True))

    assert_true("session id finalized", session_payload["session_id"] == "session_abc", session_payload)
    assert_true("active session finalized", session_payload["active_session_id"] == "session_abc", session_payload)
    assert_true("session route preserved", session_payload["route"] == "chat", session_payload)
    assert_true("session finalizer marker", session_payload["debug"]["session_response_finalizer"] is True, session_payload)

    attachment_response = FakeResponse(json.dumps({
        "route": "chat",
        "text": "uploaded",
        "assistant_message": {
            "text": "I see the file.",
            "attachments": [
                {
                    "filename": "test.png",
                    "url": "/api/uploads/test.png",
                    "mime_type": "image/png",
                }
            ],
        },
    }))

    attachment_after = hook(attachment_response)
    attachment_payload = json.loads(attachment_after.get_data(as_text=True))

    assert_true("attachment id finalized", attachment_payload["attachments"][0]["filename"] == "test.png", attachment_payload)
    assert_true("session attachments finalized", attachment_payload["session_attachments"][0]["filename"] == "test.png", attachment_payload)
    assert_true("attachment route preserved", attachment_payload["route"] == "chat", attachment_payload)
    assert_true("attachment finalizer marker", attachment_payload["debug"]["attachment_response_finalizer"] is True, attachment_payload)

    general_response = FakeResponse(json.dumps({
        "route": "project_brain_general_intelligence",
        "intent": "general_project_answer",
        "compact_project_context_delegated": True,
        "text": "Remaining risk: Start Project Brain cleanup/consolidation",
        "debug": {
            "requested_session_id": "general_123",
        },
    }))

    general_after = hook(general_response)
    general_payload = json.loads(general_after.get_data(as_text=True))

    assert_true("general route preserved", general_payload["route"] == "project_brain_general_intelligence", general_payload)
    assert_true("general text not state refreshed", "Project Brain State Recall Refresh v1" not in general_payload["text"], general_payload)
    assert_true("general session finalized", general_payload["session_id"] == "general_123", general_payload)


    html_response = FakeResponse("<html></html>", content_type="text/html")
    html_after = hook(html_response)
    assert_true("html response untouched", html_after.get_data(as_text=True) == "<html></html>", html_after.get_data(as_text=True))

    print("")
    print("NOVA PROJECT BRAIN API FINALIZER SMOKE PASSED")


if __name__ == "__main__":
    main()
