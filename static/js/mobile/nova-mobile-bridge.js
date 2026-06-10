(function () {
    "use strict";

    function installBridge(options) {
        options = options || {};

        window.NovaMobileBridge = {
            renderMarkdown: window.NovaMobileCore.renderMarkdown,
            enhanceCodeBlocks: window.NovaMobileCodeUI.enhanceCodeBlocks,
            scrollBottom: window.NovaMobileCore.scrollBottom,
            saveCurrentMessages: window.NovaMobileCore.saveCurrentMessages,
            syncSessionFromResponse: options.syncSessionFromResponse
        };

        console.log("[Nova Mobile] bridge installed");
    }

    window.NovaMobileBridgeModule = {
        installBridge
    };

    console.log("[Nova Mobile] bridge module ready");
})();

/* NOVA MOBILE SESSION BRIDGE START */
(function () {
    "use strict";

    function clean(value) {
        return String(value || "").trim();
    }

    function rememberSessionId(sessionId) {
        sessionId = clean(sessionId);

        if (!sessionId) {
            return "";
        }

        window.__novaActiveSessionId = sessionId;
        window.activeSessionId = sessionId;
        window.sessionId = sessionId;

        try {
            localStorage.setItem("nova_active_session_id", sessionId);
        } catch (_) {}

        try {
            if (document.body) {
                document.body.setAttribute("data-session-id", sessionId);
            }
        } catch (_) {}

        return sessionId;
    }

    function extractSessionId(payload) {
        if (!payload || typeof payload !== "object") {
            return "";
        }

        return clean(
            payload.active_session_id ||
            payload.session_id ||
            payload.chat_id ||
            (
                payload.session &&
                (
                    payload.session.id ||
                    payload.session.session_id ||
                    payload.session.chat_id
                )
            ) ||
            (
                payload.data &&
                (
                    payload.data.active_session_id ||
                    payload.data.session_id ||
                    (
                        payload.data.session &&
                        (
                            payload.data.session.id ||
                            payload.data.session.session_id ||
                            payload.data.session.chat_id
                        )
                    )
                )
            ) ||
            ""
        );
    }

    window.getSessionId = function () {
        return clean(
            window.__novaActiveSessionId ||
            window.activeSessionId ||
            window.sessionId ||
            localStorage.getItem("nova_active_session_id") ||
            (
                document.body &&
                document.body.getAttribute("data-session-id")
            ) ||
            ""
        );
    };

    window.NovaRememberMobileSessionId = rememberSessionId;
    window.NovaMobileSessionBridgeInstalled = true;

    if (!window.__NovaMobileSessionFetchWrapped) {
        window.__NovaMobileSessionFetchWrapped = true;

        const originalFetch = window.fetch;

        window.fetch = async function () {
            const response = await originalFetch.apply(this, arguments);

            try {
                const cloned = response.clone();
                const contentType = cloned.headers.get("content-type") || "";

                if (contentType.includes("application/json")) {
                    cloned.json().then(function (payload) {
                        const sessionId = extractSessionId(payload);

                        if (sessionId) {
                            rememberSessionId(sessionId);
                            console.log("[Nova Mobile] session remembered", sessionId);
                        }
                    }).catch(function () {});
                }
            } catch (_) {}

            return response;
        };
    }

    const existing = window.getSessionId();

    if (existing) {
        rememberSessionId(existing);
    }

    console.log("[Nova Mobile] session bridge active from module");
})();
/* NOVA MOBILE SESSION BRIDGE END */


// NOVA_MOBILE_SESSION_KEY_SYNC_LOCK_20260609
(function () {
    "use strict";

    function syncSessionKeys(sessionId) {
        sessionId = String(sessionId || "").trim();
        if (!sessionId) return;

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("nova_session_id", sessionId);
            localStorage.setItem("novaMobileSessionId", sessionId);
            localStorage.setItem("active_session_id", sessionId);
        } catch (error) {}

        try {
            if (window.NovaMobileState && window.NovaMobileState.state) {
                window.NovaMobileState.state.sessionId = sessionId;
                window.NovaMobileState.state.activeSessionId = sessionId;
                window.NovaMobileState.state.active_session_id = sessionId;
            }
        } catch (error) {}

        try {
            window.dispatchEvent(new CustomEvent("nova-mobile-active-session-synced", {
                detail: {
                    session_id: sessionId,
                    active_session_id: sessionId
                }
            }));
        } catch (error) {}
    }

    window.NovaSyncMobileSessionKeys = syncSessionKeys;

    var previousRemember = window.NovaRememberMobileSession;
    window.NovaRememberMobileSession = function (sessionId) {
        syncSessionKeys(sessionId);

        if (typeof previousRemember === "function") {
            try {
                return previousRemember.apply(this, arguments);
            } catch (error) {
                console.warn("[Nova Mobile Session Key Sync] previous remember failed", error);
            }
        }

        return sessionId;
    };

    document.addEventListener("click", function (event) {
        var target = event.target;
        if (!target) return;

        var row = target.closest("[data-session-id], [data-nova-session-id], [data-mobile-session-id]");
        if (!row) return;

        var sessionId =
            row.getAttribute("data-session-id") ||
            row.getAttribute("data-nova-session-id") ||
            row.getAttribute("data-mobile-session-id");

        syncSessionKeys(sessionId);
    }, true);

    try {
        var existing =
            localStorage.getItem("nova_mobile_active_session_id") ||
            localStorage.getItem("nova_active_session_id") ||
            localStorage.getItem("nova_session_id") ||
            localStorage.getItem("novaMobileSessionId") ||
            localStorage.getItem("active_session_id");

        if (existing) {
            syncSessionKeys(existing);
        }
    } catch (error) {}

    console.log("[Nova Mobile Session Key Sync] ready");
})();

