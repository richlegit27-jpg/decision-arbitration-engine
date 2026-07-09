from pathlib import Path

js_path = Path("static/js/mobile/nova-mobile-sessions-rescue-final-v1.js")
template_path = Path("templates/mobile.html")

js = js_path.read_text(encoding="utf-8", errors="replace")
template = template_path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_MOBILE_SESSIONS_RESTORE_TIMEOUT_V5_20260703"
cache_marker = "sessions-restore-timeout-v5-20260703"

if marker not in js:
    addition = r'''

/* NOVA_MOBILE_SESSIONS_RESTORE_TIMEOUT_V5_20260703 */
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSIONS_RESTORE_TIMEOUT_V5_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_SESSIONS_RESTORE_TIMEOUT_V5_20260703__ = true;

    var ACTIVE_KEY = "nova_mobile_active_session_id";
    var DETAIL_TIMEOUT_MS = 4500;

    function textOf(value) {
        if (value == null) return "";
        if (typeof value === "string") return value;
        if (typeof value === "number" || typeof value === "boolean") return String(value);

        try {
            return JSON.stringify(value, null, 2);
        } catch (_) {
            return String(value);
        }
    }

    function getBaseRestore() {
        return window.NovaMobileSessionRestoreV4 || {};
    }

    function findSessionRecord(data, sessionId) {
        var base = getBaseRestore();

        if (typeof base.findSessionRecord === "function") {
            return base.findSessionRecord(data, sessionId);
        }

        if (!data) return null;

        if (data.id === sessionId || data.session_id === sessionId || data.active_session_id === sessionId) {
            return data;
        }

        if (data.session && (data.session.id === sessionId || data.session.session_id === sessionId)) {
            return data.session;
        }

        return null;
    }

    function pickMessages(data, sessionId) {
        var base = getBaseRestore();

        if (typeof base.pickMessages === "function") {
            return base.pickMessages(data, sessionId);
        }

        var record = findSessionRecord(data, sessionId);

        if (record && Array.isArray(record.messages)) return record.messages;
        if (record && Array.isArray(record.history)) return record.history;
        if (Array.isArray(data && data.messages)) return data.messages;
        if (Array.isArray(data && data.history)) return data.history;

        return [];
    }

    function renderMessages(messages) {
        var base = getBaseRestore();

        if (typeof base.renderMessages === "function") {
            return base.renderMessages(messages);
        }

        return false;
    }

    function updateTitle(sessionId, data) {
        var record = findSessionRecord(data, sessionId) || {};
        var title = record.title || data.title || sessionId;
        var label = "Session: " + title + " · " + sessionId.slice(-6);

        [
            "nova-mobile-session-title",
            "nova-mobile-active-session-title",
            "mobile-session-title"
        ].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.textContent = label;
        });

        var dataTitle = document.querySelector("[data-nova-session-title]");
        if (dataTitle) dataTitle.textContent = label;

        document.title = "Nova · " + title;
    }

    function closePanel() {
        if (
            window.NovaMobileSessionsRescueFinal &&
            typeof window.NovaMobileSessionsRescueFinal.close === "function"
        ) {
            window.NovaMobileSessionsRescueFinal.close();
            return;
        }

        var panel = document.getElementById("nova-mobile-sessions-panel");

        if (panel) {
            panel.hidden = true;
            panel.setAttribute("aria-hidden", "true");
            panel.style.display = "none";
        }
    }

    async function fetchJsonWithTimeout(url) {
        var controller = null;
        var timeoutId = null;

        if (typeof AbortController !== "undefined") {
            controller = new AbortController();
            timeoutId = setTimeout(function () {
                controller.abort();
            }, DETAIL_TIMEOUT_MS);
        }

        try {
            var response = await fetch(url, {
                credentials: "include",
                cache: "no-store",
                signal: controller ? controller.signal : undefined,
                headers: {
                    "Accept": "application/json"
                }
            });

            if (!response.ok) {
                throw new Error(url + " returned " + response.status);
            }

            return await response.json();
        } finally {
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
        }
    }

    async function fetchSessionData(sessionId) {
        var encoded = encodeURIComponent(sessionId);
        var urls = [
            "/api/chat/" + encoded,
            "/api/sessions/" + encoded,
            "/api/sessions?session_id=" + encoded,
            "/api/sessions"
        ];
        var errors = [];

        for (var i = 0; i < urls.length; i += 1) {
            try {
                console.log("[Nova Sessions Restore Timeout V5] fetch", urls[i]);
                return await fetchJsonWithTimeout(urls[i]);
            } catch (err) {
                errors.push(urls[i] + " -> " + (err && err.message ? err.message : String(err)));
                console.warn("[Nova Sessions Restore Timeout V5] fetch failed", urls[i], err);
            }
        }

        throw new Error("all session restore fetches failed: " + errors.join(" | "));
    }

    async function restore(sessionId) {
        sessionId = textOf(sessionId).trim();

        if (!sessionId) {
            console.warn("[Nova Sessions Restore Timeout V5] missing session id");
            return false;
        }

        localStorage.setItem(ACTIVE_KEY, sessionId);

        var data = await fetchSessionData(sessionId);
        var messages = pickMessages(data, sessionId);
        var rendered = renderMessages(messages);

        updateTitle(sessionId, data);
        closePanel();

        var last = {
            session_id: sessionId,
            message_count: messages.length,
            rendered: rendered,
            data: data
        };

        window.NovaMobileSessionRestoreV5.last = last;

        if (window.NovaMobileSessionRestoreV4) {
            window.NovaMobileSessionRestoreV4.last = last;
        }

        console.log("[Nova Sessions Restore Timeout V5] restored", sessionId, "messages", messages.length, "rendered", rendered);

        return true;
    }

    function extractSessionId(target) {
        var node = target.closest(
            "[data-session-id], [data-nova-session-id], [data-id], [data-session], .nova-sessions-rescue-row, .nova-mobile-session-row, .session-row, button, a, li, div"
        );

        if (!node) return "";

        var label = textOf(node.textContent).trim().toLowerCase();
        var nodeId = textOf(node.id).toLowerCase();

        if (
            nodeId.indexOf("close") !== -1 ||
            label === "close" ||
            label === "×" ||
            label.indexOf("delete") === 0 ||
            label.indexOf("rename") === 0 ||
            label.indexOf("pin") === 0
        ) {
            return "";
        }

        var attrs = [
            "data-session-id",
            "data-nova-session-id",
            "data-id",
            "data-session"
        ];

        for (var i = 0; i < attrs.length; i += 1) {
            var value = node.getAttribute && node.getAttribute(attrs[i]);

            if (value) {
                return value.trim();
            }
        }

        var text = textOf(node.textContent);
        var match = text.match(/(?:session|mobile)_[A-Za-z0-9_-]{8,}/);

        if (match) {
            return match[0];
        }

        return "";
    }

    document.addEventListener("click", function (event) {
        var panel = document.getElementById("nova-mobile-sessions-panel");

        if (!panel || !panel.contains(event.target)) {
            return;
        }

        var sessionId = extractSessionId(event.target);

        if (!sessionId) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        restore(sessionId).catch(function (err) {
            console.error("[Nova Sessions Restore Timeout V5] restore failed", err);
        });
    }, true);

    window.NovaMobileSessionRestoreV5 = {
        restore: restore,
        fetchSessionData: fetchSessionData,
        pickMessages: pickMessages,
        renderMessages: renderMessages,
        last: null
    };

    if (window.NovaMobileSessionRestoreV4) {
        window.NovaMobileSessionRestoreV4.restore = restore;
    }

    console.log("[Nova Sessions Restore Timeout V5] installed");
})();
'''
    js = js.rstrip() + addition + "\n"
    js_path.write_text(js, encoding="utf-8")
    print("patched:", js_path)
else:
    print("restore timeout v5 already installed")

if cache_marker not in template:
    old = "sessions-real-restore-v4-20260703"
    if old in template:
        template = template.replace(old, old + "-" + cache_marker, 1)
    else:
        template = template.replace("</body>", f"<!-- {cache_marker} -->\n</body>", 1)

    template_path.write_text(template.rstrip() + "\n", encoding="utf-8")
    print("bumped cache in:", template_path)
else:
    print("restore timeout v5 cache already installed")
