import time

from nova_phase_7c_reference_resolution_behavior_smoke import (
    chat,
    require,
)


def main():
    print(
        "NOVA PHASE 7C ADVANCED REFERENCE MUTATION SMOKE"
    )
    print("=" * 90)

    session_id = (
        "phase_7c_advanced_reference_"
        + str(int(time.time()))
    )

    print("SESSION:", session_id)

    setup = chat(
        session_id,
        (
            "During this conversation, use three launch candidates in this exact order. "
            "First: improve voice controls. "
            "Second: add session search. "
            "Third: tighten billing alerts. "
            "Do not choose one yet."
        ),
    )

    require(
        "saved to memory" not in setup,
        "reference test setup remains session-scoped",
        setup,
    )

    middle = chat(
        session_id,
        "Which candidate was in the middle?",
    )

    require(
        "session" in middle
        and "search" in middle,
        "indirect middle reference resolves second candidate",
        middle,
    )

    side_topic = chat(
        session_id,
        (
            "Switch topics briefly: why do keyboard shortcuts "
            "help power users?"
        ),
    )

    require(
        "shortcut" in side_topic
        or "keyboard" in side_topic,
        "side topic receives relevant answer",
        side_topic,
    )

    previous_last = chat(
        session_id,
        (
            "Before that keyboard-shortcut side topic, "
            "what was the last candidate in the three-item list?"
        ),
    )

    require(
        "billing" in previous_last
        and "alert" in previous_last,
        "cross-topic last-item reference resolves third candidate",
        previous_last,
    )

    between = chat(
        session_id,
        (
            "Which candidate was between voice controls "
            "and billing alerts?"
        ),
    )

    require(
        "session" in between
        and "search" in between,
        "relational reference resolves middle candidate",
        between,
    )

    reordered = chat(
        session_id,
        (
            "Swap the first and third candidates, "
            "then state the new order."
        ),
    )

    require(
        "billing" in reordered
        and "session" in reordered
        and "voice" in reordered,
        "candidate-list mutation preserves all three choices",
        reordered,
    )

    new_first = chat(
        session_id,
        "After that swap, which candidate is first now?",
    )

    require(
        "billing" in new_first
        and "alert" in new_first,
        "reference resolves against mutated ordering",
        new_first,
    )

    remaining = chat(
        session_id,
        (
            "Remove the middle candidate from that reordered list. "
            "Which two candidates remain?"
        ),
    )

    require(
        "billing" in remaining
        and "voice" in remaining,
        "remaining references survive candidate removal",
        remaining,
    )

    restored = chat(
        session_id,
        (
            "Restore the removed candidate. "
            "When I say 'that restored option,' what do I mean?"
        ),
    )

    require(
        "session" in restored
        and "search" in restored,
        "pronoun resolves restored candidate",
        restored,
    )

    ordinary = chat(
        session_id,
        "Separate question: what planet is known as the Red Planet?",
    )

    require(
        "mars" in ordinary,
        "ordinary knowledge question remains isolated",
        ordinary,
    )

    print()
    print("=" * 90)
    print(
        "NOVA PHASE 7C ADVANCED REFERENCE MUTATION: REAL PASS"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()