// NOVA_MOBILE_MANUAL_SESSION_SELECTION_LOCK_20260609
(function () {
    "use strict";

    var manualSessionId = "";
    var manualSessionUntil = 0;

    function now() {
        return Date.now ? Date.now() : new Date().getTime();
    }

    function syncKeys(sessionId) {
        sessionId = String(sessionId || "").trim();
        if (!sessionId) return;

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("nova_session_id", sessionId);
            localStorage.setItem("novaMobileSessionId", sessionId);
            localStorage.setItem("active_session_id", sessionId);
        } catch (error) {}

        try {
            if (window.NovaMobileState && window.NovaMobileState.state) {
                window.NovaMobileState.state.sessionId = sessionId;
                window.NovaMobileState.state.activeSessionId = sessionId;
                window.NovaMobileState.state.active_session_id = sessionId;
            }
        } catch (error) {}
    }

    function setManualSession(sessionId) {
        sessionId = String(sessionId || "").trim();
        if (!sessionId) return;

        manualSessionId = sessionId;
        manualSessionUntil = now() + 15000;
        syncKeys(sessionId);

        console.log("[Nova Mobile Manual Session Lock] selected", sessionId);
    }

    function getSessionFromElement(target) {
        if (!target || !target.closest) return "";

        var row = target.closest("[data-session-id], [data-nova-session-id], [data-mobile-session-id]");
        if (!row) return "";

        return (
            row.getAttribute("data-session-id") ||
            row.getAttribute("data-nova-session-id") ||
            row.getAttribute("data-mobile-session-id") ||
            ""
        );
    }

    document.addEventListener("click", function (event) {
        var sessionId = getSessionFromElement(event.target);
        if (!sessionId) return;

        setManualSession(sessionId);
    }, true);

    var previousRemember = window.NovaRememberMobileSession;

    window.NovaRememberMobileSession = function (sessionId) {
        sessionId = String(sessionId || "").trim();

        if (
            manualSessionId &&
            sessionId &&
            sessionId !== manualSessionId &&
            now() < manualSessionUntil
        ) {
            console.warn("[Nova Mobile Manual Session Lock] blocked overwrite", {
                wanted: manualSessionId,
                incoming: sessionId
            });

            syncKeys(manualSessionId);
            return manualSessionId;
        }

        if (sessionId) {
            syncKeys(sessionId);
        }

        if (typeof previousRemember === "function") {
            try {
                return previousRemember.apply(this, arguments);
            } catch (error) {
                console.warn("[Nova Mobile Manual Session Lock] previous remember failed", error);
            }
        }

        return sessionId;
    };

    window.NovaLockManualMobileSession = setManualSession;

    console.log("[Nova Mobile Manual Session Lock] ready");
})();

// NOVA_MOBILE_PRIMARY_SESSION_WATCHDOG_20260609
(function () {
    "use strict";

    function getPrimarySessionId() {
        try {
            return String(
                localStorage.getItem("nova_mobile_active_session_id") ||
                localStorage.getItem("nova_active_session_id") ||
                localStorage.getItem("nova_session_id") ||
                localStorage.getItem("novaMobileSessionId") ||
                localStorage.getItem("active_session_id") ||
                ""
            ).trim();
        } catch (error) {
            return "";
        }
    }

    function mirrorSessionId(sessionId) {
        sessionId = String(sessionId || "").trim();
        if (!sessionId) return;

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("nova_session_id", sessionId);
            localStorage.setItem("novaMobileSessionId", sessionId);
            localStorage.setItem("active_session_id", sessionId);
        } catch (error) {}

        try {
            if (window.NovaMobileState && window.NovaMobileState.state) {
                window.NovaMobileState.state.sessionId = sessionId;
                window.NovaMobileState.state.activeSessionId = sessionId;
                window.NovaMobileState.state.active_session_id = sessionId;
            }
        } catch (error) {}
    }

    function pullClickedSessionId(target) {
        if (!target || !target.closest) return "";

        var row = target.closest("[data-session-id], [data-nova-session-id], [data-mobile-session-id]");
        if (!row) return "";

        return String(
            row.getAttribute("data-session-id") ||
            row.getAttribute("data-nova-session-id") ||
            row.getAttribute("data-mobile-session-id") ||
            ""
        ).trim();
    }

    document.addEventListener("click", function (event) {
        var sessionId = pullClickedSessionId(event.target);
        if (!sessionId) return;

        mirrorSessionId(sessionId);

        setTimeout(function () {
            mirrorSessionId(sessionId);
        }, 100);

        setTimeout(function () {
            mirrorSessionId(sessionId);
        }, 500);

        setTimeout(function () {
            mirrorSessionId(sessionId);
        }, 1500);

        console.log("[Nova Mobile Primary Session Watchdog] clicked session locked", sessionId);
    }, true);

    setInterval(function () {
        var primary = getPrimarySessionId();
        if (!primary) return;

        mirrorSessionId(primary);
    }, 750);

    setTimeout(function () {
        var primary = getPrimarySessionId();
        if (primary) {
            mirrorSessionId(primary);
        }

        console.log("[Nova Mobile Primary Session Watchdog] ready", primary);
    }, 250);
})();

