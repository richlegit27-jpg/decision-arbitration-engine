from app import _nova_direct_clean_attachment_text_response_20260611


def require(condition, message):
    if not condition:
        raise AssertionError(message)


raw = """
Attachment analysis:

Attachment test.txt content:; hello world

Key points:
1. hello world

Preview:
hello world
"""


result = _nova_direct_clean_attachment_text_response_20260611(raw)

require(
    isinstance(result, str),
    "cleaner returns string",
)

require(
    "hello world" in result,
    "attachment content preserved",
)

print("=" * 80)
print("NOVA ATTACHMENT DIRECT TEXT CLEAN SMOKE PASSED")
print("=" * 80)