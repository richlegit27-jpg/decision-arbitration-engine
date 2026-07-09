class RuntimeExecutionQueueService:

    name = "runtime_execution_queue_service"

    tags = [
        "runtime",
        "execution",
        "queue",
        "autonomy",
    ]

    def apply(
        self,
        execution_state=None,
    ):

        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        runtime_action = str(
            execution_state.get(
                "runtime_execution_action",
                "",
            )
        ).lower()

        queue = execution_state.get(
            "runtime_execution_queue",
            [],
        )

        if not isinstance(queue, list):
            queue = []

        queued = False

        if runtime_action == "runtime_execute_now":

            queue.append(
                {
                    "action": "retry_failed",
                    "priority": execution_state.get(
                        "runtime_execution_priority",
                        "medium",
                    ),
                    "source": "runtime_autonomy",
                }
            )

            queued = True

        execution_state["runtime_execution_queue"] = (
            queue[-25:]
        )

        return {
            "ok": True,
            "queued": queued,
            "queue_size": len(queue),
            "execution_state": execution_state,
            "queue": queue[-25:],
        }

    def build_autonomous_queue(
        self,
        execution_state=None,
        runtime_governor=None,
        reflection=None,
        runtime_policy_learning=None,
    ):

        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        runtime_governor = (
            runtime_governor
            if isinstance(runtime_governor, dict)
            else {}
        )

        reflection = (
            reflection
            if isinstance(reflection, dict)
            else {}
        )

        runtime_policy_learning = (
            runtime_policy_learning
            if isinstance(
                runtime_policy_learning,
                dict,
            )
            else {}
        )

        action_stats = (
            runtime_policy_learning.get(
                "action_stats",
                {},
            )
        )

        if not isinstance(action_stats, dict):
            action_stats = {}

        steps = execution_state.get(
            "steps",
            [],
        )

        if not isinstance(steps, list):
            steps = []

        failed_steps = [
            step
            for step in steps
            if (
                isinstance(step, dict)
                and str(
                    step.get(
                        "status",
                        "",
                    )
                ).lower()
                in {
                    "failed",
                    "error",
                }
            )
        ]

        completed_steps = [
            step
            for step in steps
            if (
                isinstance(step, dict)
                and str(
                    step.get(
                        "status",
                        "",
                    )
                ).lower()
                in {
                    "complete",
                    "completed",
                    "done",
                }
            )
        ]

        failed_count = len(failed_steps)
        completed_count = len(completed_steps)

        runtime_signal = str(
            execution_state.get(
                "runtime_signal",
                reflection.get(
                    "signal",
                    "",
                ),
            )
            or ""
        ).lower()

        queue = []

        if failed_count >= 1:

            queue.append(
                {
                    "action": "isolate_failure",
                    "priority": "high",
                    "source": "runtime_failure_detection",
                    "reason": "Failed runtime step detected.",
                    "failed_count": failed_count,
                }
            )

            queue.append(
                {
                    "action": "repair_step",
                    "priority": (
                        "critical"
                        if action_stats.get(
                            "repair_step",
                            {},
                        ).get(
                            "confidence",
                            0.0,
                        ) >= 0.70
                        else "high"
                    ),
                    "source": "runtime_failure_detection",
                    "reason": "Autonomous repair requested.",
                    "failed_count": failed_count,
                }
            )

        if failed_count >= 2:

            queue.append(
                {
                    "action": "rollback_runtime",
                    "priority": "critical",
                    "source": "runtime_failure_detection",
                    "reason": "Repeated failures triggered rollback.",
                    "failed_count": failed_count,
                }
            )

            queue.append(
                {
                    "action": "escalate_supervision",
                    "priority": "critical",
                    "source": "runtime_failure_detection",
                    "reason": "Supervisor escalation triggered.",
                    "failed_count": failed_count,
                }
            )

        if (
            completed_count >= 2
            and failed_count == 0
        ):

            queue.append(
                {
                    "action": "checkpoint_runtime",
                    "priority": (
                        "high"
                        if action_stats.get(
                            "checkpoint_runtime",
                            {},
                        ).get(
                            "confidence",
                            0.0,
                        ) >= 0.70
                        else "medium"
                    ),
                    "source": "runtime_success_detection",
                    "reason": "Stable runtime checkpoint requested.",
                    "completed_count": completed_count,
                }
            )

        if runtime_signal in {
            "runtime_anomaly_detected",
            "runtime_escalation_required",
        }:

            queue.append(
                {
                    "action": "mutate_strategy",
                    "priority": "high",
                    "source": "runtime_signal_detection",
                    "reason": "Runtime signal requested strategy mutation.",
                    "runtime_signal": runtime_signal,
                }
            )

            queue.append(
                {
                    "action": "reroute_execution",
                    "priority": "high",
                    "source": "runtime_signal_detection",
                    "reason": "Runtime signal requested execution reroute.",
                    "runtime_signal": runtime_signal,
                }
            )

        if runtime_signal == "runtime_stabilized_success":

            queue.append(
                {
                    "action": "checkpoint_runtime",
                    "priority": (
                        "high"
                        if action_stats.get(
                            "checkpoint_runtime",
                            {},
                        ).get(
                            "confidence",
                            0.0,
                        ) >= 0.70
                        else "medium"
                    ),
                    "source": "runtime_signal_detection",
                    "reason": "Runtime stabilized successfully.",
                    "runtime_signal": runtime_signal,
                }
            )

        execution_state["runtime_execution_queue"] = (
            queue[-25:]
        )

        return {
            "ok": True,
            "queue": queue[-25:],
            "queue_size": len(queue[-25:]),
            "failed_count": failed_count,
            "completed_count": completed_count,
            "runtime_signal": runtime_signal,
            "execution_state": execution_state,
        }

