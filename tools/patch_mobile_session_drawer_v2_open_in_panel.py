from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")
app_path = Path("app.py")

js = js_path.read_text(encoding="utf-8")

def replace_function(src, name, replacement):
    start = src.find("function " + name + "(")
    if start < 0:
        start = src.find("async function " + name + "(")
    if start < 0:
        raise SystemExit("missing function " + name)

    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit("missing opening brace for " + name)

    depth = 0
    end = None
    for i in range(brace, len(src)):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise SystemExit("missing closing brace for " + name)

    return src[:start] + replacement + src[end:]

new_render = r'''function renderMessages(id, title, messages) {
        const ui = ensureUi();
        const panel = ui.panel;

        panel.setAttribute("data-open", "true");
        panel.innerHTML = "";

        const wrap = document.createElement("div");
        wrap.className = "nova-session-drawer-v2-detail";

        const back = document.createElement("button");
        back.type = "button";
        back.className = "nova-session-drawer-v2-row";
        back.textContent = "← Back to sessions";
        back.onclick = function (event) {
            try {
                event.preventDefault();
                event.stopPropagation();
            } catch (_) {}
            loadSessions();
        };
        wrap.appendChild(back);

        const header = document.createElement("div");
        header.className = "nova-session-drawer-v2-empty";
        header.textContent = "Session: " + (title || id) + " · " + messages.length + " messages";
        wrap.appendChild(header);

        if (!messages.length) {
            const empty = document.createElement("div");
            empty.className = "nova-session-drawer-v2-message";
            empty.setAttribute("data-role", "system");
            empty.textContent = "No messages in this session.";
            wrap.appendChild(empty);
        }

        messages.forEach(function (message) {
            const row = document.createElement("div");
            row.className = "nova-session-drawer-v2-message";
            row.setAttribute("data-role", messageRole(message));
            row.textContent = messageText(message) || "[empty message]";
            wrap.appendChild(row);
        });

        panel.appendChild(wrap);

        try {
            panel.scrollTop = 0;
        } catch (_) {}
    }'''

new_open = r'''async function openSession(item) {
        const id = sessionId(item);
        if (!id) return;

        const title = item.title || "New Chat";

        try {
            localStorage.setItem("nova_mobile_active_session_id", id);
            localStorage.setItem("nova_active_session_id", id);
        } catch (_) {}

        try {
            const url = new URL(window.location.href);
            url.searchParams.set("session_id", id);
            url.searchParams.set("v", "session-open-" + Date.now());
            history.replaceState(null, "", url.toString());
        } catch (_) {}

        const ui = ensureUi();
        const panel = ui.panel;
        panel.setAttribute("data-open", "true");
        panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Opening session...</div>";

        try {
            const detail = await fetchJson("/api/sessions/" + encodeURIComponent(id));
            const session = detail.session || detail;
            const messages = normalizeMessages(detail);
            renderMessages(id, session.title || title, messages);
            log("opened", id, messages.length);
        } catch (err) {
            panel.setAttribute("data-open", "true");
            panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Session open failed. See console.</div>";
            log("open failed", err);
        }
    }'''

js = replace_function(js, "renderMessages", new_render)
js = replace_function(js, "openSession", new_open)

marker = "NOVA_SESSION_DRAWER_V2_OPEN_IN_PANEL_STYLE_20260703"
if marker not in js:
    extra = r'''

// NOVA_SESSION_DRAWER_V2_OPEN_IN_PANEL_STYLE_20260703
(function () {
    "use strict";

    function installOpenInPanelStyle() {
        try {
            let style = document.getElementById("nova-session-drawer-v2-open-in-panel-style");
            if (!style) {
                style = document.createElement("style");
                style.id = "nova-session-drawer-v2-open-in-panel-style";
                document.head.appendChild(style);
            }

            style.textContent = `
#nova-session-drawer-v2-panel .nova-session-drawer-v2-detail {
    display: block !important;
    padding: 8px !important;
}

#nova-session-drawer-v2-panel .nova-session-drawer-v2-message {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    white-space: pre-wrap !important;
    word-break: break-word !important;
    border-radius: 10px !important;
    padding: 10px !important;
    margin: 8px 0 !important;
    font-size: 13px !important;
    line-height: 1.35 !important;
}

#nova-session-drawer-v2-panel .nova-session-drawer-v2-message[data-role="user"] {
    background: rgba(139, 92, 246, 0.22) !important;
}

#nova-session-drawer-v2-panel .nova-session-drawer-v2-message[data-role="assistant"] {
    background: rgba(255, 255, 255, 0.10) !important;
}

#nova-session-drawer-v2-panel .nova-session-drawer-v2-message[data-role="system"] {
    background: rgba(255, 255, 255, 0.06) !important;
}
`;
        } catch (_) {}
    }

    installOpenInPanelStyle();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", installOpenInPanelStyle);
    }
})();
'''
    js = js.rstrip() + "\n" + extra + "\n"

js = js.rstrip() + "\n"
js_path.write_text(js, encoding="utf-8")

app = app_path.read_text(encoding="utf-8")
app2 = re.sub(
    r'nova-mobile-session-drawer-v2\.js\?v=[^"\']+',
    'nova-mobile-session-drawer-v2.js?v=20260703-open-in-panel',
    app,
)
if app2 == app:
    raise SystemExit("drawer script cache string not found in app.py")

app_path.write_text(app2, encoding="utf-8")

print("patched drawer open-in-panel behavior")
