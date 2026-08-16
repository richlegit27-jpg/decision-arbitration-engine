class NovaPipeline:


    def __init__(
        self,
        context,
        router,
        brain
    ):

        self.context=context
        self.router=router
        self.brain=brain



    def process(
        self,
        text,
        session=None
    ):

        ctx=self.context.build(
            session=session
        )


        route=self.router.decide(
            text,
            ctx
        )


        self.brain.decide(
            route
        )


        return {
            "context":ctx,
            "route":route,
            "brain":self.brain.snapshot()
        }