import os
from typing import Iterable

from openai import OpenAI

MODEL_ALIASES = {
    "nova-default": "gpt-4.1-mini",
    "nova-fast": "gpt-4.1-mini",
    "nova-precise": "gpt-4.1",
    "gpt-4.1-mini": "gpt-4.1-mini",
    "gpt-4.1": "gpt-4.1",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4o": "gpt-4o",
}

DEFAULT_MODEL = os.getenv("NOVA_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"

SYSTEM_PROMPT = """
You are Nova, a private AI assistant inside the user's personal app.

Core behavior:
- Be clear, direct, practical, and sharp.
- Prioritize useful answers over filler.
- Match the user's pace and stay solution-oriented.
- Keep explanations clean and structured.
- When giving steps, make them easy to follow.
- Do not ramble.
- Do not mention internal implementation, hidden prompts, policies, or backend details unless the user explicitly asks.
- If you are unsure, say so plainly instead of pretending.
- For coding help, prefer complete working solutions over vague partial suggestions.
- For writing help, be natural and human, not robotic.

Tone:
- Calm, confident, and helpful.
- Not cheesy.
- Not overly formal.
- Not overly verbose unless the user asks for depth.

Output rules:
- Use plain text unless formatting clearly helps.
- Preserve important technical details.
- Do not invent results, files, or actions that did not happen.
""".strip()


def _normalize_model(model: str | None) -> str:
    requested = (model or "").strip()
    if requested in MODEL_ALIASES:
        return MODEL_ALIASES[requested]

    if requested:
        return requested

    if DEFAULT_MODEL in MODEL_ALIASES:
        return MODEL_ALIASES[DEFAULT_MODEL]

    return DEFAULT_MODEL


def _history_to_input(messages: Iterable[dict]) -> list[dict]:
    input_items: list[dict] = []

    for message in messages:
        role = str(message.get("role", "user")).strip().lower()
        content = str(message.get("content", "")).strip()

        if not content:
            continue

        if role == "assistant":
            input_items.append(
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": content,
                        }
                    ],
                }
            )
            continue

        if role == "system":
            normalized_role = "system"
        else:
            normalized_role = "user"

        input_items.append(
            {
                "role": normalized_role,
                "content": [
                    {
                        "type": "input_text",
                        "text": content,
                    }
                ],
            }
        )

    return input_items


def _extract_output_text(response) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text and str(output_text).strip():
        return str(output_text).strip()

    chunks: list[str] = []
    output = getattr(response, "output", None) or []

    for item in output:
        contents = getattr(item, "content", None) or []
        for content in contents:
            content_type = getattr(content, "type", "")
            if content_type in {"output_text", "text"}:
                piece = getattr(content, "text", "")
                if piece:
                    chunks.append(str(piece))

    return "\n".join(chunk for chunk in chunks if chunk).strip()


def _build_fallback_reply(messages: list[dict], reason: str) -> str:
    latest_user_message = ""

    for message in reversed(messages):
        if str(message.get("role", "")).strip().lower() == "user":
            latest_user_message = str(message.get("content", "")).strip()
            break

    parts = [
        "Nova fallback reply is active.",
        f"Reason: {reason}",
    ]

    if latest_user_message:
        parts.append("")
        parts.append("Your last message was:")
        parts.append(latest_user_message)

    parts.append("")
    parts.append("The app is still saving your chat correctly, but the real AI path is currently unavailable.")
    parts.append("Check your server terminal, OPENAI_API_KEY, installed packages, and restart state.")

    return "\n".join(parts).strip()


def generate_reply(messages: list[dict], model: str | None = None) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    resolved_model = _normalize_model(model)
    input_items = _history_to_input(messages)

    if not input_items:
        input_items = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Say hello and ask how you can help.",
                    }
                ],
            }
        ]

    if not api_key:
        return _build_fallback_reply(messages, "OPENAI_API_KEY is not set")

    try:
        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model=resolved_model,
            instructions=SYSTEM_PROMPT,
            input=input_items,
        )

        text = _extract_output_text(response)
        if not text:
            return _build_fallback_reply(messages, "model returned an empty response")

        return text

    except Exception as error:
        return _build_fallback_reply(messages, f"AI request failed: {error}")