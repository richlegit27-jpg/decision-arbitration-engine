class RuntimePlanningService:
    def __init__(self):
        self.plan_state = {
            "active_plan": [],
            "plan_history": [],
            "planning_mode": "adaptive",
        }

    def build_plan(
        self,
        runtime_goal=None,
        runtime_identity=None,
        trend=None,
    ):
        runtime_goal = self._safe_dict(
            runtime_goal
        )

        runtime_identity = self._safe_dict(
            runtime_identity
        )

        trend = self._safe_dict(trend)

        goal_state = self._safe_dict(
            runtime_goal.get("goal_state")
        )

        identity_state = self._safe_dict(
            runtime_identity.get(
                "identity_state"
            )
        )

        current_goal = str(
            goal_state.get(
                "current_goal",
                ""
            )
        ).lower()

        runtime_identity_name = str(
            identity_state.get(
                "runtime_identity",
                ""
            )
        ).lower()

        instability_ratio = (
            self._safe_float(
                trend.get(
                    "instability_ratio"
                ),
                0.0,
            )
        )

        plan = []

        if (
            current_goal
            == "stabilize_runtime"
        ):
            plan.extend(
                [
                    "reduce_retry_pressure",
                    "suppress_mutation",
                    "preserve_stable_graphs",
                    "transition_to_stable_execution",
                ]
            )

        elif (
            current_goal
            == "restore_safe_execution"
        ):
            plan.extend(
                [
                    "preserve_successful_steps",
                    "avoid_regression",
                    "stabilize_execution_flow",
                ]
            )

        if (
            runtime_identity_name
            == "cooldown_runtime"
        ):
            plan.insert(
                0,
                "enter_cooldown_barrier",
            )

        if instability_ratio >= 0.80:
            plan.append(
                "emergency_stabilization"
            )

        self.plan_state[
            "active_plan"
        ] = plan

        self.plan_state[
            "planning_mode"
        ] = (
            "stabilization"
            if instability_ratio >= 0.70
            else "adaptive"
        )

        self.plan_state[
            "plan_history"
        ].append(
            {
                "goal": current_goal,
                "plan": list(plan),
            }
        )

        self.plan_state[
            "plan_history"
        ] = (
            self.plan_state[
                "plan_history"
            ][-25:]
        )

        return {
            "ok": True,
            "plan_state": (
                self.plan_state
            ),
        }

    def get_plan(
        self,
    ):
        return self.plan_state

    def _safe_dict(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def _safe_float(
        self,
        value,
        default=0.0,
    ):
        try:
            return float(value)
        except Exception:
            return default

