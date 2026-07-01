import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:5001"


def post_json(path, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(path):
    with urllib.request.urlopen(BASE_URL + path, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    try:
        health = get_json("/api/health")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Nova server is not reachable at {BASE_URL}: {exc}")

    assert_true("health ok", health.get("ok") is True)
    assert_true("health ready", health.get("status") == "ready")

    session_id = "phase_3l_live_api_behavior_smoke_001"
    result = post_json(
        "/api/chat",
        {
            "message": "say only pong",
            "session_id": session_id,
            "attachments": [],
        },
    )

    assistant = result.get("assistant_message") or {}
    text = str(assistant.get("text") or assistant.get("content") or "").strip()

    assert_true("chat ok", result.get("ok") is True)
    assert_true("route chat", ((result.get("debug") or {}).get("route_taken") == "chat"))
    assert_true("active session matches", result.get("active_session_id") == session_id)
    assert_true("assistant says pong", text == "pong", f"text={text!r}")

    print("NOVA PHASE 3L LIVE API BEHAVIOR SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
