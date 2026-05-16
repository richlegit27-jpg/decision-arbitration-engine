class RuntimeSubgoalEngine:

    def generate(
        self,
        runtime_goal=None,
        runtime_prediction=None,
        runtime_signal=None,
    ):

        runtime_goal = (
            runtime_goal
            if isinstance(runtime_goal, dict)
            else {}
        )

        runtime_prediction = (
            runtime_prediction
            if isinstance(runtime_prediction, dict)
            else {}
        )

        runtime_signal = str(
            runtime_signal
            or ""
        ).lower()

        subgoals = []

        active_goal = str(
            runtime_goal.get(
                "active_goal",
                "stabilize_runtime",
            )
        )

        prediction = (
            runtime_prediction.get(
                "prediction",
                {},
            )
            if isinstance(runtime_prediction, dict)
            else {}
        )

        risk_level = str(
            prediction.get(
                "risk_level",
                "low",
            )
        ).lower()

        if (
            risk_level
            in {
                "high",
                "critical",
            }
        ):

            subgoals.append(
                {
                    "goal": (
                        "reduce_runtime_risk"
                    ),
                    "priority": "high",
                }
            )

        if (
            runtime_signal
            == "runtime_integrity_block"
        ):

            subgoals.append(
                {
                    "goal": (
                        "repair_integrity_layer"
                    ),
                    "priority": "critical",
                }
            )

        if (
            runtime_signal
            == "runtime_rollback_executed"
        ):

            subgoals.append(
                {
                    "goal": (
                        "stabilize_after_rollback"
                    ),
                    "priority": "high",
                }
            )

        subgoals.append(
            {
                "goal": active_goal,
                "priority": "persistent",
            }
        )

        return {
            "ok": True,
            "subgoals": subgoals,
        }