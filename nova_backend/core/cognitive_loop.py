class CognitiveLoop:


    def __init__(
        self,
        context_engine=None,
        planner=None,
        executor=None,
        evaluator=None,
        reflector=None,
        memory=None,
    ):

        self.context_engine = context_engine
        self.planner = planner
        self.executor = executor
        self.evaluator = evaluator
        self.reflector = reflector
        self.memory = memory


        self.cycles = []



    def run(
        self,
        goal,
        context=None,
    ):

        cycle = {
            "goal": goal,
            "status": "started",
        }


        # 1. Understand

        if self.context_engine:

            context = (
                self.context_engine.build(
                    goal,
                    context=context,
                )
            )


        cycle["context"] = context



        # 2. Plan

        plan = None

        if self.planner:

            plan = (
                self.planner.create_plan(
                    goal,
                    context=context,
                )
            )


        cycle["plan"] = plan



        # 3. Execute

        result = None

        if self.executor and plan:

            result = (
                self.executor.execute(
                    plan
                )
            )


        cycle["result"] = result



        # 4. Evaluate

        evaluation = None

        if self.evaluator:

            evaluation = (
                self.evaluator.evaluate(
                    goal,
                    result,
                    context,
                )
            )


        cycle["evaluation"] = evaluation



        # 5. Reflect

        reflection = None

        if self.reflector:

            reflection = (
                self.reflector.reflect(
                    goal,
                    result,
                    evaluation,
                    context,
                )
            )


        cycle["reflection"] = reflection



        # 6. Store learning

        if self.memory and reflection:

            self.memory.consolidate(
                [
                    {
                        "text": str(reflection)
                    }
                ],
                context=context,
            )


        cycle["status"] = "complete"


        self.cycles.append(
            cycle
        )


        return cycle



    def history(self):

        return self.cycles