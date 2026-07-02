from pathlib import Path

SMOKE = Path("tools/nova_final_response_shape_contract_smoke.py")
text = SMOKE.read_text(encoding="utf-8-sig")

old = '''def get_route(data):
    debug = data.get("debug") if isinstance(data.get("debug"), dict) else {}
    return (
        data.get("route")
        or data.get("route_taken")
        or debug.get("route_taken")
        or debug.get("route")
        or ""
    )
'''

new = '''def get_route(data):
    debug = data.get("debug") if isinstance(data.get("debug"), dict) else {}
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    assistant = data.get("assistant_message") if isinstance(data.get("assistant_message"), dict) else {}
    assistant_meta = assistant.get("meta") if isinstance(assistant.get("meta"), dict) else {}

    return (
        data.get("route")
        or data.get("route_taken")
        or debug.get("route_taken")
        or debug.get("route")
        or meta.get("route")
        or meta.get("strategy")
        or assistant_meta.get("route")
        or assistant_meta.get("strategy")
        or ""
    )
'''

if old not in text:
    raise SystemExit("get_route block not found")

SMOKE.write_text(text.replace(old, new), encoding="utf-8")
print("patched final response shape smoke to accept meta.strategy route signal")
