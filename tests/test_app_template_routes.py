import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_app_routes_only_render_existing_literal_templates():
    source = (ROOT / "app.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename="app.py")
    missing = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        is_route = any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr in {"get", "route"}
            for decorator in node.decorator_list
        )
        if not is_route:
            continue

        for call in ast.walk(node):
            if not (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "render_template"
                and call.args
                and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, str)
            ):
                continue
            template = ROOT / "templates" / call.args[0].value
            if not template.is_file():
                missing.append(f"{node.name}: {call.args[0].value}")

    assert not missing, "Missing route templates: " + ", ".join(missing)
