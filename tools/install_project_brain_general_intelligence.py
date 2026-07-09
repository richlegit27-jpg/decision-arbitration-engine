from pathlib import Path
import ast

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "# NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701"

block = r'''
# NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701
# Priority project-brain intelligence adapter.
# Catches broad Nova project/judgment/concept questions before memory-write,
# generic chat, or stale fallback routes can answer them.
try:
    @app.before_request
    def _nova_project_brain_general_intelligence_priority_20260701():
        try:
            from flask import jsonify as _nova_gi_jsonify
            from flask import request as _nova_gi_request

            if _nova_gi_request.path != "/api/chat" or _nova_gi_request.method != "POST":
                return None

            payload = _nova_gi_request.get_json(silent=True) or {}

            attachments = payload.get("attachments") or []
            if attachments:
                return None

            user_text = (
                payload.get("message")
                or payload.get("text")
                or payload.get("content")
                or payload.get("user_text")
                or ""
            )

            from nova_backend.services.project_brain_general_intelligence import (
                build_project_brain_general_answer,
            )

            answer = build_project_brain_general_answer(user_text)

            if not answer:
                return None

            data = {
                "ok": True,
                "text": answer.text,
                "content": answer.text,
                "assistant_message": {
                    "role": "assistant",
                    "text": answer.text,
                    "content": answer.text,
                },
                "debug": {
                    "route": "project_brain_general_intelligence",
                    "route_taken": "project_brain_general_intelligence",
                    "intent": answer.intent,
                    "priority_project_brain_general_intelligence": True,
                },
            }

            return _nova_gi_jsonify(data)

        except Exception as exc:
            try:
                print("[NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701] failed:", exc)
            except Exception:
                pass
            return None

    print("[NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701] installed")
except Exception as _nova_project_brain_general_intelligence_priority_error_20260701:
    print(
        "[NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701] install failed:",
        _nova_project_brain_general_intelligence_priority_error_20260701,
    )
'''

if marker in text:
    print("marker already installed")
    raise SystemExit(0)

tree = ast.parse(text)
insert_line = None

for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        target_names = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                target_names.append(target.id)

        call = node.value
        if "app" in target_names and isinstance(call, ast.Call):
            func = call.func
            func_name = ""
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr

            if func_name == "Flask":
                insert_line = getattr(node, "end_lineno", node.lineno)
                break

if insert_line is None:
    raise SystemExit("Could not find app = Flask(...) insertion point")

lines = text.splitlines()
lines.insert(insert_line, "")
lines.insert(insert_line + 1, block.strip())
lines.insert(insert_line + 2, "")

path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"inserted {marker} after line {insert_line}")
