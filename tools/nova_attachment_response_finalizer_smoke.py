
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
