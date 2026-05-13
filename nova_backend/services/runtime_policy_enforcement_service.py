class RuntimePolicyEnforcementService:
    def __init__(
        self,
        policy_adapter=None,
    ):
        self.policy_adapter = policy_adapter

    def _safe_dict(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def current_policy(
        self,
    ):
        if (
            self.policy_adapter
            and hasattr(
                self.policy_adapter,
                "adapt_policy",
            )
        ):
            adapted = self._safe_dict(
                self.policy_adapter.adapt_policy()
            )

            return self._safe_dict(
                adapted.get("adaptive_policy")
            )

        return {}

    def inspect(
        self,
        execution_state=None,
        final_action=None,
        control=None,
    ):
        execution_state = self._safe_dict(
            execution_state
        )

        control = self._safe_dict(
            control
        )

        policy = self.current_policy()

        notes = []

        if not policy.get("allow_mutation", True):
            notes.append("mutation_would_be_blocked")

        if not policy.get("allow_evolution", True):
            notes.append("evolution_would_be_blocked")

        unsafe_mutation_actions = {
            "mutate",
            "evolve",
            "expand",
            "rewrite",
            "self_modify",
            "policy_evolve",
        }

        if (
            final_action in unsafe_mutation_actions
            and not policy.get(
                "allow_mutation",
                True,
            )
        ):
            enforced_action = "stabilize"
            execution_state["runtime_action_rewritten"] = True
            notes.append(
                "unsafe_mutation_rewritten_to_stabilize"
            )

        if (
            final_action in unsafe_mutation_actions
            and not policy.get(
                "allow_evolution",
                True,
            )
        ):
            enforced_action = "stabilize"
            execution_state["runtime_action_rewritten"] = True
            notes.append(
                "unsafe_evolution_rewritten_to_stabilize"
            )

        if final_action == "retry":
            retry_ceiling = int(
                policy.get("retry_ceiling", 3) or 3
            )

            retry_count = int(
                execution_state.get(
                    "runtime_retry_count",
                    0,
                )
                or 0
            )

            if retry_count + 1 > retry_ceiling:
                notes.append("retry_ceiling_would_be_hit")

        return {
            "ok": True,
            "mode": "observe_only",
            "policy": policy,
            "final_action": final_action,
            "control": control,
            "notes": notes,
        }

    def enforce_soft(
        self,
        execution_state=None,
        final_action=None,
        control=None,
    ):
        execution_state = self._safe_dict(
            execution_state
        )

        control = self._safe_dict(
            control
        )

        inspection = self.inspect(
            execution_state=execution_state,
            final_action=final_action,
            control=control,
        )

        policy = self._safe_dict(
            inspection.get("policy")
        )

        enforced_action = final_action
        notes = list(
            inspection.get("notes")
            or []
        )

        runtime_health = str(
            policy.get(
                "runtime_health"
            )
            or ""
        ).lower()

        if runtime_health == "unstable":
            execution_state["runtime_route"] = (
                "stabilization"
            )
            execution_state["runtime_stabilization_mode"] = (
                "diagnose_and_repair"
            )
            notes.append(
                "unstable_runtime_routed_to_stabilization"
            )

            cooldown_count = int(
                execution_state.get(
                    "runtime_cooldown_count",
                    0,
                )
                or 0
            )

            cooldown_count += 1

            execution_state["runtime_cooldown_count"] = (
                cooldown_count
            )

            execution_state["runtime_cooldown_active"] = True

            if cooldown_count >= 3:
                execution_state["runtime_stabilization_mode"] = (
                    "cooldown_repair"
                )
                notes.append(
                    "adaptive_cooldown_activated"
                )

        elif runtime_health == "recovering":
            execution_state["runtime_route"] = (
                "recovery"
            )
            execution_state["runtime_stabilization_mode"] = (
                "careful_resume"
            )
            execution_state["runtime_cooldown_active"] = False
            notes.append(
                "runtime_recovery_route_selected"
            )

        elif runtime_health == "stable":
            execution_state["runtime_route"] = (
                "normal"
            )
            execution_state["runtime_stabilization_mode"] = (
                "normal_operation"
            )
            execution_state["runtime_cooldown_active"] = False
            execution_state["runtime_cooldown_count"] = 0
            notes.append(
                "runtime_stability_restored"
            )

        retry_ceiling = int(
            policy.get(
                "retry_ceiling",
                3,
            )
            or 3
        )

        retry_count = int(
            execution_state.get(
                "runtime_retry_count",
                0,
            )
            or 0
        )

        if final_action == "retry":
            retry_count += 1
            execution_state["runtime_retry_count"] = (
                retry_count
            )

            if retry_count > retry_ceiling:
                enforced_action = (
                    "inspect_failed_step"
                )

                execution_state["runtime_action_rewritten"] = True

                execution_state[
                    "runtime_retry_ceiling_hit"
                ] = True
                notes.append(
                    "soft_retry_ceiling_enforced"
                )

        execution_state["runtime_policy_mode"] = (
            "soft_enforcement"
        )

        execution_state["runtime_policy_enforcement"] = {
            "original_action": final_action,
            "enforced_action": enforced_action,
            "notes": notes,
            "policy": policy,
        }

        return {
            "ok": True,
            "mode": "soft_enforcement",
            "policy": policy,
            "original_action": final_action,
            "enforced_action": enforced_action,
            "execution_state": execution_state,
            "notes": notes,
            "control": control,
        }