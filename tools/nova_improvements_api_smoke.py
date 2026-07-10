import requests


print(
    "NOVA IMPROVEMENTS API SMOKE"
)

print(
    "==========================="
)


r = requests.get(
    "http://127.0.0.1:5001/api/improvements"
)

assert r.status_code == 200

data = r.json()

assert data["ok"] is True

assert len(data["reports"]) > 0


print(
    "PASS returns improvement reports"
)

print(
    "NOVA IMPROVEMENTS API SMOKE PASSED"
)