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
    unresolved_threads: tuple[str, ...] = ()
    current_intent: str = "conversation"
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
                self.unresolved_threads,
                self.current_intent != "conversation",
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

        if (
            self.unresolved_threads
            and self.current_intent
            ==
            "resume_unresolved_thread"
        ):
            lines.append(
                "Explicit unresolved conversation threads:"
            )

            for index, thread in enumerate(
                self.unresolved_threads,
                start=1,
            ):
                lines.append(
                    f"{index}. {thread}"
                )

            lines.append(
                (
                    "The user is explicitly referring back to deferred local "
                    "conversation work. Answer from this unresolved thread "
                    "list only. Do not answer from older project state, "
                    "Project Brain memory, execution state, saved memory, "
                    "or general current-project checkpoints."
                )
            )

        elif self.unresolved_threads:
            lines.append(
                (
                    "There are explicitly deferred conversation threads, "
                    "but the user is not asking about them now. Keep them "
                    "hidden. Do not name, summarize, mention, hint at, or "
                    "use those deferred threads in this answer."
                )
            )

        if self.current_intent != "conversation":
            lines.append(
                "Current conversation intent: "
                + self.current_intent
            )

        lines.append(
            (
                "The latest user correction overrides conflicting "
                "earlier conversational instructions."
            )
        )

        return "\n".join(lines)


