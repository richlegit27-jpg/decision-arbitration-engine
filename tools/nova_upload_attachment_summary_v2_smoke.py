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
    "size_bytes" in payload,
    "size bytes exists",
)

require(
    "extracted_text" in payload
    or "attachment_summary" in payload
    or "summary" in payload,
    "attachment text summary exists",
)

print("=" * 80)
print("NOVA UPLOAD ATTACHMENT SUMMARY V2 SMOKE PASSED")
print("=" * 80)