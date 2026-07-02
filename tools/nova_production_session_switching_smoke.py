import os
import time
import requests

BASE = os.environ.get(
    "NOVA_PROD_BASE",
    "https://decision-arbitration-engine-production.up.railway.app",
).rstrip("/")


def fail(name, detail=""):
    print(f"FAIL {name}")
    if detail:
        print(detail)
    raise SystemExit(1)


def ok(name):
    print(f"PASS {name}")


def get_json(path):
    res = requests.get(f"{BASE}{path}", timeout=25)
    if res.status_code >= 400:
        fail(f"GET {path}", f"status={res.status_code} body={res.text[:500]}")
    return res.json()


def post_json(path, payload):
    res = requests.post(f"{BASE}{path}", json=payload, timeout=60)
    if res.status_code >= 400:
        fail(f"POST {path}", f"status={res.status_code} body={res.text[:500]}")
    return res.json()


def create_session(label):
    sid = f"session_switching_lock_{label}_{int(time.time())}"

    text = f"session switching smoke {label}"

    payload = {
        "session_id": sid,
        "message": text,
        "user_text": text,
        "text": text,
        "attachments": [],
    }

    chat = post_json("/api/chat", payload)

    if chat.get("ok") is not True:
        fail(f"{label} chat ok", str(chat))

    session = chat.get("session") or {}

    if session.get("id") != sid:
        fail(f"{label} chat session id", f"expected={sid} got={session.get('id')}")

    ok(f"{label} session created")
    return sid, text


def assert_restores(label, sid, expected_text):
    detail = get_json(f"/api/sessions/{sid}")

    if detail.get("ok") is not True:
        fail(f"{label} detail ok", str(detail))

    session = detail.get("session") or {}

    if session.get("id") != sid:
        fail(f"{label} detail id matches", f"expected={sid} got={session.get('id')}")

    messages = session.get("messages") or []

    if not messages:
        fail(f"{label} messages present", str(session))

    joined = " ".join(str(m.get("text") or m.get("content") or "") for m in messages)

    if expected_text not in joined:
        fail(f"{label} expected text present", joined[:500])

    ok(f"{label} session restores")
    return session


def main():
    print("NOVA PRODUCTION SESSION SWITCHING SMOKE")
    print("=======================================")
    print("BASE", BASE)

    health = get_json("/api/health")
    if health.get("ok") is not True:
        fail("health ok", str(health))
    ok("health ok")

    sid_a, text_a = create_session("a")
    time.sleep(1)
    sid_b, text_b = create_session("b")

    if sid_a == sid_b:
        fail("switch targets are distinct")

    ok("switch targets are distinct")

    session_a = assert_restores("first", sid_a, text_a)
    session_b = assert_restores("second", sid_b, text_b)

    session_a_again = assert_restores("first again", sid_a, text_a)

    if session_a_again.get("id") != session_a.get("id"):
        fail("first restore stable")

    ok("first restore stable after second switch")

    print("")
    print("FIRST:", session_a.get("title"), sid_a)
    print("SECOND:", session_b.get("title"), sid_b)
    print("")
    print("NOVA PRODUCTION SESSION SWITCHING SMOKE PASSED")


if __name__ == "__main__":
    main()
