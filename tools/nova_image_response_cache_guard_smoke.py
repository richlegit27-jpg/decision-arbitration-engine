import json

from nova_backend.services.image_response_cache_guard_service import (
    fix_image_response,
    is_image_response,
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)

    print("PASS", message)


print("=" * 80)
print("NOVA IMAGE RESPONSE CACHE GUARD SMOKE")
print("=" * 80)


image_payload = {
    "assistant_message": {
        "role": "assistant",
        "text": "some old generated text",
        "meta": {
            "source": "image_generation",
        },
    },
    "saved_artifact": {
        "kind": "image",
        "prompt": "a purple robot",
    },
    "session": {
        "messages": [],
    },
}


require(
    is_image_response(image_payload),
    "image response detected",
)


fixed = fix_image_response(image_payload)


require(
    fixed["assistant_message"]["text"] == "Generated image: a purple robot",
    "assistant image text normalized",
)


require(
    fixed["saved_artifact"]["summary"] == "Generated image: a purple robot",
    "artifact summary normalized",
)


normal_payload = {
    "assistant_message": {
        "role": "assistant",
        "text": "hello",
    }
}


require(
    not is_image_response(normal_payload),
    "normal response ignored",
)


print()
print("=" * 80)
print("NOVA IMAGE RESPONSE CACHE GUARD SMOKE: PASS")
print("=" * 80)