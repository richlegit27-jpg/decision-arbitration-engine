from flask import jsonify


class ResponseQualityService:

    def direct_clean_attachment_text_response(
        self,
        text_value,
    ):
        try:
            raw = (
                str(text_value or "")
                .replace("\r\n", "\n")
                .replace("\r", "\n")
                .strip()
            )

            if not raw:
                return raw

            if "Attachment analysis:" not in raw:
                return raw

            lines = [line.strip() for line in raw.split("\n")]
            kept = []
            seen = set()

            for line in lines:
                if not line:
                    continue

                normalized = line.lower().strip()

                if normalized in seen:
                    continue

                seen.add(normalized)

                if normalized.startswith(
                    "this uploaded attachment contains readable text about"
                ):
                    continue

                kept.append(line)

            return "\n".join(kept).strip()

        except Exception:
            return str(text_value or "").strip()

    def replace_weak_backend_reply(
        self,
        user_text,
        result,
    ):
        try:
            if not isinstance(result, dict):
                return result

            assistant = result.get("assistant_message")
            if not isinstance(assistant, dict):
                return result

            text = str(
                assistant.get("text")
                or assistant.get("content")
                or ""
            ).strip()

            normalized = (
                text
                .lower()
                .replace("â€™", "'")
                .replace("`", "'")
                .replace("Â´", "'")
                .replace("Ã¢â‚¬â„¢", "'")
                .replace("Ã£Â¢Ã¢â€šÂ¬Ã¢â€žÂ¢", "'")
                .replace("iÃ£Â¢Ã¢â€šÂ¬Ã¢â€žÂ¢m", "i'm")
                .replace("iÃ¢â‚¬â„¢m", "i'm")
            )

            compact = " ".join(normalized.split())

            weak_hit = (
                compact in {
                    "i'm ready. what are we working on?",
                    "i'm ready. what are we working on",
                    "im ready. what are we working on?",
                    "im ready. what are we working on",
                }
                or (
                    "ready" in compact
                    and "what are we working on" in compact
                )
            )

            if not weak_hit:
                return result

            prompt_lc = str(user_text or "").strip().lower()

            if "life story" in prompt_lc:
                replacement = (
                    "I do not have a personal life story like a human. "
                    "I was built to help you think, build, debug, write, learn, and move faster. "
                    "For Nova, the active phase is frontend polish: clean the mobile UI, remove weak fallback behavior, "
                    "and make the live app match the backend tests that are already passing."
                )
            else:
                replacement = "I'm here. What would you like to work on?"

            assistant["text"] = replacement
            assistant["content"] = replacement

            meta = assistant.get("meta")
            if not isinstance(meta, dict):
                meta = {}

            meta["weak_response_guarded"] = True
            meta["weak_response_original"] = text
            assistant["meta"] = meta

            result["assistant_message"] = assistant

            session = result.get("session")
            if isinstance(session, dict) and isinstance(session.get("messages"), list):
                for msg in reversed(session["messages"]):
                    if (
                        isinstance(msg, dict)
                        and str(msg.get("role") or "").lower() == "assistant"
                    ):
                        msg["text"] = replacement
                        msg["content"] = replacement
                        msg["meta"] = dict(meta)
                        break

            return result

        except Exception:
            return result


    def slim_assistant_payload(
        self,
        text,
        session_id="",
        **extra,
    ):
        payload = {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": str(text or "").strip(),
            },
            "active_session_id": str(session_id or "").strip(),
        }

        for key, value in extra.items():
            if value is not None:
                payload[key] = value

        return jsonify(payload)


    def prevent_bad_exact_pong_response(
        self,
        assistant_text,
        user_text,
    ):
        clean_answer = str(assistant_text or "").strip()
        clean_user = str(user_text or "").strip().lower()

        if clean_answer.lower() != "pong":
            return clean_answer

        allowed_pong_requests = {
            "pong",
            "say pong",
            "say pong only",
            "reply pong",
            "reply with pong",
        }

        if clean_user in allowed_pong_requests:
            return "pong"

        return clean_answer