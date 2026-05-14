class RuntimeCognitiveInjectionService:
    """
    Compresses runtime state into small cognition signals
    that chat/intelligence routing can safely consume.
    """

    def __init__(self):
        pass

    def build(self, runtime_summary=None, runtime_decision=None):

        runtime_summary = self._safe_dict(runtime_summary)
        runtime_decision = self._safe_dict(runtime_decision)

        cycle_count = self._first_present(
            runtime_summary,
            [
                "cycle_count",
                "cycles",
                "cycle",
            ],
            0,
        )

        active_goal = self._first_present(
            runtime_summary,
            [
                "active_goal",
                "runtime_goal",
                "goal",
            ],
            "",
        )

        predicted_state = self._nested_first_present(
            runtime_summary,
            [
                ("runtime_world_model", "predicted_state"),
                ("world_model", "predicted_state"),
                ("prediction", "predicted_state"),
            ],
            "",
        )

        risk_forecast = self._nested_first_present(
            runtime_summary,
            [
                ("runtime_world_model", "risk_forecast"),
                ("world_model", "risk_forecast"),
                ("prediction", "risk_forecast"),
            ],
            "",
        )

        last_action = self._first_present(
            runtime_decision,
            [
                "final_action",
                "action",
                "selected_action",
            ],
            "",
        )

        runtime_pressure = self._build_pressure(
            risk_forecast=risk_forecast,
            predicted_state=predicted_state,
        )

        recommendation = self._build_recommendation(
            risk_forecast=risk_forecast,
            predicted_state=predicted_state,
            last_action=last_action,
        )

        return {
            "runtime_active_goal": active_goal,
            "runtime_predicted_state": predicted_state,
            "runtime_risk": risk_forecast,
            "runtime_last_action": last_action,
            "runtime_cycle_count": cycle_count,
            "runtime_pressure": runtime_pressure,
            "runtime_recommendation": recommendation,
            "has_runtime_cognition": bool(
                active_goal
                or predicted_state
                or risk_forecast
                or last_action
                or cycle_count
            ),
        }

    def _safe_dict(self, value):

        if isinstance(value, dict):
            return value

        return {}

    def _first_present(self, data, keys, default=None):

        data = self._safe_dict(data)

        for key in keys:

            value = data.get(key)

            if value not in (None, "", [], {}):
                return value

        return default

    def _nested_first_present(self, data, paths, default=None):

        data = self._safe_dict(data)

        for parent_key, child_key in paths:

            parent = self._safe_dict(
                data.get(parent_key)
            )

            value = parent.get(child_key)

            if value not in (None, "", [], {}):
                return value

        return default

    def _build_pressure(
        self,
        risk_forecast="",
        predicted_state="",
    ):

        risk = str(risk_forecast or "").lower()
        predicted = str(predicted_state or "").lower()

        if risk in {"high", "critical"}:
            return "execution instability detected"

        if "unstable" in predicted:
            return "runtime instability detected"

        if "stabil" in predicted:
            return "runtime stabilization in progress"

        if risk:
            return "runtime risk signal detected"

        return ""

    def _build_recommendation(
        self,
        risk_forecast="",
        predicted_state="",
        last_action="",
    ):

        risk = str(risk_forecast or "").lower()
        predicted = str(predicted_state or "").lower()
        action = str(last_action or "").lower()

        if risk in {"high", "critical"}:
            return "reduce concurrent execution load"

        if "pause" in action:
            return "hold execution until runtime stabilizes"

        if "stabil" in predicted:
            return "continue observing runtime state"

        return ""