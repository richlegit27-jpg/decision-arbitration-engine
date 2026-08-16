class PlannerEngine:


    def __init__(self):

        self.plans = []



    def create_plan(
        self,
        goal,
        context=None,
    ):

        goal = str(goal).strip()


        plan = {
            "goal": goal,
            "status": "created",
            "steps": self._generate_steps(goal),
            "context": context or {},
        }


        self.plans.append(plan)

        return plan



    def _generate_steps(
        self,
        goal,
    ):

        goal_lower = goal.lower()


        if "build" in goal_lower:

            return [
                {
                    "step": 1,
                    "task": "Analyze requirements",
                    "status": "pending",
                },
                {
                    "step": 2,
                    "task": "Design architecture",
                    "status": "pending",
                },
                {
                    "step": 3,
                    "task": "Implement system",
                    "status": "pending",
                },
                {
                    "step": 4,
                    "task": "Test and improve",
                    "status": "pending",
                },
            ]


        return [
            {
                "step": 1,
                "task": goal,
                "status": "pending",
            }
        ]



    def get_plans(self):

        return self.plans