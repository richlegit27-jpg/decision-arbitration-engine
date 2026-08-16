import traceback


def chat_handle(
    service,
    user_text: str,
    session_id: str = "",
    attachments=None,
    brain_state=None,
    decision=None,
):
    print(
        "[CHAT HANDLE HIT]",
        {
            "user_text": user_text,
            "session_id": session_id,
        },
    )

    print(
        "DEBUG ORCHESTRATOR PLAN:",
        brain_state.get("plan")
        if isinstance(brain_state, dict)
        else None,
    )

    print(
        "DEBUG ORCHESTRATOR EXECUTION:",
        brain_state.get("execution")
        if isinstance(brain_state, dict)
        else None,
    )

    attachments = attachments or []

    try:
        user_text = service.safe_str(user_text).strip()

        if not session_id:
            session_id = service._create_session()

        if not isinstance(decision, dict):
            decision = {
                "route": "general_chat",
                "intent": "chat",
            }

        try:
            routed = service.chat_router.decide(
                user_text=user_text,
                attachments=attachments,
                session_id=session_id,
            )

            print(
                "DEBUG ROUTER RAW OUTPUT =",
                routed,
            )

            if isinstance(routed, dict):
                decision.update(routed)

            print(
                "DEBUG DECISION AFTER ROUTER UPDATE =",
                decision,
            )

        except Exception as exc:
            print(
                "[CHAT ROUTER FAILED]",
                repr(exc),
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
        )

        if (
            route == "planner"
            or intent == "planning"
            or mode == "planning"
        ):
            print(
                "DEBUG ENTERING PLANNER BLOCK"
            )

            try:
                execution_state = service._process_goal_and_plan(
                    user_text,
                    session_id,
                )

                print(
                    "DEBUG PROCESS GOAL PLAN RETURN =",
                    execution_state,
                )

                if execution_state:

                    try:
                        if hasattr(
                            service,
                            "execution_mutation_service",
                        ):
                            execution_state = (
                                service.execution_mutation_service.mark_running(
                                    execution_state
                                )
                            )

                    except Exception as exc:
                        print(
                            "[MARK RUNNING FAILED]",
                            repr(exc),
                        )

                decision["execution_state"] = execution_state

                service._save_execution_state(
                    session_id,
                    execution_state,
                )

                service._set_session_meta(
                    session_id,
                    "active_execution",
                    execution_state,
                )

                print(
                    "DEBUG STORED EXECUTION STATE =",
                    execution_state,
                )
            except Exception as exc:
                print(
                    "[PLANNER EXECUTION FAILED]",
                    repr(exc),
                )

        if (
            route == "planner"
            and isinstance(brain_state, dict)
            and brain_state.get("plan")
        ):
            decision["brain_plan"] = brain_state["plan"]

            print(
                "DEBUG BRAIN PLAN AVAILABLE:",
                decision["brain_plan"],
            )

        response_text = ""

        planner_source = None

        if (
            route == "planner"
            and isinstance(brain_state, dict)
            and isinstance(
                brain_state.get("plan"),
                dict,
            )
        ):
            planner_source = brain_state["plan"]

        elif (
            isinstance(decision, dict)
            and isinstance(
                decision.get("brain_plan"),
                dict,
            )
        ):
            planner_source = decision["brain_plan"]

        elif (
            isinstance(decision, dict)
            and isinstance(
                decision.get("execution_state"),
                dict,
            )
        ):
            planner_source = decision["execution_state"]

        if isinstance(planner_source, dict):

            goal = (
                planner_source.get("goal")
                or user_text
            )

            steps = (
                planner_source.get("steps")
                or planner_source.get("plan")
                or []
            )

            lines = []

            lines.append(
                f"Project Plan: {goal}"
            )

            lines.append("")

            for index, step in enumerate(
                steps,
                start=1,
            ):

                if isinstance(step, dict):

                    title = (
                        step.get("title")
                        or step.get("action")
                        or step.get("name")
                        or f"Step {index}"
                    )

                    status = (
                        step.get("status")
                        or "planned"
                    )

                    detail = (
                        step.get("input")
                        or step.get("result")
                        or ""
                    )

                    if detail:
                        lines.append(
                            f"{index}. {title} ({status}) - {detail}"
                        )
                    else:
                        lines.append(
                            f"{index}. {title} ({status})"
                        )

                else:
                    lines.append(
                        f"{index}. {step}"
                    )

            response_text = "\n".join(lines)

        if not response_text:
            response_text = service._run_chat_model(
                user_text=user_text,
                decision=decision,
                session_id=session_id,
            )

        print(
            "DEBUG BEFORE FINALIZE EXECUTION:",
            decision.get("execution_state"),
        )

        return service._finalize_response(
            execution_state=(
                decision.get("execution_state")
                or {}
            ),
            session_id=session_id,
            user_msg=service._build_user_message(
                user_text,
                attachments=attachments,
            ),
            assistant_msg=service._build_assistant_message(
                text=response_text,
                meta={
                    "route": (
                        "brain_planner_chat"
                        if (
                            isinstance(brain_state, dict)
                            and brain_state.get("plan")
                        )
                        else "rebuilt_chat_handler"
                    ),
                },
                attachments=[],
            ),
            decision=decision,
            saved_artifact=None,
        )

    except Exception as exc:
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