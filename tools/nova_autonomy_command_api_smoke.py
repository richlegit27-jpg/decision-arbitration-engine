from __future__ import annotations

import json
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
            for key in ("content", "text", "message", "response", "answer"):
                value = assistant.get(key)
                if isinstance(value, str) and value.strip():
                    return value

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
    session_id = f"autonomy_command_smoke_{stamp}"

    tests = [
        (
            "autonomy image command",
            "autonomy: make Nova better at image descriptions",
            [
                "nova autonomy task brief",
                "proposal_only",
                "nova_backend/services/chat_service.py",
                "static/js/mobile/nova-mobile-images.js",
                "risks",
                "tests",
                "rollback",
            ],
        ),
        (
            "autonomy memory command",
            "safe autonomy: improve project memory recall",
            [
                "nova autonomy task brief",
                "project_state_service.py",
                "nova_memory_quality_smoke.py",
                "stale checkpoint",
            ],
        ),
    ]

    for name, prompt, needles in tests:
        payload = post_chat(prompt, session_id)
        text = extract_text(payload)
        assert_contains(name, text, needles)

    normal_payload = post_chat("hi", session_id)
    normal_text = extract_text(normal_payload)

    if "nova autonomy task brief" in normal_text.lower():
        raise AssertionError("normal chat was hijacked by autonomy route")

    print("PASS normal chat not hijacked")
    print("NOVA AUTONOMY COMMAND API SMOKE PASSED")
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
