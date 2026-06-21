from __future__ import annotations

from typing import Any, Dict, List


class PromptBuilderService:
    """
    Builds Nova's system and user prompt with:

    - filtered recent conversation
    - ranked memory injection
    - ðŸ”¥ memory lock enforcement (NEW)
    - explicit anti-echo instruction
    """

    SHORT_ECHO_TEXTS = {"hi", "hello", "hey", "yo", "sup"}

    LOCKED_KINDS = {"preference", "style", "instruction"}

    def build_prompt(
        self,
        *,
        user_text: str,
        messages: List[Dict[str, Any]] | None = None,
        memory_items: List[Dict[str, Any]] | None = None,
        mode: str = "chat",
        response_style: str = "direct",
        max_recent_messages: int = 8,
        max_memory_items: int = 6,
    ) -> Dict[str, Any]:
        messages = messages or []
        memory_items = memory_items or []

        # -----------------------
        # ðŸ”¥ LOCKED MEMORY (NEW)
        # -----------------------

        locked_items = [
            item for item in memory_items
            if str(item.get("kind", "")).lower() in self.LOCKED_KINDS
        ]

        locked_lines = self._build_locked_lines(locked_items)

        # -----------------------
        # SYSTEM PROMPT (UPGRADED)
        # -----------------------

        system_prompt_parts = [
            "You are Nova, a capable local AI assistant.",
            "Respond clearly, directly, and helpfully.",
            "Do not repeat the user's input unless briefly necessary for clarity.",
            "Use memory and recent conversation only when relevant.",
        ]

        if locked_lines:
            system_prompt_parts.append(
                "The following user preferences are persistent and MUST be followed when relevant:\n- "
                + "\n- ".join(locked_lines)
            )

        system_prompt_parts.append(
            "For simple greetings or short tests, still reply naturally."
        )

        system_prompt = " ".join(system_prompt_parts)

        # -----------------------
        # RECENT + MEMORY
        # -----------------------

        recent_lines = self._build_recent_lines(
            messages=messages,
            max_recent_messages=max_recent_messages,
        )

        memory_lines = self._build_memory_lines(
            memory_items=memory_items,
            max_memory_items=max_memory_items,
        )

        # -----------------------
        # USER PROMPT
        # -----------------------

        user_prompt_parts: List[str] = []

        user_prompt_parts.append(f"Mode: {self._safe_text(mode)}")
        user_prompt_parts.append(f"Response style: {self._safe_text(response_style)}")

        if memory_lines:
            user_prompt_parts.append(
                "Relevant memory:\n- " + "\n- ".join(memory_lines)
            )

        if recent_lines:
            user_prompt_parts.append(
                "Recent conversation:\n" + "\n".join(recent_lines)
            )

        user_prompt_parts.append(
            "User message:\n"
            f"{self._safe_text(user_text)}\n\n"
            "Reply naturally and helpfully. "
            "Do not mirror or repeat the user's message as the full answer. "
            "Follow user preferences when relevant. "
            "Use only useful memory."
        )

        user_prompt = "\n\n".join(part for part in user_prompt_parts if part.strip())

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "memory_used": bool(memory_lines),
            "memory_items_used": len(memory_lines),
            "locked_memory_used": len(locked_lines),
            "recent_messages_used": len(recent_lines),
        }

    # -----------------------
    # ðŸ”¥ LOCKED MEMORY BUILDER
    # -----------------------

    def _build_locked_lines(self, items: List[Dict[str, Any]]) -> List[str]:
        lines: List[str] = []

        for item in items[:5]:  # hard cap
            text = self._safe_text(
                item.get("text")
                or item.get("content")
                or ""
            )

            if not text:
                continue

            lines.append(text)

        return lines

    # -----------------------
    # RECENT MESSAGES
    # -----------------------

    def _build_recent_lines(
        self,
        *,
        messages: List[Dict[str, Any]],
        max_recent_messages: int,
    ) -> List[str]:
        recent_lines: List[str] = []

        trimmed = messages[-max_recent_messages:] if max_recent_messages > 0 else messages

        for message in trimmed:
            role = str(message.get("role", "")).strip().lower()
            if role not in {"user", "assistant"}:
                continue

            text = self._extract_message_text(message)
            normalized = text.lower().strip()

            if not text:
                continue

            if normalized in self.SHORT_ECHO_TEXTS:
                continue

            if len(text) < 8:
                continue

            recent_lines.append(f"{role.title()}: {text}")

        return recent_lines

    # -----------------------
    # MEMORY LINES
    # -----------------------

    def _build_memory_lines(
        self,
        *,
        memory_items: List[Dict[str, Any]],
        max_memory_items: int,
    ) -> List[str]:
        lines: List[str] = []

        for item in memory_items[:max_memory_items]:
            text = self._safe_text(
                item.get("text")
                or item.get("content")
                or ""
            )

            if not text:
                continue

            kind = str(item.get("kind", "memory")).lower()
            lines.append(f"({kind}) {text}")

        return lines

    # -----------------------
    # TEXT EXTRACTION
    # -----------------------

    def _extract_message_text(self, message: Dict[str, Any]) -> str:
        raw = (
            message.get("text")
            or message.get("content")
            or message.get("body")
            or ""
        )

        if isinstance(raw, list):
            parts = []

            for entry in raw:
                if isinstance(entry, dict):
                    val = entry.get("text") or entry.get("content") or ""
                    if val:
                        parts.append(str(val))
                elif entry:
                    parts.append(str(entry))

            raw = "\n".join(parts)

        elif isinstance(raw, dict):
            raw = raw.get("text") or raw.get("content") or ""

        return self._safe_text(raw)

    def _safe_text(self, value: Any) -> str:
        return str(value or "").strip()

