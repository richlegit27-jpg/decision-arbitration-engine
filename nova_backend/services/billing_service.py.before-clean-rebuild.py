import json
import os
from pathlib import Path
from datetime import datetime, timezone


BILLING_FILE = Path("data/nova_billing.json")


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

DEFAULT_USER = {
"plan": "free",
"credits": 10000,
"monthly_credits": 10000,
    "created_at": "",
    "stripe_customer_id": ""
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load():
    if not BILLING_FILE.exists():
        BILLING_FILE.parent.mkdir(parents=True, exist_ok=True)
        _save({"users": {}})

    try:
        return json.loads(
            BILLING_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        return {"users": {}}


def _save(data):
    BILLING_FILE.parent.mkdir(parents=True, exist_ok=True)

    BILLING_FILE.write_text(
        json.dumps(
            data,
            indent=2
        ),
        encoding="utf-8"
    )


def get_account(username):
    username = str(username or "").strip().lower()

    data = _load()

    if username not in data["users"]:
        data["users"][username] = {
            **DEFAULT_USER,
            "created_at": _now()
        }
        _save(data)

    return data["users"][username]


def get_balance(username):
    account = get_account(username)

    return account.get("credits", 0)


def add_credits(username, amount):
    data = _load()

    username = str(username or "").strip().lower()

    account = data["users"].setdefault(
        username,
        {
            **DEFAULT_USER,
            "created_at": _now()
        }
    )

    account["credits"] += int(amount)

    _save(data)

    return account["credits"]


def model_cost(model, input_tokens=0, output_tokens=0):
    base = MODEL_COSTS.get(
        model,
        5
    )

    tokens = input_tokens + output_tokens

    return max(
        1,
        int(tokens / 1000) * base
    )


def consume_usage(
    username,
    model,
    input_tokens=0,
    output_tokens=0
):
    cost = model_cost(
        model,
        input_tokens,
        output_tokens
    )

    data = _load()

    username = str(username or "").strip().lower()

    account = data["users"].setdefault(
        username,
        {
            **DEFAULT_USER,
            "created_at": _now()
        }
    )

    if account["credits"] < cost:
        return {
            "ok": False,
            "reason": "insufficient credits",
            "balance": account["credits"]
        }

    account["credits"] -= cost

    _save(data)

    return {
        "ok": True,
        "cost": cost,
        "balance": account["credits"]
    }


def can_use_model(username, model):
    account = get_account(username)

    if account["plan"] == "developer":
        return True

    if model == "gpt-5":
        return False

    return True

def set_stripe_customer_id(
    username,
    stripe_customer_id,
):
    data = _load()

    username = str(
        username or ""
    ).strip().lower()

    account = data["users"].setdefault(
        username,
        {
            **DEFAULT_USER,
            "created_at": _now(),
        }
    )

    account["stripe_customer_id"] = str(
        stripe_customer_id or ""
    ).strip()

    _save(data)

    return account


def set_subscription(
    username,
    subscription_id,
    plan,
):
    data = _load()

    username = str(
        username or ""
    ).strip().lower()

    account = data["users"].setdefault(
        username,
        {
            **DEFAULT_USER,
            "created_at": _now(),
        }
    )

    plan = str(
        plan or "free"
    ).strip().lower()

plan_credits = {
    "free": 10000,
    "plus": 500000,
    "pro": 2000000,
}

monthly_credits = plan_credits.get(
    plan,
    10000,
)

    account["subscription_id"] = str(
        subscription_id or ""
    ).strip()

    account["plan"] = plan

    account["monthly_credits"] = monthly_credits

    account["credits"] = monthly_credits

    _save(data)

    return account

def cancel_subscription(
    username,
):
    data = _load()

    username = str(
        username or ""
    ).strip().lower()

    account = data["users"].setdefault(
        username,
        {
            **DEFAULT_USER,
            "created_at": _now(),
        }
    )

    account["subscription_id"] = ""

    account["plan"] = "free"

    account["monthly_credits"] = 1000

    account["credits"] = 1000

    _save(data)

    return account

def plan_from_price_id(
    price_id,
):
    price_id = str(
        price_id or ""
    ).strip()

plus_price = str(
    os.environ.get(
        "NOVA_STRIPE_PLUS_PRICE_ID",
        "",
    )
).strip()

pro_price = str(
    os.environ.get(
        "NOVA_STRIPE_PRO_PRICE_ID",
        "",
    )
).strip()

if price_id and price_id == plus_price:
    return "plus"

if price_id and price_id == pro_price:
    return "pro"

    return "free"