import hashlib
import secrets
from datetime import datetime, timedelta, timezone


class EmailVerificationService:

    def __init__(
        self,
        token_lifetime_hours=24,
    ):
        self.token_lifetime_hours = (
            token_lifetime_hours
        )

    def generate_token(self):

        return secrets.token_urlsafe(
            48
        )

    def hash_token(
        self,
        token,
    ):

        return hashlib.sha256(
            str(token).encode("utf-8")
        ).hexdigest()

    def create_verification(
        self,
    ):

        token = self.generate_token()

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(
                hours=self.token_lifetime_hours
            )
        )

        return {
            "token": token,
            "token_hash": self.hash_token(
                token
            ),
            "expires_at": expires_at.isoformat(),
        }

    def verify_token(
        self,
        token,
        stored_token_hash,
        expires_at,
    ):

        if not token:
            return False

        if not stored_token_hash:
            return False

        incoming_hash = self.hash_token(
            token
        )

        if not secrets.compare_digest(
            incoming_hash,
            str(stored_token_hash),
        ):
            return False

        try:

            expires = datetime.fromisoformat(
                str(expires_at)
            )

            if expires.tzinfo is None:

                expires = expires.replace(
                    tzinfo=timezone.utc
                )

            if datetime.now(
                timezone.utc
            ) > expires:

                return False

        except Exception:

            return False

        return True