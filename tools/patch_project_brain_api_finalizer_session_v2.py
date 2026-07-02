from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_api_finalizer.py")
SMOKE = Path("tools/nova_project_brain_api_finalizer_smoke.py")

text = SERVICE.read_text(encoding="utf-8-sig")

old = r'''
def _build_state_recall_refresh_hook(
    refresh_project_state_payload: Callable[[dict], dict],
):
    def _nova_project_brain_state_recall_refresh_api_20260702(response):
        try:
            if not _is_json_response(response):
                return response

            raw = response.get_data(as_text=True)
            if not raw:
                return response

            data = json.loads(raw)
            refreshed = refresh_project_state_payload(data)

            if refreshed is data or refreshed == data:
                return response

            response.set_data(json.dumps(refreshed, ensure_ascii=False))
            response.headers["Content-Type"] = "application/json"
            response.headers["Content-Length"] = str(len(response.get_data()))
            return response
        except Exception as exc:
            try:
                print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] failed:", exc)
            except Exception:
                pass
            return response

    _nova_project_brain_state_recall_refresh_api_20260702.__name__ = STATE_RECALL_REFRESH_HOOK_NAME
    return _nova_project_brain_state_recall_refresh_api_20260702
'''

new = r'''
def _identity_payload(payload: dict) -> dict:
    return payload


def _build_state_recall_refresh_hook(
    refresh_project_state_payload: Callable[[dict], dict],
    finalize_session_response_payload: Callable[[dict], dict] | None = None,
):
    session_finalizer = finalize_session_response_payload or _identity_payload

    def _nova_project_brain_state_recall_refresh_api_20260702(response):
        try:
            if not _is_json_response(response):
                return response

            raw = response.get_data(as_text=True)
            if not raw:
                return response

            data = json.loads(raw)
            refreshed = refresh_project_state_payload(data)
            finalized = session_finalizer(refreshed)

            if finalized is data or finalized == data:
                return response

            response.set_data(json.dumps(finalized, ensure_ascii=False))
            response.headers["Content-Type"] = "application/json"
            response.headers["Content-Length"] = str(len(response.get_data()))
            return response
        except Exception as exc:
            try:
                print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] failed:", exc)
            except Exception:
                pass
            return response

    _nova_project_brain_state_recall_refresh_api_20260702.__name__ = STATE_RECALL_REFRESH_HOOK_NAME
    return _nova_project_brain_state_recall_refresh_api_20260702
'''

if old not in text:
    raise SystemExit("target hook builder not found")

text = text.replace(old, new)

old = r'''
def install_project_brain_state_recall_refresh_finalizer(
    app: Any,
    refresh_project_state_payload: Callable[[dict], dict] | None = None,
) -> dict:
    if refresh_project_state_payload is None:
        from nova_backend.services.project_brain_state_recall_refresh import (
            refresh_project_state_payload as refresh_project_state_payload,
        )

    hook = _build_state_recall_refresh_hook(refresh_project_state_payload)
'''

new = r'''
def install_project_brain_state_recall_refresh_finalizer(
    app: Any,
    refresh_project_state_payload: Callable[[dict], dict] | None = None,
    finalize_session_response_payload: Callable[[dict], dict] | None = None,
) -> dict:
    if refresh_project_state_payload is None:
        from nova_backend.services.project_brain_state_recall_refresh import (
            refresh_project_state_payload as refresh_project_state_payload,
        )

    if finalize_session_response_payload is None:
        from nova_backend.services.session_response_finalizer import (
            finalize_session_response_payload as finalize_session_response_payload,
        )

    hook = _build_state_recall_refresh_hook(
        refresh_project_state_payload,
        finalize_session_response_payload=finalize_session_response_payload,
    )
'''

if old not in text:
    raise SystemExit("target installer block not found")

text = text.replace(old, new)

old = r'''
    return {
        "installed": True,
        "hook_name": STATE_RECALL_REFRESH_HOOK_NAME,
        "before_count": before_count,
        "after_count": len(funcs),
        "position": 0,
        "runs_last": True,
    }
'''

new = r'''
    return {
        "installed": True,
        "hook_name": STATE_RECALL_REFRESH_HOOK_NAME,
        "before_count": before_count,
        "after_count": len(funcs),
        "position": 0,
        "runs_last": True,
        "session_response_finalizer": True,
    }
'''

if old not in text:
    raise SystemExit("target installer return block not found")

SERVICE.write_text(text.replace(old, new), encoding="utf-8")

smoke = SMOKE.read_text(encoding="utf-8-sig")

old = r'''
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
'''

new = r'''
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
'''

if old not in smoke:
    raise SystemExit("target smoke refresh_payload block not found")

smoke = smoke.replace(old, new)

smoke = smoke.replace(
    r'''    result = install_project_brain_state_recall_refresh_finalizer(
        app,
        refresh_project_state_payload=refresh_payload,
    )
''',
    r'''    result = install_project_brain_state_recall_refresh_finalizer(
        app,
        refresh_project_state_payload=refresh_payload,
        finalize_session_response_payload=finalize_session_payload,
    )
''',
)

smoke = smoke.replace(
    r'''    second = install_project_brain_state_recall_refresh_finalizer(
        app,
        refresh_project_state_payload=refresh_payload,
    )
''',
    r'''    second = install_project_brain_state_recall_refresh_finalizer(
        app,
        refresh_project_state_payload=refresh_payload,
        finalize_session_response_payload=finalize_session_payload,
    )
''',
)

insert = r'''
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
'''

anchor = r'''
    html_response = FakeResponse("<html></html>", content_type="text/html")
'''

if "session id finalized" not in smoke:
    if anchor not in smoke:
        raise SystemExit("smoke anchor not found")
    smoke = smoke.replace(anchor, insert + "\n" + anchor)

SMOKE.write_text(smoke, encoding="utf-8")

print("wired Session Response Finalizer into Project Brain API Finalizer v2")
