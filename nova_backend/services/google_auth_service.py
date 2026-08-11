import os

from authlib.integrations.flask_client import OAuth


class GoogleAuthService:

    def __init__(
        self,
        app,
    ):
        self.app = app
        self.oauth = OAuth(app)

        self.google = None

        self._setup()

    def _setup(self):

        client_id = os.getenv(
            "GOOGLE_CLIENT_ID"
        )

        client_secret = os.getenv(
            "GOOGLE_CLIENT_SECRET"
        )

        if not client_id or not client_secret:
            print(
                "[GOOGLE AUTH] Missing credentials"
            )
            return

        self.google = self.oauth.register(
            name="google",
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url=(
                "https://accounts.google.com/.well-known/openid-configuration"
            ),
            client_kwargs={
                "scope": "openid email profile",
            },
        )

        print(
            "[GOOGLE AUTH] installed"
        )

    def enabled(self):
        return self.google is not None