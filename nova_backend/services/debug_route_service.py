class DebugRouteService:

    def install_routes(self, app):

        def debug_routes_enabled():
            try:
                import os

                value = str(
                    os.getenv("NOVA_DEBUG_ROUTES", "")
                ).strip().lower()

                return value in {
                    "1",
                    "true",
                    "yes",
                    "on",
                    "enabled",
                }

            except Exception:
                return False


        def debug_routes_disabled_response():
            try:
                from flask import jsonify

                return jsonify(
                    {
                        "ok": False,
                        "error": "Debug routes are disabled. Set NOVA_DEBUG_ROUTES=1 to enable.",
                    }
                ), 404

            except Exception:
                return {
                    "ok": False,
                    "error": "Debug routes are disabled. Set NOVA_DEBUG_ROUTES=1 to enable.",
                }, 404


        @app.route("/api/debug/chat-turn-shadow", methods=["GET"])
        def api_debug_chat_turn_shadow():

            try:
                if not debug_routes_enabled():
                    return debug_routes_disabled_response()

                from flask import jsonify
                from nova_backend.services.chat_service import ChatService

                return jsonify(
                    ChatService.get_global_chat_turn_shadow_snapshot()
                )

            except Exception as error:
                try:
                    from flask import jsonify

                    return jsonify(
                        {
                            "ok": False,
                            "error": str(error),
                        }
                    ), 500

                except Exception:
                    return {
                        "ok": False,
                        "error": str(error),
                    }, 500