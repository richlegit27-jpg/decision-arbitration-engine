import json
from pathlib import Path
from datetime import datetime, timezone


BILLING_FILE = Path("data/nova_billing.json")


MODEL_COSTS = {
    "gpt-4o-mini": 1,
    "gpt-4.1": 10,
    "gpt-5": 25
}


DEFAULT_USER = {
    "plan": "free",
    "credits": 1000,
    "monthly_credits": 1000,
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