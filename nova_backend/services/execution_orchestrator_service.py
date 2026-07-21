from __future__ import annotations


class ExecutionOrchestratorService:

    def __init__(
        self,
        execution_handler,
        execution_state_service=None,
        working_state_service=None,
    ):
        self.execution_handler = execution_handler
        self.execution_state_service = execution_state_service
        self.working_state_service = working_state_service


    def process_execution(
        self,
        session_id: str,
        state: dict,
    ):
        # move _process_execution body here
        pass


    def execute_step_chain(
        self,
        session_id: str,
        state: dict,
    ):
        # move _execute_step_chain body here
        pass


    def run_execution_autoloop(
        self,
        session_id: str,
        max_steps: int = 5,
    ) -> str:
        # move _run_execution_autoloop body here
        pass






















    def _process_execution(
        self,
        execution_state: dict,
        session_id: str,
    ):

        execution_state = (
            execution_state
            or self._get_session_meta(
                session_id,
                "execution_state",
            )
            or {}
        )

        if not isinstance(execution_state, dict):
            execution_state = {}

        if not isinstance(execution_state.get("steps"), list):
            execution_state["steps"] = []

        if not isinstance(execution_state.get("plan"), list):
            execution_state["plan"] = execution_state["steps"]

        if not isinstance(
            execution_state.get("current_index"),
            int,
        ):
            execution_state["current_index"] = 0

        if not isinstance(
            execution_state.get("current_step"),
            str,
        ):
            execution_state["current_step"] = ""

        if not isinstance(
            execution_state.get("status"),
            str,
        ):
            execution_state["status"] = "idle"

        if not execution_state:
            return {}

        steps = execution_state.get("steps") or []

        current_index = int(
            execution_state.get(
                "current_index",
                0,
            )
            or 0
        )

        total = len(steps)

        # =========================
        # COMPLETION CHECK
        # =========================
        if current_index >= total:

            execution_state = self._mark_execution_complete(
                execution_state,
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

            return execution_state

        # =========================
        # LOCK GUARD (STOP DOUBLE NEXT)
        # =========================

        if execution_state.get("lock"):
            execution_state["lock"] = False

            self._save_execution_state(
                session_id,
                execution_state,
            )

        try:
            step = steps[current_index]

            if self._safe_str(step.get("status")).lower() == "completed":
                next_index = current_index + 1
                next_index = max(0, min(next_index, len(steps)))

                execution_state = self._sync_execution_state(
                    execution=execution_state,
                    current_index=next_index,
                    status="running" if next_index < len(steps) else "complete",
                    current_step=(
                        self._safe_str(steps[next_index].get("title"))
                        if next_index < len(steps)
                        else "complete"
                    ),
                    progress=next_index,
                )

            print(
                "EXECUTION REAL STEP RUNNING =",
                {
                    "index": current_index,
                    "step": step,
                    "title": step.get("title"),
                    "action": step.get("action"),
                    "status_before": step.get("status"),
                },
            )

            step["status"] = "running"

            self._execute_step_logic(
                session_id,
                step,
            )

            step["status"] = "completed"

            execution_state["steps"][current_index] = dict(step)

            steps = execution_state["steps"]

            execution_state["current_index"] = current_index + 1

            next_index = execution_state["current_index"]

            if next_index < len(steps):

                next_step = steps[next_index]

                execution_state["current_step"] = self._safe_str(next_step.get("title"))

                execution_state["current_step_title"] = self._safe_str(
                    next_step.get("title")
                )

                execution_state["next_moves"] = [
                    {
                        "type": next_step.get(
                            "action",
                            "execute",
                        ),
                        "title": next_step.get(
                            "title",
                            "",
                        ),
                        "step_index": next_index,
                    }
                ]

            else:

                execution_state = self._mark_execution_complete(
                    execution_state,
                )

            if self._safe_str(step.get("status")).lower() == "completed":

                next_index = current_index + 1

            execution_state["history"] = execution_state.get("history") or []

            execution_state["history"].append(f"completed: {step.get('title')}")

            current_index += 1

            execution_state["current_index"] = current_index

            if current_index < total:

                next_step = steps[current_index]

                execution_state["current_step_title"] = next_step.get(
                    "title",
                    "",
                )

                try:

                    current_step = steps[current_index]

                    current_file = str(current_step.get("target_file") or "").strip()

                    current_bug = str(current_step.get("error") or "").strip()

                    self._update_working_state(
                        session_id,
                        {
                            "current_file": current_file,
                            "current_bug": current_bug,
                            "active_task": (
                                execution_state.get("original_user_text", "")
                            ),
                            "next_move": (
                                current_step.get("title")
                                or current_step.get("action")
                                or "continue"
                            ),
                        },
                    )

                except Exception as e:

                    exec_debug(
                        "EXECUTION_STEP_SYNC_FAILED:",
                        e,
                    )

            else:

                execution_state["current_step_title"] = ""

            self._save_execution_state(
                session_id,
                execution_state,
            )

        except Exception as e:

            execution_state = self._mark_execution_failed(
                execution_state,
                step_index=current_index,
                error=str(e),
            )

            execution_state["last_error"] = str(e)

            self._save_active_execution(
                session_id,
                execution_state,
            )

            return execution_state

        # =========================
        # FINAL STATUS
        # =========================
        if current_index >= total:

            execution_state = self._mark_execution_complete(
                execution_state,
            )

        else:

            execution_state = self._mark_execution_running(
                execution_state,
                step_index=current_index,
                current_step=(
                    execution_state.get(
                        "current_step",
                        "",
                    )
                ),
                waiting=(not execution_state.get("auto_mode")),
            )

            if execution_state.get("auto_mode"):

                return self._process_execution(
                    execution_state,
                    session_id,
                )

        execution_state["current_step"] = current_index

        goal_text = self._safe_str(execution_state.get("goal")).lower().strip()

        if "respond normally" in goal_text:

            execution_state = {}

            self._save_execution_state(
                session_id,
                {},
            )

            return execution_state

        self._save_active_execution(
            session_id,
            execution_state,
        )

        return execution_state

    def _execute_step_chain(self, session_id: str, state: dict):
        if not state:
            return

        if state.get("status") != "running":
            return

        if state.get("complete"):
            return

        if state.get("execution_lock"):
            return

        state = self._run_next_step(state)

        goal_text = self._safe_str(state.get("goal")).lower().strip()

        if "respond normally" in goal_text:

            self._save_execution_state(
                session_id,
                {},
            )

            return

        self._set_session_meta(
            session_id,
            "execution_state",
            state,
        )

        # =========================
        # AUTO CONTINUE EVENT CHAIN
        # =========================
        if state.get("auto_mode") and state.get("status") == "running":
            self._execute_step_chain(session_id, state)