import uuid

class ExecutionStreamService:

    def __init__(
        self,
        session_service,
        chat_service,
        default_executor,
        next_move_class,
        update_execution_state_safe,
    ):
        self.session_service = session_service
        self.chat_service = chat_service
        self.default_executor = default_executor
        self.NextMove = next_move_class
        self.update_execution_state_safe = update_execution_state_safe

    def send_event(self, name, payload):
        import json

        return (
            f"event: {name}\n"
            f"data: {json.dumps(payload)}\n\n"
        )

    def save_execution(
        self,
        session_id,
        execution,
    ):
        session = self.session_service.get_session(
            session_id
        )

        if not isinstance(session, dict):
            return

        working_state = session.get(
            "working_state",
            {},
        )

        if not isinstance(working_state, dict):
            working_state = {}

        working_state["execution"] = execution

        session["working_state"] = working_state

        self.session_service.update_session(
            session_id,
            session,
        )

    def replay_existing_step(
        self,
        execution,
        replay_step,
        step_title,
        action,
    ):
        move = (
            replay_step.get("move")
            if isinstance(replay_step, dict)
            else None
        )

        if not isinstance(move, dict):
            replay_step["status"] = "failed"
            replay_step["output"] = {
                "error": "Replay failed: no move stored on step.",
            }

            execution["status"] = "error"
            execution["current_step"] = (
                f"Replay failed: {step_title}"
            )

            return replay_step

        replay_result = self.default_executor(
            self.NextMove(
                id=str(
                    move.get("id")
                    or f"replay-{uuid.uuid4().hex}"
                ),
                type=str(
                    move.get("type")
                    or "echo"
                ),
                payload=(
                    move.get("payload")
                    if isinstance(
                        move.get("payload"),
                        dict,
                    )
                    else {}
                ),
            )
        )

        replay_ok = bool(
            getattr(
                replay_result,
                "success",
                False,
            )
        )

        replay_step["status"] = (
            "done"
            if replay_ok
            else "failed"
        )

        replay_step["output"] = getattr(
            replay_result,
            "output",
            {},
        )

        runtime = getattr(
            self.chat_service,
            "runtime",
            None,
        )

        if runtime is not None:
            runtime_strategy_memory = getattr(
                runtime,
                "runtime_strategy_memory",
                None,
            )

            if isinstance(runtime_strategy_memory, list):
                runtime_strategy_memory.append(
                    {
                        "action": move.get("type") or action,
                        "success": replay_ok,
                        "failure": not replay_ok,
                        "runtime_signal": (
                            "execution_success"
                            if replay_ok
                            else "execution_failure"
                        ),
                        "score_delta": (
                            1
                            if replay_ok
                            else -1
                        ),
                    }
                )

        self.update_execution_state_safe(
            execution,
            status=(
                "complete"
                if replay_ok
                else "error"
            ),
        )

        execution["current_step"] = (
            "Replay complete"
            if replay_ok
            else f"Replay failed: {step_title}"
        )

        return replay_step