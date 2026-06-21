class RuntimeAutonomyLoop:

    name = "runtime_autonomy_loop"

    tags = [
        "runtime",
        "autonomy",
        "loop",
    ]

    def run(
        self,
        scheduler_report=None,
        runtime_signal=None,
    ):

        scheduler_report = (
            scheduler_report
            if isinstance(scheduler_report, dict)
            else {}
        )

        runtime_signal = str(
            runtime_signal
            or ""
        ).lower()

        queue = (
            scheduler_report.get(
                "queue",
                []
            )
            if isinstance(
                scheduler_report.get(
                    "queue"
                ),
                list,
            )
            else []
        )

        executed = []

        for item in queue:

            executed.append(
                {
                    "queue_index": (
                        item.get(
                            "queue_index"
                        )
                    ),
                    "step": (
                        item.get("step")
                    ),
                    "status": "autonomous_ready",
                }
            )

        autonomy_mode = "observe"

        if runtime_signal in {
            "runtime_escalation_required",
            "runtime_integrity_block",
        }:

            autonomy_mode = (
                "recovery_autonomy"
            )

        elif queue:

            autonomy_mode = (
                "active_execution"
            )

        return {
            "ok": True,
            "autonomy_mode": autonomy_mode,
            "executed": executed,
            "execution_count": len(executed),
        }

