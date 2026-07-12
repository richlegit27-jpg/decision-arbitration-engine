from __future__ import annotations

import ast
from pathlib import Path

from nova_backend.services.chat_service import (
    ChatService,
)


ROOT = Path(
    r"C:\Users\Owner\nova"
)


CHAT_PATH = (
    ROOT
    /
    "nova_backend"
    /
    "services"
    /
    "chat_service.py"
)


APP_PATH = (
    ROOT
    /
    "app.py"
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
                    + repr(detail)
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
        "NOVA PHASE 7A LIVE CONVERSATION STATE WIRING SMOKE"
    )

    print(
        "=" * 72
    )

    service = ChatService.__new__(
        ChatService
    )

    service._build_system_prompt = (
        lambda decision=None:
        "SYSTEM"
    )

    service._build_continuity_context = (
        lambda session=None:
        "CONTINUITY"
    )

    service._find_latest_execution_artifact = (
        lambda session_id="":
        None
    )

    session = {
        "id": "phase_7a_wiring_smoke",
        "messages": [
            {
                "role": "user",
                "text": (
                    "what are we working on now"
                ),
            },
            {
                "role": "assistant",
                "text": (
                    "Project Brain Command Center: "
                    "Best Move: conversation quality field test"
                ),
            },
            {
                "role": "user",
                "text": (
                    "don't give me project command center shit "
                    "just tell me normally"
                ),
            },
        ],
    }

    messages = service._compose_model_messages(
        (
            "so basically are we done with "
            "the self improvement stuff now"
        ),
        session=session,
        decision={
            "route": "general_chat",
        },
        memory_context=(
            "Older saved Project Brain memory."
        ),
    )

    require(
        isinstance(
            messages,
            list,
        ),
        "model messages return list",
    )

    require(
        len(
            messages
        )
        >=
        5,
        "model messages contain layered context",
        len(
            messages
        ),
    )

    system_contents = [
        str(
            message.get(
                "content"
            )
            or ""
        )
        for message in messages
        if (
            isinstance(
                message,
                dict,
            )
            and message.get(
                "role"
            )
            ==
            "system"
        )
    ]

    state_indexes = [
        index
        for index, content in enumerate(
            system_contents
        )
        if (
            "[LIVE CONVERSATION STATE]"
            in content
        )
    ]

    require(
        len(
            state_indexes
        )
        ==
        1,
        "one live conversation state system block",
        state_indexes,
    )

    state_index = state_indexes[0]

    continuity_index = (
        system_contents.index(
            "CONTINUITY"
        )
    )

    require(
        state_index
        <
        continuity_index,
        "live state precedes continuity",
        (
            state_index,
            continuity_index,
        ),
    )

    live_state = system_contents[
        state_index
    ]

    require(
        (
            "Response mode: normal"
            in live_state
        ),
        "normal response mode reaches model path",
        live_state,
    )

    require(
        (
            "Do not answer with Project Brain Command Center"
            in live_state
        ),
        "Command Center rejection reaches model path",
        live_state,
    )

    require(
        (
            "Latest correction:"
            in live_state
        ),
        "latest correction reaches model path",
        live_state,
    )

    memory_blocks = [
        content
        for content in system_contents
        if (
            "Older saved memory."
            in content
        )
    ]

    require(
        len(
            memory_blocks
        )
        ==
        1,
        "older memory block remains present",
        memory_blocks,
    )

    require(
        (
            "Lower priority than the current user message"
            in memory_blocks[0]
        ),
        "older memory explicitly lower priority",
        memory_blocks[0],
    )

    user_messages = [
        message
        for message in messages
        if (
            isinstance(
                message,
                dict,
            )
            and message.get(
                "role"
            )
            ==
            "user"
        )
    ]

    require(
        len(
            user_messages
        )
        ==
        1,
        "one current user model message",
        user_messages,
    )

    require(
        (
            user_messages[0].get(
                "content"
            )
            ==
            (
                "so basically are we done with "
                "the self improvement stuff now"
            )
        ),
        "current user message preserved exactly",
        user_messages[0],
    )

    app_text = APP_PATH.read_text(
        encoding="utf-8-sig"
    )

    app_tree = ast.parse(
        app_text
    )

    owners = [
        node
        for node in ast.walk(
            app_tree
        )
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name
            ==
            "_nova_project_brain_general_intelligence_priority_20260701"
        )
    ]

    require(
        len(
            owners
        )
        ==
        1,
        "Project Brain priority owner remains unique",
        len(
            owners
        ),
    )

    owner = owners[0]

    app_lines = app_text.splitlines()

    owner_text = "\n".join(
        app_lines[
            owner.lineno
            -
            1
            :
            owner.end_lineno
        ]
    )

    require(
        (
            "NOVA_PHASE_7A_CONVERSATION_STATE_PROJECT_BRAIN_BYPASS_20260711"
            in owner_text
        ),
        "Phase 7A bypass lives inside existing priority owner",
    )

    require(
        (
            "conversation_state_brain.build_state"
            in owner_text
        ),
        "Project Brain owner builds live conversation state",
    )

    require(
        (
            "suppress_project_brain_contract"
            in owner_text
        ),
        "Project Brain owner reads suppression signal",
    )

    require(
        (
            app_text.count(
                "# NOVA_PHASE_7A_CONVERSATION_STATE_PROJECT_BRAIN_BYPASS_20260711"
            )
            ==
            1
        ),
        "Phase 7A Project Brain bypass marker unique",
    )

    chat_text = CHAT_PATH.read_text(
        encoding="utf-8-sig"
    )

    require(
        (
            chat_text.count(
                "conversation_state_brain.build_state"
            )
            ==
            1
        ),
        "model-message state wire unique",
        chat_text.count(
            "conversation_state_brain.build_state"
        ),
    )

    print()

    print(
        "=" * 72
    )

    print(
        "NOVA PHASE 7A LIVE CONVERSATION STATE WIRING: REAL PASS"
    )

    print(
        "=" * 72
    )


if __name__ == "__main__":
    main()
