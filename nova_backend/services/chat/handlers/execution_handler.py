class ExecutionHandler:

    def __init__(self, service):
        self.service = service

    def handle(
        self,
        user_text,
        session_id,
    ):
        execution_service = getattr(
            self.service,
            "execution_service",
            None,
        )

        if not execution_service:
            raise RuntimeError(
                "ExecutionService not attached to ChatService"
            )

        print(
            "DEBUG EXECUTION SERVICE CLASS =",
            type(execution_service),
        )

        print(
            "DEBUG HAS PROCESS GOAL PLAN =",
            hasattr(
                execution_service,
                "_process_goal_and_plan",
            ),
        )

        execution_state = (
            execution_service._process_goal_and_plan(
                user_text,
                session_id,
            )
        )

        print(
            "DEBUG PROCESS GOAL PLAN RETURN =",
            execution_state,
        )

        return execution_state