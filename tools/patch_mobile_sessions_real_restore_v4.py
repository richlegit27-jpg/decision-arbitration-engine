from pathlib import Path

js_path = Path("static/js/mobile/nova-mobile-sessions-rescue-final-v1.js")
template_path = Path("templates/mobile.html")

js = js_path.read_text(encoding="utf-8", errors="replace")
template = template_path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_MOBILE_SESSIONS_RESTORE_REAL_BACKEND_V4_20260703"
cache_marker = "sessions-real-restore-v4-20260703"

if marker not in js:
    addition = r'''

/* NOVA_MOBILE_SESSIONS_RESTORE_REAL_BACKEND_V4_20260703 */
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSIONS_RESTORE_REAL_BACKEND_V4_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_SESSIONS_RESTORE_REAL_BACKEND_V4_20260703__ = true;

    var ACTIVE_KEY = "nova_mobile_active_session_id";

    function $(id) {
        return document.getElementById(id);
    }

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

    function roleOf(message) {
        var role = textOf(message && (message.role || message.sender || message.author || message.type)).toLowerCase();

        if (role.indexOf("assistant") !== -1 || role.indexOf("nova") !== -1 || role.indexOf("bot") !== -1) {
            return "assistant";
        }

        if (role.indexOf("system") !== -1) {
            return "system";
        }

        return "user";
    }

    function messageText(message) {
        if (!message) return "";

        return textOf(
            message.text ||
            message.content ||
            message.message ||
            message.body ||
            message.answer ||
            message.response ||
            (message.assistant_message && (message.assistant_message.text || message.assistant_message.content)) ||
            (message.user_message && (message.user_message.text || message.user_message.content)) ||
            ""
        ).trim();
    }

    function attachmentsOf(message) {
        if (!message) return [];

        var attachments = message.attachments || message.files || message.images || [];

        if (!Array.isArray(attachments)) {
            return [];
        }

        return attachments;
    }

    function findSessionRecord(data, sessionId) {
        if (!data) return null;

        if (data.id === sessionId || data.session_id === sessionId || data.active_session_id === sessionId) {
            if (Array.isArray(data.messages)) return data;
        }

        if (data.session && (data.session.id === sessionId || data.session.session_id === sessionId)) {
            return data.session;
        }

        var pools = [
            data.sessions,
            data.items,
            data.data && data.data.sessions,
            data.data && data.data.items,
            data.result && data.result.sessions,
            data.result && data.result.items
        ];

        for (var p = 0; p < pools.length; p += 1) {
            var pool = pools[p];

            if (!Array.isArray(pool)) continue;

            for (var i = 0; i < pool.length; i += 1) {
                var candidate = pool[i] || {};

                if (
                    candidate.id === sessionId ||
                    candidate.session_id === sessionId ||
                    candidate.active_session_id === sessionId
                ) {
                    return candidate;
                }
            }
        }

        return null;
    }

    function pickMessages(data, sessionId) {
        var record = findSessionRecord(data, sessionId);

        if (record && Array.isArray(record.messages)) {
            return record.messages;
        }

        if (record && Array.isArray(record.history)) {
            return record.history;
        }

        if (Array.isArray(data && data.messages)) {
            return data.messages;
        }

        if (Array.isArray(data && data.history)) {
            return data.history;
        }

        return [];
    }

    function findMessageRoot() {
        var selectors = [
            "#mobileChatMessages",
            "#nova-mobile-chat-messages",
            "#novaMobileMessages",
            "#nova-mobile-messages",
            "#chatMessages",
            "#messages",
            "#chat-log",
            "#nova-chat-log",
            ".mobile-chat-messages",
            ".nova-mobile-chat-messages",
            ".nova-mobile-messages",
            ".chat-messages",
            ".messages",
            ".chat-log",
            "[data-nova-chat-messages]",
            "[data-chat-messages]"
        ];

        for (var i = 0; i < selectors.length; i += 1) {
            var el = document.querySelector(selectors[i]);

            if (el) {
                return el;
            }
        }

        return null;
    }

    function appendAttachment(container, attachment) {
        var url = attachment && (attachment.url || attachment.file_url || attachment.path || attachment.href);
        var name = attachment && (attachment.name || attachment.filename || attachment.stored_name || "attachment");

        if (!url) return;

        var lower = textOf(url).toLowerCase();

        if (
            lower.indexOf(".png") !== -1 ||
            lower.indexOf(".jpg") !== -1 ||
            lower.indexOf(".jpeg") !== -1 ||
            lower.indexOf(".webp") !== -1 ||
            lower.indexOf(".gif") !== -1 ||
            textOf(attachment.mime_type).indexOf("image/") === 0
        ) {
            var img = document.createElement("img");
            img.src = url;
            img.alt = name;
            img.style.maxWidth = "220px";
            img.style.borderRadius = "12px";
            img.style.display = "block";
            img.style.marginTop = "8px";
            container.appendChild(img);
            return;
        }

        var link = document.createElement("a");
        link.href = url;
        link.textContent = name;
        link.target = "_blank";
        link.rel = "noopener";
        link.style.display = "block";
        link.style.marginTop = "8px";
        container.appendChild(link);
    }

    function appendMessage(root, message) {
        var role = roleOf(message);
        var text = messageText(message);
        var attachments = attachmentsOf(message);

        if (!text && !attachments.length) {
            return;
        }

        var row = document.createElement("div");
        row.className = "nova-mobile-message nova-message nova-message-" + role;
        row.setAttribute("data-nova-restored-message", "true");
        row.setAttribute("data-role", role);

        var bubble = document.createElement("div");
        bubble.className = "nova-mobile-message-bubble nova-bubble";

        if (text) {
            var body = document.createElement("div");
            body.textContent = text;
            bubble.appendChild(body);
        }

        attachments.forEach(function (attachment) {
            appendAttachment(bubble, attachment);
        });

        row.appendChild(bubble);
        root.appendChild(row);
    }

    function renderMessages(messages) {
        var root = findMessageRoot();

        if (!root) {
            console.warn("[Nova Sessions Real Restore V4] no message root found");
            return false;
        }

        root.innerHTML = "";

        messages.forEach(function (message) {
            appendMessage(root, message);
        });

        root.scrollTop = root.scrollHeight;
        return true;
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
            var el = $(id);
            if (el) el.textContent = label;
        });

        var dataTitle = document.querySelector("[data-nova-session-title]");
        if (dataTitle) dataTitle.textContent = label;

        document.title = "Nova · " + title;
    }

    async function fetchJson(url) {
        var response = await fetch(url, {
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(url + " returned " + response.status);
        }

        return await response.json();
    }

    async function fetchSessionData(sessionId) {
        var encoded = encodeURIComponent(sessionId);
        var urls = [
            "/api/sessions/" + encoded,
            "/api/chat/" + encoded
        ];
        var lastError = null;

        for (var i = 0; i < urls.length; i += 1) {
            try {
                return await fetchJson(urls[i]);
            } catch (err) {
                lastError = err;
            }
        }

        throw lastError || new Error("session fetch failed");
    }

    async function restore(sessionId) {
        sessionId = textOf(sessionId).trim();

        if (!sessionId) {
            return false;
        }

        localStorage.setItem(ACTIVE_KEY, sessionId);

        var data = await fetchSessionData(sessionId);
        var messages = pickMessages(data, sessionId);

        renderMessages(messages);
        updateTitle(sessionId, data);

        if (
            window.NovaMobileSessionsRescueFinal &&
            typeof window.NovaMobileSessionsRescueFinal.close === "function"
        ) {
            window.NovaMobileSessionsRescueFinal.close();
        }

        window.NovaMobileSessionRestoreV4.last = {
            session_id: sessionId,
            message_count: messages.length,
            data: data
        };

        console.log("[Nova Sessions Real Restore V4] restored", sessionId, "messages", messages.length);

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
        var panel = $("nova-mobile-sessions-panel");

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
            console.error("[Nova Sessions Real Restore V4] restore failed", err);
        });
    }, true);

    window.NovaMobileSessionRestoreV4 = {
        restore: restore,
        pickMessages: pickMessages,
        findSessionRecord: findSessionRecord,
        renderMessages: renderMessages,
        findMessageRoot: findMessageRoot,
        last: null
    };

    console.log("[Nova Sessions Real Restore V4] installed");
})();
'''
    js = js.rstrip() + addition + "\n"
    js_path.write_text(js, encoding="utf-8")
    print("patched:", js_path)
else:
    print("real restore v4 already installed")

if cache_marker not in template:
    old = "sessions-rescue-final-v3-body-unhide-20260703"
    if old not in template:
        raise SystemExit("missing rescue v3 cache marker in template")

    template = template.replace(old, old + "-" + cache_marker, 1)
    template_path.write_text(template.rstrip() + "\n", encoding="utf-8")
    print("bumped cache in:", template_path)
else:
    print("real restore v4 cache already installed")
