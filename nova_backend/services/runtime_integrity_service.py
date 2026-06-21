class RuntimeIntegrityService:

    def validate(
        self,
        execution_state=None,
        runtime_result=None,
        runtime_history=None,
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

        runtime_history = (
            runtime_history
            if isinstance(runtime_history, list)
            else []
        )

        issues = []
        severity = 0

        runtime_signal = str(
            execution_state.get(
                "runtime_signal",
                "",
            )
        ).lower()

        recovery_mode = bool(
            execution_state.get(
                "recovery_mode",
                False,
            )
        )

        final_action = str(
            runtime_result.get(
                "final_action",
                "",
            )
        ).lower()

        if (
            recovery_mode
            and "stabilize" in final_action
        ):

            issues.append(
                "Recovery mode conflicts with stabilize action."
            )

            severity += 2

        if (
            runtime_signal
            == "runtime_integrity_block"
            and not recovery_mode
        ):

            issues.append(
                "Integrity block detected without recovery mode."
            )

            severity += 3

        repeated_actions = [
            str(
                item.get(
                    "final_action",
                    "",
                )
            ).lower()
            for item in runtime_history[-5:]
            if isinstance(item, dict)
        ]

        if (
            len(repeated_actions) >= 5
            and len(set(repeated_actions)) == 1
        ):

            issues.append(
                "Repeated identical runtime actions detected."
            )

            severity += 2

        blocked = severity >= 3

        return {
            "ok": True,
            "blocked": blocked,
            "severity": severity,
            "issues": issues,
            "checked_signal": runtime_signal,
            "checked_action": final_action,
        }

