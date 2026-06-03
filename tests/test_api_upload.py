from __future__ import annotations

from pathlib import Path


def test_file_upload():
    from app import app, UPLOADS_DIR

    client = app.test_client()

    upload_name = "pytest_test_upload.txt"
    upload_bytes = b"test upload content"

    response = client.post(
        "/api/upload",
        data={
            "file": (
                __import__("io").BytesIO(upload_bytes),
                upload_name,
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["ok"] is True
    assert payload["original_filename"] == upload_name
    assert payload["filename"]
    assert payload["file_url"].startswith("/api/uploads/")
    assert payload["url"].startswith("/api/uploads/")
    assert payload["mime_type"]
    assert int(payload["size"]) == len(upload_bytes)

    saved_path = Path(UPLOADS_DIR) / payload["filename"]
    assert saved_path.exists()
    assert saved_path.read_bytes() == upload_bytes

    saved_path.unlink(missing_ok=True)
