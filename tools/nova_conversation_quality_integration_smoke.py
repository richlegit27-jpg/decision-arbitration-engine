"""
NOVA CONVERSATION QUALITY INTEGRATION SMOKE

Validates:

Nova response
    ->
conversation quality evaluator
    ->
behavior signal builder
"""

from nova_backend.services.nova_conversation_quality_evaluator import (
    evaluate_conversation,
)

from nova_backend.services.nova_behavior_signal_builder import (
    NovaBehaviorSignalBuilder,
)


def run():
    print("NOVA CONVERSATION QUALITY INTEGRATION SMOKE")
    print("==========================================")

    sample_response = """
    Current Nova Project Brain work:

    Next step:
    create file tools/nova_conversation_quality_integration_smoke.py.

    Run:
    python .\\tools\\nova_conversation_quality_integration_smoke.py

    Then connect conversation quality evaluator,
    behavior memory,
    and upgrade engine.
    """

    result = evaluate_conversation(
        user_message="What should we do next with Nova Project Brain?",
        assistant_message=sample_response,
        previous_context=(
            "Nova Project Brain cleanup and behavior integration."
        ),
    )

    assert result is not None
    print("PASS evaluates response")

    builder = NovaBehaviorSignalBuilder()

    signals = builder.build(
        user_text="What should we do next with Nova Project Brain?",
        assistant_text=sample_response,
        context=(
            "Nova Project Brain cleanup and behavior integration."
        ),
    )

    assert signals is not None
    print("PASS builds behavior signals")

    print(
        "NOVA CONVERSATION QUALITY INTEGRATION SMOKE PASSED"
    )


if __name__ == "__main__":
    run()