from pathlib import Path

print("NOVA AUTH PERSISTENCE AUDIT")
print("===========================")

targets = [
    Path("app.py"),
    *Path("nova_backend").rglob("*.py"),
    *Path("static").rglob("*.js"),
    *Path("templates").rglob("*.html"),
]

needles = [
    "SECRET_KEY",
    "secret_key",
    "app.secret_key",
    "session[",
    "flask.session",
    "set_cookie",
    "delete_cookie",
    "clear()",
    "localStorage.clear",
    "sessionStorage.clear",
    "login",
    "logout",
    "register",
    "signup",
    "users.json",
    "nova_users",
    "user_id",
    "username",
    "password",
    "auth",
]

for path in targets:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    lines = text.splitlines()
    hits = []

    for index, line in enumerate(lines, start=1):
        low = line.lower()
        for needle in needles:
            if needle.lower() in low:
                hits.append((index, line.strip()))
                break

    if hits:
        print("")
        print("FILE", path)
        for index, line in hits[:80]:
            print(f"{index}: {line}")
        if len(hits) > 80:
            print(f"... +{len(hits) - 80} more")

print("")
print("NOVA AUTH PERSISTENCE AUDIT COMPLETE")
