

import json
import os
import tempfile
import threading
from contextlib import contextmanager

from datetime import datetime, timezone
from pathlib import Path


BILLING_FILE = Path(
    "data/nova_billing.json"
)

BILLING_LOCK = threading.RLock()
_BILLING_PROCESS_LOCK_STATE = threading.local()


@contextmanager
def _billing_process_lock():
    lock_file_path = BILLING_FILE.with_name(
        f".{BILLING_FILE.name}.lock"
    )

    lock_file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(lock_file_path, "a+b") as lock_file:
        lock_file.seek(0, os.SEEK_END)

        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()

        lock_file.seek(0)

        if os.name == "nt":
            import msvcrt

            msvcrt.locking(
                lock_file.fileno(),
                msvcrt.LK_LOCK,
                1,
            )
        else:
            import fcntl

            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_EX,
            )

        try:
            yield
        finally:
            lock_file.seek(0)

            if os.name == "nt":
                msvcrt.locking(
                    lock_file.fileno(),
                    msvcrt.LK_UNLCK,
                    1,
                )
            else:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_UN,
                )

def _billing_mutation_lock(function):
    def wrapped(*args, **kwargs):
        with BILLING_LOCK:
            depth = getattr(
                _BILLING_PROCESS_LOCK_STATE,
                "depth",
                0,
            )

            if depth:
                _BILLING_PROCESS_LOCK_STATE.depth = depth + 1

                try:
                    return function(
                        *args,
                        **kwargs,
                    )
                finally:
                    _BILLING_PROCESS_LOCK_STATE.depth = depth

            with _billing_process_lock():
                _BILLING_PROCESS_LOCK_STATE.depth = 1

                try:
                    return function(
                        *args,
                        **kwargs,
                    )
                finally:
                    _BILLING_PROCESS_LOCK_STATE.depth = 0


    return wrapped

MODEL_COSTS = {
    "gpt-4o-mini": 1,
    "gpt-4.1": 10,
    "gpt-5": 25,
    "gpt-5.4": 25,
    "nova-fast": 1,
    "nova-smart": 25,
    "nova-vision": 1,
    "nova-coding": 25,
}


PLAN_CREDITS = {
    "free": 10000,
    "plus": 500000,
    "pro": 2000000,
}


DEFAULT_USER = {
    "plan": "free",
    "credits": PLAN_CREDITS["free"],
    "monthly_credits": PLAN_CREDITS["free"],
    "created_at": "",
    "stripe_customer_id": "",
    "subscription_id": "",
}

@_billing_mutation_lock
def _default_account(
    user_id="",
    username="",
):
    return {
        **DEFAULT_USER,
        "user_id": _normalize_user_id(
            user_id
        ),
        "username": _normalize_username(
            username
        ),
    }

@_billing_mutation_lock
def _now():
    return datetime.now(
        timezone.utc
    ).isoformat()

@_billing_mutation_lock
def _normalize_username(
    username,
):
    return str(
        username or ""
    ).strip().lower()

@_billing_mutation_lock
def _normalize_user_id(
    user_id,
):
    return str(
        user_id or ""
    ).strip()

@_billing_mutation_lock
def _resolve_billing_identity(
    user_id=None,
    username=None,
):
    normalized_user_id = _normalize_user_id(
        user_id
    )
    normalized_username = _normalize_username(
        username
    )

    if normalized_user_id:
        return normalized_user_id

    if normalized_username:
        return normalized_username

    return "unknown"

@_billing_mutation_lock
def _load():
    if not BILLING_FILE.exists():

        BILLING_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        _save(
            {
                "users": {},
            }
        )

    try:

        data = json.loads(
            BILLING_FILE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            data,
            dict,
        ):
            return {
                "users": {},
            }

        if not isinstance(
            data.get("users"),
            dict,
        ):
            data["users"] = {}

        if not isinstance(
            data.get("transactions"),
            list,
        ):
            data["transactions"] = []

        return data

    except Exception as exc:

        raise RuntimeError(
            f"Nova billing ledger could not be loaded: {BILLING_FILE}"
        ) from exc

