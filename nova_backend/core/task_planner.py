class TaskPlanner:


    def __init__(self):
        self.active_plans = []


    def create_plan(
        self,
        goal,
        context=None,
    ):

        plan = {
            "goal": goal,
            "status": "planning",
            "steps": self._generate_steps(
                goal
            ),
            "current_step": 0,
            "context": context or {},
        }


        self.active_plans.append(
            plan
        )

        return plan



    def _generate_steps(
        self,
        goal,
    ):

        goal = str(goal)


        return [
            {
                "id": 1,
                "name": "Understand objective",
                "status": "pending",
            },
            {
                "id": 2,
                "name": "Gather requirements",
                "status": "pending",
            },
            {
                "id": 3,
                "name": "Create solution",
                "status": "pending",
            },
            {
                "id": 4,
                "name": "Test result",
                "status": "pending",
            },
            {
                "id": 5,
                "name": "Finalize output",
                "status": "pending",
            },
        ]



    def advance(
        self,
        plan,
    ):

        current = plan.get(
            "current_step",
            0,
        )

        steps = plan.get(
            "steps",
            [],
        )


        if current < len(steps):

            steps[current]["status"] = "complete"

            plan["current_step"] += 1


        if plan["current_step"] >= len(steps):
            plan["status"] = "complete"


        return plan



    def get_active_plans(self):

        return self.active_plans