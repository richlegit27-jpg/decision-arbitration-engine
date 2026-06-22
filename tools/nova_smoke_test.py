import requests
import json
import sys

BASE = "http://127.0.0.1:5001"

checks = [
    ("home", "GET", "/"),
    ("app", "GET", "/app"),
    ("health", "GET", "/api/health"),
    ("sessions", "GET", "/api/sessions"),
    ("memory", "GET", "/api/memory"),
    ("artifacts", "GET", "/api/artifacts"),
]

failed = False

print("\nNOVA SMOKE TEST")
print("=" * 60)

for name, method, path in checks:
    url = BASE + path

    try:
        r = requests.get(url, timeout=8)
        ok = 200 <= r.status_code < 300
        print(f"{name:12} {r.status_code} {path}")

        if not ok:
            failed = True

        if path.startswith("/api/"):
            try:
                data = r.json()
                keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
                print(f"             json keys: {keys}")
            except Exception:
                print("             non-json response")
                failed = True

    except Exception as e:
        failed = True
        print(f"{name:12} FAILED {path}")
        print(f"             {e}")

print("\nCHAT TEST")
print("=" * 60)

payload = {
    "text": "Smoke test: reply with one short sentence saying Nova chat works.",
    "user_text": "Smoke test: reply with one short sentence saying Nova chat works.",
    "message": "Smoke test: reply with one short sentence saying Nova chat works.",
    "attachments": []
}

try:
    r = requests.post(
        BASE + "/api/chat",
        headers={
            "Content-Type": "application/json",
            "x-api-key": "testkey123"
        },
        json=payload,
        timeout=30
    )

    print("chat status:", r.status_code)

    if r.status_code != 200:
        failed = True

    try:
        data = r.json()
        text = (
            data.get("assistant_message", {}).get("text")
            or data.get("assistant_message", {}).get("content")
            or data.get("text")
            or data.get("message")
            or ""
        )

        print("assistant:", text)

        if not data.get("ok", False):
            failed = True

        if not text:
            failed = True

    except Exception:
        failed = True
        print(r.text[:1200])

except Exception as e:
    failed = True
    print("chat FAILED")
    print(e)

print("\nRESULT")
print("=" * 60)

if failed:
    print("FAIL")
    sys.exit(1)

print("PASS")
sys.exit(0)
