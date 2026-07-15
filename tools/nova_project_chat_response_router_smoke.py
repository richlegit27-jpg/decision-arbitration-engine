from nova_backend.services.project_chat_response_router_service import (
    normalize_text,
    patch_payload,
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)

    print("PASS", message)


print("=" * 80)
print("NOVA PROJECT CHAT RESPONSE ROUTER SMOKE")
print("=" * 80)


require(
    normalize_text("  Nova   project   state  ")
    == "Nova project state",
    "text normalization works",
)


payload = {}

fixed = patch_payload(
    payload,
    "Current Nova checkpoint is healthy.",
)


require(
    fixed["assistant_message"]["text"]
    == "Current Nova checkpoint is healthy.",
    "project answer injected",
)


require(
    fixed["route"]
    == "project_brain_general_intelligence",
    "route metadata applied",
)


print()
print("=" * 80)
print("NOVA PROJECT CHAT RESPONSE ROUTER SMOKE: PASS")
print("=" * 80)