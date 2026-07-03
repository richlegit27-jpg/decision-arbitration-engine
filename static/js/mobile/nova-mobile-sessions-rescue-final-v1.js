/* NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V1_20260703 */
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V1_20260703__ = true;

    function $(id) {
        return document.getElementById(id);
    }

    function addStyle() {
        if ($("nova-mobile-sessions-rescue-style")) return;

        var style = document.createElement("style");
        style.id = "nova-mobile-sessions-rescue-style";
        style.textContent = `
            #nova-mobile-sessions-rescue-button {
                position: fixed !important;
                top: 10px !important;
                right: 10px !important;
                z-index: 2147483600 !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                min-height: 36px !important;
                padding: 8px 12px !important;
                border-radius: 999px !important;
                border: 1px solid rgba(255,255,255,0.18) !important;
                background: rgba(20,20,28,0.92) !important;
                color: #fff !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                line-height: 1 !important;
                box-shadow: 0 8px 24px rgba(0,0,0,0.35) !important;
                opacity: 1 !important;
                visibility: visible !important;
                pointer-events: auto !important;
            }

            #nova-mobile-sessions-panel {
                position: fixed !important;
                inset: 0 !important;
                z-index: 2147483500 !important;
                background: rgba(8,8,12,0.98) !important;
                color: #fff !important;
                padding: 14px !important;
                box-sizing: border-box !important;
                overflow: auto !important;
            }

            #nova-mobile-sessions-panel.hidden {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                pointer-events: none !important;
            }

            .nova-sessions-rescue-header {
                display: flex !important;
                align-items: center !important;
                justify-content: space-between !important;
                gap: 12px !important;
                margin-bottom: 12px !important;
            }

            .nova-sessions-rescue-title {
                font-size: 18px !important;
                font-weight: 800 !important;
            }

            .nova-sessions-rescue-close {
                min-height: 36px !important;
                padding: 8px 12px !important;
                border-radius: 999px !important;
                border: 1px solid rgba(255,255,255,0.18) !important;
                background: rgba(255,255,255,0.08) !important;
                color: #fff !important;
                font-weight: 700 !important;
            }

            .nova-sessions-rescue-row {
                width: 100% !important;
                display: block !important;
                text-align: left !important;
                margin: 8px 0 !important;
                padding: 12px !important;
                border-radius: 14px !important;
                border: 1px solid rgba(255,255,255,0.12) !important;
                background: rgba(255,255,255,0.06) !important;
                color: #fff !important;
            }

            .nova-sessions-rescue-row strong {
                display: block !important;
                font-size: 14px !important;
                margin-bottom: 4px !important;
            }

            .nova-sessions-rescue-row span {
                display: block !important;
                opacity: 0.72 !important;
                font-size: 12px !important;
            }
        `;
        document.head.appendChild(style);
    }


    function restoreBodyVisibility(reason) {
        /* NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V3_BODY_UNHIDE_20260703 */
        var body = document.body;
        if (!body) return;

        body.removeAttribute("hidden");

        if (body.getAttribute("aria-hidden") === "true") {
            body.removeAttribute("aria-hidden");
        }

        body.style.removeProperty("display");
        body.style.removeProperty("visibility");
        body.style.removeProperty("opacity");
        body.style.removeProperty("pointer-events");

        if (getComputedStyle(body).display === "none") {
            body.style.setProperty("display", "block", "important");
        }

        if (getComputedStyle(body).visibility === "hidden") {
            body.style.setProperty("visibility", "visible", "important");
        }

        if (getComputedStyle(body).opacity === "0") {
            body.style.setProperty("opacity", "1", "important");
        }

        body.style.setProperty("pointer-events", "auto", "important");
        body.dataset.novaSessionsBodyRestored = reason || "unknown";
    }

    function showMainLayout() {
        var shell = document.querySelector(".mobile-shell");
        var messages = $("mobileChatMessages");
        var composer = $("nova-mobile-composer");

        [shell, messages, composer].forEach(function (el) {
            if (!el) return;
            el.style.removeProperty("height");
            el.style.removeProperty("max-height");
            el.style.removeProperty("min-height");
            el.style.removeProperty("overflow");
            el.style.removeProperty("transform");
        });

        if (messages) {
            messages.style.setProperty("display", "block", "important");
            messages.style.setProperty("visibility", "visible", "important");
            messages.style.setProperty("opacity", "1", "important");
            messages.style.setProperty("pointer-events", "auto", "important");
        }

        if (composer) {
            composer.style.setProperty("display", "flex", "important");
            composer.style.setProperty("visibility", "visible", "important");
            composer.style.setProperty("opacity", "1", "important");
            composer.style.setProperty("pointer-events", "auto", "important");
        }
    }


    function ensurePanelMarkup(panel) {
        /* NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V2_PANEL_MARKUP_20260703 */
        if (!panel) return;

        var existingList = panel.querySelector("#nova-mobile-sessions-rescue-list");
        var existingClose = panel.querySelector(".nova-sessions-rescue-close");

        if (existingList && existingClose) {
            return;
        }

        panel.innerHTML = `
            <div class="nova-sessions-rescue-header">
                <div class="nova-sessions-rescue-title">Sessions</div>
                <button type="button" class="nova-sessions-rescue-close" data-action="close-sessions">Close</button>
            </div>
            <div id="nova-mobile-sessions-rescue-list">Loading sessions...</div>
        `;
    }

    function getPanel() {
        var panel = $("nova-mobile-sessions-panel") ||
            document.querySelector(".nova-mobile-sessions-panel") ||
            document.querySelector("[data-nova-sessions-panel='true']");

        if (panel) {
            if (!panel.id) panel.id = "nova-mobile-sessions-panel";
            ensurePanelMarkup(panel);
            return panel;
        }

        panel = document.createElement("div");
        panel.id = "nova-mobile-sessions-panel";
        panel.className = "hidden";
        panel.setAttribute("aria-hidden", "true");
        panel.setAttribute("data-nova-sessions-panel", "true");
        panel.innerHTML = `
            <div class="nova-sessions-rescue-header">
                <div class="nova-sessions-rescue-title">Sessions</div>
                <button type="button" class="nova-sessions-rescue-close" data-action="close-sessions">Close</button>
            </div>
            <div id="nova-mobile-sessions-rescue-list">Loading sessions...</div>
        `;
        document.body.appendChild(panel);
        ensurePanelMarkup(panel);
        return panel;
    }

    function closePanel() {
        var panel = getPanel();

        restoreBodyVisibility("close-before");

        if (document.activeElement && panel.contains(document.activeElement)) {
            try {
                document.activeElement.blur();
            } catch (e) {}
        }

        panel.removeAttribute("hidden");
        panel.classList.add("hidden");
        panel.setAttribute("aria-hidden", "true");
        panel.setAttribute("data-nova-sessions-open", "false");
        panel.dataset.novaSessionsOpen = "false";
        panel.style.setProperty("display", "none", "important");
        panel.style.setProperty("visibility", "hidden", "important");
        panel.style.setProperty("opacity", "0", "important");
        panel.style.setProperty("pointer-events", "none", "important");

        document.documentElement.classList.remove("nova-mobile-sessions-open", "nova-sessions-open", "sessions-open");
        if (document.body) {
            document.body.classList.remove("nova-mobile-sessions-open", "nova-sessions-open", "sessions-open");
        }

        showMainLayout();
    }

    function normalizeSessions(payload) {
        if (Array.isArray(payload)) return payload;
        if (payload && Array.isArray(payload.sessions)) return payload.sessions;
        if (payload && Array.isArray(payload.items)) return payload.items;
        if (payload && payload.data && Array.isArray(payload.data.sessions)) return payload.data.sessions;
        return [];
    }

    function renderSessions(sessions) {
        var list = $("nova-mobile-sessions-rescue-list");
        if (!list) return;

        if (!sessions.length) {
            list.textContent = "No sessions found from /api/sessions.";
            return;
        }

        list.innerHTML = "";

        sessions.forEach(function (session) {
            var id = session.id || session.session_id || session.key || "";
            var title = session.title || session.name || session.label || id || "Untitled session";
            var updated = session.updated_at || session.modified_at || session.created_at || "";

            var row = document.createElement("button");
            row.type = "button";
            row.className = "nova-sessions-rescue-row";
            row.innerHTML = "<strong></strong><span></span>";
            row.querySelector("strong").textContent = title;
            row.querySelector("span").textContent = id ? (updated ? id + " · " + updated : id) : updated;

            row.addEventListener("click", function () {
                if (!id) return;

                try {
                    localStorage.setItem("nova_mobile_active_session_id", id);
                    localStorage.setItem("nova_active_session_id", id);
                } catch (e) {}

                if (window.NovaMobileSessionPanelV6 && typeof window.NovaMobileSessionPanelV6.switchSession === "function") {
                    window.NovaMobileSessionPanelV6.switchSession(id);
                    closePanel();
                    return;
                }

                if (typeof window.NovaMobileSwitchSession === "function") {
                    window.NovaMobileSwitchSession(id);
                    closePanel();
                    return;
                }

                window.location.href = "/mobile?session_id=" + encodeURIComponent(id);
            });

            list.appendChild(row);
        });
    }

    function loadSessions() {
        var list = $("nova-mobile-sessions-rescue-list");
        if (list) list.textContent = "Loading sessions...";

        fetch("/api/sessions", {
            method: "GET",
            credentials: "include",
            cache: "no-store"
        })
        .then(function (response) {
            return response.json();
        })
        .then(function (payload) {
            renderSessions(normalizeSessions(payload));
        })
        .catch(function (error) {
            if (list) {
                list.textContent = "Could not load sessions: " + (error && error.message ? error.message : error);
            }
        });
    }

    function openPanel() {
        addStyle();
        restoreBodyVisibility("open-before");

        var panel = getPanel();
        ensurePanelMarkup(panel);

        panel.removeAttribute("hidden");
        panel.classList.remove("hidden");
        panel.setAttribute("aria-hidden", "false");
        panel.setAttribute("data-nova-sessions-open", "true");
        panel.dataset.novaSessionsOpen = "true";
        panel.style.setProperty("display", "block", "important");
        panel.style.setProperty("visibility", "visible", "important");
        panel.style.setProperty("opacity", "1", "important");
        panel.style.setProperty("pointer-events", "auto", "important");

        document.documentElement.classList.add("nova-mobile-sessions-open");
        if (document.body) {
            document.body.classList.add("nova-mobile-sessions-open");
        }

        restoreBodyVisibility("open-after");
        loadSessions();
    }

    function findExistingButton() {
        return $("nova-mobile-sessions-button") ||
            $("mobileSessionsButton") ||
            $("nova-sessions-button") ||
            document.querySelector("[data-action='sessions']") ||
            document.querySelector("[data-mobile-action='sessions']") ||
            document.querySelector("[aria-label='Sessions']") ||
            document.querySelector("[title='Sessions']");
    }

    function ensureButton() {
        addStyle();
        restoreBodyVisibility("ensure-button");

        var button = findExistingButton();

        if (!button) {
            button = document.createElement("button");
            button.type = "button";
            button.id = "nova-mobile-sessions-rescue-button";
            button.textContent = "Sessions";
            button.setAttribute("aria-label", "Sessions");
            document.body.appendChild(button);
        } else {
            button.id = button.id || "nova-mobile-sessions-rescue-button";
            button.style.setProperty("display", "inline-flex", "important");
            button.style.setProperty("visibility", "visible", "important");
            button.style.setProperty("opacity", "1", "important");
            button.style.setProperty("pointer-events", "auto", "important");
        }

        if (button.dataset.novaSessionsRescueWired === "1") return button;

        button.dataset.novaSessionsRescueWired = "1";
        button.removeAttribute("onclick");

        button.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            if (event.stopImmediatePropagation) {
                event.stopImmediatePropagation();
            }
            openPanel();
            return false;
        }, true);

        return button;
    }

    document.addEventListener("click", function (event) {
        var target = event.target && event.target.closest
            ? event.target.closest("[data-action='close-sessions'], .nova-sessions-rescue-close")
            : null;

        if (!target) return;

        event.preventDefault();
        event.stopPropagation();
        if (event.stopImmediatePropagation) {
            event.stopImmediatePropagation();
        }

        closePanel();
        return false;
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closePanel();
        }
    }, true);

    window.NovaMobileSessionsRescueFinal = {
        ensureButton: ensureButton,
        open: openPanel,
        close: closePanel,
        reload: loadSessions
    };

    function boot() {
        restoreBodyVisibility("boot-start");
        ensureButton();
        closePanel();
        restoreBodyVisibility("boot-end");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    setInterval(function () {
        restoreBodyVisibility("interval");
        ensureButton();
    }, 1500);

    console.log("[NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V1_20260703] ready");
})();

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

