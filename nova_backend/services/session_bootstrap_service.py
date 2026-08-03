from datetime import datetime, timezone
from flask import g, session as flask_session
from nova_backend.services.onboarding_service import OnboardingService


def _now_iso():
    try:
        return datetime.now(timezone.utc).isoformat()
    except Exception:
        return ""


class SessionBootstrapService:

    def __init__(self, session_service, logger=None):
        self.session_service = session_service
        self.logger = logger
        self.onboarding_service = OnboardingService()


    def ensure_requested_session(
        self,
        session_id,
        title="Mobile Chat",
    ):
        target_session_id = str(session_id or "").strip()

        if not target_session_id:
            return None

        try:
            existing = self.session_service.get_session(
                target_session_id,
            )

            if existing:
                try:
                    self.session_service.set_active(
                        target_session_id
                    )
                except Exception:
                    if self.logger:
                        self.logger.exception(
                            "[mobile-session-save] failed preserving existing session"
                        )

                return existing

        except Exception:
            if self.logger:
                self.logger.exception(
                    "[mobile-session-save] failed checking existing session"
                )

        owner_id = ""

        try:
            auth_user = getattr(g, "nova_auth_user", None) or {}

            owner_id = str(
                auth_user.get("id")
                or flask_session.get("nova_user_id")
                or ""
            ).strip()

        except Exception:
            owner_id = ""

        now = _now_iso()

        new_session = {
            "id": target_session_id,
            "title": str(title or "Mobile Chat").strip()[:80] or "Mobile Chat",
            "user_id": owner_id,
            "messages": [],
            "pinned": False,
            "created_at": now,
            "updated_at": now,
            "working_state": {
                "active_task": "",
                "current_file": "",
                "current_bug": "",
                "last_success": "",
                "next_move": "",
                "checkpoint": "",
                "updated_at": "",
            },
            "active_execution": None,
        }

        # NOVA_SESSION_BOOTSTRAP_ONBOARDING_ATTACH_20260728
        try:
            onboarding_patch = (
                self.onboarding_service.build_user_onboarding_patch()
            )

            if isinstance(onboarding_patch, dict):
                new_session["meta"] = onboarding_patch

        except Exception:
            if self.logger:
                self.logger.exception(
                    "[mobile-session-save] onboarding patch failed"
                )

        try:
            store = self.session_service._read_store()

            if not isinstance(store, dict):
                store = {
                    "active_session_id": "",
                    "sessions": [],
                }

            sessions = store.get("sessions")

            if not isinstance(sessions, list):
                sessions = []

            sessions = [
                item
                for item in sessions
                if isinstance(item, dict)
                and str(item.get("id") or "").strip()
                != target_session_id
            ]

            sessions.insert(0, new_session)

            store["sessions"] = sessions
            store["active_session_id"] = target_session_id

            self.session_service.save(
                sessions,
                active=target_session_id,
            )

            return new_session

        except Exception:
            if self.logger:
                self.logger.exception(
                    "[mobile-session-save] failed creating requested session"
                )

            return new_session


    def resolve_chat_session(
        self,
        session_id,
        data,
        user_text,
        auth_user_id="",
    ):
        force_new_session = bool(
            data.get("force_new_session")
            or data.get("new_session")
        )

        requested_session_id = str(
            session_id or ""
        ).strip()

        if requested_session_id and not force_new_session:
            try:
                existing = self.session_service.get_session(
                    requested_session_id,
                    user_id=auth_user_id,
                )
            except TypeError:
                existing = self.session_service.get_session(
                    requested_session_id
                )
            except Exception:
                existing = None

            if existing:
                try:
                    self.session_service.set_active(
                        requested_session_id,
                        user_id=auth_user_id,
                    )
                except TypeError:
                    try:
                        self.session_service.set_active(
                            requested_session_id
                        )
                    except Exception:
                        pass
                except Exception:
                    pass

                return requested_session_id

            created = self.ensure_requested_session(
                requested_session_id,
                title="New Chat",
            )

            if isinstance(created, dict):
                created_id = str(
                    created.get("id") or ""
                ).strip()

                if created_id:
                    return created_id

            return requested_session_id

        if not force_new_session:
            try:
                active = self.session_service.get_active()

                if active:
                    active_session_id = str(
                        active.get("id") or ""
                    ).strip()

                    if active_session_id:
                        return active_session_id

            except Exception:
                if self.logger:
                    self.logger.exception(
                        "[session-bootstrap] active "
                        "session lookup failed"
                    )

        created = self.session_service.create_session(
            "New Chat",
            user_id=auth_user_id,
        )

        return str(
            created.get("id") or ""
        ).strip()

