from nova_backend.services.project_chat_response_router_service import (
    normalize_text,
    build_project_answer,
    apply_project_route,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)

    print("PASS", message)


print("=" * 80)
print("NOVA PROJECT CHAT LIVE BRAIN INTEGRATION SMOKE")
print("=" * 80)


text = normalize_text(
    "   what is next for nova?   "
)

require(
    text == "what is next for nova?",
    "text normalization works",
)


reply = build_project_answer(
    "what now?"
)

require(
    reply is not None,
    "project brain answer generated",
)


payload = {}

result = apply_project_route(
    payload,
    reply,
)


require(
    isinstance(result, dict),
    "payload returned",
)


require(
    result.get("response"),
    "response written",
)


require(
    result.get("route") is not None,
    "route metadata applied",
)


print()
print("=" * 80)
print("NOVA PROJECT CHAT LIVE BRAIN INTEGRATION SMOKE PASSED")
print("=" * 80)