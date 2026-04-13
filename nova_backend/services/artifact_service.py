from __future__ import annotations

from typing import Any, Dict, List, Optional

from nova_backend.models.artifact import (
    new_artifact,
    normalize_artifact,
    artifact_preview,
    artifact_viewer_payload,
)
from nova_backend.utils.file_utils import (
    read_json_file,
    atomic_write_json,
    safe_list,
)
from nova_backend.utils.time_utils import iso_now, newest_first


class ArtifactService:
    def __init__(self, artifacts_file: str):
        self.artifacts_file = artifacts_file
        self.artifacts: List[dict] = []
        self._load()

    # -----------------------
    # LOAD / SAVE
    # -----------------------

    def _load(self) -> None:
        data = read_json_file(self.artifacts_file, default=[])
        raw_artifacts = safe_list(data)
        self.artifacts = [normalize_artifact(a) for a in raw_artifacts]
        self.artifacts = newest_first(self.artifacts, "updated_at")

    def _save(self) -> None:
        atomic_write_json(self.artifacts_file, self.artifacts)

    # -----------------------
    # INTERNAL HELPERS
    # -----------------------

    def _clean_text(self, value: Any) -> str:
        return " ".join(str(value or "").strip().lower().split())

    def _normalize_execution_signature(self, execution: Dict[str, Any] | None) -> Dict[str, Any]:
        execution = execution if isinstance(execution, dict) else {}

        steps = execution.get("steps") if isinstance(execution.get("steps"), list) else []
        normalized_steps: List[str] = []

        for step in steps:
            if not isinstance(step, dict):
                continue

            title = self._clean_text(step.get("title"))
            status = self._clean_text(step.get("status"))
            notes = self._clean_text(step.get("notes"))
            normalized_steps.append(f"{title}|{status}|{notes}")

        return {
            "goal": self._clean_text(execution.get("goal")),
            "summary": self._clean_text(execution.get("summary")),
            "status": self._clean_text(execution.get("status")),
            "steps": normalized_steps,
        }

    def _execution_equivalent(
        self,
        left: Dict[str, Any] | None,
        right: Dict[str, Any] | None,
    ) -> bool:
        a = self._normalize_execution_signature(left)
        b = self._normalize_execution_signature(right)
        return (
            a["goal"] == b["goal"]
            and a["summary"] == b["summary"]
            and a["status"] == b["status"]
            and a["steps"] == b["steps"]
        )

    # -----------------------
    # GETTERS
    # -----------------------

    def get_all(self) -> List[dict]:
        return newest_first(list(self.artifacts), "updated_at")

    def get_by_id(self, artifact_id: str | None) -> Optional[dict]:
        if not artifact_id:
            return None

        for artifact in self.artifacts:
            if artifact.get("id") == artifact_id:
                return normalize_artifact(artifact)

        return None

    def get_by_session_id(self, session_id: str | None) -> List[dict]:
        if not session_id:
            return []

        matches = [
            normalize_artifact(a)
            for a in self.artifacts
            if str(a.get("session_id") or "").strip() == str(session_id).strip()
        ]
        return newest_first(matches, "updated_at")

    def get_latest_execution_run_for_session(self, session_id: str | None) -> Optional[dict]:
        if not session_id:
            return None

        session_id = str(session_id).strip()
        for artifact in newest_first(self.artifacts, "updated_at"):
            normalized = normalize_artifact(artifact)
            if str(normalized.get("session_id") or "").strip() != session_id:
                continue
            if str(normalized.get("kind") or "").strip() != "execution_run":
                continue
            return normalized

        return None

    def find_latest_execution_run_by_goal(
        self,
        session_id: str | None,
        goal: str | None,
    ) -> Optional[dict]:
        if not session_id:
            return None

        target_session = str(session_id).strip()
        target_goal = self._clean_text(goal)

        if not target_goal:
            return None

        for artifact in newest_first(self.artifacts, "updated_at"):
            normalized = normalize_artifact(artifact)

            if str(normalized.get("session_id") or "").strip() != target_session:
                continue

            if str(normalized.get("kind") or "").strip() != "execution_run":
                continue

            meta = normalized.get("meta") if isinstance(normalized.get("meta"), dict) else {}
            execution = meta.get("execution") if isinstance(meta, dict) else {}
            existing_goal = self._clean_text(execution.get("goal") if isinstance(execution, dict) else "")

            if existing_goal == target_goal:
                return normalized

        return None

    # -----------------------
    # CREATE / UPDATE
    # -----------------------

    def create(
        self,
        kind: str = "artifact",
        title: str = "Untitled",
        body: str = "",
        session_id: str = "",
        source: str = "",
        meta: Dict[str, Any] | None = None,
    ) -> dict:
        artifact = new_artifact(
            kind=kind,
            title=title,
            body=body,
            session_id=session_id,
            source=source,
            meta=meta,
        )
        normalized = normalize_artifact(artifact)
        self.artifacts.insert(0, normalized)
        self.artifacts = newest_first(self.artifacts, "updated_at")
        self._save()
        return normalized

    def upsert(self, artifact: Dict[str, Any]) -> dict:
        normalized = normalize_artifact(artifact)
        artifact_id = normalized.get("id")

        for index, existing in enumerate(self.artifacts):
            if existing.get("id") == artifact_id:
                normalized["created_at"] = existing.get("created_at") or normalized.get("created_at")
                normalized["updated_at"] = iso_now()
                self.artifacts[index] = normalize_artifact(normalized)
                self.artifacts = newest_first(self.artifacts, "updated_at")
                self._save()
                return self.artifacts[index]

        normalized["updated_at"] = iso_now()
        self.artifacts.insert(0, normalize_artifact(normalized))
        self.artifacts = newest_first(self.artifacts, "updated_at")
        self._save()
        return self.artifacts[0]

    def delete(self, artifact_id: str) -> bool:
        before = len(self.artifacts)
        self.artifacts = [a for a in self.artifacts if a.get("id") != artifact_id]

        if len(self.artifacts) == before:
            return False

        self._save()
        return True

    def save_execution_run(self, session_id: str, execution: Dict[str, Any] | None) -> Optional[dict]:
        if not session_id or not isinstance(execution, dict):
            return None

        goal = str(execution.get("goal") or "Execution").strip() or "Execution"
        status = str(execution.get("status") or "planned").strip() or "planned"
        summary = str(execution.get("summary") or "").strip()
        current_step = str(execution.get("current_step") or "").strip()
        steps = execution.get("steps") if isinstance(execution.get("steps"), list) else []

        execution_payload = {
            "id": str(execution.get("id") or "").strip(),
            "mode": str(execution.get("mode") or "plan_run").strip(),
            "goal": goal,
            "status": status,
            "current_step": current_step,
            "summary": summary,
            "steps": steps,
            "started_at": str(execution.get("started_at") or "").strip(),
            "updated_at": str(execution.get("updated_at") or "").strip(),
        }

        existing = self.find_latest_execution_run_by_goal(session_id=session_id, goal=goal)

        if existing:
            existing_meta = existing.get("meta") if isinstance(existing.get("meta"), dict) else {}
            existing_execution = existing_meta.get("execution") if isinstance(existing_meta, dict) else {}

            if self._execution_equivalent(existing_execution, execution_payload):
                return existing

            updated = dict(existing)
            updated["kind"] = "execution_run"
            updated["title"] = f"Execution: {goal[:80]}"
            updated["body"] = summary
            updated["session_id"] = str(session_id).strip()
            updated["source"] = "execution"
            updated["meta"] = {
                "execution": execution_payload
            }
            updated["updated_at"] = iso_now()
            return self.upsert(updated)

        return self.create(
            kind="execution_run",
            title=f"Execution: {goal[:80]}",
            body=summary,
            session_id=str(session_id).strip(),
            source="execution",
            meta={
                "execution": execution_payload
            },
        )

    # -----------------------
    # PAYLOADS
    # -----------------------

    def build_list_payload(self) -> List[dict]:
        payload: List[dict] = []

        for artifact in newest_first(self.artifacts, "updated_at"):
            normalized = normalize_artifact(artifact)
            payload.append(
                {
                    "id": normalized.get("id", ""),
                    "kind": normalized.get("kind", "artifact"),
                    "title": normalized.get("title", "Untitled"),
                    "preview": artifact_preview(normalized),
                    "session_id": normalized.get("session_id", ""),
                    "source": normalized.get("source", ""),
                    "created_at": normalized.get("created_at", ""),
                    "updated_at": normalized.get("updated_at", ""),
                    "viewer": artifact_viewer_payload(normalized),
                }
            )

        return payload

    def build_view_payload(self, artifact_id: str) -> Optional[dict]:
        artifact = self.get_by_id(artifact_id)
        if not artifact:
            return None

        normalized = normalize_artifact(artifact)

        return {
            "id": normalized.get("id", ""),
            "kind": normalized.get("kind", "artifact"),
            "title": normalized.get("title", "Untitled"),
            "body": normalized.get("body", ""),
            "preview": artifact_preview(normalized),
            "session_id": normalized.get("session_id", ""),
            "source": normalized.get("source", ""),
            "meta": normalized.get("meta", {}),
            "created_at": normalized.get("created_at", ""),
            "updated_at": normalized.get("updated_at", ""),
            "viewer": artifact_viewer_payload(normalized),
        }