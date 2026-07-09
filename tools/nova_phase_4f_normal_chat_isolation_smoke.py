import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:5001"


BAD_NORMAL_CHAT_PHRASES = (
    "active nova mission",
    "active mission",
    "current step",
    "start a new mission",
    "no active mission",
    "last mission",
    "autonomy task",
    "project state",
    "remaining work",
    "next command",
    "next move:",
    "current focus:",
    "first remaining item:",
    "autonomy-plan fallback",
    "patch-build fallback",
)


def post_chat(message, session_id):
    body = {
        "message": message,
        "session_id": session_id,
        "attachments": [],
    }

    req = urllib.request.Request(
        BASE + "/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=25) as res:
        return json.loads(res.read().decode("utf-8", errors="replace"))


def get_text(payload):
    assistant = payload.get("assistant_message")
    if isinstance(assistant, dict):
        for key in ("content", "text", "message", "response", "answer"):
            value = assistant.get(key)
            if isinstance(value, str) and value.strip():
                return value

    for key in ("content", "response", "message", "text", "answer"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return json.dumps(payload, ensure_ascii=False)


def get_route(payload):
    debug = payload.get("debug") or {}
    decision = payload.get("decision") or {}
    meta = payload.get("meta") or {}

    if not isinstance(debug, dict):
        debug = {}
    if not isinstance(decision, dict):
        decision = {}
    if not isinstance(meta, dict):
        meta = {}

    return (
        debug.get("route_taken")
        or debug.get("route")
        or decision.get("route")
        or meta.get("strategy")
        or meta.get("route")
        or ""
    )


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def assert_clean_normal_chat(name, payload):
    text = get_text(payload)
    route = str(get_route(payload)).lower()
    low = text.lower()

    assert_true(name + " has text", bool(text.strip()), text)
    assert_true(
        name + " not autonomy route",
        "autonomy" not in route and "execution" not in route,
        f"route={route} text={text}",
    )

    found = [phrase for phrase in BAD_NORMAL_CHAT_PHRASES if phrase in low]
    assert_true(
        name + " has no autonomy/project bleed",
        not found,
        f"found={found} text={text}",
    )


def run():
    stamp = str(int(time.time()))
    session_id = "phase_4f_normal_chat_isolation_" + stamp

    # Normal chat should stay normal.
    first = post_chat("ping", session_id)
    assert_clean_normal_chat("initial normal chat", first)

    # Create a mission.
    mission = post_chat("auto-plan make a tiny notes cleanup helper", session_id)
    mission_text = get_text(mission).lower()
    assert_true(
        "mission starts",
        "step" in mission_text or "plan" in mission_text or "mission" in mission_text,
        mission_text,
    )

    # Advance/complete enough that stale mission carryover used to be risky.
    post_chat("next", session_id)
    post_chat("next", session_id)
    post_chat("next", session_id)

    # Fresh normal chat after mission traffic must not get hijacked.
    after = post_chat("what is 2 plus 2?", session_id)
    after_text = get_text(after).lower()
    assert_clean_normal_chat("post mission normal chat", after)
    assert_true(
        "post mission answers normal question",
        "4" in after_text or "four" in after_text,
        after_text,
    )

    # Another casual normal message should remain casual.
    casual = post_chat("tell me a short joke", session_id)
    assert_clean_normal_chat("casual normal chat", casual)

    print("NOVA PHASE 4F NORMAL CHAT ISOLATION SMOKE PASSED")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print("NOVA PHASE 4F NORMAL CHAT ISOLATION SMOKE FAILED")
        print(exc)
        sys.exit(1)
