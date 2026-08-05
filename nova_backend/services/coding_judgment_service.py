def get_coding_judgment_answer(user_text):
    clean = " ".join(
        str(user_text or "").lower().split()
    )

    triggers = (
        "what test should we run before touching code",
        "what tests should we run before touching code",
        "before touching code",
        "before patching",
        "before we patch",
    )

    if not any(
        trigger in clean
        for trigger in triggers
    ):
        return ""

    return (
        "Before touching code, run the smallest checks that prove "
        "the current behavior is safe:\n\n"
        "1. `python -m py_compile` on the Python files you may touch.\n"
        "2. The most relevant focused smoke test.\n"
        "3. `git status --short` before staging or committing."
    )