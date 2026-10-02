
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from nova_backend.services import billing_service as billing


def _mock_provider_modules(monkeypatch, create_provider_client):
    model_registry = ModuleType("nova_backend.model_registry")
    model_registry.get_model_provider = lambda _model: "openai"
    model_registry.resolve_model = lambda model: model
    model_registry.get_default_model_alias = lambda: "gpt-4o-mini"
    provider_gateway = ModuleType(
        "nova_backend.services.provider_gateway_service"
    )
    provider_gateway.create_provider_client = create_provider_client
    monkeypatch.setitem(sys.modules, "nova_backend.model_registry", model_registry)
    monkeypatch.setitem(
        sys.modules,
        "nova_backend.services.provider_gateway_service",
        provider_gateway,
    )


def test_planning_and_execution_repair_paths_require_credit_enforcement(
    monkeypatch,
    tmp_path,
):
    from nova_backend.services import execution_handler as execution_module
    from nova_backend.services import ai_execution_service as ai_execution_module
    from nova_backend.services import project_planning_ai_service as planning_module

    calls = []

    def fake_chat_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"tasks": [{"title": "Build the feature", "target_file": "feature.py"}]}'
                    )
                )
            ]
        )

    monkeypatch.setattr(
        planning_module,
        "chat_completions_create",
        fake_chat_completion,
    )
    planning_module.ProjectPlanningAIService().build_plan(
        "Build a feature"
    )

    handler = execution_module.ExecutionHandler(service=None)
    handler.current_user_id = "billing-regression-user"
    monkeypatch.setattr(
        execution_module,
        "chat_completions_create",
        fake_chat_completion,
    )
    handler._generate_file_replacement(
        {"target_file": str(tmp_path / "replacement.py"), "goal": "write"}
    )
    handler._generate_function_replacement(
        {"target_function": "build", "goal": "repair"}
    )
    ai_execution = ai_execution_module.AIExecutionService()
    monkeypatch.setattr(
        ai_execution_module.model_gateway_service,
        "responses_create",
        fake_chat_completion,
    )
    ai_execution._create_response(
        session_id="ai-execution-session",
        system_prompt="system",
        user_prompt="execute a step",
    )

    assert len(calls) == 4
    assert all(call["nova_enforce_credits"] is True for call in calls)
    assert all(
        call.get("nova_user_id") == "billing-regression-user"
        for call in calls[1:3]
    )
    assert calls[3]["nova_session_id"] == "ai-execution-session"


def test_auto_fix_retry_path_requires_credit_enforcement(
    monkeypatch,
    tmp_path,
):
    from nova_backend.services.auto_fix import service as auto_fix_module

    target = tmp_path / "repair_target.py"
    target.write_text("def value():\n    return 1\n", encoding="utf-8")
    calls = []

    def fake_responses_create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            output_text="def value():\n    return 2\n"
        )

    monkeypatch.setattr(
        auto_fix_module,
        "responses_create",
        fake_responses_create,
    )

    class ChatServiceStub:
        model = "gpt-4o-mini"

        @staticmethod
        def safe_str(value):
            return str(value or "")

        @staticmethod
        def _guess_path_from_text(_text):
            return str(target)

        @staticmethod
        def _get_session_meta(_session_id, key):
            return "file" if key == "pending_fix_mode" else ""

        @staticmethod
        def _set_session_meta(*_args):
            return None

        @staticmethod
        def _normalize_python_indentation(value):
            return value

        @staticmethod
        def _update_working_state(*_args):
            return None

        @staticmethod
        def _build_assistant_message(**kwargs):
            return kwargs

        @staticmethod
        def _build_user_message(value):
            return value

        @staticmethod
        def _finalize_response(**kwargs):
            return kwargs

    result = auto_fix_module.AutoFixService(ChatServiceStub()).execute_file_fix(
        user_text=f"Fix this file {target}",
        session_id="auto-fix-session",
    )

    assert result["decision"]["route"] == "auto_fix_prepare"
    assert len(calls) == 1
    assert calls[0]["nova_enforce_credits"] is True
    assert calls[0]["nova_session_id"] == "auto-fix-session"


def test_gateway_insufficient_credit_preflight_prevents_provider_invocation(
    monkeypatch,
):
    from nova_backend.services import model_gateway_service as gateway

    monkeypatch.setattr(billing, "get_balance", lambda **_kwargs: 0)
    monkeypatch.setattr(billing, "model_cost", lambda **_kwargs: 1)
    provider_calls = []
    charges = []
    monkeypatch.setattr(
        billing,
        "consume_usage",
        lambda **kwargs: charges.append(kwargs) or {"ok": True},
    )
    _mock_provider_modules(
        monkeypatch,
        lambda _provider: provider_calls.append("client created"),
    )

    with pytest.raises(RuntimeError, match="Insufficient Nova credits"):
        gateway.chat_completions_create(
            model="gpt-4o-mini",
            messages=[],
            nova_user_id="billing-regression-user",
            nova_enforce_credits=True,
        )

    assert provider_calls == []
    assert charges == []


