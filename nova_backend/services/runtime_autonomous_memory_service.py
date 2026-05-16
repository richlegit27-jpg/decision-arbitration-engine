class RuntimeAutonomousMemoryService:

    name = "runtime_autonomous_memory_service"

    tags = [
        "runtime",
        "autonomy",
        "memory",
        "learning",
    ]

    def remember(
        self,
        execution_state=None,
        runtime_autonomous_execution=None,
    ):

        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        runtime_autonomous_execution = (
            runtime_autonomous_execution
            if isinstance(
                runtime_autonomous_execution,
                dict,
            )
            else {}
        )

        memory = execution_state.get(
            "runtime_autonomous_memory",
            [],
        )

        if not isinstance(memory, list):
            memory = []

        memory = list(memory)

        historical_actions = execution_state.get(
            "runtime_autonomous_actions",
            [],
        )

        if not isinstance(historical_actions, list):
            historical_actions = []

        historical_actions = list(historical_actions)

        executed_actions = runtime_autonomous_execution.get(
            "executed_actions",
            [],
        )

        if not isinstance(executed_actions, list):
            executed_actions = []

        runtime_signal = str(
            execution_state.get(
                "runtime_signal",
                "",
            )
        )

        cycle_count = execution_state.get(
            "cycle_count",
            runtime_autonomous_execution.get(
                "cycle_count",
            ),
        )

        existing_keys = set()

        for item in memory:

            if not isinstance(item, dict):
                continue

            existing_keys.add(
                (
                    item.get("action"),
                    item.get("runtime_signal"),
                    item.get("cycle_count"),
                )
            )

        for action in executed_actions:

            if not isinstance(action, dict):
                continue

            memory_item = {
                "action": action.get("action"),
                "priority": action.get("priority"),
                "reason": action.get("reason"),
                "runtime_signal": runtime_signal,
                "cycle_count": cycle_count,
            }

            memory_key = (
                memory_item.get("action"),
                memory_item.get("runtime_signal"),
                memory_item.get("cycle_count"),
            )

            if memory_key not in existing_keys:

                memory.append(memory_item)
                existing_keys.add(memory_key)

            action_key = (
                action.get("action"),
                action.get("priority"),
                action.get("reason"),
            )

            existing_action_keys = {
                (
                    item.get("action"),
                    item.get("priority"),
                    item.get("reason"),
                )
                for item in historical_actions
                if isinstance(item, dict)
            }

            if action_key not in existing_action_keys:

                historical_actions.append(
                    action
                )

        execution_state["runtime_autonomous_memory"] = (
            memory[-100:]
        )

        execution_state["runtime_autonomous_actions"] = (
            historical_actions[-250:]
        )

        return {
            "ok": True,
            "memory_size": len(memory[-100:]),
            "execution_state": execution_state,
            "runtime_autonomous_memory": memory[-100:],
            "runtime_autonomous_actions": historical_actions[-250:],
        }