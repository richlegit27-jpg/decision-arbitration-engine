class RuntimeLearningService:
    def __init__(self):
        self.policy_memory = {
            "retry_success_rate": 0.5,
            "pause_effectiveness": 0.5,
            "continue_effectiveness": 0.5,
            "history_samples": 0,
        }

        self.strategy_memory = {
            "retry_strategy_score": 0.5,
            "pause_strategy_score": 0.5,
            "continue_strategy_score": 0.5,
        }

        self.meta_policy = {
            "learning_rate": 0.1,
            "adaptation_speed": 1.0,
            "exploration_bias": 0.2,
        }

    def _safe_dict(self, value):
        return value if isinstance(value, dict) else {}

    def update_meta_policy(
        self,
        execution_summary,
        reflection,
    ):
        execution_summary = self._safe_dict(execution_summary)
        reflection = self._safe_dict(reflection)

        meta = self.meta_policy

        failed = execution_summary.get("failed_count", 0)
        complete = execution_summary.get("complete", False)

        if failed:
            meta["learning_rate"] = min(
                0.5,
                meta["learning_rate"] + 0.02,
            )
            meta["adaptation_speed"] += 0.1

        if complete:
            meta["learning_rate"] = max(
                0.05,
                meta["learning_rate"] - 0.01,
            )
            meta["adaptation_speed"] = max(
                0.5,
                meta["adaptation_speed"] - 0.05,
            )

        if reflection.get("signal") == "runtime_idle":
            meta["exploration_bias"] = min(
                1.0,
                meta["exploration_bias"] + 0.05,
            )

        self.meta_policy = meta

        return meta

    def update_learning_metrics(
        self,
        execution_summary,
        reflection,
    ):
        execution_summary = self._safe_dict(execution_summary)
        reflection = self._safe_dict(reflection)

        memory = self.policy_memory
        learning_rate = self.meta_policy.get("learning_rate", 0.1)

        memory["history_samples"] += 1

        signal = reflection.get("signal")

        if signal == "failure_detected":
            memory["retry_success_rate"] = (
                memory["retry_success_rate"]
                * (1 - learning_rate)
                + learning_rate
            )

        if execution_summary.get("complete"):
            memory["continue_effectiveness"] = (
                memory["continue_effectiveness"]
                * (1 - learning_rate)
                + learning_rate
            )

        if signal == "runtime_idle":
            memory["pause_effectiveness"] = (
                memory["pause_effectiveness"]
                * (1 - learning_rate)
                + learning_rate
            )

        self.policy_memory = memory

        return memory

    def update_strategy_memory(
        self,
        execution_summary,
    ):
        execution_summary = self._safe_dict(execution_summary)

        strategy = self.strategy_memory
        learning_rate = self.meta_policy.get("learning_rate", 0.1)

        if execution_summary.get("failed_count"):
            strategy["retry_strategy_score"] += learning_rate * 0.5

        if execution_summary.get("complete"):
            strategy["continue_strategy_score"] += learning_rate * 0.5

        if execution_summary.get("current_index", 0) == 0:
            strategy["pause_strategy_score"] += learning_rate * 0.2

        for key in strategy:
            strategy[key] = max(
                0.0,
                min(1.0, strategy[key]),
            )

        self.strategy_memory = strategy

        return strategy

    def run_learning_cycle(
        self,
        execution_summary,
        reflection,
    ):
        execution_summary = self._safe_dict(execution_summary)
        reflection = self._safe_dict(reflection)

        policy_memory = self.update_learning_metrics(
            execution_summary=execution_summary,
            reflection=reflection,
        )

        strategy_memory = self.update_strategy_memory(
            execution_summary=execution_summary,
        )

        meta_policy = self.update_meta_policy(
            execution_summary=execution_summary,
            reflection=reflection,
        )

        return {
            "policy_memory": policy_memory,
            "strategy_memory": strategy_memory,
            "meta_policy": meta_policy,
        }

    def get_policy_memory(self):
        return self.policy_memory

    def get_strategy_memory(self):
        return self.strategy_memory

    def get_meta_policy(self):
        return self.meta_policy