import traceback
import time

from nova_backend.services.auth_context import get_current_user_id

def chat_handle(
    service,
    user_text: str,
    session_id: str = "",
    attachments=None,
    brain_state=None,
    decision=None,
    working_state=None,
    regenerate=False,
):
    decision_intent = (
        decision.get("intent")
        if isinstance(decision, dict)
        else None
    )

    _t0 = time.perf_counter()

    print(
        "[CHAT_HANDLE FUNCTION ENTER]",
        flush=True,
    )

    print(
        "[CHAT HANDLE HIT]",
        {
            "user_text": user_text,
            "session_id": session_id,
        },
        flush=True,
    )

    attachments = attachments or []

    try:
        user_text = service.safe_str(
            user_text
        ).strip()

        if not session_id:
            session_id = service._create_session()

        if not isinstance(decision, dict) or not decision:
            decision = {
                "route": "general_chat",
                "intent": "chat",
                "mode": "chat",
            }

            try:
                print(
                    "[CHAT_HANDLE ROUTER FALLBACK]",
                    flush=True,
                )

                if hasattr(
                    service,
                    "_decide_route",
                ):
                    routed = service._decide_route(
                        user_text=user_text,
                        attachments=attachments,
                        session_id=session_id,
                    )
                else:
                    routed = service.chat_router.decide(
                        user_text=user_text,
                        attachments=attachments,
                        session_id=session_id,
                    )

                if isinstance(routed, dict):
                    decision.update(routed)

            except Exception as exc:
                print(
                    "[CHAT ROUTER FALLBACK FAILED]",
                    repr(exc),
                    flush=True,
                )

        print(
            "DEBUG PRIMARY ROUTE DECISION =",
            decision,
            flush=True,
        )

        route = str(
            decision.get("route") or ""
        ).lower()

        intent = str(
            decision.get("intent") or ""
        ).lower()

        mode = str(
            decision.get("mode") or ""
        ).lower()

        print(
            "DEBUG FINAL DECISION VALUES =",
            {
                "route": route,
                "intent": intent,
                "mode": mode,
            },
            flush=True,
        )

        print(
            "[CHAT_HANDLE CODE LOCATION]",
            {
                "filename": chat_handle.__code__.co_filename,
                "line": chat_handle.__code__.co_firstlineno,
            },
            flush=True,
        )

        # ==========================================
        # EXECUTION ROUTE
        # ==========================================

        if route == "execution":

            print(
                "[CHAT_HANDLE EXECUTION ROUTE]",
                {
                    "session_id": session_id,
                    "intent": intent,
                    "mode": mode,
                    "user_text": user_text,
                },
                flush=True,
            )

            orchestrator = getattr(
                service,
                "execution_orchestrator_service",
                None,
            )

            print(
                "[CHAT_HANDLE ORCHESTRATOR]",
                repr(orchestrator),
                flush=True,
            )

            if orchestrator is None:
                raise RuntimeError(
                    "ExecutionOrchestratorService "
                    "is not configured."
                )

            execution_state = {}

            decision_intent = (
                decision.get("intent")
                if isinstance(decision, dict)
                else None
            )

            try:
                loaded_state = {}

                # Brand-new task execution requests must not inherit
                # persisted execution state from an older conversation.
                if decision_intent != "task_execution":
                    execution_state_service = getattr(
                        service,
                        "execution_state_service",
                        None,
                    )

                    if (
                        execution_state_service is not None
                        and hasattr(
                            execution_state_service,
                            "get_execution_state",
                        )
                    ):
                        loaded_state = (
                            execution_state_service.get_execution_state(
                                session_id
                            )
                            or {}
                        )

                    elif hasattr(
                        service,
                        "_get_execution_state",
                    ):
                        loaded_state = (
                            service._get_execution_state(
                                session_id
                            )
                            or {}
                        )

                    if isinstance(
                        loaded_state,
                        dict,
                    ):
                        execution_state = loaded_state

            except Exception as exc:
                print(
                    "[EXECUTION STATE LOAD FAILED]",
                    repr(exc),
                    flush=True,
                )

            print(
                "[CHAT_HANDLE EXECUTION STATE]",
                execution_state,
                flush=True,
            )

            # ======================================
            # EXECUTION BOOTSTRAP
            #
            # A new execution request has no steps
            # yet. The orchestrator only executes
            # existing steps, so create the plan
            # before sending it to the orchestrator.
            #
            # IMPORTANT:
            # A completed execution is authoritative.
            # Do not resurrect a stale pending project
            # step from the workspace after execution
            # has already completed.
            # ======================================

            has_steps = bool(
                isinstance(
                    execution_state,
                    dict,
                )
                and execution_state.get("steps")
            )

            decision_intent = (
                decision.get("intent")
                if isinstance(decision, dict)
                else None
            )

            execution_status = str(
                execution_state.get("status") or ""
            ).strip().lower()

            execution_complete = (
                execution_state.get("complete") is True
                or execution_status in {
                    "complete",
                    "completed",
                }
            )

            # A new task_execution request starts a fresh execution.
            # Reuse persisted state only for continuation/control flows.
            decision_intent = (
                decision.get("intent")
                if isinstance(decision, dict)
                else None
            )

            if (
                decision_intent == "task_execution"
                and not execution_state
            ):
                print(
                    "[CHAT HANDLE NEW EXECUTION RESETTING STALE STATE]",
                    {
                        "old_status": execution_state.get("status"),
                        "old_complete": execution_state.get("complete"),
                        "old_step_count": len(
                            execution_state.get("steps") or []
                        ),
                    },
                    flush=True,
                )

                execution_state = {}
                has_steps = False
                execution_status = ""
                execution_complete = False

            print(
                "[CHAT_HANDLE EXECUTION COMPLETION GUARD]",
                {
                    "execution_complete": execution_complete,
                    "status": execution_state.get("status"),
                    "complete": execution_state.get("complete"),
                    "current_index": execution_state.get(
                        "current_index"
                    ),
                    "current_step_index": execution_state.get(
                        "current_step_index"
                    ),
                    "has_steps": has_steps,
                    "decision_intent": decision_intent,
                },
                flush=True,
            )

            if (
                decision_intent == "execution_control"
                and isinstance(decision, dict)
                and decision.get("command") in {
                    "approve",
                    "deny",
                }
                and (
                    execution_status == "waiting_approval"
                    or (
                        isinstance(execution_state, dict)
                        and isinstance(
                            execution_state.get("steps"),
                            list,
                        )
                        and any(
                            isinstance(step, dict)
                            and (
                                step.get("requires_approval") is True
                                or step.get("approval_required") is True
                                or str(
                                    step.get("approval_status") or ""
                                ).strip().lower()
                                in {
                                    "pending",
                                    "waiting",
                                    "waiting_approval",
                                    "awaiting_approval",
                                    "approval_required",
                                }
                            )
                            for step in execution_state.get(
                                "steps",
                                [],
                            )
                        )
                    )
                )
            ):
                print(
                    "[CHAT_HANDLE APPROVAL CONTROL DIRECT]",
                    {
                        "command": decision.get("command"),
                        "status": execution_state.get(
                            "status"
                        ),
                        "current_index": execution_state.get(
                            "current_index"
                        ),
                    },
                    flush=True,
                )

                try:
                    approval_result = orchestrator.process_execution(
                        session_id=session_id,
                        state=execution_state,
                        command=decision.get("command"),
                    )

                    if isinstance(
                        approval_result,
                        dict,
                    ):
                        execution_state = (
                            approval_result.get(
                                "execution_state"
                            )
                            or approval_result.get(
                                "state"
                            )
                            or execution_state
                        )

                        assistant_message = (
                            approval_result.get(
                                "assistant_message"
                            )
                            or {}
                        )

                        if isinstance(
                            assistant_message,
                            dict,
                        ):
                            return assistant_message

                except Exception as exc:
                    print(
                        "[CHAT_HANDLE APPROVAL CONTROL FAILED]",
                        repr(exc),
                        flush=True,
                    )
                    raise

            # ======================================
            # APPROVAL CONTROL DIRECT ROUTE
            # ======================================
            # Approval confirmations must go directly
            # to the orchestrator. They must NOT enter
            # project-step discovery, because the project
            # workspace may legitimately have no
            # "pending project execution step" even
            # though the execution state is waiting for
            # approval.
            #
            # This preserves:
            #   yes -> execution_control -> approve
            #   waiting_approval -> orchestrator
            # ======================================

            if (
                decision_intent == "execution_control"
                and isinstance(decision, dict)
                and decision.get("command") in {
                    "approve",
                    "deny",
                }
                and execution_status == "waiting_approval"
            ):
                approval_command = decision.get(
                    "command"
                )

                print(
                    "[CHAT_HANDLE APPROVAL CONTROL DIRECT]",
                    {
                        "command": approval_command,
                        "status": execution_state.get(
                            "status"
                        ),
                        "current_index": execution_state.get(
                            "current_index"
                        ),
                        "current_step_index": execution_state.get(
                            "current_step_index"
                        ),
                    },
                    flush=True,
                )

                approval_result = orchestrator.process_execution(
                    session_id=session_id,
                    state=execution_state,
                    command=approval_command,
                )

                if isinstance(
                    approval_result,
                    dict,
                ):
                    execution_state = (
                        approval_result.get(
                            "execution_state"
                        )
                        or approval_result.get(
                            "state"
                        )
                        or execution_state
                    )

                    assistant_message = (
                        approval_result.get(
                            "assistant_message"
                        )
                        or {}
                    )

                    if isinstance(
                        assistant_message,
                        dict,
                    ):
                        return assistant_message

            active_project = None
            project_step = None

            if (
                not execution_complete
                and decision_intent in {
                    "execution_continuation",
                    "task_execution",
                }
            ):
                decision_intent = (
                    decision.get("intent")
                    if isinstance(decision, dict)
                    else None
                )

                if (
                    decision_intent == "task_execution"
                    and not execution_state
                ):
                    project_builder = getattr(
                        service,
                        "project_builder_service",
                        None,
                    )

                    if project_builder is not None:
                        project_result = (
                            project_builder.build_project_from_request(
                                user_text=user_text,
                                owner_id=get_current_user_id(),
                            )
                        )

                        print(
                            "[CHAT_HANDLE FRESH PROJECT BOOTSTRAP]",
                            {
                                "project_id": (
                                    project_result.get("project_id")
                                    if isinstance(
                                        project_result,
                                        dict,
                                    )
                                    else None
                                ),
                                "task_count": len(
                                    (
                                        project_result.get("tasks")
                                        if isinstance(
                                            project_result,
                                            dict,
                                        )
                                        else []
                                    )
                                    or []
                                ),
                            },
                            flush=True,
                        )

                project_workspace = getattr(
                    service,
                    "project_workspace_service",
                    None,
                )

                active_project = (
                    project_workspace.get_active_project()
                    if project_workspace is not None
                    and hasattr(
                        project_workspace,
                        "get_active_project",
                    )
                    else None
                )

                print(

                "[CHAT_HANDLE ACTIVE PROJECT RAW DEBUG]",
                {
                    "project_id": active_project.get("id"),
                    "project_keys": list(
                        active_project.keys()
                    ),
                    "project_content": active_project.get(
                        "content"
                    ),
                    "task_count": len(
                        active_project.get("tasks")
                        or []
                    ),
                    "tasks": [
                        {
                            "id": task.get("id"),
                            "title": task.get("title"),
                            "keys": list(task.keys()),
                            "content": task.get("content"),
                            "steps": task.get("steps"),
                        }
                        for task in (
                            active_project.get("tasks")
                            or []
                        )
                        if isinstance(task, dict)
                    ],
                },
                flush=True,
            )

            for task in (
                active_project.get("tasks")
                if isinstance(active_project, dict)
                else []
            ):

                if not isinstance(task, dict):
                    continue

                task_status = str(
                    task.get("status") or ""
                ).strip().lower()

                if task_status in {
                    "completed",
                    "complete",
                    "failed",
                    "blocked",
                }:
                    continue

                for candidate_step in (
                    task.get("steps") or []
                ):

                    if not isinstance(
                        candidate_step,
                        dict,
                    ):
                        continue

                    step_status = str(
                        candidate_step.get("status")
                        or ""
                    ).strip().lower()

                    if step_status not in {
                        "completed",
                        "complete",
                        "failed",
                        "blocked",
                    }:
                        project_step = {
                            **candidate_step,
                            "project_context": (
                                candidate_step.get(
                                    "project_context"
                                )
                                or candidate_step.get(
                                    "context"
                                )
                                or active_project.get(
                                    "description"
                                )
                                or active_project.get(
                                    "request"
                                )
                                or active_project.get(
                                    "title"
                                )
                                or active_project.get(
                                    "name"
                                )
                                or ""
                            ),
                            "goal": (
                                candidate_step.get(
                                    "goal"
                                )
                                or active_project.get(
                                    "description"
                                )
                                or active_project.get(
                                    "request"
                                )
                                or active_project.get(
                                    "title"
                                )
                                or active_project.get(
                                    "name"
                                )
                                or ""
                            ),
                            "content": (
                                candidate_step.get(
                                    "content"
                                )
                                or candidate_step.get(
                                    "file_content"
                                )
                                or task.get(
                                    "content"
                                )
                                or active_project.get(
                                    "content"
                                )
                                or ""
                            ),
                        }
                        break

                if project_step is not None:
                    break

            if project_step is None:
                existing_execution_state = (
                    execution_state
                    if isinstance(
                        execution_state,
                        dict,
                    )
                    else {}
                )

                existing_steps = (
                    existing_execution_state.get(
                        "steps"
                    )
                    if isinstance(
                        existing_execution_state.get(
                            "steps"
                        ),
                        list,
                    )
                    else []
                )

                current_index = existing_execution_state.get(
                    "current_index",
                    0,
                )

                try:
                    current_index = int(
                        current_index
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    current_index = 0

                if (
                    0 <= current_index < len(
                        existing_steps
                    )
                    and isinstance(
                        existing_steps[current_index],
                        dict,
                    )
                ):
                    project_step = dict(
                        existing_steps[
                            current_index
                        ]
                    )

                    print(
                        "[CHAT_HANDLE APPROVAL FALLBACK TO EXECUTION STEP]",
                        {
                            "current_index": current_index,
                            "action": project_step.get(
                                "action"
                            ),
                            "target_file": project_step.get(
                                "target_file"
                            ),
                            "approval_required": project_step.get(
                                "approval_required"
                            ),
                            "approval_status": project_step.get(
                                "approval_status"
                            ),
                        },
                        flush=True,
                    )

            if project_step is None:
                raise RuntimeError(
                    "No pending project execution step found."
                )
            existing_execution_state = (
                execution_state
                if isinstance(execution_state, dict)
                else {}
            )

            existing_status = str(
                existing_execution_state.get("status") or ""
            ).strip().lower()

            existing_steps = (
                existing_execution_state.get("steps")
                if isinstance(
                    existing_execution_state.get("steps"),
                    list,
                )
                else []
            )

            existing_waiting_approval = (
                existing_status == "waiting_approval"
                or existing_execution_state.get(
                    "waiting"
                ) is True
                or existing_execution_state.get(
                    "approval_required"
                ) is True
                or any(
                    isinstance(step, dict)
                    and (
                        step.get("approval_required") is True
                        or step.get("requires_approval") is True
                        or step.get("status")
                        in {
                            "waiting_approval",
                            "awaiting_approval",
                            "approval_required",
                        }
                    )
                    for step in existing_steps
                )
            )

            if existing_waiting_approval:
                execution_state = existing_execution_state

                execution_state["status"] = "waiting_approval"
                execution_state["waiting"] = True
                execution_state["complete"] = False
                execution_state["continue_request"] = True

                print(
                    "[CHAT_HANDLE PRESERVED APPROVAL EXECUTION]",
                    {
                        "status": execution_state.get(
                            "status"
                        ),
                        "waiting": execution_state.get(
                            "waiting"
                        ),
                        "approval_status": execution_state.get(
                            "approval_status"
                        ),
                        "current_index": execution_state.get(
                            "current_index"
                        ),
                    },
                    flush=True,
                )

            else:
                execution_state = {
                    "status": "ready",
                    "goal": (
                        active_project.get(
                            "description"
                        )
                        or active_project.get(
                            "request"
                        )
                        or active_project.get(
                            "title"
                        )
                        or active_project.get(
                            "name"
                        )
                        or project_step.get(
                            "title"
                        )
                    ),
                    "steps": [
                        project_step
                    ],
                    "current_index": 0,
                    "current_step": project_step.get(
                        "id"
                    ),
                    "complete": False,
                    "command": "run_step",
                    "intent": decision_intent,
                    "mode": "execution",
                    "continue_request": True,
                }

            print(
                "[CHAT_HANDLE PROJECT EXECUTION STATE]",
                {
                    "project_id": (
                        active_project.get("id")
                        if isinstance(
                            active_project,
                            dict,
                        )
                        else None
                    ),
                    "step_id": project_step.get(
                        "id"
                    ),
                    "task_id": project_step.get(
                        "task_id"
                    ),
                    "target_file": project_step.get(
                        "target_file"
                    ),
                    "action": project_step.get(
                        "action"
                    ),
                },
                flush=True,
            )



            if (
                isinstance(
                    execution_state,
                    dict,
                )
                and execution_state
            ):

                try:

                    service._save_execution_state(
                        session_id,
                        execution_state,
                    )

                except Exception as exc:

                    print(
                        "[CHAT_HANDLE SAVE EXECUTION STATE FAILED]",
                        repr(exc),
                        flush=True,
                    )

                try:

                    service._set_session_meta(
                        session_id,
                        "active_execution",
                        execution_state,
                    )

                except Exception as exc:

                    print(
                        "[CHAT_HANDLE SESSION META SAVE FAILED]",
                        repr(exc),
                        flush=True,
                    )

            # ======================================
            # VALIDATE PLAN
            # ======================================

            if not isinstance(
                execution_state,
                dict,
            ):

                raise RuntimeError(
                    "Execution planner did not return "
                    "a valid execution state."
                )

            steps = execution_state.get(
                "steps"
            ) or []

            if not isinstance(
                steps,
                list,
            ):

                raise RuntimeError(
                    "Execution planner returned "
                    "an invalid steps collection."
                )

            if not steps:

                raise RuntimeError(
                    "Execution request could not be "
                    "converted into an execution plan."
                )

            print(
                "[CHAT_HANDLE EXECUTION READY]",
                {
                    "session_id": session_id,
                    "goal": execution_state.get(
                        "goal"
                    ),
                    "step_count": len(steps),
                    "current_index": execution_state.get(
                        "current_index"
                    ),
                },
                flush=True,
            )

            # ======================================
            # EXECUTION RUN
            # ======================================

            execution_result = orchestrator.process_execution(
                session_id=session_id,
                state=execution_state,
                command="run_step",
            )


            if execution_result is None:

                raise RuntimeError(
                    "Execution orchestrator returned "
                    "None after receiving a valid plan."
                )

            if isinstance(
                execution_result,
                dict,
            ):

                nested_execution_state = (
                    execution_result.get(
                        "execution_state"
                    )
                )

                if isinstance(
                    nested_execution_state,
                    dict,
                ) and nested_execution_state.get(
                    "steps"
                ):

                    merged_execution_state = dict(
                        execution_state
                    )

                    merged_execution_state.update(
                        nested_execution_state
                    )

                    execution_state = (
                        merged_execution_state
                    )

                else:

                    # The orchestrator may return only
                    # completion metadata. Preserve the
                    # original plan and merge the metadata.
                    execution_state = dict(
                        execution_state
                    )

                    for key in (
                        "status",
                        "complete",
                        "waiting",
                        "current_index",
                        "current_step",
                        "current_step_title",
                        "current_step_index",
                        "history",
                        "last_action",
                        "updated_at",
                        "error",
                    ):

                        if key in execution_result:
                            execution_state[key] = (
                                execution_result[key]
                            )

                    approval_prompt = ""

                    steps = execution_state.get(
                        "steps"
                    ) or []

                    for step in steps:
                        if not isinstance(
                            step,
                            dict,
                        ):
                            continue

                        result_text = str(
                            step.get("result") or ""
                        ).strip()

                        if (
                            "approval is required" in result_text.lower()
                            or "do you approve" in result_text.lower()
                            or "approve? (yes/no)" in result_text.lower()
                        ):
                            approval_prompt = result_text

                            step["status"] = "waiting"
                            step["waiting"] = True
                            step["approval_required"] = True
                            step["approval_prompt"] = result_text

                            break

                    if approval_prompt:

                        execution_state["status"] = (
                            "waiting"
                        )

                        execution_state["complete"] = (
                            False
                        )

                        execution_state["waiting"] = (
                            True
                        )

                        execution_state["approval_required"] = (
                            True
                        )

                        execution_state["approval_prompt"] = (
                            approval_prompt
                        )

                        execution_state["current_index"] = max(
                            0,
                            len(steps) - 1,
                        )

                        execution_state[
                            "current_step_index"
                        ] = execution_state[
                            "current_index"
                        ]

                        execution_state[
                            "current_step"
                        ] = steps[
                            execution_state["current_index"]
                        ].get(
                            "title"
                        ) or ""

                        execution_state[
                            "current_step_title"
                        ] = execution_state[
                            "current_step"
                        ]

                    elif execution_result.get(
                        "status"
                    ) == "success":

                        execution_state["status"] = (
                            "success"
                        )

                        execution_state["complete"] = (
                            True
                        )

                        execution_state["waiting"] = (
                            False
                        )

                        execution_state[
                            "current_index"
                        ] = len(
                            execution_state.get(
                                "steps"
                            ) or []
                        )

                        execution_state[
                            "current_step_index"
                        ] = execution_state[
                            "current_index"
                        ]

                        execution_state[
                            "current_step"
                        ] = ""

                        execution_state[
                            "current_step_title"
                        ] = ""

                    if not isinstance(
                        steps,
                        list,
                    ) or not steps:

                        raise RuntimeError(
                            "Execution orchestrator returned "
                            "an execution state without steps."
                        )

                    service._save_execution_state(
                        session_id,
                        execution_state,
                    )

                    service._set_session_meta(
                        session_id,
                        "active_execution",
                        execution_state,
                    )

                    assistant_text = (
                        approval_prompt
                        if approval_prompt
                        else (
                            execution_result.get("message")
                            if execution_state.get("status")
                            not in {"failed", "error", "cancelled"}
                            else (
                                execution_result.get("message")
                                or "Execution step failed."
                            )
                        )
                    )


                    return {
                        "ok": execution_result.get(
                            "ok",
                            True,
                        ),
                        "assistant_message": (
                            execution_result.get(
                                "assistant_message"
                            )
                            or {
                                "role": "assistant",
                                "text": "",
                            }
                        ),
                        "session_id": session_id,
                        "execution": execution_result.get(
                            "execution",
                            execution_state,
                        ),
                        "execution_state": execution_result.get(
                            "execution",
                            execution_state,
                        ),
                        "step_output": execution_result.get(
                            "step_output",
                            "",
                        ),
                    }

                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": str(
                            execution_result
                        ),
                    },
                    "session_id": session_id,
                    "execution": execution_result,
                    "execution_state": execution_result,
                }

        # ==========================================
        # WEB FETCH ROUTE
        # ==========================================
        if route == "web_fetch":

            return service._execute_web_fetch(
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
                decision=decision,
            )

        # ==========================================
        # PLANNER ROUTE
        # ==========================================

        if (
            route == "planner"
            or intent == "planning"
            or mode == "planning"
        ) and len(user_text.split()) > 3:

            try:

                execution_state = (
                    service._process_goal_and_plan(
                        user_text,
                        session_id,
                    )
                )

                decision[
                    "execution_state"
                ] = execution_state

                service._save_execution_state(
                    session_id,
                    execution_state,
                )

                service._set_session_meta(
                    session_id,
                    "active_execution",
                    execution_state,
                )

            except Exception as exc:

                print(
                    "[PLANNER EXECUTION FAILED]",
                    repr(exc),
                    flush=True,
                )

        if (
            route == "planner"
            and isinstance(
                brain_state,
                dict,
            )
            and brain_state.get("plan")
        ):

            decision[
                "brain_plan"
            ] = brain_state["plan"]

        # ==========================================
        # MEMORY RECALL
        # ==========================================

        if route == "memory_recall":

            return service._execute_memory_recall(
                decision=decision,
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
            )

        # ==========================================
        # PROJECT STATE / NEXT STEP ROUTE
        # ==========================================

        print(
            "[CHAT_HANDLE MISSION CONTROL GATE]",
            {
                "intent": intent,
                "brain_state_type": type(brain_state).__name__,
                "brain_state": brain_state,
            },
            flush=True,
        )

        if (
            intent == "mission_control"
            and isinstance(
                brain_state,
                dict,
            )
        ):

            if (
                decision_intent == "task_execution"
                and not execution_state
            ):
                project_builder = getattr(
                    service,
                    "project_builder_service",
                    None,
                )

                if project_builder is not None:
                    project_result = (
                        project_builder.build_project_from_request(
                            user_text=user_text,
                            owner_id=get_current_user_id(),
                        )
                    )

                    print(
                        "[CHAT_HANDLE FRESH PROJECT BOOTSTRAP]",
                        {
                            "project_id": (
                                project_result.get("project_id")
                                if isinstance(
                                    project_result,
                                    dict,
                                )
                                else None
                            ),
                            "task_count": len(
                                (
                                    project_result.get("tasks")
                                    if isinstance(
                                        project_result,
                                        dict,
                                    )
                                    else []
                                )
                                or []
                            ),
                        },
                        flush=True,
                    )

            project_workspace = getattr(
                service,
                "project_workspace_service",
                None,
            )

            active_project = (
                project_workspace.get_active_project()
                if project_workspace is not None
                and hasattr(
                    project_workspace,
                    "get_active_project",
                )
                else None
            )

            if not isinstance(
                active_project,
                dict,
            ):
                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "No active project is available."
                        ),
                    },
                    "session_id": session_id,
                    "brain_state": brain_state,
                }

            next_step = (
                brain_state.get("next_step")
                or brain_state.get("current_step")
            )

            if isinstance(
                next_step,
                dict,
            ):
                next_step = dict(
                    next_step
                )

            if not isinstance(
                next_step,
                dict,
            ):
                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "No active project step is available yet."
                        ),
                    },
                    "session_id": session_id,
                    "brain_state": brain_state,
                }

            print(
                "[CHAT_HANDLE NEXT STEP EXECUTION]",
                {
                    "project_id": active_project.get("id"),
                    "task_id": (
                        next_step.get("task_id")
                        or next_step.get("id")
                    ),
                    "title": (
                        next_step.get("title")
                        or next_step.get("name")
                    ),
                    "status": next_step.get("status"),
                },
                flush=True,
            )

            # ------------------------------------------
            # Build an execution state from the actual
            # project step selected by project brain.
            # ------------------------------------------

            project_step = None

            tasks = (
                active_project.get("tasks")
                or []
            )

            next_task_id = str(
                next_step.get("task_id")
                or next_step.get("id")
                or ""
            ).strip()

            # ---------------------------------------------------------
            # First, locate the task selected by project brain.
            # ---------------------------------------------------------

            selected_task = None

            for task in tasks:
                if not isinstance(
                    task,
                    dict,
                ):
                    continue

                task_id = str(
                    task.get("id")
                    or ""
                ).strip()

                if (
                    next_task_id
                    and task_id
                    and task_id == next_task_id
                ):
                    selected_task = task
                    break

            # ---------------------------------------------------------
            # If project brain selected an approval/precondition task,
            # do not execute that task as the mutation itself.
            #
            # Find the concrete mutation task that has an actual
            # target/content/action and preserve its approval metadata.
            # ---------------------------------------------------------

            mutation_actions = {
                "create",
                "write",
                "modify",
                "update",
                "patch",
                "replace",
                "delete",
                "remove",
            }

            selected_action = str(
                (selected_task or {}).get("action")
                or ""
            ).strip().lower()

            selected_target = str(
                (selected_task or {}).get("target_file")
                or ""
            ).strip()

            selected_content = (
                (selected_task or {}).get("content")
                or (selected_task or {}).get("file_content")
                or ""
            )

            selected_is_concrete_mutation = (
                selected_action in mutation_actions
                and bool(
                    selected_target
                    or selected_content
                )
            )

            if (
                selected_task is not None
                and not selected_is_concrete_mutation
            ):
                for candidate_task in tasks:
                    if not isinstance(
                        candidate_task,
                        dict,
                    ):
                        continue

                    candidate_action = str(
                        candidate_task.get("action")
                        or ""
                    ).strip().lower()

                    candidate_target = str(
                        candidate_task.get("target_file")
                        or ""
                    ).strip()

                    candidate_content = (
                        candidate_task.get("content")
                        or candidate_task.get("file_content")
                        or ""
                    )

                    if (
                        candidate_action in mutation_actions
                        and (
                            candidate_target
                            or candidate_content
                        )
                    ):
                        selected_task = candidate_task
                        break

            # ---------------------------------------------------------
            # Build the execution step from the selected concrete task.
            # ---------------------------------------------------------

            if isinstance(
                selected_task,
                dict,
            ):
                task_id = str(
                    selected_task.get("id")
                    or ""
                ).strip()

                candidate_steps = (
                    selected_task.get("steps")
                    or []
                )

                for candidate_step in candidate_steps:
                    if not isinstance(
                        candidate_step,
                        dict,
                    ):
                        continue

                    project_step = {
                        **candidate_step,
                        "task_id": task_id,
                        "title": (
                            candidate_step.get("title")
                            or selected_task.get("title")
                            or next_step.get("title")
                            or ""
                        ),
                        "project_context": (
                            candidate_step.get(
                                "project_context"
                            )
                            or active_project.get(
                                "description"
                            )
                            or active_project.get(
                                "request"
                            )
                            or active_project.get(
                                "title"
                            )
                            or ""
                        ),
                        "goal": (
                            candidate_step.get(
                                "goal"
                            )
                            or selected_task.get(
                                "goal"
                            )
                            or active_project.get(
                                "description"
                            )
                            or active_project.get(
                                "request"
                            )
                            or active_project.get(
                                "title"
                            )
                            or ""
                        ),
                        "content": (
                            candidate_step.get(
                                "content"
                            )
                            or candidate_step.get(
                                "file_content"
                            )
                            or selected_task.get(
                                "content"
                            )
                            or ""
                        ),
                    }

                    break

                if project_step is None:
                    project_step = {
                        **selected_task,
                        "task_id": task_id,
                        "project_context": (
                            active_project.get(
                                "description"
                            )
                            or active_project.get(
                                "request"
                            )
                            or active_project.get(
                                "title"
                            )
                            or ""
                        ),
                        "goal": (
                            selected_task.get("goal")
                            or active_project.get(
                                "description"
                            )
                            or active_project.get(
                                "request"
                            )
                            or active_project.get(
                                "title"
                            )
                            or ""
                        ),
                    }

            if project_step is None:
                project_step = next_step

            existing_execution = (
                service._load_execution_state(
                    session_id
                )
                or {}
            )

            project_execution = (
                active_project.get(
                    "execution"
                )
                if isinstance(
                    active_project,
                    dict,
                )
                else {}
            )

            existing_status = str(
                existing_execution.get(
                    "status",
                    "",
                )
                or ""
            ).strip().lower()

            project_execution_status = str(
                project_execution.get(
                    "status",
                    "",
                )
                or ""
            ).strip().lower()

            if (
                isinstance(
                    project_execution,
                    dict,
                )
                and project_execution.get(
                    "current_task_id"
                )
                and project_execution_status
                in {
                    "paused",
                    "waiting",
                    "waiting_approval",
                }
            ):
                execution_state = dict(
                    existing_execution
                )

                if not execution_state.get(
                    "steps"
                ):
                    execution_state["steps"] = [
                        project_step
                    ]

                execution_state.update(
                    {
                        "status": project_execution_status,
                        "waiting": True,
                        "approval_required": True,
                        "complete": False,
                        "project_id": active_project.get(
                            "id"
                        ),
                        "current_task_id": project_execution.get(
                            "current_task_id"
                        ),
                        "current_step": project_execution.get(
                            "current_step"
                        ),
                    }
                )

                print(
                    "[CHAT HANDLE NEXT STEP USING PROJECT PAUSED EXECUTION]",
                    {
                        "status": execution_state.get(
                            "status"
                        ),
                        "current_task_id": execution_state.get(
                            "current_task_id"
                        ),
                        "current_step": execution_state.get(
                            "current_step"
                        ),
                    },
                    flush=True,
                )

            elif (
                isinstance(
                    existing_execution,
                    dict,
                )
                and existing_execution.get(
                    "steps"
                )
                and (
                    existing_status
                    in {
                        "waiting",
                        "waiting_approval",
                        "paused",
                    }
                    or existing_execution.get(
                        "waiting"
                    )
                    is True
                    or existing_execution.get(
                        "approval_required"
                    )
                    is True
                )
            ):
                execution_state = existing_execution

                print(
                    "[CHAT HANDLE NEXT STEP REUSING EXISTING EXECUTION]",
                    {
                        "status": execution_state.get(
                            "status"
                        ),
                        "waiting": execution_state.get(
                            "waiting"
                        ),
                        "approval_required": execution_state.get(
                            "approval_required"
                        ),
                        "current_index": execution_state.get(
                            "current_index"
                        ),
                        "current_step": execution_state.get(
                            "current_step"
                        ),
                    },
                    flush=True,
                )

            else:
                execution_state = {
                    "status": "ready",
                    "goal": (
                        project_step.get("goal")
                        or active_project.get(
                            "description"
                        )
                        or active_project.get(
                            "request"
                        )
                        or active_project.get(
                            "title"
                        )
                        or project_step.get(
                            "title"
                        )
                        or ""
                    ),
                    "steps": [
                        project_step
                    ],
                    "current_index": 0,
                    "current_step": (
                        project_step.get(
                            "id"
                        )
                        or project_step.get(
                            "task_id"
                        )
                        or project_step.get(
                            "title"
                        )
                        or ""
                    ),
                    "complete": False,
                    "command": "run_step",
                    "intent": "execution_continuation",
                    "mode": "execution",
                    "continue_request": True,
                    "project_id": active_project.get(
                        "id"
                    ),
                }

            print(
                "[CHAT_HANDLE NEXT STEP EXECUTION STATE]",
                execution_state,
                flush=True,
            )

            orchestrator = getattr(
                service,
                "execution_orchestrator_service",
                None,
            )

            if orchestrator is None:
                raise RuntimeError(
                    "ExecutionOrchestratorService "
                    "is not configured."
                )

            execution_result = (
                orchestrator.process_execution(
                    session_id=session_id,
                    state=execution_state,
                    command="run_step",
                )
            )

            if execution_result is None:
                raise RuntimeError(
                    "Execution orchestrator returned "
                    "None for next-step execution."
                )

            if isinstance(
                execution_result,
                dict,
            ):
                returned_execution = (
                    execution_result.get(
                        "execution"
                    )
                    or execution_result.get(
                        "execution_state"
                    )
                    or execution_state
                )

                if isinstance(
                    returned_execution,
                    dict,
                ):
                    execution_state.update(
                        returned_execution
                    )

                service._save_execution_state(
                    session_id,
                    execution_state,
                )

                service._set_session_meta(
                    session_id,
                    "active_execution",
                    execution_state,
                )

                return {
                    "ok": execution_result.get(
                        "ok",
                        True,
                    ),
                    "assistant_message": (
                        execution_result.get(
                            "assistant_message"
                        )
                        or {
                            "role": "assistant",
                            "text": (
                                execution_result.get(
                                    "message"
                                )
                                or execution_state.get(
                                    "current_step"
                                )
                                or "Execution continued."
                            ),
                        }
                    ),
                    "session_id": session_id,
                    "execution": execution_result.get(
                        "execution",
                        execution_state,
                    ),
                    "execution_state": execution_state,
                    "step_output": execution_result.get(
                        "step_output",
                        "",
                    ),
                    "brain_state": brain_state,
                }

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": str(
                        execution_result
                    ),
                },
                "session_id": session_id,
                "execution": execution_result,
                "execution_state": execution_state,
                "brain_state": brain_state,
            }


        # ==========================================
        # NORMAL MODEL CHAT
        # ==========================================

        print(
            "[CHAT_HANDLE BEFORE MODEL]",
            round(
                time.perf_counter() - _t0,
                3,
            ),
            flush=True,
        )

        response_text = (
            service._run_chat_model(
                user_text=user_text,
                decision=decision,
                session_id=session_id,
                requested_model=decision.get(
                    "model"
                ),
            )
        )

        print(
            "[CHAT_HANDLE AFTER MODEL]",
            round(
                time.perf_counter() - _t0,
                3,
            ),
            flush=True,
        )

        result = service._finalize_response(
            execution_state=(
                decision.get(
                    "execution_state"
                )
                or {}
            ),
            session_id=session_id,
            user_text=user_text,
            user_msg=service._build_user_message(
                user_text,
                attachments=attachments,
            ),
            assistant_msg=(
                service._build_assistant_message(
                    text=response_text,
                    meta={
                        "route": (
                            route
                            or "general_chat"
                        ),
                    },
                    attachments=[],
                )
            ),
            attachments=attachments,
            decision=decision,
            regenerate=regenerate,
            saved_artifact=None,
        )

        print(
            "[CHAT_HANDLE COMPLETE]",
            round(
                time.perf_counter() - _t0,
                3,
            ),
            flush=True,
        )

        return result

    except Exception as exc:

        print(
            "[CHAT_HANDLE FAILED]",
            repr(exc),
            flush=True,
        )

        traceback.print_exc()

        return {
            "ok": False,
            "assistant_message": {
                "role": "assistant",
                "text": (
                    "Nova handler error: "
                    f"{exc}"
                ),
            },
            "session_id": session_id,
        }
