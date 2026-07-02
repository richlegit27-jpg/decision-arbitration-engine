
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
