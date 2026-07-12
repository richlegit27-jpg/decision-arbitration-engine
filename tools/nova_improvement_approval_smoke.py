import requests


BASE = "http://127.0.0.1:5001"


print(
    "NOVA IMPROVEMENT APPROVAL SMOKE"
)

print(
    "================================"
)


r = requests.get(
    f"{BASE}/api/improvements"
)

assert r.status_code == 200

data = r.json()

assert data["ok"] is True

print(
    "PASS returns improvement"
)


report = data["reports"][0]

assert (
    report["status"]
    ==
    "pending_review"
)

print(
    "PASS starts pending review"
)


improvement_id = report["id"]


r = requests.post(
    f"{BASE}/api/improvements/{improvement_id}/approve"
)

assert r.status_code == 200

approved = r.json()["report"]

assert (
    approved["status"]
    ==
    "approved"
)

print(
    "PASS approval changes state"
)


r = requests.post(
    f"{BASE}/api/improvements/{improvement_id}/reject"
)

assert r.status_code == 200

rejected = r.json()["report"]

assert (
    rejected["status"]
    ==
    "rejected"
)

print(
    "PASS rejection changes state"
)


print(
    "NOVA IMPROVEMENT APPROVAL SMOKE PASSED"
)