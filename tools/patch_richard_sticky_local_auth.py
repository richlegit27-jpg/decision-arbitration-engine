from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_RICHARD_STICKY_LOCAL_AUTH_20260703"

if marker in text:
    print("sticky local auth already installed")
else:
    addition = r'''

# --- NOVA_RICHARD_STICKY_LOCAL_AUTH_20260703 ---
try:
    from flask import request as _nova_sticky_auth_request_20260703
    from flask import session as _nova_sticky_auth_session_20260703

    @_nova_app.before_request
    def _nova_richard_sticky_local_auth_before_20260703():
        try:
            remembered = str(_nova_sticky_auth_request_20260703.cookies.get("nova_remember_username") or "").strip().lower()
            if remembered != "richard":
                return None

            # If Flask session was lost after refresh/redeploy, rebuild the local auth shape.
            if not _nova_sticky_auth_session_20260703.get("username"):
                _nova_sticky_auth_session_20260703["username"] = "richard"
            if not _nova_sticky_auth_session_20260703.get("user_id"):
                _nova_sticky_auth_session_20260703["user_id"] = "user_richard_sticky_local_auth"
            _nova_sticky_auth_session_20260703["authenticated"] = True
            _nova_sticky_auth_session_20260703["auth_mode"] = "local"
        except Exception:
            return None
        return None

    @_nova_app.after_request
    def _nova_richard_sticky_local_auth_after_20260703(response):
        try:
            username = str(
                _nova_sticky_auth_session_20260703.get("username")
                or _nova_sticky_auth_session_20260703.get("local_username")
                or ""
            ).strip().lower()

            if username == "richard":
                response.set_cookie(
                    "nova_remember_username",
                    "richard",
                    max_age=60 * 60 * 24 * 365,
                    httponly=True,
                    secure=True,
                    samesite="Lax",
                    path="/",
                )
        except Exception:
            pass
        return response

    print("[NOVA_RICHARD_STICKY_LOCAL_AUTH_20260703] installed")
except Exception as _nova_sticky_auth_error_20260703:
    try:
        print("[NOVA_RICHARD_STICKY_LOCAL_AUTH_20260703] failed:", _nova_sticky_auth_error_20260703)
    except Exception:
        pass
'''
    text = text.rstrip() + addition + "\n"
    path.write_text(text, encoding="utf-8")
    print("patched sticky local auth:", path)
