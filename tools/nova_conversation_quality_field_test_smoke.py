
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
    assert_true(f"{message} status", response.status_code == 200, response.text[:800])
    return response.json()


def get_text(data):
    assistant = data.get("assistant_message")
    assistant_text = ""
    if isinstance(assistant, dict):
        assistant_text = assistant.get("text") or assistant.get("content") or ""

    return (
        data.get("text")
        or data.get("answer")
        or data.get("message")
        or assistant_text
        or ""
    )


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


def assert_usable_answer(name, data):
    text = get_text(data)
    assert_true(f"{name} has text", bool(text.strip()), data)
    assert_true(f"{name} has assistant message", isinstance(data.get("assistant_message"), dict), data)
    assert_true(f"{name} has debug", isinstance(data.get("debug"), dict), data)


def main():
    print("NOVA CONVERSATION QUALITY FIELD TEST SMOKE")
    print("==========================================")

    stamp = str(int(time.time()))
    session_id = f"conversation_quality_{stamp}"

    first = post_chat("hey nova", session_id)
    assert_usable_answer("casual greeting", first)
    assert_true("casual greeting not execution", "execution" not in get_route(first).lower(), first)

    second = post_chat("i'm testing if you can keep following what i'm saying", session_id)
    assert_usable_answer("continuation setup", second)
    assert_true("continuation setup not image", "image" not in get_route(second).lower(), second)

    direct = post_chat("what are we working on now", session_id)
    assert_usable_answer("direct project recall", direct)
    assert_true("direct recall route", get_route(direct) == "project_state_current_memory_direct_recall", direct)
    from nova_backend.services.project_brain_upgrade_radar import (
        select_best_upgrade,
    )

    current_best_move = select_best_upgrade().name

    assert_true(
        "direct recall has canonical current best move",
        current_best_move in get_text(direct),
        get_text(direct),
    )

    assert_true(
        "direct recall excludes stale cleanup move",
        "Start Project Brain cleanup/consolidation"
        not in get_text(direct),
        get_text(direct),
    )

    general = post_chat("what changed recently in the Nova project", session_id)
    assert_usable_answer("general project answer", general)
    assert_true("general project route", get_route(general) == "project_brain_general_intelligence", general)

    print("")
    print("NOVA CONVERSATION QUALITY FIELD TEST SMOKE PASSED")


if __name__ == "__main__":
    main()
