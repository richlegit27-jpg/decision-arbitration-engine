import requests
import sys
from pathlib import Path

BASE = "http://127.0.0.1:5001"
ROOT = Path(__file__).resolve().parents[1]
TEST_FILE = ROOT / "tools" / "smoke_attachment.txt"
UPLOADS_DIR = ROOT / "uploads"

failed = False


def cleanup():
    try:
        TEST_FILE.unlink(missing_ok=True)
    except Exception:
        pass

    try:
        for file in UPLOADS_DIR.glob("smoke_attachment_*.txt"):
            file.unlink(missing_ok=True)
    except Exception:
        pass


print("\nNOVA ATTACHMENT SMOKE TEST")
print("=" * 60)

cleanup()

try:
    TEST_FILE.write_text(
        "This is a Nova attachment smoke test. The assistant should recognize this uploaded file.",
        encoding="utf-8"
    )

    with TEST_FILE.open("rb") as f:
        r = requests.post(
            BASE + "/api/upload",
            files={"file": ("smoke_attachment.txt", f, "text/plain")},
            timeout=20
        )

    print("upload status:", r.status_code)

    if r.status_code != 200:
        failed = True
        print(r.text[:800])
        raise SystemExit(1)

    upload_data = r.json()
    print("upload json keys:", list(upload_data.keys()))

    attachment = {
        "filename": upload_data.get("filename") or "smoke_attachment.txt",
        "name": upload_data.get("filename") or "smoke_attachment.txt",
        "url": upload_data.get("url") or upload_data.get("file_url") or "",
        "path": upload_data.get("path") or "",
        "type": upload_data.get("mime_type") or "text/plain",
    }

    payload = {
        "text": "Summarize the attached smoke test file in one short sentence.",
        "user_text": "Summarize the attached smoke test file in one short sentence.",
        "message": "Summarize the attached smoke test file in one short sentence.",
        "attachments": [attachment],
    }

    r = requests.post(
        BASE + "/api/chat",
        headers={
            "Content-Type": "application/json",
            "x-api-key": "testkey123",
        },
        json=payload,
        timeout=30,
    )

    print("chat status:", r.status_code)

    if r.status_code != 200:
        failed = True
        print(r.text[:1200])
        raise SystemExit(1)

    data = r.json()
    text = (
        data.get("assistant_message", {}).get("text")
        or data.get("assistant_message", {}).get("content")
        or data.get("text")
        or ""
    )

    print("assistant:", text)

    if not data.get("ok", False):
        failed = True

    if not text:
        failed = True

except SystemExit:
    raise

except Exception as e:
    failed = True
    print("FAILED:", e)

finally:
    cleanup()

print("\nRESULT")
print("=" * 60)

if failed:
    print("FAIL")
    sys.exit(1)

print("PASS")
sys.exit(0)
