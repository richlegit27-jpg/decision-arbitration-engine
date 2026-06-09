/* NOVA_MOBILE_SESSIONS_MODULE_20260606 */

(function () {
    "use strict";

    function $(id) {
        return document.getElementById(id);
    }

    function requireApi() {
        const api = window.NovaMobileSessionDeps || {};

        const required = [
            "state",
            "getSessionId",
            "chatBox",
            "addBubble",
            "updateActiveSessionTitle",
            "scrollBottom",
            "newChat"
        ];

        for (const key of required) {
            if (!api[key]) {
                console.warn("[Nova Mobile Sessions] missing dependency:", key);
                return null;
            }
        }

        return api;
    }

    function ensureSessionsPanel() {
        let panel = $("nova-mobile-sessions-panel");

        if (panel) {
            return panel;
        }

        panel = document.createElement("section");
        panel.id = "nova-mobile-sessions-panel";
        panel.setAttribute("aria-label", "Mobile sessions");
        panel.className = "hidden";
        panel.style.display = "none";

        document.body.appendChild(panel);

        return panel;
    }

    function openSessionsPanel(panel) {
        if (!panel) return;

        panel.className = "";
        panel.removeAttribute("aria-hidden");

        panel.style.cssText =
            "display:block !important;" +
            "visibility:visible !important;" +
            "opacity:1 !important;" +
            "position:fixed !important;" +
            "top:50px !important;" +
            "left:8px !important;" +
            "right:8px !important;" +
            "bottom:70px !important;" +
            "width:auto !important;" +
            "height:auto !important;" +
            "max-height:none !important;" +
            "overflow-y:auto !important;" +
            "z-index:2147483647 !important;" +
            "background:#0b1020 !important;" +
            "border:3px solid #7c5cff !important;" +
            "border-radius:16px !important;" +
            "padding:12px !important;" +
            "color:#f8fafc !important;" +
            "box-shadow:0 20px 80px rgba(0,0,0,.85) !important;" +
            "pointer-events:auto !important;" +
            "transform:none !important;";
    }

    function closeSessionsPanel(panel) {
        if (!panel) return;

        panel.style.setProperty("display", "none", "important");
        panel.classList.add("hidden");
    }

    function buttonBase(button) {
        button.style.color = "#f8fafc";
        button.style.border = "1px solid rgba(255,255,255,.16)";
        button.style.borderRadius = "10px";
        button.style.padding = "10px";
        button.style.cursor = "pointer";
    }

    function createSessionRow(session, sessionsPanel, api) {
        const row = document.createElement("div");
        row.style.display = "flex";
        row.style.gap = "6px";
        row.style.marginBottom = "6px";
        row.style.background = "rgba(255,255,255,.06)";
        row.style.border = "1px solid rgba(255,255,255,.14)";
        row.style.borderRadius = "12px";
        row.style.padding = "6px";

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "mobile-session-item";
        btn.style.flex = "1";
        btn.style.background = "rgba(124,92,255,.22)";
        btn.style.textAlign = "left";
        buttonBase(btn);

        const pinBtn = document.createElement("button");
        pinBtn.type = "button";
        pinBtn.title = "Pin session";
        pinBtn.style.width = "42px";
        pinBtn.style.flex = "0 0 42px";
        pinBtn.style.background = "rgba(124,92,255,.35)";
        buttonBase(pinBtn);

        const renameBtn = document.createElement("button");
        renameBtn.type = "button";
        renameBtn.textContent = "âœ";
        renameBtn.title = "Rename session";
        renameBtn.style.width = "42px";
        renameBtn.style.flex = "0 0 42px";
        renameBtn.style.background = "rgba(124,92,255,.45)";
        buttonBase(renameBtn);

        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.textContent = "ðŸ—‘";
        deleteBtn.title = "Delete session";
        deleteBtn.style.width = "42px";
        deleteBtn.style.flex = "0 0 42px";
        deleteBtn.style.background = "rgba(255,80,80,.35)";
        buttonBase(deleteBtn);

        const shortId = String(session.id || "").slice(-6);

        function currentTitle() {
            return (
                (api.state.sessionTitles && api.state.sessionTitles[session.id]) ||
                session.title ||
                "New Chat"
            );
        }

        function renderTitle() {
            const pinnedText = session.pinned ? "ðŸ“Œ " : "";

            btn.textContent = pinnedText + currentTitle() + " Â· " + shortId;
            pinBtn.textContent = session.pinned ? "ðŸ“Œ" : "ðŸ“";
        }

        renderTitle();

        btn.onclick = async function () {
            const currentSessionId = api.getSessionId();
            const box = api.chatBox();

            if (currentSessionId && box) {
                api.state.cachedMessages[currentSessionId] = box.innerHTML;
            }

            localStorage.setItem("nova_mobile_active_session_id", session.id);
            api.updateActiveSessionTitle(session);

            if (!box) return;

            box.innerHTML = "";

            if (api.state.cachedMessages[session.id]) {
                box.innerHTML = api.state.cachedMessages[session.id];
            } else {
                try {
                    const res = await fetch("/api/sessions/" + encodeURIComponent(session.id));
                    const sessionData = await res.json();
                    const messages = Array.isArray(sessionData.messages) ? sessionData.messages : [];

                    messages.forEach(function (msg) {
                        api.addBubble(msg.role || "assistant", msg.text || msg.content || "");
                    });
                } catch (err) {
                    api.addBubble("assistant", "Failed to load session messages.");
                }
            }

            closeSessionsPanel(sessionsPanel);
            api.scrollBottom();
        };

        pinBtn.onclick = async function (event) {
            event.preventDefault();
            event.stopPropagation();

            const nextPinned = !session.pinned;

            try {
                const response = await fetch("/api/sessions/pin", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        session_id: session.id,
                        pinned: nextPinned
                    })
                });

                if (!response.ok) {
                    throw new Error("Pin failed with HTTP " + response.status);
                }

                session.pinned = nextPinned;
                renderTitle();
                loadSessionsPanel(sessionsPanel);
            } catch (err) {
                alert("Pin failed");
            }
        };

        renameBtn.onclick = async function (event) {
            event.preventDefault();
            event.stopPropagation();

            const newTitle = prompt("Rename session:", currentTitle());

            if (!newTitle) return;

            try {
                const response = await fetch("/api/sessions/rename", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        session_id: session.id,
                        title: newTitle
                    })
                });

                if (!response.ok) {
                    throw new Error("Rename failed with HTTP " + response.status);
                }

                session.title = newTitle;
                api.state.sessionTitles[session.id] = newTitle;
                renderTitle();

                if (api.getSessionId() === session.id) {
                    api.updateActiveSessionTitle({
                        id: session.id,
                        title: newTitle
                    });
                }
            } catch (err) {
                alert("Rename failed");
            }
        };

        deleteBtn.onclick = async function (event) {
            event.preventDefault();
            event.stopPropagation();

            const title = currentTitle();
            const ok = confirm("Delete session: " + title + "?");

            if (!ok) return;

            try {
                const response = await fetch("/api/sessions/delete", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        session_id: session.id
                    })
                });

                if (!response.ok) {
                    throw new Error("Delete failed with HTTP " + response.status);
                }

                delete api.state.cachedMessages[session.id];
                delete api.state.sessionTitles[session.id];

                if (api.getSessionId() === session.id) {
                    api.newChat();
                }

                loadSessionsPanel(sessionsPanel);
            } catch (err) {
                alert("Delete failed");
            }
        };

        row.appendChild(btn);
        row.appendChild(pinBtn);
        row.appendChild(renameBtn);
        row.appendChild(deleteBtn);

        return row;
    }

    async function loadSessionsPanel(sessionsPanel) {
        const api = requireApi();
        if (!api || !sessionsPanel) return;

        sessionsPanel.innerHTML = "";

        const closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.className = "mobile-session-item";
        closeBtn.textContent = "Close Sessions";
        closeBtn.style.marginBottom = "10px";
        closeBtn.style.background = "rgba(255,255,255,.10)";
        buttonBase(closeBtn);

        closeBtn.onclick = function () {
            closeSessionsPanel(sessionsPanel);
        };

        sessionsPanel.appendChild(closeBtn);

        try {
            const response = await fetch("/api/sessions");
            const data = await response.json();

            const sessions = (Array.isArray(data.sessions) ? data.sessions : [])
                .filter(function (session) {
                    return session && session.id;
                })
                .sort(function (a, b) {
                    if (!!a.pinned !== !!b.pinned) {
                        return a.pinned ? -1 : 1;
                    }

                    const aTime = Date.parse(a.updated_at || a.created_at || "") || 0;
                    const bTime = Date.parse(b.updated_at || b.created_at || "") || 0;

                    return bTime - aTime;
                })
                .slice(0, 25);

            console.log("[Nova Mobile Sessions Module]", sessions);

            if (!sessions.length) {
                const empty = document.createElement("div");
                empty.textContent = "No saved sessions found yet.";
                empty.style.padding = "12px";
                sessionsPanel.appendChild(empty);
                return;
            }

            sessions.forEach(function (session) {
                sessionsPanel.appendChild(createSessionRow(session, sessionsPanel, api));
            });
        } catch (error) {
            const err = document.createElement("button");
            err.type = "button";
            err.className = "mobile-session-item";
            err.textContent = "Failed to load sessions";
            err.style.background = "rgba(255,80,80,.25)";
            buttonBase(err);
            sessionsPanel.appendChild(err);
        }
    }

    function findSessionsToggle() {
        let btn = $("nova-mobile-sessions-toggle-forced");

        if (btn) {
            return btn;
        }

        btn = document.createElement("button");
        btn.id = "nova-mobile-sessions-toggle-forced";
        btn.type = "button";
        btn.textContent = "â˜°";
        btn.title = "Sessions";

        btn.style.position = "fixed";
        btn.style.top = "12px";
        btn.style.left = "12px";
        btn.style.width = "48px";
        btn.style.height = "48px";
        btn.style.borderRadius = "999px";
        btn.style.zIndex = "2147483647";
        btn.style.background = "rgba(124,92,255,.98)";
        btn.style.color = "#ffffff";
        btn.style.border = "1px solid rgba(255,255,255,.30)";
        btn.style.fontSize = "24px";
        btn.style.display = "flex";
        btn.style.alignItems = "center";
        btn.style.justifyContent = "center";
        btn.style.boxShadow = "0 10px 30px rgba(0,0,0,.45)";
        btn.style.cursor = "pointer";

        document.body.appendChild(btn);

        return btn;
    }

    function wire() {
        const api = requireApi();
        if (!api) return false;

        const sessionsToggle = findSessionsToggle();
        const sessionsPanel = ensureSessionsPanel();

        if (!sessionsToggle || !sessionsPanel) return false;

        // NOVA_MOBILE_FORCED_SESSIONS_TOGGLE_DELEGATED_20260608
        // Sessions toggle click ownership lives in static/js/mobile/nova-mobile-events.js.
        // This module still owns sessions panel rendering/open/close helpers.

        window.NovaMobileOpenSessions = function () {
            openSessionsPanel(sessionsPanel);
            loadSessionsPanel(sessionsPanel);
        };

        console.log("[Nova Mobile Sessions Module] wired");
        return true;
    }

    window.NovaMobileSessions = {
        wire: wire,
        openSessionsPanel: openSessionsPanel,
        closeSessionsPanel: closeSessionsPanel,
        loadSessionsPanel: loadSessionsPanel
    };
})();

