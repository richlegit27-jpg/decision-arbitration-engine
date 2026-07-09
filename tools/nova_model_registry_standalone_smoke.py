from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
registry_path = ROOT / "nova_backend" / "model_registry.py"

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

spec = importlib.util.spec_from_file_location("nova_model_registry_standalone", registry_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

check("registry file exists", registry_path.exists())
check("public aliases", module.get_public_models() == ["nova-cheap", "nova-smart", "nova-pro", "nova-max"])
check("details include billing tier", all("billing_tier" in item for item in module.get_model_details()))
check("cheap resolves", module.resolve_model("nova-cheap") == "gpt-4.1-mini")
check("provider model allowed", module.resolve_model("gpt-4.1") == "gpt-4.1")
check("unknown falls back", module.resolve_model("not-real-model") == module.get_default_model())
check("billing tier cheap", module.get_model_billing_tier("nova-cheap") == "cheap")
check("vision model exists", bool(module.get_vision_model()))
check("image model exists", bool(module.get_image_model()))

print("")
print("NOVA STANDALONE MODEL REGISTRY SMOKE PASSED")
