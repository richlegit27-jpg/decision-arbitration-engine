"""Provider adapters for canonical Nova tool contracts."""

from __future__ import annotations


def to_openai_responses_tools(definitions: list[dict]) -> list[dict]:
    """Translate provider-neutral definitions to Responses function tools."""
    return [
        {
            "type": "function",
            "name": item["name"],
            "description": item["description"],
            "parameters": item["parameters"],
            "strict": False,
        }
        for item in definitions
        if isinstance(item, dict)
        and item.get("name")
        and isinstance(item.get("parameters"), dict)
    ]


def to_openai_chat_tools(definitions: list[dict]) -> list[dict]:
    """Translate provider-neutral definitions to Chat Completions tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": item["name"],
                "description": item["description"],
                "parameters": item["parameters"],
                "strict": False,
            },
        }
        for item in definitions
        if isinstance(item, dict)
        and item.get("name")
        and isinstance(item.get("parameters"), dict)
    ]
