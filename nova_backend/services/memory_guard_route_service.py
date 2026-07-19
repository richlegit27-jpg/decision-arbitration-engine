from flask import jsonify, request

class MemoryGuardRouteService:

    def __init__(self, memory_service, session_service, memory_guard_service):
        self.memory_service = memory_service
        self.session_service = session_service
        self.memory_guard_service = memory_guard_service

    def install_routes(self, app):

        @app.before_request
        def nova_before_request_explicit_memory_guard_20260611():
            try:
                if request.path not in (
                    "/api/chat",
                    "/api/chat/stream",
                ) or request.method != "POST":
                    return None

                payload = request.get_json(silent=True) or {}

                return self.memory_guard_service.handle_explicit_memory_guard(
                    payload,
                    self.memory_service,
                    self.session_service,
                    jsonify,
                    app.logger,
                )

            except Exception:
                return None


        @app.before_request
        def nova_before_request_favorite_recall_guard_20260611():
            try:
                if request.path not in (
                    "/api/chat",
                    "/api/chat/stream",
                ) or request.method != "POST":
                    return None

                payload = request.get_json(silent=True) or {}

                return self.memory_guard_service.handle_favorite_recall_guard(
                    payload,
                    self.memory_service,
                    self.session_service,
                    jsonify,
                    app.logger,
                )

            except Exception:
                return None


        @app.before_request
        def nova_before_request_memory_summary_guard_20260611():
            try:
                if request.path not in (
                    "/api/chat",
                    "/api/chat/stream",
                ) or request.method != "POST":
                    return None

                payload = request.get_json(silent=True) or {}

                return self.memory_guard_service.handle_memory_summary_guard(
                    payload,
                    self.memory_service,
                    self.session_service,
                    jsonify,
                    app.logger,
                )

            except Exception:
                return None