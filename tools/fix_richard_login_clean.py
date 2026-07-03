from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

def remove_marker_block(src, marker):
    start = src.find(marker)
    if start == -1:
        return src, False

    # include the line start before the marker
    line_start = src.rfind("\n", 0, start)
    if line_start == -1:
        line_start = 0

    next_candidates = []
    for token in ("\n# --- NOVA_", "\n# === NOVA_"):
        pos = src.find(token, start + len(marker))
        if pos != -1:
            next_candidates.append(pos)

    end = min(next_candidates) if next_candidates else len(src)
    return src[:line_start] + src[end:], True

text, removed_sticky = remove_marker_block(text, "# --- NOVA_RICHARD_STICKY_LOCAL_AUTH_20260703 ---")
text, removed_stable = remove_marker_block(text, "# --- NOVA_RICHARD_STABLE_LOCAL_LOGIN_20260703 ---")

clean_marker = "# --- NOVA_RICHARD_LOCAL_LOGIN_CLEAN_20260703 ---"

if clean_marker not in text:
    addition = r'''

# --- NOVA_RICHARD_LOCAL_LOGIN_CLEAN_20260703 ---
try:
    from flask import request as _nova_login_request_20260703
    from flask import session as _nova_login_session_20260703
    from flask import jsonify as _nova_login_jsonify_20260703
    from flask import redirect as _nova_login_redirect_20260703

    def _nova_richard_login_apply_clean_20260703():
        _nova_login_session_20260703["username"] = "richard"
        _nova_login_session_20260703["user_id"] = "user_richard_stable_local_login"
        _nova_login_session_20260703["authenticated"] = True
        _nova_login_session_20260703["auth_mode"] = "local"
        _nova_login_session_20260703.permanent = True

    @app.before_request
    def _nova_richard_cookie_login_before_clean_20260703():
        try:
            remembered = str(_nova_login_request_20260703.cookies.get("nova_richard_login") or "").strip()
            if remembered == "1":
                _nova_richard_login_apply_clean_20260703()
        except Exception:
            pass
        return None

    @app.route("/richard-login", methods=["GET"])
    @app.route("/api/auth/richard-login", methods=["GET", "POST"])
    def _nova_richard_login_route_clean_20260703():
        _nova_richard_login_apply_clean_20260703()

        wants_json = (
            _nova_login_request_20260703.path.startswith("/api/")
            or "application/json" in str(_nova_login_request_20260703.headers.get("Accept") or "").lower()
        )

        if wants_json:
            response = _nova_login_jsonify_20260703({
                "ok": True,
                "authenticated": True,
                "mode": "local",
                "user": {
                    "id": "user_richard_stable_local_login",
                    "username": "richard",
                    "email": "",
                },
            })
        else:
            response = _nova_login_redirect_20260703("/mobile")

        response.set_cookie(
            "nova_richard_login",
            "1",
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            secure=True,
            samesite="Lax",
            path="/",
        )
        return response

    print("[NOVA_RICHARD_LOCAL_LOGIN_CLEAN_20260703] installed")
except Exception as _nova_login_clean_error_20260703:
    try:
        print("[NOVA_RICHARD_LOCAL_LOGIN_CLEAN_20260703] failed:", _nova_login_clean_error_20260703)
    except Exception:
        pass
'''
    text = text.rstrip() + addition + "\n"

path.write_text(text.rstrip() + "\n", encoding="utf-8")

print("removed sticky block:", removed_sticky)
print("removed stable block:", removed_stable)
print("still has broken _nova_app login:", "_nova_app.before_request" in text[text.find(clean_marker):] if clean_marker in text else False)
print("has clean login route:", clean_marker in text)
print("has /api/auth/richard-login:", "/api/auth/richard-login" in text)
