from __future__ import annotations

from flask import Blueprint, jsonify, request


state_bp = Blueprint(
    "state_bp",
    __name__,
)


def register_state_routes(
    app,
    session_store,
    artifact_store,
    memory_store,
    execution_state_service=None,
):

    @state_bp.route("/api/state", methods=["GET"])
    def api_state():

        sessions_data = session_store.load()

        artifacts = (
            artifact_store.all()
            if hasattr(artifact_store, "all")
            else []
        )

        memory = (
            memory_store.all()
            if hasattr(memory_store, "all")
            else []
        )

        active_session_id = (
            request.headers.get("X-Session-ID")
            or ""
        )

        if (
            not active_session_id
            and hasattr(
                session_store,
                "get_active_session_id",
            )
        ):

            try:

                active_session_id = (
                    session_store
                    .get_active_session_id()
                    or ""
                )

            except Exception:

                active_session_id = ""

        if (
            not active_session_id
            and isinstance(
                sessions_data,
                dict,
            )
        ):

            active_session_id = (
                sessions_data
                .get("active_session_id")
                or ""
            )

        print(
            "STATE ROUTE ACTIVE SESSION:",
            active_session_id,
        )

        execution_state = {}

        if (
            execution_state_service
            and active_session_id
        ):

            try:

                execution_state = (
                    execution_state_service
                    .get_execution_state(
                        active_session_id
                    )
                    or {}
                )

            except Exception as e:

                print(
                    "STATE EXECUTION LOAD FAILED:",
                    repr(e),
                )

                execution_state = {}


        print(
            "[STATE ROUTE EXECUTION RETURN]",
            execution_state,
        )


        return jsonify(
            {
                "ok": True,
                "session": sessions_data,
                "execution_state": execution_state,
                "active_execution": execution_state,
                "artifacts": artifacts,
                "memory": memory,
            }
        )


    app.register_blueprint(state_bp)