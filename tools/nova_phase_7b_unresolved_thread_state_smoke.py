from __future__ import annotations

from nova_backend.services.conversation_state_brain import (
    ConversationStateBrain,
)


def require(
    condition: bool,
    label: str,
    detail="",
) -> None:
    if not condition:
        raise AssertionError(
            (
                label
                +
                (
                    " DETAIL: "
                    + repr(
                        detail
                    )
                    if detail != ""
                    else ""
                )
            )
        )

    print(
        "PASS",
        label,
    )


def main() -> None:
    print(
        "NOVA PHASE 7B UNRESOLVED THREAD STATE SMOKE"
    )
    print(
        "=" * 72
    )

    brain = ConversationStateBrain()

    history = [
        {
            "role": "user",
            "text": (
                "we are fixing Nova conversation state"
            ),
        },
        {
            "role": "assistant",
            "text": (
                "We are working on conversation state."
            ),
        },
        {
            "role": "user",
            "text": (
                "after this let's fix attachments"
            ),
        },
        {
            "role": "assistant",
            "text": (
                "Okay, we can return to attachments after this."
            ),
        },
    ]

    state = brain.build_state(
        history,
        "why did the state brain matter",
    )

    require(
        (
            state.unresolved_threads
            ==
            (
                "fix attachments",
            )
        ),
        "explicit deferred thread persists",
        state.unresolved_threads,
    )

    require(
        (
            state.active_topic
            ==
            "why did the state brain matter"
        ),
        "deferred thread does not hijack current topic",
        state.active_topic,
    )

    require(
        (
            state.current_intent
            ==
            "new_or_explicit_topic"
        ),
        "current substantive question keeps current intent",
        state.current_intent,
    )

    context = state.build_context_block()

    require(
        (
            "There are explicitly deferred conversation threads"
            in context
        ),
        "unrelated context keeps hidden-thread warning",
        context,
    )

    require(
        (
            "fix attachments"
            not in context
        ),
        "unrelated context hides exact deferred thread",
        context,
    )

    require(
        (
            "Do not name, summarize, mention, hint at, or use"
            in context
        ),
        "unrelated context contains strong quiet rule",
        context,
    )

    recall_state = brain.build_state(
        history,
        (
            "what was the other thing "
            "we still needed to do"
        ),
    )

    require(
        (
            recall_state.current_intent
            ==
            "resume_unresolved_thread"
        ),
        "explicit unresolved-thread recall detected",
        recall_state.current_intent,
    )

    recall_context = (
        recall_state.build_context_block()
    )

    require(
        "answer from this unresolved thread list only"
        in recall_context.lower(),
        "unresolved-thread recall gets resolution instruction",
        recall_context,
    )

    multiple_history = [
        {
            "role": "user",
            "text": (
                "we still need to finish billing tiers"
            ),
        },
        {
            "role": "assistant",
            "text": "Okay.",
        },
        {
            "role": "user",
            "text": (
                "after this let's clean up mobile sessions"
            ),
        },
        {
            "role": "assistant",
            "text": "Okay.",
        },
    ]

    multiple_state = brain.build_state(
        multiple_history,
        "tell me more about conversation state",
    )

    require(
        (
            multiple_state.unresolved_threads
            ==
            (
                "finish billing tiers",
                "clean up mobile sessions",
            )
        ),
        "multiple explicit threads remain ordered",
        multiple_state.unresolved_threads,
    )

    resolution_history = (
        multiple_history
        +
        [
            {
                "role": "user",
                "text": (
                    "we're done with billing tiers"
                ),
            },
            {
                "role": "assistant",
                "text": "Good.",
            },
        ]
    )

    resolution_state = brain.build_state(
        resolution_history,
        "what's still open",
    )

    require(
        (
            resolution_state.unresolved_threads
            ==
            (
                "clean up mobile sessions",
            )
        ),
        "specific completed thread is removed",
        resolution_state.unresolved_threads,
    )

    require(
        (
            resolution_state.current_intent
            ==
            "resume_unresolved_thread"
        ),
        "what is still open resumes unresolved-thread intent",
        resolution_state.current_intent,
    )

    generic_resolution_history = (
        history
        +
        [
            {
                "role": "user",
                "text": "that's done",
            },
        ]
    )

    generic_resolution_state = brain.build_state(
        generic_resolution_history,
        "tell me about memory",
    )

    require(
        (
            generic_resolution_state.unresolved_threads
            ==
            ()
        ),
        "generic completion resolves most recent thread",
        generic_resolution_state.unresolved_threads,
    )

    ordinary_history = [
        {
            "role": "user",
            "text": "what is Python",
        },
        {
            "role": "assistant",
            "text": "Python is a programming language.",
        },
        {
            "role": "user",
            "text": "how does Flask work",
        },
    ]

    ordinary_state = brain.build_state(
        ordinary_history,
        "tell me more",
    )

    require(
        (
            ordinary_state.unresolved_threads
            ==
            ()
        ),
        "ordinary questions do not become fake unresolved todos",
        ordinary_state.unresolved_threads,
    )

    require(
        ordinary_state.short_followup,
        "ordinary short follow-up behavior remains intact",
    )

    print()
    print(
        "=" * 72
    )
    print(
        "NOVA PHASE 7B UNRESOLVED THREAD STATE: REAL PASS"
    )
    print(
        "=" * 72
    )


if __name__ == "__main__":
    main()
