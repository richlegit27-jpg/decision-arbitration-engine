            step["status"] = "running"

                execution_state["steps"][current_index] = dict(step)

                execution_state = (
                    self.execution_mutation_service.mark_running(
                        execution_state,
                        step_index=current_index,
                        current_step=step.get("title") or "",
                        waiting=False,
                    )
                    if self.execution_mutation_service
                    and hasattr(
                        self.execution_mutation_service,
                        "mark_running",
                    )
                    else execution_state
                )

            self._save_execution_state(
                session_id,
                execution_state,
            )



            step["status"] = "running"

            execution_state = (
                self.execution_mutation_service.mark_running(
                    execution_state,
                    step_index=current_index,
                    current_step=step.get("title") or "",
                    waiting=False,
                )
            )

            print(
                "DEBUG BEFORE EXECUTE_STEP_LOGIC",
                {
                    "has_execution_step_service": self.execution_step_service is not None,
                    "step": step,
                },
                flush=True,
            )

            print(
                "DEBUG STEP BEFORE EXECUTE_STEP_LOGIC =",
                {
                    "title": step.get("title"),
                    "action": step.get("action"),
                    "target_file": step.get("target_file"),
                    "keys": list(step.keys()),
                    "full": step,
                },
                flush=True,
            )

            result = self.execution_step_service.execute_step_logic(
                session_id=session_id,
                step=step,
            )

            print(
                "DEBUG AFTER EXECUTE_STEP_LOGIC",
                result,
                flush=True,
            )

            step_status = self._safe_str(
                step.get("status")
            ).lower().strip()

            if step_status == "waiting_approval":
                approval_reason = self._safe_str(
                    step.get("error")
                    or (
                        "Approval required "
                        "before execution."
                    )
                )

                step_title = self._safe_str(
                    step.get("title")
                    or "current step"
                )

                execution_state["steps"][
                    current_index
                ] = dict(step)

                execution_state = (
                    self.execution_mutation_service.mark_waiting_approval(
                        execution_state,
                        step_index=current_index,
                        reason=approval_reason,
                    )
                )

                execution_state = (
                    self.execution_mutation_service.append_history(
                        execution_state,
                        (
                            "waiting approval: "
                            f"{step_title}"
                        ),
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
                        "text": (
                            "Approval required: "
                            f"{step_title}. "
                            f"{approval_reason}"
                        ),
                    },
                    "execution": execution_state,
                    "step_output": "",
                }

            if step_status in {
                "failed",
                "blocked",
            }:
                step_error = self._safe_str(
                    step.get("error")
                    or "Execution step failed."
                )
                step_title = self._safe_str(
                    step.get("title")
                    or "current step"
                )

                execution_state["steps"][
                    current_index
                ] = dict(step)

                execution_state = (
                    self.execution_mutation_service.mark_failed(
                        execution_state,
                        step_index=current_index,
                        error=step_error,
                    )
                )

                execution_state = (
                    self.execution_mutation_service.append_history(
                        execution_state,
                        f"failed: {step_title}: {step_error}",
                    )
                )

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            f"Step failed: {step_title}. "
                            f"{step_error}"
                        ),
                    },
                    "execution": execution_state,
                    "step_output": step.get(
                        "result",
                        "",
                    ),
                }

            step["status"] = "completed"

            if result:
                step["result"] = (
                    result.get("result")
                    if isinstance(result, dict)
                    else result
                )

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


            next_index = (
                execution_state[
                    "current_index"
                ]
            )

            if next_index >= len(steps):
                execution_state = (
                    self.execution_mutation_service.mark_complete(
                        execution_state
                    )
                )

            else:
                next_step = steps[next_index]

                next_step["status"] = "pending"

                execution_state["steps"][next_index] = dict(
                    next_step
                )

                execution_state["waiting"] = False
                execution_state[
                    "_execution_processing"
                ] = False

                execution_state[
                    "current_step"
                ] = dict(
                    next_step
                )

                execution_state[
                    "current_step_title"
                ] = (
                    next_step.get("title")
                    or ""
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

                print(
                    "DEBUG RUN_ALL STEP SENT TO EXECUTOR =",
                    {
                        "title": step.get("title"),
                        "action": step.get("action"),
                        "target_file": step.get("target_file"),
                        "content_length": len(
                            step.get("content") or ""
                        ),
                        "full_step": step,
                    },
                    flush=True,
                )

                result = self.execution_step_service.execute_step_logic(
                    session_id=session_id,
                    step=step,
                )

                step_status = self._safe_str(
                    step.get("status")
                ).lower().strip()

                if step_status == "waiting_approval":
                    approval_reason = self._safe_str(
                        step.get("error")
                        or (
                            "Approval required "
                            "before execution."
                        )
                    )

                    step_title = self._safe_str(
                        step.get("title")
                        or "current step"
                    )

                    execution_state["steps"][
                        current_index
                    ] = dict(step)

                    execution_state = (
                        self.execution_mutation_service.mark_waiting_approval(
                            execution_state,
                            step_index=current_index,
                            reason=approval_reason,
                        )
                    )

                    execution_state = (
                        self.execution_mutation_service.append_history(
                            execution_state,
                            (
                                "waiting approval: "
                                f"{step_title}"
                            ),
                        )
                    )

                    self._save_active_execution(
                        session_id,
                        execution_state,
                    )

                    return {
                        "ok": True,
                        "assistant_message": {
                            "role": "assistant",
                            "text": (
                                "Approval required: "
                                f"{step_title}. "
                                f"{approval_reason}"
                            ),
                        },
                        "execution": execution_state,
                        "step_output": "",
                    }

                if step_status in {
                    "failed",
                    "blocked",
                }:
                    step_error = self._safe_str(
                        step.get("error")
                        or "Execution step failed."
                    )

                    step_title = self._safe_str(
                        step.get("title")
                        or "current step"
                    )

                    execution_state["steps"][
                        current_index
                    ] = dict(step)

                    execution_state = (
                        self.execution_mutation_service.mark_failed(
                            execution_state,
                            step_index=current_index,
                            error=step_error,
                        )
                    )

                    execution_state = (
                        self.execution_mutation_service.append_history(
                            execution_state,
                            (
                                f"failed: {step_title}: "
                                f"{step_error}"
                            ),
                        )
                    )

                    self._save_active_execution(
                        session_id,
                        execution_state,
                    )

                    return {
                        "ok": False,
                        "assistant_message": {
                            "role": "assistant",
                            "text": (
                                f"Step failed: {step_title}. "
                                f"{step_error}"
                            ),
                        },
                        "execution": execution_state,
                        "step_output": step.get(
                            "result",
                            "",
                        ),
                    }

                if result:
                    step["result"] = result

                execution_state["steps"][current_index] = dict(step)

                steps = execution_state["steps"]

                step_title = self._safe_str(step.get("title"))

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
        # CANCEL
        # =========================

        if command == "cancel":
            execution_state = (
                self.execution_mutation_service.cancel(
                    execution_state
                )
            )

            execution_state = (
                self.execution_mutation_service.reset(
                    execution_state
                )
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

            try:
                from nova_backend.services.chat_execution_service import (
                    chat_execution_service,
                )

                if hasattr(
                    chat_execution_service,
                    "cancel",
                ):
                    execution_state = (
                        chat_execution_service.cancel(
                            session_id
                        )
                    )

                else:
                    chat_execution_service.reset(
                        session_id
                    )

            except Exception as legacy_reset_error:
                print(
                    "LEGACY EXECUTION RESET FAILED:",
                    legacy_reset_error,
                )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": "Execution cancelled.",
                },
                "execution": execution_state,
                "execution_state": execution_state,
            }

        # =========================
        # RETRY FAILED
        # =========================
        if command == "retry_failed":
            (
                execution_state,
                failed_index,
            ) = (
                self.execution_mutation_service.prepare_failed_retry(
                    execution_state,
                )
            )

            if failed_index is None:
                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": "No failed execution step found to retry.",
                    },
                    "execution": execution_state,
                }

            self._save_execution_state(
                session_id,
                execution_state,
            )

            return self._process_execution_command(
                command="run_step",
                session_id=session_id,
                execution_state=execution_state,
            )



