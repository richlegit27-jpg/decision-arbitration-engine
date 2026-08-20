from __future__ import annotations

from flask import Blueprint, jsonify, request

from nova_backend.services.session_detail_cache_service import (
    SessionDetailCacheService,
)


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

    @state_bp.route(
        "/api/state",
        methods=["GET"],
    )
    def api_state():

        sessions_data = session_store.load()

        if isinstance(
            sessions_data,
            list,
        ):

            sessions_data = {
                "sessions": {
                    str(
                        session.get("id")
                    ): session
                    for session in sessions_data
                    if isinstance(
                        session,
                        dict,
                    )
                    and session.get("id")
                }
            }

        artifacts = (
            artifact_store.all()
            if hasattr(
                artifact_store,
                "all",
            )
            else []
        )

        memory = (
            memory_store.all()
            if hasattr(
                memory_store,
                "all",
            )
            else []
        )

        active_session_id = (
            request.headers.get(
                "X-Session-ID"
            )
            or ""
        )

        if not active_session_id:

            if hasattr(
                session_store,
                "get_active_session_id",
            ):

                try:

                    active_session_id = (
                        session_store
                        .get_active_session_id()
                        or ""
                    )

                except Exception:

                    active_session_id = ""

        if not active_session_id:

            if isinstance(
                sessions_data,
                dict,
            ):

                active_session_id = (
                    sessions_data.get(
                        "active_session_id"
                    )
                    or ""
                )


        print(
            "STATE ROUTE ACTIVE SESSION:",
            active_session_id,
        )


        execution_state = {}


        # PRIMARY SOURCE
        # Session detail cache
        if active_session_id:

            try:

                detail_cache = SessionDetailCacheService()

                detail_store = (
                    detail_cache
                    .load_sessions_store()
                )


                print(
                    "DEBUG CACHE KEYS:",
                    list(detail_store.keys())[-10:]
                    if isinstance(
                        detail_store,
                        dict,
                    )
                    else "NOT DICT",
                )


                print(
                    "DEBUG LOOKING FOR SESSION:",
                    active_session_id,
                )


                cached_session = (
                    detail_store.get(
                        active_session_id
                    )
                    if isinstance(
                        detail_store,
                        dict,
                    )
                    else None
                )


                print(
                    "DEBUG CACHED SESSION FOUND:",
                    bool(cached_session),
                )


                if isinstance(
                    cached_session,
                    dict,
                ):

                    execution_state = (
                        cached_session.get(
                            "execution_state"
                        )
                        or cached_session.get(
                            "active_execution"
                        )
                        or {}
                    )


                print(
                    "DEBUG CACHE EXECUTION FOUND:",
                    execution_state,
                )


            except Exception as e:

                print(
                    "STATE CACHE ERROR:",
                    repr(e),
                )


        # EXECUTION SERVICE FALLBACK
        if (
            not execution_state
            and execution_state_service
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
                    "STATE EXECUTION SERVICE ERROR:",
                    repr(e),
                )


        # SESSION STORE FALLBACK
        if not execution_state:

            try:

                session = {}

                if isinstance(
                    sessions_data,
                    dict,
                ):

                    session = (
                        sessions_data
                        .get(
                            "sessions",
                            {},
                        )
                        .get(
                            active_session_id,
                            {},
                        )
                    )


                if isinstance(
                    session,
                    dict,
                ):

                    execution_state = (
                        session.get(
                            "execution_state"
                        )
                        or session.get(
                            "active_execution"
                        )
                        or {}
                    )


                    if not execution_state:

                        meta = session.get(
                            "meta",
                            {},
                        )


                        if isinstance(
                            meta,
                            dict,
                        ):

                            execution_state = (
                                meta.get(
                                    "execution_state"
                                )
                                or meta.get(
                                    "active_execution"
                                )
                                or {}
                            )


            except Exception as e:

                print(
                    "STATE SESSION ERROR:",
                    repr(e),
                )


        print(
            "DEBUG FINAL EXECUTION:",
            execution_state,
        )


        return jsonify(
            {
                "ok": True,
                "session_id": active_session_id,
                "session": sessions_data,
                "execution_state": execution_state,
                "active_execution": execution_state,
                "artifacts": artifacts,
                "memory": memory,
            }
        )


    app.register_blueprint(
        state_bp
    )