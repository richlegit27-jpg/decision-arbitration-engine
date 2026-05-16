class RuntimeResponseSanitizerService:
    """
    Keeps internal runtime/session/artifact state from flooding chat responses.

    Goal:
        Preserve the assistant message.
        Preserve minimal session identity.
        Preserve artifacts only as lightweight references.
        Strip giant internal payloads from conversational API responses.
    """

    def _safe_dict(self, value):
        if isinstance(value, dict):
            return value
        return {}

    def _safe_list(self, value):
        if isinstance(value, list):
            return value
        return []

    def _safe_str(self, value):
        if value is None:
            return ""

        try:
            return str(value).strip()
        except Exception:
            return ""

    def sanitize_artifact(self, artifact):
        artifact = self._safe_dict(artifact)

        return {
            "id": artifact.get("id"),
            "title": artifact.get("title"),
            "kind": artifact.get("kind"),
            "type": artifact.get("type"),
            "summary": artifact.get("summary"),
            "preview": artifact.get("preview"),
            "image_url": artifact.get("image_url"),
            "video_url": artifact.get("video_url"),
            "audio_url": artifact.get("audio_url"),
            "created_at": artifact.get("created_at"),
            "updated_at": artifact.get("updated_at"),
        }

    def sanitize_session(self, session):
        session = self._safe_dict(session)

        return {
            "id": session.get("id"),
            "title": session.get("title"),
            "updated_at": session.get("updated_at"),
            "pinned": session.get("pinned", False),
            "message_count": len(
                self._safe_list(
                    session.get("messages")
                )
            ),
        }

    def sanitize(self, payload):
        payload = self._safe_dict(payload)

        assistant_message = self._safe_dict(
            payload.get("assistant_message")
        )

        session = self.sanitize_session(
            payload.get("session")
        )

        artifacts = [
            self.sanitize_artifact(artifact)
            for artifact in self._safe_list(
                payload.get("artifacts")
            )
        ]

        return {
            "ok": payload.get("ok", True),
            "assistant_message": assistant_message,
            "session": session,
            "active_session_id": (
                payload.get("active_session_id")
                or session.get("id")
            ),
            "saved_artifact": self.sanitize_artifact(
                payload.get("saved_artifact")
            )
            if payload.get("saved_artifact")
            else None,
            "artifacts": artifacts[:25],
            "debug": self._safe_dict(
                payload.get("debug")
            ),
        }