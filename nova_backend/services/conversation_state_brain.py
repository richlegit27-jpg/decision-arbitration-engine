from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConversationState:
    active_topic: str = ""
    latest_user_instruction: str = ""
    latest_correction: str = ""
    response_mode: str = "default"
    short_followup: bool = False
    recall_requested: bool = False
    suppress_project_brain_contract: bool = False
    source_message_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def build_context_block(self) -> str:
        meaningful = any(
            (
                self.active_topic,
                self.latest_user_instruction,
                self.latest_correction,
                self.short_followup,
                self.recall_requested,
                self.suppress_project_brain_contract,
                self.response_mode != "default",
            )
        )

        if not meaningful:
            return ""

        lines = [
            "[LIVE CONVERSATION STATE]",
            (
                "Priority: current user message > latest conversation "
                "correction > recent thread > persistent memory."
            ),
        ]

        if self.active_topic:
            lines.append(
                f"Active topic: {self.active_topic}"
            )

        if self.latest_user_instruction:
            lines.append(
                "Latest user instruction: "
                + self.latest_user_instruction
            )

        if self.latest_correction:
            lines.append(
                "Latest correction: "
                + self.latest_correction
            )

        if self.response_mode != "default":
            lines.append(
                f"Response mode: {self.response_mode}"
            )

        if self.short_followup and self.active_topic:
            lines.append(
                (
                    "The current message is a short follow-up. "
                    "Resolve vague references against the active topic."
                )
            )

        if self.recall_requested:
            lines.append(
                (
                    "The user is asking about the recent conversation. "
                    "Use the recent thread before older saved memory."
                )
            )

        if self.suppress_project_brain_contract:
            lines.append(
                (
                    "Do not answer with Project Brain Command Center, "
                    "operator contract, routing diagnostics, smoke lists, "
                    "or internal planning-console output. Answer normally "
                    "and directly."
                )
            )

        lines.append(
            (
                "The latest user correction overrides conflicting "
                "earlier conversational instructions."
            )
        )

        return "\n".join(lines)


