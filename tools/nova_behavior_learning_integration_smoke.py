"""
NOVA BEHAVIOR LEARNING INTEGRATION SMOKE

Validates:

conversation
    ->
quality evaluator
    ->
behavior signal builder
    ->
behavior memory
    ->
upgrade engine
    ->
learning event
"""

from nova_backend.services.nova_conversation_quality_evaluator import (
    evaluate_conversation,
)

from nova_backend.services.nova_behavior_signal_builder import (
    NovaBehaviorSignalBuilder,
)

from nova_backend.services.nova_behavior_memory import (
    NovaBehaviorMemory,
)

from nova_backend.services.nova_behavior_upgrade_engine import (
    analyze_behavior_upgrade,
)

def run():
    print("NOVA BEHAVIOR LEARNING INTEGRATION SMOKE")
    print("========================================")

    user_message = (
        "What should we do next with Nova Project Brain?"
    )

    assistant_message = """
    Current Nova Project Brain work:

    Next step:
    create the behavior learning integration smoke.

    Run:
    python .\\tools\\nova_behavior_learning_integration_smoke.py

    Then connect quality evaluation,
    behavior memory,
    and upgrade engine.
    """

    context = (
        "Nova Project Brain cleanup and behavior integration."
    )

    quality = evaluate_conversation(
        user_message=user_message,
        assistant_message=assistant_message,
        previous_context=context,
    )

    assert quality is not None
    print("PASS evaluates conversation quality")

    builder = NovaBehaviorSignalBuilder()

    signals = builder.build(
        user_text=user_message,
        assistant_text=assistant_message,
        context=context,
    )

    assert signals is not None
    print("PASS builds behavior signals")

    upgrade = analyze_behavior_upgrade(
        quality
    )

    assert upgrade is not None
    print("PASS creates behavior upgrade")

    memory = NovaBehaviorMemory()

    event = memory.record_behavior(
        upgrade
    )

    assert event is not None
    print("PASS stores behavior memory")

    print(
        "NOVA BEHAVIOR LEARNING INTEGRATION SMOKE PASSED"
    )

if __name__ == "__main__":
    run()