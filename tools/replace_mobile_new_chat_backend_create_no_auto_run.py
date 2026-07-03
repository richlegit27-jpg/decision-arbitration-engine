from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-new-chat-backend-create-v1.js")
app_path = Path("app.py")

if not js_path.exists():
    raise SystemExit("missing " + str(js_path))

js = r'''
(function () {
    "use strict";

    const VERSION = "backend-create-v2-no-auto-run-20260703";

    if (window.__NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_V2_NO_AUTO_RUN_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_V2_NO_AUTO_RUN_20260703__ = VERSION;

    let inFlight = false;
    let lastRunAt = 0;

    function log() {
        try {
            console.log.apply(console, ["[Nova Mobile New Chat Backend Create V2]"].concat(Array.from(arguments)));
        } catch (_) {}
    }

    function extractSessionId(payload) {
        if (!payload) return "";

        return String(
            payload.session_id ||
            payload.id ||
            payload.active_session_id ||
            (payload.session && (payload.session.session_id || payload.session.id)) ||
            (payload.data && (payload.data.session_id || payload.data.id || payload.data.active_session_id)) ||
            ""
        ).trim();
    }

    function createBackendSession() {
        return fetch("/api/sessions/new", {
            method: "POST",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                source: "mobile_new_chat_backend_create_v2",
                title: "New Chat"
            })
        }).then(function (response) {
            if (!response.ok) {
                throw new Error("Session create HTTP " + response.status);
            }
            return response.json();
        }).then(function (payload) {
            const id = extractSessionId(payload);

            if (!id) {
                throw new Error("Session create returned no usable id: " + JSON.stringify(payload).slice(0, 600));
            }

            return {
                id: id,
                payload: payload
            };
        });
    }

    function clearVisibleChat() {
        try {
            const candidates = [
                "#messages",
                "#chat-messages",
                "#nova-chat-messages",
                "#nova-mobile-messages",
                ".messages",
                ".chat-messages",
                ".nova-mobile-messages"
            ];

            candidates.forEach(function (selector) {
                document.querySelectorAll(selector).forEach(function (el) {
                    if (el && el.id !== "nova-session-drawer-v2-panel") {
                        el.innerHTML = "";
                    }
                });
            });
        } catch (_) {}
    }

    function goToSession(id) {
        try {
            localStorage.setItem("nova_mobile_active_session_id", id);
            localStorage.setItem("nova_active_session_id", id);
        } catch (_) {}

        clearVisibleChat();

        try {
            const url = new URL(window.location.href);
            url.pathname = "/mobile";
            url.searchParams.set("session_id", id);
            url.searchParams.set("v", "new-chat-backend-create-v2-" + Date.now());
            window.location.href = url.toString();
        } catch (_) {
            window.location.href = "/mobile?session_id=" + encodeURIComponent(id) + "&v=new-chat-backend-create-v2-" + Date.now();
        }
    }

    function runNewChatFlow(event) {
        try {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
            }
        } catch (_) {}

        const now = Date.now();

        if (inFlight || now - lastRunAt < 1500) {
            log("ignored duplicate new-chat request");
            return;
        }

        inFlight = true;
        lastRunAt = now;

        createBackendSession().then(function (result) {
            log("created", result.id);
            goToSession(result.id);
        }).catch(function (err) {
            log("failed once", err);
        }).finally(function () {
            setTimeout(function () {
                inFlight = false;
            }, 1000);
        });
    }

    function looksLikeNewChatButton(el) {
        if (!el) return false;

        const text = String(el.textContent || "").trim().toLowerCase();
        const aria = String(el.getAttribute("aria-label") || "").trim().toLowerCase();
        const title = String(el.getAttribute("title") || "").trim().toLowerCase();
        const id = String(el.id || "").toLowerCase();
        const klass = String(el.className || "").toLowerCase();

        const haystack = [text, aria, title, id, klass].join(" ");

        if (haystack.indexOf("session") >= 0 && haystack.indexOf("new") < 0) {
            return false;
        }

        return (
            haystack.indexOf("new chat") >= 0 ||
            haystack.indexOf("new-chat") >= 0 ||
            haystack.indexOf("start new") >= 0 ||
            haystack === "+" ||
            text === "+"
        );
    }

    function installClickCapture() {
        if (window.__NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_V2_CLICK_CAPTURE_INSTALLED_20260703__) {
            return;
        }

        window.__NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_V2_CLICK_CAPTURE_INSTALLED_20260703__ = true;

        document.addEventListener("click", function (event) {
            try {
                const target = event.target;
                const button = target && target.closest && target.closest("button, a, [role='button']");
                if (!button) return;

                if (button.closest && button.closest("#nova-session-drawer-v2-panel")) {
                    return;
                }

                if (!looksLikeNewChatButton(button)) {
                    return;
                }

                runNewChatFlow(event);
            } catch (err) {
                log("click capture failed", err);
            }
        }, true);
    }

    // Important: no automatic create on page load.
    // New Chat now only runs from a real New Chat click.
    installClickCapture();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", installClickCapture);
    }

    log("ready", VERSION);
})();
'''

js_path.write_text(js.strip() + "\n", encoding="utf-8")

app = app_path.read_text(encoding="utf-8")
app2 = re.sub(
    r"nova-mobile-new-chat-backend-create-v1\.js\?v=[^\"']+",
    "nova-mobile-new-chat-backend-create-v1.js?v=backend-create-v2-no-auto-run-20260703",
    app,
)

if app2 == app:
    print("warning: app.py script cache string not found; file replaced anyway")
else:
    app_path.write_text(app2, encoding="utf-8")

print("replaced new chat backend create with no-auto-run v2")
