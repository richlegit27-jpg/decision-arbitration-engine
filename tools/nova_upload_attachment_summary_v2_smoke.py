from app import app
import io


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


print("=" * 80)
print("NOVA UPLOAD ATTACHMENT SUMMARY V2 SMOKE")
print("=" * 80)

client = app.test_client()

response = client.post(
    "/api/upload",
    data={
        "file": (
            io.BytesIO(
                b"This is a V2 attachment extraction test."
            ),
            "v2_test.txt",
        )
    },
    content_type="multipart/form-data",
)

require(
    response.status_code == 200,
    "upload returns 200",
)

payload = response.get_json()

require(
    isinstance(payload, dict),
    "upload returns json object",
)

require(
    "original_filename" in payload,
    "original filename exists",
)

require(
    int(
        payload.get("size")
        or payload.get("size_bytes")
        or 0
    ) > 0,
    "file size exists",
)

require(
    bool(
        payload.get("url")
        or payload.get("file_url")
    ),
    "file url exists",
)

require(
    bool(payload.get("mime_type")),
    "mime type exists",
)

print("=" * 80)
print("NOVA UPLOAD ATTACHMENT SUMMARY V2 SMOKE PASSED")
print("=" * 80)