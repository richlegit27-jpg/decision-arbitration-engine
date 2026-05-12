class StrategyEngine:
    """
    Handles simple decision refinement rules.
    (kept lightweight for now)
    """

    def __init__(self):
        pass

    def select(self, brain_state: dict, action: str) -> str:

        execution = brain_state.get("execution", {})
        status = execution.get("status")

        # failure overrides everything
        if status == "failed":
            return "retry_failed"

        return action