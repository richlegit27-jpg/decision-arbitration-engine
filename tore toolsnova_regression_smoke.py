[1mdiff --git a/app.py b/app.py[m
[1mindex c597d5d..aefb05c 100644[m
[1m--- a/app.py[m
[1m+++ b/app.py[m
[36m@@ -3697,7 +3697,9 @@[m [mdef _nova_ensure_requested_session(session_id, title="Mobile Chat"):[m
         return None[m
 [m
     try:[m
[31m-        existing = session_service.get_session(target_session_id)[m
[32m+[m[32m        existing = session_service.get_session([m
[32m+[m[32m    target_session_id,[m
[32m+[m[32m)[m
         if existing:[m
             sessions = session_service.get_all()[m
             session_service.save(sessions, active=target_session_id)[m
[36m@@ -3707,9 +3709,26 @@[m [mdef _nova_ensure_requested_session(session_id, title="Mobile Chat"):[m
 [m
     now = _nova_mobile_now_iso()[m
 [m
[32m+[m[32m    owner_id = ""[m
[32m+[m
[32m+[m[32m    try:[m
[32m+[m[32m        from flask import g, session as flask_session[m
[32m+[m
[32m+[m[32m        auth_user = getattr(g, "nova_auth_user", None) or {}[m
[32m+[m
[32m+[m[32m        owner_id = str([m
[32m+[m[32m            auth_user.get("id")[m
[32m+[m[32m            or flask_session.get("nova_user_id")[m
[32m+[m[32m            or ""[m
[32m+[m[32m        ).strip()[m
[32m+[m
[32m+[m[32m    except Exception:[m
[32m+[m[32m        owner_id = ""[m
[32m+[m
     session = {[m
         "id": target_session_id,[m
         "title": str(title or "Mobile Chat").strip()[:80] or "Mobile Chat",[m
[32m+[m[32m        "user_id": owner_id,[m
         "messages": [],[m
         "pinned": False,[m
         "created_at": now,[m
[36m@@ -17616,9 +17635,17 @@[m [mtry:[m
         return None[m
 [m
     def _nova_phase4g_create_session_20260701(data, session_id, title=""):[m
[31m-        owner_id = str([m
[31m-            session.get("nova_user_id") or ""[m
[31m-        ).strip()[m
[32m+[m[32m        owner_id = ""[m
[32m+[m
[32m+[m[32m        try:[m
[32m+[m[32m            from flask import session as flask_session[m
[32m+[m
[32m+[m[32m            owner_id = str([m
[32m+[m[32m                flask_session.get("nova_user_id") or ""[m
[32m+[m[32m            ).strip()[m
[32m+[m
[32m+[m[32m        except Exception:[m
[32m+[m[32m            owner_id = ""[m
 [m
         session = {[m
             "id": session_id,[m
[36m@@ -17638,12 +17665,16 @@[m [mtry:[m
 [m
         if isinstance(data, dict):[m
             sessions = data.get("sessions")[m
[32m+[m
             if isinstance(sessions, list):[m
                 sessions.append(session)[m
[32m+[m
             elif isinstance(sessions, dict):[m
                 sessions[session_id] = session[m
[32m+[m
             else:[m
                 data["sessions"] = [session][m
[32m+[m
             return session[m
 [m
         if isinstance(data, list):[m
[1mdiff --git a/tools/nova_regression_smoke.py b/tools/nova_regression_smoke.py[m
[1mindex e96b55c..80a6811 100644[m
[1m--- a/tools/nova_regression_smoke.py[m
[1m+++ b/tools/nova_regression_smoke.py[m
[36m@@ -2,11 +2,45 @@[m
 import os[m
 import sys[m
 import time[m
[31m-from urllib import request, error[m
[31m-[m
[32m+[m[32mimport requests[m
 [m
 BASE_URL = "http://127.0.0.1:5001/api/chat"[m
 [m
[32m+[m[32mAUTH_URL = "http://127.0.0.1:5001/api/auth"[m
[32m+[m
[32m+[m[32mTEST_SUFFIX = str(int(time.time()))[m
[32m+[m
[32m+[m[32mTEST_USERNAME = f"nova_regression_test_{TEST_SUFFIX}"[m
[32m+[m[32mTEST_EMAIL = f"{TEST_USERNAME}@test.local"[m
[32m+[m[32mTEST_PASSWORD = "NovaRegression123!"[m
[32m+[m
[32m+[m[32mclient = requests.Session()[m
[32m+[m
[32m+[m[32mdef ensure_test_login():[m
[32m+[m[32m    register = client.post([m
[32m+[m[32m        f"{AUTH_URL}/register",[m
[32m+[m[32mjson={[m
[32m+[m[32m    "username": TEST_USERNAME,[m
[32m+[m[32m    "email": TEST_EMAIL,[m
[32m+[m[32m    "password": TEST_PASSWORD,[m
[32m+[m[32m},[m
[32m+[m[32m        timeout=30,[m
[32m+[m[32m    )[m
[32m+[m
[32m+[m[32m    if register.status_code not in (200, 400):[m
[32m+[m[32m        raise RuntimeError(register.text)[m
[32m+[m
[32m+[m[32m    login = client.post([m
[32m+[m[32m        f"{AUTH_URL}/login",[m
[32m+[m[32m        json={[m
[32m+[m[32m            "email": TEST_EMAIL,[m
[32m+[m[32m            "password": TEST_PASSWORD,[m
[32m+[m[32m        },[m
[32m+[m[32m        timeout=30,[m
[32m+[m[32m    )[m
[32m+[m
[32m+[m[32m    if login.status_code != 200:[m
[32m+[m[32m        raise RuntimeError(login.text)[m
 [m
 def post_chat(message, session_id, attachments=None, depth=8):[m
     payload = {[m
[36m@@ -16,20 +50,13 @@[m [mdef post_chat(message, session_id, attachments=None, depth=8):[m
         "attachments": attachments or [],[m
     }[m
 [m
[31m-    data = json.dumps(payload).encode("utf-8")[m
[31m-[m
[31m-    req = request.Request([m
[32m+[m[32m    response = client.post([m
         BASE_URL,[m
[31m-        data=data,[m
[31m-        headers={"Content-Type": "application/json"},[m
[31m-        method="POST",[m
[32m+[m[32m        json=payload,[m
[32m+[m[32m        timeout=60,[m
     )[m
 [m
[31m-    try:[m
[31m-        with request.urlopen(req, timeout=60) as res:[m
[31m-            return json.loads(res.read().decode("utf-8"))[m
[31m-    except error.URLError as exc:[m
[31m-        raise RuntimeError(f"Request failed for {message!r}: {exc}") from exc[m
[32m+[m[32m    return response.json()[m
 [m
 [m
 def text_of(result):[m
[36m@@ -66,6 +93,8 @@[m [mdef assert_true(name, condition, detail=""):[m
 [m
 [m
 def run():[m
[32m+[m[32m    ensure_test_login()[m
[32m+[m
     stamp = str(int(time.time()))[m
 [m
     # 1. Normal chat should stay chat, not execution.[m
