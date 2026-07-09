# NOVA_UPLOAD_ATTACHMENT_RESPONSE_NORMALIZER_TESTS_20260705

from io import BytesIO
import importlib

from nova_backend.services.upload_attachment_response_normalizer import (
    normalize_upload_response_payload,
)


def test_upload_response_normalizer_adds_canonical_fields_from_name():
    payload = {
        "ok": True,
        "name": "notes.txt",
        "mimetype": "text/plain",
        "size": "42",
    }

    output = normalize_upload_response_payload(payload)

    assert output["filename"] == "notes.txt"
    assert output["name"] == "notes.txt"
    assert output["url"] == "/api/uploads/notes.txt"
    assert output["download_url"] == "/api/uploads/notes.txt"
    assert output["mime_type"] == "text/plain"
    assert output["content_type"] == "text/plain"
    assert output["size_bytes"] == 42


def test_upload_response_normalizer_extracts_filename_from_url():
    payload = {
        "ok": True,
        "url": "/api/uploads/uploaded-file.md",
        "content_type": "text/markdown",
    }

    output = normalize_upload_response_payload(payload)

    assert output["filename"] == "uploaded-file.md"
    assert output["name"] == "uploaded-file.md"
    assert output["mime_type"] == "text/markdown"


def test_upload_response_normalizer_reads_nested_file_dict():
    payload = {
        "ok": True,
        "file": {
            "stored_filename": "nested.txt",
            "mime_type": "text/plain",
            "size_bytes": 100,
        },
    }

    output = normalize_upload_response_payload(payload)

    assert output["filename"] == "nested.txt"
    assert output["name"] == "nested.txt"
    assert output["url"] == "/api/uploads/nested.txt"
    assert output["mime_type"] == "text/plain"
    assert output["size_bytes"] == 100


def test_real_upload_response_has_attachment_context_fields(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    app_module = importlib.import_module("app")
    client = app_module.app.test_client()

    response = client.post(
        "/api/upload",
        data={
            "file": (
                BytesIO(b"Canonical upload response marker."),
                "canonical-upload.txt",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code in {200, 201}

    data = response.get_json(silent=True) or {}

    assert data.get("ok") is not False
    assert data.get("filename") or data.get("name")
    assert data.get("url") or data.get("download_url")
