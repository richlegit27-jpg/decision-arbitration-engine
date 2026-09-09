from flask import jsonify, request


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

                if isinstance(
                    auth_user,
                    dict,
                ):
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
                    or ""
                ).strip()

                if user_id:
                    try:
                        from nova_backend.services.session_auth_scope_service import (
                            current_auth_user,
                        )

                        user = current_auth_user()

                        if isinstance(
                            user,
                            dict,
                        ):
                            return {
                                "user_id": str(
                                    user.get("id")
                                    or user_id
                                ).strip(),
                                "username": str(
                                    user.get("username")
                                    or ""
                                ).strip(),
                            }

                    except Exception:
                        pass

                    return {
                        "user_id": user_id,
                        "username": "",
                    }

            except Exception:
                pass

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

                customer_id = str(
                    account.get(
                        "stripe_customer_id",
                        "",
                    )
                ).strip()

                if not customer_id:

                    customer = create_customer(
                        username=username,
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

                origin = str(
                    request.headers.get(
                        "Origin",
                        "",
                    )
                ).strip()

                if not origin:
                    origin = str(
                        request.host_url
                    ).rstrip("/")

                success_url = (
                    origin
                    + "/billing?checkout=success"
                )

                cancel_url = (
                    origin
                    + "/billing?checkout=cancelled"
                )

                checkout = create_checkout_session(
                    price_id=price_id,
                    success_url=success_url,
                    cancel_url=cancel_url,
                    customer_id=customer_id,
                    username=username,
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
                    cancel_subscription,
                    plan_from_price_id,
                    set_subscription,
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

                if event_type == (
                    "checkout.session.completed"
                ):

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

                    if username and plan != "free":

                        set_subscription(
                            username,
                            subscription_id,
                            plan,
                        )

                        print(
                            "[NOVA STRIPE SUBSCRIPTION ACTIVATED]",
                            username,
                            plan,
                        )


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

                    if username:

                        cancel_subscription(
                            username
                        )

                        print(
                            "[NOVA STRIPE SUBSCRIPTION CANCELLED]",
                            username,
                            subscription_id,
                        )


                return _nova_payments_json(
                    {
                        "ok": True,
                        "received": True,
                        "event_type": event_type,
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
