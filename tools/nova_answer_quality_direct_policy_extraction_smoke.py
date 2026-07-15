from nova_backend.services.answer_quality_direct_policy_service import (
    get_direct_policy_answer,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


CASES = [
    (
        "what is the difference between memory and execution in nova",
        [
            "Memory is what Nova knows",
            "Execution is what Nova does",
        ],
    ),
    (
        "why should we not patch blindly right now",
        [
            "Do not patch blindly",
            "smoke-backed patches keep the project stable",
        ],
    ),
]


print("=" * 80)
print("NOVA ANSWER QUALITY DIRECT POLICY EXTRACTION SMOKE")
print("=" * 80)


for question, expected in CASES:
    answer = get_direct_policy_answer(question)

    require(answer is not None, f"missing answer: {question}")

    for signal in expected:
        require(
            signal in answer,
            f"missing signal {signal}: {question}",
        )

    print("PASS:", question)


print()
print("NOVA ANSWER QUALITY DIRECT POLICY EXTRACTION SMOKE PASSED")