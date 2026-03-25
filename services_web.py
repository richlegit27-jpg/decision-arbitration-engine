# C:\Users\Owner\nova\services_ai.py

from __future__ import annotations

from typing import Callable


def call_model(
    text: str,
    context: str,
    openai_client,
    default_model: str,
) -> str:
    if not openai_client:
        return "Missing OpenAI key."

    final_input = f"{context}\n\n{text}" if context else text

    response = openai_client.responses.create(
        model=default_model,
        input=final_input,
    )

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    return "No response"


def improve_answer(
    user_text: str,
    answer: str,
    context: str,
    call_model_func: Callable[[str, str], str],
) -> str:
    prompt = f"""
Improve this answer.

User:
{user_text}

Answer:
{answer}

Make it:
- clearer
- more accurate
- more helpful
- tighter

Return only the improved answer.
""".strip()

    try:
        improved = call_model_func(prompt, context)
        return improved if improved else answer
    except Exception:
        return answer


def score_answer(
    user_text: str,
    answer: str,
    call_model_func: Callable[[str, str], str],
) -> float:
    prompt = f"""
Score this answer from 1 to 10.

User:
{user_text}

Answer:
{answer}

Return only a number.
""".strip()

    try:
        raw = call_model_func(prompt, "")
        return float(raw.strip())
    except Exception:
        return 5.0


def autonomous_loop_refine(
    user_text: str,
    base_answer: str,
    context: str,
    call_model_func: Callable[[str, str], str],
) -> str:
    best = base_answer

    for _ in range(2):
        improved = improve_answer(user_text, best, context, call_model_func)
        old_score = score_answer(user_text, best, call_model_func)
        new_score = score_answer(user_text, improved, call_model_func)
        if new_score > old_score:
            best = improved

    return best