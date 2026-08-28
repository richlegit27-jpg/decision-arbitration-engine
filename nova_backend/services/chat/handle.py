import traceback
import time


def chat_handle(
    service,
    user_text: str,
    session_id: str = "",
    attachments=None,
    brain_state=None,
    decision=None,
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

    print(
        "DEBUG ORCHESTRATOR PLAN:",
        brain_state.get("plan")
        if isinstance(brain_state, dict)
        else None,
        flush=True,
    )

    print(
        "DEBUG ORCHESTRATOR EXECUTION:",
        brain_state.get("execution")
        if isinstance(brain_state, dict)
        else None,
        flush=True,
    )

    attachments = attachments or []

    print(
        "[CHAT_HANDLE AFTER ATTACHMENTS]",
        round(time.perf_counter() - _t0, 3),
        flush=True,
    )

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
            print(
                "[CHAT_HANDLE BEFORE ROUTER]",
                round(time.perf_counter() - _t0, 3),
                flush=True,
            )

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
                flush=True,
            )

            if isinstance(routed, dict):
                decision.update(routed)

            print(
                "[CHAT_HANDLE AFTER ROUTER]",
                round(time.perf_counter() - _t0, 3),
                flush=True,
            )

        except Exception as exc:
            print(
                "[CHAT ROUTER FAILED]",
                repr(exc),
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
        ) and (
            len(user_text.split()) > 3
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

        if route == "planner" and isinstance(brain_state, dict):
            if brain_state.get("plan"):
                decision["brain_plan"] = brain_state["plan"]

        if route == "memory_recall":
            return service._execute_memory_recall(
                decision=decision,
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
            )

        print(
            "[CHAT_HANDLE BEFORE MODEL]",
            round(time.perf_counter() - _t0, 3),
            flush=True,
        )

        response_text = service._run_chat_model(
            user_text=user_text,
            decision=decision,
            session_id=session_id,
        )

        print(
            "[CHAT_HANDLE AFTER MODEL]",
            round(time.perf_counter() - _t0, 3),
            flush=True,
        )

        print(
            "DEBUG BEFORE FINALIZE DECISION =",
            decision,
            flush=True,
        )

        result = service._finalize_response(
            execution_state=(
                decision.get("execution_state")
                or {}
            ),
            session_id=session_id,
            user_text=user_text,
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

        print(
            "[CHAT_HANDLE COMPLETE]",
            round(time.perf_counter() - _t0, 3),
            flush=True,
        )

        return result

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