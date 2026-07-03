from pathlib import Path
import re

ROOT = Path(".").resolve()


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def write(rel, text):
    (ROOT / rel).write_text(text.rstrip() + "\n", encoding="utf-8")


def add_import(text, import_line):
    if import_line in text:
        return text

    lines = text.splitlines()
    insert_at = 0

    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_at = i + 1

    lines.insert(insert_at, import_line)
    return "\n".join(lines) + "\n"


def replace_required(text, old, new, name):
    if old not in text:
        print(f"SKIP {name}: already patched or exact text not found")
        return text

    print(f"PATCH {name}")
    return text.replace(old, new)


# nova_app.py
path = "nova_app.py"
text = read(path)
text = add_import(
    text,
    "from nova_backend.services.model_registry import get_default_model, get_model_details, get_public_models, resolve_model",
)
text = replace_required(
    text,
    'DEFAULT_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip() or "gpt-4.1-mini"',
    "DEFAULT_MODEL = get_default_model()",
    "nova_app DEFAULT_MODEL",
)
text = replace_required(
    text,
    '"models": [\n            DEFAULT_MODEL,\n            "gpt-4.1-mini",\n            "gpt-4.1",\n            "gpt-4o-mini",\n        ],\n        "default": DEFAULT_MODEL,',
    '"models": get_public_models(),\n        "model_details": get_model_details(),\n        "default": DEFAULT_MODEL,',
    "nova_app models list",
)
text = text.replace(
    'model = normalize_text(data.get("model")) or DEFAULT_MODEL',
    'model = resolve_model(normalize_text(data.get("model")) or DEFAULT_MODEL)',
)
write(path, text)


# nova_context.py
path = "nova_context.py"
text = read(path)
text = add_import(text, "from nova_backend.services.model_registry import get_default_model")
text = replace_required(
    text,
    'DEFAULT_MODEL = (os.getenv("OPENAI_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini").strip()',
    "DEFAULT_MODEL = get_default_model()",
    "nova_context DEFAULT_MODEL",
)
write(path, text)


# routes_core.py
path = "routes_core.py"
text = read(path)
text = add_import(text, "from nova_backend.services.model_registry import get_model_details, get_public_models")
text = replace_required(
    text,
    '"models": [DEFAULT_MODEL, "gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"],',
    '"models": get_public_models(),\n                "model_details": get_model_details(),',
    "routes_core models list",
)
write(path, text)


# services_ai.py
path = "services_ai.py"
text = read(path)
text = add_import(text, "from nova_backend.services.model_registry import resolve_model")
text = replace_required(
    text,
    'model=default_model or "gpt-4.1-mini",',
    "model=resolve_model(default_model),",
    "services_ai model call",
)
write(path, text)


# chat_service.py
path = "nova_backend/services/chat_service.py"
text = read(path)
text = add_import(
    text,
    "from nova_backend.services.model_registry import get_default_model, get_image_model, get_vision_model, resolve_model",
)

text, count = re.subn(
    r'self\.chat_model\s*=\s*os\.getenv\(\s*"OPENAI_MODEL",\s*"gpt-5\.4",\s*\)',
    "self.chat_model = get_default_model()",
    text,
    count=1,
)
print("PATCH chat_service chat_model" if count else "SKIP chat_service chat_model")

text, count = re.subn(
    r'self\.image_model\s*=\s*os\.getenv\(\s*"NOVA_IMAGE_MODEL",\s*"[^"]+",\s*\)',
    "self.image_model = get_image_model()",
    text,
    count=1,
)
print("PATCH chat_service image_model" if count else "SKIP chat_service image_model")

text = text.replace(
    'model=getattr(self, "model", "gpt-4o-mini")',
    'model=resolve_model(getattr(self, "model", None))',
)

text = text.replace(
    'model=os.getenv("NOVA_VISION_MODEL", "gpt-4o-mini")',
    "model=get_vision_model()",
)

text = text.replace(
    "model=self.chat_model,",
    "model=resolve_model(self.chat_model),",
)

text = text.replace(
    "model=self.model,",
    "model=resolve_model(self.model),",
)

write(path, text)

print("")
print("patched model registry wiring")
