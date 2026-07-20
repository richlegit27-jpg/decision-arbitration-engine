from __future__ import annotations


class ProjectStateDirectFreshnessPriorityService:

    def __init__(self, execution_state_service=None):
        self.execution_state_service = execution_state_service

    def install(self, app):
        self._install_guard(app)
        return app

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

                    payload = request.get_json(silent=True) or {}

                    if not isinstance(payload, dict):
                        return None

                    from nova_backend.services.project_state_direct_freshness_bridge import (
                        build_project_state_direct_fresh_response,
                    )

                    response_json = build_project_state_direct_fresh_response(
                        payload
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