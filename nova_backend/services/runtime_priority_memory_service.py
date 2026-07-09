class RuntimePriorityMemoryService:
    def prioritize(
        self,
        execution_state=None,
    ):
        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        runtime_memory = execution_state.get(
            "runtime_autonomous_memory",
            [],
        )

        if not isinstance(runtime_memory, list):
            runtime_memory = []

        priority_memory = []

        for item in runtime_memory:

            if not isinstance(item, dict):
                continue

            signal = str(
                item.get("runtime_signal") or ""
            ).lower()

            reason = str(
                item.get("reason") or ""
            ).lower()

            keep = False

            if "repair" in signal:
                keep = True

            if "checkpoint" in signal:
                keep = True

            if "rollback" in signal:
                keep = True

            if "integrity" in signal:
                keep = True

            if "failure" in reason:
                keep = True

            if keep:
                priority_memory.append(
                    item
                )

        execution_state[
            "runtime_priority_memory"
        ] = priority_memory[-10:]

        return {
            "ok": True,
            "priority_count": len(
                priority_memory
            ),
            "execution_state": execution_state,
        }

