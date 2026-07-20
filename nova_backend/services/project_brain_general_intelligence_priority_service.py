from __future__ import annotations


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
                ...
        except Exception as exc:
            print(
                "[NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701] install failed:",
                exc,
            )