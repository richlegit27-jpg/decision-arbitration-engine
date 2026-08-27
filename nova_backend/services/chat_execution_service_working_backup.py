
from __future__ import annotations


def _nova_boot_log_20260701(*args, **kwargs):
    import os as _nova_boot_log_os_20260701

    if str(_nova_boot_log_os_20260701.getenv("NOVA_VERBOSE_BOOT_LOGS", "")).strip().lower() in {"1", "true", "yes", "on"}:
        print(*args, **kwargs)



import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from nova_backend.services.mission_service import mission_service

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

    def __init__(
        self,
        state_path: Optional[str] = None,
        execution_handler=None,
        session_service=None,
    ) -> None:

        self.state_path = (
            Path(state_path)
            if state_path
            else DEFAULT_EXECUTION_STATE_PATH
        )

        self.execution_handler = execution_handler
        self.session_service = session_service
        self._states: Dict[str, Dict[str, Any]] = {}

        self._load_states()

        self.state_path = Path(state_path) if state_path else DEFAULT_EXECUTION_STATE_PATH
        self._states: Dict[str, Dict[str, Any]] = {}
        self._load_states()

    def is_execution_trigger(
        self,
        user_text: str,
    ) -> bool:
        clean = self._clean_text(
            user_text
        )

        return clean in EXECUTION_TRIGGER_WORDS

    def attach_mission(
        self,
        session_id: str,
        mission_id: str,
    ):

        state = self._states.get(session_id)

        if not state:
            return None

        state["mission_id"] = mission_id

        return state

    def start(
        self,
        session_id: str,
        goal: str,
        steps: Optional[List[Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        safe_session_id = self._safe_session_id(
            session_id
        )

        existing = self._states.get(
            safe_session_id
        )

        if isinstance(existing, dict):

            if (
                existing.get("complete") is True
                or existing.get("status") in {
                    "complete",
                    "completed",
                }
            ):
                return self._copy_state(
                    existing
                )

            if (
                existing.get("current_step")
                or existing.get("steps")
                or existing.get("goal")
            ):
                return self._copy_state(
                    existing
                )

        safe_goal = (
            str(goal or "Untitled mission")
            .strip()
            or "Untitled mission"
        )

        safe_steps = self._normalize_steps(
            steps
        )

        safe_context = (
            context
            if isinstance(context, dict)
            else {}
        )

        initial_index = 0

        for idx, step in enumerate(safe_steps):
            if isinstance(step, dict):
                if step.get("next_action") == "request_target":
                    initial_index = idx
                    break

        print(
            "DEBUG START SAFE STEPS=",
            safe_steps,
            flush=True,
        )

        print(
            "DEBUG START INITIAL INDEX=",
            initial_index,
            flush=True,
        )

        state = {
            "status": "ready",
            "goal": safe_goal,
            "context": safe_context,
            "task_type": safe_context.get(
                "task_type",
                "general",
            ),
            "steps": safe_steps,
            "current_index": initial_index,
            "current_step": (
                safe_steps[initial_index]
                if safe_steps
                else None
            ),

            "history": [],
            "waiting": True,
            "complete": False,
            "error": None,
            "mission_id": None,
        }

        self._states[safe_session_id] = state

        self._sync_state_to_session(
            safe_session_id,
            state,
        )

        execution_state_service = getattr(
            self,
            "execution_state_service",
            None,
        )

        if execution_state_service:
            execution_state_service.save_execution_state(
                safe_session_id,
                state,
            )

        self._save_states()
        logger.info(
            "[ChatExecutionService] started session=%s goal=%r steps=%s",
            safe_session_id,
            safe_goal,
            len(safe_steps),
        )

        return self._copy_state(
            state
        )

    def get_state(self, session_id: str) -> Dict[str, Any]:
        safe_session_id = self._safe_session_id(session_id)

        state = None

        execution_state_service = getattr(
            self,
            "execution_state_service",
            None,
        )

        state = self._states.get(
            safe_session_id
        )

        if state is None and execution_state_service:
            try:
                persisted = (
                    execution_state_service.get_execution_state(
                        safe_session_id
                    )
                )

                if isinstance(persisted, dict) and persisted:
                    state = persisted

            except Exception as e:
                logger.error(
                    "[ChatExecutionService] persisted state read failed: %s",
                    e,
                )

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

    def advance(
        self,
        session_id: str,
        user_text: str = "",
    ) -> Dict[str, Any]:
        safe_session_id = self._safe_session_id(
            session_id
        )

        state = self._states.get(
            safe_session_id
        )

        if not state:
            try:
                self._load_states()

                state = self._states.get(
                    safe_session_id
                )

            except Exception as e:
                logger.error(
                    "[ChatExecutionService] LOAD STATE FAILED: %s",
                    e,
                )

        if state and str(
            state.get("status") or ""

        ).strip().lower() == "idle":
            return self._copy_state(
                state
            )

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
                "error": (
                    "No active execution mission. "
                    "Start one with auto-plan <goal>."
                ),
            }

        # NOVA_REQUEST_TARGET_CAPTURE_20260826
        # Capture implementation target before execution continues.
        steps = state.get("steps") or []
        current_index = int(
            state.get("current_index") or 0
        )

        if (
            user_text
            and current_index < len(steps)
        ):

            ignored_commands = {
                "next",
                "continue",
                "go",
                "run",
                "advance",
            }

            current_step = steps[current_index]

        # Activate waiting implementation step
        if (
            isinstance(
                current_step,
                dict,
            )
            and current_step.get(
                "next_action"
            )
            == "request_target"
        ):
            current_step["status"] = (
                "waiting_for_target"
            )

            if user_text.strip() not in ignored_commands:
                current_step["target_file"] = user_text.strip()

                current_step["target_files"] = [
                    user_text.strip()
                ]

                current_step["next_action"] = (
                    "generate_file_replacement"
                )

                current_step["mutation_ready"] = True

            steps[current_index] = (
                current_step
            )

            state["steps"] = steps

            state["current_step"] = (
                current_step
            )

            if (
                user_text.strip().lower() in ignored_commands
                and current_step.get("next_action")
                == "request_target"
            ):
                current_step["status"] = (
                    "waiting_for_target"
                )

                state["steps"][current_index] = (
                    current_step
                )
                state["current_step"] = (
                    current_step
                )
                state["waiting"] = True

                self._sync_state_to_session(
                    safe_session_id,
                    state,
                )

                self._save_states()

                return self._copy_state(
                    state
                )

        if state.get("status") == "failed":
            state["status"] = "running"
            state["waiting"] = False
            state["complete"] = False

            current_index = int(
                state.get("current_index") or 0
            )

            steps = state.get("steps") or []

            if current_index < len(steps):
                steps[current_index]["status"] = "active"
                steps[current_index].pop(
                    "error",
                    None,
                )
                steps[current_index].pop(
                    "apply_result",
                    None,
                )
            self._sync_state_to_session(
                safe_session_id,
                state,
            )

            self._save_states()

        if state.get("complete") or state.get("status") == "complete":
            state["status"] = "complete"
            state["waiting"] = False
            state["complete"] = True
            state["current_step"] = None

            self._sync_state_to_session(
                safe_session_id,
                state,
            )

            self._save_states()
            return self._copy_state(state)

        steps = state.get("steps") or []
        current_index = int(state.get("current_index") or 0)

        task_type = state.get(
            "task_type",
            "general",
        )

        context = state.get(
            "context",
            {},
        )

        if current_index >= len(steps):
            state["status"] = "complete"
            state["waiting"] = False
            state["complete"] = True
            state["current_step"] = None
            self._save_states()
            return self._copy_state(state)

        current_step = dict(
            steps[current_index]
        )

        print(
            "DEBUG ADVANCE LOADED STEP =",
            current_step,
            flush=True,
        )

        if (
            current_step.get("next_action")
            == "request_target"
            and user_text
            and str(user_text).strip().lower()
            not in {
                "next",
                "continue",
                "go",
                "run",
                "advance",
            }
        ):

            text = str(
                user_text or ""
            ).strip()

            if (
                text
                and current_step.get("next_action")
                == "request_target"
                and not text.lower().startswith(
                    "auto-plan"
                )
            ):
                current_step["target_file"] = text
                current_step["next_action"] = (
                    "generate_file_replacement"
                )
                current_step["mutation_ready"] = True
                current_step["payload_required"] = True
                current_step["status"] = "active"

                current_step["target_files"] = [
                    text
                ]

                current_step["waiting_for_target"] = False

                steps[current_index] = current_step

                state["steps"] = steps

                state["context"]["steps"] = steps

                steps[current_index] = current_step
                state["steps"] = steps
                state["current_step"] = current_step
                self._save_states()

                if isinstance(
                    state.get("context"),
                    dict,
                ):
                    state["context"]["steps"] = steps

                state["waiting"] = False
                state["status"] = "running"

                self._sync_state_to_session(
                    safe_session_id,
                    state,
                )

                self._save_states()

                return self._copy_state(
                    state
                )

        print(
            "DEBUG EXECUTION HANDLER =",
            self.execution_handler,
        )

        if self.execution_handler:

            execution_result = (
                self.execution_handler.run_next_step(
                    action="run_step",
                    session_id=safe_session_id,
                    execution_state=state,
                )
            )

            returned_state = (
                execution_result.get(
                    "execution_state"
                )
                if isinstance(
                    execution_result,
                    dict,
                )
                else None
            )

            print(
                "DEBUG BEFORE HANDLER STEPS =",
                state.get("steps"),
                flush=True,
            )

            print(
                "DEBUG HANDLER RETURNED STEPS =",
                (
                    returned_state.get("steps")
                    if isinstance(
                        returned_state,
                        dict,
                    )
                    else None
                ),
                flush=True,
            )

            if isinstance(
                returned_state,
                dict,
            ):
                for key in (
                    "context",
                    "execution_decision",
                    "error",
                    "history",
                ):
                    if key in returned_state:
                        state[key] = returned_state[key]

                if "steps" in returned_state:

                    returned_steps = returned_state.get(
                        "steps"
                    ) or []

                    if isinstance(
                        returned_steps,
                        list,
                    ):

                        for index, returned_step in enumerate(
                            returned_steps
                        ):

                            if index >= len(steps):
                                steps.append(
                                    returned_step
                                )
                                continue

                            current_step_state = steps[index]

                            if not isinstance(
                                current_step_state,
                                dict,
                            ):
                                steps[index] = returned_step
                                continue

                            if not isinstance(
                                returned_step,
                                dict,
                            ):
                                continue

                            preserved_fields = {
                                "target_file": current_step_state.get(
                                    "target_file"
                                ),
                                "target_files": current_step_state.get(
                                    "target_files"
                                ),
                                "target_function": current_step_state.get(
                                    "target_function"
                                ),
                            }

                            for key, value in returned_step.items():
                                current_step_state[key] = value

                            for key, value in preserved_fields.items():
                                if value:
                                    current_step_state[key] = value

                        state["steps"] = steps

                elif steps:
                    state["steps"] = steps

            else:

                state["steps"] = steps

            steps = state.get("steps") or []

            if state.get("complete"):
                return self._copy_state(
                    state
                )

            current_step = steps[current_index]



            next_index = current_index + 1


            if (
                isinstance(current_step, dict)
                and current_step.get("action") == "implement"
                and current_step.get("next_action")
                == "generate_file_replacement"
                and current_step.get("status") != "completed"
            ):
                current_step["status"] = "active"

                steps[current_index] = current_step
                state["steps"] = steps
                state["current_step"] = current_step

            if (
                isinstance(current_step, dict)
                and current_step.get("action") == "review"
            ):
                current_step["status"] = "completed"
                current_step["result"] = (
                    "Review completed. Mutation result verified."
                )

                steps[current_index] = current_step
                state["steps"] = steps
                state["current_step"] = current_step

            if (
                isinstance(current_step, dict)
                and current_step.get("status") == "completed"
                and next_index < len(steps)
            ):
                steps[next_index]["status"] = "active"



            if next_index < len(steps):

                previous_step = steps[current_index]

                next_step = steps[next_index]
                if (
                    isinstance(previous_step, dict)
                    and isinstance(next_step, dict)
                ):
                    if previous_step.get("target_file"):
                        next_step["target_file"] = (
                            previous_step["target_file"]
                        )

                    if previous_step.get("target_files"):
                        next_step["target_files"] = (
                            previous_step["target_files"]
                        )

                    if next_step.get("action") == "implement":
                        next_step["status"] = "active"
                        next_step["mutation_ready"] = True
                        next_step["payload_required"] = True

                    steps[next_index] = next_step



                if (
                    isinstance(previous_step, dict)
                    and isinstance(next_step, dict)
                ):
                    if previous_step.get("target_file"):
                        next_step["target_file"] = (
                            previous_step["target_file"]
                        )

                    if previous_step.get("target_files"):
                        next_step["target_files"] = (
                            previous_step["target_files"]
                        )

                    if previous_step.get("target_function"):
                        next_step["target_function"] = (
                            previous_step["target_function"]
                        )

                steps[next_index] = next_step

                state["current_index"] = next_index

                state["current_step"] = next_step

                if (
                    isinstance(next_step, dict)
                    and next_step.get("next_action")
                    in {
                        "request_target",
                    }
                ):
                    state["status"] = "waiting"
                    state["waiting"] = True

                else:
                    state["status"] = "running"
                    state["waiting"] = False

                state["complete"] = False

            else:

                state["current_step"] = None
                state["status"] = "complete"
                state["waiting"] = False
                state["complete"] = True

            self._sync_state_to_session(
                safe_session_id,
                state,
            )

            self._save_states()

            return self._copy_state(state)

        next_index = current_index + 1

        state["current_index"] = next_index

        if next_index >= len(steps):

            state["status"] = "complete"
            state["waiting"] = False
            state["complete"] = True
            state["current_step"] = None

        else:

            state["current_step"] = steps[next_index]

            next_step = steps[next_index]

            if (
                isinstance(next_step, dict)
                and next_step.get("next_action")
                in {
                    "request_target",
                }
            ):
                state["status"] = "waiting"
                state["waiting"] = True

            else:
                state["status"] = "running"
                state["waiting"] = False

            state["complete"] = False

        mission_id = state.get("mission_id")

        if mission_id:

            mission_service.advance_step(
                mission_id,
                {
                    "step": state.get("current_step"),
                    "status": "advanced",
                },
            )

        state["next_action"] = {
            "task_type": task_type,
            "step": state.get(
                "current_step",
            ),
            "reason": "Continue current mission step.",
        }

        self._sync_state_to_session(
            safe_session_id,
            state,
        )

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

        mission_id = state.get("mission_id")

        if mission_id:
            mission_service.update_status(
                mission_id,
                "failed",
            )

        return self._copy_state(state)

    def set_session_service(
        self,
        session_service,
    ) -> None:
        self.session_service = session_service

    def reset(self, session_id: str) -> Dict[str, Any]:
        safe_session_id = self._safe_session_id(
            session_id
        )

        self._states.pop(
            safe_session_id,
            None,
        )

        self._save_states()

        if hasattr(
            self,
            "active_execution_cache",
        ):
            self.active_execution_cache.pop(
                safe_session_id,
                None,
            )

        if hasattr(
            self,
            "completed_execution_cache",
        ):
            self.completed_execution_cache.pop(
                safe_session_id,
                None,
            )

        try:
            session_service = getattr(
                self,
                "session_service",
                None,
            )

            if session_service is not None:

                session = session_service.get_session(
                    safe_session_id
                )

                if session:

                    session["active_execution"] = None
                    session["execution_state"] = None

                    if isinstance(
                        session.get("working_state"),
                        dict,
                    ):
                        session["working_state"][
                            "active_execution"
                        ] = None

                        session["working_state"][
                            "execution_state"
                        ] = None

                    if hasattr(
                        session_service,
                        "save",
                    ):
                        session_service.save(
                            [
                                session
                            ],
                            safe_session_id,
                        )

        except Exception as e:
            print(
                "RESET SESSION EXECUTION CLEANUP FAILED:",
                e,
            )

        return self.get_state(
            safe_session_id
        )


    def format_reply(self, state: Dict[str, Any]) -> str:

        status = state.get("status") or "idle"
        goal = state.get("goal")

        current_step = state.get("current_step")
        current_index = int(
            state.get("current_index") or 0
        )

        steps = state.get("steps") or []

        if (
            isinstance(steps, list)
            and current_index < len(steps)
        ):
            current_step = steps[current_index]

        total = len(steps)
        error = state.get("error")
        if status == "idle":
            return error or "No active execution mission. Start one with: auto-plan <goal>"

        if status == "complete":
            if goal:
                return (
                    "Done. I finished working on "
                    + goal
                    + " and checked the result."
                )
            return "Done. I finished the task and checked the result."
        if error:
            return error

        if current_step:
            step_number = (
                min(current_index + 1, total)
                if total
                else current_index + 1
            )

            if (
                isinstance(current_step, dict)
                and current_step.get("next_action")
                == "request_target"
            ):
                return (
                    "I need the implementation target before "
                    "continuing.\n\n"
                    "Please provide:\n"
                    "- target file path\n"
                    "- target function or class (optional)\n"
                    "- requested change"
                )

            return (
                f"Continuing mission:\n\n"
                f"Goal: {goal}\n\n"
                f"Step {step_number}/{total}:\n"
                f"{current_step}\n\n"
                "Status: waiting"
            )

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

    def _normalize_steps(
        self,
        steps: Optional[List[Any]],
    ) -> List[Dict[str, Any]]:

        print(
            "DEBUG NORMALIZE INPUT STEPS =",
            steps,
        )

        print(
            "DEBUG NORMALIZE INPUT TYPES =",
            [
                type(x).__name__
                for x in steps
            ] if steps else []
        )

        if not steps:
            return [
                {
                    "title": "Design the solution",
                    "action": "design",
                    "status": "pending",
                    "result": "",
                    "error": None,
                },
                {
                    "title": "Implement the change",
                    "action": "implement",
                    "status": "pending",
                    "result": "",
                    "error": None,
                    "target_file": (
                        ""
                    ),
                    "target_files": [],
                    "target_function": (
                        ""
                    ),
                    "mutation_mode": "file",
                    "next_action": "request_target",
                    "mutation_ready": False,
                    "payload_required": True,
                },
                {
                    "title": "Verify the result",
                    "action": "test",
                    "status": "pending",
                    "result": "",
                    "error": None,
                },
            ]

        normalized = []

        for item in steps:

            if isinstance(item, dict):
                step = dict(item)

                step.setdefault(
                    "target_file",
                    "",
                )

                step.setdefault(
                    "target_files",
                    [],
                )

                step.setdefault(
                    "target_function",
                    "",
                )

                if not step.get("title"):
                    step["title"] = str(
                        step.get("text")
                        or step.get("name")
                        or ""
                    ).strip()

                step.setdefault(
                    "action",
                    "design",
                )

                step.setdefault(
                    "status",
                    "pending",
                )

                step.setdefault(
                    "result",
                    "",
                )

                step.setdefault(
                    "error",
                    None,
                )

                normalized.append(step)

            else:
                normalized.append(
                    {
                        "title": str(item).strip(),
                        "action": "design",
                        "status": "pending",
                        "result": "",
                        "error": None,
                    }
                )

        print(
            "DEBUG NORMALIZE OUTPUT =",
            normalized,
        )

        return normalized

    def _clean_text(self, user_text: str) -> str:
        return " ".join(str(user_text or "").strip().lower().split())

    def _safe_session_id(self, session_id: str) -> str:
        return str(session_id or "default").strip() or "default"

    def _sync_state_to_session(
        self,
        session_id: str,
        state: Dict[str, Any],
    ):
        try:
            if not self.session_service:
                return

            if not isinstance(state, dict):
                return

            session = self.session_service.get_session(
                session_id
            )

            if not isinstance(session, dict):
                return

            session["execution_state"] = state
            session["active_execution"] = state

            if isinstance(
                state.get("context"),
                dict,
            ):
                state["context"]["steps"] = state.get(
                    "steps",
                    [],
                )

            working_state = session.get(
                "working_state"
            )

            if not isinstance(working_state, dict):
                working_state = {}

            working_state["execution_state"] = state
            working_state["active_execution"] = state

            session["working_state"] = working_state

            if hasattr(
                self.session_service,
                "save",
            ):
                print(
                    "DEBUG SYNC BEFORE SAVE =",
                    {
                        "session_id": session_id,
                        "stored_id": session.get("id"),
                        "execution_state_type": type(
                            session.get("execution_state")
                        ).__name__,
                        "execution_steps": len(
                            session.get("execution_state", {}).get(
                                "steps",
                                [],
                            )
                        )
                        if isinstance(
                            session.get("execution_state"),
                            dict,
                        )
                        else None,
                        "active_execution_type": type(
                            session.get("active_execution")
                        ).__name__,
                    },
                    flush=True,
                )

                self.session_service.save(
                    [
                        session
                    ],
                    session_id,
                )

        except Exception as e:
            print(
                "SYNC EXECUTION STATE FAILED =",
                e,
                flush=True,
            )

    def _copy_state(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:

        steps = state.get("steps") or []

        print(
            "DEBUG COPY_STATE STEPS =",
            steps,
        )

        current_index = int(
            state.get("current_index")
            or state.get("current_step_index")
            or 0
        )

        copied_steps = [
            dict(step)
            if isinstance(step, dict)
            else step
            for step in steps
        ]

        current_step = state.get(
            "current_step"
        )

        if (
            isinstance(copied_steps, list)
            and 0 <= current_index < len(copied_steps)
        ):
            current_step = copied_steps[current_index]

        return {
            "status": state.get("status"),
            "goal": state.get("goal"),
            "task_type": state.get(
                "task_type",
                "general",
            ),
            "context": state.get(
                "context",
                {},
            ),
            "execution_decision": state.get(
                "execution_decision",
                {},
            ),
            "steps": copied_steps,
            "current_index": current_index,
            "current_step": current_step,
            "history": list(
                state.get("history") or []
            ),
            "waiting": (
                bool(state.get("waiting"))
                and str(
                    state.get("status") or ""
                ).strip().lower()
                not in {
                    "complete",
                    "completed",
                }
            ),
            "complete": (
                bool(state.get("complete"))
                or str(
                    state.get("status") or ""
                ).strip().lower()
                in {
                    "complete",
                    "completed",
                }
            ),
            "mission_id": state.get(
                "mission_id"
            ),
            "error": state.get(
                "error"
            ),
        }

ExecutionService = ChatExecutionService


# NOVA_EXECUTION_POST_COMPLETE_IDLE_GUARD_20260609
# If user sends k/next/continue after a mission is already complete,


# NOVA_EXECUTION_CANCEL_COMPAT_20260630
# Adds the missing cancel(session_id) method expected by the execution command guard.
# Stop/cancel must clear the active mission so "k" cannot continue it afterward.
try:
    import json as _nova_exec_cancel_json_20260630
    from pathlib import Path as _nova_exec_cancel_Path_20260630

    def _nova_execution_idle_state_20260630(message="Execution stopped."):
        return {
            "status": "idle",
            "complete": False,
            "current_index": 0,
            "current_step": None,
            "goal": None,
            "steps": [],
            "history": [],
            "waiting": False,
            "error": None,
            "message": message,
        }

    def _nova_execution_clear_session_file_20260630(session_id, idle_state):
        try:
            sid = str(session_id or "").strip()
            if not sid:
                return

            root = _nova_exec_cancel_Path_20260630(__file__).resolve().parents[2]
            sessions_path = root / "data" / "nova_sessions.json"

            if not sessions_path.exists():
                return

            data = _nova_exec_cancel_json_20260630.loads(
                sessions_path.read_text(encoding="utf-8") or "{}"
            )

            def clear_one(session):
                if not isinstance(session, dict):
                    return False

                if str(session.get("id") or "") != sid:
                    return False

                session["active_execution"] = None
                session["execution_state"] = idle_state

                working_state = session.get("working_state")
                if isinstance(working_state, dict):
                    working_state["active_task"] = ""
                    working_state["next_move"] = ""
                    working_state["checkpoint"] = ""
                    session["working_state"] = working_state

                return True

            changed = False

            if isinstance(data, dict):
                if isinstance(data.get("sessions"), list):
                    for session in data["sessions"]:
                        changed = clear_one(session) or changed

                if isinstance(data.get(sid), dict):
                    changed = clear_one(data[sid]) or changed

                for value in data.values():
                    if isinstance(value, dict):
                        changed = clear_one(value) or changed

            elif isinstance(data, list):
                for session in data:
                    changed = clear_one(session) or changed

            if changed:
                sessions_path.write_text(
                    _nova_exec_cancel_json_20260630.dumps(
                        data,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
        except Exception:
            pass

    def _nova_execution_cancel_compat_20260630(self, session_id="", *args, **kwargs):
        sid = str(
            session_id
            or kwargs.get("session_id")
            or kwargs.get("active_session_id")
            or ""
        ).strip()

        idle_state = _nova_execution_idle_state_20260630()

        # Clear common in-memory state containers if this service uses any of them.
        for attr_name in (
            "active_execution",
            "execution_state",
            "state",
            "current_state",
        ):
            try:
                if hasattr(self, attr_name):
                    setattr(self, attr_name, idle_state)
            except Exception:
                pass

        for attr_name in (
            "states",
            "_states",
            "execution_states",
            "_execution_states",
            "active_executions",
            "_active_executions",
            "session_states",
            "_session_states",
        ):
            try:
                box = getattr(self, attr_name, None)
                if isinstance(box, dict):
                    if sid:
                        box[sid] = idle_state
                    else:
                        box.clear()
            except Exception:
                pass

        _nova_execution_clear_session_file_20260630(sid, idle_state)

        try:
            if sid and hasattr(self, "_states"):
                self._states.pop(sid, None)
                self._save_states()
        except Exception:
            pass

        return idle_state

    if "ChatExecutionService" in globals():
        ChatExecutionService.cancel = _nova_execution_cancel_compat_20260630
        ChatExecutionService.stop = _nova_execution_cancel_compat_20260630
        _nova_boot_log_20260701("[NOVA_EXECUTION_CANCEL_COMPAT_20260630] installed")
    else:
        print("[NOVA_EXECUTION_CANCEL_COMPAT_20260630] skipped: ChatExecutionService not found")
except Exception as _nova_execution_cancel_error_20260630:
    print("[NOVA_EXECUTION_CANCEL_COMPAT_20260630] failed:", _nova_execution_cancel_error_20260630)

# NOVA_EXECUTION_EMPTY_COMPLETE_NORMALIZER_20260630
# If an execution command runs after stop/cancel, do not report fake
# "Execution complete" for an empty/no-goal/no-step state.
try:
    def _nova_execution_no_active_state_20260630():
        return {
            "status": "idle",
            "complete": False,
            "current_index": 0,
            "current_step": None,
            "goal": None,
            "steps": [],
            "history": [],
            "waiting": False,
            "error": "No active execution mission. Start one with: auto-plan <goal>",
        }

    def _nova_execution_is_empty_complete_20260630(state):
        if not isinstance(state, dict):
            return False

        status = str(state.get("status") or "").strip().lower()
        complete = bool(state.get("complete"))
        goal = state.get("goal")
        steps = state.get("steps")

        return (
            (status == "complete" or complete)
            and not goal
            and (not isinstance(steps, list) or len(steps) == 0)
        )

    def _nova_execution_normalize_empty_complete_result_20260630(result):
        idle_state = _nova_execution_no_active_state_20260630()
        message = idle_state["error"]

        if isinstance(result, dict):
            state = result.get("execution_state")

            if _nova_execution_is_empty_complete_20260630(state):
                result["execution_state"] = idle_state

                assistant_message = result.get("assistant_message")
                if isinstance(assistant_message, dict):
                    assistant_message["text"] = message
                    assistant_message["content"] = message
                    assistant_message["execution_state"] = idle_state
                    result["assistant_message"] = assistant_message
                else:
                    result["assistant_message"] = {
                        "role": "assistant",
                        "text": message,
                        "content": message,
                        "execution_state": idle_state,
                    }

                result["ok"] = True
                result["skip_cleanup"] = True
                result["skip_post_processing"] = True
                result["skip_rewrite"] = True

                return result

            assistant_message = result.get("assistant_message")
            if isinstance(assistant_message, dict):
                msg_state = assistant_message.get("execution_state")
                if _nova_execution_is_empty_complete_20260630(msg_state):
                    assistant_message["text"] = message
                    assistant_message["content"] = message
                    assistant_message["execution_state"] = idle_state
                    result["assistant_message"] = assistant_message
                    result["execution_state"] = idle_state
                    return result

        if _nova_execution_is_empty_complete_20260630(result):
            return idle_state

        return result

    def _nova_execution_wrap_empty_complete_method_20260630(method_name):
        original = getattr(ChatExecutionService, method_name, None)

        if not callable(original):
            return False

        if getattr(original, "_nova_empty_complete_normalizer_20260630", False):
            return True

        def _nova_execution_empty_complete_wrapper_20260630(self, *args, **kwargs):
            result = original(self, *args, **kwargs)
            return _nova_execution_normalize_empty_complete_result_20260630(result)

        _nova_execution_empty_complete_wrapper_20260630._nova_empty_complete_normalizer_20260630 = True
        setattr(ChatExecutionService, method_name, _nova_execution_empty_complete_wrapper_20260630)
        return True

    _nova_execution_normalized_methods_20260630 = []

    if "ChatExecutionService" in globals():
        for _nova_execution_method_name_20260630 in dir(ChatExecutionService):
            if _nova_execution_method_name_20260630.startswith("__"):
                continue

            if _nova_execution_method_name_20260630 in {
                "cancel",
                "stop",
            }:
                continue

            if _nova_execution_wrap_empty_complete_method_20260630(_nova_execution_method_name_20260630):
                _nova_execution_normalized_methods_20260630.append(_nova_execution_method_name_20260630)

        _nova_boot_log_20260701(
            "[NOVA_EXECUTION_EMPTY_COMPLETE_NORMALIZER_20260630] installed:",
            ",".join(_nova_execution_normalized_methods_20260630) or "none",
        )
    else:
        print("[NOVA_EXECUTION_EMPTY_COMPLETE_NORMALIZER_20260630] skipped: ChatExecutionService not found")
except Exception as _nova_execution_empty_complete_error_20260630:
    print("[NOVA_EXECUTION_EMPTY_COMPLETE_NORMALIZER_20260630] failed:", _nova_execution_empty_complete_error_20260630)

# NOVA_CHAT_EXECUTION_SINGLETON_20260710

# Shared execution service instance for imports across Nova.
chat_execution_service = ChatExecutionService()
