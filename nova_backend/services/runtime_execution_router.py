class RuntimeExecutionRouter:

    name = "runtime_execution_router"

    tags = [
        "runtime",
        "execution",
        "router",
    ]

    def route(
        self,
        scheduler_report=None,
        autonomy_report=None,
        supervision_report=None,
        operating_report=None,
        runtime_signal=None,
    ):

        scheduler_report = (
            scheduler_report
            if isinstance(scheduler_report, dict)
            else {}
        )

        autonomy_report = (
            autonomy_report
            if isinstance(autonomy_report, dict)
            else {}
        )

        supervision_report = (
            supervision_report
            if isinstance(supervision_report, dict)
            else {}
        )

        operating_report = (
            operating_report
            if isinstance(operating_report, dict)
            else {}
        )

        runtime_signal = str(
            runtime_signal
            or ""
        ).lower()

        route = "observe_only"
        priority = "low"
        execute_now = False

        scheduler_mode = str(
            scheduler_report.get(
                "scheduler_mode",
                "",
            )
        ).lower()

        autonomy_mode = str(
            autonomy_report.get(
                "autonomy_mode",
                "",
            )
        ).lower()

        supervision_mode = str(
            supervision_report.get(
                "supervision_mode",
                "",
            )
        ).lower()

        operating_mode = str(
            operating_report.get(
                "operating_mode",
                "",
            )
        ).lower()

        if runtime_signal in {
            "runtime_integrity_block",
            "runtime_rollback_executed",
            "runtime_escalation_required",
        }:

            route = "recovery_execution"
            priority = "critical"
            execute_now = True

        elif (
            scheduler_mode == "priority_recovery"
            or autonomy_mode == "recovery_autonomy"
            or supervision_mode == "critical_supervision"
            or operating_mode == "recovery_runtime"
        ):

            route = "guarded_recovery_execution"
            priority = "high"
            execute_now = True

        elif autonomy_mode == "active_execution":

            route = "normal_autonomous_execution"
            priority = "medium"
            execute_now = True

        return {
            "ok": True,
            "route": route,
            "priority": priority,
            "execute_now": execute_now,
            "runtime_signal": runtime_signal,
            "scheduler_mode": scheduler_mode,
            "autonomy_mode": autonomy_mode,
            "supervision_mode": supervision_mode,
            "operating_mode": operating_mode,
        }