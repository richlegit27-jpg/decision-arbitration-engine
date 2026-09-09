from __future__ import annotations


class ExecutionPlanNormalizer:
    """
    Converts conceptual planner steps into execution-ready
    Nova execution steps.

    The planner remains responsible for deciding WHAT should
    happen. This normalizer translates that decision into a
    structure the execution system can consume.
    """


    def normalize(
        self,
        plan,
    ):

        if not isinstance(plan, dict):

            return {
                "goal": "",
                "steps": [],
                "status": "invalid_plan",
            }


        goal = str(
            plan.get("goal")
            or plan.get("mission")
            or ""
        ).strip()


        original_steps = (
            plan.get("steps")
            or []
        )


        normalized_steps = []


        for index, step in enumerate(
            original_steps,
            start=1,
        ):

            normalized_step = (
                self.normalize_step(
                    step,
                    index=index,
                    goal=goal,
                )
            )


            if normalized_step:

                normalized_steps.append(
                    normalized_step
                )


        normalized_plan = dict(plan)

        normalized_plan["goal"] = goal

        normalized_plan["steps"] = (
            normalized_steps
        )

        normalized_plan["execution_ready"] = True


        return normalized_plan


    def normalize_step(
        self,
        step,
        index=1,
        goal="",
    ):

        if isinstance(step, str):

            step = {
                "description": step,
            }


        if not isinstance(step, dict):

            return None


        normalized = dict(step)


        action = str(
            normalized.get("action")
            or normalized.get("tool_name")
            or normalized.get("step")
            or ""
        ).strip().lower()


        description = str(
            normalized.get("description")
            or normalized.get("title")
            or normalized.get("input")
            or ""
        ).strip()


        normalized["id"] = (
            normalized.get("id")
            or index
        )

        normalized["status"] = (
            normalized.get("status")
            or "pending"
        )

        normalized["goal"] = goal


        if not isinstance(
            normalized.get("payload"),
            dict,
        ):

            normalized["payload"] = {}


        conceptual_actions = {

            "understand": {
                "action": "planning",
            },

            "analyze": {
                "action": "planning",
            },

            "analysis": {
                "action": "planning",
            },

            "plan": {
                "action": "planning",
            },

            "planning": {
                "action": "planning",
            },

            "implement": {
                "action": "implementation",
            },

            "execution": {
                "action": "implementation",
            },

            "complete": {
                "action": "implementation",
            },

            "verify": {
                "action": "validation",
            },

            "validation": {
                "action": "validation",
            },

            "review": {
                "action": "validation",
            },

        }


        mapped = conceptual_actions.get(
            action
        )


        if mapped:

            normalized["action"] = (
                mapped["action"]
            )

        else:

            normalized["action"] = action


        normalized.setdefault(
            "description",
            description,
        )


        normalized.setdefault(
            "title",
            description
            or action
            or f"Step {index}",
        )


        normalized.setdefault(
            "execution_mode",
            "planner",
        )


        return normalized