class RuntimeGoalArbitrationEngine:

    def prioritize(
        self,
        subgoals=None,
        runtime_signal=None,
    ):

        subgoals = (
            subgoals
            if isinstance(subgoals, list)
            else []
        )

        runtime_signal = str(
            runtime_signal
            or ""
        ).lower()

        ordered = sorted(
            subgoals,
            key=lambda item: (
                self._priority_score(
                    item.get(
                        "priority"
                    )
                )
            ),
            reverse=True,
        )

        selected = (
            ordered[0]
            if ordered
            else {}
        )

        escalation = False

        if runtime_signal in {
            "runtime_integrity_block",
            "runtime_rollback_executed",
            "runtime_escalation_required",
        }:

            escalation = True

        return {
            "ok": True,
            "selected_goal": selected,
            "goal_count": len(ordered),
            "escalation": escalation,
            "ordered_goals": ordered,
        }

    def _priority_score(
        self,
        priority,
    ):

        priority = str(
            priority
            or ""
        ).lower()

        mapping = {
            "critical": 100,
            "high": 75,
            "persistent": 50,
            "medium": 25,
            "low": 10,
        }

        return mapping.get(
            priority,
            0,
        )