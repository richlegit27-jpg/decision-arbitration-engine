class PlannerBridge:

    def __init__(
        self,
        planner_service=None,
    ):
        self.planner_service = planner_service

    def create_plan(
        self,
        goal,
        context=None,
    ):
        plan = {
            "goal": goal,
            "steps": [],
            "status": "created",
            "context": context or {},
        }

        if self.planner_service:
            try:
                generated = self.planner_service.plan(
                    goal,
                    context,
                )

                if isinstance(
                    generated,
                    dict,
                ):
                    plan.update(
                        generated
                    )

            except Exception as exc:
                plan["error"] = str(exc)
                plan["status"] = "planner_failed"

        if not plan["steps"]:
            plan["steps"] = [
                {
                    "action": "analysis",
                    "title": "Analyze project goal and requirements",
                    "input": goal,
                },
                {
                    "action": "planning",
                    "title": "Create project phases and milestones",
                    "input": goal,
                },
                {
                    "action": "execution",
                    "title": "Define tasks, priorities, and timeline",
                    "input": goal,
                },
                {
                    "action": "validation",
                    "title": "Review risks and success criteria",
                    "input": goal,
                },
            ]

        return plan