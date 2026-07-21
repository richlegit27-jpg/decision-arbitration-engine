from __future__ import annotations


class ExecutionOrchestratorService:

    def __init__(
        self,
        execution_handler,
        execution_state_service=None,
        working_state_service=None,
        safe_str=None,
        python_runner=None,
    ):
        self.execution_handler = execution_handler
        self.execution_state_service = execution_state_service
        self.working_state_service = working_state_service
        self._safe_str = safe_str
        self.python_runner = python_runner


    def _process_execution_command(
        self,
        command="",
        session_id="",
        execution_state=None,
    ):

        persisted_execution_state = {}

        execution_state = (
            execution_state
            if isinstance(
                execution_state,
                dict,
            )
            else {}
        )

        command = self._safe_str(command).strip().lower()

        intelligence_intent = (
            self._safe_str(
                execution_state.get("intent") or execution_state.get("mode") or ""
            )
            .strip()
            .lower()
        )

        if intelligence_intent in {
            "resume_execution",
            "continue_waiting_execution",
        }:
            command = "run_step"

        elif intelligence_intent == "run_all_steps":
            command = "run_all"

        elif intelligence_intent == "retry_failed_step":
            command = "retry_failed"

        elif intelligence_intent == "cancel_execution":
            command = "cancel"

        working_state = {}

        if self.working_state_service:
            working_state = (
                self.working_state_service.get_working_state(
                    session_id
                )
                or {}
            )
        persisted_execution_state = (
            self.execution_state_service.load(
                session_id
            )
            or {}
        )

        persisted_has_state = bool(persisted_execution_state.get("steps"))

        incoming_has_state = bool(execution_state.get("steps"))

        if persisted_has_state:

            execution_state = persisted_execution_state

        elif incoming_has_state:

            execution_state = execution_state

        else:

            execution_state = {}

        steps = execution_state.get("steps") or []

        current_index = int(
            execution_state.get(
                "current_index",
                0,
            )
            or 0
        )

        if not isinstance(
            steps,
            list,
        ):
            steps = []

        if current_index < 0:
            current_index = 0

        if current_index >= len(steps):
            current_index = len(steps)

        print(
            "EXECUTION DEBUG BEFORE COMPLETE CHECK =",
            {
                "command": command,
                "current_index": current_index,
                "steps_len": len(steps),
                "status": execution_state.get("status"),
                "current_step": execution_state.get("current_step"),
            },
        )

        # =========================
        # NEXT AFTER COMPLETION
        # =========================

        if command in {
            "next",
            "continue",
            "keep going",
            "run next",
        }:

            command = "run_step"

            current_index = int(
                execution_state.get(
                    "current_index",
                    0,
                )
                or 0
            )

            execution_state = (
                self.execution_mutation_service.mark_running(
                    execution_state,
                    step_index=current_index,
                    current_step=execution_state.get("current_step") or "",
                    waiting=False,
                )
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

        # =========================
        # RUN STEP
        # =========================
        if command in {
            "run_step",
            "run step",
        }:

            if not steps:

                persisted_execution = (
                    self.execution_state_service.load(
                        session_id
                    )
                    or {}
                )

                if isinstance(
                    persisted_execution,
                    dict,
                ) and persisted_execution.get("steps"):
                    execution_state = persisted_execution

                    current_index = int(
                        execution_state.get(
                            "current_index",
                            0,
                        )
                        or 0
                    )

                    steps = execution_state.get(
                        "steps",
                        [],
                    )

                    current_index = int(
                        execution_state.get(
                            "current_index",
                            0,
                        )
                    )

            if not steps:
                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "No active execution plan. "
                            "Start one with: auto-plan <goal>"
                        ),
                    },
                    "execution": execution_state,
                }

            while current_index < len(steps) and self._safe_str(
                steps[current_index].get("status")
            ).lower().strip() in {
                "completed",
                "done",
            }:
                current_index += 1

            execution_state["current_index"] = current_index

            if current_index >= len(steps):

                execution_state = (
                    self.execution_mutation_service.mark_complete(
                        execution_state,
                    )
                )
                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": ("All execution steps completed."),
                    },
                    "execution": execution_state,
                }

            refreshed_execution = (
                self.execution_state_service.load(
                    session_id
                )
                or execution_state
            )
            refreshed_steps = refreshed_execution.get("steps") or []

            if not isinstance(
                refreshed_steps,
                list,
            ) or current_index >= len(refreshed_steps):
                refreshed_steps = steps

            step = refreshed_steps[current_index]

            execution_state = refreshed_execution

            steps = refreshed_steps
            execution_state["current_index"] = current_index

            if current_index >= len(steps):
                execution_state = (
                    self.execution_mutation_service.mark_complete(
                        execution_state,
                    )
                )

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": "All execution steps completed.",
                    },
                    "execution": execution_state,
                }

            refreshed_execution = (
                self.execution_state_service.load(
                    session_id
                )
                or execution_state
            )
            
            refreshed_steps = refreshed_execution.get("steps") or []

            if not isinstance(
                refreshed_steps,
                list,
            ) or current_index >= len(refreshed_steps):
                refreshed_steps = steps

            original_step = (
                steps[current_index]
                if current_index < len(steps) and isinstance(steps[current_index], dict)
                else {}
            )

            refreshed_step = (
                refreshed_steps[current_index]
                if current_index < len(refreshed_steps)
                and isinstance(refreshed_steps[current_index], dict)
                else {}
            )

            step = {
                **original_step,
                **refreshed_step,
            }

            execution_state = refreshed_execution
            steps = refreshed_steps

            step["status"] = "running"

            execution_state = (
                self.execution_mutation_service.mark_running(
                    execution_state,
                    step_index=current_index,
                    current_step=step.get("title") or "",
                    waiting=False,
                )
            )

            result = self.execute_step_logic(
                session_id=session_id,
                step=step,
            )

            step["status"] = "completed"

            if result:
                step["result"] = result

            execution_state["steps"][current_index] = dict(step)

            steps = execution_state["steps"]

            result = step.get(
                "result",
                "",
            )

            execution_state = (
                self.execution_mutation_service.append_history(
                    execution_state,
                    f"completed: {step.get('title')}",
                )
            )

            execution_state["current_index"] = current_index + 1

            execution_state["current_step_index"] = current_index + 1

            execution_state["progress"] = current_index + 1

            execution_state["waiting"] = True

            execution_state["_execution_processing"] = False

            next_index = execution_state.get(
                "current_index",
                current_index + 1,
            )

            if next_index < len(steps):
                next_step = steps[next_index]

                execution_state["current_step"] = next_step.get("title") or ""

                execution_state["current_step_title"] = next_step.get("title") or ""
            execution_state["_execution_processing"] = False

            next_index = execution_state["current_index"]

            if next_index < len(steps):
                next_step = steps[next_index]

                execution_state["current_step"] = next_step.get("title") or ""

                execution_state["current_step_title"] = next_step.get("title") or ""

            self._save_execution_state(
                session_id,
                execution_state,
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": (f"Completed step: " f"{step.get('title')}"),
                },
                "execution": execution_state,
                "step_output": result,
            }

        # =========================
        # RUN ALL
        # =========================
        if command == "run_all":

            outputs = []
            loop_guard = 0

            while True:

                loop_guard += 1
                if loop_guard > 100:
                    return {
                        "ok": False,
                        "assistant_message": {
                            "role": "assistant",
                            "text": "Execution stopped because the run_all loop guard was reached.",
                        },
                        "execution": execution_state,
                    }

                current_index = int(execution_state.get("current_index", 0) or 0)

                if current_index >= len(steps):
                    execution_state = (
                        self.execution_mutation_service.mark_complete(
                            execution_state,
                        )
                    )
                    break

                step = steps[current_index]

                step["status"] = "running"

                execution_state["steps"][current_index] = dict(step)

                execution_state = (
                    self.execution_mutation_service.mark_running(
                        execution_state,
                        step_index=current_index,
                        current_step=step.get("title") or "",
                        waiting=False,
                    )
                )
                execution_state["_execution_processing"] = False

                self._save_active_execution(
                    session_id,
                    execution_state,
                )

                result = self.execute_step_logic(
                    session_id=session_id,
                    step=step,
                )

                print(
                    "AFTER EXECUTE STEP OBJECT =",
                    step,
                )

                print(
                    "AFTER EXECUTE EXECUTION STEPS BEFORE WRITEBACK =",
                    execution_state.get("steps"),
                )

                step["status"] = "completed"

                if result:
                    step["result"] = result

                execution_state["steps"][current_index] = dict(step)

                steps = execution_state["steps"]

                print(
                    "AFTER EXECUTE EXECUTION STEPS AFTER WRITEBACK =",
                    execution_state.get("steps"),
                )

                step_title = self._safe_str(step.get("title"))

                step_action = self._safe_str(step.get("action")).lower()

                target_file = self._safe_str(step.get("target_file"))

                python_result = None

                if step_action == "implement" and target_file:

                    Path(target_file).parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    Path(target_file).write_text(
                        """
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


# NO_IMAGE_GENERATION_WHEN_ATTACHMENT_PRESENT_LOCK: attachment analysis must not be hijacked by image generation.
if (not attachments) and (__name__ == "__main__"):
    print("Calculator app created.")
    print("2 + 3 =", add(2, 3))
""".strip() + "\n",
                        encoding="utf-8",
                    )

                    step["result"] = f"Created file: {target_file}"

                    step["error"] = None

                elif (
                    step_action
                    in {
                        "test",
                        "run",
                        "execute",
                    }
                    and target_file
                    and hasattr(self, "python_runner")
                ):

                    python_result = self.python_runner.run_file(target_file)

                    step["result"] = (
                        python_result.get("stdout")
                        or python_result.get("stderr")
                        or python_result.get("error")
                        or "python executed"
                    )

                    step["error"] = None if python_result.get("ok") else step["result"]

                else:

                    step["result"] = "step executed"

                    step["error"] = None

                execution_state = (
                    self.execution_mutation_service.append_history(
                        execution_state,
                        f"completed: {step_title}",
                    )
                )
                execution_state["current_index"] = current_index + 1

                execution_state["progress"] = current_index + 1

                outputs.append(f"Completed step: {step_title}")

                if execution_state["current_index"] >= len(steps):
                    execution_state = (
                        self.execution_mutation_service.mark_complete(
                            execution_state,
                        )
                    )
                    break

            self._save_active_execution(
                session_id,
                execution_state,
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": "\n".join(outputs),
                },
                "execution": execution_state,
            }

        # =========================
        # RETRY FAILED
        # =========================
        if command == "retry_failed":

            execution_state["failure_count"] = (
                int(execution_state.get("failure_count") or 0) + 1
            )

            failed_index = None

            for idx, step in enumerate(steps):
                if step.get("status") == "failed":
                    failed_index = idx
                    break

            if failed_index is None:
                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": "No failed execution step found to retry.",
                    },
                    "execution": execution_state,
                }

            execution_state["current_index"] = failed_index

            failure_count = int(execution_state.get("failure_count") or 0)

            if failure_count == 1:
                execution_state["retry_strategy"] = "retry_step"

            elif failure_count == 2:
                execution_state["retry_strategy"] = "retry_with_smaller_scope"

            elif failure_count == 3:
                execution_state["retry_strategy"] = "retry_with_file_scope"

            else:
                execution_state["retry_strategy"] = "change_strategy"

            self._save_execution_state(
                session_id,
                execution_state,
            )

            return self._process_execution_command(
                command="run_step",
                session_id=session_id,
                execution_state=execution_state,
            )

        # =========================
        # CANCEL
        # =========================
        if command == "cancel":

            execution_state = (
                self.execution_mutation_service.cancel(
                    execution_state,
                )
            )
            self._save_execution_state(
                session_id,
                execution_state,
            )

            self._save_execution_state(
                session_id,
                {},
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": "Execution cancelled.",
                },
                "execution": execution_state,
            }


        return {
            "ok": False,
            "assistant_message": {
                "role": "assistant",
                "text": (f"Unknown execution command: " f"{command}"),
            },
            "execution": execution_state,
        }



    def execute_step_logic(self, session_id, step):
        try:
            step["status"] = "running"

            step_action = self._safe_str(step.get("action")).lower()

            print(
                "STEP ACTION =",
                repr(step_action),
            )

            target_file = self._safe_str(step.get("target_file"))

            python_result = None

            if step_action == "implement" and target_file:

                Path(target_file).parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                Path(target_file).write_text(
                    """
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


if __name__ == "__main__":
    print("Calculator app created.")
    print("2 + 3 =", add(2, 3))
""".strip() + "\n",
                    encoding="utf-8",
                )

                step["result"] = f"Created file: {target_file}"

                step["error"] = None

            elif (
                step_action
                in {
                    "test",
                    "run",
                    "execute",
                }
                and target_file
                and hasattr(self, "python_runner")
            ):

                python_result = self.python_runner.run_file(target_file)

                result = (
                    f"STDOUT="
                    f"{python_result.get('stdout')} | "
                    f"STDERR="
                    f"{python_result.get('stderr')} | "
                    f"ERROR="
                    f"{python_result.get('error')}"
                )

                step["result"] = result

                step["error"] = None if python_result.get("ok") else result

            else:

                step["result"] = "step executed"

                step["error"] = None

            step["status"] = "completed"

        except Exception as e:
            step["status"] = "failed"
            step["error"] = str(e)