class ConversationStateBrain:
    MAX_MESSAGES = 14

    RECALL_PHRASES = {
        "what were we talking about",
        "what was we talking about",
        "what did we talk about",
        "what were we just talking about",
        "remind me what we were talking about",
        "where were we",
    }

    SHORT_FOLLOWUPS = {
        "tell me more",
        "tell me more about it",
        "more",
        "go deeper",
        "explain more",
        "explain that",
        "what about it",
        "what about that",
        "why",
        "how",
        "continue",
        "keep going",
        "expand",
        "expand on that",
        "historical use and controversies",
        "historical background",
        "major controversies",
        "current relevance",
        "why are we doing that",
        "why did that matter",
        "what did we just fix",
        "what's next",
        "whats next",
        "what next",
        "so what next",
        "then what",
        "and then",
        "it",
        "that",
        "this",
        "the first one",
        "the second one",
        "the last one",
        "that one",
        "this one",
    }

    GREETINGS = {
        "hey",
        "hey nova",
        "hi",
        "hi nova",
        "hello",
        "hello nova",
        "yo",
        "yo nova",
        "sup",
    }

    NORMAL_MODE_MARKERS = (
        "tell me normally",
        "just tell me normally",
        "answer normally",
        "talk normally",
        "say it normally",
        "plain english",
        "plainly",
        "normal answer",
        "just tell me",
    )

    CONCISE_MODE_MARKERS = (
        "keep it short",
        "keep it brief",
        "be brief",
        "be concise",
        "short answer",
        "get to the point",
    )

    DETAILED_MODE_MARKERS = (
        "go deep",
        "go deeper",
        "full detail",
        "be detailed",
        "explain everything",
        "give me the full",
    )

    INSTRUCTION_MARKERS = (
        "don't ",
        "do not ",
        "stop ",
        "no more ",
        "just tell me",
        "answer ",
        "talk ",
        "say it ",
        "keep it ",
        "be brief",
        "be concise",
        "from now on",
        "instead ",
        "not like that",
        "i mean ",
        "actually ",
    )

    def _clean_text(self, value: Any) -> str:
        return " ".join(
            str(value or "").strip().split()
        )

    def _probe(self, value: Any) -> str:
        return self._clean_text(value).lower().strip(
            " ?.!,:;-"
        )

    def _message_text(
        self,
        message: dict[str, Any],
    ) -> str:
        return self._clean_text(
            message.get("text")
            or message.get("content")
            or message.get("message")
            or ""
        )

    def normalize_messages(
        self,
        messages: Any,
        max_messages: int | None = None,
    ) -> list[dict[str, str]]:
        limit = max_messages or self.MAX_MESSAGES

        if not isinstance(messages, list):
            return []

        normalized: list[dict[str, str]] = []

        for message in messages[-limit:]:
            if not isinstance(message, dict):
                continue

            role = self._probe(
                message.get("role")
            )

            text = self._message_text(message)

            if role not in {
                "user",
                "assistant",
                "system",
            }:
                continue

            if not text:
                continue

            normalized.append(
                {
                    "role": role,
                    "text": text,
                }
            )

        return normalized

    def is_recall_request(
        self,
        user_text: str,
    ) -> bool:
        return (
            self._probe(user_text)
            in self.RECALL_PHRASES
        )

    def is_short_followup(
        self,
        user_text: str,
    ) -> bool:
        probe = self._probe(user_text)

        if not probe:
            return False

        if probe in self.SHORT_FOLLOWUPS:
            return True

        prefixes = (
            "tell me more about",
            "go deeper on",
            "expand on",
            "what about",
            "explain the",
            "explain that",
            "explain it",
            "more about",
            "why did",
            "why does",
            "why was",
            "why is that",
            "how does that",
            "how did that",
        )

        return any(
            probe.startswith(prefix)
            for prefix in prefixes
        )

    def is_user_instruction(
        self,
        user_text: str,
    ) -> bool:
        probe = self._probe(user_text)

        return any(
            marker in probe
            for marker in self.INSTRUCTION_MARKERS
        )

    def is_correction(
        self,
        user_text: str,
    ) -> bool:
        probe = self._probe(user_text)

        correction_markers = (
            "don't ",
            "do not ",
            "stop ",
            "no more ",
            "not like that",
            "instead ",
            "i mean ",
            "actually ",
            "just tell me",
        )

        return any(
            marker in probe
            for marker in correction_markers
        )

    def _detect_response_mode(
        self,
        user_messages: list[str],
    ) -> str:
        for text in reversed(user_messages):
            probe = self._probe(text)

            if any(
                marker in probe
                for marker in self.NORMAL_MODE_MARKERS
            ):
                return "normal"

            if any(
                marker in probe
                for marker in self.CONCISE_MODE_MARKERS
            ):
                return "concise"

            if any(
                marker in probe
                for marker in self.DETAILED_MODE_MARKERS
            ):
                return "detailed"

        return "default"

    def _should_suppress_project_brain_contract(
        self,
        user_messages: list[str],
    ) -> bool:
        for text in reversed(user_messages):
            probe = self._probe(text)

            mentions_contract = any(
                marker in probe
                for marker in (
                    "project command center",
                    "project brain command center",
                    "command center shit",
                    "command center",
                    "operator contract",
                    "internal diagnostics",
                )
            )

            rejects_contract = any(
                marker in probe
                for marker in (
                    "don't ",
                    "do not ",
                    "stop ",
                    "no more ",
                    "not ",
                    "just tell me",
                )
            )

            if mentions_contract and rejects_contract:
                return True

            if self.is_user_instruction(text):
                return False

        return False

    def _is_topic_candidate(
        self,
        text: str,
    ) -> bool:
        probe = self._probe(text)

        if not probe:
            return False

        if probe in self.GREETINGS:
            return False

        if self.is_recall_request(text):
            return False

        if self.is_short_followup(text):
            return False

        if self.is_user_instruction(text):
            return False

        return True

    def _resolve_active_topic(
        self,
        messages: list[dict[str, str]],
        current_user_text: str,
    ) -> str:
        current = self._clean_text(
            current_user_text
        )

        if (
            current
            and self._is_topic_candidate(current)
        ):
            return current[:500]

        for message in reversed(messages):
            if message["role"] != "user":
                continue

            text = message["text"]
            probe = self._probe(text)

            if not text:
                continue

            if probe in self.GREETINGS:
                continue

            if self.is_recall_request(text):
                continue

            if self.is_user_instruction(text):
                continue

            return text[:500]

        for message in reversed(messages):
            if message["role"] != "assistant":
                continue

            text = message["text"]

            probe = self._probe(text)

            if not text:
                continue

            if "project brain command center" in probe:
                continue

            if "command center contract" in probe:
                continue

            return text[:500]

        return ""

    def build_state(
        self,
        messages: Any,
        current_user_text: str = "",
        max_messages: int | None = None,
    ) -> ConversationState:
        normalized = self.normalize_messages(
            messages,
            max_messages=max_messages,
        )

        current = self._clean_text(
            current_user_text
        )

        user_messages = [
            message["text"]
            for message in normalized
            if message["role"] == "user"
        ]

        if current:
            if (
                not user_messages
                or self._probe(user_messages[-1])
                != self._probe(current)
            ):
                user_messages.append(current)

        latest_instruction = ""

        for text in reversed(user_messages):
            if self.is_user_instruction(text):
                latest_instruction = text
                break

        latest_correction = ""

        for text in reversed(user_messages):
            if self.is_correction(text):
                latest_correction = text
                break

        return ConversationState(
            active_topic=self._resolve_active_topic(
                normalized,
                current,
            ),
            latest_user_instruction=latest_instruction,
            latest_correction=latest_correction,
            response_mode=self._detect_response_mode(
                user_messages
            ),
            short_followup=self.is_short_followup(
                current
            ),
            recall_requested=self.is_recall_request(
                current
            ),
            suppress_project_brain_contract=(
                self._should_suppress_project_brain_contract(
                    user_messages
                )
            ),
            source_message_count=len(normalized),
        )


conversation_state_brain = ConversationStateBrain()
