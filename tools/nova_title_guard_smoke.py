from nova_backend.services.title_guard_service import (
    is_garbage_title,
    clean_title,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)

    print("PASS", message)


print("=" * 80)
print("NOVA TITLE GUARD SMOKE")
print("=" * 80)


require(
    is_garbage_title("aaaaaaaaaaaaaaaaaaaa"),
    "detects repeated garbage title",
)


require(
    not is_garbage_title("Build State Bridge"),
    "keeps normal title",
)


cleaned = clean_title(
    "Web Fetch",
    "Create a backup system",
    "",
    "",
)


require(
    cleaned == "Create a backup system",
    "replaces web placeholder title",
)


cleaned = clean_title(
    "zzzzzzzzzzzzzzzzzz",
    "hello",
    "",
    "",
)


require(
    cleaned == "New Chat",
    "replaces garbage title",
)


print()
print("=" * 80)
print("NOVA TITLE GUARD SMOKE: PASS")
print("=" * 80)