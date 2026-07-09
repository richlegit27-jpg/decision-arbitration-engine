(function () {
    "use strict";

    const MARK = "__NOVA_MOBILE_SESSION_SWITCH_RESTORE_V1_20260704__";

    if (window[MARK]) {
        return;
    }

    window[MARK] = true;

    const PANEL_ID = "nova-session-switch-restore-panel-v1";

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function isSessionsLauncher(button) {
        if (!button) {
            return false;
        }

        const id = String(button.id || "").toLowerCase();
        const text = String(button.textContent || "").trim().toLowerCase();
        const aria = String(button.getAttribute("aria-label") || "").trim().toLowerCase();

        return (
            id === "nova-mobile-sessions-toggle" ||
            id === "nova-clean-session-launcher-v2" ||
            text === "sessions" ||
            aria === "sessions"
        );
    }

    function getChatContainer() {
        return (
            document.getElementById("mobileChatMessages") ||
            document.getElementById("nova-mobile-chat-messages") ||
            document.querySelector("[data-mobile-chat-messages]") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector(".chat-messages")
        );
    }

    function normalizeSessions(payload) {
        return (
            payload &&
            (
                payload.items ||
                payload.sessions ||
                payload.data ||
                []
            )
        ) || [];
    }

    function normalizeMessages(payload) {
        return (
            payload &&
            payload.session &&
            Array.isArray(payload.session.messages)
        )
            ? payload.session.messages
            : [];
    }

    function setActiveSessionId(sessionId) {
        if (!sessionId) {
            return;
        }

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("active_session_id", sessionId);
        } catch (err) {}

        try {
            const url = new URL(window.location.href);
            url.searchParams.set("session_id", sessionId);
            url.searchParams.set("v", "session-switch-restore-" + Date.now());
            history.replaceState({}, "", url.toString());
        } catch (err) {}

        window.__novaActiveSessionId = sessionId;
        window.__NOVA_ACTIVE_SESSION_ID__ = sessionId;
    }

    function renderMessagesFallback(payload) {
        const chat = getChatContainer();
        const messages = normalizeMessages(payload);

        if (!chat) {
            console.error("[Nova Session Switch Restore V1] chat container missing");
            return false;
        }

        chat.innerHTML = "";

        messages.forEach(function (message) {
            const role = String(message.role || "assistant").toLowerCase();
            const text = String(message.text || message.content || "");

            const item = document.createElement("div");
            item.className = "nova-session-restored-message nova-session-restored-message-" + role;
            item.setAttribute("data-role", role);
            item.style.cssText = [
                "margin:10px 8px",
                "padding:10px 12px",
                "border-radius:14px",
                "white-space:pre-wrap",
                "line-height:1.4",
                "font-size:14px",
                role === "user"
                    ? "background:rgba(124,92,255,.22);border:1px solid rgba(124,92,255,.35);margin-left:38px"
                    : "background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);margin-right:38px"
            ].join(";");

            item.textContent = text;
            chat.appendChild(item);

            if (Array.isArray(message.attachments) && message.attachments.length) {
                const attach = document.createElement("div");
                attach.style.cssText = "margin-top:8px;font-size:12px;opacity:.8;";
                attach.textContent = "Attachments: " + message.attachments.map(function (a) {
                    return a.filename || a.name || a.url || "file";
                }).join(", ");
                item.appendChild(attach);
            }
        });

        try {
            chat.scrollTop = chat.scrollHeight;
        } catch (err) {}

        console.error("[Nova Session Switch Restore V1] fallback rendered messages", messages.length);

        return true;
    }

    function renderSessionPayload(payload) {
        const sessionId = payload && payload.session && payload.session.id;

        if (sessionId) {
            setActiveSessionId(sessionId);
        }

        let rendered = false;

        try {
            if (
                window.NovaMobileChatVisibleRecoveryV1 &&
                typeof window.NovaMobileChatVisibleRecoveryV1.renderPayload === "function"
            ) {
                window.NovaMobileChatVisibleRecoveryV1.renderPayload(payload);
                rendered = true;
                console.error("[Nova Session Switch Restore V1] rendered with VisibleRecovery");
            }
        } catch (err) {
            console.error("[Nova Session Switch Restore V1] VisibleRecovery render failed", err);
        }

        if (!rendered) {
            rendered = renderMessagesFallback(payload);
        }

        try {
            window.dispatchEvent(new CustomEvent("nova:session-switched", {
                detail: {
                    sessionId: sessionId,
                    payload: payload
                }
            }));
        } catch (err) {}

        return rendered;
    }

    async function fetchJson(url, options) {
        const response = await fetch(url, Object.assign({
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        }, options || {}));

        if (!response.ok) {
            const text = await response.text().catch(function () {
                return "";
            });

            throw new Error("HTTP " + response.status + " " + text.slice(0, 200));
        }

        return await response.json();
    }

    async function switchToSession(sessionId) {
        if (!sessionId) {
            return false;
        }

        console.error("[Nova Session Switch Restore V1] switching session", sessionId);

        const payload = await fetchJson("/api/sessions/" + encodeURIComponent(sessionId) + "?cache_bust=" + Date.now());

        if (!payload || !payload.ok || !payload.session) {
            console.error("[Nova Session Switch Restore V1] bad session payload", payload);
            return false;
        }

        renderSessionPayload(payload);
        closePanel();

        return true;
    }

    function closePanel() {
        const panel = document.getElementById(PANEL_ID);

        if (panel) {
            panel.remove();
            console.error("[Nova Session Switch Restore V1] closed panel");
        }
    }

    function renderPanel(sessions, activeSessionId) {
        closePanel();

        const panel = document.createElement("div");
        panel.id = PANEL_ID;
        panel.setAttribute("role", "dialog");
        panel.setAttribute("aria-label", "Sessions");
        panel.style.cssText = [
            "position:fixed",
            "top:64px",
            "right:10px",
            "left:10px",
            "max-height:72vh",
            "overflow:auto",
            "z-index:2147483647",
            "background:rgba(18,18,24,.98)",
            "color:white",
            "border:1px solid rgba(255,255,255,.18)",
            "border-radius:18px",
            "box-shadow:0 18px 60px rgba(0,0,0,.55)",
            "padding:12px",
            "-webkit-overflow-scrolling:touch"
        ].join(";");

        const header = document.createElement("div");
        header.style.cssText = "display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px;";
        header.innerHTML = '<div style="font-weight:900;font-size:16px;">Sessions</div>';

        const close = document.createElement("button");
        close.type = "button";
        close.textContent = "Close";
        close.style.cssText = "border:1px solid rgba(255,255,255,.2);background:rgba(255,255,255,.1);color:white;border-radius:12px;padding:8px 10px;";
        close.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            closePanel();
        }, true);

        header.appendChild(close);
        panel.appendChild(header);

        const newChat = document.createElement("button");
        newChat.type = "button";
        newChat.textContent = "New Chat";
        newChat.style.cssText = "width:100%;margin:0 0 10px 0;border:1px solid rgba(124,92,255,.55);background:rgba(124,92,255,.22);color:white;border-radius:14px;padding:11px 12px;font-weight:800;text-align:left;";
        newChat.addEventListener("click", async function (event) {
            event.preventDefault();
            event.stopPropagation();

            try {
                const payload = await fetchJson("/api/sessions/new", {
                    method: "POST"
                });

                const sessionId =
                    payload.session_id ||
                    (payload.session && payload.session.id) ||
                    payload.id;

                if (sessionId) {
                    await switchToSession(sessionId);
                } else {
                    location.href = "/mobile?v=new-chat-" + Date.now();
                }
            } catch (err) {
                console.error("[Nova Session Switch Restore V1] new chat failed", err);
                location.href = "/mobile?v=new-chat-fallback-" + Date.now();
            }
        }, true);

        panel.appendChild(newChat);

        if (!sessions.length) {
            const empty = document.createElement("div");
            empty.textContent = "No sessions found.";
            empty.style.cssText = "opacity:.75;padding:12px;";
            panel.appendChild(empty);
        }

        sessions.forEach(function (session) {
            const row = document.createElement("button");
            const sessionId = session.id || session.session_id || "";
            const title = session.title || "Untitled";
            const count = Number(session.message_count || 0);
            const pinned = session.pinned ? "📌 " : "";
            const active = sessionId && sessionId === activeSessionId;

            row.type = "button";
            row.setAttribute("data-session-id", sessionId);
            row.style.cssText = [
                "display:block",
                "width:100%",
                "text-align:left",
                "margin:8px 0",
                "padding:11px 12px",
                "border-radius:14px",
                active
                    ? "border:1px solid rgba(124,92,255,.8);background:rgba(124,92,255,.24)"
                    : "border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.07)",
                "color:white"
            ].join(";");

            row.innerHTML =
                '<div style="font-weight:850;">' + escapeHtml(pinned + title) + '</div>' +
                '<div style="opacity:.72;font-size:12px;margin-top:3px;">' +
                    escapeHtml(sessionId) + ' · ' + count + ' messages' +
                '</div>';

            row.addEventListener("click", async function (event) {
                event.preventDefault();
                event.stopPropagation();

                try {
                    await switchToSession(sessionId);
                } catch (err) {
                    console.error("[Nova Session Switch Restore V1] switch failed", sessionId, err);
                    alert("Session switch failed: " + err.message);
                }
            }, true);

            panel.appendChild(row);
        });

        document.body.appendChild(panel);

        console.error("[Nova Session Switch Restore V1] rendered panel sessions", sessions.length);
    }

    async function openPanel() {
        console.error("[Nova Session Switch Restore V1] opening sessions panel");

        const payload = await fetchJson("/api/sessions?cache_bust=" + Date.now());
        const sessions = normalizeSessions(payload);
        const activeSessionId =
            payload.active_session_id ||
            localStorage.getItem("nova_mobile_active_session_id") ||
            new URLSearchParams(location.search).get("session_id") ||
            "";

        renderPanel(sessions, activeSessionId);
    }

    function bindLaunchers() {
        ["pointerdown", "touchstart", "mousedown", "click"].forEach(function (eventName) {
            document.addEventListener(eventName, function (event) {
                const button = event.target && event.target.closest
                    ? event.target.closest("button, [role='button'], a")
                    : null;

                if (!isSessionsLauncher(button)) {
                    return;
                }

                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();

                openPanel().catch(function (err) {
                    console.error("[Nova Session Switch Restore V1] open failed", err);
                    alert("Sessions failed to open: " + err.message);
                });

                return false;
            }, true);
        });

        console.error("[Nova Session Switch Restore V1] launcher bound");
    }

    window.NovaMobileSessionSwitchRestoreV1 = {
        version: "session-switch-restore-v1",
        openPanel: openPanel,
        closePanel: closePanel,
        switchToSession: switchToSession,
        renderSessionPayload: renderSessionPayload
    };

    bindLaunchers();

    console.error("[Nova Session Switch Restore V1] installed");
})();
