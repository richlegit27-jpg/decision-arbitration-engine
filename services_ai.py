from __future__ import annotations

from typing import Any


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def call_model(
    text: str,
    context: str = "",
    openai_client: Any = None,
    default_model: str = "gpt-4.1-mini",
) -> str:
    prompt = _clean_text(text)
    system_context = _clean_text(context)

    if not prompt:
        return ""

    if openai_client is None:
        return "OpenAI client is not configured."

    try:
        response = openai_client.chat.completions.create(
            model=default_model or "gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_context or "You are Nova."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        if not response or not getattr(response, "choices", None):
            return ""

        message = response.choices[0].message
        if not message:
            return ""

        content = getattr(message, "content", "")
        return _clean_text(content)

    except Exception as exc:
        return f"Model error: {exc}"


def autonomous_loop_refine(
    user_text: str,
    base_answer: str,
    context: str = "",
    call_model_func: Any = None,
) -> str:
    if not callable(call_model_func):
        return _clean_text(base_answer)

    user_text = _clean_text(user_text)
    base_answer = _clean_text(base_answer)
    context = _clean_text(context)

    if not base_answer:
        return ""

    refine_prompt = f"""
Refine this answer for the user.

Rules:
- keep it direct
- keep it clear
- remove fluff
- preserve meaning
- do not turn it into a formal article
- keep it helpful and natural

User request:
{user_text}

Draft answer:
{base_answer}
""".strip()

    improved = _clean_text(call_model_func(refine_prompt, context))
    return improved or base_answer