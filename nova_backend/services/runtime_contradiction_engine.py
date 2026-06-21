class RuntimeContradictionEngine:

    def analyze(
        self,
        execution_state=None,
        runtime_result=None,
        healing_report=None,
        governor_policy=None,
    ):

        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        runtime_result = (
            runtime_result
            if isinstance(runtime_result, dict)
            else {}
        )

        healing_report = (
            healing_report
            if isinstance(healing_report, dict)
            else {}
        )

        governor_policy = (
            governor_policy
            if isinstance(governor_policy, dict)
            else {}
        )

        contradictions = []
        severity = 0

        runtime_signal = str(
            execution_state.get(
                "runtime_signal",
                "",
            )
        ).lower()

        final_action = str(
            runtime_result.get(
                "final_action",
                "",
            )
        ).lower()

        healing_mode = str(
            healing_report.get(
                "healing_mode",
                "",
            )
        ).lower()

        governor_mode = str(
            governor_policy.get(
                "mode",
                "",
            )
        ).lower()

        recovery_mode = bool(
            execution_state.get(
                "recovery_mode",
                False,
            )
        )

        if (
            "repair" in final_action
            and "stabilize" in final_action
        ):

            contradictions.append(
                "Repair and stabilize actions collided."
            )

            severity += 2

        if (
            runtime_signal
            == "runtime_stabilized_success"
            and healing_mode == "repair_only"
        ):

            contradictions.append(
                "Runtime stabilized while healing remained repair_only."
            )

            severity += 3

        if (
            governor_mode == "repair_only"
            and "mutation" in final_action
        ):

            contradictions.append(
                "Governor blocked mutation while mutation action executed."
            )

            severity += 2

        if (
            recovery_mode
            and runtime_signal
            == "runtime_stabilized_success"
        ):

            contradictions.append(
                "Recovery mode active during stabilized success state."
            )

            severity += 2

        if (
            runtime_signal
            == "runtime_integrity_block"
            and "preserve" in final_action
        ):

            contradictions.append(
                "Integrity block collided with preserve action."
            )

            severity += 3

        blocked = severity >= 3

        return {
            "ok": True,
            "blocked": blocked,
            "severity": severity,
            "contradictions": contradictions,
            "runtime_signal": runtime_signal,
            "final_action": final_action,
            "healing_mode": healing_mode,
            "governor_mode": governor_mode,
            "recovery_mode": recovery_mode,
        }

