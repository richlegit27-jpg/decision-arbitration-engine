from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_api_finalizer.py")
APP = Path("app.py")
SMOKE = Path("tools/nova_project_brain_api_finalizer_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
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


def install_project_brain_state_recall_refresh_finalizer(
    app: Any,
    refresh_project_state_payload: Callable[[dict], dict] | None = None,
) -> dict:
    if refresh_project_state_payload is None:
        from nova_backend.services.project_brain_state_recall_refresh import (
            refresh_project_state_payload as refresh_project_state_payload,
        )

    hook = _build_state_recall_refresh_hook(refresh_project_state_payload)

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
    }
''', encoding="utf-8")

app_text = APP.read_text(encoding="utf-8-sig")

marker = "# NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702"
start = app_text.find(marker)
if start == -1:
    raise SystemExit("State Recall Refresh app.py marker not found")

if start > 0 and app_text[start - 1] == "\n":
    start = start - 1

tail = '    print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] install failed:", _nova_project_brain_state_recall_refresh_api_error_20260702)\n'
end_tail = app_text.find(tail, start)
if end_tail == -1:
    raise SystemExit("State Recall Refresh app.py block tail not found")

end = end_tail + len(tail)

replacement = r'''
# NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702
# Service-owned finalizer install: direct project-state recall must prefer State Bridge memory.
try:
    from nova_backend.services.project_brain_api_finalizer import (
        install_project_brain_state_recall_refresh_finalizer as _nova_install_project_brain_state_recall_refresh_finalizer_20260702,
    )

    _nova_project_brain_state_recall_refresh_finalizer_result_20260702 = (
        _nova_install_project_brain_state_recall_refresh_finalizer_20260702(app)
    )

    print(
        "[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] service finalizer installed",
        _nova_project_brain_state_recall_refresh_finalizer_result_20260702,
    )
except Exception as _nova_project_brain_state_recall_refresh_api_error_20260702:
    print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] install failed:", _nova_project_brain_state_recall_refresh_api_error_20260702)
'''.strip() + "\n"

new_app_text = app_text[:start].rstrip() + "\n\n" + replacement + "\n" + app_text[end:].lstrip()

APP.write_text(new_app_text, encoding="utf-8")

SMOKE.write_text(r'''
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
    )

    assert_true("installer result", result["installed"] is True, result)
    assert_true("hook inserted first", app.after_request_funcs[None][0].__name__ == STATE_RECALL_REFRESH_HOOK_NAME, app.after_request_funcs)
    assert_true("existing hook preserved", app.after_request_funcs[None][1].__name__ == "existing_hook", app.after_request_funcs)

    second = install_project_brain_state_recall_refresh_finalizer(
        app,
        refresh_project_state_payload=refresh_payload,
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

    html_response = FakeResponse("<html></html>", content_type="text/html")
    html_after = hook(html_response)
    assert_true("html response untouched", html_after.get_data(as_text=True) == "<html></html>", html_after.get_data(as_text=True))

    print("")
    print("NOVA PROJECT BRAIN API FINALIZER SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

print("extracted Project Brain State Recall Refresh API finalizer into service")
