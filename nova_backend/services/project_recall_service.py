from pathlib import Path
import json


class ProjectRecallService:

    def __init__(
        self,
        project_focus_memory_service,
        project_state_memory_service,
        project_state_memory_kinds,
        data_dir,
    ):
        self.project_focus_memory_service = (
            project_focus_memory_service
        )

        self.project_state_memory_service = (
            project_state_memory_service
        )

        self.project_state_memory_kinds = (
            project_state_memory_kinds
        )

        self.data_dir = Path(data_dir)


    def try_project_focus_direct_recall(
        self,
        user_text,
        session_id,
    ):
        if not self.project_focus_memory_service.is_project_focus_recall_question(
            user_text
        ):
            return None

        focus = self.project_focus_memory_service.find_recent_project_focus(
            session_id
        )

        if not focus:
            focus = self.project_focus_memory_service.find_project_focus_memory(
                session_id
            )

        if not focus:
            return None

        return {
            "text": f"Your current project focus was {focus}.",
            "route": "project_focus",
            "debug": {
                "direct_recall": "project_focus",
                "focus": focus,
            },
        }

    def find_current_project_state_memory(self):
        try:
            memory_path = self.data_dir / "nova_memory.json"

            payload = json.loads(
                memory_path.read_text(
                    encoding="utf-8"
                ) or "{}"
            )

            items = payload.get("memory") or []
            candidates = []

            for item in items:
                if not isinstance(item, dict):
                    continue

                kind = str(
                    item.get("kind") or ""
                ).strip().lower()

                category = str(
                    item.get("category") or ""
                ).strip().lower()

                memory_id = str(
                    item.get("id") or ""
                ).strip().lower()

                value = str(
                    item.get("text")
                    or item.get("content")
                    or ""
                ).strip()

                if not value:
                    continue

                if (
                    kind == "project_state"
                    or category == "project_state"
                    or memory_id
                    == "memory_nova_project_state_current"
                ):
                    try:
                        weight = float(
                            item.get("weight") or 0.0
                        )
                    except Exception:
                        weight = 0.0

                    candidates.append(
                        (
                            0 if item.get("pinned") else 1,
                            -weight,
                            str(item.get("updated_at") or ""),
                            value,
                        )
                    )

            candidates.sort()

            if candidates:
                return candidates[0][3]

        except Exception:
            return ""

        return ""

    def try_project_state_direct_recall(
        self,
        user_text,
        session_id,
    ):
        kinds = (
            self.project_state_memory_service
            .question_project_state_kinds(
                user_text
            )
        )

        if not kinds:
            return None

        current = self.find_current_project_state_memory()

        if current:
            return {
                "text": current,
                "route": "project_state_current_memory_direct_recall",
                "route_taken": "project_state_current_memory_direct_recall",
                "project_state_memory_recall": True,
            }

        lines = []

        for kind in kinds:
            value = (
                self.project_state_memory_service
                .find_project_state_memory(
                    session_id,
                    kind,
                )
            )

            if not value:
                continue

            label = str(
                (
                    self.project_state_memory_kinds.get(kind)
                    or {}
                ).get("label")
                or kind
            ).strip()

            clean_value = str(
                value or ""
            ).strip()

            if clean_value:
                lines.append(
                    f"{label}: {clean_value}"
                )

        if not lines:
            return None

        return {
            "text": "\n".join(lines),
            "direct_recall": "project_state",
            "kinds": kinds,
        }