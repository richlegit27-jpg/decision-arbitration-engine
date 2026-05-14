class RuntimeAutonomousExecutor:

    name = "runtime_autonomous_executor"

    tags = [
        "runtime",
        "autonomy",
        "execution",
        "executor",
    ]

    def execute(
        self,
        execution_state=None,
        runtime_execution_queue=None,
    ):

        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        runtime_execution_queue = (
            runtime_execution_queue
            if isinstance(runtime_execution_queue, dict)
            else {}
        )

        queue = runtime_execution_queue.get(
            "queue",
            execution_state.get(
                "runtime_execution_queue",
                [],
            ),
        )

        if not isinstance(queue, list):
            queue = []

        executed_actions = []
        blocked_actions = []

        auto_execute_allowed = bool(
            execution_state.get(
                "runtime_auto_execute_allowed",
                True,
            )
        )

        safety_lock = bool(
            execution_state.get(
                "runtime_safety_lock",
                False,
            )
        )

        if safety_lock:

            return {
                "ok": True,
                "executed": False,
                "reason": "Runtime safety lock is active.",
                "executed_actions": executed_actions,
                "blocked_actions": queue,
                "execution_state": execution_state,
            }

        if not auto_execute_allowed:

            return {
                "ok": True,
                "executed": False,
                "reason": "Runtime auto execution is disabled.",
                "executed_actions": executed_actions,
                "blocked_actions": queue,
                "execution_state": execution_state,
            }

        remaining_queue = []

        for item in queue:

            if not isinstance(item, dict):
                continue

            action = str(
                item.get(
                    "action",
                    "",
                )
            ).lower()

            if action == "retry_failed":

                execution_state["runtime_last_autonomous_action"] = (
                    "retry_failed"
                )
                execution_state["runtime_autonomous_retry_requested"] = True
                execution_state["runtime_signal"] = (
                    "runtime_autonomous_retry"
                )

                executed_actions.append(item)

            elif action == "pause":

                execution_state["runtime_last_autonomous_action"] = "pause"
                execution_state["runtime_autonomous_pause_requested"] = True
                execution_state["runtime_signal"] = (
                    "runtime_autonomous_pause"
                )

                executed_actions.append(item)

            elif action == "repair_step":

                execution_state["runtime_last_autonomous_action"] = (
                    "repair_step"
                )
                execution_state["runtime_repair_requested"] = True
                execution_state["runtime_signal"] = (
                    "runtime_autonomous_repair_step"
                )
                execution_state["recovery_mode"] = True

                executed_actions.append(item)

            elif action == "rollback_runtime":

                execution_state["runtime_last_autonomous_action"] = (
                    "rollback_runtime"
                )
                execution_state["runtime_rollback_requested"] = True
                execution_state["runtime_signal"] = (
                    "runtime_autonomous_rollback"
                )
                execution_state["recovery_mode"] = True

                executed_actions.append(item)

            elif action == "mutate_strategy":

                execution_state["runtime_last_autonomous_action"] = (
                    "mutate_strategy"
                )
                execution_state["runtime_strategy_mutation_requested"] = True
                execution_state["runtime_signal"] = (
                    "runtime_autonomous_strategy_mutation"
                )

                executed_actions.append(item)

            elif action == "isolate_failure":

                execution_state["runtime_last_autonomous_action"] = (
                    "isolate_failure"
                )
                execution_state["runtime_failure_isolation_requested"] = True
                execution_state["runtime_signal"] = (
                    "runtime_autonomous_failure_isolation"
                )
                execution_state["recovery_mode"] = True

                executed_actions.append(item)

            elif action == "checkpoint_runtime":

                execution_state["runtime_last_autonomous_action"] = (
                    "checkpoint_runtime"
                )
                execution_state["runtime_checkpoint_requested"] = True
                execution_state["runtime_signal"] = (
                    "runtime_autonomous_checkpoint"
                )

                executed_actions.append(item)

            elif action == "escalate_supervision":

                execution_state["runtime_last_autonomous_action"] = (
                    "escalate_supervision"
                )
                execution_state["runtime_supervision_escalated"] = True
                execution_state["runtime_signal"] = (
                    "runtime_autonomous_supervision_escalation"
                )

                executed_actions.append(item)

            elif action == "reroute_execution":

                execution_state["runtime_last_autonomous_action"] = (
                    "reroute_execution"
                )
                execution_state["runtime_reroute_requested"] = True
                execution_state["runtime_signal"] = (
                    "runtime_autonomous_reroute_execution"
                )

                executed_actions.append(item)

            elif action == "rebuild_plan":

                execution_state["runtime_last_autonomous_action"] = (
                    "rebuild_plan"
                )
                execution_state["runtime_plan_rebuild_requested"] = True
                execution_state["runtime_signal"] = (
                    "runtime_autonomous_rebuild_plan"
                )

                executed_actions.append(item)

            else:

                blocked_actions.append(item)
                remaining_queue.append(item)

        execution_state["runtime_execution_queue"] = remaining_queue[-25:]

        return {
            "ok": True,
            "executed": bool(executed_actions),
            "reason": (
                "Runtime autonomous executor processed queue."
                if executed_actions
                else "No executable autonomous actions were queued."
            ),
            "executed_actions": executed_actions,
            "blocked_actions": blocked_actions,
            "remaining_queue": remaining_queue,
            "execution_state": execution_state,
        }