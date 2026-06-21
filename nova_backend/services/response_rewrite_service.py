# C:\Users\Owner\nova\nova_backend\services\response_rewrite_service.py

from nova_backend.services.nova_voice_profile import NOVA_VOICE_PROFILE
import re


class ResponseRewriteService:
    """
    Aggressive Nova rewrite layer

    Goal:
    - Kill assistant fluff completely
    - Force direct execution tone
    - Preserve useful content only
    """

    def __init__(self):
        self.weak_openers = [
            r"^sure[,.!\s]+",
            r"^of course[,.!\s]+",
            r"^absolutely[,.!\s]+",
            r"^certainly[,.!\s]+",
            r"^i can help with that[,.!\s]+",
            r"^here(?:'s| is)\s+(?:a|the)?\s*",
            r"^looks like you pasted.*",
        ]

        self.dead_weight_phrases = [
            "if you want",
            "let me know",
            "feel free to",
            "hope this helps",
            "happy to help",
            "i can help with that",
            "looks like you",
            "send me the rest",
            "i can also",

            # ðŸ”¥ added (anti-chatbot tone)
            "got it",
            "bugs can be frustrating",
            "step by step",
            "we can fix this",
        ]

        self.voice_profile = NOVA_VOICE_PROFILE

    def rewrite(self, text: str, user_text: str = "", route: str = "", intent: str = "") -> str:
        return str(text or "").strip()

    def _clean(self, text: str) -> str:
        if text is None:
            return ""
        return str(text).strip()

    def _remove_weak_openers(self, text: str) -> str:
        out = text.strip()

        for pattern in self.weak_openers:
            out = re.sub(pattern, "", out, flags=re.IGNORECASE).strip()

        return out

    def _remove_dead_weight(self, text: str) -> str:
        out = text

        for phrase in self.dead_weight_phrases:
            out = re.sub(re.escape(phrase), "", out, flags=re.IGNORECASE)

        return out.strip()

    def _extract_strongest_line(self, text: str) -> str:
        lines = re.split(r"[.!?\n]", text)

        # prioritize lines with action words
        for line in lines:
            l = line.strip()
            if not l:
                continue

            if any(k in l.lower() for k in ["fix", "do", "run", "add", "use", "replace"]):
                return l

        # fallback â†’ first meaningful line
        for line in lines:
            l = line.strip()
            if l:
                return l

        return text

    def _tighten_spacing(self, text: str) -> str:
        out = text
        out = re.sub(r"[ \t]+", " ", out)
        out = re.sub(r"\n{3,}", "\n\n", out)
        out = re.sub(r"\s+([,.!?])", r"\1", out)
        return out.strip()

    def _looks_empty_or_weak(self, text: str) -> bool:
        cleaned = self._clean(text)
        if len(cleaned) < 3:
            return True
        if cleaned.lower() in {"ok", "okay", "sure", "yes"}:
            return True
        return False

    def _force_command_style(self, text: str) -> str:
        # remove soft language
        text = re.sub(r"\b(you can|you might|try to|consider)\b", "", text, flags=re.IGNORECASE)
        return text.strip()

    def _force_structured_style(self, text: str) -> str:
        lines = re.split(r"[.!?\n]", text)
        clean = [l.strip() for l in lines if l.strip()]
        return "\n".join(f"- {l}" for l in clean[:5])

    def _force_direct_style(self, text: str) -> str:
        lines = re.split(r"[.!?\n]", text)

        for line in lines:
            line = line.strip()
            if line:
                return line

        return text

    def _enforce_voice_tone(self, text: str) -> str:
        text = re.sub(r"\b(maybe|perhaps|might|could)\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bi think\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"i can also.*", "", text, flags=re.IGNORECASE)
        return text.strip()

    def _force_execution_first(self, text: str) -> str:
        lowered = self._clean(text).lower()

        # ðŸ”¥ force action extraction only (no soft fallback)
        lines = re.split(r"[.!?\n]", text)
        clean = [l.strip() for l in lines if l.strip()]

        for l in clean:
            if any(k in l.lower() for k in [
                "fix", "run", "add", "use", "replace",
                "check", "reproduce", "test", "debug"
            ]):
                return l

        # ðŸ”¥ if nothing actionable â†’ force directive
        return "Identify the issue."