// NOVA_MOBILE_CLEAN_SESSIONS_OVERRIDE_20260609
(function () {
    "use strict";

    function $(id) {
        return document.getElementById(id);
    }

    function getPanel() {
        return $("nova-mobile-sessions-panel");
    }

    function getChatBox() {
        return (
            $("nova-mobile-chat") ||
            $("nova-mobile-messages") ||
            $("nova-chat-messages") ||
            document.querySelector(".nova-mobile-chat") ||
            document.querySelector(".nova-mobile-messages") ||
            document.querySelector(".chat-messages") ||
            document.querySelector("[data-mobile-chat]")
        );
    }

    function syncSession(sessionId) {
        sessionId = String(sessionId || "").trim();
        if (!sessionId) return;

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("nova_session_id", sessionId);
            localStorage.setItem("novaMobileSessionId", sessionId);
            localStorage.setItem("active_session_id", sessionId);
        } catch (error) {}

        try {
            if (window.NovaMobileState && window.NovaMobileState.state) {
                window.NovaMobileState.state.sessionId = sessionId;
                window.NovaMobileState.state.activeSessionId = sessionId;
                window.NovaMobileState.state.active_session_id = sessionId;
            }
        } catch (error) {}
    }

    function openPanel(panel) {
        if (!panel) return;

        panel.classList.remove("hidden", "is-hidden", "closed");
        panel.removeAttribute("aria-hidden");

        panel.style.cssText = [
            "display:block !important",
            "visibility:visible !important",
            "opacity:1 !important",
            "position:fixed !important",
            "top:60px !important",
            "left:10px !important",
            "right:10px !important",
            "bottom:80px !important",
            "overflow-y:auto !important",
            "z-index:2147483647 !important",
            "background:rgba(11,16,32,.98) !important",
            "border:2px solid rgba(124,92,255,.95) !important",
            "border-radius:16px !important",
            "padding:10px !important",
            "color:#f8fafc !important",
            "box-shadow:0 20px 60px rgba(0,0,0,.65) !important"
        ].join(";");
    }

    function closePanel(panel) {
        if (!panel) return;

        try {
            if (document.activeElement && panel.contains(document.activeElement)) {
                document.activeElement.blur();
            }
        } catch (error) {}

        panel.classList.add("hidden");
        panel.setAttribute("aria-hidden", "true");
        panel.style.display = "none";
    }

    function renderMessage(chatBox, message) {
        if (!chatBox || !message) return;

        var role = String(message.role || "assistant");
        var text = String(message.text || "").trim();

        var bubble = document.createElement("div");
        bubble.className = "nova-mobile-message mobile-message message " + role;
        bubble.setAttribute("data-role", role);

        if (!text && Array.isArray(message.attachments) && message.attachments.length) {
            text = "Attachment";
        }

        bubble.textContent = text || "";
        chatBox.appendChild(bubble);

        if (Array.isArray(message.attachments)) {
            message.attachments.forEach(function (attachment) {
                if (!attachment || !attachment.url) return;

                var link = document.createElement("a");
                link.href = attachment.url;
                link.textContent = attachment.filename || attachment.url;
                link.target = "_blank";
                link.rel = "noopener";
                link.style.display = "block";
                link.style.marginTop = "6px";
                bubble.appendChild(link);
            });
        }
    }

    function loadSession(session) {
        if (!session || !session.id) return;

        syncSession(session.id);

        var title = String(session.title || session.id || "Session");
        var titleEl = $("nova-mobile-active-session");
        if (titleEl) {
            titleEl.textContent = "Session: " + title;
        }

        var chatBox = getChatBox();
        if (chatBox) {
            chatBox.innerHTML = "";

            var messages = Array.isArray(session.messages) ? session.messages : [];
            messages.forEach(function (message) {
                renderMessage(chatBox, message);
            });

            try {
                chatBox.scrollTop = chatBox.scrollHeight;
            } catch (error) {}
        }

        closePanel(getPanel());

        console.log("[Nova Mobile Clean Sessions Override] loaded", {
            id: session.id,
            title: title,
            messages: Array.isArray(session.messages) ? session.messages.length : 0
        });
    }

    function renderSessions(panel, sessions) {
        openPanel(panel);

        var useful = (Array.isArray(sessions) ? sessions : []).filter(function (session) {
            var count = session && Array.isArray(session.messages) ? session.messages.length : 0;
            return session && session.id && count > 0;
        });

        useful.sort(function (a, b) {
            return String(b.updated_at || b.created_at || "").localeCompare(String(a.updated_at || a.created_at || ""));
        });

        panel.innerHTML = "";

        var header = document.createElement("div");
        header.style.display = "flex";
        header.style.alignItems = "center";
        header.style.justifyContent = "space-between";
        header.style.gap = "10px";
        header.style.marginBottom = "10px";

        var title = document.createElement("strong");
        title.textContent = "Saved Sessions";

        var close = document.createElement("button");
        close.type = "button";
        close.textContent = "Close";
        close.className = "mobile-session-item";
        close.onclick = function () {
            closePanel(panel);
        };

        header.appendChild(title);
        header.appendChild(close);
        panel.appendChild(header);

        if (!useful.length) {
            var empty = document.createElement("div");
            empty.className = "mobile-session-item";
            empty.textContent = "No saved sessions with messages yet.";
            panel.appendChild(empty);
            return;
        }

        useful.forEach(function (session) {
            var count = Array.isArray(session.messages) ? session.messages.length : 0;
            var shortId = String(session.id).slice(-8);
            var label = String(session.title || "Untitled Session").trim();

            var row = document.createElement("button");
            row.type = "button";
            row.className = "mobile-session-item";
            row.setAttribute("data-clean-session-id", session.id);
            row.style.display = "block";
            row.style.width = "100%";
            row.style.textAlign = "left";
            row.style.margin = "8px 0";
            row.style.padding = "10px";
            row.style.borderRadius = "12px";

            row.textContent = label + " · " + count + " messages · " + shortId;

            row.onclick = function (event) {
                event.preventDefault();
                event.stopPropagation();
                loadSession(session);
            };

            panel.appendChild(row);
        });
    }

    async function openCleanSessions(event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
        }

        var panel = getPanel();
        if (!panel) return;

        openPanel(panel);
        panel.innerHTML = "<div class='mobile-session-item'>Loading saved sessions...</div>";

        try {
            var response = await fetch("/api/sessions", {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                cache: "no-store"
            });

            var data = await response.json();
            var sessions = Array.isArray(data.sessions) ? data.sessions : [];

            renderSessions(panel, sessions);

            console.log("[Nova Mobile Clean Sessions Override] rendered", sessions.length);
        } catch (error) {
            console.error("[Nova Mobile Clean Sessions Override] failed", error);
            panel.innerHTML = "<div class='mobile-session-item'>Failed to load sessions.</div>";
        }
    }

    function isSessionsButton(target) {
        if (!target || !target.closest) return false;

        var button = target.closest("button, a");
        if (!button) return false;

        if (button.closest("#nova-mobile-sessions-panel")) return false;

        var text = String(button.textContent || "").trim().toLowerCase();
        var id = String(button.id || "").toLowerCase();
        var cls = String(button.className || "").toLowerCase();
        var aria = String(button.getAttribute("aria-label") || "").toLowerCase();

        return (
            text === "sessions" ||
            id.includes("session") ||
            cls.includes("session") ||
            aria.includes("session")
        );
    }

    document.addEventListener("click", function (event) {
        if (!isSessionsButton(event.target)) return;
        openCleanSessions(event);
    }, true);

    window.NovaOpenCleanMobileSessions = openCleanSessions;

    console.log("[Nova Mobile Clean Sessions Override] ready");
})();

