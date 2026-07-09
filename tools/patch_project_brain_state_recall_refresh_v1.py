from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_state_recall_refresh.py")
APP = Path("app.py")
SMOKE = Path("tools/nova_project_brain_state_recall_refresh_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_MEMORY_PATH = Path("data/nova_memory.json")


PROJECT_STATE_ROUTE = "project_state_current_memory_direct_recall"
STATE_BRIDGE_SOURCE = "project_brain_state_bridge"
STATE_BRIDGE_ID = "project_brain_state_bridge_current"

STALE_NEXT_MARKERS = (
    "Next move: Start Project Brain cleanup/consolidation",
    "Start Project Brain cleanup/consolidation",
)


def _clean(value) -> str:
    return str(value or "").strip()


def _load_json(path: str | Path, default):
    file_path = Path(path)

    if not file_path.exists():
        return default

    try:
        return json.loads(file_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _iter_memory_items(data):
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
        return

    if not isinstance(data, dict):
        return

    for key in ("current_project_state", "project_brain_state_bridge"):
        item = data.get(key)
        if isinstance(item, dict):
            yield item

    for key in ("memories", "items", "entries"):
        values = data.get(key)
        if isinstance(values, list):
            for item in values:
                if isinstance(item, dict):
                    yield item


def load_state_bridge_item(memory_path: str | Path = DEFAULT_MEMORY_PATH) -> dict:
    data = _load_json(memory_path, {"memories": []})

    candidates = []
    for item in _iter_memory_items(data):
        if (
            item.get("id") == STATE_BRIDGE_ID
            or item.get("source") == STATE_BRIDGE_SOURCE
            or "state_bridge" in item.get("tags", [])
        ):
            text = _clean(
                item.get("text")
                or item.get("content")
                or item.get("value")
            )
            if text:
                candidates.append((item, text))

    if not candidates:
        return {}

    return candidates[-1][0]


def load_state_bridge_text(memory_path: str | Path = DEFAULT_MEMORY_PATH) -> str:
    item = load_state_bridge_item(memory_path)

    return _clean(
        item.get("text")
        or item.get("content")
        or item.get("value")
    )


def answer_has_stale_cleanup(text: str) -> bool:
    value = _clean(text)
    return any(marker in value for marker in STALE_NEXT_MARKERS)


def should_refresh_project_state_answer(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False

    debug = payload.get("debug")
    if not isinstance(debug, dict):
        debug = {}

    route = (
        payload.get("route")
        or payload.get("route_taken")
        or debug.get("route_taken")
        or debug.get("route")
        or ""
    )

    if route == PROJECT_STATE_ROUTE:
        return True

    assistant_message = payload.get("assistant_message")
    assistant_text = ""
    if isinstance(assistant_message, dict):
        assistant_text = _clean(
            assistant_message.get("text")
            or assistant_message.get("content")
            or assistant_message.get("message")
        )

    combined = "\n".join([
        _clean(payload.get("text")),
        _clean(payload.get("answer")),
        _clean(payload.get("message")),
        assistant_text,
    ])

    return answer_has_stale_cleanup(combined)


def refresh_project_state_payload(
    payload: dict,
    memory_path: str | Path = DEFAULT_MEMORY_PATH,
) -> dict:
    if not isinstance(payload, dict):
        return payload

    state_text = load_state_bridge_text(memory_path)

    if not state_text:
        return payload

    if not should_refresh_project_state_answer(payload):
        return payload

    refreshed = dict(payload)

    assistant_message = refreshed.get("assistant_message")
    if isinstance(assistant_message, dict):
        assistant_message = dict(assistant_message)
    else:
        assistant_message = {}

    assistant_message["text"] = state_text
    assistant_message["content"] = state_text
    refreshed["assistant_message"] = assistant_message

    refreshed["text"] = state_text
    refreshed["answer"] = state_text
    refreshed["message"] = state_text

    debug = refreshed.get("debug")
    if isinstance(debug, dict):
        debug = dict(debug)
    else:
        debug = {}

    debug["route"] = PROJECT_STATE_ROUTE
    debug["route_taken"] = PROJECT_STATE_ROUTE
    debug["project_brain_state_recall_refresh"] = True
    debug["project_brain_state_recall_source"] = STATE_BRIDGE_SOURCE
    refreshed["debug"] = debug
    refreshed["route"] = PROJECT_STATE_ROUTE
    refreshed["route_taken"] = PROJECT_STATE_ROUTE

    return refreshed


def build_state_recall_refresh_answer(memory_path: str | Path = DEFAULT_MEMORY_PATH) -> str:
    text = load_state_bridge_text(memory_path)

    if not text:
        return "Project Brain State Recall Refresh: no State Bridge memory record found."

    stale = answer_has_stale_cleanup(text)

    return "\n".join([
        "Project Brain State Recall Refresh:",
        f"Source: {STATE_BRIDGE_SOURCE}",
        f"Has stale cleanup wording: {stale}",
        f"Direct Recall Text: {text}",
    ])
''', encoding="utf-8")

app_text = APP.read_text(encoding="utf-8-sig")

marker = "NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702"

if marker not in app_text:
    block = r'''

# NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702
# Thin compatibility hook: direct project-state recall must prefer the State Bridge memory record.
try:
    from nova_backend.services.project_brain_state_recall_refresh import refresh_project_state_payload as _nova_project_brain_refresh_project_state_payload_20260702

    @app.after_request
    def _nova_project_brain_state_recall_refresh_api_20260702(response):
        try:
            content_type = str(response.headers.get("Content-Type") or "")
            if "application/json" not in content_type.lower():
                return response

            raw = response.get_data(as_text=True)
            if not raw:
                return response

            data = json.loads(raw)
            refreshed = _nova_project_brain_refresh_project_state_payload_20260702(data)

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

    print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] installed")
except Exception as _nova_project_brain_state_recall_refresh_api_error_20260702:
    print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] install failed:", _nova_project_brain_state_recall_refresh_api_error_20260702)
'''
    APP.write_text(app_text.rstrip() + "\n" + block + "\n", encoding="utf-8")
    print("patched app.py with State Recall Refresh API hook")
else:
    print("State Recall Refresh API hook already installed")

SMOKE.write_text(r'''
import json
import tempfile
from pathlib import Path

from nova_backend.services.project_brain_state_recall_refresh import (
    PROJECT_STATE_ROUTE,
    answer_has_stale_cleanup,
    build_state_recall_refresh_answer,
    load_state_bridge_text,
    refresh_project_state_payload,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PROJECT BRAIN STATE RECALL REFRESH SMOKE")
    print("=============================================")

    state_text = (
        "Current Nova project state: Richard is working on the local Nova Flask app with Joe. "
        "Current checkpoint: Project Brain gangster intelligence stack is locked through Project Brain State Bridge v1. "
        "Current blocker: No active Project Brain intelligence blocker is open. "
        "Next move: Project Brain State Recall Refresh v1. "
        "Direct project-state recall should use this State Bridge record instead of stale cleanup wording."
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        memory_path = Path(temp_dir) / "nova_memory.json"
        memory_path.write_text(
            json.dumps({
                "memories": [
                    {
                        "id": "old_project_state",
                        "source": "old_project_state",
                        "text": "Next move: Start Project Brain cleanup/consolidation",
                    },
                    {
                        "id": "project_brain_state_bridge_current",
                        "source": "project_brain_state_bridge",
                        "tags": ["project_state", "state_bridge"],
                        "text": state_text,
                    },
                ]
            }, indent=2),
            encoding="utf-8",
        )

        loaded = load_state_bridge_text(memory_path)
        assert_true("loads state bridge text", loaded == state_text, loaded)
        assert_true("detects stale cleanup", answer_has_stale_cleanup("Next move: Start Project Brain cleanup/consolidation"))

        payload = {
            "debug": {
                "route_taken": PROJECT_STATE_ROUTE,
            },
            "route": PROJECT_STATE_ROUTE,
            "assistant_message": {
                "text": "Next move: Start Project Brain cleanup/consolidation",
                "content": "Next move: Start Project Brain cleanup/consolidation",
            },
            "text": "Next move: Start Project Brain cleanup/consolidation",
        }

        refreshed = refresh_project_state_payload(payload, memory_path=memory_path)

        assert_true("refresh preserves route", refreshed["debug"]["route_taken"] == PROJECT_STATE_ROUTE, refreshed)
        assert_true("refresh marker", refreshed["debug"]["project_brain_state_recall_refresh"] is True, refreshed)
        assert_true("assistant text refreshed", refreshed["assistant_message"]["text"] == state_text, refreshed)
        assert_true("top text refreshed", refreshed["text"] == state_text, refreshed)
        assert_true("stale cleanup removed", "Start Project Brain cleanup/consolidation" not in refreshed["text"], refreshed["text"])
        assert_true("next move refreshed", "Next move: Project Brain State Recall Refresh v1" in refreshed["text"], refreshed["text"])

        normal_payload = {
            "debug": {"route_taken": "chat"},
            "assistant_message": {"text": "normal chat"},
            "text": "normal chat",
        }
        normal_refreshed = refresh_project_state_payload(normal_payload, memory_path=memory_path)
        assert_true("normal chat untouched", normal_refreshed == normal_payload, normal_refreshed)

        answer = build_state_recall_refresh_answer(memory_path)
        assert_true("answer title", "Project Brain State Recall Refresh" in answer, answer)
        assert_true("answer source", "project_brain_state_bridge" in answer, answer)

    print("")
    print("NOVA PROJECT BRAIN STATE RECALL REFRESH SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

print("installed Project Brain State Recall Refresh v1")
