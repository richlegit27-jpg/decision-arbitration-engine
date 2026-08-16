from datetime import datetime
import uuid


class ExecutionEngine:

    def __init__(
        self,
        step_service=None,
    ):

        self.executions = {}

        self.step_service = (
            step_service
        )


    def create_plan(
        self,
        goal,
        steps=None,
    ):

        execution_id = (
            "exec_"
            + uuid.uuid4().hex[:12]
        )

        if not steps:
            steps = [
                {
                    "id": 1,
                    "task": goal,
                    "status": "pending",
                }
            ]

        else:
            normalized_steps = []

            for index, step in enumerate(
                steps,
                start=1,
            ):

                if isinstance(step, str):

                    normalized_steps.append(
                        {
                            "id": index,
                            "task": step,
                            "status": "pending",
                        }
                    )

                elif isinstance(step, dict):

                    step.setdefault(
                        "id",
                        index,
                    )

                    step.setdefault(
                        "status",
                        "pending",
                    )

                    normalized_steps.append(
                        step
                    )

            steps = normalized_steps


        execution = {
            "id": execution_id,
            "goal": goal,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "current_step": 0,
            "steps": steps,
        }


        self.executions[execution_id] = execution

        return execution


    def get(
        self,
        execution_id,
    ):

        return self.executions.get(
            execution_id,
            {},
        )


    def advance(
        self,
        execution_id,
    ):

        execution = self.get(
            execution_id
        )

        if not execution:
            return {}


        current = execution["current_step"]


        if current >= len(
            execution["steps"]
        ):

            execution["status"] = "complete"

            return execution


        step = execution["steps"][current]


        if self.step_service:

            self.step_service.execute_step_logic(
                session_id="",
                step=step,
            )


        if step.get("status") == "failed":

            execution["status"] = "failed"

            execution["error"] = (
                step.get("error")
                or "Execution step failed."
            )

            return execution


        step["status"] = "complete"

        execution["steps"][current] = step

        execution["current_step"] += 1


        if execution["current_step"] >= len(
            execution["steps"]
        ):

            execution["status"] = "complete"


        return execution


    def add_step(
        self,
        execution_id,
        task,
    ):

        execution = self.get(
            execution_id
        )

        if execution:

            execution["steps"].append(
                {
                    "id": len(
                        execution["steps"]
                    ) + 1,
                    "task": task,
                    "status": "pending",
                }
            )


        return execution


    def run(
        self,
        goal,
        steps=None,
    ):
        """
        Universal execution entry point.

        Creates an execution plan and advances
        through the initial execution lifecycle.
        """

        execution = self.create_plan(
            goal=goal,
            steps=steps,
        )


        if not execution:

            return {
                "status": "failed",
                "error": "Could not create execution plan.",
            }


        execution = self.advance(
            execution["id"]
        )


        return execution