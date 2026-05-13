class GovernorService:
    def __init__(self):
        self.governor_policy = {
            "allow_retry": True,
            "allow_pause": True,
            "allow_continue": True,
            "adaptation_level": 1,
        }

    def _safe_dict(self, value):
        return value if isinstance(value, dict) else {}

    def update_governor_policy(self, reflection):
        reflection = self._safe_dict(reflection)

        policy = self.governor_policy
        signal = reflection.get("signal")

        if signal == "failure_detected":
            policy["adaptation_level"] += 1
            policy["allow_retry"] = True

        elif signal == "execution_complete":
            policy["adaptation_level"] = max(
                1,
                policy["adaptation_level"] - 1,
            )
            policy["allow_continue"] = True

        elif signal == "runtime_idle":
            policy["allow_pause"] = True

        self.governor_policy = policy

        return policy

    def build_execution_override(self, decision):
        decision = self._safe_dict(decision)

        action = decision.get("action")

        return {
            "action": action,
            "should_pause": action == "wait_for_task",
            "should_retry": action == "inspect_failed_step",
            "should_continue": action == "preserve_success_state",
        }

    def govern(
        self,
        decision,
        execution_override=None,
        execution_state=None,
        policy_memory=None,
        strategy_memory=None,
    ):
        decision = self._safe_dict(decision)
        execution_override = self._safe_dict(execution_override)
        execution_state = self._safe_dict(execution_state)
        policy_memory = self._safe_dict(policy_memory)
        strategy_memory = self._safe_dict(strategy_memory)

        policy = self.governor_policy

        action = decision.get("action")
        override_action = execution_override.get("action")

        final_action = override_action if override_action else action

        retry_pref = strategy_memory.get(
            "retry_strategy_score",
            0.5,
        )

        continue_pref = strategy_memory.get(
            "continue_strategy_score",
            0.5,
        )

        pause_effectiveness = policy_memory.get(
            "pause_effectiveness",
            0.5,
        )

        if execution_override.get("should_retry"):
            if retry_pref > continue_pref and policy.get("allow_retry"):
                final_action = "retry"

        if execution_override.get("should_pause"):
            if (
                pause_effectiveness > 0.3
                and policy.get("allow_pause")
            ):
                final_action = "pause"

        if execution_override.get("should_continue"):
            if (
                continue_pref >= retry_pref
                and policy.get("allow_continue")
            ):
                final_action = "continue"

        execution_state["governed_action"] = final_action

        return final_action, execution_state

    def get_policy(self):
        return self.governor_policy