from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "NOVA_FINAL_SESSIONS_EMPTY_FILTER_20260702"

if marker in text:
    print("final sessions empty filter already installed")
    raise SystemExit(0)

patch = r'''

# ============================================================
# NOVA_FINAL_SESSIONS_EMPTY_FILTER_20260702
# Final-pass /api/sessions cleanup.
# Removes inactive empty sessions from both items and sessions.
# Keeps active, pinned, non-empty, or active-execution sessions.
# ============================================================
try:
    import json as _nova_final_sessions_json
    from flask import request as _nova_final_sessions_request

    def _nova_final_sessions_count_20260702(item):
        try:
            return int(item.get("message_count") or 0)
        except Exception:
            return 0

    def _nova_final_sessions_keep_20260702(item, active_session_id):
        try:
            if not isinstance(item, dict):
                return False

            sid = str(item.get("id") or "")

            if active_session_id and sid == active_session_id:
                return True

            if item.get("pinned") is True:
                return True

            if _nova_final_sessions_count_20260702(item) > 0:
                return True

            active_execution = item.get("active_execution")
            if isinstance(active_execution, dict) and len(active_execution) > 0:
                return True

            return False
        except Exception:
            return True

    def _nova_final_sessions_empty_filter_20260702(response):
        try:
            if _nova_final_sessions_request.path.rstrip("/") != "/api/sessions":
                return response

            if getattr(response, "status_code", 200) >= 400:
                return response

            data = response.get_json(silent=True)
            if not isinstance(data, dict):
                try:
                    raw = response.get_data(as_text=True)
                    data = _nova_final_sessions_json.loads(raw)
                except Exception:
                    return response

            debug = data.get("debug")
            if not isinstance(debug, dict):
                debug = {}

            active_session_id = str(
                data.get("active_session_id")
                or data.get("session_id")
                or debug.get("active_session_id")
                or debug.get("session_id")
                or debug.get("requested_session_id")
                or ""
            )

            total_hidden = 0
            changed = False

            for key in ("items", "sessions"):
                original = data.get(key)
                if not isinstance(original, list):
                    continue

                filtered = [
                    item for item in original
                    if _nova_final_sessions_keep_20260702(item, active_session_id)
                ]

                hidden = max(0, len(original) - len(filtered))
                if hidden:
                    total_hidden += hidden
                    data[key] = filtered
                    changed = True

            if changed:
                visible_count = 0
                if isinstance(data.get("sessions"), list):
                    visible_count = len(data["sessions"])
                elif isinstance(data.get("items"), list):
                    visible_count = len(data["items"])

                debug["final_empty_inactive_session_filter"] = True
                debug["hidden_empty_inactive_session_count"] = total_hidden
                debug["returned_session_count"] = visible_count
                data["debug"] = debug

                payload = _nova_final_sessions_json.dumps(data, ensure_ascii=False)
                response.set_data(payload)
                response.mimetype = "application/json"

                try:
                    response.headers["Content-Length"] = str(len(payload.encode("utf-8")))
                except Exception:
                    pass

            return response
        except Exception as exc:
            try:
                print("[NOVA_FINAL_SESSIONS_EMPTY_FILTER_20260702] failed:", exc)
            except Exception:
                pass
            return response

    # Append, do not insert. Flask runs after_request funcs in reverse order,
    # so appending makes this finalizer run early enough to survive older wrappers.
    app.after_request(_nova_final_sessions_empty_filter_20260702)
    print("[NOVA_FINAL_SESSIONS_EMPTY_FILTER_20260702] installed")

except Exception as _nova_final_sessions_empty_filter_error_20260702:
    try:
        print("[NOVA_FINAL_SESSIONS_EMPTY_FILTER_20260702] outer failed:", _nova_final_sessions_empty_filter_error_20260702)
    except Exception:
        pass
'''

insert_anchor = 'if __name__ == "__main__":'

if insert_anchor in text:
    text = text.replace(insert_anchor, patch + "\n\n" + insert_anchor, 1)
else:
    text = text.rstrip() + "\n" + patch + "\n"

path.write_text(text, encoding="utf-8")
print("patched final sessions empty filter")
