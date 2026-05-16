class RuntimeRollbackEngine:

    def decide(
        self,
        mutation_report=None,
        checkpoint_report=None,
        runtime_result=None,
    ):

        mutation_report = (
            mutation_report
            if isinstance(mutation_report, dict)
            else {}
        )

        checkpoint_report = (
            checkpoint_report
            if isinstance(checkpoint_report, dict)
            else {}
        )

        runtime_result = (
            runtime_result
            if isinstance(runtime_result, dict)
            else {}
        )

        blocked = bool(
            mutation_report.get(
                "blocked",
                False,
            )
        )

        checkpoint = (
            checkpoint_report.get(
                "checkpoint",
                {}
            )
            if isinstance(checkpoint_report, dict)
            else {}
        )

        should_rollback = False
        reason = None

        if blocked and checkpoint:

            should_rollback = True
            reason = (
                "Mutation sandbox blocked runtime change."
            )

        return {
            "ok": True,
            "should_rollback": should_rollback,
            "reason": reason,
            "checkpoint_id": (
                checkpoint.get(
                    "checkpoint_id"
                )
            ),
            "restore_state": (
                checkpoint.get(
                    "execution_state",
                    {},
                )
                if should_rollback
                else {}
            ),
        }