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
        user_text = service.safe_str(
            user_text
        ).strip()

        if not session_id:
            session_id = service._create_session()

        if not isinstance(decision, dict):
            decision = {
                "route": "general_chat",
                "intent": "chat",
            }

        try:
            if hasattr(service, "_decide_route"):
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

            print(
                "DEBUG PRIMARY ROUTE DECISION =",
                routed,
            )

            if isinstance(routed, dict):
                decision.update(routed)

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

        if route == "web_fetch":
            return service._execute_web_fetch(
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
                decision=decision,
            )

        if (
            route == "planner"
            or intent == "planning"
            or mode == "planning"
        ):
            try:
                execution_state = service._process_goal_and_plan(
                    user_text,
                    session_id,
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

        if route == "memory_recall":
            return service._execute_memory_recall(
                decision=decision,
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
            )

        response_text = service._run_chat_model(
            user_text=user_text,
            decision=decision,
            session_id=session_id,
        )

        print(
            "DEBUG BEFORE FINALIZE DECISION =",
            decision,
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
                    "route": "general_chat",
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