from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "NOVA_SESSIONS_EMPTY_INACTIVE_FILTER_20260702"

if marker in text:
    print("sessions empty inactive filter already installed")
    raise SystemExit(0)

patch = r'''

# ============================================================
# NOVA_SESSIONS_EMPTY_INACTIVE_FILTER_20260702
# Hide inactive empty sessions from /api/sessions.
# Keeps active, pinned, and non-empty sessions visible.
# This cleans Railway image-generation session pollution without
# touching image generation, upload storage, or session persistence.
# ============================================================
try:
    import json as _nova_sessions_filter_json
    from flask import request as _nova_sessions_filter_request

    def _nova_sessions_filter_count_20260702(item):
        try:
            return int(item.get("message_count") or 0)
        except Exception:
            return 0

    def _nova_sessions_filter_keep_20260702(item, active_session_id):
        try:
            if not isinstance(item, dict):
                return False

            session_id = str(item.get("id") or "")

            if active_session_id and session_id == active_session_id:
                return True

            if item.get("pinned") is True:
                return True

            if _nova_sessions_filter_count_20260702(item) > 0:
                return True

            active_execution = item.get("active_execution")
            if isinstance(active_execution, dict) and active_execution:
                return True

            return False
        except Exception:
            return True

    def _nova_sessions_empty_inactive_filter_20260702(response):
        try:
            if _nova_sessions_filter_request.path != "/api/sessions":
                return response

            if getattr(response, "status_code", 200) >= 400:
                return response

            data = response.get_json(silent=True)
            if not isinstance(data, dict):
                return response

            active_session_id = (
                data.get("active_session_id")
                or data.get("session_id")
                or (data.get("debug") or {}).get("active_session_id")
                or (data.get("debug") or {}).get("session_id")
                or ""
            )
            active_session_id = str(active_session_id or "")

            original_items = data.get("items")
            original_sessions = data.get("sessions")

            changed = False
            hidden_count = 0

            if isinstance(original_items, list):
                filtered_items = [
                    item for item in original_items
                    if _nova_sessions_filter_keep_20260702(item, active_session_id)
                ]
                hidden_count += max(0, len(original_items) - len(filtered_items))
                if len(filtered_items) != len(original_items):
                    data["items"] = filtered_items
                    changed = True

            if isinstance(original_sessions, list):
                filtered_sessions = [
                    item for item in original_sessions
                    if _nova_sessions_filter_keep_20260702(item, active_session_id)
                ]
                if len(filtered_sessions) != len(original_sessions):
                    data["sessions"] = filtered_sessions
                    changed = True

            if changed:
                try:
                    debug = data.get("debug")
                    if not isinstance(debug, dict):
                        debug = {}

                    visible_count = 0
                    if isinstance(data.get("sessions"), list):
                        visible_count = len(data.get("sessions"))
                    elif isinstance(data.get("items"), list):
                        visible_count = len(data.get("items"))

                    debug["empty_inactive_session_filter"] = True
                    debug["hidden_empty_inactive_session_count"] = hidden_count
                    debug["returned_session_count"] = visible_count
                    debug["route_taken"] = debug.get("route_taken") or "slim_sessions_payload"
                    data["debug"] = debug
                except Exception:
                    pass

                payload = _nova_sessions_filter_json.dumps(data, ensure_ascii=False)
                response.set_data(payload)
                response.mimetype = "application/json"
                try:
                    response.headers["Content-Length"] = str(len(payload.encode("utf-8")))
                except Exception:
                    pass

            return response
        except Exception as exc:
            try:
                print("[NOVA_SESSIONS_EMPTY_INACTIVE_FILTER_20260702] failed:", exc)
            except Exception:
                pass
            return response

    try:
        _nova_sessions_after_funcs_20260702 = app.after_request_funcs.setdefault(None, [])
        _nova_sessions_after_funcs_20260702.insert(0, _nova_sessions_empty_inactive_filter_20260702)
        print("[NOVA_SESSIONS_EMPTY_INACTIVE_FILTER_20260702] installed")
    except Exception as _nova_sessions_filter_install_error_20260702:
        try:
            print("[NOVA_SESSIONS_EMPTY_INACTIVE_FILTER_20260702] install failed:", _nova_sessions_filter_install_error_20260702)
        except Exception:
            pass

except Exception as _nova_sessions_empty_inactive_filter_error_20260702:
    try:
        print("[NOVA_SESSIONS_EMPTY_INACTIVE_FILTER_20260702] outer failed:", _nova_sessions_empty_inactive_filter_error_20260702)
    except Exception:
        pass
'''

insert_anchor = 'if __name__ == "__main__":'

if insert_anchor in text:
    text = text.replace(insert_anchor, patch + "\n\n" + insert_anchor, 1)
else:
    text = text.rstrip() + "\n" + patch + "\n"

path.write_text(text, encoding="utf-8")
print("patched sessions empty inactive filter")
