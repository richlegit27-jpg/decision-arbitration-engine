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