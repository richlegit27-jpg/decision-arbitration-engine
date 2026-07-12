from __future__ import annotations

from nova_backend.services.conversation_state_brain import (
    ConversationStateBrain,
)


def require(
    condition: bool,
    label: str,
) -> None:
    if not condition:
        raise AssertionError(label)

    print(
        "PASS",
        label,
    )


def main() -> None:
    print(
        "NOVA PHASE 7A CONVERSATION STATE BRAIN SMOKE"
    )
    print(
        "=" * 60
    )

    brain = ConversationStateBrain()

    state = brain.build_state(
        [],
        "hey nova",
    )

    require(
        state.response_mode == "default",
        "greeting keeps default response mode",
    )

    require(
        not state.suppress_project_brain_contract,
        "greeting does not suppress project brain contract",
    )

    history = [
        {
            "role": "user",
            "text": (
                "i'm testing if you can keep following "
                "what i'm saying"
            ),
        },
        {
            "role": "assistant",
            "text": (
                "You are testing whether I can keep "
                "the conversation straight."
            ),
        },
        {
            "role": "user",
            "text": "what are we working on now",
        },
        {
            "role": "assistant",
            "text": (
                "Project Brain Command Center: "
                "Best Move: Nova Conversation Quality Field Test v1."
            ),
        },
        {
            "role": "user",
            "text": (
                "don't give me project command center shit "
                "just tell me normally"
            ),
        },
    ]

    state = brain.build_state(
        history,
        (
            "so basically are we done with "
            "the self improvement stuff now"
        ),
    )

    require(
        state.response_mode == "normal",
        "latest normal-answer instruction persists",
    )

    require(
        state.suppress_project_brain_contract,
        "project command center rejection persists",
    )

    require(
        (
            state.latest_correction
            == (
                "don't give me project command center shit "
                "just tell me normally"
            )
        ),
        "latest user correction captured",
    )

    require(
        (
            state.latest_user_instruction
            == (
                "don't give me project command center shit "
                "just tell me normally"
            )
        ),
        "latest conversation instruction captured",
    )

    require(
        (
            state.active_topic
            == (
                "so basically are we done with "
                "the self improvement stuff now"
            )
        ),
        "current substantive topic becomes active topic",
    )

    continuation_history = [
        {
            "role": "user",
            "text": "what did we just fix",
        },
        {
            "role": "assistant",
            "text": (
                "We fixed and locked the Project Brain "
                "regression path."
            ),
        },
    ]

    state = brain.build_state(
        continuation_history,
        "why did that matter",
    )

    require(
        state.short_followup,
        "why did that matter is short followup",
    )

    require(
        state.active_topic == "what did we just fix",
        "short followup inherits recent active topic",
    )

    correction_history = [
        {
            "role": "user",
            "text": "keep it brief",
        },
        {
            "role": "assistant",
            "text": "Okay.",
        },
        {
            "role": "user",
            "text": "actually just tell me normally",
        },
    ]

    state = brain.build_state(
        correction_history,
        "what next",
    )

    require(
        state.response_mode == "normal",
        "latest response mode correction wins",
    )

    context_block = state.build_context_block()

    require(
        "[LIVE CONVERSATION STATE]" in context_block,
        "context block has state header",
    )

    require(
        "Latest user instruction:" in context_block,
        "context block exposes latest instruction",
    )

    require(
        (
            "latest user correction overrides"
            in context_block.lower()
        ),
        "context block declares correction priority",
    )

    recall_history = [
        {
            "role": "user",
            "text": "we are building Nova conversation state",
        },
        {
            "role": "assistant",
            "text": "We are starting Phase 7A.",
        },
    ]

    state = brain.build_state(
        recall_history,
        "what were we talking about",
    )

    require(
        state.recall_requested,
        "conversation recall request detected",
    )

    require(
        (
            state.active_topic
            == "we are building Nova conversation state"
        ),
        "conversation recall resolves recent topic",
    )

    print()
    print(
        "=" * 60
    )
    print(
        "NOVA PHASE 7A CONVERSATION STATE BRAIN: REAL PASS"
    )
    print(
        "=" * 60
    )


if __name__ == "__main__":
    main()
