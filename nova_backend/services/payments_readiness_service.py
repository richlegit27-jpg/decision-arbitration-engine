from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[2]


def _truthy_env(name: str) -> bool:
    value = (os.environ.get(name) or "").strip().lower()
    return value in {"1", "true", "yes", "on", "live"}


def _configured_env(name: str) -> bool:
    return bool((os.environ.get(name) or "").strip())


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _billing_account(username: str) -> Dict[str, Any]:
    try:
        from nova_backend.services.billing_service import get_account

        account = get_account(username)
        if isinstance(account, dict):
            return dict(account)
    except Exception:
        pass

    return {
        "plan": "free",
        "credits": 0,
        "monthly_credits": 0,
        "created_at": "",
        "stripe_customer_id": "",
    }


def _planned_plans() -> List[Dict[str, Any]]:
    return [
        {
            "id": "free",
            "label": "Free",
            "status": "local_active",
            "monthly_credits": 1000,
            "stripe_price_env": "",
            "stripe_price_configured": False,
        },
        {
            "id": "standard",
            "label": "Standard",
            "status": "planned",
            "monthly_credits": 10000,
            "stripe_price_env": "NOVA_STRIPE_STANDARD_PRICE_ID",
            "stripe_price_configured": _configured_env("NOVA_STRIPE_STANDARD_PRICE_ID"),
        },
        {
            "id": "pro",
            "label": "Pro",
            "status": "planned",
            "monthly_credits": 50000,
            "stripe_price_env": "NOVA_STRIPE_PRO_PRICE_ID",
            "stripe_price_configured": _configured_env("NOVA_STRIPE_PRO_PRICE_ID"),
        },
    ]


def _usage_enforcement_status() -> Dict[str, Any]:
    services = ROOT / "nova_backend" / "services"

    billing_text = _safe_read(
        services / "billing_service.py"
    ).lower()

    gateway_text = _safe_read(
        services / "model_gateway_service.py"
    ).lower()

    chat_text = _safe_read(
        services / "chat_service.py"
    ).lower()

    finalizer_text = _safe_read(
        services / "token_usage_finalize_service.py"
    ).lower()

    hosted_web_text = _safe_read(
        services / "hosted_web_search_service.py"
    ).lower()

    image_vision_text = _safe_read(
        services / "image_vision_service.py"
    ).lower()

    app_text = _safe_read(
        ROOT / "app.py"
    ).lower()

    gateway_usage_enforced = all(
        marker in gateway_text
        for marker in (
            "def chat_completions_create",
            "def responses_create",
            "consume_usage(",
            "_nova_preflight_credits(",
        )
    )

    chat_usage_enforced = (
        "responses_create(" in chat_text
        and "chat_completions_create(" in chat_text
        and "self.client.responses.create(" not in chat_text
    )

    hosted_web_usage_enforced = (
        "response = responses_create(" in hosted_web_text
        and "self.client.responses.create(" not in hosted_web_text
    )

    image_vision_usage_enforced = (
        "response = chat_completions_create("
        in image_vision_text
        and "client.chat.completions.create("
        not in image_vision_text
    )

    app_vision_usage_enforced = (
        "_nova_response = _nova_chat_completions_create("
        in app_text
        and "_nova_client.chat.completions.create("
        not in app_text
    )

    duplicate_finalize_billing = (
        "consume_usage(" in finalizer_text
    )

    active_model_paths_gateway_enforced = all(
        (
            chat_usage_enforced,
            hosted_web_usage_enforced,
            image_vision_usage_enforced,
            app_vision_usage_enforced,
        )
    )

    return {
        "billing_service_consume_usage_exists": (
            "def consume_usage" in billing_text
        ),
        "model_gateway_mentions_billing": (
            "billing_service" in gateway_text
            or "consume_usage" in gateway_text
        ),
        "chat_service_mentions_billing": (
            "responses_create(" in chat_text
            or "chat_completions_create(" in chat_text
        ),
        "gateway_usage_enforced": gateway_usage_enforced,
        "chat_usage_enforced": chat_usage_enforced,
        "hosted_web_usage_enforced": (
            hosted_web_usage_enforced
        ),
        "image_vision_usage_enforced": (
            image_vision_usage_enforced
        ),
        "app_vision_usage_enforced": (
            app_vision_usage_enforced
        ),
        "active_model_paths_gateway_enforced": (
            active_model_paths_gateway_enforced
        ),
        "duplicate_finalize_billing": (
            duplicate_finalize_billing
        ),
    }

