from pathlib import Path

from nova_backend.services.model_registry import (
    get_default_model,
    get_image_model,
    get_model_billing_tier,
    get_model_details,
    get_public_models,
    get_vision_model,
    resolve_model,
)

ROOT = Path(__file__).resolve().parents[1]


def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)


models = get_public_models()
details = get_model_details()

check("public aliases exist", models == ["nova-cheap", "nova-smart", "nova-pro", "nova-max"])
check("model details include tiers", all("billing_tier" in item for item in details))
check("default resolves", bool(get_default_model()))
check("cheap resolves", resolve_model("nova-cheap") == "gpt-4.1-mini")
check("unknown falls back", resolve_model("not-real-model") == get_default_model())
check("billing tier cheap", get_model_billing_tier("nova-cheap") == "cheap")
check("vision model resolves", bool(get_vision_model()))
check("image model resolves", bool(get_image_model()))

nova_app = (ROOT / "nova_app.py").read_text(encoding="utf-8", errors="replace")
routes_core = (ROOT / "routes_core.py").read_text(encoding="utf-8", errors="replace")
services_ai = (ROOT / "services_ai.py").read_text(encoding="utf-8", errors="replace")
chat_service = (ROOT / "nova_backend/services/chat_service.py").read_text(encoding="utf-8", errors="replace")

check("nova_app imports registry", "get_public_models" in nova_app and "resolve_model" in nova_app)
check("nova_app model input resolves", "model = resolve_model(" in nova_app)
check("routes_core exposes model details", "get_model_details" in routes_core)
check("services_ai resolves model", "model=resolve_model(default_model)" in services_ai)
check("chat service uses default model helper", "self.chat_model = get_default_model()" in chat_service)
check("chat service resolves chat model calls", "model=resolve_model(self.chat_model)" in chat_service or "model=resolve_model(self.model)" in chat_service)
check("chat service uses vision helper", "get_vision_model()" in chat_service)
check("chat service uses image helper", "get_image_model()" in chat_service)

print("")
print("NOVA MODEL REGISTRY SMOKE PASSED")
