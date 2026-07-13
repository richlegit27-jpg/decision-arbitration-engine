from nova_backend.services.session_title_guard_service import (
    clean_title,
    is_garbage_title,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


print("=" * 90)
print("NOVA SESSION TITLE GUARD SMOKE")
print("=" * 90)

require(
    is_garbage_title("!!!!!!!!!!!!!!!!!!!!"),
    "detect repeated symbol garbage",
)

require(
    is_garbage_title("aaaaaaaaaaaaaaaaaaaa"),
    "detect repeated character garbage",
)

require(
    not is_garbage_title("Build robot arm controller"),
    "normal user title survives",
)

require(
    clean_title(
        "Web Fetch",
        "Build robot arm controller",
        "chat",
        "web_fetch",
    )
    == "Build robot arm controller",
    "web fetch title replaced with user text",
)

require(
    clean_title(
        "!!!!!!!!!!!!!!!!!",
        "Hello Nova",
        "accidental_input_guard",
        "accidental_input_guard",
    )
    == "New Chat",
    "garbage accidental title becomes new chat",
)

require(
    clean_title(
        "My Nova Project",
        "ignored",
        "chat",
        "chat",
    )
    == "My Nova Project",
    "valid title preserved",
)

print()
print("=" * 90)
print("NOVA SESSION TITLE GUARD SMOKE: PASS")
print("=" * 90)