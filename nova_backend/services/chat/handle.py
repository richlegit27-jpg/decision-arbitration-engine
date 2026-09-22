            print(
                "[CHAT_HANDLE EXECUTION BOOTSTRAP]",
                {
                    "session_id": session_id,
                    "user_text": user_text,
                },
                flush=True,
            )

            try:

                execution_state = (
                    service._process_goal_and_plan(
                        user_text,
                        session_id,
                    )
                )

            except Exception as exc:

                print(
                    "[CHAT_HANDLE PLAN BOOTSTRAP FAILED]",
                    repr(exc),
                    flush=True,
                )

                traceback.print_exc()

                execution_state = {}

            print(
                "[CHAT_HANDLE BOOTSTRAPPED STATE]",
                execution_state,
                flush=True,
            )
import traceback
import time


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

            try:
                loaded_state = {}

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
                not execution_complete
                and (
                    decision_intent == "execution_continuation"
                    or not has_steps
                )
            ):


                decision_intent = (
                    decision.get("intent")
                    if isinstance(decision, dict)
                    else None
                )

                if decision_intent == "execution_continuation":

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

                    project_step = None

                    if isinstance(active_project, dict):

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
                or []
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
                raise RuntimeError(
                    "No pending project execution step found."
                )

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


                print(
                    "[CHAT_HANDLE EXECUTION BOOTSTRAP]",
                        {
                            "session_id": session_id,
                            "user_text": user_text,
                        },
                        flush=True,
                    )

                    try:

                        execution_state = (
                            service._process_goal_and_plan(
                                user_text,
                                session_id,
                            )
                        )

                    except Exception as exc:

                        print(
                            "[CHAT_HANDLE PLAN BOOTSTRAP FAILED]",
                            repr(exc),
                            flush=True,
                        )

                        traceback.print_exc()

                        execution_state = {}

                print(
                    "[CHAT_HANDLE BOOTSTRAPPED STATE]",
                    execution_state,
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

                    execution_result = (
                        service.execution_orchestrator_service.process_execution(
                            session_id=session_id,
                            state=execution_state,
                            command="run_step",
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

        if (
            intent == "mission_control"
            and isinstance(
                brain_state,
                dict,
            )
        ):

            next_step = (
                brain_state.get("next_step")
                or brain_state.get("current_step")
            )

            if isinstance(
                next_step,
                dict,
            ):
                next_step = (
                    next_step.get("title")
                    or next_step.get("name")
                    or str(next_step)
                )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": (
                        next_step
                        or "No active project step is available yet."
                    ),
                },
                "session_id": session_id,
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