def test_gateway_provider_failure_retry_does_not_charge(
    monkeypatch,
):
    from nova_backend.services import model_gateway_service as gateway
    from nova_backend.services import usage_ledger_service

    monkeypatch.setattr(billing, "get_balance", lambda **_kwargs: 100)
    monkeypatch.setattr(billing, "model_cost", lambda **_kwargs: 1)
    charges = []
    usage_records = []
    monkeypatch.setattr(
        billing,
        "consume_usage",
        lambda **kwargs: charges.append(kwargs) or {"ok": True},
    )
    monkeypatch.setattr(
        usage_ledger_service,
        "record_model_usage",
        lambda **kwargs: usage_records.append(kwargs),
    )

    class FailingCompletions:
        def create(self, **_kwargs):
            raise OSError("simulated provider outage")

    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=FailingCompletions(),
        )
    )
    _mock_provider_modules(monkeypatch, lambda _provider: client)

    for _attempt in range(2):
        with pytest.raises(OSError, match="simulated provider outage"):
            gateway.chat_completions_create(
                model="gpt-4o-mini",
                messages=[],
                nova_user_id="billing-regression-user",
                nova_enforce_credits=True,
            )

    assert charges == []
    assert usage_records == []


def test_gateway_missing_usage_metadata_does_not_debit(
    monkeypatch,
):
    from nova_backend.services import model_gateway_service as gateway
    from nova_backend.services import usage_ledger_service

    monkeypatch.setattr(billing, "get_balance", lambda **_kwargs: 100)
    monkeypatch.setattr(billing, "model_cost", lambda **_kwargs: 1)
    charges = []
    usage_records = []
    monkeypatch.setattr(
        billing,
        "consume_usage",
        lambda **kwargs: charges.append(kwargs) or {"ok": True},
    )
    monkeypatch.setattr(
        usage_ledger_service,
        "record_model_usage",
        lambda **kwargs: usage_records.append(kwargs),
    )

    class MissingUsageCompletions:
        def create(self, **_kwargs):
            return SimpleNamespace(
                id="provider-response-no-usage",
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="response without usage"),
                    )
                ],
            )

    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=MissingUsageCompletions(),
        )
    )
    _mock_provider_modules(monkeypatch, lambda _provider: client)

    with pytest.raises(RuntimeError, match="usage is missing or zero"):
        gateway.chat_completions_create(
            model="gpt-4o-mini",
            messages=[],
            nova_user_id="billing-regression-user",
            nova_enforce_credits=True,
        )

    assert charges == []
    assert usage_records == []


def test_gateway_successful_retry_charges_once_for_same_provider_response(
    monkeypatch,
    isolated_billing_file,
):
    from nova_backend.services import model_gateway_service as gateway
    from nova_backend.services import usage_ledger_service

    billing.add_credits(
        username="billing-retry-user",
        user_id="billing-retry-user-id",
        amount=100,
    )
    usage_records = []
    monkeypatch.setattr(
        usage_ledger_service,
        "record_model_usage",
        lambda **kwargs: usage_records.append(kwargs),
    )

    response = SimpleNamespace(
        id="provider-response-retry-1",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="ok"),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
    )

    class SuccessfulCompletions:
        def create(self, **_kwargs):
            return response

    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SuccessfulCompletions(),
        )
    )
    _mock_provider_modules(monkeypatch, lambda _provider: client)

    for _attempt in range(2):
        gateway.chat_completions_create(
            model="gpt-4o-mini",
            messages=[],
            nova_user_id="billing-retry-user-id",
            nova_username="billing-retry-user",
            nova_enforce_credits=True,
        )

    data = json.loads(isolated_billing_file.read_text(encoding="utf-8"))
    usage_transactions = [
        item
        for item in data["transactions"]
        if item.get("user_id") == "billing-retry-user-id"
        and item.get("type") == "usage"
    ]
    assert len(usage_transactions) == 1
    assert billing.get_balance(user_id="billing-retry-user-id") == 99
    assert len(usage_records) == 2


@pytest.fixture
def isolated_billing_file(tmp_path, monkeypatch):
    """Use an isolated ledger and deterministic zero-credit defaults."""
    ledger = tmp_path / "nova_billing_test.json"

    monkeypatch.setattr(billing, "BILLING_FILE", ledger)
    monkeypatch.setattr(
        billing,
        "DEFAULT_USER",
        {
            **billing.DEFAULT_USER,
            "credits": 0,
        },
    )

    return ledger


