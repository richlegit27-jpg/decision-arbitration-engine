class RuntimePredictionHistoryService:

    def __init__(self):

        self.history = []

    def _safe_dict(self, value):

        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def record_prediction(
        self,
        prediction=None,
    ):

        prediction = self._safe_dict(
            prediction
        )

        self.history.append(
            prediction
        )

        self.history = self.history[-100:]

        return {
            "ok": True,
            "history_count": len(self.history),
            "last_prediction": prediction,
        }

    def summarize_history(self):

        states = {}

        for item in self.history:

            state = item.get(
                "predicted_state",
                "unknown",
            )

            states[state] = (
                states.get(
                    state,
                    0,
                ) + 1
            )

        return {
            "ok": True,
            "history_count": len(self.history),
            "state_counts": states,
        }

