import json
import requests


BASE_URL = "http://127.0.0.1:5001"


def require(condition, message):
    if not condition:
        raise AssertionError(message)

    print("PASS", message)


print("=" * 80)
print("NOVA API CHAT PROJECT BRAIN LIVE SMOKE")
print("=" * 80)


payload = {
    "message": "what now?",
    "session_id": "project_brain_live_smoke_001",
}


response = requests.post(
    f"{BASE_URL}/api/chat",
    json=payload,
    timeout=30,
)


print("STATUS:", response.status_code)
print("BODY:", response.text[:2000])

require(
    response.status_code == 200,
    "api chat returned 200",
)

data = response.json()


require(
    isinstance(data, dict),
    "response json returned",
)


text = json.dumps(
    data
).lower()


require(
    "project" in text
    or "nova" in text
    or "next" in text,
    "project brain signal present",
)


require(
    "assistant_message" in data
    or "response" in data
    or "message" in data
    or "answer" in data,
    "assistant response exists",
)

print()
print("=" * 80)
print("NOVA API CHAT PROJECT BRAIN LIVE SMOKE PASSED")
print("=" * 80)