import json
import urllib.request
from pathlib import Path


URL = "http://127.0.0.1:5001/api/chat"


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def post_chat(payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    print("NOVA PHASE 6F IMAGE ATTACHMENT ROUTE LIVE SMOKE")
    print("")

    payload = {
        "message": "summarize this attached image",
        "session_id": "phase6f_image_route_live_smoke_001",
        "attachments": [
            {
                "filename": "phase6f-missing-test.png",
                "content_type": "image/png",
                "url": "/api/uploads/phase6f-missing-test.png",
            }
        ],
    }

    result = post_chat(payload)

    assistant = result.get("assistant_message") or {}
    meta = assistant.get("meta") or {}
    debug = result.get("debug") or {}
    decision = debug.get("decision") or {}

    text = str(assistant.get("text") or "")

    assert_true("api ok", result.get("ok") is True)
    assert_true("attachment route taken", debug.get("route_taken") == "attachment_analysis", debug)
    assert_true("decision route attachment", decision.get("route") == "attachment_analysis", decision)
    assert_true("decision mode image", decision.get("mode") == "image_analysis", decision)
    assert_true("vision gate active", meta.get("api_chat_image_vision_gate") is True, meta)
    assert_true("attachment analysis active", meta.get("attachment_analysis") is True, meta)
    assert_true("no source urls", meta.get("source_urls") == [] and decision.get("source_urls") == [])
    assert_true("no sources", meta.get("sources") == [] and decision.get("sources") == [])
    assert_true("missing image reported", "image file not found" in text.lower(), text)

    print("")
    print("NOVA PHASE 6F IMAGE ATTACHMENT ROUTE LIVE SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
