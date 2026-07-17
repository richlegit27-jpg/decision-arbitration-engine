import json
import re
from datetime import datetime


class ProjectStateMemoryService:

    PROJECT_STATE_MEMORY_KINDS = {
        "current_task": {
            "label": "Current task",
            "answer": "Your current task was {value}.",
            "recall_terms": [
                "what is my current task",
                "what's my current task",
                "what was my current task",
                "what are we doing",
                "what are we working on",
                "what is the next move",
                "what's the next move",
            ],
        },
        "blocker": {
            "label": "Blocker",
            "answer": "Your current blocker was {value}.",
            "recall_terms": [
                "what is blocking me",
                "what's blocking me",
                "what was blocking me",
                "what is the blocker",
                "what's the blocker",
                "current blocker",
            ],
        },
        "active_file": {
            "label": "Active file",
            "answer": "Your active file was {value}.",
            "recall_terms": [
                "what file am i working on",
                "which file am i working on",
                "what is the active file",
                "what's the active file",
                "current file",
                "active file",
            ],
        },
        "last_checkpoint": {
            "label": "Last checkpoint",
            "answer": "Your last checkpoint was {value}.",
            "recall_terms": [
                "what was my last checkpoint",
                "what is my last checkpoint",
                "where did we checkpoint",
                "last checkpoint",
                "current checkpoint",
                "lockpoint",
            ],
        },
    }

    def __init__(
        self,
        project_state_file,
    ):
        self.project_state_file = project_state_file

    def project_state_now(
        self,
    ):
        return datetime.utcnow().isoformat(
            timespec="seconds"
        ) + "Z"

    def read_project_state_store(
        self,
    ):
        try:
            if not self.project_state_file.exists():
                return {
                    "sessions": {}
                }

            payload = json.loads(
                self.project_state_file.read_text(
                    encoding="utf-8-sig"
                )
            )

            if not isinstance(payload, dict):
                return {
                    "sessions": {}
                }

            if not isinstance(
                payload.get("sessions"),
                dict,
            ):
                payload["sessions"] = {}

            return payload

        except Exception:
            return {
                "sessions": {}
            }

    def write_project_state_store(
        self,
        payload,
    ):
        try:
            if not isinstance(payload, dict):
                payload = {
                    "sessions": {}
                }

            self.project_state_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            self.project_state_file.write_text(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            return True

        except Exception:
            return False

    def clean_project_state_value(
        self,
        value,
    ):
        cleaned = str(value or "").strip()

        return re.sub(
            r"\s+",
            " ",
            cleaned,
        ).strip(" .!?")

    def get_project_state_session(
        self,
        session_id,
    ):
        store = self.read_project_state_store()

        sessions = store.setdefault(
            "sessions",
            {},
        )

        target = str(
            session_id or ""
        ).strip()

        if not target:
            return {}

        state = sessions.get(target)

        return state if isinstance(
            state,
            dict,
        ) else {}

    def set_project_state_values(
        self,
        session_id,
        values,
    ):
        target = str(
            session_id or ""
        ).strip()

        if not target:
            return {}

        store = self.read_project_state_store()

        sessions = store.setdefault(
            "sessions",
            {},
        )

        state = sessions.get(target)

        if not isinstance(
            state,
            dict,
        ):
            state = {}

        for item in values or []:
            if not isinstance(
                item,
                dict,
            ):
                continue

            kind = str(
                item.get("kind") or ""
            ).strip()

            value = self.clean_project_state_value(
                item.get("value")
            )

            if (
                kind in self.PROJECT_STATE_MEMORY_KINDS
                and value
            ):
                state[kind] = value

        state["updated_at"] = self.project_state_now()

        sessions[target] = state
        store["sessions"] = sessions

        self.write_project_state_store(
            store
        )

        return state

    def extract_project_state_values(
        self,
        user_text,
    ):
        raw = str(
            user_text or ""
        ).strip()

        found = []

        if not raw:
            return found

        patterns = {
            "current_task": r"(?:current task is|task:|next move is)\s+(.+)",
            "blocker": r"(?:blocker is|blocker:|blocked by)\s+(.+)",
            "active_file": r"(?:active file is|file:|working on file)\s+(.+)",
            "last_checkpoint": r"(?:last checkpoint is|checkpoint:|lockpoint is)\s+(.+)",
        }

        for kind, pattern in patterns.items():
            match = re.search(
                pattern,
                raw,
                re.IGNORECASE,
            )

            if match:
                value = self.clean_project_state_value(
                    match.group(1)
                )

                if value:
                    found.append(
                        {
                            "kind": kind,
                            "value": value,
                        }
                    )

        return found

    def save_project_state_memories(
        self,
        user_text,
        session_id,
    ):
        extracted = self.extract_project_state_values(
            user_text
        )

        if not extracted:
            return []

        state = self.set_project_state_values(
            session_id,
            extracted,
        )

        return [
            {
                **item,
                "session_id": session_id,
                "state": state,
            }
            for item in extracted
        ]

    def question_project_state_kinds(
        self,
        user_text,
    ):
        text = str(
            user_text or ""
        ).lower()

        kinds = []

        for kind, config in self.PROJECT_STATE_MEMORY_KINDS.items():
            for term in config.get(
                "recall_terms",
                [],
            ):
                if term in text:
                    kinds.append(kind)
                    break

        return kinds

    def find_project_state_memory(
        self,
        session_id,
        kind,
    ):
        state = self.get_project_state_session(
            session_id
        )

        return self.clean_project_state_value(
            state.get(kind)
        )

    def build_project_state_context(
        self,
        session_id,
    ):
        state = self.get_project_state_session(
            session_id
        )

        lines = []

        for key, label in (
            ("current_task", "Current task"),
            ("blocker", "Blocker"),
            ("active_file", "Active file"),
            ("last_checkpoint", "Last checkpoint"),
        ):
            value = self.clean_project_state_value(
                state.get(key)
            )

            if value:
                lines.append(
                    f"{label}: {value}"
                )

        if not lines:
            return ""

        return "\n".join(
            [
                "HIGH PRIORITY SESSION PROJECT STATE:",
                *lines,
            ]
        )

    def inject_project_state_context(
        self,
        user_text,
        session_id,
    ):
        context = self.build_project_state_context(
            session_id
        )

        if not context:
            return user_text

        return (
            f"{context}\n\n"
            f"User message:\n{str(user_text or '').strip()}"
        )