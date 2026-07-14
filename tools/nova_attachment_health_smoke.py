from __future__ import annotations

import requests


BASE = "http://127.0.0.1:5001"


def require(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


print("=" * 80)
print("NOVA ATTACHMENT HEALTH SMOKE")
print("=" * 80)


r = requests.get(
    BASE + "/api/health",
    timeout=10,
)

require(
    r.status_code == 200,
    "health endpoint returns 200",
)

data = r.json()

require(
    isinstance(data, dict),
    "health returns json object",
)

require(
    "attachment_pipeline_ready" in data,
    "attachment pipeline readiness field exists",
)

require(
    "attachment_pipeline" in data,
    "attachment pipeline details exist",
)

print()
print("=" * 80)
print("NOVA ATTACHMENT HEALTH SMOKE PASSED")
print("=" * 80)