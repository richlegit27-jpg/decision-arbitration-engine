from nova_backend.services.project_brain_decision_log_route_contract import (
    is_decision_log_question,
    extract_user_text,
    build_decision_log_api_payload,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


print("=" * 80)
print("NOVA PROJECT BRAIN DECISION LOG ROUTE CONTRACT SMOKE")
print("=" * 80)


payload = {
    "message": "show me the decision log"
}

text = extract_user_text(payload)

require(
    text == "show me the decision log",
    "user text extraction works",
)

require(
    is_decision_log_question(text),
    "decision log question classifier works",
)

result = build_decision_log_api_payload(limit=8)

require(
    isinstance(result, dict),
    "decision log payload returns dict",
)

require(
    "assistant_message" in result,
    "decision log payload contains assistant message",
)

print()
print("=" * 80)
print("NOVA PROJECT BRAIN DECISION LOG ROUTE CONTRACT SMOKE PASSED")
print("=" * 80)