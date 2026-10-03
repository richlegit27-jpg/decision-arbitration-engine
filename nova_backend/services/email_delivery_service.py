from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode, urlsplit


class EmailDeliveryError(RuntimeError):
    pass


class EmailDeliveryService:
    """Small SMTP adapter for transactional account emails."""

    def __init__(self, environ=None):
        values = os.environ if environ is None else environ
        self.host = str(values.get("NOVA_SMTP_HOST") or "").strip()
        self.port = int(values.get("NOVA_SMTP_PORT") or 587)
        self.username = str(values.get("NOVA_SMTP_USERNAME") or "")
        self.password = str(values.get("NOVA_SMTP_PASSWORD") or "")
        self.from_email = str(values.get("NOVA_EMAIL_FROM") or "").strip()
        self.public_url = str(values.get("NOVA_PUBLIC_URL") or "").strip().rstrip("/")
        self.use_ssl = str(values.get("NOVA_SMTP_USE_SSL") or "").lower() in {
            "1", "true", "yes", "on"
        }
        self.use_starttls = str(values.get("NOVA_SMTP_STARTTLS", "1")).lower() in {
            "1", "true", "yes", "on"
        }

    def is_configured(self) -> bool:
        if not (self.host and self.from_email and self.public_url):
            return False
        try:
            parsed = urlsplit(self.public_url)
        except ValueError:
            return False
        production = (
            str(os.environ.get("RAILWAY_ENVIRONMENT") or "").lower() == "production"
            or str(os.environ.get("FLASK_ENV") or "").lower() == "production"
        )
        return bool(
            parsed.hostname
            and parsed.scheme in ({"https"} if production else {"http", "https"})
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
        )

    def _url(self, path: str, token: str) -> str:
        if not self.is_configured():
            raise EmailDeliveryError("Transactional email is not configured.")
        return f"{self.public_url}{path}#{urlencode({'token': token})}"

    def _send(self, recipient: str, subject: str, body: str) -> None:
        if not self.is_configured():
            raise EmailDeliveryError("Transactional email is not configured.")

        message = EmailMessage()
        message["From"] = self.from_email
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        try:
            if self.use_ssl:
                with smtplib.SMTP_SSL(
                    self.host,
                    self.port,
                    timeout=20,
                    context=ssl.create_default_context(),
                ) as client:
                    self._authenticate(client)
                    client.send_message(message)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=20) as client:
                    client.ehlo()
                    if self.use_starttls:
                        client.starttls(context=ssl.create_default_context())
                        client.ehlo()
                    self._authenticate(client)
                    client.send_message(message)
        except Exception as exc:
            # Provider errors can contain message contents or credentials.
            raise EmailDeliveryError(
                f"Transactional email delivery failed ({type(exc).__name__})."
            ) from exc

    def _authenticate(self, client) -> None:
        if self.username:
            client.login(self.username, self.password)

    def send_verification(self, recipient: str, token: str) -> None:
        link = self._url("/verify-email", token)
        self._send(
            recipient,
            "Verify your Nova account",
            f"Verify your email address to finish creating your Nova account:\n\n{link}\n\n"
            "This link expires in 24 hours and can be used once.",
        )

    def send_password_reset(self, recipient: str, token: str) -> None:
        link = self._url("/reset-password", token)
        self._send(
            recipient,
            "Reset your Nova password",
            f"Use this link to reset your Nova password:\n\n{link}\n\n"
            "This link expires in one hour and can be used once. If you did not request it, ignore this email.",
        )
