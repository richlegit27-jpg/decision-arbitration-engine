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

        steps = execution_plan.get(
            "steps",
            [],
        )

        if not isinstance(steps, list):
            steps = []

        scheduler_mode = "normal"
        priority = "medium"

        if runtime_signal in {
            "runtime_integrity_block",
            "runtime_rollback_executed",
            "runtime_escalation_required",
        }:

            scheduler_mode = "priority_recovery"
            priority = "critical"

        elif runtime_signal in {
            "runtime_requested_failure_inspection",
            "runtime_anomaly_detected",
        }:

            scheduler_mode = "normal"
            priority = "high"

        return {
            "ok": True,
            "scheduler_mode": scheduler_mode,
            "priority": priority,
            "scheduled_steps": steps,
            "runtime_signal": runtime_signal,
        }

    def run(
        self,
        context=None,
        **kwargs,
    ):

        context = (
            context
            if isinstance(context, dict)
            else {}
        )

        execution_plan = (
            kwargs.get("execution_plan")
            or context.get("execution_plan")
            or context.get("plan")
            or {}
        )

        runtime_signal = (
            kwargs.get("runtime_signal")
            or context.get("runtime_signal")
            or ""
        )

        return self.schedule(
            execution_plan=execution_plan,
            runtime_signal=runtime_signal,
        )

