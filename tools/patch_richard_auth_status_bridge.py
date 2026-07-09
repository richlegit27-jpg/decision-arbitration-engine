from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "# --- NOVA_RICHARD_AUTH_STATUS_BRIDGE_20260703 ---"

if marker in text:
    print("Richard auth status bridge already installed")
else:
    addition = r'''

# --- NOVA_RICHARD_AUTH_STATUS_BRIDGE_20260703 ---
try:
    from flask import request as _nova_status_request_20260703
    from flask import session as _nova_status_session_20260703
    from flask import jsonify as _nova_status_jsonify_20260703

    def _nova_richard_status_user_20260703():
        return {
            "id": "user_richard_stable_local_login",
            "username": "richard",
            "email": "",
        }

    def _nova_richard_status_apply_20260703():
        _nova_status_session_20260703["username"] = "richard"
        _nova_status_session_20260703["user_id"] = "user_richard_stable_local_login"
        _nova_status_session_20260703["authenticated"] = True
        _nova_status_session_20260703["auth_mode"] = "local"
        _nova_status_session_20260703.permanent = True

    _nova_auth_status_wrapped_20260703 = False

    for _nova_rule_20260703 in list(app.url_map.iter_rules()):
        if str(_nova_rule_20260703) == "/api/auth/status":
            _nova_endpoint_20260703 = _nova_rule_20260703.endpoint
            _nova_original_status_20260703 = app.view_functions.get(_nova_endpoint_20260703)

            if _nova_original_status_20260703 and not getattr(
                _nova_original_status_20260703,
                "_nova_richard_auth_status_bridge_20260703",
                False,
            ):
                def _nova_auth_status_bridge_20260703(*args, **kwargs):
                    try:
                        remembered = str(
                            _nova_status_request_20260703.cookies.get("nova_richard_login") or ""
                        ).strip()

                        session_user = str(
                            _nova_status_session_20260703.get("username") or ""
                        ).strip().lower()

                        session_authed = bool(
                            _nova_status_session_20260703.get("authenticated")
                        )

                        if remembered == "1" or (session_authed and session_user == "richard"):
                            _nova_richard_status_apply_20260703()

                            response = _nova_status_jsonify_20260703({
                                "ok": True,
                                "authenticated": True,
                                "mode": "local",
                                "user": _nova_richard_status_user_20260703(),
                            })

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
                    except Exception:
                        pass

                    return _nova_original_status_20260703(*args, **kwargs)

                _nova_auth_status_bridge_20260703._nova_richard_auth_status_bridge_20260703 = True
                app.view_functions[_nova_endpoint_20260703] = _nova_auth_status_bridge_20260703
                _nova_auth_status_wrapped_20260703 = True

            break

    print("[NOVA_RICHARD_AUTH_STATUS_BRIDGE_20260703] installed", _nova_auth_status_wrapped_20260703)
except Exception as _nova_status_bridge_error_20260703:
    try:
        print("[NOVA_RICHARD_AUTH_STATUS_BRIDGE_20260703] failed:", _nova_status_bridge_error_20260703)
    except Exception:
        pass
'''
    text = text.rstrip() + addition + "\n"
    path.write_text(text, encoding="utf-8")
    print("patched Richard auth status bridge")
