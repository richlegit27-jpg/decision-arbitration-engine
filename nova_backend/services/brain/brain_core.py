class BrainCore:
    def __init__(self):
        pass

    def decide(self, brain_state: dict) -> str:

        text = (brain_state.get("input") or "").lower()
        execution = brain_state.get("execution", {})
        signals = brain_state.get("signals", {})

        if signals.get("is_failure_state"):
            return "retry_failed"

        if signals.get("is_continuation"):
            return "run_step"

        if text in {"run all", "run_all", "execute", "run it"}:
            return "run_all"

        if text in {"auto fix", "autofix", "apply_auto_fix"}:
            return "apply_auto_fix"

        if text in {"stop", "cancel"}:
            return "cancel"

        return "chat"

