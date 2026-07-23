import json
from pathlib import Path
from datetime import datetime, timezone

class OnboardingService:

    VERSION = 1
    USER_ONBOARDING_FILE = Path("data/nova_user_onboarding.json")

    def get_state(self, session):
        if not isinstance(session, dict):
            return "new"

        meta = session.get("meta") or {}
        onboarding = meta.get("onboarding") or {}

        return str(
            onboarding.get("state") or "new"
        )

    def should_show_welcome(self, session):
        return self.get_state(session) == "new"

    def build_welcome_message(self):
        return (
            "Welcome to Nova.\n\n"
            "I'm your AI workspace. I can help you answer questions, "
            "plan projects, analyze files, work with files, and create things.\n\n"
            "What would you like to do first?"
        )

    def build_returning_message(self):
        return (
            "Welcome back to Nova.\n\n"
            "What are we working on today?"
        )

    def should_show_returning_message(self, session):
        if not isinstance(session, dict):
            return False

        meta = session.get("meta") or {}
        onboarding = meta.get("onboarding") or {}

        return onboarding.get("returning_greeting_seen") is not True

    def build_welcome_actions(self):
        return [
            {
                "id": "ask_question",
                "label": "Ask a question",
                "prompt": "I want to ask a question. Help me get started.",
            },
            {
                "id": "plan_project",
                "label": "Plan something",
                "prompt": "I want to plan something. Help me figure out the next steps.",
            },
            {
                "id": "upload_file",
                "label": "Upload a file",
                "prompt": "I want to upload a file. Help me understand what I can do with it.",
            },
            {
                "id": "start_build",
                "label": "Build something",
                "prompt": "I want to build something. Help me decide where to start.",
            },
        ]
    def build_onboarding_patch(self):
        return {
            "onboarding": {
                "state": "complete",
                "version": self.VERSION,
                "completed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
        }

    def user_key(self, user_id):
        return f"onboarding:{str(user_id or '').strip()}"

    def should_show_user_welcome(self, user_meta):
        if not isinstance(user_meta, dict):
            return True

        return not bool(
            user_meta.get("onboarding_complete")
        )

    def build_user_onboarding_patch(self):
        return {
            "onboarding_complete": True,
            "onboarding_version": self.VERSION,
            "onboarding_completed_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    def load_user_state(self, user_id):
        if not user_id:
            return {}

        try:
            if not self.USER_ONBOARDING_FILE.exists():
                return {}

            data = json.loads(
                self.USER_ONBOARDING_FILE.read_text(
                    encoding="utf-8"
                )
            )

            return data.get(str(user_id), {})

        except Exception:
            return {}

    def load_user_state(self, user_id):
        if not user_id:
            return {}

        try:
            self.USER_ONBOARDING_FILE.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            data = {}

            if self.USER_ONBOARDING_FILE.exists():
                data = json.loads(
                    self.USER_ONBOARDING_FILE.read_text(
                        encoding="utf-8"
                    )
                )

            current = data.get(str(user_id), {})
            current.update(patch)

            data[str(user_id)] = current

            self.USER_ONBOARDING_FILE.write_text(
                json.dumps(
                    data,
                    indent=2,
                ),
                encoding="utf-8",
            )

            return current

        except Exception:
            return {}