from pathlib import Path

SERVICE = Path("nova_backend/services/attachment_response_finalizer.py")
SMOKE = Path("tools/nova_attachment_response_finalizer_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
from __future__ import annotations

from copy import deepcopy
from typing import Any


ATTACHMENT_RESPONSE_FINALIZER_NAME = "nova_attachment_response_finalizer_v1"


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def clean_attachment_item(item: Any) -> dict:
    if not isinstance(item, dict):
        return {}

    cleaned = {}

    for key in (
        "filename",
        "name",
        "original_name",
        "path",
        "url",
        "mime_type",
        "content_type",
        "size",
        "size_bytes",
        "kind",
        "type",
        "summary",
        "text",
    ):
        value = item.get(key)
        if value is not None and value != "":
            cleaned[key] = value

    return cleaned


def normalize_attachments(value: Any) -> list[dict]:
    result = []
    seen = set()

    for item in _as_list(value):
        cleaned = clean_attachment_item(item)
        if not cleaned:
            continue

        identity = (
            str(cleaned.get("filename") or cleaned.get("name") or "").strip(),
            str(cleaned.get("url") or cleaned.get("path") or "").strip(),
            str(cleaned.get("mime_type") or cleaned.get("content_type") or "").strip(),
        )

        if identity in seen:
            continue

        seen.add(identity)
        result.append(cleaned)

    return result


def extract_response_attachments(payload: dict) -> list[dict]:
    if not isinstance(payload, dict):
        return []

    assistant_message = _as_dict(payload.get("assistant_message"))
    debug = _as_dict(payload.get("debug"))

    candidates = []

    for key in ("attachments", "session_attachments", "uploaded_attachments"):
        candidates.extend(_as_list(payload.get(key)))

    for key in ("attachments", "session_attachments"):
        candidates.extend(_as_list(assistant_message.get(key)))

    for key in ("attachments", "session_attachments"):
        candidates.extend(_as_list(debug.get(key)))

    return normalize_attachments(candidates)


def should_finalize_attachment_response(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False

    if extract_response_attachments(payload):
        return True

    assistant_message = _as_dict(payload.get("assistant_message"))

    return any(
        key in payload or key in assistant_message
        for key in ("attachments", "session_attachments", "uploaded_attachments")
    )


def finalize_attachment_response_payload(
    payload: dict,
    *,
    preserve_existing: bool = True,
) -> dict:
    if not should_finalize_attachment_response(payload):
        return payload

    attachments = extract_response_attachments(payload)

    result = deepcopy(payload)

    if not preserve_existing or "attachments" not in result:
        result["attachments"] = attachments

    if not preserve_existing or "session_attachments" not in result:
        result["session_attachments"] = attachments

    assistant_message = result.get("assistant_message")
    if isinstance(assistant_message, dict):
        if not preserve_existing or "attachments" not in assistant_message:
            assistant_message["attachments"] = attachments
        result["assistant_message"] = assistant_message

    debug = result.get("debug")
    if not isinstance(debug, dict):
        debug = {}

    debug["attachment_response_finalizer"] = True
    debug["attachment_count"] = len(attachments)
    debug["session_attachments_count"] = len(attachments)
    result["debug"] = debug

    return result
''', encoding="utf-8")

SMOKE.write_text(r'''
from nova_backend.services.attachment_response_finalizer import (
    clean_attachment_item,
    extract_response_attachments,
    finalize_attachment_response_payload,
    normalize_attachments,
    should_finalize_attachment_response,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA ATTACHMENT RESPONSE FINALIZER SMOKE")
    print("========================================")

    raw_item = {
        "filename": "test.png",
        "url": "/api/uploads/test.png",
        "mime_type": "image/png",
        "size_bytes": 123,
        "unused": "drop me",
    }

    cleaned = clean_attachment_item(raw_item)
    assert_true("clean keeps filename", cleaned["filename"] == "test.png", cleaned)
    assert_true("clean drops unused", "unused" not in cleaned, cleaned)

    duplicated = normalize_attachments([raw_item, raw_item, {}, "bad"])
    assert_true("normalize dedupes", len(duplicated) == 1, duplicated)

    payload = {
        "route": "chat",
        "text": "uploaded",
        "assistant_message": {
            "text": "I see the file.",
            "attachments": [
                {
                    "filename": "test.png",
                    "url": "/api/uploads/test.png",
                    "mime_type": "image/png",
                }
            ],
        },
    }

    assert_true("should finalize", should_finalize_attachment_response(payload) is True)

    extracted = extract_response_attachments(payload)
    assert_true("extract one attachment", len(extracted) == 1, extracted)
    assert_true("extract filename", extracted[0]["filename"] == "test.png", extracted)

    finalized = finalize_attachment_response_payload(payload)
    assert_true("top attachments added", len(finalized["attachments"]) == 1, finalized)
    assert_true("session attachments added", len(finalized["session_attachments"]) == 1, finalized)
    assert_true("route preserved", finalized["route"] == "chat", finalized)
    assert_true("marker added", finalized["debug"]["attachment_response_finalizer"] is True, finalized)
    assert_true("attachment count", finalized["debug"]["attachment_count"] == 1, finalized)

    existing = {
        "attachments": [
            {
                "filename": "keep.txt",
            }
        ],
        "assistant_message": {
            "attachments": [
                {
                    "filename": "new.txt",
                }
            ],
        },
    }

    preserved = finalize_attachment_response_payload(existing, preserve_existing=True)
    assert_true("preserve existing top attachments", preserved["attachments"][0]["filename"] == "keep.txt", preserved)

    overwritten = finalize_attachment_response_payload(existing, preserve_existing=False)
    assert_true("overwrite top attachments", overwritten["attachments"][0]["filename"] == "keep.txt" or overwritten["attachments"][0]["filename"] == "new.txt", overwritten)
    assert_true("overwrite has debug", overwritten["debug"]["attachment_response_finalizer"] is True, overwritten)

    normal = {
        "text": "normal chat",
        "route": "chat",
    }

    untouched = finalize_attachment_response_payload(normal)
    assert_true("normal untouched", untouched == normal, untouched)

    print("")
    print("NOVA ATTACHMENT RESPONSE FINALIZER SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

print("installed Attachment Response Finalizer v1 service and smoke")