// NOVA_MOBILE_HARD_OPEN_SESSIONS_20260608
(function () {
    "use strict";

    function byId(id) {
        return document.getElementById(id);
    }

    function showElement(el) {
        if (!el) return;

        // NOVA_MOBILE_SESSIONS_REMOVE_HIDDEN_CLASS_20260608
        // The panel was found, but class="hidden" kept computed display as none.
        el.hidden = false;
        el.removeAttribute("hidden");
        el.removeAttribute("aria-hidden");
        el.setAttribute("aria-hidden", "false");

        el.classList.remove("hidden");
        el.classList.remove("is-hidden");
        el.classList.remove("closed");

        el.classList.add("open");
        el.classList.add("active");
        el.classList.add("is-open");
        el.classList.add("show");

        el.style.setProperty("display", "block", "important");
        el.style.setProperty("visibility", "visible", "important");
        el.style.setProperty("opacity", "1", "important");
        el.style.setProperty("pointer-events", "auto", "important");
        el.style.setProperty("position", "fixed", "important");
        el.style.setProperty("top", "0", "important");
        el.style.setProperty("right", "0", "important");
        el.style.setProperty("bottom", "0", "important");
        el.style.setProperty("width", "min(92vw, 420px)", "important");
        el.style.setProperty("max-width", "420px", "important");
        el.style.setProperty("overflow-y", "auto", "important");
        el.style.setProperty("transform", "translateX(0)", "important");
        el.style.setProperty("z-index", "99999", "important");
    }

    function findSessionPanel() {
        return (
            byId("nova-mobile-sessions-panel") ||
            byId("nova-mobile-session-panel") ||
            byId("nova-mobile-sessions-drawer") ||
            byId("nova-mobile-session-drawer") ||
            byId("nova-mobile-sessions") ||
            byId("mobile-sessions-panel") ||
            document.querySelector("[data-nova-mobile-sessions]") ||
            document.querySelector(".nova-mobile-sessions-panel") ||
            document.querySelector(".nova-mobile-sessions-drawer") ||
            document.querySelector(".mobile-sessions-panel") ||
            document.querySelector(".sessions-panel") ||
            document.querySelector(".sessions-drawer")
        );
    }

    function findSessionOverlay() {
        return (
            byId("nova-mobile-sessions-overlay") ||
            byId("nova-mobile-session-overlay") ||
            document.querySelector(".nova-mobile-sessions-overlay") ||
            document.querySelector(".sessions-overlay")
        );
    }

    function openSessions(event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        var panel = findSessionPanel();
        var overlay = findSessionOverlay();

        showElement(panel);
        showElement(overlay);

        if (window.NovaMobileSessions && typeof window.NovaMobileSessions.loadSessionsPanel === "function") {
            window.NovaMobileSessions.loadSessionsPanel(panel);
        }

        document.body.classList.add("sessions-open");
        document.body.classList.add("nova-mobile-sessions-open");

        if (typeof window.NovaMobileRenderSessions === "function") {
            window.NovaMobileRenderSessions();
        }

        if (typeof window.renderMobileSessions === "function") {
            window.renderMobileSessions();
        }

        if (typeof window.renderSessions === "function") {
            window.renderSessions();
        }

        console.log("[Nova Mobile Sessions] hard open fired", {
            panelFound: !!panel,
            overlayFound: !!overlay
        });
    }

    function closeSessions(event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        var panel = findSessionPanel();
        var overlay = findSessionOverlay();

        [panel, overlay].forEach(function (el) {
            if (!el) return;

            el.classList.remove("open");
            el.classList.remove("active");
            el.classList.remove("is-open");
            el.classList.remove("show");

            el.setAttribute("aria-hidden", "true");
            el.style.display = "none";
            el.style.pointerEvents = "none";
        });

        document.body.classList.remove("sessions-open");
        document.body.classList.remove("nova-mobile-sessions-open");
    }

    function bindSessionButtons() {
        var selectors = [
            "#nova-mobile-sessions-button",
            "#nova-mobile-session-button",
            "#nova-mobile-open-sessions",
            "#nova-mobile-sessions-toggle",
            "#mobile-sessions-button",
            "#sessions-button",
            "[data-action='sessions']",
            "[data-action='open-sessions']",
            "[data-nova-open-sessions]",
            ".nova-mobile-sessions-button",
            ".mobile-sessions-button",
            ".sessions-button"
        ];

        var buttons = [];

        selectors.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (button) {
                if (buttons.indexOf(button) === -1) {
                    buttons.push(button);
                }
            });
        });

        buttons.forEach(function (button) {
            if (button.dataset.novaHardSessionsBound === "1") return;
            button.dataset.novaHardSessionsBound = "1";
            button.addEventListener("click", openSessions, true);
        });

        document.querySelectorAll("[data-action='close-sessions'], .sessions-close, .nova-mobile-sessions-close").forEach(function (button) {
            if (button.dataset.novaHardSessionsCloseBound === "1") return;
            button.dataset.novaHardSessionsCloseBound = "1";
            button.addEventListener("click", closeSessions, true);
        });

        console.log("[Nova Mobile Sessions] hard open bridge ready", buttons.length);
    }

    window.NovaMobileSessionsHardOpen = openSessions;
    window.NovaOpenMobileSessions = openSessions;
    window.NovaMobileOpenSessions = openSessions;
    window.openMobileSessions = openSessions;

    window.NovaMobileSessionsHardClose = closeSessions;
    window.NovaCloseMobileSessions = closeSessions;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bindSessionButtons);
    } else {
        bindSessionButtons();
    }

    window.addEventListener("load", bindSessionButtons);
    setTimeout(bindSessionButtons, 250);
    setTimeout(bindSessionButtons, 1000);
})();
