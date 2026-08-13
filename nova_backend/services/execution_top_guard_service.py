class ExecutionTopGuardService:

    def handle(
        self,
        payload,
        session_id,
        **services
    ):
        return {
            "handled": False
        }


execution_top_guard_service = ExecutionTopGuardService()