// NOVA_MOBILE_FORCE_VISIBLE_SESSION_MESSAGES_20260609
(function () {
    "use strict";

    function $(id) {
        return document.getElementById(id);
    }

    function isVisible(el) {
        if (!el) return false;

        try {
            var style = window.getComputedStyle(el);
            var rect = el.getBoundingClientRect();

            return (
                style.display !== "none" &&
                style.visibility !== "hidden" &&
                rect.width > 0 &&
                rect.height > 0
            );
        } catch (error) {
            return false;
        }
    }

    function findChatTarget() {
        var selectors = [
            "#nova-mobile-chat",
            "#nova-mobile-chat-box",
            "#nova-mobile-chat-log",
            "#nova-mobile-messages",
            "#nova-mobile-thread",
            "#nova-chat-messages",
            "#chat-box",
            "#messages",
            ".nova-mobile-chat",
            ".nova-mobile-chat-box",
            ".nova-mobile-messages",
            ".mobile-chat",
            ".mobile-chat-body",
            ".chat-messages",
            ".messages",
            "[data-mobile-chat]"
        ];

        var candidates = [];

        selectors.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (el) {
                if (!el) return;
                if (el.closest("#nova-mobile-sessions-panel")) return;
                if (el.closest("#nova-mobile-composer")) return;
                if (el.closest("form")) return;

                candidates.push(el);
            });
        });

        candidates = candidates.filter(function (el, index) {
            return candidates.indexOf(el) === index;
        });

        var visible = candidates.filter(isVisible);
        if (visible.length) return visible[0];
        if (candidates.length) return candidates[0];

        var main =
            document.querySelector("main") ||
            document.querySelector(".mobile-main") ||
            document.body;

        var created = $("nova-mobile-forced-session-messages");
        if (!created) {
            created = document.createElement("section");
            created.id = "nova-mobile-forced-session-messages";
            created.style.cssText = [
                "display:block",
                "padding:12px",
                "margin:12px",
                "border-radius:14px",
                "background:rgba(15,23,42,.92)",
                "color:#f8fafc",
                "border:1px solid rgba(124,92,255,.55)",
                "max-height:65vh",
                "overflow-y:auto"
            ].join(";");

            if (main && main.firstChild) {
                main.insertBefore(created, main.firstChild);
            } else {
                document.body.appendChild(created);
            }
        }

        return created;
    }

    function syncSession(sessionId) {
        sessionId = String(sessionId || "").trim();
        if (!sessionId) return;

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("nova_session_id", sessionId);
            localStorage.setItem("novaMobileSessionId", sessionId);
            localStorage.setItem("active_session_id", sessionId);
        } catch (error) {}

        try {
            if (window.NovaMobileState && window.NovaMobileState.state) {
                window.NovaMobileState.state.sessionId = sessionId;
                window.NovaMobileState.state.activeSessionId = sessionId;
                window.NovaMobileState.state.active_session_id = sessionId;
            }
        } catch (error) {}
    }

    function closeSessionsPanel() {
        var panel = $("nova-mobile-sessions-panel");
        if (!panel) return;

        try {
            if (document.activeElement && panel.contains(document.activeElement)) {
                document.activeElement.blur();
            }
        } catch (error) {}

        panel.classList.add("hidden");
        panel.setAttribute("aria-hidden", "true");
        panel.style.display = "none";
    }

    function renderSessionMessages(session) {
        if (!session || !session.id) return;

        var messages = Array.isArray(session.messages) ? session.messages : [];
        var target = findChatTarget();

        syncSession(session.id);

        var title = String(session.title || session.id || "Session");
        var activeTitle = $("nova-mobile-active-session");
        if (activeTitle) {
            activeTitle.textContent = "Session: " + title;
        }

        if (!target) {
            console.warn("[Nova Mobile Force Visible Session Messages] no target");
            return;
        }

        target.innerHTML = "";

        var header = document.createElement("div");
        header.style.cssText = "font-weight:700;margin:0 0 10px 0;opacity:.95;";
        header.textContent = title + " · " + messages.length + " messages";
        target.appendChild(header);

        if (!messages.length) {
            var empty = document.createElement("div");
            empty.textContent = "This session has no saved messages.";
            empty.style.opacity = ".75";
            target.appendChild(empty);
        }

        messages.forEach(function (message) {
            var role = String(message.role || "assistant");
            var text = String(message.text || "").trim();

            var bubble = document.createElement("div");
            bubble.className = "nova-mobile-message mobile-message message " + role;
            bubble.setAttribute("data-role", role);
            bubble.style.cssText = [
                "display:block",
                "margin:10px 0",
                "padding:10px 12px",
                "border-radius:14px",
                role === "user" ? "background:rgba(124,92,255,.22)" : "background:rgba(148,163,184,.16)",
                "white-space:pre-wrap",
                "line-height:1.45",
                "color:#f8fafc"
            ].join(";");

            bubble.textContent = text || "(empty message)";

            if (Array.isArray(message.attachments) && message.attachments.length) {
                message.attachments.forEach(function (attachment) {
                    var url = attachment && attachment.url;
                    if (!url) return;

                    var link = document.createElement("a");
                    link.href = url;
                    link.textContent = attachment.filename || url;
                    link.target = "_blank";
                    link.rel = "noopener";
                    link.style.cssText = "display:block;margin-top:8px;color:#c4b5fd;";
                    bubble.appendChild(link);
                });
            }

            target.appendChild(bubble);
        });

        try {
            target.scrollTop = target.scrollHeight;
        } catch (error) {}

        closeSessionsPanel();

        console.log("[Nova Mobile Force Visible Session Messages] rendered", {
            id: session.id,
            title: title,
            messages: messages.length,
            target: target.id || target.className || target.tagName
        });
    }

    async function getSessions() {
        var response = await fetch("/api/sessions", {
            method: "GET",
            headers: {
                "Accept": "application/json"
            },
            cache: "no-store"
        });

        var data = await response.json();
        return Array.isArray(data.sessions) ? data.sessions : [];
    }

    document.addEventListener("click", async function (event) {
        var button = event.target && event.target.closest
            ? event.target.closest("[data-clean-session-id]")
            : null;

        if (!button) return;

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        var sessionId = String(button.getAttribute("data-clean-session-id") || "").trim();
        if (!sessionId) return;

        try {
            var sessions = await getSessions();
            var session = sessions.find(function (item) {
                return item && String(item.id) === sessionId;
            });

            if (!session) {
                console.warn("[Nova Mobile Force Visible Session Messages] session not found", sessionId);
                return;
            }

            renderSessionMessages(session);
        } catch (error) {
            console.error("[Nova Mobile Force Visible Session Messages] failed", error);
        }
    }, true);

    window.NovaForceRenderMobileSessionMessages = renderSessionMessages;

    console.log("[Nova Mobile Force Visible Session Messages] ready");
})();

