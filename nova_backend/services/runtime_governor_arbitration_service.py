class RuntimeGovernorArbitrationService:
    def __init__(self):
        self.weights = {
            "repair": 0.80,
            "policy": 1.20,
            "memory": 0.95,
            "strategy": 1.00,
            "reflection": 0.90,
        }

    def arbitrate(
        self,
        repair_action=None,
        policy_action=None,
        memory_action=None,
        strategy_action=None,
        reflection_action=None,
        runtime_policy=None,
        trend=None,
    ):
        runtime_policy = self._safe_dict(runtime_policy)
        trend = self._safe_dict(trend)

        candidates = {
            "repair": repair_action,
            "policy": policy_action,
            "memory": memory_action,
            "strategy": strategy_action,
            "reflection": reflection_action,
        }

        scores = {}

        for engine, action in candidates.items():
            if not action:
                continue

            score = self.weights.get(engine, 1.0)

            if engine == "policy":
                score += self._policy_pressure_score(
                    runtime_policy=runtime_policy,
                    trend=trend,
                    action=action,
                )

            if engine == "repair":
                score += self._repair_pressure_score(
                    trend=trend,
                    action=action,
                )

            scores[engine] = {
                "action": action,
                "score": round(score, 4),
            }

        if not scores:
            return {
                "ok": False,
                "selected_engine": None,
                "selected_action": None,
                "scores": scores,
                "candidates": candidates,
                "reason": "no_governor_candidates",
            }

        selected_engine = max(
            scores,
            key=lambda item: scores[item]["score"],
        )

        selected_action = scores[selected_engine]["action"]

        selected_action = self._rewrite_selected_action(
            selected_engine=selected_engine,
            selected_action=selected_action,
            runtime_policy=runtime_policy,
            trend=trend,
        )

        return {
            "ok": True,
            "selected_engine": selected_engine,
            "selected_action": selected_action,
            "scores": scores,
            "candidates": candidates,
            "reason": f"{selected_engine}_pressure_selected",
        }

    def _rewrite_selected_action(
        self,
        selected_engine,
        selected_action,
        runtime_policy,
        trend,
    ):
        runtime_health = str(
            runtime_policy.get("runtime_health", "")
        ).lower()

        retry_actions = self._safe_int(
            trend.get("retry_actions"),
            0,
        )

        instability_ratio = self._safe_float(
            trend.get("instability_ratio"),
            0.0,
        )

        action_lc = str(selected_action).lower()

        if (
            selected_engine == "policy"
            and action_lc == "retry"
            and runtime_health == "unstable"
            and retry_actions >= 3
        ):
            return "cooldown_repair"

        if (
            selected_engine == "policy"
            and instability_ratio >= 0.70
            and action_lc in {"mutate", "evolve", "mutation"}
        ):
            return "stabilize"

        return selected_action

    def _policy_pressure_score(
        self,
        runtime_policy,
        trend,
        action,
    ):
        score = 0.0

        runtime_health = str(
            runtime_policy.get("runtime_health", "")
        ).lower()

        instability_ratio = self._safe_float(
            trend.get("instability_ratio"),
            0.0,
        )

        retry_actions = self._safe_int(
            trend.get("retry_actions"),
            0,
        )

        throttled_cycles = self._safe_int(
            trend.get("throttled_cycles"),
            0,
        )

        action_lc = str(action).lower()

        if runtime_health == "unstable":
            score += 0.50

        if instability_ratio >= 0.60:
            score += 0.45

        if retry_actions >= 3:
            score += 0.35

        if throttled_cycles >= 2:
            score += 0.25

        if action_lc in {
            "throttle",
            "stabilize",
            "cooldown",
            "cooldown_repair",
            "diagnose_and_repair",
        }:
            score += 0.40

        return score

    def _repair_pressure_score(
        self,
        trend,
        action,
    ):
        score = 0.0

        retry_actions = self._safe_int(
            trend.get("retry_actions"),
            0,
        )

        action_lc = str(action).lower()

        if action_lc == "retry":
            score += 0.20

        if retry_actions >= 3 and action_lc == "retry":
            score -= 0.45

        return score

    def _safe_dict(
        self,
        value,
    ):
        return value if isinstance(value, dict) else {}

    def _safe_int(
        self,
        value,
        default=0,
    ):
        try:
            return int(value)
        except Exception:
            return default

    def _safe_float(
        self,
        value,
        default=0.0,
    ):
        try:
            return float(value)
        except Exception:
            return default