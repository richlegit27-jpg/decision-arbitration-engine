class RuntimeCognitiveInjectionService:
    """
    Converts large runtime state into a small cognition-safe summary.

    Goal:
        Never inject the full runtime JSON into chat.
        Only inject stable, useful operating signals.
    """

    def __init__(self, max_lines: int = 8):
        self.max_lines = max_lines

    def _safe_dict(self, value):
        if isinstance(value, dict):
            return value
        return {}

    def _safe_str(self, value):
        if value is None:
            return ""

        try:
            return str(value).strip()
        except Exception:
            return ""

    def _dig(self, data, *keys):
        current = data

        for key in keys:
            if not isinstance(current, dict):
                return ""

            current = current.get(key)

        return current

    def build_summary(self, runtime_state) -> str:
        runtime_state = self._safe_dict(runtime_state)

        compressed = self._safe_dict(
            runtime_state.get("compressed_runtime")
        )

        if not compressed:
            compressed = runtime_state

        world_prediction = self._safe_dict(
            compressed.get("runtime_world_prediction")
        )

        execution_router = self._safe_dict(
            compressed.get("runtime_execution_router")
        )

        execution_queue = self._safe_dict(
            compressed.get("runtime_execution_queue")
        )

        queue_state = self._safe_dict(
            execution_queue.get("execution_state")
        )

        identity = self._safe_dict(
            queue_state.get("runtime_identity")
        )

        identity_state = self._safe_dict(
            identity.get("identity_state")
        )

        goal = self._safe_dict(
            queue_state.get("runtime_goal")
        )

        goal_state = self._safe_dict(
            goal.get("goal_state")
        )

        lines = []

        def add(label, value):
            value = self._safe_str(value)

            if not value:
                return

            lines.append(f"- {label}: {value}")

        add(
            "health",
            compressed.get("runtime_health"),
        )

        add(
            "route",
            compressed.get("runtime_route"),
        )

        add(
            "signal",
            compressed.get("runtime_signal"),
        )

        add(
            "goal",
            world_prediction.get("active_goal")
            or goal_state.get("current_goal"),
        )

        add(
            "predicted_state",
            world_prediction.get("predicted_state"),
        )

        add(
            "risk_forecast",
            world_prediction.get("risk_forecast"),
        )

        add(
            "autonomy_mode",
            execution_router.get("autonomy_mode"),
        )

        add(
            "runtime_identity",
            identity_state.get("runtime_identity"),
        )

        if not lines:
            return ""

        lines = lines[: self.max_lines]

        return "Runtime state:\n" + "\n".join(lines)

    def inject(
        self,
        user_text: str = "",
        runtime_state=None,
        existing_context: str = "",
    ) -> str:

        summary = self.build_summary(runtime_state)

        existing_context = self._safe_str(existing_context)

        if not summary:
            return existing_context

        if existing_context:
            return summary + "\n\n" + existing_context

        return summary