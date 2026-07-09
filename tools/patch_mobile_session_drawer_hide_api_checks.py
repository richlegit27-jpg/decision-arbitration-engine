from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")

js = js_path.read_text(encoding="utf-8")

def replace_function(src, name, replacement):
    start = src.find("function " + name + "(")
    if start < 0:
        raise SystemExit("missing function " + name)

    brace = src.find("{", start)
    depth = 0
    end = None

    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise SystemExit("missing function end " + name)

    return src[:start] + replacement + src[end:]

new_is_debug = r'''function isDebugSession(item) {
        var id = sessionId(item).toLowerCase();
        var title = String((item && item.title) || "").toLowerCase();
        var combined = id + " " + title;

        return (
            id.indexOf("regression_") === 0 ||
            id.indexOf("test_") === 0 ||
            id.indexOf("smoke_") === 0 ||
            id.indexOf("duplicate_") === 0 ||
            id.indexOf("debug_") === 0 ||
            id.indexOf("api_check_") === 0 ||
            combined.indexOf("regression") >= 0 ||
            combined.indexOf("smoke") >= 0 ||
            combined.indexOf("duplicate_api_check") >= 0 ||
            combined.indexOf("api check") >= 0
        );
    }'''

js = replace_function(js, "isDebugSession", new_is_debug)
js = js.rstrip() + "\n"
js_path.write_text(js, encoding="utf-8")

targets = [
    Path("app.py"),
    Path("templates/index.html"),
    Path("templates/mobile.html"),
]

for path in targets:
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")
    new_text = re.sub(
        r'nova-mobile-session-drawer-v2\.js\?v=[^"\']+',
        "nova-mobile-session-drawer-v2.js?v=20260703-stable-no-jitter-3-hide-api-checks",
        text,
    )

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print("updated", path)

print("hid duplicate/api-check sessions")
