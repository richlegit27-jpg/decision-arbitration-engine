class RuntimeMutationSandbox:

    def evaluate(
        self,
        before_state=None,
        after_state=None,
        mutation_reason=None,
    ):

        before_state = (
            before_state
            if isinstance(before_state, dict)
            else {}
        )

        after_state = (
            after_state
            if isinstance(after_state, dict)
            else {}
        )

        mutation_reason = str(
            mutation_reason
            or ""
        )

        issues = []
        severity = 0

        before_signal = str(
            before_state.get(
                "runtime_signal",
                "",
            )
        ).lower()

        after_signal = str(
            after_state.get(
                "runtime_signal",
                "",
            )
        ).lower()

        before_recovery = bool(
            before_state.get(
                "recovery_mode",
                False,
            )
        )

        after_recovery = bool(
            after_state.get(
                "recovery_mode",
                False,
            )
        )

        if (
            before_signal
            != after_signal
            and after_signal
            in {
                "runtime_integrity_block",
                "runtime_contradiction_detected",
                "runtime_escalation_required",
            }
        ):

            issues.append(
                "Mutation introduced high-risk runtime signal."
            )

            severity += 3

        if (
            not before_recovery
            and after_recovery
            and "recovery" not in mutation_reason.lower()
        ):

            issues.append(
                "Mutation activated recovery mode without recovery reason."
            )

            severity += 2

        blocked = severity >= 3

        return {
            "ok": True,
            "blocked": blocked,
            "severity": severity,
            "issues": issues,
            "before_signal": before_signal,
            "after_signal": after_signal,
            "before_recovery": before_recovery,
            "after_recovery": after_recovery,
            "mutation_reason": mutation_reason,
        }

