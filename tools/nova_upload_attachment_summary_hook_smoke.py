import json
import os
import tempfile

from app import app


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


print("=" * 80)
print("NOVA UPLOAD ATTACHMENT SUMMARY HOOK SMOKE")
print("=" * 80)

client = app.test_client()

with tempfile.NamedTemporaryFile(
    mode="w",
    suffix=".txt",
    delete=False,
    encoding="utf-8",
) as f:
    f.write("Nova upload hook smoke test attachment.")
    path = f.name

try:
    with open(path, "rb") as upload:
        response = client.post(
            "/api/upload",
            data={"file": upload},
            content_type="multipart/form-data",
        )

    require(
        response.status_code == 200,
        "upload endpoint returns 200",
    )

    data = response.get_json()

    require(
        isinstance(data, dict),
        "upload response returns json object",
    )

    require(
        "attachment_summary" in data
        or "summary" in data
        or "extracted_text" in data,
        "upload response contains attachment context fields",
    )

finally:
    try:
        os.remove(path)
    except Exception:
        pass


print("=" * 80)
print("NOVA UPLOAD ATTACHMENT SUMMARY HOOK SMOKE PASSED")
print("=" * 80)