class ConversationStateBrain:
    MAX_MESSAGES = 24
    MAX_UNRESOLVED_THREADS = 3

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

    UNRESOLVED_THREAD_MARKERS = (
        "after this ",
        "after we finish ",
        "after we're done ",
        "after we are done ",
        "once we're done ",
        "once we are done ",
        "later we need to ",
        "later we have to ",
        "later let's ",
        "later lets ",
        "we still need to ",
        "we still have to ",
        "we also need to ",
        "we also have to ",
        "don't forget we need to ",
        "do not forget we need to ",
        "we need to come back to ",
        "come back to ",
        "before we finish ",
        "next we need to ",
        "then we need to ",
        "then we have to ",
    )

    UNRESOLVED_THREAD_RECALL_PHRASES = {
        "what was the other thing",
        "what was the other thing we needed to do",
        "what was the other thing we still needed to do",
        "what else did we need to do",
        "what else do we need to do",
        "what did we still need to do",
        "what did we leave for later",
        "what did we say we'd do later",
        "what did we say we would do later",
        "what were we going to come back to",
        "what do we still have left",
        "what's still open",
        "whats still open",
        "what is still open",
    }

    GENERIC_THREAD_RESOLUTION_PHRASES = {
        "that's done",
        "thats done",
        "that is done",
        "we're done with that",
        "we are done with that",
        "that's finished",
        "thats finished",
        "that is finished",
        "scratch that",
        "forget that",
        "drop that",
    }

    THREAD_RESOLUTION_MARKERS = (
        "done with ",
        "finished with ",
        "we finished ",
        "we handled ",
        "we fixed ",
        "we completed ",
        "we closed ",
        "close out ",
        "scratch ",
        "drop ",
        "forget ",
    )

    THREAD_LEADING_FILLERS = (
        "let's ",
        "lets ",
        "we need to ",
        "we have to ",
        "we should ",
        "do ",
    )

    THREAD_TOKEN_STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "at",
        "be",
        "do",
        "for",
        "from",
        "have",
        "it",
        "later",
        "need",
        "of",
        "on",
        "or",
        "our",
        "that",
        "the",
        "this",
        "to",
        "we",
        "with",
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
            "why did that",
            "why did it",
            "why does that",
            "why does it",
            "why was that",
            "why was it",
            "why is that",
            "how does that",
            "how does it",
            "how did that",
            "how did it",
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

    def _thread_tokens(
        self,
        value: str,
    ) -> set[str]:
        probe = self._probe(
            value
        )

        cleaned = "".join(
            character
            if (
                character.isalnum()
                or character.isspace()
            )
            else " "
            for character in probe
        )

        return {
            token
            for token in cleaned.split()
            if (
                len(token) >= 3
                and token
                not in self.THREAD_TOKEN_STOPWORDS
            )
        }

    def _extract_explicit_thread(
        self,
        user_text: str,
    ) -> str:
        clean = self._clean_text(
            user_text
        )

        probe = clean.lower()

        if not probe:
            return ""

        best_index = None
        best_marker = ""

        for marker in self.UNRESOLVED_THREAD_MARKERS:
            index = probe.find(
                marker
            )

            if index < 0:
                continue

            if (
                best_index is None
                or index < best_index
            ):
                best_index = index
                best_marker = marker

        if best_index is None:
            return ""

        candidate = clean[
            best_index
            +
            len(
                best_marker
            )
            :
        ].strip(
            " .,!?:;-"
        )

        candidate_probe = candidate.lower()

        for filler in self.THREAD_LEADING_FILLERS:
            if candidate_probe.startswith(
                filler
            ):
                candidate = candidate[
                    len(
                        filler
                    )
                    :
                ].strip(
                    " .,!?:;-"
                )

                break

        if not candidate:
            return ""

        return candidate[:500]

    def _is_unresolved_thread_recall(
        self,
        user_text: str,
    ) -> bool:
        return (
            self._probe(
                user_text
            )
            in self.UNRESOLVED_THREAD_RECALL_PHRASES
        )

    def _apply_thread_resolution(
        self,
        threads: list[str],
        user_text: str,
    ) -> list[str]:
        if not threads:
            return []

        probe = self._probe(
            user_text
        )

        if (
            probe
            in self.GENERIC_THREAD_RESOLUTION_PHRASES
        ):
            return threads[:-1]

        if not any(
            marker in probe
            for marker in self.THREAD_RESOLUTION_MARKERS
        ):
            return list(
                threads
            )

        user_tokens = self._thread_tokens(
            user_text
        )

        if not user_tokens:
            return list(
                threads
            )

        remaining = []

        for thread in threads:
            thread_tokens = self._thread_tokens(
                thread
            )

            if (
                thread_tokens
                and thread_tokens.intersection(
                    user_tokens
                )
            ):
                continue

            remaining.append(
                thread
            )

        return remaining

    def _resolve_unresolved_threads(
        self,
        messages: list[dict[str, str]],
        current_user_text: str,
    ) -> tuple[str, ...]:
        user_messages = [
            message["text"]
            for message in messages
            if message["role"] == "user"
        ]

        current = self._clean_text(
            current_user_text
        )

        if (
            current
            and (
                not user_messages
                or self._probe(
                    user_messages[-1]
                )
                != self._probe(
                    current
                )
            )
        ):
            user_messages.append(
                current
            )

        threads: list[str] = []

        for text in user_messages:
            threads = self._apply_thread_resolution(
                threads,
                text,
            )

            thread = self._extract_explicit_thread(
                text
            )

            if not thread:
                continue

            thread_probe = self._probe(
                thread
            )

            threads = [
                existing
                for existing in threads
                if (
                    self._probe(
                        existing
                    )
                    != thread_probe
                )
            ]

            threads.append(
                thread
            )

            if (
                len(
                    threads
                )
                >
                self.MAX_UNRESOLVED_THREADS
            ):
                threads = threads[
                    -self.MAX_UNRESOLVED_THREADS
                    :
                ]

        return tuple(
            threads
        )

    def _detect_current_intent(
        self,
        current_user_text: str,
    ) -> str:
        current = self._clean_text(
            current_user_text
        )

        if not current:
            return "conversation"

        if self._is_unresolved_thread_recall(
            current
        ):
            return "resume_unresolved_thread"

        if self.is_recall_request(
            current
        ):
            return "recall_recent_conversation"

        if self.is_correction(
            current
        ):
            return "conversation_correction"

        if self._extract_explicit_thread(
            current
        ):
            return "defer_unresolved_thread"

        if self.is_short_followup(
            current
        ):
            return "continue_active_thread"

        if self._is_topic_candidate(
            current
        ):
            return "new_or_explicit_topic"

        return "conversation"

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

        unresolved_threads = (
            self._resolve_unresolved_threads(
                normalized,
                current,
            )
        )

        current_intent = (
            self._detect_current_intent(
                current
            )
        )

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
            unresolved_threads=unresolved_threads,
            current_intent=current_intent,
            source_message_count=len(normalized),
        )


conversation_state_brain = ConversationStateBrain()
