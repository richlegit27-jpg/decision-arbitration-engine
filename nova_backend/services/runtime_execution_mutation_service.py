class RuntimeExecutionMutationService:

    name = "runtime_execution_mutation_service"

    tags = [
        "runtime",
        "execution",
        "mutation",
        "control",
    ]

    def mutate(
        self,
        execution_state=None,
        runtime_execution_router=None,
        bridge_state=None,
    ):

        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        runtime_execution_router = (
            runtime_execution_router
            if isinstance(runtime_execution_router, dict)
            else {}
        )

        bridge_state = (
            bridge_state
            if isinstance(bridge_state, dict)
            else {}
        )

        route = str(
            runtime_execution_router.get(
                "route",
                "observe_only",
            )
        ).lower()

        priority = str(
            runtime_execution_router.get(
                "priority",
                "low",
            )
        ).lower()

        execute_now = bool(
            runtime_execution_router.get(
                "execute_now",
                False,
            )
        )

        bridge_action = str(
            bridge_state.get(
                "bridge_action",
                "",
            )
        ).lower()

        execution_action = str(
            bridge_state.get(
                "execution_action",
                "",
            )
        ).lower()

        mutation_applied = False
        mutation_action = "none"
        mutation_reason = "Runtime remained in observe-only mode."

        execution_state.setdefault(
            "runtime_mutations",
            []
        )

        if (
            execute_now
            and route in {
                "normal_autonomous_execution",
                "guarded_recovery_execution",
                "recovery_execution",
            }
        ):

            mutation_applied = True
            mutation_action = "prioritize_current_execution"
            mutation_reason = (
                "Runtime router requested active execution."
            )

            execution_state["runtime_execution_priority"] = (
                priority
            )

            execution_state["runtime_execution_route"] = (
                route
            )

            execution_state["runtime_execute_now"] = True

            execution_state["runtime_mutation_mode"] = (
                "active_execution_control"
            )

        if bridge_action == "runtime_directed_execution":

            mutation_applied = True
            mutation_action = "bridge_authorized_runtime_execution"
            mutation_reason = (
                "Runtime bridge authorized directed execution."
            )

            execution_state["runtime_bridge_authorized"] = True
            execution_state["runtime_execution_action"] = (
                execution_action
            )

        execution_state["runtime_mutations"].append(
            {
                "applied": mutation_applied,
                "action": mutation_action,
                "reason": mutation_reason,
                "route": route,
                "priority": priority,
                "execute_now": execute_now,
            }
        )

        execution_state["runtime_mutations"] = (
            execution_state["runtime_mutations"][-25:]
        )

        return {
            "ok": True,
            "mutation_applied": mutation_applied,
            "mutation_action": mutation_action,
            "mutation_reason": mutation_reason,
            "execution_state": execution_state,
            "runtime_execution_router": runtime_execution_router,
            "bridge_state": bridge_state,
        }