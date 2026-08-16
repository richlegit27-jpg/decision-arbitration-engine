from nova_backend.routes.state_routes import register_state_routes


class StateRouteService:

    def install_routes(
        self,
        app,
        session_store,
        artifact_store,
        memory_store,
        execution_state_service=None,
    ):
        register_state_routes(
            app,
            session_store,
            artifact_store,
            memory_store,
            execution_state_service,
        )