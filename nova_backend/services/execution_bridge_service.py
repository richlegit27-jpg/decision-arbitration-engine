from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, Optional

from nova_backend.services.project_brain_context_builder import (
    build_project_brain_context,
)


class ExecutionBridgeService:
    def __init__(
        self,
        chat_execution_service=None,
        chat_service=None,
        project_planning_ai_service=None,
        logger=None,
    ):
        self.chat_execution_service = chat_execution_service
        self.chat_service = chat_service
        self.project_planning_ai_service = (
            project_planning_ai_service
        )
        self.logger = logger or logging.getLogger(
            __name__
        )

    def _get_user_text(
        self,
        payload,
    ) -> str:
        if not isinstance(payload, dict):
            return ""

        return str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()

    def _extract_deterministic_file_request(
        self,
        goal: str,
    ) -> Optional[Dict[str, str]]:
        """
        Detect direct file-write requests before the AI planner
        can replace the exact requested operation with a generic
        implementation step.
        """

        clean = str(goal or "").strip()

        if not clean:
            return None

        file_match = re.search(
            r"(?is)"
            r"\b(?:create|write|overwrite|replace|save|update|modify)"
            r"\b"
            r".*?"
            r"([A-Za-z]:\\[^:\r\n]+?\.[A-Za-z0-9]+)"
            r"(?:\s+with\s+exactly\s+this\s+content\s*:?\s*)"
            r"(.*)$",
            clean,
        )

        if not file_match:
            return None

        target_file = (
            file_match.group(1)
            .strip()
            .rstrip(".,;:")
        )

        content = file_match.group(2)

        if content is None:
            return None

        content = content.strip()

        if not target_file or not content:
            return None

        return {
            "target_file": target_file,
            "content": content,
        }

    def _build_direct_file_step(
        self,
        goal: str,
        target_file: str,
        content: str,
    ) -> Dict[str, Any]:
        return {
            "title": (
                "Create or overwrite requested file"
            ),
            "description": goal,
            "text": goal,
            "action": "create_file",
            "execution_mode": "direct",
            "target_file": target_file,
            "target_function": "",
            "content": content,
            "file_content": content,
            "mutation_mode": "file",
            "next_action": "write_file",
            "mutation_ready": True,
            "payload_required": False,
            "requires_approval": True,
            "approval_required": True,
            "approval_status": "pending",
            "status": "ready",
        }

    def try_execution_trigger(
        self,
        session_id,
        user_text,
    ):
        return None

    def try_execution_status(
        self,
        session_id=None,
        user_text=None,
        **kwargs,
    ):
        """
        Detect active execution continuation states.

        Handles approval/resume commands before normal chat routing.
        """

        text = str(user_text or "").strip().lower()

        if not session_id:
            return {
                "handled": False,
                "active": False,
                "execution_active": False,
                "session_id": "",
            }

        execution_state = None

        try:
            if hasattr(self, "chat_service"):
                execution_state = (
                    self.chat_service._load_execution_state(
                        session_id
                    )
                )
        except Exception as exc:
            print(
                "[EXECUTION STATUS LOAD ERROR]",
                exc,
                flush=True,
            )

        if not isinstance(execution_state, dict):
            return {
                "handled": False,
                "active": False,
                "execution_active": False,
                "session_id": session_id,
            }

        print(
            "[BRIDGE LOADED EXECUTION STATE]",
            {
                "session_id": session_id,
                "keys": list(execution_state.keys()),
                "status": execution_state.get("status"),
                "approval_status": execution_state.get("approval_status"),
                "waiting": execution_state.get("waiting"),
                "approval_required": execution_state.get("approval_required"),
                "steps_count": len(execution_state.get("steps", []))
                if isinstance(execution_state.get("steps"), list)
                else None,
            },
            flush=True,
        )

        status = str(
            execution_state.get("status") or ""
        ).strip().lower()

        approval_status = str(
            execution_state.get("approval_status") or ""
        ).strip().lower()

        waiting = bool(
            execution_state.get("waiting")
            or execution_state.get("approval_required")
        )

        approval_words = {
            "yes",
            "y",
            "ok",
            "okay",
            "approve",
            "approved",
            "go ahead",
            "do it",
        }

        if (
            status == "waiting_approval"
            and approval_status == "pending"
            and waiting
            and text in approval_words
        ):
            print(
                "[EXECUTION APPROVAL CONTINUATION DETECTED]",
                {
                    "session_id": session_id,
                    "status": status,
                    "approval_status": approval_status,
                },
                flush=True,
            )

            return {
                "handled": True,
                "active": True,
                "execution_active": True,
                "route": "execution",
                "intent": "approve_execution",
                "command": "approve",
                "session_id": session_id,
                "execution_state": execution_state,
            }

        return {
            "handled": False,
            "active": status in {
                "running",
                "waiting",
                "waiting_approval",
            },
            "execution_active": status in {
                "running",
                "waiting",
                "waiting_approval",
            },
            "session_id": session_id,
        }
    def try_execution_target_capture(
        self,
        session_id=None,
        user_text=None,
        **kwargs,
    ):
        """
        Compatibility method used by chat_service.

        Returning None allows the normal chat execution pipeline to continue.
        Actual execution triggering remains handled by the execution bridge's
        existing execution methods.
        """
        return None

    def try_execution_autoplan_start(
        self,
        session_id,
        user_text,
    ):
        print(
            "DEBUG NEW AUTOPLAN BRIDGE LOADED",
            flush=True,
        )

        try:
            clean = str(
                user_text or ""
            ).strip()

            lower = clean.lower()

            continuation_commands = {
                "k",
                "kk",
                "next",
                "nex",
                "continue",
                "resume",
            }

            if lower in continuation_commands:
                print(
                    "[AUTOPLAN CONTINUATION BYPASS]",
                    clean,
                    flush=True,
                )
                return None

            prefixes = [
                "auto-plan ",
                "autoplan ",
                "auto plan ",
            ]

            matched_prefix = None

            for prefix in prefixes:
                if lower.startswith(prefix):
                    matched_prefix = prefix
                    break

            is_natural_execution_request = (
                self.chat_execution_service.is_execution_trigger(
                    clean
                )
            )

            if matched_prefix:
                goal = clean[
                    len(matched_prefix):
                ].strip()

            elif is_natural_execution_request:
                goal = clean

                execution_phrases = (
                    "and run all steps",
                    "run all steps",
                    "and execute all steps",
                    "execute all steps",
                    "and run all",
                    "run all",
                    "and execute all",
                    "execute all",
                    "start execution",
                )

                goal_lower_clean = goal.lower()

                for phrase in execution_phrases:
                    if phrase in goal_lower_clean:
                        position = (
                            goal_lower_clean.find(
                                phrase
                            )
                        )

                        goal = goal[
                            :position
                        ].strip(
                            " .,:;-"
                        )

                        break

            else:
                print(
                    "[AUTOPLAN BYPASS]",
                    clean,
                    flush=True,
                )
                return None

            if not goal:
                goal = "Untitled mission"

            goal_lower = goal.lower()

            steps = []

            project_context = (
                build_project_brain_context()
            )

            brain_context = {
                "project_name": (
                    project_context.project_name
                ),
                "active_checkpoint": (
                    project_context.active_checkpoint
                ),
                "blocker": (
                    project_context.blocker
                ),
                "next_move": (
                    project_context.next_move
                ),
            }

            # -------------------------------------------------
            # Deterministic file handling MUST happen before
            # the AI planner.
            # -------------------------------------------------

            deterministic_file = (
                self._extract_deterministic_file_request(
                    goal
                )
            )

            if deterministic_file:
                target_file = (
                    deterministic_file[
                        "target_file"
                    ]
                )

                content = (
                    deterministic_file[
                        "content"
                    ]
                )

                steps = [
                    self._build_direct_file_step(
                        goal=goal,
                        target_file=target_file,
                        content=content,
                    )
                ]

                print(
                    "[DETERMINISTIC FILE REQUEST]",
                    {
                        "goal": goal,
                        "target_file": target_file,
                        "content_length": len(
                            content
                        ),
                        "action": "create_file",
                    },
                    flush=True,
                )

            deterministic_file_match = re.search(
                r"(?is)"
                r"\b(?:create|write|overwrite|replace|save|update|modify)"
                r"\b.*?"
                r"([A-Za-z]:\\[^:\r\n]+?\.[A-Za-z0-9]+)"
                r"(?:\s+with\s+exactly\s+this\s+content\s*:?\s*)"
                r"(.*)$",
                goal,
            )

            if deterministic_file_match:
                target_file = (
                    deterministic_file_match.group(1)
                    .strip()
                    .rstrip(".,;:")
                )

                exact_content = (
                    deterministic_file_match.group(2)
                    .strip()
                )

                steps = [
                    {
                        "title": (
                            "Create or overwrite requested file"
                        ),
                        "description": goal,
                        "text": goal,
                        "action": "create_file",
                        "execution_mode": "direct",
                        "target_file": target_file,
                        "target_function": "",
                        "content": exact_content,
                        "file_content": exact_content,
                        "mutation_mode": "file",
                        "next_action": "write_file",
                        "mutation_ready": True,
                        "payload_required": False,
                        "requires_approval": True,
                        "approval_required": True,
                        "approval_status": "pending",
                        "status": "ready",
                    }
                ]

                print(
                    "[DETERMINISTIC FILE REQUEST]",

                    {
                        "target_file": target_file,
                        "content_length": len(
                            exact_content
                        ),
                    },
                    flush=True,
                )


            else:
                try:
                    plan = (
                        self.project_planning_ai_service.build_plan(
                            request=goal,
                            project_context={
                                "project_name": (
                                    project_context.project_name
                                ),
                                "active_checkpoint": (
                                    project_context.active_checkpoint
                                ),
                                "blocker": (
                                    project_context.blocker
                                ),
                                "next_move": (
                                    project_context.next_move
                                ),
                            },
                        )
                    )

                    steps = plan.get(
                        "tasks",
                        [],
                    )

                    if not isinstance(
                        steps,
                        list,
                    ):
                        steps = []

                    steps = [
                        step
                        for step in steps
                        if isinstance(
                            step,
                            dict,
                        )
                        and str(
                            step.get("title")
                            or ""
                        ).strip()
                    ]

                    print(
                        "[AI AUTOPLAN RESULT]",
                        {
                            "goal": goal,
                            "plan_name": plan.get(
                                "name"
                            ),
                            "task_count": len(
                                steps
                            ),
                        },
                        flush=True,
                    )

                except Exception as exc:
                    self.logger.exception(
                        "[AI AUTOPLAN FAILED]"
                    )

                    print(
                        "[AI AUTOPLAN FALLBACK]",
                        repr(exc),
                        flush=True,
                    )

                    steps = []

            if not steps:
                file_operation_match = re.search(
                    r"(?is)"
                    r"\b(create|write|overwrite|replace|save|update|modify)"
                    r"\b.*?"
                    r"([A-Za-z]:\\[^:\r\n]+?\.[A-Za-z0-9]+)"
                    r"\b",
                    goal,
                )

                if file_operation_match:
                    target_file = (
                        file_operation_match.group(
                            2
                        )
                        .strip()
                        .rstrip(".,;:")
                    )

                    steps = [
                        {
                            "title": goal,
                            "description": goal,
                            "text": goal,
                            "action": "create_file",
                            "execution_mode": "direct",
                            "target_file": target_file,
                            "target_function": "",
                            "mutation_mode": "file",
                            "next_action": (
                                "generate_file_replacement"
                            ),
                            "mutation_ready": True,
                            "payload_required": True,
                            "requires_approval": True,
                            "approval_required": True,
                            "approval_status": "pending",
                            "status": "ready",
                        }
                    ]

                    print(
                        "[NATURAL FILE FALLBACK]",
                        {
                            "goal": goal,
                            "target_file": target_file,
                        },
                        flush=True,
                    )

                else:
                    steps = [
                        {
                            "title": (
                                f"Analyze the goal: {goal}"
                            ),
                            "action": "analyze",
                            "execution_mode": "ai",
                        },
                        {
                            "title": (
                                "Determine the required work "
                                "and implementation approach"
                            ),
                            "action": "plan",
                            "execution_mode": "ai",
                        },
                        {
                            "title": (
                                "Review the result and "
                                "determine next actions"
                            ),
                            "action": "review",
                            "execution_mode": "ai",
                        },
                    ]

            print(
                "DEBUG AUTOPLAN STEPS BEFORE START:",
                steps,
                flush=True,
            )

            for step in steps:
                if not isinstance(
                    step,
                    dict,
                ):
                    continue

                if step.get("action") not in {
                    "implement",
                    "create_file",
                }:
                    continue

                target_file = str(
                    step.get("target_file")
                    or ""
                ).strip()

                target_files = (
                    step.get("target_files")
                    or []
                )

                has_real_target = bool(
                    target_file
                    or target_files
                )

                if has_real_target:
                    step.setdefault(
                        "target_function",
                        "",
                    )

                    step["mutation_mode"] = (
                        "file"
                    )

                    step["next_action"] = (
                        "write_file"
                        if step.get(
                            "action"
                        )
                        == "create_file"
                        else "generate_file_replacement"
                    )

                    step["mutation_ready"] = (
                        True
                    )

                    step["payload_required"] = (
                        False
                        if step.get(
                            "action"
                        )
                        == "create_file"
                        else True
                    )

                else:
                    step["mutation_mode"] = (
                        "general"
                    )

                    step["next_action"] = (
                        "execute_task"
                    )

                    step["mutation_ready"] = (
                        True
                    )

                    step["payload_required"] = (
                        False
                    )

                    step["status"] = (
                        "ready"
                    )

            session_id = str(
                session_id or ""
            ).strip()

            if not session_id:
                session_id = (
                    "execution_"
                    + uuid.uuid4().hex
                )

            print(
                "AUTOPLAN BEFORE START",
                {
                    "has_chat_execution_service": (
                        hasattr(
                            self,
                            "chat_execution_service",
                        )
                    ),
                    "has_chat_service": (
                        hasattr(
                            self,
                            "chat_service",
                        )
                    ),
                    "session_id": session_id,
                    "goal": goal,
                    "steps": len(steps),
                },
                flush=True,
            )

            print(
                "DEBUG STEPS RIGHT BEFORE START =",
                steps,
                flush=True,
            )

            state = (
                self.chat_execution_service.start(
                    session_id=session_id,
                    goal=goal,
                    steps=steps,
                    context={
                        "source": "auto_plan",
                        "task_goal": goal,
                        "step_count": len(
                            steps
                        ),
                        "steps": steps,
                        "project": "Nova",
                        "execution_reason": (
                            "Complete the user's requested task "
                            "through a guided execution workflow."
                        ),
                        "project_brain": (
                            brain_context
                        ),
                    },
                )
            )

            print(
                "DEBUG STATE AFTER EXECUTION START =",
                state,
                flush=True,
            )

            if state:
                if (
                    self.chat_service
                    and hasattr(
                        self.chat_service,
                        "_save_execution_state",
                    )
                ):
                    self.chat_service._save_execution_state(
                        session_id,
                        state,
                    )

            step_lines = []

            for index, step in enumerate(
                steps
            ):
                if isinstance(
                    step,
                    dict,
                ):
                    step_lines.append(
                        f"{index + 1}. "
                        f"{step.get('title', 'Execution step')}"
                    )
                else:
                    step_lines.append(
                        f"{index + 1}. {step}"
                    )

            target = {
                "target_file": "",
                "target_files": [],
                "target_function": "",
            }

            for step in steps:
                if not isinstance(
                    step,
                    dict,
                ):
                    continue

                if step.get(
                    "target_file"
                ):
                    target[
                        "target_file"
                    ] = step.get(
                        "target_file"
                    )

                if step.get(
                    "target_files"
                ):
                    target[
                        "target_files"
                    ] = step.get(
                        "target_files"
                    )

                if step.get(
                    "target_function"
                ):
                    target[
                        "target_function"
                    ] = step.get(
                        "target_function"
                    )

            print(
                "[EXECUTION TARGET HANDOFF]",
                {
                    "session_id": session_id,
                    "target": target,
                    "status": state.get(
                        "status"
                    ),
                    "current_index": state.get(
                        "current_index"
                    ),
                },
                flush=True,
            )

            print(
                "[EXECUTION TARGET CONTINUE]",
                {
                    "session_id": session_id,
                    "current_index": state.get(
                        "current_index"
                    ),
                    "status": state.get(
                        "status"
                    ),
                    "handler": type(
                        self.chat_execution_service.execution_handler
                    ).__name__
                    if getattr(
                        self.chat_execution_service,
                        "execution_handler",
                        None,
                    )
                    is not None
                    else None,
                },
                flush=True,
            )

            execution_result = (
                self.chat_execution_service.advance(
                    session_id=session_id,
                )
            )

            print(
                "[EXECUTION TARGET CONTINUE RESULT]",
                repr(execution_result),
                flush=True,
            )

            if execution_result is None:
                raise RuntimeError(
                    "Chat execution service returned None "
                    "after target capture."
                )

            if isinstance(
                execution_result,
                dict,
            ):
                return execution_result

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": str(
                        execution_result
                    ),
                    "content": str(
                        execution_result
                    ),
                },
                "session_id": session_id,
                "execution": execution_result,
            }

        except Exception as exc:
            self.logger.exception(
                "[NovaExecutionAutoPlanStart] failed"
            )

            reply_text = (
                "Execution auto-plan start failed: "
                + str(exc)
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                },
                "session_id": session_id,
                "execution_state": {},
                "error": str(exc),
            }



