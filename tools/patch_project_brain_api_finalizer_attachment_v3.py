from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_api_finalizer.py")
SMOKE = Path("tools/nova_project_brain_api_finalizer_smoke.py")

text = SERVICE.read_text(encoding="utf-8-sig")

text = text.replace(
r'''def _build_state_recall_refresh_hook(
    refresh_project_state_payload: Callable[[dict], dict],
    finalize_session_response_payload: Callable[[dict], dict] | None = None,
):
    session_finalizer = finalize_session_response_payload or _identity_payload
''',
r'''def _build_state_recall_refresh_hook(
    refresh_project_state_payload: Callable[[dict], dict],
    finalize_session_response_payload: Callable[[dict], dict] | None = None,
    finalize_attachment_response_payload: Callable[[dict], dict] | None = None,
):
    session_finalizer = finalize_session_response_payload or _identity_payload
    attachment_finalizer = finalize_attachment_response_payload or _identity_payload
'''
)

text = text.replace(
r'''            refreshed = refresh_project_state_payload(data)
            finalized = session_finalizer(refreshed)

            if finalized is data or finalized == data:
                return response

            response.set_data(json.dumps(finalized, ensure_ascii=False))
''',
r'''            refreshed = refresh_project_state_payload(data)
            session_finalized = session_finalizer(refreshed)
            finalized = attachment_finalizer(session_finalized)

            if finalized is data or finalized == data:
                return response

            response.set_data(json.dumps(finalized, ensure_ascii=False))
'''
)

text = text.replace(
r'''def install_project_brain_state_recall_refresh_finalizer(
    app: Any,
    refresh_project_state_payload: Callable[[dict], dict] | None = None,
    finalize_session_response_payload: Callable[[dict], dict] | None = None,
) -> dict:
''',
r'''def install_project_brain_state_recall_refresh_finalizer(
    app: Any,
    refresh_project_state_payload: Callable[[dict], dict] | None = None,
    finalize_session_response_payload: Callable[[dict], dict] | None = None,
    finalize_attachment_response_payload: Callable[[dict], dict] | None = None,
) -> dict:
'''
)

text = text.replace(
r'''    if finalize_session_response_payload is None:
        from nova_backend.services.session_response_finalizer import (
            finalize_session_response_payload as finalize_session_response_payload,
        )

    hook = _build_state_recall_refresh_hook(
        refresh_project_state_payload,
        finalize_session_response_payload=finalize_session_response_payload,
    )
''',
r'''    if finalize_session_response_payload is None:
        from nova_backend.services.session_response_finalizer import (
            finalize_session_response_payload as finalize_session_response_payload,
        )

    if finalize_attachment_response_payload is None:
        from nova_backend.services.attachment_response_finalizer import (
            finalize_attachment_response_payload as finalize_attachment_response_payload,
        )

    hook = _build_state_recall_refresh_hook(
        refresh_project_state_payload,
        finalize_session_response_payload=finalize_session_response_payload,
        finalize_attachment_response_payload=finalize_attachment_response_payload,
    )
'''
)

text = text.replace(
r'''        "session_response_finalizer": True,
''',
r'''        "session_response_finalizer": True,
        "attachment_response_finalizer": True,
'''
)

SERVICE.write_text(text, encoding="utf-8")

smoke = SMOKE.read_text(encoding="utf-8-sig")

if "def finalize_attachment_payload(payload):" not in smoke:
    smoke = smoke.replace(
r'''def finalize_session_payload(payload):
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
''',
r'''def finalize_session_payload(payload):
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
'''
    )

smoke = smoke.replace(
r'''        finalize_session_response_payload=finalize_session_payload,
    )
''',
r'''        finalize_session_response_payload=finalize_session_payload,
        finalize_attachment_response_payload=finalize_attachment_payload,
    )
'''
)

if "attachment id finalized" not in smoke:
    smoke = smoke.replace(
r'''    general_response = FakeResponse(json.dumps({
        "route": "project_brain_general_intelligence",
        "intent": "general_project_answer",
        "compact_project_context_delegated": True,
        "text": "Remaining risk: Start Project Brain cleanup/consolidation",
        "debug": {
            "requested_session_id": "general_123",
        },
    }))
''',
r'''    attachment_response = FakeResponse(json.dumps({
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
'''
    )

SMOKE.write_text(smoke, encoding="utf-8")

print("wired Attachment Response Finalizer into Project Brain API Finalizer v3")
