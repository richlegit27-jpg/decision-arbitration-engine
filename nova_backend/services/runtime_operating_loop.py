class RuntimeOperatingLoop:

    name = "runtime_operating_loop"

    tags = [
        "runtime",
        "operating",
        "loop",
    ]

    def cycle(
        self,
        collective_report=None,
        runtime_signal=None,
    ):

        collective_report = (
            collective_report
            if isinstance(collective_report, dict)
            else {}
        )

        runtime_signal = str(
            runtime_signal
            or ""
        ).lower()

        consensus = (
            collective_report.get(
                "consensus",
                []
            )
            if isinstance(
                collective_report.get(
                    "consensus"
                ),
                list,
            )
            else []
        )

        loop_state = []

        for item in consensus:

            loop_state.append(
                {
                    "agent_id": (
                        item.get(
                            "agent_id"
                        )
                    ),
                    "state": (
                        "continuous_operation"
                    ),
                    "decision": (
                        item.get(
                            "decision"
                        )
                    ),
                }
            )

        operating_mode = (
            "continuous_runtime"
        )

        if runtime_signal in {
            "runtime_integrity_block",
            "runtime_escalation_required",
        }:

            operating_mode = (
                "recovery_runtime"
            )

        return {
            "ok": True,
            "operating_mode": (
                operating_mode
            ),
            "loop_count": len(
                loop_state
            ),
            "loop_state": loop_state,
        }