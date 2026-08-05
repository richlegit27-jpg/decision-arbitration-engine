def is_project_next_question(value):
    clean = (
        str(value or "")
        .strip()
        .lower()
        .replace("?", "'")
        .rstrip("?!.")
    )

    return clean in {
        "what's next",
        "whats next",
        "what is next",
        "what should we do next",
    }


def get_project_next_answer(user_text):
    from nova_backend.services.project_brain_general_intelligence import (
        build_project_brain_general_answer,
    )

    general_answer = build_project_brain_general_answer(
        user_text
    )

    if isinstance(general_answer, dict):
        return str(
            general_answer.get("content")
            or general_answer.get("text")
            or general_answer.get("answer")
            or ""
        ).strip()

    return str(
        getattr(
            general_answer,
            "text",
            general_answer,
        )
        or ""
    ).strip()