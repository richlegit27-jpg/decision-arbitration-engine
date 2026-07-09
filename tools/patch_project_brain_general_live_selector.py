from pathlib import Path

path = Path("nova_backend/services/project_brain_general_intelligence.py")
text = path.read_text(encoding="utf-8")
original = text

text = text.replace(
    "from nova_backend.services.project_brain_context_builder import build_current_project_answer",
    "from nova_backend.services.project_brain_live_answer_selector import build_project_brain_live_answer",
)

text = text.replace(
    "return build_current_project_answer()",
    "return build_project_brain_live_answer(user_text=user_text).text",
)

if text != original:
    path.write_text(text, encoding="utf-8")
    print(f"{path}: patched Project Brain general answer to use live selector")
else:
    print(f"{path}: no change")

smoke_path = Path("tools/nova_project_brain_live_selector_api_smoke.py")
smoke_code = r'''
import json
import urllib.request


API_URL = "http://127.0.0.1:5001/api/chat"


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def post_chat(message, session_id):
    payload = {
        "message": message,
        "session_id": session_id,
        "attachments": [],
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=15) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, json.loads(body)


def extract_text(data):
    assistant = data.get("assistant_message") or {}
    return (
        assistant.get("text")
        or assistant.get("content")
        or data.get("text")
        or data.get("answer")
        or ""
    )


def extract_route(data):
    debug = data.get("debug") or {}
    assistant = data.get("assistant_message") or {}
    return (
        debug.get("route_taken")
        or debug.get("route")
        or assistant.get("route")
        or data.get("route")
        or ""
    )


def check_case(name, message, expected_terms, blocked_terms=None):
    print("")
    print("CASE:", name)
    status, data = post_chat(message, f"live_selector_api_{name.replace(' ', '_')}")
    text = extract_text(data)
    route = extract_route(data)
    lower = text.lower()

    print("STATUS:", status)
    print("ROUTE:", route)
    print("ANSWER:", text[:1200])

    assert_true(f"{name} api status", status == 200, status)
    assert_true(f"{name} answer exists", bool(text.strip()))
    assert_true(
        f"{name} route still project brain",
        "project_brain" in route.lower() or "project_state" in route.lower(),
        route,
    )

    for term in expected_terms:
        assert_true(
            f"{name} includes {term}",
            term.lower() in lower,
            text,
        )

    for term in blocked_terms or []:
        assert_true(
            f"{name} avoids {term}",
            term.lower() not in lower,
            text,
        )


def main():
    print("NOVA PROJECT BRAIN LIVE SELECTOR API SMOKE")
    print("==========================================")

    check_case(
        name="plain status uses freshness",
        message="where are we at with Nova right now?",
        expected_terms=[
            "current nova project state",
            "project brain",
            "freshness snapshot",
        ],
        blocked_terms=[
            "project brain decision context",
            "intent:",
        ],
    )

    check_case(
        name="next move uses decision",
        message="what should we do next?",
        expected_terms=[
            "project brain decision context",
            "intent: next_move_judgment",
            "validation:",
            "avoid:",
        ],
    )

    check_case(
        name="app py risk uses decision",
        message="should we patch app.py or test first?",
        expected_terms=[
            "project brain decision context",
            "intent: route_layer_risk",
            "service-layer extraction",
            "guard-stack audit",
        ],
    )

    print("")
    print("NOVA PROJECT BRAIN LIVE SELECTOR API SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
'''
smoke_path.write_text(smoke_code.lstrip(), encoding="utf-8")
print(f"{smoke_path}: wrote")