// NOVA_MOBILE_FIXED_SESSION_VIEWER_20260609
(function () {
    "use strict";

    var suppressUntil = 0;

    function syncSession(sessionId) {
        sessionId = String(sessionId || "").trim();
        if (!sessionId) return;

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("nova_session_id", sessionId);
            localStorage.setItem("novaMobileSessionId", sessionId);
            localStorage.setItem("active_session_id", sessionId);
        } catch (error) {}

        try {
            if (window.NovaMobileState && window.NovaMobileState.state) {
                window.NovaMobileState.state.sessionId = sessionId;
                window.NovaMobileState.state.activeSessionId = sessionId;
                window.NovaMobileState.state.active_session_id = sessionId;
            }
        } catch (error) {}
    }

    function closeSessionsPanel() {
        var panel = document.getElementById("nova-mobile-sessions-panel");
        if (!panel) return;

        try {
            if (document.activeElement && panel.contains(document.activeElement)) {
                document.activeElement.blur();
            }
        } catch (error) {}

        panel.classList.add("hidden");
        panel.setAttribute("aria-hidden", "true");
        panel.style.display = "none";
    }

    function getViewer() {
        var viewer = document.getElementById("nova-mobile-fixed-session-viewer");

        if (!viewer) {
            viewer = document.createElement("section");
            viewer.id = "nova-mobile-fixed-session-viewer";
            document.body.appendChild(viewer);
        }

        viewer.style.cssText = [
            "display:block !important",
            "visibility:visible !important",
            "opacity:1 !important",
            "position:fixed !important",
            "top:58px !important",
            "left:8px !important",
            "right:8px !important",
            "bottom:88px !important",
            "z-index:2147483646 !important",
            "overflow-y:auto !important",
            "background:#050816 !important",
            "color:#f8fafc !important",
            "border:2px solid rgba(124,92,255,.95) !important",
            "border-radius:16px !important",
            "padding:12px !important",
            "box-shadow:0 20px 70px rgba(0,0,0,.75) !important",
            "font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif !important"
        ].join(";");

        return viewer;
    }

    function makeButton(text) {
        var button = document.createElement("button");
        button.type = "button";
        button.textContent = text;
        button.style.cssText = [
            "border:1px solid rgba(148,163,184,.35)",
            "background:rgba(15,23,42,.95)",
            "color:#f8fafc",
            "border-radius:10px",
            "padding:8px 10px",
            "font-weight:700"
        ].join(";");

        return button;
    }

    function renderSession(session) {
        if (!session || !session.id) return;

        syncSession(session.id);
        closeSessionsPanel();

        var viewer = getViewer();
        var messages = Array.isArray(session.messages) ? session.messages : [];
        var title = String(session.title || session.id || "Saved Session");

        viewer.innerHTML = "";

        var header = document.createElement("div");
        header.style.cssText = [
            "display:flex",
            "align-items:center",
            "justify-content:space-between",
            "gap:10px",
            "position:sticky",
            "top:0",
            "background:#050816",
            "padding-bottom:10px",
            "margin-bottom:10px",
            "border-bottom:1px solid rgba(148,163,184,.25)"
        ].join(";");

        var heading = document.createElement("div");
        heading.innerHTML = "<strong>" + title.replace(/[<>&]/g, "") + "</strong><br><span style='opacity:.75'>" + messages.length + " saved messages</span>";

        var close = makeButton("Close");
        close.onclick = function () {
            viewer.style.display = "none";
        };

        header.appendChild(heading);
        header.appendChild(close);
        viewer.appendChild(header);

        if (!messages.length) {
            var empty = document.createElement("div");
            empty.textContent = "This session has no saved messages.";
            empty.style.cssText = "padding:12px;opacity:.75;";
            viewer.appendChild(empty);
        }

        messages.forEach(function (message) {
            var role = String(message.role || "assistant");
            var text = String(message.text || "").trim();

            var bubble = document.createElement("div");
            bubble.style.cssText = [
                "display:block",
                "margin:10px 0",
                "padding:11px 12px",
                "border-radius:14px",
                role === "user" ? "background:rgba(124,92,255,.28)" : "background:rgba(148,163,184,.16)",
                "border:1px solid rgba(255,255,255,.07)",
                "white-space:pre-wrap",
                "line-height:1.45",
                "font-size:14px"
            ].join(";");

            var label = document.createElement("div");
            label.textContent = role.toUpperCase();
            label.style.cssText = "font-size:11px;font-weight:800;opacity:.65;margin-bottom:6px;";

            var body = document.createElement("div");
            body.textContent = text || "(empty message)";

            bubble.appendChild(label);
            bubble.appendChild(body);

            if (Array.isArray(message.attachments) && message.attachments.length) {
                message.attachments.forEach(function (attachment) {
                    if (!attachment || !attachment.url) return;

                    var link = document.createElement("a");
                    link.href = attachment.url;
                    link.textContent = attachment.filename || attachment.url;
                    link.target = "_blank";
                    link.rel = "noopener";
                    link.style.cssText = "display:block;margin-top:8px;color:#c4b5fd;font-weight:700;";
                    bubble.appendChild(link);
                });
            }

            viewer.appendChild(bubble);
        });

        viewer.scrollTop = 0;

        console.log("[Nova Mobile Fixed Session Viewer] visible", {
            id: session.id,
            title: title,
            messages: messages.length
        });
    }

    async function loadAndRender(sessionId) {
        sessionId = String(sessionId || "").trim();
        if (!sessionId) return;

        try {
            var response = await fetch("/api/sessions", {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                cache: "no-store"
            });

            var data = await response.json();
            var sessions = Array.isArray(data.sessions) ? data.sessions : [];

            var session = sessions.find(function (item) {
                return item && String(item.id) === sessionId;
            });

            if (!session) {
                console.warn("[Nova Mobile Fixed Session Viewer] session not found", sessionId);
                return;
            }

            renderSession(session);
        } catch (error) {
            console.error("[Nova Mobile Fixed Session Viewer] failed", error);
        }
    }

    function getCleanSessionButton(target) {
        if (!target || !target.closest) return null;
        return target.closest("[data-clean-session-id]");
    }

    function handleSessionPick(event) {
        var button = getCleanSessionButton(event.target);
        if (!button) return;

        var sessionId = String(button.getAttribute("data-clean-session-id") || "").trim();
        if (!sessionId) return;

        suppressUntil = Date.now() + 2000;

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        syncSession(sessionId);
        loadAndRender(sessionId);
    }

    document.addEventListener("pointerdown", handleSessionPick, true);
    document.addEventListener("touchstart", handleSessionPick, true);
    document.addEventListener("mousedown", handleSessionPick, true);

    document.addEventListener("click", function (event) {
        if (Date.now() > suppressUntil) return;

        var button = getCleanSessionButton(event.target);
        if (!button) return;

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }, true);

    window.NovaOpenFixedMobileSessionViewer = loadAndRender;

    console.log("[Nova Mobile Fixed Session Viewer] ready");
})();

