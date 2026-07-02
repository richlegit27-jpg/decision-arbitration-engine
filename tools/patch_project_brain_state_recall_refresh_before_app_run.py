from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8-sig")

marker = "# NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702"

start = text.find(marker)
if start == -1:
    raise SystemExit("State Recall Refresh marker not found")

if start > 0 and text[start - 1] == "\n":
    start = start - 1

tail = '    print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] install failed:", _nova_project_brain_state_recall_refresh_api_error_20260702)\n'
end_tail = text.find(tail, start)
if end_tail == -1:
    raise SystemExit("State Recall Refresh block tail not found")

end = end_tail + len(tail)

text_without_block = text[:start].rstrip() + "\n\n" + text[end:].lstrip()

block = r'''
# NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702
# Thin compatibility hook: direct project-state recall must prefer the State Bridge memory record.
try:
    import json as _nova_project_brain_state_recall_refresh_json_20260702
    from nova_backend.services.project_brain_state_recall_refresh import refresh_project_state_payload as _nova_project_brain_refresh_project_state_payload_20260702

    @app.after_request
    def _nova_project_brain_state_recall_refresh_api_20260702(response):
        try:
            content_type = str(response.headers.get("Content-Type") or "")
            if "application/json" not in content_type.lower():
                return response

            raw = response.get_data(as_text=True)
            if not raw:
                return response

            data = _nova_project_brain_state_recall_refresh_json_20260702.loads(raw)
            refreshed = _nova_project_brain_refresh_project_state_payload_20260702(data)

            if refreshed is data or refreshed == data:
                return response

            response.set_data(_nova_project_brain_state_recall_refresh_json_20260702.dumps(refreshed, ensure_ascii=False))
            response.headers["Content-Type"] = "application/json"
            response.headers["Content-Length"] = str(len(response.get_data()))
            return response
        except Exception as exc:
            try:
                print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] failed:", exc)
            except Exception:
                pass
            return response

    try:
        funcs = app.after_request_funcs.setdefault(None, [])
        funcs[:] = [
            func for func in funcs
            if getattr(func, "__name__", "") != "_nova_project_brain_state_recall_refresh_api_20260702"
        ]
        funcs.insert(0, _nova_project_brain_state_recall_refresh_api_20260702)
        print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] forced final after_request order before app.run")
    except Exception as _nova_project_brain_state_recall_refresh_order_error_20260702:
        print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] order failed:", _nova_project_brain_state_recall_refresh_order_error_20260702)

    print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] installed before app.run")
except Exception as _nova_project_brain_state_recall_refresh_api_error_20260702:
    print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] install failed:", _nova_project_brain_state_recall_refresh_api_error_20260702)
'''.strip() + "\n\n"

insert_at = text_without_block.rfind('if __name__ == "__main__":')
if insert_at == -1:
    app_run_at = text_without_block.rfind("app.run(")
    if app_run_at == -1:
        raise SystemExit("Could not find app runner insertion point")
    insert_at = text_without_block.rfind("\n", 0, app_run_at) + 1

new_text = text_without_block[:insert_at].rstrip() + "\n\n" + block + text_without_block[insert_at:].lstrip()

APP.write_text(new_text, encoding="utf-8")
print("moved State Recall Refresh hook before app runner")
