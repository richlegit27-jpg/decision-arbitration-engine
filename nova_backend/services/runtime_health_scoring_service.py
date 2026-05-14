# C:\Users\Owner\nova\nova_backend\services\runtime_health_scoring_service.py

class RuntimeHealthScoringService:
    def __init__(
        self,
    ):
        pass

    def score(
        self,
        execution_state=None,
        runtime_result=None,
        runtime_history=None,
    ):
        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        runtime_result = (
            runtime_result
            if isinstance(runtime_result, dict)
            else {}
        )

        runtime_history = (
            runtime_history
            if isinstance(runtime_history, list)
            else []
        )

        health_score = 100
        warnings = []

        runtime_signal = (
            execution_state.get("runtime_signal")
            or runtime_result.get("runtime_signal")
            or ""
        )

        if "error" in str(runtime_signal).lower():
            health_score -= 25
            warnings.append("Runtime signal contains error.")

        if execution_state.get("recovery_mode"):
            health_score -= 20
            warnings.append("Runtime is in recovery mode.")

        if runtime_result.get("runtime_integrity", {}).get("blocked"):
            health_score -= 30
            warnings.append("Runtime integrity blocked execution.")

        if runtime_result.get("runtime_consensus", {}).get("blocked"):
            health_score -= 20
            warnings.append("Runtime consensus blocked execution.")

        recent_recovery_count = 0

        for item in runtime_history[-10:]:
            if not isinstance(item, dict):
                continue

            if item.get("recovery_mode"):
                recent_recovery_count += 1

        if recent_recovery_count >= 3:
            health_score -= 15
            warnings.append("Repeated recovery mode detected recently.")

        health_score = max(0, min(100, health_score))

        if health_score >= 85:
            health_state = "healthy"
        elif health_score >= 65:
            health_state = "watch"
        elif health_score >= 40:
            health_state = "degraded"
        else:
            health_state = "critical"

        return {
            "ok": True,
            "health_score": health_score,
            "health_state": health_state,
            "warnings": warnings,
            "recent_recovery_count": recent_recovery_count,
            "runtime_signal": runtime_signal,
        }