// NOVA_MOBILE_CHAT_PAYLOAD_SESSION_LOCK_20260609
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_CHAT_PAYLOAD_SESSION_LOCK__) {
        return;
    }

    window.__NOVA_MOBILE_CHAT_PAYLOAD_SESSION_LOCK__ = true;

    function getSessionId() {
        var existing = "";

        try {
            existing =
                localStorage.getItem("nova_mobile_active_session_id") ||
                localStorage.getItem("nova_active_session_id") ||
                localStorage.getItem("nova_session_id") ||
                localStorage.getItem("novaMobileSessionId") ||
                localStorage.getItem("active_session_id") ||
                "";
        } catch (error) {}

        existing = String(existing || "").trim();

        if (!existing) {
            existing = "mobile_" + Date.now();
        }

        try {
            localStorage.setItem("nova_mobile_active_session_id", existing);
            localStorage.setItem("nova_active_session_id", existing);
            localStorage.setItem("nova_session_id", existing);
            localStorage.setItem("novaMobileSessionId", existing);
            localStorage.setItem("active_session_id", existing);
        } catch (error) {}

        try {
            if (window.NovaMobileState && window.NovaMobileState.state) {
                window.NovaMobileState.state.sessionId = existing;
                window.NovaMobileState.state.activeSessionId = existing;
                window.NovaMobileState.state.active_session_id = existing;
            }
        } catch (error) {}

        return existing;
    }

    function isChatUrl(url) {
        url = String(url || "");
        return (
            url.indexOf("/api/chat") !== -1 ||
            url.indexOf("/api/chat/stream") !== -1
        );
    }

    function patchPayload(body) {
        var payload = {};

        try {
            payload = JSON.parse(String(body || "{}"));
        } catch (error) {
            return body;
        }

        var sessionId = getSessionId();

        payload.session_id = payload.session_id || sessionId;
        payload.client_session_id = payload.client_session_id || sessionId;
        payload.active_session_id = payload.active_session_id || sessionId;

        if (!payload.session) {
            payload.session = {
                id: sessionId
            };
        }

        return JSON.stringify(payload);
    }

    var originalFetch = window.fetch;

    window.fetch = function novaMobileSessionFetch(input, init) {
        var url = "";
        var options = init ? Object.assign({}, init) : undefined;

        try {
            if (typeof input === "string") {
                url = input;
            } else if (input && input.url) {
                url = input.url;
            }
        } catch (error) {}

        if (isChatUrl(url)) {
            if (!options) {
                options = {};
            }

            if (options.body) {
                options.body = patchPayload(options.body);
            }

            options.headers = Object.assign({}, options.headers || {}, {
                "Content-Type": "application/json"
            });

            console.log("[Nova Mobile Chat Payload Session Lock] patched", {
                url: url,
                session_id: getSessionId()
            });

            return originalFetch.call(this, input, options);
        }

        return originalFetch.apply(this, arguments);
    };

    console.log("[Nova Mobile Chat Payload Session Lock] ready");
})();

// NOVA_MOBILE_DIRECT_SESSION_PERSIST_BRIDGE_20260609
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_DIRECT_SESSION_PERSIST_BRIDGE__) return;
    window.__NOVA_MOBILE_DIRECT_SESSION_PERSIST_BRIDGE__ = true;

    function getSessionId() {
        var sessionId = "";

        try {
            sessionId =
                localStorage.getItem("nova_mobile_active_session_id") ||
                localStorage.getItem("nova_active_session_id") ||
                localStorage.getItem("nova_session_id") ||
                localStorage.getItem("novaMobileSessionId") ||
                localStorage.getItem("active_session_id") ||
                "";
        } catch (error) {}

        sessionId = String(sessionId || "").trim();

        if (!sessionId) {
            sessionId = "mobile_" + Date.now();
        }

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("nova_session_id", sessionId);
            localStorage.setItem("novaMobileSessionId", sessionId);
            localStorage.setItem("active_session_id", sessionId);
        } catch (error) {}

        return sessionId;
    }

    function getAssistantText(data) {
        if (!data) return "";

        if (typeof data === "string") return data;

        if (typeof data.assistant_message === "string") {
            return data.assistant_message;
        }

        if (data.assistant_message && typeof data.assistant_message === "object") {
            return String(
                data.assistant_message.text ||
                data.assistant_message.content ||
                data.assistant_message.message ||
                ""
            );
        }

        return String(
            data.text ||
            data.content ||
            data.response ||
            data.message ||
            data.summary ||
            ""
        );
    }

    function getUserTextFromBody(body) {
        try {
            var payload = JSON.parse(String(body || "{}"));
            return String(
                payload.user_text ||
                payload.text ||
                payload.message ||
                payload.prompt ||
                ""
            ).trim();
        } catch (error) {
            return "";
        }
    }

    function isChatUrl(url) {
        url = String(url || "");
        return (
            url.indexOf("/api/chat") !== -1 ||
            url.indexOf("/api/chat/stream") !== -1
        );
    }

    async function persistExchange(sessionId, userText, assistantText) {
        userText = String(userText || "").trim();
        assistantText = String(assistantText || "").trim();

        if (!userText && !assistantText) return;

        try {
            await fetch("/api/mobile/session/persist", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    client_session_id: sessionId,
                    active_session_id: sessionId,
                    user_text: userText,
                    assistant_text: assistantText
                })
            });

            console.log("[Nova Mobile Direct Session Persist Bridge] saved", {
                session_id: sessionId,
                user_text: userText.slice(0, 60)
            });
        } catch (error) {
            console.warn("[Nova Mobile Direct Session Persist Bridge] failed", error);
        }
    }

    var previousFetch = window.fetch;

    window.fetch = async function novaMobileDirectPersistFetch(input, init) {
        var url = "";

        try {
            if (typeof input === "string") {
                url = input;
            } else if (input && input.url) {
                url = input.url;
            }
        } catch (error) {}

        var isChat = isChatUrl(url);
        var userText = isChat && init && init.body ? getUserTextFromBody(init.body) : "";
        var sessionId = isChat ? getSessionId() : "";

        var response = await previousFetch.apply(this, arguments);

        if (isChat && userText) {
            try {
                var clone = response.clone();
                var data = await clone.json();
                var assistantText = getAssistantText(data);
                await persistExchange(sessionId, userText, assistantText);
            } catch (error) {
                console.warn("[Nova Mobile Direct Session Persist Bridge] response parse failed", error);
            }
        }

        return response;
    };

    console.log("[Nova Mobile Direct Session Persist Bridge] ready");
})();

