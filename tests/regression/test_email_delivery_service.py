from __future__ import annotations

import pytest

from nova_backend.services.email_delivery_service import (
    EmailDeliveryError,
    EmailDeliveryService,
)


def test_account_email_links_use_public_url_and_put_token_in_fragment():
    service = EmailDeliveryService({
        "NOVA_SMTP_HOST": "smtp.example.test",
        "NOVA_EMAIL_FROM": "Nova <accounts@example.test>",
        "NOVA_PUBLIC_URL": "https://nova.example.test/",
    })
    sent = []
    service._send = lambda *args: sent.append(args)

    service.send_verification("user@example.test", "secret-token")
    service.send_password_reset("user@example.test", "reset-token")

    assert len(sent) == 2
    assert "https://nova.example.test/verify-email#token=secret-token" in sent[0][2]
    assert "https://nova.example.test/reset-password#token=reset-token" in sent[1][2]
    assert "secret-token" not in sent[0][1]


def test_email_delivery_fails_closed_without_configuration():
    service = EmailDeliveryService({})

    assert service.is_configured() is False
    with pytest.raises(EmailDeliveryError, match="not configured"):
        service.send_verification("user@example.test", "secret-token")
