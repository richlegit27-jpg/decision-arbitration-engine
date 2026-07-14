import sys


def require(condition, message):
    if not condition:
        raise AssertionError(message)


from nova_backend.services.session_response_finalizer_service import (
    assistant_same_text_already_saved,
)


print("=" * 80)
print("NOVA FINALIZER SAME TEXT GUARD SMOKE")
print("=" * 80)


messages = [
    {
        "role": "user",
        "text": "hello",
        "content": "hello",
    },
    {
        "role": "assistant",
        "text": "Hello Richard.",
        "content": "Hello Richard.",
    },
]


duplicate = assistant_same_text_already_saved(
    messages,
    assistant_text="Hello Richard.",
)

require(
    duplicate is True,
    "existing assistant text was not detected",
)

print("PASS duplicate assistant text detected")


new_text = assistant_same_text_already_saved(
    messages,
    assistant_text="Different answer.",
)

require(
    new_text is False,
    "new assistant text incorrectly blocked",
)

print("PASS unique assistant text allowed")


print()
print("=" * 80)
print("NOVA FINALIZER SAME TEXT GUARD SMOKE PASSED")
print("=" * 80)