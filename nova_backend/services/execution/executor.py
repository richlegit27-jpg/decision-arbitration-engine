class Executor:
    """
    Executes actions decided by BrainCore.
    """

    def __init__(self):
        pass

    def execute(self, action: str, context: dict = None):

        context = context or {}

        if action == "run_step":
            return {"status": "running_step"}

        if action == "run_all":
            return {"status": "running_all"}

        if action == "retry_failed":
            return {"status": "retrying"}

        if action == "apply_auto_fix":
            return {"status": "auto_fix"}

        if action == "cancel":
            return {"status": "cancelled"}

        return {"status": "chat"}