@_billing_mutation_lock
def plan_from_price_id(price_id):
    import os

    price_id = str(
        price_id
        or ""
    ).strip()

    if not price_id:
        return ""

    plus_price_id = str(
        os.environ.get(
            "NOVA_STRIPE_PLUS_PRICE_ID",
            "",
        )
        or ""
    ).strip()

    pro_price_id = str(
        os.environ.get(
            "NOVA_STRIPE_PRO_PRICE_ID",
            "",
        )
        or ""
    ).strip()

    if (
        plus_price_id
        and price_id == plus_price_id
    ):
        return "plus"

    if (
        pro_price_id
        and price_id == pro_price_id
    ):
        return "pro"

    return ""

def _save(
    data,
):
    BILLING_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = json.dumps(
        data,
        indent=2,
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=BILLING_FILE.parent,
        prefix=f".{BILLING_FILE.name}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_file.write(payload)
        temp_path = Path(
            temp_file.name
        )

    try:
        os.replace(
            temp_path,
            BILLING_FILE,
        )
    except Exception:
        try:
            temp_path.unlink(
                missing_ok=True
            )
        except Exception:
            pass
        raise

def _record_transaction(
    data,
    transaction_type,
    user_id="",
    username="",
    amount=0,
    balance_after=0,
    model="",
    input_tokens=0,
    output_tokens=0,
    meta=None,
):
    import uuid

    transactions = data.setdefault(
        "transactions",
        [],
    )

    transaction = {
        "id": f"txn_{uuid.uuid4().hex}",
        "timestamp": _now(),
        "type": str(
            transaction_type or ""
        ).strip(),
        "user_id": _normalize_user_id(
            user_id
        ),
        "username": _normalize_username(
            username
        ),
        "amount": int(
            amount or 0
        ),
        "balance_after": int(
            balance_after or 0
        ),
        "model": str(
            model or ""
        ).strip(),
        "input_tokens": int(
            input_tokens or 0
        ),
        "output_tokens": int(
            output_tokens or 0
        ),
        "meta": (
            meta
            if isinstance(meta, dict)
            else {}
        ),
    }

    transactions.append(
        transaction
    )

    return transaction

@_billing_mutation_lock
def get_account(
    username=None,
    user_id=None,
):
    identity = _resolve_billing_identity(
        user_id=user_id,
        username=username,
    )

    data = _load()

    account = data["users"].setdefault(
        identity,
        _default_account(
            user_id=user_id,
            username=username,
        ),
    )

    normalized_user_id = _normalize_user_id(
        user_id
    )

    normalized_username = _normalize_username(
        username
    )

    data = _load()

    changed = False

    # Identity migration:
    # Older Nova billing records may have been stored using the
    # username as the key. When the authenticated user_id becomes
    # available, adopt that existing account instead of creating
    # a second free account.
    if (
        identity not in data["users"]
        and normalized_user_id
        and normalized_username
        and normalized_username in data["users"]
    ):
        legacy_account = data["users"].pop(
            normalized_username
        )

        data["users"][identity] = legacy_account

        changed = True

    if identity not in data["users"]:

        data["users"][identity] = (
            _default_account(
                user_id=user_id,
                username=username,
            )
        )

        changed = True

    account = data["users"][identity]

    if (
        normalized_user_id
        and account.get("user_id") != normalized_user_id
    ):
        account["user_id"] = normalized_user_id
        changed = True

    if (
        normalized_username
        and account.get("username") != normalized_username
    ):
        account["username"] = normalized_username
        changed = True

    if changed:
        _save(data)

    return account

@_billing_mutation_lock
def set_stripe_customer_id(
    username=None,
    user_id=None,
    customer_id="",
):
    identity = _resolve_billing_identity(
        user_id=user_id,
        username=username,
    )

    data = _load()

    account = data["users"].setdefault(
        identity,
        _default_account(
            user_id=user_id,
            username=username,
        ),
    )

    account["stripe_customer_id"] = str(
        customer_id or ""
    ).strip()

    normalized_user_id = _normalize_user_id(
        user_id
    )

    normalized_username = _normalize_username(
        username
    )

    if normalized_user_id:
        account["user_id"] = normalized_user_id

    if normalized_username:
        account["username"] = normalized_username

    _save(data)

    return dict(account)

@_billing_mutation_lock
def get_account_summary(
    username=None,
    user_id=None,
):
    account = get_account(
        username=username,
        user_id=user_id,
    )

    identity = _resolve_billing_identity(
        user_id=user_id,
        username=username,
    )

    data = _load()

    transactions = [
        transaction
        for transaction in data.get(
            "transactions",
            [],
        )
        if (
            transaction.get(
                "user_id",
                "",
            )
            == _normalize_user_id(user_id)
            or (
                not _normalize_user_id(user_id)
                and transaction.get(
                    "username",
                    "",
                )
                == _normalize_username(username)
            )
        )
    ]

    transactions.sort(
        key=lambda transaction: transaction.get(
            "timestamp",
            "",
        ),
        reverse=True,
    )

    usage_transactions = [
        transaction
        for transaction in transactions
        if transaction.get("type") == "usage"
    ]

    credits_used = sum(
        abs(
            int(
                transaction.get(
                    "amount",
                    0,
                )
            )
        )
        for transaction in usage_transactions
    )

    return {
        "identity": identity,
        "plan": account.get(
            "plan",
            "free",
        ),
        "credits": int(
            account.get(
                "credits",
                0,
            )
        ),
        "monthly_credits": int(
            account.get(
                "monthly_credits",
                0,
            )
        ),
        "credits_used": credits_used,
        "transaction_count": len(
            transactions
        ),
        "recent_transactions": transactions[:10],
        "created_at": account.get(
            "created_at",
            "",
        ),
    }

@_billing_mutation_lock
def get_balance(
    username=None,
    user_id=None,
):
    account = get_account(
        username=username,
        user_id=user_id,
    )

    return int(
        account.get(
            "credits",
            0,
        )
    )

@_billing_mutation_lock
def set_subscription(
    username=None,
    plan="",
    subscription_id="",
    user_id=None,
):
    plan = str(plan or "").strip().lower()
    subscription_id = str(subscription_id or "").strip()

    if plan not in ("plus", "pro") or not subscription_id:
        raise ValueError("A valid subscription plan and ID are required.")

    identity = _resolve_billing_identity(
        user_id=user_id,
        username=username,
    )

    data = _load()

    account = data["users"].setdefault(
        identity,
        _default_account(
            user_id=user_id,
            username=username,
        ),
    )

    account["plan"] = plan
    account["subscription_id"] = subscription_id
    account["monthly_credits"] = int(PLAN_CREDITS[plan])

    normalized_user_id = _normalize_user_id(user_id)
    normalized_username = _normalize_username(username)

    if normalized_user_id:
        account["user_id"] = normalized_user_id

    if normalized_username:
        account["username"] = normalized_username

    _save(data)

    return dict(account)


@_billing_mutation_lock
def cancel_subscription(
    username=None,
    user_id=None,
    subscription_id="",
):
    identity = _resolve_billing_identity(
        user_id=user_id,
        username=username,
    )

    data = _load()
    account = data["users"].get(identity)

    if account is None:
        return None

    requested_subscription_id = str(
        subscription_id or ""
    ).strip()

    stored_subscription_id = str(
        account.get("subscription_id", "") or ""
    ).strip()

    # Ignore stale cancellation events for an older subscription.
    if (
        requested_subscription_id
        and stored_subscription_id
        and requested_subscription_id != stored_subscription_id
    ):
        return dict(account)

    account["plan"] = "free"
    account["subscription_id"] = ""
    account["monthly_credits"] = int(PLAN_CREDITS["free"])

    _save(data)

    return dict(account)


@_billing_mutation_lock
def add_credits(
    username=None,
    amount=0,
    user_id=None,
):
    identity = _resolve_billing_identity(
        user_id=user_id,
        username=username,
    )

    data = _load()

    account = data["users"].setdefault(
        identity,
        _default_account(
            user_id=user_id,
            username=username,
        ),
    )

    normalized_user_id = _normalize_user_id(
        user_id
    )

    normalized_username = _normalize_username(
        username
    )

    if normalized_user_id:
        account["user_id"] = normalized_user_id

    if normalized_username:
        account["username"] = normalized_username

    account["credits"] = (
        int(
            account.get(
                "credits",
                0,
            )
        )
        + int(amount)
    )

    transaction = _record_transaction(
        data=data,
        transaction_type="credit",
        user_id=normalized_user_id,
        username=normalized_username,
        amount=int(amount),
        balance_after=account["credits"],
        meta={
            "source": "add_credits",
        },
    )

    _save(data)

    return {
        "credits": account["credits"],
        "transaction_id": transaction["id"],
    }

@_billing_mutation_lock
def model_cost(
    model,
    input_tokens=0,
    output_tokens=0,
):
    base = MODEL_COSTS.get(
        model,
        5,
    )

    tokens = (
        int(input_tokens or 0)
        + int(output_tokens or 0)
    )

    if tokens <= 0:
        return 0

    token_blocks = (
        tokens + 999
    ) // 1000

    return max(
        1,
        token_blocks * base,
    )

@_billing_mutation_lock
def consume_usage(
    username=None,
    model="unknown",
    input_tokens=0,
    output_tokens=0,
    user_id=None,
    idempotency_key=None,
):
    cost = model_cost(
        model,
        input_tokens,
        output_tokens,
    )

    identity = _resolve_billing_identity(
        user_id=user_id,
        username=username,
    )

    data = _load()

    account = data["users"].setdefault(
        identity,
        _default_account(
            user_id=user_id,
            username=username,
        ),
    )

    normalized_user_id = _normalize_user_id(
        user_id
    )

    normalized_username = _normalize_username(
        username
    )

    idempotency_key = str(
        idempotency_key or ""
    ).strip()

    if idempotency_key:
        for existing_transaction in data.get(
            "transactions",
            [],
        ):
            if not isinstance(
                existing_transaction,
                dict,
            ):
                continue

            existing_meta = existing_transaction.get(
                "meta",
                {},
            )

            if not isinstance(existing_meta, dict):
                continue

            if (
                existing_transaction.get("type") != "usage"
                or existing_meta.get("idempotency_key")
                != idempotency_key
            ):
                continue

            if normalized_user_id:
                same_owner = (
                    existing_transaction.get("user_id")
                    == normalized_user_id
                )
            else:
                same_owner = (
                    bool(normalized_username)
                    and existing_transaction.get("username")
                    == normalized_username
                )

            if not same_owner:
                continue

            return {
                "ok": True,
                "cost": abs(
                    int(existing_transaction.get("amount", 0))
                ),
                "balance": int(
                    account.get("credits", 0)
                ),
                "transaction_id": existing_transaction.get("id"),
                "user_id": normalized_user_id,
                "username": normalized_username,
                "idempotent_replay": True,
            }

    if normalized_user_id:
        account["user_id"] = normalized_user_id

    if normalized_username:
        account["username"] = normalized_username

    balance = int(
        account.get(
            "credits",
            0,
        )
    )

    if balance < cost:

        return {
            "ok": False,
            "reason": "insufficient credits",
            "balance": balance,
            "cost": cost,
            "user_id": normalized_user_id,
            "username": normalized_username,
        }

    account["credits"] = (
        balance - cost
    )

    transaction = _record_transaction(
        data=data,
        transaction_type="usage",
        user_id=normalized_user_id,
        username=normalized_username,
        amount=-cost,
        balance_after=account["credits"],
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        meta={
            "source": "consume_usage",
            "credits_charged": cost,
            "idempotency_key": idempotency_key or None,
        },
    )

    _save(data)

    return {
        "ok": True,
        "cost": cost,
        "balance": account["credits"],
        "transaction_id": transaction["id"],
        "user_id": normalized_user_id,
        "username": normalized_username,
    }
