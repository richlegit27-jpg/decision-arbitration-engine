from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


EXECUTION_TRIGGER_WORDS = {
    "k",
    "ok",
    "okay",
    "next",
    "continue",
    "run it",
    "run step",
    "execute",
    "go",
}


DEFAULT_EXECUTION_STATE_PATH = Path("C:/Users/Owner/nova/data/nova_execution_state.json")


class ChatExecutionService:
    """
    Nova execution lane.

    Purpose:
    - Keep execution state predictable.
    - Let short commands like k/next/continue/run it advance the current mission.
    - Persist execution state so refresh/restart does not lose the active mission.
    """

    def __init__(self, state_path: Optional[str] = None) -> None:
        self.state_path = Path(state_path) if state_path else DEFAULT_EXECUTION_STATE_PATH
        self._states: Dict[str, Dict[str, Any]] = {}
        self._load_states()

    def is_execution_trigger(self, user_text: str) -> bool:
        clean = self._clean_text(user_text)
        return clean in EXECUTION_TRIGGER_WORDS

    def start(
        self,
        session_id: str,
        goal: str,
        steps: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        safe_session_id = self._safe_session_id(session_id)
        safe_goal = str(goal or "Untitled mission").strip() or "Untitled mission"
        safe_steps = self._normalize_steps(steps)

        state = {
            "status": "ready",
            "goal": safe_goal,
            "steps": safe_steps,
            "current_index": 0,
            "current_step": safe_steps[0] if safe_steps else None,
            "history": [],
            "waiting": True,
            "complete": False,
            "error": None,
        }

        self._states[safe_session_id] = state
        self._save_states()

        logger.info(
            "[ChatExecutionService] started session=%s goal=%r steps=%s",
            safe_session_id,
            safe_goal,
            len(safe_steps),
        )
        return self.get_state(safe_session_id)

    def get_state(self, session_id: str) -> Dict[str, Any]:
        safe_session_id = self._safe_session_id(session_id)
        state = self._states.get(safe_session_id)

        if not state:
            return {
                "status": "idle",
                "goal": None,
                "steps": [],
                "current_index": 0,
                "current_step": None,
                "history": [],
                "waiting": False,
                "complete": False,
                "error": None,
            }

        return self._copy_state(state)

    def advance(self, session_id: str) -> Dict[str, Any]:
        safe_session_id = self._safe_session_id(session_id)
        state = self._states.get(safe_session_id)

        if not state:
            return {
                "status": "idle",
                "goal": None,
                "steps": [],
                "current_index": 0,
                "current_step": None,
                "history": [],
                "waiting": False,
                "complete": False,
                "error": "No active execution mission. Start one with auto-plan <goal>.",
            }

        if state.get("complete") or state.get("status") == "complete":
            state["status"] = "complete"
            state["waiting"] = False
            state["complete"] = True
            state["current_step"] = None
            self._save_states()
            return self._copy_state(state)

        steps = state.get("steps") or []
        current_index = int(state.get("current_index") or 0)

        if current_index >= len(steps):
            state["status"] = "complete"
            state["waiting"] = False
            state["complete"] = True
            state["current_step"] = None
            self._save_states()
            return self._copy_state(state)

        current_step = steps[current_index]
        state["status"] = "running"
        state["waiting"] = False
        state["current_step"] = current_step

        state.setdefault("history", []).append(
            {
                "index": current_index,
                "step": current_step,
                "status": "complete",
            }
        )

        next_index = current_index + 1
        state["current_index"] = next_index

        if next_index >= len(steps):
            state["status"] = "complete"
            state["waiting"] = False
            state["complete"] = True
            state["current_step"] = None
        else:
            state["status"] = "waiting"
            state["waiting"] = True
            state["complete"] = False
            state["current_step"] = steps[next_index]

        self._save_states()

        logger.info(
            "[ChatExecutionService] advanced session=%s status=%s index=%s",
            safe_session_id,
            state.get("status"),
            state.get("current_index"),
        )
        return self._copy_state(state)

    def run_all(self, session_id: str, max_steps: int = 25) -> Dict[str, Any]:
        safe_session_id = self._safe_session_id(session_id)

        for _ in range(max_steps):
            state = self.advance(safe_session_id)
            if state.get("status") in {"idle", "complete", "failed"}:
                return state

        state = self.get_state(safe_session_id)
        state["status"] = "failed"
        state["error"] = "Execution stopped because max_steps was reached."
        self._states[safe_session_id] = state
        self._save_states()
        return self._copy_state(state)

    def reset(self, session_id: str) -> Dict[str, Any]:
        safe_session_id = self._safe_session_id(session_id)
        self._states.pop(safe_session_id, None)
        self._save_states()
        return self.get_state(safe_session_id)

    def format_reply(self, state: Dict[str, Any]) -> str:
        status = state.get("status") or "idle"
        goal = state.get("goal")
        current_step = state.get("current_step")
        current_index = int(state.get("current_index") or 0)
        steps = state.get("steps") or []
        total = len(steps)
        error = state.get("error")

        if status == "idle":
            return error or "No active execution mission. Start one with: auto-plan <goal>"

        if status == "complete":
            if goal:
                return f"Execution complete: {goal}"
            return "Execution complete."

        if error:
            return error

        if current_step:
            step_number = min(current_index + 1, total) if total else current_index + 1
            return f"Execution {status}. Step {step_number}/{total}: {current_step}"

        return f"Execution {status}."

    def _load_states(self) -> None:
        try:
            if not self.state_path.exists():
                self._states = {}
                return

            raw = self.state_path.read_text(encoding="utf-8").strip()
            if not raw:
                self._states = {}
                return

            data = json.loads(raw)
            if isinstance(data, dict):
                self._states = data
            else:
                self._states = {}

            logger.info(
                "[ChatExecutionService] loaded execution states count=%s path=%s",
                len(self._states),
                self.state_path,
            )
        except Exception:
            logger.exception("[ChatExecutionService] failed to load execution state")
            self._states = {}

    def _save_states(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
            temp_path.write_text(
                json.dumps(self._states, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            temp_path.replace(self.state_path)
        except Exception:
            logger.exception("[ChatExecutionService] failed to save execution state")

    def _normalize_steps(self, steps: Optional[List[Any]]) -> List[str]:
        if not steps:
            return [
                "Design the solution",
                "Implement the change",
                "Verify the result",
            ]

        normalized = []
        for item in steps:
            if isinstance(item, dict):
                title = (
                    item.get("title")
                    or item.get("name")
                    or item.get("step")
                    or item.get("description")
                    or str(item)
                )
                normalized.append(str(title).strip())
            else:
                normalized.append(str(item).strip())

        return [item for item in normalized if item]

    def _clean_text(self, user_text: str) -> str:
        return " ".join(str(user_text or "").strip().lower().split())

    def _safe_session_id(self, session_id: str) -> str:
        return str(session_id or "default").strip() or "default"

    def _copy_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": state.get("status"),
            "goal": state.get("goal"),
            "steps": list(state.get("steps") or []),
            "current_index": int(state.get("current_index") or 0),
            "current_step": state.get("current_step"),
            "history": list(state.get("history") or []),
            "waiting": bool(state.get("waiting")),
            "complete": bool(state.get("complete")),
            "error": state.get("error"),
        }


ExecutionService = ChatExecutionService


# NOVA_EXECUTION_POST_COMPLETE_IDLE_GUARD_20260609
# If user sends k/next/continue after a mission is already complete,
# return idle instead of repeating "Execution complete: <goal>".

try:
    _nova_original_execution_advance_20260609 = ChatExecutionService.advance

    def _nova_execution_advance_post_complete_idle_20260609(self, session_id: str):
        safe_session_id = self._safe_session_id(session_id)

        try:
            state = self._states.get(safe_session_id) or {}

            if isinstance(state, dict) and (
                state.get("complete") is True
                or str(state.get("status") or "").strip().lower() in {"complete", "completed"}
            ):
                self._states[safe_session_id] = {
                    "status": "idle",
                    "goal": None,
                    "steps": [],
                    "current_index": 0,
                    "current_step": None,
                    "history": [],
                    "waiting": False,
                    "complete": False,
                    "error": "No active execution mission. Start one with: auto-plan <goal>",
                }

                self._save_states()

                return self._copy_state(self._states[safe_session_id])
        except Exception:
            pass

        return _nova_original_execution_advance_20260609(self, session_id)

    ChatExecutionService.advance = _nova_execution_advance_post_complete_idle_20260609

except Exception:
    pass

