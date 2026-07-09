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

    def rewrite(self, text: str, user_text: str = "", route: str = "") -> str:
        original = self._clean(text)

        if not original:
            return ""

        rewritten = original

        # base cleanup
        rewritten = self._remove_weak_openers(rewritten)
        rewritten = self._remove_dead_weight(rewritten)

        # ðŸ”¥ enforce voice profile (remove avoided phrases)
        for phrase in self.voice_profile.get("avoid", []):
            rewritten = re.sub(re.escape(phrase), "", rewritten, flags=re.IGNORECASE)

        # ðŸ”¥ route-aware tone control
        route = (route or "").lower()

        if route in ("coding", "analysis"):
            rewritten = self._force_command_style(rewritten)

        elif route in ("planning",):
            rewritten = self._force_structured_style(rewritten)

        elif route in ("general_chat", "chat"):
            rewritten = self._force_direct_style(rewritten)

        # fallback tightening
        rewritten = self._extract_strongest_line(rewritten)
        rewritten = self._tighten_spacing(rewritten)

        if self._looks_empty_or_weak(rewritten):
            return original

        rewritten = self._enforce_voice_tone(rewritten)
        return rewritten.strip()

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
        # basic tone enforcement: remove softness + tighten
        text = re.sub(r"\b(maybe|perhaps|might|could)\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bi think\b", "", text, flags=re.IGNORECASE)
        return text.strip()

