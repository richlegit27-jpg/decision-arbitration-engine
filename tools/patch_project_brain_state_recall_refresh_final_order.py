from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8-sig")

old = '''    print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] installed")
except Exception as _nova_project_brain_state_recall_refresh_api_error_20260702:
    print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] install failed:", _nova_project_brain_state_recall_refresh_api_error_20260702)
'''

new = '''    try:
        funcs = app.after_request_funcs.setdefault(None, [])
        funcs[:] = [
            func for func in funcs
            if getattr(func, "__name__", "") != "_nova_project_brain_state_recall_refresh_api_20260702"
        ]
        funcs.insert(0, _nova_project_brain_state_recall_refresh_api_20260702)
        print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] forced final after_request order")
    except Exception as _nova_project_brain_state_recall_refresh_order_error_20260702:
        print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] order failed:", _nova_project_brain_state_recall_refresh_order_error_20260702)

    print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] installed")
except Exception as _nova_project_brain_state_recall_refresh_api_error_20260702:
    print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] install failed:", _nova_project_brain_state_recall_refresh_api_error_20260702)
'''

if old not in text:
    raise SystemExit("target install tail not found")

APP.write_text(text.replace(old, new), encoding="utf-8")
print("forced State Recall Refresh hook to final after_request order")
