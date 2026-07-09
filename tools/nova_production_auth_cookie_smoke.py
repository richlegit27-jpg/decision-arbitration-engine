import json
import sys
import time
from http.cookies import SimpleCookie

import requests


BASE = "https://decision-arbitration-engine-production.up.railway.app"


def pretty(obj):
    try:
        return json.dumps(obj, indent=2, sort_keys=True)
    except Exception:
        return str(obj)


def show_response(label, response):
    print("")
    print(f"=== {label} ===")
    print("STATUS:", response.status_code)
    print("SET-COOKIE:", response.headers.get("Set-Cookie"))
    print("BODY:", response.text[:2000])


def show_cookies(label, session):
    print("")
    print(f"=== {label} ===")
    if not session.cookies:
        print("(empty)")
        return

    for cookie in session.cookies:
        print(
            f"name={cookie.name} value_len={len(cookie.value or '')} "
            f"domain={cookie.domain} path={cookie.path} secure={cookie.secure}"
        )


def get_json(response):
    try:
        return response.json()
    except Exception:
        return {}


def main():
    stamp = int(time.time())
    username = f"auth_cookie_probe_{stamp}"
    email = f"{username}@example.com"
    password = "testpass123"

    print("NOVA PRODUCTION AUTH COOKIE SMOKE")
    print("================================")
    print("BASE", BASE)
    print("USER", username)

    health = requests.get(f"{BASE}/api/health", timeout=20)
    show_response("HEALTH BEFORE", health)

    session = requests.Session()

    register_body = {
        "username": username,
        "email": email,
        "password": password,
    }

    register = session.post(
        f"{BASE}/api/auth/register",
        json=register_body,
        timeout=20,
    )
    show_response("REGISTER", register)
    show_cookies("COOKIE JAR AFTER REGISTER", session)

    status_after_register = session.get(
        f"{BASE}/api/auth/status",
        timeout=20,
    )
    show_response("STATUS AFTER REGISTER SAME SESSION", status_after_register)
    show_cookies("COOKIE JAR AFTER REGISTER STATUS", session)

    login_session = requests.Session()

    login = login_session.post(
        f"{BASE}/api/auth/login",
        json={
            "username": username,
            "password": password,
        },
        timeout=20,
    )
    show_response("LOGIN", login)
    show_cookies("COOKIE JAR AFTER LOGIN", login_session)

    status_after_login = login_session.get(
        f"{BASE}/api/auth/status",
        timeout=20,
    )
    show_response("STATUS AFTER LOGIN SAME SESSION", status_after_login)
    show_cookies("COOKIE JAR AFTER LOGIN STATUS", login_session)

    health_after = requests.get(f"{BASE}/api/health", timeout=20)
    show_response("HEALTH AFTER", health_after)

    register_json = get_json(register)
    status_register_json = get_json(status_after_register)
    login_json = get_json(login)
    status_login_json = get_json(status_after_login)

    failed = []

    if register.status_code != 200 or not register_json.get("authenticated"):
        failed.append("register did not authenticate")

    if not status_register_json.get("authenticated"):
        failed.append("status after register did not stay authenticated")

    if login.status_code != 200 or not login_json.get("authenticated"):
        failed.append("login did not authenticate")

    if not status_login_json.get("authenticated"):
        failed.append("status after login did not stay authenticated")

    if failed:
        print("")
        print("NOVA PRODUCTION AUTH COOKIE SMOKE FAILED")
        for item in failed:
            print("-", item)
        return 1

    print("")
    print("NOVA PRODUCTION AUTH COOKIE SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
