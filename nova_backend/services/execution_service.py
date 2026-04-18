from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


class ExecutionService:
    """
    Execution Layer v2

    Purpose:
    - Create structured execution runs
    - Normalize execution payloads
    - Advance / fail / complete runs safely
    - Update existing executions instead of only creating new ones
    - Provide stable artifact/viewer payloads for the right rail

    Status model:
    - execution status: planned | running | blocked | completed | failed
    - step status: pending | running | completed | failed | blocked
    """

    EXECUTION_STATUSES = {"planned", "running", "blocked", "completed", "failed"}
    STEP_STATUSES = {"pending", "running", "completed", "failed", "blocked"}

    # =========================
    # BASICS
    # =========================

    def iso_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def make_id(self, prefix: str = "exec") -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _safe_str(self, value: Any, default: str = "") -> str:
        if value is None:
            return default
        try:
            text = str(value).strip()
        except Exception:
            return default
        return text if text else default

    def _safe_list(self, value: Any) -> List[Any]:
        return value if isinstance(value, list) else []

    def _safe_dict(self, value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _normalize_status(self, value: Any, allowed: set[str], default: str) -> str:
        text = self._safe_str(value, default).lower()
        return text if text in allowed else default

    def _coerce_step_text(self, raw: Any) -> str:
        if isinstance(raw, dict):
            return self._safe_str(raw.get("text") or raw.get("title") or raw.get("label"))
        return self._safe_str(raw)

    # =========================
    # STEP NORMALIZATION
    # =========================

    def normalize_step(
        self,
        step: Any,
        index: int = 0,
        default_status: str = "pending",
    ) -> Optional[Dict[str, Any]]:
        if step is None:
            return None

        if isinstance(step, str):
            text = self._safe_str(step)
            if not text:
                return None
            return {
                "id": f"step_{index + 1}",
                "text": text,
                "status": self._normalize_status(default_status, self.STEP_STATUSES, "pending"),
                "notes": "",
                "started_at": "",
                "completed_at": "",
                "blocked_at": "",
                "failed_at": "",
                "meta": {},
            }

        if not isinstance(step, dict):
            return None

        text = self._coerce_step_text(step)
        if not text:
            return None

        status = self._normalize_status(
            step.get("status"),
            self.STEP_STATUSES,
            default_status,
        )

        normalized = {
            "id": self._safe_str(step.get("id"), f"step_{index + 1}"),
            "text": text,
            "status": status,
            "notes": self._safe_str(step.get("notes")),
            "started_at": self._safe_str(step.get("started_at")),
            "completed_at": self._safe_str(step.get("completed_at")),
            "blocked_at": self._safe_str(step.get("blocked_at")),
            "failed_at": self._safe_str(step.get("failed_at")),
            "meta": deepcopy(step.get("meta")) if isinstance(step.get("meta"), dict) else {},
        }

        now = self.iso_now()

        if status == "running" and not normalized["started_at"]:
            normalized["started_at"] = now

        if status == "completed" and not normalized["completed_at"]:
            normalized["completed_at"] = now
            if not normalized["started_at"]:
                normalized["started_at"] = now

        if status == "blocked" and not normalized["blocked_at"]:
            normalized["blocked_at"] = now
            if not normalized["started_at"]:
                normalized["started_at"] = now

        if status == "failed" and not normalized["failed_at"]:
            normalized["failed_at"] = now
            if not normalized["started_at"]:
                normalized["started_at"] = now

        return normalized

    def normalize_steps(self, steps: Any) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []

        for index, raw in enumerate(self._safe_list(steps)):
            step = self.normalize_step(raw, index=index)
            if step:
                normalized.append(step)

        return normalized

    # =========================
    # EXECUTION NORMALIZATION
    # =========================

    def _derive_execution_status(
        self,
        steps: List[Dict[str, Any]],
        fallback: str = "planned",
    ) -> str:
        if not steps:
            return fallback

        statuses = [self._safe_str(step.get("status")).lower() for step in steps]

        if any(status == "failed" for status in statuses):
            return "failed"

        if any(status == "blocked" for status in statuses):
            return "blocked"

        if statuses and all(status == "completed" for status in statuses):
            return "completed"

        if any(status == "running" for status in statuses):
            return "running"

        if any(status == "completed" for status in statuses):
            return "running"

        return "planned"

    def _find_current_step_text(self, steps: List[Dict[str, Any]]) -> str:
        for step in steps:
            if self._safe_str(step.get("status")).lower() == "running":
                return self._safe_str(step.get("text"))
        for step in steps:
            if self._safe_str(step.get("status")).lower() == "blocked":
                return self._safe_str(step.get("text"))
        for step in steps:
            if self._safe_str(step.get("status")).lower() == "pending":
                return self._safe_str(step.get("text"))
        return ""

    def _count_step_statuses(self, steps: List[Dict[str, Any]]) -> Dict[str, int]:
        counts = {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "blocked": 0,
            "failed": 0,
            "total": len(steps),
        }
        for step in steps:
            status = self._safe_str(step.get("status")).lower()
            if status in counts:
                counts[status] += 1
        return counts

    def normalize_execution(self, execution: Any) -> Dict[str, Any]:
        if not isinstance(execution, dict):
            execution = {}

        steps = self.normalize_steps(execution.get("steps"))
        derived_status = self._derive_execution_status(steps, fallback="planned")

        status = self._normalize_status(
            execution.get("status"),
            self.EXECUTION_STATUSES,
            derived_status,
        )

        now = self.iso_now()

        normalized = {
            "id": self._safe_str(execution.get("id"), self.make_id("exec")),
            "type": "execution_run",
            "title": self._safe_str(execution.get("title"), "Execution Run"),
            "status": status,
            "goal": self._safe_str(execution.get("goal")),
            "steps": steps,
            "current_step": self._safe_str(execution.get("current_step")),
            "result": self._safe_str(execution.get("result")),
            "error": self._safe_str(execution.get("error")),
            "created_at": self._safe_str(execution.get("created_at"), now),
            "updated_at": self._safe_str(execution.get("updated_at"), now),
            "completed_at": self._safe_str(execution.get("completed_at")),
            "meta": deepcopy(execution.get("meta")) if isinstance(execution.get("meta"), dict) else {},
        }

        if not normalized["current_step"]:
            normalized["current_step"] = self._find_current_step_text(steps)

        if normalized["status"] == "completed":
            normalized["current_step"] = ""
            if not normalized["completed_at"]:
                normalized["completed_at"] = now

        if normalized["status"] == "failed" and not normalized["error"]:
            normalized["error"] = "Execution failed."

        normalized["meta"]["step_counts"] = self._count_step_statuses(steps)

        return normalized

    # =========================
    # CREATE / START
    # =========================

    def new_execution(
        self,
        title: str,
        goal: str = "",
        steps: Optional[List[Any]] = None,
        status: str = "planned",
        meta: Optional[Dict[str, Any]] = None,
        auto_start: bool = True,
    ) -> Dict[str, Any]:
        now = self.iso_now()
        normalized_steps = self.normalize_steps(steps or [])
        normalized_status = self._normalize_status(status, self.EXECUTION_STATUSES, "planned")

        if normalized_steps and auto_start and normalized_status == "planned":
            first_pending_index = next(
                (i for i, step in enumerate(normalized_steps) if step["status"] == "pending"),
                None,
            )
            if first_pending_index is not None:
                normalized_steps[first_pending_index]["status"] = "running"
                normalized_steps[first_pending_index]["started_at"] = now
                normalized_status = "running"

        execution = {
            "id": self.make_id("exec"),
            "type": "execution_run",
            "title": self._safe_str(title, "Execution Run"),
            "status": normalized_status,
            "goal": self._safe_str(goal),
            "steps": normalized_steps,
            "current_step": self._find_current_step_text(normalized_steps),
            "result": "",
            "error": "",
            "created_at": now,
            "updated_at": now,
            "completed_at": "",
            "meta": deepcopy(meta) if isinstance(meta, dict) else {},
        }

        return self.normalize_execution(execution)

    def start_execution(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        execution = self.normalize_execution(execution)
        if execution["status"] in {"completed", "failed"}:
            return execution

        if execution["steps"]:
            found_running = False
            for step in execution["steps"]:
                if step["status"] == "running":
                    found_running = True
                    break

            if not found_running:
                for step in execution["steps"]:
                    if step["status"] == "pending":
                        step["status"] = "running"
                        step["started_at"] = step["started_at"] or self.iso_now()
                        break

        execution["status"] = self._derive_execution_status(execution["steps"], fallback="running")
        execution["current_step"] = self._find_current_step_text(execution["steps"])
        execution["updated_at"] = self.iso_now()
        return self.normalize_execution(execution)

    # =========================
    # STEP HELPERS
    # =========================

    def _find_step_index(
        self,
        steps: List[Dict[str, Any]],
        step_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[int]:
        if step_id:
            for i, step in enumerate(steps):
                if self._safe_str(step.get("id")) == self._safe_str(step_id):
                    return i

        if status:
            for i, step in enumerate(steps):
                if self._safe_str(step.get("status")).lower() == status.lower():
                    return i

        return None

    def _next_pending_step_index(self, steps: List[Dict[str, Any]]) -> Optional[int]:
        for i, step in enumerate(steps):
            if self._safe_str(step.get("status")).lower() == "pending":
                return i
        return None

    # =========================
    # PROGRESSION
    # =========================

    def advance_execution_step(
        self,
        execution: Dict[str, Any],
        completed_step_id: Optional[str] = None,
        completed_note: str = "",
        next_step_id: Optional[str] = None,
        result: str = "",
    ) -> Dict[str, Any]:
        execution = self.normalize_execution(execution)
        if execution["status"] in {"completed", "failed"}:
            return execution

        now = self.iso_now()
        steps = execution["steps"]

        running_index = self._find_step_index(steps, step_id=completed_step_id)
        if running_index is None:
            running_index = self._find_step_index(steps, status="running")

        if running_index is not None:
            steps[running_index]["status"] = "completed"
            steps[running_index]["completed_at"] = now
            if not steps[running_index]["started_at"]:
                steps[running_index]["started_at"] = now
            if completed_note:
                steps[running_index]["notes"] = self._safe_str(completed_note)

        next_index = self._find_step_index(steps, step_id=next_step_id)
        if next_index is None or self._safe_str(steps[next_index].get("status")).lower() not in {"pending", "running"}:
            next_index = self._next_pending_step_index(steps)

        if next_index is not None:
            steps[next_index]["status"] = "running"
            steps[next_index]["started_at"] = steps[next_index]["started_at"] or now
            execution["status"] = "running"
            execution["current_step"] = self._safe_str(steps[next_index]["text"])
        else:
            execution["status"] = "completed"
            execution["current_step"] = ""
            execution["completed_at"] = now

        if result:
            execution["result"] = self._safe_str(result)

        execution["updated_at"] = now
        return self.normalize_execution(execution)

    def set_step_running(
        self,
        execution: Dict[str, Any],
        step_id: str,
        note: str = "",
    ) -> Dict[str, Any]:
        execution = self.normalize_execution(execution)
        if execution["status"] in {"completed", "failed"}:
            return execution

        now = self.iso_now()
        steps = execution["steps"]

        for step in steps:
            if step["status"] == "running" and step["id"] != step_id:
                step["status"] = "pending"

        target_index = self._find_step_index(steps, step_id=step_id)
        if target_index is None:
            return execution

        steps[target_index]["status"] = "running"
        steps[target_index]["started_at"] = steps[target_index]["started_at"] or now
        if note:
            steps[target_index]["notes"] = self._safe_str(note)

        execution["status"] = "running"
        execution["current_step"] = self._safe_str(steps[target_index]["text"])
        execution["updated_at"] = now
        return self.normalize_execution(execution)

    def block_execution(
        self,
        execution: Dict[str, Any],
        reason: str = "",
        blocked_step_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        execution = self.normalize_execution(execution)
        if execution["status"] in {"completed", "failed"}:
            return execution

        now = self.iso_now()
        steps = execution["steps"]

        target_index = self._find_step_index(steps, step_id=blocked_step_id)
        if target_index is None:
            target_index = self._find_step_index(steps, status="running")

        if target_index is not None:
            steps[target_index]["status"] = "blocked"
            steps[target_index]["blocked_at"] = now
            if not steps[target_index]["started_at"]:
                steps[target_index]["started_at"] = now
            if reason:
                steps[target_index]["notes"] = self._safe_str(reason)
            execution["current_step"] = self._safe_str(steps[target_index]["text"])

        execution["status"] = "blocked"
        if reason:
            execution["error"] = self._safe_str(reason)
        execution["updated_at"] = now
        return self.normalize_execution(execution)

    def unblock_execution(
        self,
        execution: Dict[str, Any],
        step_id: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        execution = self.normalize_execution(execution)
        if execution["status"] in {"completed", "failed"}:
            return execution

        now = self.iso_now()
        steps = execution["steps"]

        target_index = self._find_step_index(steps, step_id=step_id)
        if target_index is None:
            target_index = self._find_step_index(steps, status="blocked")

        if target_index is None:
            return execution

        steps[target_index]["status"] = "running"
        steps[target_index]["started_at"] = steps[target_index]["started_at"] or now
        if note:
            steps[target_index]["notes"] = self._safe_str(note)

        execution["status"] = "running"
        execution["error"] = ""
        execution["current_step"] = self._safe_str(steps[target_index]["text"])
        execution["updated_at"] = now
        return self.normalize_execution(execution)

    def complete_execution(
        self,
        execution: Dict[str, Any],
        result: str = "",
    ) -> Dict[str, Any]:
        execution = self.normalize_execution(execution)
        now = self.iso_now()

        for step in execution["steps"]:
            if step["status"] in {"pending", "running", "blocked"}:
                step["status"] = "completed"
                if not step["started_at"]:
                    step["started_at"] = now
                step["completed_at"] = now

        execution["status"] = "completed"
        execution["current_step"] = ""
        execution["result"] = self._safe_str(result)
        execution["error"] = ""
        execution["completed_at"] = now
        execution["updated_at"] = now
        return self.normalize_execution(execution)

    def fail_execution(
        self,
        execution: Dict[str, Any],
        error: str = "",
        failed_step_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        execution = self.normalize_execution(execution)
        now = self.iso_now()
        target_index = self._find_step_index(execution["steps"], step_id=failed_step_id)

        if target_index is None:
            target_index = self._find_step_index(execution["steps"], status="running")

        if target_index is None:
            target_index = self._find_step_index(execution["steps"], status="blocked")

        if target_index is not None:
            execution["steps"][target_index]["status"] = "failed"
            execution["steps"][target_index]["notes"] = self._safe_str(error, "Execution failed.")
            execution["steps"][target_index]["failed_at"] = now
            if not execution["steps"][target_index]["started_at"]:
                execution["steps"][target_index]["started_at"] = now

        execution["status"] = "failed"
        execution["error"] = self._safe_str(error, "Execution failed.")
        execution["updated_at"] = now
        return self.normalize_execution(execution)

    # =========================
    # UPDATE / MERGE
    # =========================

    def update_execution(
        self,
        execution: Dict[str, Any],
        updates: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        execution = self.normalize_execution(execution)
        updates = self._safe_dict(updates)

        merged = deepcopy(execution)

        if "title" in updates:
            merged["title"] = self._safe_str(updates.get("title"), merged["title"])

        if "goal" in updates:
            merged["goal"] = self._safe_str(updates.get("goal"), merged["goal"])

        if "result" in updates:
            merged["result"] = self._safe_str(updates.get("result"), merged["result"])

        if "error" in updates:
            merged["error"] = self._safe_str(updates.get("error"), merged["error"])

        if "status" in updates:
            merged["status"] = self._normalize_status(
                updates.get("status"),
                self.EXECUTION_STATUSES,
                merged["status"],
            )

        if "meta" in updates and isinstance(updates.get("meta"), dict):
            merged_meta = deepcopy(merged.get("meta") or {})
            merged_meta.update(deepcopy(updates["meta"]))
            merged["meta"] = merged_meta

        if "steps" in updates:
            merged["steps"] = self.normalize_steps(updates.get("steps"))

        if "current_step" in updates:
            merged["current_step"] = self._safe_str(updates.get("current_step"))

        merged["updated_at"] = self.iso_now()
        return self.normalize_execution(merged)

    # =========================
    # ARTIFACT + VIEWER
    # =========================

    def to_artifact_payload(
        self,
        execution: Dict[str, Any],
        session_id: str = "",
        artifact_id: str = "",
    ) -> Dict[str, Any]:
        execution = self.normalize_execution(execution)
        viewer = self.to_artifact_viewer(execution)

        payload = {
            "id": self._safe_str(artifact_id),
            "session_id": self._safe_str(session_id),
            "kind": "execution_run",
            "title": execution["title"],
            "body": viewer.get("body") or "",
            "viewer": viewer,
            "meta": {
                "execution_id": execution.get("id", ""),
                "status": execution.get("status", "planned"),
                "goal": execution.get("goal", ""),
                "current_step": execution.get("current_step", ""),
                "steps": deepcopy(execution.get("steps", [])),
                "result": execution.get("result", ""),
                "error": execution.get("error", ""),
                "completed_at": execution.get("completed_at", ""),
                "step_counts": deepcopy(execution.get("meta", {}).get("step_counts", {})),
            },
        }

        if not payload["id"]:
            payload.pop("id", None)

        return payload

    def build_execution_reply(self, execution: Dict[str, Any]) -> str:
        execution = self.normalize_execution(execution)

        lines: List[str] = []
        title = self._safe_str(execution.get("title"), "Execution Run")
        status = self._safe_str(execution.get("status")).upper()
        goal = self._safe_str(execution.get("goal"))
        current_step = self._safe_str(execution.get("current_step"))
        result = self._safe_str(execution.get("result"))
        error = self._safe_str(execution.get("error"))
        counts = self._safe_dict(execution.get("meta", {}).get("step_counts"))

        lines.append(f"{title} [{status}]")

        if goal:
            lines.append(f"Goal: {goal}")

        if execution["steps"]:
            lines.append("Steps:")
            for step in execution["steps"]:
                marker = {
                    "pending": "-",
                    "running": "→",
                    "completed": "✓",
                    "blocked": "!",
                    "failed": "✗",
                }.get(step["status"], "-")
                lines.append(f"{marker} {step['text']}")

        if counts:
            lines.append(
                "Progress: "
                f"{counts.get('completed', 0)}/{counts.get('total', 0)} complete"
            )

        if current_step:
            lines.append(f"Current step: {current_step}")

        if result:
            lines.append(f"Result: {result}")

        if error:
            lines.append(f"Error: {error}")

        return "\n".join(lines).strip()

    def to_artifact_viewer(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        execution = self.normalize_execution(execution)

        body_lines: List[str] = []

        if execution["goal"]:
            body_lines.append(f"Goal: {execution['goal']}")
            body_lines.append("")

        if execution["steps"]:
            body_lines.append("Steps:")
            for step in execution["steps"]:
                marker = {
                    "pending": "[ ]",
                    "running": "[>]",
                    "completed": "[x]",
                    "blocked": "[!]",
                    "failed": "[x!]",
                }.get(step["status"], "[ ]")
                line = f"{marker} {step['text']}"
                notes = self._safe_str(step.get("notes"))
                if notes:
                    line = f"{line} — {notes}"
                body_lines.append(line)

        counts = self._safe_dict(execution.get("meta", {}).get("step_counts"))
        if counts:
            body_lines.append("")
            body_lines.append(
                f"Progress: {counts.get('completed', 0)}/{counts.get('total', 0)} complete"
            )

        if execution["current_step"]:
            body_lines.append("")
            body_lines.append(f"Current step: {execution['current_step']}")

        if execution["result"]:
            body_lines.append("")
            body_lines.append(f"Result: {execution['result']}")

        if execution["error"]:
            body_lines.append("")
            body_lines.append(f"Error: {execution['error']}")

        return {
            "kind": "execution_run",
            "title": execution["title"],
            "body": "\n".join(body_lines).strip(),
            "meta": {
                "status": execution["status"],
                "goal": execution["goal"],
                "current_step": execution["current_step"],
                "result": execution["result"],
                "error": execution["error"],
                "steps": deepcopy(execution["steps"]),
                "created_at": execution["created_at"],
                "updated_at": execution["updated_at"],
                "completed_at": execution.get("completed_at", ""),
                "step_counts": deepcopy(execution.get("meta", {}).get("step_counts", {})),
            },
        }

    # =========================
    # LOOKUP HELPERS
    # =========================

    def find_execution_artifact(
        self,
        artifacts: List[Dict[str, Any]],
        execution_id: str,
        session_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        execution_id = self._safe_str(execution_id)
        session_id = self._safe_str(session_id)

        if not execution_id:
            return None

        for artifact in reversed(self._safe_list(artifacts)):
            if not isinstance(artifact, dict):
                continue
            meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
            if self._safe_str(meta.get("execution_id")) != execution_id:
                continue
            if session_id and self._safe_str(artifact.get("session_id")) != session_id:
                continue
            return artifact

        return None

    def execution_from_artifact(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        artifact = self._safe_dict(artifact)
        meta = self._safe_dict(artifact.get("meta"))
        viewer = self._safe_dict(artifact.get("viewer"))

        execution = {
            "id": self._safe_str(meta.get("execution_id")),
            "title": self._safe_str(artifact.get("title"), "Execution Run"),
            "status": self._safe_str(meta.get("status"), "planned"),
            "goal": self._safe_str(meta.get("goal")),
            "current_step": self._safe_str(meta.get("current_step")),
            "result": self._safe_str(meta.get("result")),
            "error": self._safe_str(meta.get("error")),
            "steps": deepcopy(meta.get("steps")) if isinstance(meta.get("steps"), list) else [],
            "created_at": self._safe_str(artifact.get("created_at")),
            "updated_at": self._safe_str(artifact.get("updated_at")),
            "completed_at": self._safe_str(meta.get("completed_at")),
            "meta": deepcopy(viewer.get("meta")) if isinstance(viewer.get("meta"), dict) else {},
        }

        return self.normalize_execution(execution)

    # =========================
    # PLANNING BOOTSTRAP
    # =========================

    def build_planning_execution(
        self,
        user_text: str,
        title: str = "",
        max_steps: int = 5,
    ) -> Dict[str, Any]:
        cleaned_user_text = self._safe_str(user_text, "Complete the requested task.")
        execution_title = self._safe_str(title, "Execution Plan")

        seed_steps = [
            "Inspect the current state and constraints",
            "Choose the safest implementation path",
            "Apply the required change",
            "Verify the result",
            "Summarize outcome and next move",
        ][: max(1, min(max_steps, 8))]

        return self.new_execution(
            title=execution_title,
            goal=cleaned_user_text,
            steps=seed_steps,
            status="planned",
            meta={"source": "planning_v2"},
            auto_start=True,
        )