// NOVA_MOBILE_FINAL_SESSION_ACTIONS_OWNER_20260609
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_FINAL_SESSION_ACTIONS_OWNER__) {
        return;
    }

    window.__NOVA_MOBILE_FINAL_SESSION_ACTIONS_OWNER__ = true;

    var rendering = false;

    function $(id) {
        return document.getElementById(id);
    }

    function getPanel() {
        return $("nova-mobile-sessions-panel") ||
            $("mobileSessionsPanel") ||
            $("sessionsPanel") ||
            document.querySelector("[data-mobile-sessions-panel]");
    }

    function getChatBox() {
        return $("nova-mobile-chat") ||
            $("nova-mobile-messages") ||
            $("mobileChatMessages") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector(".mobile-chat-container") ||
            document.querySelector("[data-mobile-chat-messages]");
    }

    function isPanelOpen(panel) {
        if (!panel) return false;

        var rect = panel.getBoundingClientRect();
        var style = window.getComputedStyle(panel);

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            rect.width > 20 &&
            rect.height > 20
        );
    }

    function stylePanel(panel) {
        panel.id = "nova-mobile-sessions-panel";
        panel.removeAttribute("aria-hidden");
        panel.classList.remove("hidden");
        panel.style.setProperty("display", "block", "important");
        panel.style.setProperty("position", "fixed", "important");
        panel.style.setProperty("top", "72px", "important");
        panel.style.setProperty("left", "10px", "important");
        panel.style.setProperty("right", "10px", "important");
        panel.style.setProperty("bottom", "92px", "important");
        panel.style.setProperty("z-index", "2147483646", "important");
        panel.style.setProperty("overflow", "auto", "important");
        panel.style.setProperty("padding", "12px", "important");
        panel.style.setProperty("border-radius", "18px", "important");
        panel.style.setProperty("background", "rgba(10,10,18,.96)", "important");
        panel.style.setProperty("border", "1px solid rgba(255,255,255,.16)", "important");
        panel.style.setProperty("box-shadow", "0 18px 50px rgba(0,0,0,.45)", "important");
    }

    function closePanel() {
        var panel = getPanel();
        if (!panel) return;
        panel.style.setProperty("display", "none", "important");
        panel.classList.add("hidden");
        panel.setAttribute("aria-hidden", "true");
        panel.removeAttribute("data-nova-final-session-actions");
    }

    function button(label) {
        var b = document.createElement("button");
        b.type = "button";
        b.textContent = label;
        b.style.setProperty("border", "1px solid rgba(255,255,255,.18)", "important");
        b.style.setProperty("background", "rgba(255,255,255,.09)", "important");
        b.style.setProperty("color", "#fff", "important");
        b.style.setProperty("border-radius", "12px", "important");
        b.style.setProperty("padding", "8px 10px", "important");
        b.style.setProperty("font-size", "13px", "important");
        b.style.setProperty("cursor", "pointer", "important");
        return b;
    }

    async function api(path, body) {
        var response = await fetch(path, {
            method: body ? "POST" : "GET",
            headers: body ? {
                "Content-Type": "application/json",
                "Accept": "application/json"
            } : {
                "Accept": "application/json"
            },
            body: body ? JSON.stringify(body) : undefined,
            cache: "no-store"
        });

        var data = await response.json();

        if (!response.ok || data.ok === false) {
            throw new Error(data.error || data.message || ("Request failed: " + path));
        }

        return data;
    }

    function messageText(message) {
        return String(
            (message && (message.text || message.content || message.body || message.message)) ||
            ""
        );
    }

    function renderLoadedSession(session) {
        if (!session || !session.id) return;

        try {
            localStorage.setItem("nova_mobile_active_session_id", String(session.id));
            localStorage.setItem("nova_active_session_id", String(session.id));
        } catch (error) {}

        api("/api/sessions/switch", { session_id: session.id }).catch(function () {});

        var chat = getChatBox();
        if (!chat) {
            closePanel();
            return;
        }

        var messages = Array.isArray(session.messages) ? session.messages : [];

        chat.innerHTML = "";

        if (!messages.length) {
            var empty = document.createElement("div");
            empty.className = "assistant-message mobile-message assistant";
            empty.textContent = "This saved session has no messages yet.";
            chat.appendChild(empty);
        }

        messages.forEach(function (message) {
            var role = String((message && message.role) || "assistant").toLowerCase();
            var bubble = document.createElement("div");
            bubble.className = "mobile-message " + (role === "user" ? "user" : "assistant");
            bubble.textContent = messageText(message);
            chat.appendChild(bubble);
        });

        try {
            chat.scrollTop = chat.scrollHeight;
        } catch (error) {}

        closePanel();

        console.log("[Nova Mobile Final Session Actions] opened", {
            id: session.id,
            messages: messages.length
        });
    }

    async function loadSessionById(sessionId) {
        var data = await api("/api/sessions/" + encodeURIComponent(sessionId));
        renderLoadedSession(data.session || data);
    }

    function renderRow(panel, session) {
        var row = document.createElement("div");
        row.setAttribute("data-nova-final-session-row", String(session.id || ""));
        row.style.setProperty("display", "grid", "important");
        row.style.setProperty("grid-template-columns", "1fr auto auto auto", "important");
        row.style.setProperty("gap", "6px", "important");
        row.style.setProperty("align-items", "center", "important");
        row.style.setProperty("margin", "0 0 8px 0", "important");
        row.style.setProperty("padding", "8px", "important");
        row.style.setProperty("border-radius", "14px", "important");
        row.style.setProperty("background", "rgba(255,255,255,.06)", "important");
        row.style.setProperty("border", "1px solid rgba(255,255,255,.12)", "important");

        var title = button((session.pinned ? "📌 " : "") + String(session.title || session.id || "Saved Session"));
        title.style.setProperty("text-align", "left", "important");
        title.style.setProperty("overflow", "hidden", "important");
        title.style.setProperty("text-overflow", "ellipsis", "important");
        title.style.setProperty("white-space", "nowrap", "important");
        title.onclick = function (event) {
            event.preventDefault();
            event.stopPropagation();
            loadSessionById(session.id).catch(function (error) {
                console.error("[Nova Mobile Final Session Actions] open failed", error);
                alert("Open failed");
            });
        };

        var pin = button(session.pinned ? "Unpin" : "Pin");
        pin.onclick = async function (event) {
            event.preventDefault();
            event.stopPropagation();

            try {
                await api("/api/sessions/pin", {
                    session_id: session.id,
                    pinned: !session.pinned
                });
                await renderFinalSessions(true);
            } catch (error) {
                console.error("[Nova Mobile Final Session Actions] pin failed", error);
                alert("Pin failed");
            }
        };

        var rename = button("Rename");
        rename.onclick = async function (event) {
            event.preventDefault();
            event.stopPropagation();

            var current = String(session.title || "");
            var next = prompt("Rename session:", current);
            if (next === null) return;

            next = String(next || "").trim();
            if (!next) return;

            try {
                await api("/api/sessions/rename", {
                    session_id: session.id,
                    title: next
                });
                await renderFinalSessions(true);
            } catch (error) {
                console.error("[Nova Mobile Final Session Actions] rename failed", error);
                alert("Rename failed");
            }
        };

        var del = button("Delete");
        del.style.setProperty("background", "rgba(255,70,70,.22)", "important");
        del.onclick = async function (event) {
            event.preventDefault();
            event.stopPropagation();

            if (!confirm("Delete this session?")) return;

            try {
                await api("/api/sessions/delete", {
                    session_id: session.id
                });
                await renderFinalSessions(true);
            } catch (error) {
                console.error("[Nova Mobile Final Session Actions] delete failed", error);
                alert("Delete failed");
            }
        };

        row.appendChild(title);
        row.appendChild(pin);
        row.appendChild(rename);
        row.appendChild(del);
        panel.appendChild(row);
    }

    async function renderFinalSessions(force) {
        var panel = getPanel();

        if (!panel) {
            panel = document.createElement("section");
            panel.id = "nova-mobile-sessions-panel";
            document.body.appendChild(panel);
        }

        if (rendering) return;
        if (!force && panel.getAttribute("data-nova-final-session-actions") === "ready") return;

        rendering = true;

        try {
            stylePanel(panel);
            panel.setAttribute("data-nova-final-session-actions", "rendering");
            panel.innerHTML = "";

            var header = document.createElement("div");
            header.style.setProperty("display", "flex", "important");
            header.style.setProperty("justify-content", "space-between", "important");
            header.style.setProperty("align-items", "center", "important");
            header.style.setProperty("gap", "8px", "important");
            header.style.setProperty("margin-bottom", "10px", "important");

            var title = document.createElement("strong");
            title.textContent = "Saved Sessions";
            title.style.setProperty("color", "#fff", "important");

            var close = button("Close");
            close.onclick = function (event) {
                event.preventDefault();
                event.stopPropagation();
                closePanel();
            };

            header.appendChild(title);
            header.appendChild(close);
            panel.appendChild(header);

            var data = await api("/api/sessions");
            var sessions = Array.isArray(data.sessions) ? data.sessions : [];

            sessions = sessions.filter(function (session) {
                return session && session.id;
            }).sort(function (a, b) {
                if (!!a.pinned !== !!b.pinned) {
                    return a.pinned ? -1 : 1;
                }

                return String(b.updated_at || b.created_at || "").localeCompare(
                    String(a.updated_at || a.created_at || "")
                );
            }).slice(0, 25);

            if (!sessions.length) {
                var empty = document.createElement("div");
                empty.textContent = "No saved sessions found yet.";
                empty.style.setProperty("padding", "12px", "important");
                empty.style.setProperty("color", "#fff", "important");
                panel.appendChild(empty);
            } else {
                sessions.forEach(function (session) {
                    renderRow(panel, session);
                });
            }

            panel.setAttribute("data-nova-final-session-actions", "ready");

            console.log("[Nova Mobile Final Session Actions] rendered", sessions.length);
        } catch (error) {
            console.error("[Nova Mobile Final Session Actions] render failed", error);
            panel.innerHTML = "<div class='mobile-session-item'>Failed to load sessions actions.</div>";
        } finally {
            rendering = false;
        }
    }

    function isSessionsButton(target) {
        if (!target || !target.closest) return false;

        var button = target.closest("button, a");
        if (!button) return false;
        if (button.closest("#nova-mobile-sessions-panel")) return false;

        var text = String(button.textContent || "").trim().toLowerCase();
        var id = String(button.id || "").toLowerCase();
        var cls = String(button.className || "").toLowerCase();
        var aria = String(button.getAttribute("aria-label") || "").toLowerCase();

        return (
            text === "sessions" ||
            id.includes("session") ||
            cls.includes("session") ||
            aria.includes("session")
        );
    }

    document.addEventListener("click", function (event) {
        if (!isSessionsButton(event.target)) return;

        setTimeout(function () {
            renderFinalSessions(true);
        }, 80);
    }, true);

    setInterval(function () {
        var panel = getPanel();

        if (
            panel &&
            isPanelOpen(panel) &&
            panel.getAttribute("data-nova-final-session-actions") !== "ready"
        ) {
            renderFinalSessions(true);
        }
    }, 500);

    window.NovaMobileFinalSessionActionsOpen = function () {
        renderFinalSessions(true);
    };

    console.log("[Nova Mobile Final Session Actions] ready");
})();