def test_gateway_rejected_billing_does_not_record_usage(monkeypatch):
    from types import SimpleNamespace

    from nova_backend.services import billing_service as billing_module
    from nova_backend.services import model_gateway_service as gateway
    from nova_backend.services import usage_ledger_service as usage_module

    recorded = []

    monkeypatch.setattr(
        billing_module,
        "consume_usage",
        lambda **kwargs: {
            "ok": False,
            "reason": "insufficient credits",
        },
    )
    monkeypatch.setattr(
        usage_module,
        "record_model_usage",
        lambda **kwargs: recorded.append(kwargs),
    )

    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
    )

    with pytest.raises(RuntimeError, match="insufficient credits"):
        gateway._nova_consume_and_record_usage(
            user_id="gateway-test-user",
            username="gateway-test-user",
            session_id="gateway-test-session",
            model="gpt-4o-mini",
            messages=[],
            response=response,
            enforce=True,
        )

    assert recorded == []

def test_consume_usage_deducts_credits_and_persists_transaction(
    isolated_billing_file,
):
    billing.add_credits(
        username="billing-test-user",
        user_id="billing-test-001",
        amount=100,
    )

    result = billing.consume_usage(
        username="billing-test-user",
        user_id="billing-test-001",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=100,
    )

    assert result["ok"] is True
    assert result["cost"] == 1
    assert result["balance"] == 99
    assert billing.get_balance(
        user_id="billing-test-001",
        username="billing-test-user",
    ) == 99

    data = json.loads(
        isolated_billing_file.read_text(encoding="utf-8")
    )
    transactions = [
        item for item in data["transactions"]
        if item.get("user_id") == "billing-test-001"
        and item.get("type") == "usage"
    ]

    assert len(transactions) == 1
    assert transactions[0]["amount"] == -1
    assert transactions[0]["balance_after"] == 99


def test_insufficient_credits_does_not_deduct_or_record_usage(
    isolated_billing_file,
):
    billing.add_credits(
        username="billing-test-poor",
        user_id="billing-test-002",
        amount=1,
    )

    before = json.loads(
        isolated_billing_file.read_text(encoding="utf-8")
    )
    usage_before = sum(
        1 for item in before["transactions"]
        if item.get("user_id") == "billing-test-002"
        and item.get("type") == "usage"
    )

    result = billing.consume_usage(
        username="billing-test-poor",
        user_id="billing-test-002",
        model="gpt-5.4",
        input_tokens=1000,
        output_tokens=0,
    )

    assert result["ok"] is False
    assert result["reason"] == "insufficient credits"
    assert result["balance"] == 1

    after = json.loads(
        isolated_billing_file.read_text(encoding="utf-8")
    )
    account = after["users"]["billing-test-002"]
    usage_after = sum(
        1 for item in after["transactions"]
        if item.get("user_id") == "billing-test-002"
        and item.get("type") == "usage"
    )

    assert account["credits"] == 1
    assert usage_after == usage_before


def test_usage_deduction_does_not_change_another_users_balance(
    isolated_billing_file,
):
    billing.add_credits(
        username="billing-test-alpha",
        user_id="billing-test-alpha-id",
        amount=50,
    )
    billing.add_credits(
        username="billing-test-beta",
        user_id="billing-test-beta-id",
        amount=70,
    )

    result = billing.consume_usage(
        username="billing-test-alpha",
        user_id="billing-test-alpha-id",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=100,
    )

    assert result["ok"] is True
    assert billing.get_balance(
        user_id="billing-test-alpha-id",
    ) == 49
    assert billing.get_balance(
        user_id="billing-test-beta-id",
    ) == 70



def test_gateway_preserves_successful_charge_when_usage_ledger_fails(
    monkeypatch,
    caplog,
):
    from types import SimpleNamespace

    from nova_backend.services import billing_service as billing_module
    from nova_backend.services import model_gateway_service as gateway
    from nova_backend.services import usage_ledger_service as usage_module

    charges = []

    monkeypatch.setattr(
        billing_module,
        "consume_usage",
        lambda **kwargs: (
            charges.append(kwargs)
            or {"ok": True, "cost": 1, "balance": 99}
        ),
    )

    def fail_usage_record(**kwargs):
        raise OSError("simulated usage ledger write failure")

    monkeypatch.setattr(
        usage_module,
        "record_model_usage",
        fail_usage_record,
    )

    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
    )

    result = gateway._nova_consume_and_record_usage(
        user_id="gateway-test-user",
        username="gateway-test-user",
        session_id="gateway-test-session",
        model="gpt-4o-mini",
        messages=[],
        response=response,
        enforce=True,
    )

    assert len(charges) == 1
    assert result["ok"] is True
    assert result["cost"] == 1
    assert result["balance"] == 99
    assert "usage analytics write failed" in caplog.text
    assert "simulated usage ledger write failure" in caplog.text

