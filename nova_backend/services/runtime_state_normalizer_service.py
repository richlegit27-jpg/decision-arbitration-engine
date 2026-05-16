class RuntimeStateNormalizerService:

    def normalize(
        self,
        execution_state=None,
    ):
        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        heavy_keys = [
            "runtime_autonomous_execution",
            "runtime_execution_queue",
        ]

        normalized = {}

        for key in heavy_keys:

            value = execution_state.get(
                key,
                {}
            )

            if not isinstance(value, dict):
                continue

            reduced = {}

            for allowed_key in [
                "ok",
                "reason",
                "runtime_signal",
                "queue_size",
                "completed_count",
                "failed_count",
            ]:

                if allowed_key in value:
                    reduced[allowed_key] = (
                        value.get(allowed_key)
                    )

            normalized[key] = reduced

        execution_state[
            "runtime_normalized_state"
        ] = normalized

        return {
            "ok": True,
            "normalized": normalized,
            "execution_state": execution_state,
        }