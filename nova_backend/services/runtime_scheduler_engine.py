class RuntimeSchedulerEngine:

    name = "runtime_scheduler_engine"

    tags = [
        "runtime",
        "scheduler",
        "planning",
    ]

    def schedule(
        self,
        execution_plan=None,
        runtime_signal=None,
    ):

        execution_plan = (
            execution_plan
            if isinstance(execution_plan, dict)
            else {}
        )

        runtime_signal = str(
            runtime_signal
            or ""
        ).lower()

        executed_steps = (
            execution_plan.get(
                "executed_steps",
                []
            )
            if isinstance(
                execution_plan.get(
                    "executed_steps"
                ),
                list,
            )
            else []
        )

        queue = []

        for index, step in enumerate(
            executed_steps
        ):

            queue.append(
                {
                    "queue_index": index,
                    "step": step.get(
                        "step"
                    ),
                    "status": "queued",
                }
            )

        scheduler_mode = "normal"

        if runtime_signal in {
            "runtime_integrity_block",
            "runtime_rollback_executed",
            "runtime_escalation_required",
        }:

            scheduler_mode = (
                "priority_recovery"
            )

        return {
            "ok": True,
            "scheduler_mode": scheduler_mode,
            "queue": queue,
            "queue_size": len(queue),
        }