def test_consume_usage_is_idempotent_for_same_key(
    isolated_billing_file,
):
    billing.add_credits(
        username="billing-idempotency-user",
        user_id="billing-idempotency-001",
        amount=100,
    )

    first = billing.consume_usage(
        username="billing-idempotency-user",
        user_id="billing-idempotency-001",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=100,
        idempotency_key="provider_response:test-123",
    )

    second = billing.consume_usage(
        username="billing-idempotency-user",
        user_id="billing-idempotency-001",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=100,
        idempotency_key="provider_response:test-123",
    )

    assert first["ok"] is True
    assert second["ok"] is True

    assert second.get("idempotent_replay") is True
    assert second["transaction_id"] == first["transaction_id"]

    assert billing.get_balance(
        user_id="billing-idempotency-001",
        username="billing-idempotency-user",
    ) == 99

    data = billing._load()

    matching_transactions = [
        transaction
        for transaction in data.get("transactions", [])
        if (
            transaction.get("type") == "usage"
            and transaction.get("user_id")
            == "billing-idempotency-001"
            and transaction.get("meta", {}).get(
                "idempotency_key"
            ) == "provider_response:test-123"
        )
    ]

    assert len(matching_transactions) == 1
from types import SimpleNamespace


def test_image_vision_uses_credit_enforced_gateway(tmp_path, monkeypatch):
    from nova_backend.services import image_vision_service as vision_module

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    (upload_dir / "sample.png").write_bytes(b"test-image-bytes")
    monkeypatch.setenv("UPLOADS_DIR", str(upload_dir))
    calls = []
    monkeypatch.setattr(
        vision_module,
        "chat_completions_create",
        lambda **kwargs: calls.append(kwargs)
        or SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="A test image."))]
        ),
    )

    result = vision_module.ImageVisionService().handle(
        {"filename": "sample.png"},
        "Describe this image",
    )

    assert result["vision_used"] is True
    assert len(calls) == 1
    assert calls[0]["nova_enforce_credits"] is True


def test_hosted_web_search_uses_credit_enforced_gateway(monkeypatch):
    from nova_backend.services import hosted_web_search_service as web_module

    calls = []
    monkeypatch.setattr(
        web_module,
        "responses_create",
        lambda **kwargs: calls.append(kwargs)
        or SimpleNamespace(output_text="Evidence-backed answer.", output=[]),
    )

    web_module.HostedWebSearchService(model="gpt-test").search("test query")

    assert len(calls) == 1
    assert calls[0]["nova_enforce_credits"] is True

def test_payments_readiness_uses_authenticated_user_id_for_billing_account(
    isolated_billing_file,
):
    from nova_backend.services.payments_readiness_service import (
        build_payments_readiness,
    )

    billing.add_credits(
        user_id="readiness-user-id",
        username="readiness-user",
        amount=45,
    )

    result = build_payments_readiness(
        username="readiness-user",
        user_id="readiness-user-id",
    )

    assert result["account"]["credits"] == 45
    assert result["username"] == "readiness-user"


def test_public_plan_readiness_does_not_create_a_default_richard_account(
    isolated_billing_file,
):
    from nova_backend.services.payments_readiness_service import (
        build_payments_readiness,
    )

    result = build_payments_readiness()
    assert result["account"]["plan"] == "free"
    assert billing.BILLING_FILE.exists() is False



def test_chat_gateway_calls_for_billed_support_paths_enforce_credits():
    import ast
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "nova_backend/services/chat_service.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"))
    checked_functions = {
        "_execute_web_fetch",
        "_run_chat_model",
        "_execute_general_chat",
        "_create_model_response",
    }
    calls = {name: [] for name in checked_functions}

    class CallCollector(ast.NodeVisitor):
        def __init__(self):
            self.function = None

        def visit_FunctionDef(self, node):
            previous = self.function
            self.function = node.name
            self.generic_visit(node)
            self.function = previous

        def visit_Call(self, node):
            if self.function in calls:
                if isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                elif isinstance(node.func, ast.Name):
                    name = node.func.id
                else:
                    name = ""
                if name in {"responses_create", "chat_completions_create"}:
                    calls[self.function].append(node)
            self.generic_visit(node)

    CallCollector().visit(tree)
    assert all(calls.values())
    assert all(
        any(
            keyword.arg == "nova_enforce_credits"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in call.keywords
        )
        for function_calls in calls.values()
        for call in function_calls
    )
