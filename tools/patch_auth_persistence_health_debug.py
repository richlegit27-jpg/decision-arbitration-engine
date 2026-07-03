from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "NOVA_AUTH_PERSISTENCE_HEALTH_DEBUG_20260702"

if marker in text:
    print("auth persistence health debug already installed")
    raise SystemExit(0)

patch = r'''

# ============================================================
# NOVA_AUTH_PERSISTENCE_HEALTH_DEBUG_20260702
# Adds auth persistence visibility to /api/health:
# - where auth users are stored
# - whether auth users file exists
# - whether Flask secret file exists
# - number of stored users
# Does not expose passwords, hashes, salts, or secret values.
# ============================================================
try:
    import json as _nova_auth_health_json_20260702
    from pathlib import Path as _NovaAuthHealthPath20260702

    def _nova_auth_health_data_dir_20260702():
        try:
            return DATA_DIR
        except Exception:
            try:
                return _NovaAuthHealthPath20260702(__file__).resolve().parent / "data"
            except Exception:
                return _NovaAuthHealthPath20260702("data")

    def _nova_auth_health_count_users_20260702(path):
        try:
            if not path.exists():
                return 0

            payload = _nova_auth_health_json_20260702.loads(path.read_text(encoding="utf-8") or "{}")

            if isinstance(payload, dict):
                users = payload.get("users")
                if isinstance(users, list):
                    return len(users)
                if isinstance(users, dict):
                    return len(users)
                return len(payload)

            if isinstance(payload, list):
                return len(payload)
        except Exception:
            pass

        return 0

    def _nova_auth_health_patch_payload_20260702(payload):
        try:
            if not isinstance(payload, dict):
                return payload

            data_dir = _nova_auth_health_data_dir_20260702()
            users_file = data_dir / "nova_auth_users.json"
            secret_file = data_dir / "nova_flask_secret.key"

            payload["auth_data_dir"] = str(data_dir)
            payload["auth_users_file"] = str(users_file)
            payload["auth_users_file_exists"] = bool(users_file.exists())
            payload["auth_users_count"] = _nova_auth_health_count_users_20260702(users_file)
            payload["auth_secret_file"] = str(secret_file)
            payload["auth_secret_file_exists"] = bool(secret_file.exists())
            payload["flask_secret_key_configured"] = bool(getattr(app, "secret_key", None))
        except Exception as exc:
            try:
                payload["auth_persistence_debug_error"] = str(exc)
            except Exception:
                pass

        return payload

    def _nova_auth_health_after_request_20260702(response):
        try:
            from flask import request as _nova_auth_health_request_20260702

            if _nova_auth_health_request_20260702.path.rstrip("/") != "/api/health":
                return response

            if getattr(response, "status_code", 200) >= 400:
                return response

            payload = response.get_json(silent=True)

            if not isinstance(payload, dict):
                return response

            payload = _nova_auth_health_patch_payload_20260702(payload)

            body = _nova_auth_health_json_20260702.dumps(payload, ensure_ascii=False)
            response.set_data(body)
            response.mimetype = "application/json"

            try:
                response.headers["Content-Length"] = str(len(body.encode("utf-8")))
            except Exception:
                pass

            return response
        except Exception as exc:
            try:
                print("[NOVA_AUTH_PERSISTENCE_HEALTH_DEBUG_20260702] failed:", exc)
            except Exception:
                pass
            return response

    try:
        app.after_request(_nova_auth_health_after_request_20260702)
        print("[NOVA_AUTH_PERSISTENCE_HEALTH_DEBUG_20260702] installed")
    except Exception as _nova_auth_health_install_error_20260702:
        try:
            print("[NOVA_AUTH_PERSISTENCE_HEALTH_DEBUG_20260702] install failed:", _nova_auth_health_install_error_20260702)
        except Exception:
            pass

except Exception as _nova_auth_health_outer_error_20260702:
    try:
        print("[NOVA_AUTH_PERSISTENCE_HEALTH_DEBUG_20260702] outer failed:", _nova_auth_health_outer_error_20260702)
    except Exception:
        pass
'''

anchor = 'if __name__ == "__main__":'

if anchor in text:
    text = text.replace(anchor, patch + "\n\n" + anchor, 1)
else:
    text = text.rstrip() + "\n" + patch + "\n"

path.write_text(text, encoding="utf-8")
print("patched auth persistence health debug")
