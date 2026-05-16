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

        if execution_state.get(
            "runtime_bridge_authorized"
        ):

            final_action = (
                execution_state.get(
                    "runtime_execution_action"
                )
                or "runtime_execute_now"
            )

            notes.append(
                "inspect_bridge_override"
            )

            return {
                "ok": True,
                "mode": "autonomous_execution",
                "policy": policy,
                "final_action": final_action,
                "control": control,
                "notes": notes,
            }

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

        queue_size = int(
            execution_state.get(
                "runtime_queue_size",
                0,
            )
            or 0
        )

        queue_size = int(
            execution_state.get(
                "runtime_queue_size",
                0,
            )
            or 0
        )

        runtime_execution_queue = (
            execution_state.get(
                "runtime_execution_queue",
                []
            )
        )

        if (
            not runtime_execution_queue
            and control.get(
                "runtime_execution_queue"
            )
        ):

            runtime_execution_queue = (
                control.get(
                    "runtime_execution_queue"
                )
            )

        if (
            queue_size <= 0
            and isinstance(
                runtime_execution_queue,
                dict,
            )
        ):

            queue_size = int(
                runtime_execution_queue.get(
                    "queue_size",
                    0,
                )
                or 0
            )

        if (
            queue_size <= 0
            and isinstance(
                runtime_execution_queue,
                dict,
            )
        ):

            queue_size = int(
                len(
                    runtime_execution_queue.get(
                        "queue",
                        [],
                    )
                )
            )

        elif (
            queue_size <= 0
            and isinstance(
                runtime_execution_queue,
                list,
            )
        ):

            queue_size = int(
                len(runtime_execution_queue)
            )

        if (
            not runtime_execution_queue
            and control.get(
                "runtime_execution_queue"
            )
        ):

            runtime_execution_queue = (
                control.get(
                    "runtime_execution_queue"
                )
            )

        if (
            queue_size <= 0
            and isinstance(
                runtime_execution_queue,
                dict,
            )
        ):

            queue_size = int(
                runtime_execution_queue.get(
                    "queue_size",
                    0,
                )
                or 0
            )

            if isinstance(
                runtime_execution_queue,
                dict,
            ):

                queue_size = int(
                    len(
                        runtime_execution_queue.get(
                            "queue",
                            [],
                        )
                    )
                )

            elif isinstance(
                runtime_execution_queue,
                list,
            ):

                queue_size = int(
                    len(runtime_execution_queue)
                )

        bridge_authorized = bool(
            execution_state.get(
                "runtime_bridge_authorized",
                False,
            )
        )

        autonomous_execution_requested = bool(
            execution_state.get(
                "runtime_execute_now",
                False,
            )
        )

        # =====================================
        # UNSTABLE
        # =====================================

        if runtime_health == "unstable":

            execution_state["runtime_route"] = (
                "stabilization"
            )

            execution_state[
                "runtime_stabilization_mode"
            ] = "diagnose_and_repair"

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

            execution_state[
                "runtime_cooldown_count"
            ] = cooldown_count

            execution_state[
                "runtime_cooldown_active"
            ] = True

            if cooldown_count >= 3:

                execution_state[
                    "runtime_stabilization_mode"
                ] = "cooldown_repair"

                notes.append(
                    "adaptive_cooldown_activated"
                )

         # =====================================
        # RECOVERING
        # =====================================

        elif runtime_health == "recovering":

            execution_state["runtime_route"] = (
                "recovery"
            )

            execution_state[
                "runtime_stabilization_mode"
            ] = "careful_resume"

            execution_state[
                "runtime_cooldown_active"
            ] = False

            notes.append(
                "runtime_recovery_route_selected"
            )

            # =====================================
            # AUTONOMOUS EXECUTION OVERRIDE
            # =====================================

            if (
                bridge_authorized
                and autonomous_execution_requested
                and queue_size > 0
            ):

                enforced_action = (
                    "reroute_execution"
                )

                final_action = (
                    "reroute_execution"
                )

                execution_state[
                    "runtime_route"
                ] = "autonomous_execution"

                execution_state[
                    "runtime_stabilization_mode"
                ] = "directed_execution"

                execution_state[
                    "runtime_governed_override"
                ] = True

                execution_state[
                    "runtime_execute_now"
                ] = True

                execution_state[
                    "runtime_autonomous_execution_allowed"
                ] = True

                execution_state[
                    "runtime_policy_override"
                ] = True

                execution_state[
                    "runtime_preferred_strategy"
                ] = "reroute_execution"

                execution_state[
                    "runtime_consensus_action"
                ] = "reroute_execution"

                execution_state[
                    "runtime_consensus_authority"
                ] = "runtime_bridge_override"

                execution_state[
                    "runtime_final_action"
                ] = "reroute_execution"

                execution_state[
                    "governed_action"
                ] = "reroute_execution"

                execution_state[
                    "runtime_suppressed_strategy"
                ] = None

                execution_state[
                    "runtime_repair_mode"
                ] = "directed_execution"

                execution_state[
                    "runtime_selected_repair"
                ] = {
                    "action": (
                        "reroute_execution"
                    ),
                    "priority": "high",
                    "reason": (
                        "Bridge override bypassed "
                        "recovery suppression."
                    ),
                }

                execution_state[
                    "healing_mode"
                ] = "active_execution"

                execution_state[
                    "runtime_execution_queue"
                ] = runtime_execution_queue

                execution_state[
                    "runtime_queue_size"
                ] = queue_size

                notes.append(
                    "bridge_authorized_execution_override"
                )

                notes.append(
                    "runtime_execution_forced_active"
                )

        # =====================================
        # STABLE
        # =====================================

        elif runtime_health == "stable":

            execution_state["runtime_route"] = (
                "normal"
            )

            execution_state[
                "runtime_stabilization_mode"
            ] = "normal_operation"

            execution_state[
                "runtime_cooldown_active"
            ] = False

            execution_state[
                "runtime_cooldown_count"
            ] = 0

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

            execution_state[
                "runtime_retry_count"
            ] = retry_count

            if retry_count > retry_ceiling:

                enforced_action = (
                    "inspect_failed_step"
                )

                execution_state[
                    "runtime_action_rewritten"
                ] = True

                execution_state[
                    "runtime_retry_ceiling_hit"
                ] = True

                notes.append(
                    "soft_retry_ceiling_enforced"
                )

        execution_state[
            "runtime_policy_mode"
        ] = "soft_enforcement"

        execution_state[
            "runtime_policy_enforcement"
        ] = {
            "original_action": final_action,
            "enforced_action": enforced_action,
            "notes": notes,
            "policy": policy,
        }

        if execution_state.get(
            "runtime_bridge_authorized"
        ):

            enforced_action = (
                execution_state.get(
                    "runtime_execution_action"
                )
                or "runtime_execute_now"
            )

            policy[
                "allow_evolution"
            ] = True

            policy[
                "allow_retry"
            ] = True

            policy[
                "runtime_health"
            ] = "stable"

            notes.append(
                "bridge_override_execution"
            )

            notes.append(
                "bridge_authorized_execution_override"
            )

        if execution_state.get(
            "runtime_bridge_authorized"
        ):

            enforced_action = (
                execution_state.get(
                    "runtime_execution_action"
                )
                or "runtime_execute_now"
            )

            execution_state[
                "healing_mode"
            ] = (
                "active_execution"
            )

            execution_state[
                "runtime_route"
            ] = (
                "autonomous_execution"
            )

            execution_state[
                "recovery_mode"
            ] = False

            policy[
                "runtime_health"
            ] = "stable"

            notes.append(
                "forced_bridge_execution_exit"
            )

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
