"""
NOVA CONVERSATION QUALITY FIELD TEST

Purpose:
Validate that Nova stays aligned, concrete, and operational
during realistic conversation flows.
"""

from dataclasses import dataclass


@dataclass
class QualityCase:
    name: str
    question: str
    expected_signals: list[str]
    forbidden_signals: list[str]


CASES = [
    QualityCase(
        name="thread continuity",
        question="What should we do next with Nova Project Brain?",
        expected_signals=[
            "Project Brain",
            "next",
            "behavior",
        ],
        forbidden_signals=[
            "start over",
            "generic advice",
        ],
    ),

QualityCase(
    name="latest correction priority",
    question=(
        "The priority changed. "
        "The active work is behavior integration now."
    ),
    expected_signals=[
        "behavior",
        "integration",
    ],
    forbidden_signals=[],
),

    QualityCase(
        name="operational answer",
        question="What is the next useful action?",
        expected_signals=[
            "file",
            "test",
            "command",
        ],
        forbidden_signals=[
            "improve the system",
            "keep working",
        ],
    ),
    QualityCase(
        name="avoid filler",
        question="Give me the next step.",
        expected_signals=[
            "next",
        ],
        forbidden_signals=[
            "great question",
            "exciting journey",
            "let's explore",
        ],
    ),
]


def evaluate_answer(answer: str, case: QualityCase):
    text = answer.lower()

    missing = [
        item
        for item in case.expected_signals
        if item.lower() not in text
    ]

    forbidden = [
        item
        for item in case.forbidden_signals
        if item.lower() in text
    ]

    return {
        "pass": not missing and not forbidden,
        "missing": missing,
        "forbidden": forbidden,
    }

def run():
    print("NOVA CONVERSATION QUALITY FIELD TEST")
    print("====================================")

    score = 0

    sample_answer = """
    Current Nova Project Brain work:

Latest correction:
the active priority is behavior integration.

    Next step:
    create file tools/nova_conversation_quality_field_test.py.

    Run this command:

    python .\\tools\\nova_conversation_quality_field_test.py

    Then connect:
    conversation quality evaluator ->
    behavior integration ->
    behavior memory ->
    upgrade engine.

    This keeps Project Brain continuity while improving Nova behavior quality.
    """

    for case in CASES:
        result = evaluate_answer(sample_answer, case)

        if result["pass"]:
            score += 1
            print("PASS", case.name)
        else:
            print("FAIL", case.name)
            print(" missing:", result["missing"])
            print(" forbidden:", result["forbidden"])

    print()
    print(
        f"NOVA CONVERSATION QUALITY SCORE: "
        f"{score}/{len(CASES)}"
    )


if __name__ == "__main__":
    run()