
class RuntimeStrategyMemoryService:
    def __init__(
        self,
        max_records=50,
    ):
        self.max_records = max_records

    def _safe_dict(
        self,
        value,
    ):
        return value if isinstance(value, dict) else {}

    def _safe_list(
        self,
        value,
    ):
        return value if isinstance(value, list) else []

    def remember(
        self,
        execution_state=None,
        final_action=None,
        runtime_signal=None,
        success=None,
    ):
        execution_state = self._safe_dict(execution_state)

        strategy_memory = self._safe_list(
            execution_state.get("runtime_strategy_memory")
        )

        final_action = str(
            final_action
            or execution_state.get("runtime_final_action")
            or execution_state.get("governed_action")
            or ""
        )

        runtime_signal = str(
            runtime_signal
            or execution_state.get("runtime_signal")
            or ""
        ).lower()

        if success is None:
            success = bool(
                execution_state.get("complete")
                or execution_state.get("status") == "completed"
                or "success" in runtime_signal
                or "stabilized" in runtime_signal
            )

        failure = bool(
            "failure" in runtime_signal
            or "failed" in runtime_signal
            or execution_state.get("status") == "failed"
        )

        score_delta = 0

        if success:
            score_delta += 2

        if failure:
            score_delta -= 2

        if "cooldown" in final_action:
            score_delta += 1

        if "preserve" in final_action:
            score_delta += 2

        if "retry" in final_action and failure:
            score_delta -= 1

        record = {
            "action": final_action,
            "runtime_signal": runtime_signal,
            "success": success,
            "failure": failure,
            "score_delta": score_delta,
        }

        strategy_memory.append(record)
        strategy_memory = strategy_memory[-self.max_records:]

        strategy_scores = {}

        for item in strategy_memory:
            if not isinstance(item, dict):
                continue

            action = str(item.get("action") or "")

            if not action:
                continue

            strategy_scores[action] = (
                strategy_scores.get(action, 0)
                + int(item.get("score_delta", 0) or 0)
            )

        preferred_strategy = None
        suppressed_strategy = None

        if strategy_scores:
            preferred_strategy = max(
                strategy_scores,
                key=strategy_scores.get,
            )

            suppressed_strategy = min(
                strategy_scores,
                key=strategy_scores.get,
            )

        execution_state["runtime_strategy_memory"] = strategy_memory
        execution_state["runtime_strategy_scores"] = strategy_scores
        execution_state["runtime_preferred_strategy"] = preferred_strategy
        execution_state["runtime_suppressed_strategy"] = suppressed_strategy

        return {
            "ok": True,
            "execution_state": execution_state,
            "record": record,
            "strategy_scores": strategy_scores,
            "preferred_strategy": preferred_strategy,
            "suppressed_strategy": suppressed_strategy,
        }