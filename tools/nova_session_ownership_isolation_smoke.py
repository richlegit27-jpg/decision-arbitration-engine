import uuid

from app import app


RUN_ID = uuid.uuid4().hex[:8]

USER_A = f"session_owner_a_{RUN_ID}"
EMAIL_A = f"{USER_A}@test.local"

USER_B = f"session_owner_b_{RUN_ID}"
EMAIL_B = f"{USER_B}@test.local"

def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


print("=" * 80)
print("NOVA SESSION OWNERSHIP ISOLATION SMOKE")
print("=" * 80)


client = app.test_client()


# User A register/login
a = client.post(
    "/api/auth/register",
    json={
        "username": USER_A,
        "email": EMAIL_A,
        "password": "test1234",
    },
)

print("USER A STATUS:", a.status_code)
print("USER A BODY:", a.get_json())
require(a.status_code in (200, 201), "user A created")


# User A creates session
session_a = client.post(
    "/api/sessions/new",
    json={"title": "User A Session"},
).get_json()

session_a_id = session_a["session"]["id"]

require(bool(session_a_id), "user A session created")


# User B client
client_b = app.test_client()

b = client_b.post(
    "/api/auth/register",
    json={
        "username": USER_B,
        "email": EMAIL_B,
        "password": "test1234",
    },
)
require(b.status_code in (200, 201), "user B created")


# User B creates session
session_b = client_b.post(
    "/api/sessions/new",
    json={"title": "User B Session"},
).get_json()

session_b_id = session_b["session"]["id"]

require(bool(session_b_id), "user B session created")


# Ownership checks
open_a = client.get(f"/api/sessions/{session_a_id}")
open_b = client_b.get(f"/api/sessions/{session_b_id}")

require(open_a.status_code == 200, "A can open A")
require(open_b.status_code == 200, "B can open B")


cross_b = client_b.get(f"/api/sessions/{session_a_id}")
cross_a = client.get(f"/api/sessions/{session_b_id}")


require(
    cross_b.status_code in (403, 404),
    "B cannot open A",
)

require(
    cross_a.status_code in (403, 404),
    "A cannot open B",
)


print()
print("=" * 80)
print("NOVA SESSION OWNERSHIP ISOLATION SMOKE: PASS")