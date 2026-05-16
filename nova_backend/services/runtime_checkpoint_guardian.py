class RuntimeCheckpointGuardian:

    def __init__(self):

        self.checkpoints = []

    def create_checkpoint(
        self,
        execution_state=None,
        runtime_result=None,
        reason=None,
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

        checkpoint = {
            "checkpoint_id": (
                f"checkpoint_"
                f"{len(self.checkpoints) + 1}"
            ),
            "reason": reason,
            "execution_state": dict(
                execution_state
            ),
            "runtime_signal": (
                execution_state.get(
                    "runtime_signal"
                )
            ),
            "final_action": (
                runtime_result.get(
                    "final_action"
                )
            ),
        }

        self.checkpoints.append(
            checkpoint
        )

        self.checkpoints = (
            self.checkpoints[-10:]
        )

        return {
            "ok": True,
            "checkpoint": checkpoint,
        }

    def latest_checkpoint(
        self,
    ):

        if not self.checkpoints:

            return {
                "ok": False,
                "checkpoint": None,
            }

        return {
            "ok": True,
            "checkpoint": (
                self.checkpoints[-1]
            ),
        }

    def restore_latest(
        self,
    ):

        latest = self.latest_checkpoint()

        checkpoint = latest.get(
            "checkpoint"
        )

        if not checkpoint:

            return {
                "ok": False,
                "restored": False,
            }

        return {
            "ok": True,
            "restored": True,
            "execution_state": (
                checkpoint.get(
                    "execution_state",
                    {},
                )
            ),
            "checkpoint": checkpoint,
        }