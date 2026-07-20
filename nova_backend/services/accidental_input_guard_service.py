from collections import Counter
import re


class AccidentalInputGuardService:

    def _is_accidental_input(self, value) -> bool:
        text = str(value or "")
        compact = "".join(text.split())

        if not compact:
            return True

        lower = compact.lower()

        allowed_short_commands = {
            "k",
            "ok",
            "okay",
            "next",
            "continue",
            "run",
            "runit",
            "stop",
            "cancel",
            "yes",
            "no",
        }

        if lower in allowed_short_commands:
            return False

        if len(compact) < 8:
            return False

        counts = Counter(compact)
        most_common_ratio = counts.most_common(1)[0][1] / max(len(compact), 1)

        alpha_count = sum(1 for ch in compact if ch.isalpha())
        digit_count = sum(1 for ch in compact if ch.isdigit())
        symbol_count = sum(1 for ch in compact if not ch.isalnum())

        symbol_digit_ratio = (digit_count + symbol_count) / max(len(compact), 1)

        if len(compact) >= 12 and most_common_ratio >= 0.75:
            return True

        if len(compact) >= 20 and alpha_count == 0 and symbol_digit_ratio >= 0.90:
            return True

        if len(compact) >= 24 and alpha_count <= 2 and symbol_digit_ratio >= 0.80:
            return True

        repeated_runs = re.search(r"(.)\1{9,}", compact)
        if repeated_runs and len(compact) >= 12:
            return True

        bracket_smash = re.search(r"([\[\]\(\)\{\}=\\\/\|'\-]){8,}", compact)
        if bracket_smash and alpha_count <= 3:
            return True

        return False


    def handle(
        self,
        user_text="",
        session_id="",
        attachments=None,
    ):
        try:
            has_attachments = bool(attachments)

            if not has_attachments and self._is_accidental_input(user_text):
                clean_message = "Looks like that was accidental."

                return {
                    "ok": True,
                    "route": "accidental_input_guard",
                    "mode": "guard",
                    "assistant_text": clean_message,
                    "response": clean_message,
                    "message": clean_message,
                    "content": clean_message,
                    "assistant_message": {
                        "role": "assistant",
                        "text": clean_message,
                        "content": clean_message,
                        "attachments": [],
                        "meta": {
                            "source": "accidental_input_guard",
                            "save_memory": False,
                            "use_memory": False,
                            "skip_title_update": True,
                        },
                    },
                    "session_id": session_id,
                    "active_session_id": session_id,
                    "attachments": [],
                    "skip_post_processing": True,
                    "save_memory": False,
                    "use_memory": False,
                    "skip_title_update": True,
                }

        except Exception:
            pass

        return None