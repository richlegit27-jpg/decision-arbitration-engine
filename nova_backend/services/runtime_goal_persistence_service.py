class RuntimeGoalPersistenceService:
    def __init__(self):
        self.goal_state = {
            "current_goal": "maintain_runtime_stability",
            "sub_goal": "observe_runtime_pressure",
            "priority": "medium",
            "goal_age": 0,
            "goal_progress": 0.0,
            "goal_status": "active",
            "goal_history": [],
        }

    def evolve_goal(
        self,
        runtime_identity=None,
        runtime_governor=None,
        trend=None,
    ):
        runtime_identity = self._safe_dict(runtime_identity)
        runtime_governor = self._safe_dict(runtime_governor)
        trend = self._safe_dict(trend)

        identity_state = self._safe_dict(
            runtime_identity.get("identity_state")
        )

        identity = str(
            identity_state.get("runtime_identity", "")
        ).lower()

        selected_action = str(
            runtime_governor.get("selected_action", "")
        ).lower()

        instability_ratio = self._safe_float(
            trend.get("instability_ratio"),
            0.0,
        )

        stability_ratio = self._safe_float(
            trend.get("stability_ratio"),
            0.0,
        )

        retry_actions = self._safe_int(
            trend.get("retry_actions"),
            0,
        )

        goal = "maintain_runtime_stability"
        sub_goal = "observe_runtime_pressure"
        priority = "medium"
        progress = min(
            1.0,
            max(
                0.0,
                stability_ratio,
            ),
        )

        if identity == "cooldown_runtime":
            goal = "stabilize_runtime"
            sub_goal = "reduce_retry_pressure"
            priority = "critical"
            progress = max(
                0.0,
                1.0 - instability_ratio,
            )

        elif identity == "stabilization_runtime":
            goal = "restore_safe_execution"
            sub_goal = "preserve_success_without_mutation"
            priority = "high"
            progress = stability_ratio

        elif selected_action == "preserve_success_state":
            goal = "preserve_success_state"
            sub_goal = "avoid_regression"
            priority = "medium"
            progress = max(
                progress,
                0.65,
            )

        if retry_actions >= 10:
            priority = "critical"

        self.goal_state["goal_age"] = (
            self._safe_int(
                self.goal_state.get("goal_age"),
                0,
            )
            + 1
        )

        self.goal_state.update(
            {
                "current_goal": goal,
                "sub_goal": sub_goal,
                "priority": priority,
                "goal_progress": round(
                    progress,
                    4,
                ),
                "goal_status": "active",
            }
        )

        self.goal_state["goal_history"].append(
            {
                "goal": goal,
                "sub_goal": sub_goal,
                "priority": priority,
                "progress": round(
                    progress,
                    4,
                ),
            }
        )

        self.goal_state["goal_history"] = (
            self.goal_state["goal_history"][-25:]
        )

        return {
            "ok": True,
            "goal_state": self.goal_state,
        }

    def get_goal(
        self,
    ):
        return self.goal_state

    def _safe_dict(
        self,
        value,
    ):
        return value if isinstance(value, dict) else {}

    def _safe_int(
        self,
        value,
        default=0,
    ):
        try:
            return int(value)
        except Exception:
            return default

    def _safe_float(
        self,
        value,
        default=0.0,
    ):
        try:
            return float(value)
        except Exception:
            return default

