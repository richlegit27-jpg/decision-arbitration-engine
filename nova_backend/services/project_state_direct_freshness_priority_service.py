from __future__ import annotations


class ProjectStateDirectFreshnessPriorityService:

    def __init__(
        self,
        execution_state_service=None,
        chat_execution_service=None,
    ):
        self.execution_state_service = (
            execution_state_service
        )
        self.chat_execution_service = (
            chat_execution_service
        )

    def install(self, app):
        self._install_guard(app)
        return app

    def _has_active_execution(
        self,
        payload,
    ):
        if not isinstance(payload, dict):
            return False

        session_id = str(
            payload.get("session_id")
            or payload.get("active_session_id")
            or ""
        ).strip()

        if not session_id:
            return False

        service = self.execution_state_service

        if service is not None:
            get_execution_state = getattr(
                service,
                "get_execution_state",
                None,
            )

            if callable(get_execution_state):
                try:
                    execution_state = (
                        get_execution_state(
                            session_id
                        )
                    )
                except Exception:
                    execution_state = {}

                execution_is_active = getattr(
                    service,
                    "execution_is_active",
                    None,
                )

                if callable(execution_is_active):
                    try:
                        if execution_is_active(
                            execution_state
                        ):
                            return True
                    except Exception:
                        pass

        chat_service = self.chat_execution_service

        if chat_service is not None:
            refresh_states = getattr(
                chat_service,
                "_load_states",
                None,
            )

            if callable(refresh_states):
                try:
                    refresh_states()
                except Exception:
                    pass
            get_state = getattr(
                chat_service,
                "get_state",
                None,
            )

            if callable(get_state):
                try:
                    chat_state = get_state(
                        session_id
                    )
                except Exception:
                    chat_state = {}

                if isinstance(chat_state, dict):
                    goal = str(
                        chat_state.get("goal") or ""
                    ).strip()

                    status = str(
                        chat_state.get("status") or ""
                    ).strip().lower()

                    complete = (
                        chat_state.get("complete")
                        is True
                    )

                    if (
                        goal
                        and not complete
                        and status
                        not in {
                            "idle",
                            "complete",
                            "completed",
                            "done",
                            "failed",
                            "error",
                            "cancelled",
                            "canceled",
                        }
                    ):
                        return True

        return False

    def _install_guard(self, app):
        try:
            from flask import jsonify, request

            @app.before_request
            def _nova_project_state_direct_freshness_priority_20260720():
                try:
                    if request.path != "/api/chat":
                        return None

                    if request.method != "POST":
                        return None

                    payload = (
                        request.get_json(
                            silent=True
                        )
                        or {}
                    )

                    if not isinstance(payload, dict):
                        return None

                    if self._has_active_execution(
                        payload
                    ):
                        return None

                    from nova_backend.services.project_state_direct_freshness_bridge import (
                        build_project_state_direct_fresh_response,
                    )

                    response_json = (
                        build_project_state_direct_fresh_response(
                            payload
                        )
                    )

                    if not response_json:
                        return None

                    return jsonify(response_json)

                except Exception as exc:
                    print(
                        "[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_PRIORITY_20260720] bypass:",
                        exc,
                    )
                    return None

            print(
                "[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_PRIORITY_20260720] installed"
            )

        except Exception as exc:
            print(
                "[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_PRIORITY_20260720] failed:",
                exc,
            )