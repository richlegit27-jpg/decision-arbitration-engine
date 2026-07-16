from __future__ import annotations


def finalize_upload_attachment_response(payload):
    from nova_backend.services.upload_attachment_response_normalizer import (
        normalize_upload_response_payload,
    )

    from nova_backend.services.chat_turn_attachment_hydrator import (
        hydrate_attachment_for_context,
    )

    normalized = normalize_upload_response_payload(payload)
    hydrated = hydrate_attachment_for_context(normalized)

    return hydrated