from __future__ import annotations

import json
import sys
import time
from urllib import error, request


BASE_URL = "http://127.0.0.1:5001"


def post_chat(message: str, session_id: str) -> dict:
    payload = {
        "message": message,
        "session_id": session_id,
        "attachments": [],
    }

    body = json.dumps(payload).encode("utf-8")

    req = request.Request(
        f"{BASE_URL}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=45) as res:
        raw = res.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def extract_text(payload) -> str:
    if isinstance(payload, dict):
        assistant = payload.get("assistant_message")
        if isinstance(assistant, dict):
            content = assistant.get("content")
            if isinstance(content, str) and content.strip():
                return content

        for key in ("content", "response", "message", "text", "answer"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return json.dumps(payload, ensure_ascii=False)


def assert_contains(name: str, text: str, needles: list[str]) -> None:
    low = text.lower()
    missing = [needle for needle in needles if needle.lower() not in low]

    if missing:
        raise AssertionError(
            f"{name} FAILED. Missing {missing}. Response was:\n{text}"
        )

    print(f"PASS {name}")


def main() -> int:
    stamp = str(int(time.time()))
    session_id = f"project_state_smoke_{stamp}"

    tests = [
        (
            "current project state",
            "what are we working on?",
            ["nova", "memory", "project-state"],
        ),
        (
            "just fixed",
            "what did we just fix?",
            ["regression", "locked"],
        ),
        (
            "remaining work",
            "what is left?",
            ["left", "project-state"],
        ),
        (
            "next command",
            "next",
            ["next", "project-state"],
        ),
        (
            "k command",
            "k",
            ["next", "project-state"],
        ),
    ]

    for name, prompt, needles in tests:
        payload = post_chat(prompt, session_id)
        text = extract_text(payload)
        assert_contains(name, text, needles)

    print("PROJECT STATE SMOKE PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except error.URLError as exc:
        print(f"FAILED: Nova server not reachable at {BASE_URL}: {exc}")
        raise SystemExit(1)
    except Exception as exc:
        print(f"FAILED: {exc}")
        raise SystemExit(1)
