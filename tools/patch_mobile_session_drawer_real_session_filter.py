from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")

if not js_path.exists():
    raise SystemExit("missing drawer file")

js = js_path.read_text(encoding="utf-8")

marker = "NOVA_SESSION_DRAWER_V2_REAL_SESSION_FILTER_20260703"

if marker not in js:
    insert_before = "    function messagesFrom(payload) {"
    if insert_before not in js:
        raise SystemExit("missing messagesFrom anchor")

    helper = r'''
    // NOVA_SESSION_DRAWER_V2_REAL_SESSION_FILTER_20260703
    function showDebugSessions() {
        try {
            var params = new URLSearchParams(window.location.search);
            if (
                params.get("debug_sessions") === "1" ||
                params.get("show_debug_sessions") === "1" ||
                params.get("dev_sessions") === "1"
            ) {
                return true;
            }

            return localStorage.getItem("nova_show_debug_sessions") === "1";
        } catch (_) {
            return false;
        }
    }

    function isDebugSession(item) {
        var id = sessionId(item).toLowerCase();
        var title = String((item && item.title) || "").toLowerCase();
        var combined = id + " " + title;

        return (
            id.indexOf("regression_") === 0 ||
            id.indexOf("test_") === 0 ||
            id.indexOf("smoke_") === 0 ||
            combined.indexOf("regression") >= 0 ||
            combined.indexOf("smoke") >= 0
        );
    }

    function shouldShowSessionInDrawer(item) {
        if (!item) return false;

        var id = sessionId(item);
        if (!id) return false;

        if (isDebugSession(item) && !showDebugSessions()) {
            return false;
        }

        return true;
    }

    function sessionKind(item) {
        var id = sessionId(item).toLowerCase();

        if (id.indexOf("mobile_") === 0) return "Mobile";
        if (id.indexOf("session_") === 0) return "Legacy";
        if (id.indexOf("regression_") === 0) return "Regression";
        if (id.indexOf("test_") === 0) return "Test";
        if (id.indexOf("smoke_") === 0) return "Smoke";

        return "Session";
    }

    function sessionSortRank(item) {
        var kind = sessionKind(item);

        if (kind === "Mobile") return 0;
        if (kind === "Legacy") return 1;
        if (kind === "Session") return 2;
        return 9;
    }

    function compareDrawerSessions(a, b) {
        var ar = sessionSortRank(a);
        var br = sessionSortRank(b);

        if (ar !== br) return ar - br;

        var at = String((a && (a.updated_at || a.created_at || a.last_updated)) || "");
        var bt = String((b && (b.updated_at || b.created_at || b.last_updated)) || "");

        return bt.localeCompare(at);
    }

'''
    js = js.replace(insert_before, helper + insert_before, 1)

js = js.replace(
    "var sessions = sessionsFrom(payload);",
    "var allSessions = sessionsFrom(payload);\n            var sessions = allSessions.filter(shouldShowSessionInDrawer).sort(compareDrawerSessions);\n            var hiddenDebugCount = allSessions.length - sessions.length;",
    1
)

js = js.replace(
    'head.textContent = "Sessions: " + sessions.length;',
    'head.textContent = "Sessions: " + sessions.length + (hiddenDebugCount ? " · hidden tests: " + hiddenDebugCount : "");',
    1
)

js = js.replace(
    'meta.textContent = (count === undefined || count === null ? "?" : count) + " messages · " + id;',
    'meta.textContent = sessionKind(item) + " · " + (count === undefined || count === null ? "?" : count) + " messages · " + id;',
    1
)

js = js.rstrip() + "\n"
js_path.write_text(js, encoding="utf-8")

# Cache-bust every served script ref without touching old patch tool files.
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
        r"nova-mobile-session-drawer-v2\.js\?v=[^\"'<>\\s]+",
        "nova-mobile-session-drawer-v2.js?v=20260703-stable-no-jitter-2-session-filter",
        text,
    )

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print("updated", path)

print("patched drawer session filter")
