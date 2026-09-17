from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from nova_backend.services.execution_step_service import (
    ExecutionStepService,
)

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

    def __init__(
        self,
        chat_service=None,
        execution_step_service=None,
        python_runner=None,
        approval_service=None,
        ai_execution_service=None,
        tool_executor=None,
    ):
        self.chat_service = chat_service

        self.execution_step_service = (
            execution_step_service
            or ExecutionStepService(
                safe_str=self._safe_str,
                python_runner=python_runner,
                approval_service=approval_service,
                ai_execution_service=ai_execution_service,
                tool_executor=tool_executor,
            )
        )

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

    def _extract_terminal_command(
        self,
        user_text: str,
    ) -> str:
        text = self._safe_str(user_text).strip()

        if not text:
            return ""

        import re

        # Prefer explicit fenced or backtick-wrapped commands.
        fenced_match = re.search(
            r"```(?:powershell|pwsh|cmd|bash|sh|shell)?\s*([\s\S]*?)```",
            text,
            flags=re.IGNORECASE,
        )

        if fenced_match:
            command = fenced_match.group(1).strip()

            if command:
                return command

        backtick_match = re.search(
            r"`([^`]+)`",
            text,
        )

        if backtick_match:
            command = backtick_match.group(1).strip()

            if command:
                return command

        lowered = text.lower()

        markers = (
            "execute this terminal command now:",
            "execute this terminal command:",
            "execute terminal command:",
            "run exactly this terminal command:",
            "run this terminal command:",
            "run the following terminal command:",
            "run terminal command:",
            "terminal command:",
            "command:",
            "runs:",
            "run:",
        )

        for marker in markers:
            index = lowered.find(marker)

            if index < 0:
                continue

            command = text[
                index + len(marker):
            ].strip()

            if not command:
                continue

            command = command.strip("`").strip()

            if (
                len(command) >= 2
                and command[0] in {'"', "'"}
                and command[-1] == command[0]
            ):
                command = command[1:-1].strip()

            if command:
                return command

        return ""

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
            **deepcopy(step),
            "id": self._safe_str(
                step.get("id"),
                f"step_{index + 1}",
            ),
            "text": text,
            "status": status,
            "notes": self._safe_str(
                step.get("notes")
            ),
            "started_at": self._safe_str(
                step.get("started_at")
            ),
            "completed_at": self._safe_str(
                step.get("completed_at")
            ),
            "blocked_at": self._safe_str(
                step.get("blocked_at")
            ),
            "failed_at": self._safe_str(
                step.get("failed_at")
            ),
            "meta": (
                deepcopy(step.get("meta"))
                if isinstance(step.get("meta"), dict)
                else {}
            ),
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
            "history": (
                execution.get("history")
                if isinstance(execution.get("history"), list)
                else []
            ),
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
                    "running": "ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢",
                    "completed": "ÃƒÂ¢Ã…â€œÃ¢â‚¬Å“",
                    "blocked": "!",
                    "failed": "ÃƒÂ¢Ã…â€œÃ¢â‚¬â€",
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
                    line = f"{line} ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â {notes}"
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
        cleaned_user_text = self._safe_str(
            user_text,
            "Complete the requested task.",
        ).strip()

        execution_title = self._safe_str(
            title,
            "Execution Plan",
        )

        print(
            "[PLANNER INPUT DEBUG]",
            {
                "user_text_repr": repr(user_text),
                "cleaned_user_text_repr": repr(cleaned_user_text),
                "length": len(cleaned_user_text),
            },
            flush=True,
        )

        import re
        file_patterns = [
            re.compile(
                r"""
                ^\s*
                (?:create|write|overwrite|save)
                (?:\s+or\s+overwrite)?
                \s+
                (?:the\s+)?
                (?:file\s+)?
                (?P<target_file>.+?)
                \s+with\s+
                (?:exactly\s+)?
                (?:this\s+)?
                content\s*:\s*
                (?P<content>[\s\S]*?)
                \s*$
                """,
                flags=re.IGNORECASE | re.VERBOSE,
            ),

            re.compile(
                r"""
                ^\s*
                create\s+
                (?:the\s+)?
                file\s+
                (?P<target_file>.+?)
                \s+
                with\s+
                (?:
                    (?:the\s+)?exact\s+
                    |
                    exactly\s+
                )?
                (?:this\s+)?
                content\s*:\s*
                (?P<content>[\s\S]*?)
                \s*$
                """,
                flags=re.IGNORECASE | re.VERBOSE,
            ),

            re.compile(
                r"""
                ^\s*
                create\s+
                (?:a\s+)?
                file
                (?:\s+named|\s+called)?
                \s+
                (?P<target_file>.+?)
                \s+
                containing\s+
                (?:exactly\s+)?
                (?P<content>[\s\S]*?)
                \s*$
                """,
                flags=re.IGNORECASE | re.VERBOSE,
            ),
        ]
        file_match = None

        print(
            "[PLANNER FILE PARSER DEBUG]",
            {
                "pattern_count": len(file_patterns),
                "input": cleaned_user_text,
            },
            flush=True,
        )

        for pattern in file_patterns:
            file_match = pattern.match(cleaned_user_text)
            if file_match:
                break

        print(
            "[PLANNER FILE PARSER RESULT]",
            {
                "matched": bool(file_match),
                "target_file": (
                    file_match.group("target_file")
                    if file_match
                    else None
                ),
                "content": (
                    file_match.group("content")
                    if file_match
                    else None
                ),
            },
            flush=True,
        )

        if file_match:
            target_file = (
                file_match.group("target_file")
                .strip()
                .rstrip(":")
                .strip()
                .strip("\"'")
            )

            content = (
                file_match.group("content")
                .strip()
            )

            # Remove a trailing verification clause from the requested
            # file content. The verification instruction belongs to the
            # second execution step, not inside the file itself.
            content = re.split(
                r"\s*,\s*(?:then\s+)?verify\b"
                r"|\s+(?:then\s+)?verify\b",
                content,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip()

            # Remove one prose-period suffix only.
            if content.endswith(".") and not content.endswith(".."):
                content = content[:-1]

            content = content.strip("\"'")

            print(
                "[PLANNER CONCRETE FILE MATCH]",
                {
                    "target_file": target_file,
                    "content": content,
                },
                flush=True,
            )

            seed_steps = [
                {
                    "id": "create-requested-file",
                    "title": "Create requested file",
                    "text": cleaned_user_text,
                    "description": (
                        "Create the requested file with the requested content."
                    ),
                    "action": "implement",
                    "status": "pending",
                    "target_file": target_file,
                    "target_files": [target_file],
                    "target_function": "",
                    "content": content,
                    "mutation_mode": "create",
                    "next_action": "execute",
                    "mutation_ready": True,
                    "payload_required": False,
                },
                {
                    "id": "verify-result",
                    "title": "Verify the result",
                    "text": (
                        "Verify that the requested file was created "
                        "with the requested content."
                    ),
                    "description": (
                        "Verify that the requested file was created "
                        "with the requested content."
                    ),
                    "action": "verify",
                    "status": "pending",
                },
            ][: max(1, min(max_steps, 8))]

            return self.new_execution(
                title=execution_title,
                goal=cleaned_user_text,
                steps=seed_steps,
                status="planned",
                meta={
                    "source": "planning_v6",
                    "step_action": "implement",
                    "mutation_request": True,
                    "terminal_request": False,
                    "target_file": target_file,
                    "content": content,
                    "mutation_mode": "create",
                },
                auto_start=True,
            )

        # ----------------------------------------------------------
        # GENERAL REQUEST CLASSIFICATION
        # ----------------------------------------------------------

        lowered_text = cleaned_user_text.lower()

        target_file = ""
        content = ""


        mutation_match = re.match(
            r"^\s*(fix|create|write|edit|modify|update|patch|replace|"
            r"change|delete|remove|append|prepend|save)\b",
            lowered_text,
        )

        terminal_match = re.match(
            r"^\s*(run|execute|shell|powershell|pwsh|cmd|bash|sh|"
            r"python|python3|pip|npm|node|git|curl|invoke-restmethod|"
            r"invoke-webrequest)\b",
            lowered_text,
        )

        extracted_command = ""

        if terminal_match and not mutation_match:
            extracted_command = self._extract_terminal_command(
                cleaned_user_text
            )

        if mutation_match:
            step_action = "implement"
            step_title = "Implement the requested change"
            step_description = (
                "Apply the requested file or project change directly. "
                "Do not execute the natural-language request as a shell command."
            )
        elif extracted_command:
            step_action = "command"
            step_title = "Execute the terminal command"
            step_description = cleaned_user_text
        else:
            step_action = "implement"
            step_title = "Execute the requested task"
            step_description = cleaned_user_text

        execute_step = {
            "id": "execute-request",
            "title": step_title,
            "text": cleaned_user_text,
            "description": step_description,
            "action": step_action,
            "status": "pending",
        }

        if mutation_match and target_file:
            execute_step["target_file"] = target_file
            execute_step["target_files"] = [target_file]
            execute_step["content"] = content
            execute_step["file_content"] = content
            execute_step["mutation_mode"] = "create"
            execute_step["mutation_ready"] = True
            execute_step["next_action"] = "execute"
            execute_step["payload_required"] = False

        if extracted_command:
            execute_step["command"] = extracted_command
            execute_step["shell_command"] = extracted_command

        seed_steps = [
            execute_step,
            {
                "id": "verify-result",
                "title": "Verify the result",
                "text": (
                    "Verify that the requested change was completed successfully."
                ),
                "description": (
                    "Verify that the requested change was completed successfully."
                ),
                "action": "verify",
                "status": "pending",
            },
        ][: max(1, min(max_steps, 8))]

        return self.new_execution(
            title=execution_title,
            goal=cleaned_user_text,
            steps=seed_steps,
            status="planned",
            meta={
                "source": "planning_v6",
                "step_action": step_action,
                "mutation_request": bool(mutation_match),
                "terminal_request": bool(extracted_command),
            },
            auto_start=True,
        )

    def execute_current_step(self, execution: Dict[str, Any]) -> str:
        execution = self.normalize_execution(execution)

        goal = self._safe_str(
            execution.get("goal")
        ).lower()

        current_step = self._safe_str(
            execution.get("current_step")
        ).lower()

        # ===== PLAN HANDLER =====
        if "plan" in goal:

            if "apply" in current_step:
                return """Plan:

Goal:
Create a clear actionable plan.

Steps:
1. Define the objective
2. Break into tasks
3. Prioritize tasks
4. Assign timeline
5. Identify resources
6. Execute
7. Review and adjust

Next action:
Write the exact goal in one sentence.
"""

            if "inspect" in current_step:
                return (
                    "State inspected. Missing inputs identified. "
                    "Ready to proceed."
                )

            if "safest" in current_step:
                return (
                    "Proceeding with a general-purpose plan structure "
                    "using assumptions."
                )

            if "verify" in current_step:
                return (
                    "Plan structure verified for completeness and usability."
                )

            if "summarize" in current_step:
                return (
                    "Plan created. Next step: refine based on real inputs."
                )

        # ===== REAL EXECUTION DELEGATION =====
        execution_steps = execution.get("steps") or []
        current_index = execution.get("current_index", 0)

        try:
            current_index = int(current_index)
        except (TypeError, ValueError):
            current_index = 0

        if not isinstance(execution_steps, list):
            execution_steps = []

        if not execution_steps:
            return "No executable steps were found."

        if current_index < 0 or current_index >= len(execution_steps):
            current_index = 0

        raw_step = execution_steps[current_index]

        if isinstance(raw_step, dict):
            step = dict(raw_step)
        else:
            step = {
                "text": self._safe_str(raw_step),
                "title": self._safe_str(raw_step),
            }

        execution_goal = self._safe_str(
            execution.get("goal")
        ).strip()

        # The planner currently creates a generic placeholder step.
        # Preserve the actual user request so the real executor can
        # extract target_file/content/command from it.
        if execution_goal:
            existing_goal = self._safe_str(
                step.get("goal")
            ).strip()

            existing_description = self._safe_str(
                step.get("description")
            ).strip()

            existing_text = self._safe_str(
                step.get("text")
            ).strip()

            if not existing_goal:
                step["goal"] = execution_goal

            if not existing_description:
                step["description"] = (
                    existing_text or execution_goal
                )

            if not existing_text:
                step["text"] = step["description"]

            generic_titles = {
                "implement the requested change",
                "implement the requested change.",
                "execute requested change",
                "implementation",
                "implement",
            }

            step_title = self._safe_str(
                step.get("title")
            ).strip().lower()

            if step_title in generic_titles:
                step["title"] = execution_goal

        if not self._safe_str(
            step.get("title")
        ).strip():
            step["title"] = self._safe_str(
                execution.get("current_step"),
                "Execute requested change",
            )

        if not self._safe_str(
            step.get("action")
        ).strip():
            execution_meta = execution.get("meta") or {}

            step["action"] = self._safe_str(
                execution_meta.get("step_action"),
                "implement",
            ).lower()

        step["status"] = "running"

        try:
            result = self.execution_step_service.execute_step_logic(
                session_id=self._safe_str(
                    execution.get("session_id")
                    or execution.get("id")
                ),
                step=step,
            )
        except TypeError:
            # Compatibility fallback for alternate method signatures.
            result = self.execution_step_service.execute_step_logic(
                self._safe_str(
                    execution.get("session_id")
                    or execution.get("id")
                ),
                step,
            )

        if isinstance(result, dict):
            execution_steps[current_index] = result
            execution["steps"] = execution_steps

            result_status = self._safe_str(
                result.get("status")
            ).lower()

            if result_status in {
                "completed",
                "failed",
                "blocked",
                "waiting",
            }:
                execution["status"] = result_status

            result_output = (
                result.get("output")
                or result.get("result")
                or result.get("message")
                or ""
            )

            if result_output:
                execution["last_output"] = self._safe_str(
                    result_output
                )

            return self._safe_str(
                result_output,
                "Execution step processed.",
            )

        execution_steps[current_index]["status"] = "completed"
        execution_steps[current_index]["output"] = self._safe_str(
            result
        )
        execution["steps"] = execution_steps
        execution["status"] = "completed"

        return self._safe_str(
            result,
            "Execution step completed.",
        )

    def serialize_move(self, move):
        if isinstance(move, dict):
            return move

        return {
            "id": str(getattr(move, "id", "")),
            "type": str(getattr(move, "type", "")),
            "payload": (
                getattr(move, "payload", {})
                if isinstance(
                    getattr(move, "payload", {}),
                    dict,
                )
                else {}
            ),
        }

    def apply_control_action(
        self,
        execution,
        action,
    ):
        execution = self.normalize_execution(execution)

        if action == "run_step":
            step_num = len(execution["steps"]) + 1
            step_title = f"Step {step_num}"

            execution["steps"].append(
                {
                    "title": step_title,
                    "status": "completed",
                    "output": "Step completed.",
                }
            )

            execution["history"].append(
                f"run_step: {step_title}"
            )
            execution["status"] = "completed"
            execution["last_action"] = action
            execution["current_step"] = step_title

        elif action == "run_all":
            start_num = len(execution["steps"]) + 1

            for offset in range(3):
                step_num = start_num + offset
                step_title = f"Step {step_num}"

                execution["steps"].append(
                    {
                        "title": step_title,
                        "status": "completed",
                        "output": "Step completed.",
                    }
                )

            execution["history"].append(
                "run_all: added 3 completed steps"
            )
            execution["status"] = "completed"
            execution["last_action"] = action
            execution["current_step"] = "Run all complete"

        elif action == "test_fail":
            step_num = len(execution["steps"]) + 1
            step_title = f"Failed Step {step_num}"

            execution["steps"].append(
                {
                    "title": step_title,
                    "status": "failed",
                    "output": "Simulated failure.",
                }
            )

            execution["history"].append(
                f"test_fail: {step_title}"
            )
            execution["status"] = "failed"
            execution["last_action"] = action
            execution["current_step"] = step_title

        elif action in ("retry", "retry_failed"):
            failed_index = None

            for i in range(
                len(execution["steps"]) - 1,
                -1,
                -1,
            ):
                step = execution["steps"][i]
                status = str(
                    step.get("status") or ""
                ).lower()

                if status in ("failed", "error"):
                    failed_index = i
                    break

            if failed_index is not None:
                failed_step = execution["steps"][failed_index]
                title = str(
                    failed_step.get("title")
                    or f"Step {failed_index + 1}"
                )

                failed_step["status"] = "completed"
                failed_step["output"] = "Retry successful."

                execution["status"] = "completed"
                execution["last_action"] = "retry_failed"
                execution["current_step"] = "Retry complete"
                execution["history"].append(
                    f"retry_failed: {title}"
                )
            else:
                execution["history"].append(
                    "retry_failed: no failed step found"
                )
                execution["status"] = "completed"
                execution["last_action"] = "retry_failed"
                execution["current_step"] = (
                    "No failed step found"
                )

        elif action == "stop":
            execution["history"].append("stop")
            execution["status"] = "blocked"
            execution["last_action"] = action
            execution["current_step"] = "Stopped"

        else:
            execution["history"].append(
                f"unknown action: {action}"
            )
            execution["status"] = "failed"
            execution["last_action"] = action
            execution["current_step"] = "Unknown action"

        return self.normalize_execution(execution)















