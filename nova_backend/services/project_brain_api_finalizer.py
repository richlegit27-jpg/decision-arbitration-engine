
from __future__ import annotations

import json
from typing import Any, Callable


STATE_RECALL_REFRESH_HOOK_NAME = "_nova_project_brain_state_recall_refresh_api_20260702"


def _is_json_response(response: Any) -> bool:
    try:
        content_type = str(response.headers.get("Content-Type") or "")
    except Exception:
        return False

    return "application/json" in content_type.lower()


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

    funcs = app.after_request_funcs.setdefault(None, [])
    before_count = len(funcs)

    funcs[:] = [
        func for func in funcs
        if getattr(func, "__name__", "") != STATE_RECALL_REFRESH_HOOK_NAME
    ]

    # Flask runs after_request funcs in reverse registration order.
    # Index 0 executes last, so this remains the final JSON response mutator.
    funcs.insert(0, hook)

    return {
        "installed": True,
        "hook_name": STATE_RECALL_REFRESH_HOOK_NAME,
        "before_count": before_count,
        "after_count": len(funcs),
        "position": 0,
        "runs_last": True,
        "session_response_finalizer": True,
    }
