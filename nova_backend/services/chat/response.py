class ChatResponseHandler:

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def extract_response_text(self, resp) -> str:
        try:
            output_text = getattr(resp, "output_text", None)

            if output_text:
                return str(output_text).strip()

        except Exception:
            pass

        try:
            data = (
                resp.model_dump()
                if hasattr(resp, "model_dump")
                else {}
            )

        except Exception:
            data = {}

        if isinstance(data, dict):

            text_parts = []

            for item in data.get("output") or []:

                if not isinstance(item, dict):
                    continue

                for part in item.get("content") or []:

                    if not isinstance(part, dict):
                        continue

                    text_value = (
                        part.get("text")
                        or part.get("output_text")
                    )

                    if text_value:
                        text_parts.append(
                            str(text_value)
                        )

            if text_parts:
                return "\n".join(
                    text_parts
                ).strip()

            for key in (
                "text",
                "content",
                "message",
            ):
                value = data.get(key)

                if value:
                    return str(value).strip()

        try:
            if hasattr(resp, "output"):

                for item in resp.output:

                    content = getattr(
                        item,
                        "content",
                        [],
                    )

                    for part in content:

                        text_value = getattr(
                            part,
                            "text",
                            None,
                        )

                        if text_value:
                            return str(
                                text_value
                            ).strip()

        except Exception:
            pass

        return ""

    def _clean_final_response_text(
        self,
        text: str,
        response_policy=None,
        mission_mode: str = "",
        user_text: str = "",
    ) -> str:
        text = self.safe_str(text).strip()
        user_text_raw = self.safe_str(user_text).strip()
        user_text_lc = user_text_raw.lower()
        response_policy = response_policy if isinstance(response_policy, dict) else {}

        exec_debug("CLEAN_FINAL_HIT:", user_text_raw)

        # === SMFF HARD OVERRIDE FOR CODE HELP ===
        try:
            memory_text = str(
                self.memory_context_service.format_memory_context(
                    getattr(self, "_last_used_memory_items", [])
                )
            ).lower()
        except Exception:
            memory_text = ""

        smff_active = any(
            x in memory_text
            for x in [
                "smff",
                "full-file",
                "full file",
                "full code",
                "powershell",
                "direct",
                "no fluff",
            ]
        )

        code_intent = any(
            x in user_text_lc
            for x in [
                "fix",
                "function",
                "code",
                "python",
                "flask",
                "route",
                "error",
                "traceback",
                "syntaxerror",
                "indentationerror",
                "attributeerror",
                ".py",
                ".js",
                ".html",
                ".css",
            ]
        )

        asks_alternatives = any(
            x in user_text_lc
            for x in [
                "alternative",
                "alternatives",
                "another way",
                "different way",
                "options",
                "other answer",
                "other answers",
                "different answer",
            ]
        )

        if smff_active and code_intent and not asks_alternatives:
            return (
                "Send full file path + full broken code.\n"
                "IÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ll return the full replacement, cleanly indented.\n\n"
                "PowerShell test:\n"
                "python -m py_compile <file_path>"
            )

        if smff_active and code_intent and asks_alternatives:
            return (
                "Option A ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â safest:\n"
                "Send the full file path + full broken file. IÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ll return the full-file replacement.\n\n"
                "Option B ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â faster:\n"
                "Send the full function only. IÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ll return the full function replacement.\n\n"
                "Option C ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â debug-only:\n"
                "Run this and send the exact error:\n"
                "python -m py_compile <file_path>"
            )

        filler_phrases = [
            "if you want",
            "i can also",
            "would you like",
            "i can give you",
            "i can help with",
            "more realistic",
            "more cartoon",
            "wallpaper format",
            "transparent background",
            "transparent background version",
        ]
        cleaned_lines = []

        for line in text.splitlines():
            lowered = line.strip().lower()

            if any(phrase in lowered for phrase in filler_phrases):
                break

            cleaned_lines.append(line)

        text = "\n".join(cleaned_lines).strip()

        if not text:
            return ""

        if "Generated image:" in text:
            return text

        # === PREVENT DUPLICATE SMFF INTAKE ===
        if (
            "Send the full function and file path." in text
            and "full replacement block" in text
        ):
            return (
                "Send the full function and file path.\n"
                "IÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ll return the full replacement block, cleanly indented."
            )

        kill_phrases = [
            "i can help",
            "let me know",
            "feel free",
            "hopefully",
            "in conclusion",
            "overall",
            "you might want",
            "one option is",
        ]

        lines = []
        for line in text.split("\n"):
            clean = line.strip()
            lc = clean.lower()

            if not clean:
                continue

            if any(p in lc for p in kill_phrases):
                continue

            lines.append(clean)

        text = "\n".join(lines).strip()

        bad_endings = [
            "Example:",
            "HereÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢s how:",
            "Here's how:",
            "This prints:",
            "That prints:",
            "Output:",
            "Result:",
        ]

        for bad in bad_endings:
            if text.endswith(bad):
                text = text[: -len(bad)].strip()

        lines = [line.rstrip() for line in text.splitlines() if line.strip()]

        while lines:
            last = lines[-1].strip()
            last_lc = last.lower()

            if (
                last.endswith(":")
                or last.endswith("-")
                or last_lc
                in {"example", "output", "result", "hereÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢s how", "here's how"}
            ):
                lines.pop()
                continue

            break

        text = "\n".join(lines).strip()

        if user_text_lc.startswith("latest"):
            useful = [line for line in text.split("\n") if line.strip()]
            text = "\n".join(useful[:6]).strip() or text

        if any(
            line.strip().startswith(("1.", "2.", "3.", "4.", "5."))
            for line in text.split("\n")
        ):
            text = "\n".join(text.split("\n")[:7]).strip()

        if response_policy.get("answer_length") == "short":
            text = "\n".join(text.split("\n")[:6]).strip()

        if response_policy.get("user_frustrated"):
            text = text.replace("please", "").replace("kindly", "").strip()

        # =============================
        # ANSWER PUNCH
        # =============================

        punch_rewrites = {
            "javascript is a programming language used to make websites interactive.": (
                "JavaScript = the language that makes websites interactive."
            ),
            "python is a high-level programming language.": (
                "Python = a readable programming language used for scripts, apps, automation, data, and AI."
            ),
            "css stands for cascading style sheets.": (
                "CSS = the styling language for webpages."
            ),
            "html stands for hypertext markup language.": (
                "HTML = the structure language of webpages."
            ),
        }

        lines = text.split("\n")
        if lines:
            first_lc = lines[0].strip().lower()
            if first_lc in punch_rewrites:
                lines[0] = punch_rewrites[first_lc]

        text = "\n".join(lines).strip()

        # =============================
        # AUTHORITY TONE
        # =============================

        hedges = [
            "maybe",
            "perhaps",
            "possibly",
            "generally",
            "typically",
            "usually",
            "kind of",
            "sort of",
        ]

        strong_lines = []
        for line in text.split("\n"):
            clean_line = line.strip()

            if len(clean_line.split()) > 5:
                for hedge in hedges:
                    clean_line = clean_line.replace(hedge, "").replace(
                        hedge.title(), ""
                    )

            strong_lines.append(" ".join(clean_line.split()))

        text = "\n".join(strong_lines).strip()

        return text or ""


 