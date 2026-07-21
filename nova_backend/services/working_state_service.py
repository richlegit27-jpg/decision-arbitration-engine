import json
import re


class WorkingStateService:

    def __init__(self, session_service):
        self.session_service = session_service

    def get_working_state(self, session_id):
        try:
            session = self.session_service.get_session(
                session_id
            )

            if not isinstance(session, dict):
                return {}

            state = session.get("working_state")

            return self.normalize_working_state(
                state
            )

        except Exception:
            return {}


    def update_working_state(
        self,
        session_id,
        patch,
    ):
        current = self.get_working_state(
            session_id
        )

        if not isinstance(patch, dict):
            patch = {}

        merged = dict(current)
        merged.update(patch)

        clean_state = self.normalize_working_state(
            merged
        )

        self.set_working_state(
            session_id,
            clean_state,
        )

        return clean_state
    def set_working_state(
        self,
        session_id,
        state,
    ):
        clean_state = self.normalize_working_state(
            state
        )

        sessions = self.session_service._load_sessions()

        index = self.session_service._find(
            sessions,
            session_id,
        )

        if index is not None:
            sessions[index]["working_state"] = clean_state

            self.session_service._save_sessions(
                sessions,
                self.session_service.get_active_session_id(),
            )

        return clean_state

    def normalize_working_state(
        self,
        working_state,
    ):
        if isinstance(working_state, dict):
            return working_state

        if working_state is None:
            return {}

        if isinstance(working_state, str):
            try:
                parsed = json.loads(
                    working_state
                )

                return (
                    parsed
                    if isinstance(parsed, dict)
                    else {}
                )

            except Exception:
                return {}

        return {}

    def clean_working_state_value(
        self,
        value,
        limit=160,
    ):
        text = str(value or "").strip()

        if not text:
            return ""

        text = (
            text
            .replace("\r", " ")
            .replace("\n", " ")
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        bad_starts = (
            "yes",
            "agreed",
            "recommended next step",
            "current project truth says",
            "what this means",
            "in short",
        )

        lower = text.lower()

        if any(
            lower.startswith(x)
            for x in bad_starts
        ):
            return ""

        return text[:limit]

    def is_valid_state_value(
        self,
        value,
    ):
        if not value:
            return False

        value = str(value).strip()

        if not value:
            return False

        if len(value) > 120:
            return False

        if "\n" in value:
            return False

        bad_patterns = [
            "recommended order",
            "if you want",
            "you can also",
            "for example",
        ]

        lower = value.lower()

        for pattern in bad_patterns:
            if pattern in lower:
                return False

        return True

    def merge_working_state(
        self,
        current_state,
        updates,
    ):
        current = self.normalize_working_state(
            current_state
        )

        updates = (
            updates
            if isinstance(updates, dict)
            else {}
        )

        merged = dict(current)

        for key, value in updates.items():
            cleaned = self.clean_working_state_value(
                value
            )

            if self.is_valid_state_value(cleaned):
                merged[key] = cleaned

        return merged

    def merge_working_state(
        self,
        current_state,
        updates,
    ):
        current_state = (
            current_state
            if isinstance(current_state, dict)
            else {}
        )

        updates = (
            updates
            if isinstance(updates, dict)
            else {}
        )

        merged = {
            "active_task": "",
            "current_file": "",
            "current_bug": "",
            "last_success": "",
            "next_move": "",
            "checkpoint": "",
        }

        for key in merged.keys():
            old_value = self.clean_working_state_value(
                current_state.get(key, "")
            )

            new_value = self.clean_working_state_value(
                updates.get(key, "")
            )

            merged[key] = (
                new_value
                if new_value
                else old_value
            )

        from datetime import datetime, timezone

        merged["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        return merged