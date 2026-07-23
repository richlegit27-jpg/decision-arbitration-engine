class ExecutionMutationService:

    def __init__(self, execution_state_service=None):
        self.execution_state_service = execution_state_service

    def mark_running(
        self,
        execution_state,
        step_index=0,
        current_step="",
        waiting=False,
    ):
        execution_state = dict(execution_state or {})

        execution_state["status"] = "running"
        execution_state["complete"] = False
        execution_state["waiting"] = bool(waiting)
        execution_state["lock"] = False

        execution_state["current_index"] = step_index
        execution_state["current_step"] = current_step or ""
        execution_state["current_step_title"] = current_step or ""

        return execution_state

    def mark_complete(
        self,
        execution_state,
    ):
        execution_state = dict(execution_state or {})

        steps = execution_state.get("steps") or []

        execution_state["status"] = "complete"
        execution_state["complete"] = True
        execution_state["waiting"] = False
        execution_state["lock"] = False

        execution_state["next_moves"] = []

        execution_state["current_index"] = len(steps)

        execution_state["current_step"] = ""
        execution_state["current_step_title"] = ""

        execution_state["progress"] = len(steps)

        return execution_state

    def mark_failed(
        self,
        execution_state,
        step_index=0,
        error="",
    ):
        execution_state = dict(
            execution_state or {}
        )

        execution_state["status"] = "failed"
        execution_state["complete"] = False
        execution_state["waiting"] = True
        execution_state["lock"] = False
        execution_state["current_index"] = (
            step_index
        )
        execution_state[
            "current_step_index"
        ] = step_index
        execution_state[
            "failed_step_index"
        ] = step_index
        execution_state["error"] = str(
            error
            or "Execution step failed."
        )
        execution_state[
            "_execution_processing"
        ] = False

        return execution_state

    def mark_waiting_approval(
        self,
        execution_state,
        step_index=0,
        reason="",
    ):
        execution_state = dict(
            execution_state or {}
        )

        execution_state["status"] = (
            "waiting_approval"
        )
        execution_state["complete"] = False
        execution_state["waiting"] = True
        execution_state["lock"] = False
        execution_state["current_index"] = (
            step_index
        )
        execution_state[
            "current_step_index"
        ] = step_index
        execution_state[
            "approval_required"
        ] = True
        execution_state[
            "approval_status"
        ] = "pending"
        execution_state["error"] = str(
            reason
            or (
                "Approval required "
                "before execution."
            )
        )
        execution_state[
            "_execution_processing"
        ] = False

        return execution_state

    def append_history(
        self,
        execution_state,
        message,
    ):
        if not isinstance(execution_state, dict):
            execution_state = {}

        history = execution_state.get("history")

        if not isinstance(history, list):
            history = []

        history.append(message)
        execution_state["history"] = history

        return execution_state

    def prepare_failed_retry(
        self,
        execution_state,
    ):
        if not isinstance(execution_state, dict):
            execution_state = {}

        failure_count = (
            int(
                execution_state.get(
                    "failure_count"
                )
                or 0
            )
            + 1
        )

        execution_state["failure_count"] = (
            failure_count
        )

        steps = execution_state.get("steps") or []

        failed_index = None

        for index, step in enumerate(steps):
            if (
                isinstance(step, dict)
                and step.get("status") == "failed"
            ):
                failed_index = index
                break

        if failed_index is None:
            return execution_state, None



        strategies = {
            1: "retry_step",
            2: "retry_with_smaller_scope",
            3: "retry_with_file_scope",
        }

        execution_state["failure_count"] = (
            failure_count
        )
        execution_state["current_index"] = (
            failed_index
        )
        execution_state["retry_strategy"] = (
            strategies.get(
                failure_count,
                "change_strategy",
            )
        )

        return execution_state, failed_index

    def cancel(
        self,
        execution_state,
    ):
        if not isinstance(execution_state, dict):
            execution_state = {}

        execution_state["status"] = "cancelled"
        execution_state["waiting"] = False
        execution_state["lock"] = False
        execution_state["next_moves"] = []
        execution_state["current_step"] = ""
        execution_state["current_step_title"] = ""

        return execution_state

    def reset(
        self,
        execution_state=None,
    ):
        if not isinstance(execution_state, dict):
            execution_state = {}

        execution_state = dict(execution_state)

        execution_state["status"] = "idle"
        execution_state["waiting"] = False
        execution_state["complete"] = False
        execution_state["active"] = False

        execution_state["steps"] = []
        execution_state["plan"] = []
        execution_state["current_index"] = 0
        execution_state["history"] = []

        execution_state["current_step"] = ""
        execution_state["current_step_title"] = ""
        execution_state["last_action"] = ""

        return execution_state