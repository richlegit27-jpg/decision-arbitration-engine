from app import app


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


print("=" * 80)
print("NOVA ATTACHMENT STATUS ROUTE SMOKE")
print("=" * 80)

client = app.test_client()

response = client.get("/api/attachment/status")

require(
    response.status_code == 200,
    "attachment status endpoint returns 200",
)

data = response.get_json()

require(
    isinstance(data, dict),
    "attachment status returns json object",
)

require(
    "ok" in data,
    "attachment status exposes ok field",
)

print("STATUS PAYLOAD:")
print(data)

print("=" * 80)
print("NOVA ATTACHMENT STATUS ROUTE SMOKE PASSED")
print("=" * 80)