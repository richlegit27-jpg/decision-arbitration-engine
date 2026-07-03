from pathlib import Path

app_path = Path("app.py")
js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")

app = app_path.read_text(encoding="utf-8")
old = 'nova-mobile-session-drawer-v2.js?v=20260703-drawer-v2'
new = 'nova-mobile-session-drawer-v2.js?v=20260703-top-left-lock-e8ef92c'

if old in app:
    app = app.replace(old, new)
    app_path.write_text(app, encoding="utf-8")
    print("updated app.py drawer script cache version")
elif new in app:
    print("app.py drawer script cache version already updated")
else:
    raise SystemExit("could not find drawer script version in app.py")

js = js_path.read_text(encoding="utf-8")
js = js.rstrip() + "\n"
js_path.write_text(js, encoding="utf-8")
print("cleaned trailing blank lines in drawer js")