def build_payments_readiness(username: str = "richard") -> Dict[str, Any]:
    clean_username = (username or "richard").strip() or "richard"
    account = _billing_account(clean_username)
    plans = _planned_plans()
    usage = _usage_enforcement_status()

    payments_live = _truthy_env("NOVA_PAYMENTS_LIVE")
    stripe_secret_configured = _configured_env("STRIPE_SECRET_KEY")
    stripe_webhook_secret_configured = _configured_env("STRIPE_WEBHOOK_SECRET")
    any_paid_price_configured = any(
        bool(plan.get("stripe_price_configured"))
        for plan in plans
        if plan.get("id") != "free"
    )

    blockers = []

    if not payments_live:
        blockers.append("NOVA_PAYMENTS_LIVE is not enabled.")

    if not stripe_secret_configured:
        blockers.append("STRIPE_SECRET_KEY is not configured.")

    if not stripe_webhook_secret_configured:
        blockers.append("STRIPE_WEBHOOK_SECRET is not configured.")

    if not any_paid_price_configured:
        blockers.append("No paid Stripe price IDs are configured.")

    if not usage.get("gateway_usage_enforced"):
        blockers.append(
            "Model gateway does not enforce billing credits yet."
        )

    if not usage.get(
        "active_model_paths_gateway_enforced"
    ):
        blockers.append(
            "One or more active model paths bypass billing enforcement."
        )

    if usage.get("duplicate_finalize_billing"):
        blockers.append(
            "Duplicate response-finalizer billing is still enabled."
        )

    checkout_ready = (
        payments_live
        and stripe_secret_configured
        and any_paid_price_configured
    )

    webhook_ready = (
        payments_live
        and stripe_webhook_secret_configured
    )

    live_ready = (
        checkout_ready
        and webhook_ready
        and usage.get(
            "gateway_usage_enforced"
        )
        and usage.get(
            "active_model_paths_gateway_enforced"
        )
        and not usage.get(
            "duplicate_finalize_billing"
        )
    )

    return {
        "mode": "live_ready" if live_ready else "staged_planned",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "username": clean_username,
        "account": {
            "plan": account.get("plan", "free"),
            "credits": int(account.get("credits", 0) or 0),
            "monthly_credits": int(account.get("monthly_credits", 0) or 0),
            "created_at": account.get("created_at", ""),
            "stripe_customer_configured": bool(account.get("stripe_customer_id")),
        },
        "payments": {
            "live_enabled": payments_live,
            "checkout_ready": checkout_ready,
            "webhook_ready": webhook_ready,
            "stripe_secret_configured": stripe_secret_configured,
            "stripe_webhook_secret_configured": stripe_webhook_secret_configured,
            "paid_price_configured": any_paid_price_configured,
            "portal_ready": checkout_ready,
        },
        "usage_enforcement": usage,
        "plans": plans,
        "blockers": blockers,
        "summary": {
            "safe_to_show_buttons": True,
            "safe_to_take_payment": live_ready,
            "checkout_route_should_be_staged": not checkout_ready,
            "webhook_route_should_be_noop": not webhook_ready,
            "next_patch": (
                "wire live Stripe checkout/webhook"
                if live_ready
                else "keep payment routes staged and add backend usage enforcement before going live"
            ),
        },
    }
