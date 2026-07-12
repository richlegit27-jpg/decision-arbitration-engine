import json
import time
import requests

BASE = "http://127.0.0.1:5001"


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def post_chat(message, session_id):
    response = requests.post(
        f"{BASE}/api/chat",
        json={
            "message": message,
            "session_id": session_id,
            "attachments": [],
        },
        timeout=30,
    )
    assert_true(f"{message} api status", response.status_code == 200, response.text[:500])
    return response.json()


def get_route(data):
    debug = data.get("debug") if isinstance(data.get("debug"), dict) else {}
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    assistant = data.get("assistant_message") if isinstance(data.get("assistant_message"), dict) else {}
    assistant_meta = assistant.get("meta") if isinstance(assistant.get("meta"), dict) else {}

    return (
        data.get("route")
        or data.get("route_taken")
        or debug.get("route_taken")
        or debug.get("route")
        or meta.get("route")
        or meta.get("strategy")
        or assistant_meta.get("route")
        or assistant_meta.get("strategy")
        or ""
    )


def get_text(data):
    assistant = data.get("assistant_message")
    assistant_text = ""
    if isinstance(assistant, dict):
        assistant_text = assistant.get("text") or assistant.get("content") or ""
    return data.get("text") or data.get("answer") or data.get("message") or assistant_text or ""


def assert_response_shape(name, data):
    assert_true(f"{name} has dict", isinstance(data, dict), data)
    assert_true(f"{name} has assistant_message", isinstance(data.get("assistant_message"), dict), data)
    assistant = data["assistant_message"]

    text = get_text(data)
    assert_true(f"{name} has text", bool(str(text).strip()), data)

    assert_true(
        f"{name} assistant has text/content",
        bool(str(assistant.get("text") or assistant.get("content") or "").strip()),
        assistant,
    )

    assert_true(f"{name} has debug", isinstance(data.get("debug"), dict), data)
    assert_true(f"{name} has route", bool(get_route(data)), data)


def main():
    print("NOVA FINAL RESPONSE SHAPE CONTRACT SMOKE")
    print("========================================")

    stamp = str(int(time.time()))

    normal = post_chat("hello", f"shape_normal_{stamp}")
    assert_response_shape("normal chat", normal)
    assert_true("normal route not empty", bool(get_route(normal)), normal)

    direct = post_chat("what are we working on now", f"shape_direct_{stamp}")
    assert_response_shape("direct recall", direct)
    assert_true(
        "direct recall route preserved",
        get_route(direct) == "project_state_current_memory_direct_recall",
        json.dumps(direct.get("debug", {}), indent=2),
    )
    from nova_backend.services.project_brain_upgrade_radar import (
        select_best_upgrade,
    )

    current_best_move = (
        select_best_upgrade().name
    )

    assert_true(
        "direct recall uses canonical state bridge move",
        current_best_move in get_text(direct),
        get_text(direct),
    )

    assert_true(
        "direct recall excludes stale cleanup move",
        "Start Project Brain cleanup/consolidation"
        not in get_text(direct),
        get_text(direct),
    )

    general = post_chat("what changed recently in the Nova project", f"shape_general_{stamp}")
    assert_response_shape("general project", general)
    assert_true(
        "general project route preserved",
        get_route(general) == "project_brain_general_intelligence",
        json.dumps(general.get("debug", {}), indent=2),
    )

    print("")
    print("NOVA FINAL RESPONSE SHAPE CONTRACT SMOKE PASSED")


if __name__ == "__main__":
    main()
