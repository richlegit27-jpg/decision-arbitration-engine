import os
import sys
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
    res = requests.get(f"{BASE}{path}", timeout=20)
    if res.status_code >= 400:
        fail(f"GET {path}", f"status={res.status_code} body={res.text[:500]}")
    return res.json()


def post_json(path, payload):
    res = requests.post(f"{BASE}{path}", json=payload, timeout=60)
    if res.status_code >= 400:
        fail(f"POST {path}", f"status={res.status_code} body={res.text[:500]}")
    return res.json()


def main():
    print("NOVA PRODUCTION SESSION RESTORE LOCK SMOKE")
    print("==========================================")
    print("BASE", BASE)

    health = get_json("/api/health")
    if health.get("ok") is not True:
        fail("health ok", str(health))
    ok("health ok")

    sid = f"session_restore_lock_{int(time.time())}"

    chat = post_json("/api/chat", {
        "session_id": sid,
        "message": "session restore lock smoke test",
        "user_text": "session restore lock smoke test",
        "text": "session restore lock smoke test",
        "attachments": [],
    })

    if chat.get("ok") is not True:
        fail("chat ok", str(chat))

    session = chat.get("session") or {}
    if session.get("id") != sid:
        fail("chat session id", str(session.get("id")))

    if int(session.get("message_count") or 0) < 1:
        fail("chat message count", str(session.get("message_count")))

    ok("chat creates saved session")

    listing = get_json("/api/sessions")
    sessions = listing.get("sessions") or listing.get("items") or []

    match = None
    for item in sessions:
        if item.get("id") == sid:
            match = item
            break

    if not match:
        fail("session appears in list", str([s.get("id") for s in sessions[:10]]))

    if int(match.get("message_count") or 0) < 1:
        fail("listed session message count", str(match))

    ok("session appears in list")

    detail = get_json(f"/api/sessions/{sid}")

    if detail.get("ok") is not True:
        fail("detail ok", str(detail))

    detail_session = detail.get("session") or {}

    if detail_session.get("id") != sid:
        fail("detail session id", str(detail_session.get("id")))

    messages = detail_session.get("messages") or []
    if not messages:
        fail("detail messages present", str(detail_session))

    joined = " ".join(str(m.get("text") or m.get("content") or "") for m in messages)
    if "session restore lock smoke test" not in joined:
        fail("detail contains user message", joined[:500])

    ok("session detail restores messages")

    user_id = detail_session.get("user_id") or detail.get("user_id") or ""
    username = detail_session.get("username") or detail.get("username") or ""

    if not user_id and not username:
        fail("owner present", str(detail))

    ok("owner present")

    print("")
    print("NOVA PRODUCTION SESSION RESTORE LOCK SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
