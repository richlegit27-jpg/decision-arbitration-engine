from flask import jsonify, request


from urllib.parse import urlsplit


def register_payments_routes(app):

    try:

        def _nova_payments_route_exists(rule_text):
            try:
                return any(
                    str(rule) == rule_text
                    for rule in app.url_map.iter_rules()
                )
            except Exception:
                return False

        def _nova_payments_current_user():
            try:
                from flask import g, session

                auth_user = getattr(
                    g,
                    "nova_auth_user",
                    None,
                )

                if isinstance(auth_user, dict):
                    user_id = str(
                        auth_user.get("id")
                        or auth_user.get("user_id")
                        or ""
                    ).strip()

                    username = str(
                        auth_user.get("username")
                        or ""
                    ).strip()

                    if user_id:
                        return {
                            "user_id": user_id,
                            "username": username,
                        }

                user_id = str(
                    session.get("nova_user_id")
                    or session.get("user_id")
                    or ""
                ).strip()

                username = str(
                    session.get("username")
                    or ""
                ).strip()

                if user_id:
                    return {
                        "user_id": user_id,
                        "username": username,
                    }

                from nova_backend.services.auth_context import (
                    get_current_user_id,
                )

                user_id = str(
                    get_current_user_id() or ""
                ).strip()

                return {
                    "user_id": user_id,
                    "username": username,
                }

            except Exception:
                return {
                    "user_id": "",
                    "username": "",
                }

        def _nova_payments_current_username():
            current_user = (
                _nova_payments_current_user()
            )

            return str(
                current_user.get(
                    "username",
                    "",
                )
                or ""
            ).strip()

        def _nova_payments_json(
            payload,
            status_code=200,
        ):
            response = jsonify(payload)
            response.status_code = status_code
            return response


        if not _nova_payments_route_exists(
            "/api/billing/readiness"
        ):

            @app.get("/api/billing/readiness")
            def nova_billing_readiness_api():

                from nova_backend.services.payments_readiness_service import (
                    build_payments_readiness,
                )

                current_user = (
                    _nova_payments_current_user()
                )

                user_id = str(
                    current_user.get(
                        "user_id",
                        "",
                    )
                    or ""
                ).strip()

                username = str(
                    current_user.get(
                        "username",
                        "",
                    )
                    or ""
                ).strip()

                if not user_id:

                    return _nova_payments_json(
                        {
                            "ok": False,
                            "error": (
                                "Authentication is required."
                            ),
                        },
                        401,
                    )

                data = build_payments_readiness(
                    username=username,
                    user_id=user_id,
                )

                return _nova_payments_json(
                    {
                        "ok": True,
                        **data,
                    }
                )

        if not _nova_payments_route_exists(
            "/api/billing/plans"
        ):

            @app.get("/api/billing/plans")
            def nova_billing_plans_api():

                from nova_backend.services.payments_readiness_service import (
                    build_payments_readiness,
                )

                username = (
                    _nova_payments_current_username()
                )

                data = build_payments_readiness(
                    username=username
                )

                return _nova_payments_json(
                    {
                        "ok": True,
                        "plans": data.get(
                            "plans",
                            [],
                        ),
                        "payments": data.get(
                            "payments",
                            {},
                        ),
                    }
                )


        if not _nova_payments_route_exists(
            "/api/billing/account"
        ):

            @app.get("/api/billing/account")
            def nova_billing_account_api():

                from nova_backend.services.billing_service import (
                    get_account,
                    get_account_summary,
                )

                current_user = (
                    _nova_payments_current_user()
                )

                user_id = str(
                    current_user.get(
                        "user_id",
                        "",
                    )
                    or ""
                ).strip()

                username = str(
                    current_user.get(
                        "username",
                        "",
                    )
                    or ""
                ).strip()

                if not user_id:
                    return _nova_payments_json(
                        {
                            "ok": False,
                            "error": (
                                "Authentication is required "
                                "to start checkout."
                            ),
                        },
                        401,
                    )

                account = get_account(
                    username=username,
                    user_id=user_id,
                )

                summary = get_account_summary(
                    username=username,
                    user_id=user_id,
                )

                return _nova_payments_json(
                    {
                        "ok": True,
                        "username": username,
                        "account": account,
                        "summary": summary,
                    }
                )


        if not _nova_payments_route_exists(
            "/api/billing/checkout"
        ):

            @app.post("/api/billing/checkout")
            def nova_billing_checkout_api():

                data = request.get_json(
                    silent=True
                ) or {}

                plan = str(
                    data.get("plan") or ""
                ).strip().lower()

                if plan not in (
                    "plus",
                    "pro",
                ):
                    return _nova_payments_json(
                        {
                            "ok": False,
                            "error": "Invalid billing plan.",
                        },
                        400,
                    )

                import os

                from nova_backend.services.billing_service import (
                    get_account,
                    plan_from_price_id,
                    set_stripe_customer_id,
                )

                from nova_backend.services.stripe_service import (
                    create_checkout_session,
                    create_customer,
                    stripe_is_configured,
                )

                if not stripe_is_configured():

                    return _nova_payments_json(
                        {
                            "ok": False,
                            "error": (
                                "Stripe is not configured."
                            ),
                        },
                        503,
                    )
                current_user = (
                    _nova_payments_current_user()
                )

                user_id = str(
                    current_user.get(
                        "user_id",
                        "",
                    )
                    or ""
                ).strip()

                username = str(
                    current_user.get(
                        "username",
                        "",
                    )
                    or ""
                ).strip()

                if not user_id:

                    return _nova_payments_json(
                        {
                            "ok": False,
                            "error": (
                                "Authentication is required "
                                "to start checkout."
                            ),
                        },
                        401,
                    )

                account = get_account(
                    username=username,
                    user_id=user_id,
                )

                price_env = (
                    "NOVA_STRIPE_PLUS_PRICE_ID"
                    if plan == "plus"
                    else "NOVA_STRIPE_PRO_PRICE_ID"
                )

                price_id = str(
                    os.environ.get(
                        price_env,
                        "",
                    )
                ).strip()

                if not price_id:

                    return _nova_payments_json(
                        {
                            "ok": False,
                            "error": (
                                f"Stripe price ID is not configured "
                                f"for the {plan} plan."
                            ),
                        },
                        503,
                    )

                resolved_plan = plan_from_price_id(
                    price_id
                )

                if resolved_plan != plan:

                    return _nova_payments_json(
                        {
                            "ok": False,
                            "error": (
                                "Stripe plan configuration mismatch."
                            ),
                        },
                        500,
                    )

                public_base_url = str(
                    os.environ.get("NOVA_PUBLIC_URL")
                    or app.config.get("NOVA_PUBLIC_URL")
                    or ""
                ).strip().rstrip("/")
                is_production = (
                    str(os.environ.get("FLASK_ENV") or "").lower() == "production"
                    or str(os.environ.get("RAILWAY_ENVIRONMENT") or "").lower() == "production"
                )
                if not public_base_url:
                    if is_production:
                        return _nova_payments_json(
                            {
                                "ok": False,
                                "error": "Billing return URL is not configured.",
                            },
                            503,
                        )
                    public_base_url = str(request.host_url).rstrip("/")

                parsed_public_url = urlsplit(public_base_url)
                if (
                    parsed_public_url.scheme not in ("http", "https")
                    or not parsed_public_url.netloc
                    or parsed_public_url.username
                    or parsed_public_url.password
                    or parsed_public_url.query
                    or parsed_public_url.fragment
                    or parsed_public_url.path not in ("", "/")
                    or (is_production and parsed_public_url.scheme != "https")
                ):
                    return _nova_payments_json(
                        {
                            "ok": False,
                            "error": "Billing return URL configuration is invalid.",
                        },
                        503,
                    )

                customer_id = str(
                    account.get(
                        "stripe_customer_id",
                        "",
                    )
                ).strip()

                if not customer_id:

                    customer = create_customer(
                        username=username,
                        user_id=user_id,
                    )

                    customer_id = str(
                        customer.get("id") or ""
                    ).strip()

                    if not customer_id:

                        return _nova_payments_json(
                            {
                                "ok": False,
                                "error": (
                                    "Could not create Stripe customer."
                                ),
                            },
                            500,
                        )

                    set_stripe_customer_id(
                        username=username,
                        user_id=user_id,
                        customer_id=customer_id,
                    )

                success_url = (
                    public_base_url
                    + "/billing?checkout=success"
                )

                cancel_url = (
                    public_base_url
                    + "/billing?checkout=cancelled"
                )

                checkout = create_checkout_session(
                    price_id=price_id,
                    success_url=success_url,
                    cancel_url=cancel_url,
                    customer_id=customer_id,
                    username=username,
                    user_id=user_id,
                )

                checkout_url = str(
                    checkout.get("url") or ""
                ).strip()

                if not checkout_url:

                    return _nova_payments_json(
                        {
                            "ok": False,
                            "error": (
                                "Stripe did not return a checkout URL."
                            ),
                        },
                        500,
                    )

                return _nova_payments_json(
                    {
                        "ok": True,
                        "plan": plan,
                        "checkout_url": checkout_url,
                    }
                )


        if not _nova_payments_route_exists(
            "/api/billing/webhook"
        ):

            @app.post("/api/billing/webhook")
            def nova_billing_webhook_api():

                import json

                from nova_backend.services.billing_service import (
                    plan_from_price_id,
                    process_stripe_subscription_event,
                    stripe_event_was_processed,
                )

                from nova_backend.services.stripe_service import (
                    verify_webhook,
                )

                payload = request.get_data()

                signature = str(
                    request.headers.get(
                        "Stripe-Signature",
                        "",
                    )
                ).strip()

                if not signature:

                    return _nova_payments_json(
                        {
                            "ok": False,
                            "error": (
                                "Missing Stripe signature."
                            ),
                        },
                        400,
                    )

                try:

                    event = verify_webhook(
                        payload,
                        signature,
                    )

                except Exception as exc:

                    print(
                        "[NOVA STRIPE WEBHOOK VERIFY ERROR]",
                        repr(exc),
                    )

                    return _nova_payments_json(
                        {
                            "ok": False,
                            "error": (
                                "Invalid Stripe webhook."
                            ),
                        },
                        400,
                    )

                event_id = str(event.get("id") or "").strip()
                if not event_id:
                    return _nova_payments_json(
                        {
                            "ok": False,
                            "error": "Stripe event ID is missing.",
                        },
                        400,
                    )

                if stripe_event_was_processed(event_id):
                    return _nova_payments_json({
                        "ok": True,
                        "received": True,
                        "duplicate": True,
                        "event_type": str(event.get("type") or ""),
                    })

                event_type = str(
                    event.get("type") or ""
                ).strip()

                event_data = event.get(
                    "data",
                    {}
                )

                event_object = {}

                if isinstance(
                    event_data,
                    dict,
                ):
                    event_object = event_data.get(
                        "object",
                        {},
                    )

                if not isinstance(
                    event_object,
                    dict,
                ):
                    event_object = {}

                metadata = event_object.get(
                    "metadata",
                    {},
                )

                if not isinstance(
                    metadata,
                    dict,
                ):
                    metadata = {}

                username = str(
                    metadata.get(
                        "nova_username",
                        "",
                    )
                ).strip()
                user_id = str(
                    metadata.get("nova_user_id", "")
                ).strip()
                event_action = "ignore"
                subscription_id = ""
                plan = ""

                if event_type in (
                    "checkout.session.completed",
                    "checkout.session.async_payment_succeeded",
                ):

                    payment_status = str(
                        event_object.get("payment_status") or ""
                    ).strip().lower()
                    mode = str(
                        event_object.get("mode") or ""
                    ).strip().lower()

                    if not username:
                        username = str(
                            event_object.get(
                                "client_reference_id",
                                "",
                            )
                        ).strip()

                    subscription_id = str(
                        event_object.get(
                            "subscription",
                            "",
                        )
                    ).strip()

                    price_id = str(
                        metadata.get(
                            "nova_price_id",
                            "",
                        )
                    ).strip()

                    plan = plan_from_price_id(
                        price_id
                    )

                    if (
                        mode == "subscription"
                        and payment_status in ("paid", "no_payment_required")
                        and
                        (user_id or username)
                        and subscription_id
                        and plan in ("plus", "pro")
                    ):

                        event_action = "activate"


                elif event_type in (
                    "customer.subscription.deleted",
                    "customer.subscription.paused",
                ):

                    subscription_id = str(
                        event_object.get(
                            "id",
                            "",
                        )
                    ).strip()

                    if user_id or username:

                        event_action = "cancel"

                elif event_type == "customer.subscription.updated":
                    subscription_id = str(
                        event_object.get("id") or ""
                    ).strip()
                    subscription_status = str(
                        event_object.get("status") or ""
                    ).strip().lower()
                    items = event_object.get("items")
                    item_data = (
                        items.get("data", [])
                        if isinstance(items, dict)
                        else []
                    )
                    first_item = (
                        item_data[0]
                        if isinstance(item_data, list) and item_data
                        and isinstance(item_data[0], dict)
                        else {}
                    )
                    price = first_item.get("price")
                    price_id = str(
                        price.get("id") or ""
                        if isinstance(price, dict)
                        else price or ""
                    ).strip()
                    plan = plan_from_price_id(price_id)

                    if (
                        user_id or username
                    ) and subscription_id:
                        if subscription_status == "active" and plan in ("plus", "pro"):
                            event_action = "activate"
                        elif subscription_status in {
                            "canceled",
                            "unpaid",
                            "paused",
                            "incomplete_expired",
                        }:
                            event_action = "cancel"


                event_result = process_stripe_subscription_event(
                    event_id=event_id,
                    action=event_action,
                    username=username,
                    user_id=user_id,
                    plan=plan,
                    subscription_id=subscription_id,
                )
                return _nova_payments_json(
                    {
                        "ok": True,
                        "received": True,
                        "event_type": event_type,
                        "processed": event_result["processed"],
                        "duplicate": event_result["duplicate"],
                    }
                )


        if not _nova_payments_route_exists(
            "/admin/billing-readiness"
        ):

            @app.get("/admin/billing-readiness")
            def nova_admin_billing_readiness():

                from nova_backend.services.payments_readiness_service import (
                    build_payments_readiness,
                )

                username = (
                    _nova_payments_current_username()
                )

                data = build_payments_readiness(
                    username=username
                )

                return (
                    "<h1>Nova Billing Readiness</h1>"
                    f"<pre>{data}</pre>"
                )


        print(
            "[NOVA PAYMENTS ROUTES] installed"
        )


    except Exception as exc:

        print(
            "[NOVA PAYMENTS ROUTES] failed:",
            exc,
        )
