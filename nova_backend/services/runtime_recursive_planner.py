class RuntimeRecursivePlanner:

    def expand(
        self,
        selected_goal=None,
        runtime_signal=None,
    ):

        selected_goal = (
            selected_goal
            if isinstance(selected_goal, dict)
            else {}
        )

        runtime_signal = str(
            runtime_signal
            or ""
        ).lower()

        goal_name = str(
            selected_goal.get(
                "goal",
                "stabilize_runtime",
            )
        )

        steps = []

        if (
            goal_name
            == "reduce_runtime_risk"
        ):

            steps.extend(
                [
                    "analyze_failure_patterns",
                    "reduce_mutation_pressure",
                    "increase_runtime_observation",
                ]
            )

        elif (
            goal_name
            == "repair_integrity_layer"
        ):

            steps.extend(
                [
                    "inspect_integrity_layer",
                    "restore_safe_state",
                    "verify_runtime_consistency",
                ]
            )

        elif (
            goal_name
            == "stabilize_after_rollback"
        ):

            steps.extend(
                [
                    "verify_rollback_integrity",
                    "rebuild_runtime_state",
                    "resume_safe_execution",
                ]
            )

        else:

            steps.extend(
                [
                    "observe_runtime",
                    "preserve_runtime_state",
                ]
            )

        if (
            runtime_signal
            == "runtime_escalation_required"
        ):

            steps.insert(
                0,
                "activate_emergency_recovery",
            )

        return {
            "ok": True,
            "goal": goal_name,
            "step_count": len(steps),
            "steps": steps,
        }

