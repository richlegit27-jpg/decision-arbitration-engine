import os
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


def main():
    print("NOVA PRODUCTION SESSION SWITCHING SMOKE")
    print("=======================================")
    print("BASE", BASE)

    listing = get_json("/api/sessions")
    sessions = listing.get("sessions") or listing.get("items") or []

    usable = [
        s for s in sessions
        if s.get("id") and int(s.get("message_count") or 0) > 0
    ]

    if len(usable) < 2:
        fail("at least two restorable sessions", str([
            {
                "id": s.get("id"),
                "title": s.get("title"),
                "message_count": s.get("message_count"),
            }
            for s in sessions[:10]
        ]))

    ok("at least two restorable sessions")

    first = usable[0]
    second = usable[1]

    for label, item in (("first", first), ("second", second)):
        sid = item.get("id")
        detail = get_json(f"/api/sessions/{sid}")

        if detail.get("ok") is not True:
            fail(f"{label} detail ok", str(detail))

        session = detail.get("session") or {}

        if session.get("id") != sid:
            fail(f"{label} detail id matches", f"expected={sid} got={session.get('id')}")

        messages = session.get("messages") or []
        if not messages:
            fail(f"{label} messages present", str(session))

        ok(f"{label} session restores")

    if first.get("id") == second.get("id"):
        fail("switch targets are distinct")

    ok("switch targets are distinct")

    print("")
    print("FIRST:", first.get("title"), first.get("id"))
    print("SECOND:", second.get("title"), second.get("id"))
    print("")
    print("NOVA PRODUCTION SESSION SWITCHING SMOKE PASSED")


if __name__ == "__main__":
    main()
