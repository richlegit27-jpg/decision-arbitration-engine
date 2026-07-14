from app import app


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


print("=" * 80)
print("NOVA ATTACHMENT STATUS HEALTH HOOK SMOKE")
print("=" * 80)

client = app.test_client()

response = client.get("/api/health")

require(
    response.status_code == 200,
    "health endpoint returns 200",
)

data = response.get_json()

require(
    isinstance(data, dict),
    "health returns json object",
)

require(
    "attachment_pipeline_ready" in data,
    "health exposes attachment pipeline readiness",
)

require(
    "attachment_pipeline" in data,
    "health exposes attachment pipeline status",
)

print("=" * 80)
print("NOVA ATTACHMENT STATUS HEALTH HOOK SMOKE PASSED")
print("=" * 80)