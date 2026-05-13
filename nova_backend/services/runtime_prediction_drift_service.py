class RuntimePredictionDriftService:

    def __init__(
        self,
        prediction_history=None,
    ):

        self.prediction_history = (
            prediction_history
        )

    def _safe_dict(self, value):

        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def analyze_drift(self):

        history_summary = (
            self.prediction_history.summarize_history()
            if self.prediction_history
            else {}
        )

        history_summary = self._safe_dict(
            history_summary
        )

        state_counts = self._safe_dict(
            history_summary.get(
                "state_counts"
            )
        )

        adaptive = int(
            state_counts.get(
                "adaptive",
                0,
            )
        )

        unstable = int(
            state_counts.get(
                "unstable",
                0,
            )
        )

        stable = int(
            state_counts.get(
                "stable",
                0,
            )
        )

        drift_state = "stable"

        if unstable > stable:

            drift_state = (
                "destabilizing"
            )

        elif adaptive >= stable:

            drift_state = (
                "transitioning"
            )

        return {
            "ok": True,
            "drift_state": drift_state,
            "state_counts": state_counts,
        }

    def recommend_drift_response(self):

        drift = self.analyze_drift()

        drift_state = str(
            drift.get(
                "drift_state",
                "",
            )
        ).lower()

        recommendations = []

        if drift_state == "destabilizing":

            recommendations.append(
                "Increase repair and debugging intensity."
            )

        elif drift_state == "transitioning":

            recommendations.append(
                "Maintain adaptive orchestration balance."
            )

        else:

            recommendations.append(
                "Runtime prediction drift remains stable."
            )

        return {
            "ok": True,
            "drift_state": drift_state,
            "recommendations": recommendations,
            "drift": drift,
        }