import json
import time
import requests


BASE = "https://decision-arbitration-engine-production.up.railway.app"


def show(label, response):
    print("")
    print(f"=== {label} ===")
    print("STATUS:", response.status_code)
    print("BODY:", response.text[:2000])


def as_json(response):
    try:
        return response.json()
    except Exception:
        return {}


def find_messages(payload):
    if not isinstance(payload, dict):
        return []

    candidates = [
        payload.get("messages"),
        payload.get("conversation"),
        payload.get("history"),
        payload.get("chat_history"),
        (payload.get("session") or {}).get("messages") if isinstance(payload.get("session"), dict) else None,
        (payload.get("data") or {}).get("messages") if isinstance(payload.get("data"), dict) else None,
    ]

    for candidate in candidates:
        if isinstance(candidate, list):
            return candidate

    return []


def detail(session, session_id):
    endpoints = [
        f"{BASE}/api/sessions/{session_id}",
        f"{BASE}/api/chat/{session_id}",
    ]

    for url in endpoints:
        response = session.get(url, timeout=30)
        show(f"DETAIL {url}", response)

        payload = as_json(response)
        messages = find_messages(payload)

        if response.status_code == 200 and messages:
            return payload, messages

    return {}, []


def main():
    stamp = int(time.time())
    username = f"session_restore_probe_{stamp}"
    password = "testpass123"
    email = f"{username}@example.com"

    session = requests.Session()

    print("NOVA PRODUCTION AUTHENTICATED SESSION RESTORE SMOKE")
    print("==================================================")
    print("BASE", BASE)
    print("USER", username)

    register = session.post(
        f"{BASE}/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
        timeout=30,
    )
    show("REGISTER", register)

    status = session.get(f"{BASE}/api/auth/status", timeout=30)
    show("AUTH STATUS", status)

    failed = []

    if not as_json(status).get("authenticated"):
        failed.append("auth status not authenticated after register")

    session_a = f"restore_probe_a_{stamp}"
    session_b = f"restore_probe_b_{stamp}"

    body_a = {
        "message": f"session restore probe A {stamp}",
        "user_text": f"session restore probe A {stamp}",
        "session_id": session_a,
    }

    body_b = {
        "message": f"session restore probe B {stamp}",
        "user_text": f"session restore probe B {stamp}",
        "session_id": session_b,
    }

    chat_a = session.post(f"{BASE}/api/chat", json=body_a, timeout=60)
    show("CHAT A", chat_a)

    chat_b = session.post(f"{BASE}/api/chat", json=body_b, timeout=60)
    show("CHAT B", chat_b)

    sessions = session.get(f"{BASE}/api/sessions", timeout=30)
    show("SESSIONS LIST", sessions)

    detail_a, messages_a = detail(session, session_a)
    detail_b, messages_b = detail(session, session_b)

    joined_a = json.dumps(messages_a, ensure_ascii=False)
    joined_b = json.dumps(messages_b, ensure_ascii=False)

    if f"session restore probe A {stamp}" not in joined_a:
        failed.append("session A detail did not restore probe text")

    if f"session restore probe B {stamp}" not in joined_b:
        failed.append("session B detail did not restore probe text")

    if failed:
        print("")
        print("NOVA PRODUCTION AUTHENTICATED SESSION RESTORE SMOKE FAILED")
        for item in failed:
            print("-", item)
        return 1

    print("")
    print("NOVA PRODUCTION AUTHENTICATED SESSION RESTORE SMOKE PASSED")
    print("SESSION_A", session_a)
    print("SESSION_B", session_b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
