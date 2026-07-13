from __future__ import annotations


def apply_weak_response_guard(
    user_text: str,
    result: dict,
) -> dict:
    try:
        if not isinstance(result, dict):
            return result

        assistant = result.get("assistant_message")

        if not isinstance(assistant, dict):
            return result

        current_text = str(
            assistant.get("text")
            or assistant.get("content")
            or ""
        ).strip()

        current_compact = " ".join(
            current_text
            .lower()
            .replace("â€™", "'")
            .replace("Ã¢â‚¬â„¢", "'")
            .replace("Ã£Â¢Ã¢â€šÂ¬Ã¢â€žÂ¢", "'")
            .replace("iÃ£Â¢Ã¢â€šÂ¬Ã¢â€žÂ¢m", "i'm")
            .replace("iÃ¢â‚¬â„¢m", "i'm")
            .split()
        )

        if (
            "ready" in current_compact
            and "what are we working on" in current_compact
        ):
            replacement = (
                "I do not have a personal life story like a human. "
                "I was built to help you think, build, debug, write, learn, and move faster. "
                "For Nova, the active phase is frontend polish: clean the mobile UI, "
                "remove weak fallback behavior, and make the live app match "
                "the backend tests that are already passing."
            )

            assistant["text"] = replacement
            assistant["content"] = replacement

            meta = assistant.get("meta")

            if not isinstance(meta, dict):
                meta = {}

            meta["weak_response_guarded"] = True
            meta["weak_response_original"] = current_text

            assistant["meta"] = meta
            result["assistant_message"] = assistant

        return result

    except Exception:
        return result