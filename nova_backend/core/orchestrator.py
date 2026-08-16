class NovaOrchestrator:


    def __init__(
        self,
        router=None,
        context_engine=None,
        memory=None,
        project_brain=None,
        execution_engine=None,
    ):

        self.router = router
        self.context_engine = context_engine
        self.memory = memory
        self.project_brain = project_brain
        self.execution_engine = execution_engine



    def process(
        self,
        text,
        session=None,
    ):

        context = {}

        if self.context_engine:

            context = self.context_engine.build(
                session=session
            )


        decision = {
            "route": "general_chat",
            "action": "respond",
        }


        if self.router:

            decision.update(
                self.router.decide(
                    text,
                    context,
                )
            )


        route = decision.get(
            "route"
        )


        if route == "memory":

            return {
                "type": "memory",
                "decision": decision,
                "context": context,
            }


        if route == "continuity":

            return {
                "type": "continuity",
                "decision": decision,
                "context": context,
            }


        if route == "execution":

            return {
                "type": "execution",
                "decision": decision,
                "context": context,
            }


        return {
            "type": "chat",
            "decision": decision,
            "context": context,
        }