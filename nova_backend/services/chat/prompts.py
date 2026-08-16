def _build_chat_input(
    self,
    user_text: str,
    decision: dict,
    session_id: str = "",
) -> str:
    user_text = self.safe_str(user_text)

    memory_items = self._rank_memory_context(
        user_text=user_text,
        limit=int(
            decision.get("memory_limit")
            or self.memory_limit
        ),
        session_id=session_id,
    )

    memory_block = self._format_memory_context(
        memory_items[:3]
    )

    sections = []

    if memory_block:
        sections.append(
            "Relevant memory:\n"
            f"{memory_block}"
        )

    execution_state = decision.get(
        "execution_state"
    )

    if isinstance(
        execution_state,
        dict,
    ) and execution_state:

        sections.append(
            "Execution plan:\n"
            f"{execution_state}"
        )

    brain_plan = decision.get(
        "brain_plan"
    )

    if isinstance(
        brain_plan,
        dict,
    ) and brain_plan:

        sections.append(
            "Planner context:\n"
            f"{brain_plan}"
        )

    try:
        session = self._get_session_payload(
            session_id
        )

        continuity_context = (
            self._build_continuity_context(
                session=session
            )
        )

        print(
            "[CONTINUITY TEST]",
            repr(continuity_context)[:1000],
        )

        if continuity_context:
            sections.append(
                continuity_context
            )

    except Exception:
        pass

    if not sections:
        return user_text

    return (
        "\n\n".join(sections)
        + "\n\nInstructions:\n"
        + "- Answer clearly and directly.\n"
        + "- Use relevant memory when it helps.\n"
        + "- Do not claim missing context if the answer is already available.\n\n"
        + "User message:\n"
        + user_text
    )