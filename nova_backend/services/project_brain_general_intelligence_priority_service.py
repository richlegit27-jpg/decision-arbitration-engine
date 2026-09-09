from __future__ import annotations

from flask import request


class ProjectBrainGeneralIntelligencePriorityService:

    def __init__(
        self,
        execution_state_service=None,
        chat_service=None,
    ):
        self.execution_state_service = execution_state_service
        self.chat_service = chat_service

    def install(self, app):

        self._install_guard(app)

        return app

    def _install_guard(self, app):

        try:

            @app.before_request
            def _nova_project_brain_general_intelligence_priority_20260701():

                path = str(
                    request.path or ""
                ).strip()

                method = str(
                    request.method or ""
                ).upper()

                # -------------------------------------------------
                # HARD API ROUTE BYPASS
                #
                # Project Brain intelligence routing must never
                # intercept normal Flask API endpoints.
                # -------------------------------------------------

                if path.startswith("/api/tools"):

                    return None

                if path.startswith("/api/health"):

                    return None

                if path.startswith("/api/auth"):

                    return None

                if path.startswith("/api/models"):

                    return None

                if path.startswith("/api/state"):

                    return None

                if path.startswith("/api/memory"):

                    return None

                if path.startswith("/api/sessions"):

                    return None

                if path.startswith("/api/chats"):

                    return None

                if path.startswith("/api/files"):

                    return None

                if path.startswith("/api/uploads"):

                    return None

                if path.startswith("/api/projects"):

                    return None

                if path.startswith("/api/kb"):

                    return None

                if path.startswith("/api/routes"):

                    return None

                # -------------------------------------------------
                # Only allow Project Brain interception for chat
                # intelligence requests.
                # -------------------------------------------------

                allowed_paths = (
                    "/api/chat",
                    "/api/chat/",
                )

                if not any(
                    path.startswith(prefix)
                    for prefix in allowed_paths
                ):

                    return None

                # Do not interfere with non-POST chat helpers.

                if method not in (
                    "POST",
                ):

                    return None

                # -------------------------------------------------
                # Existing Project Brain routing continues below.
                #
                # IMPORTANT:
                # If your original file contains additional logic
                # below this point, preserve that logic here.
                # -------------------------------------------------

                return None

        except Exception as exc:

            print(
                "[NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701] "
                "install failed:",
                exc,
            )