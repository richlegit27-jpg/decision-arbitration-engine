class RuntimeMemoryCompressionService:

    def __init__(
        self,
        max_raw_events=100,
    ):
        self.max_raw_events = (
            max_raw_events
        )

    def compress(
        self,
        execution_state=None,
    ):
        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        compressed = {}

        memory_keys = [
            "runtime_autonomous_memory",
            "runtime_history",
            "prediction_history",
            "goal_history",
            "identity_history",
            "plan_history",
        ]

        for key in memory_keys:

            value = execution_state.get(
                key,
                [],
            )

            if not isinstance(value, list):
                continue

            compressed[key] = value[-5:]

        execution_state[
            "runtime_compressed_memory"
        ] = compressed

        execution_state[
            "runtime_memory_compression_active"
        ] = True

        return {
            "ok": True,
            "compressed_keys": list(
                compressed.keys()
            ),
            "execution_state": execution_state,
        }