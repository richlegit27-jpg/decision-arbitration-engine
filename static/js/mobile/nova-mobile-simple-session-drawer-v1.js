(function () {
    "use strict";

    const MARK = "NOVA_MOBILE_CLEAN_SESSION_DRAWER_V3_CLOSE_TOGGLE_20260704";
    const OLD_MARK = "NOVA_MOBILE_SIMPLE_SESSION_DRAWER_V1_20260704";
    const OLD_ISOLATED_MARK = "NOVA_MOBILE_SIMPLE_SESSION_DRAWER_ISOLATED_V2_20260704";

    const BUTTON_ID = "nova-clean-session-launcher-v2";
    const PANEL_ID = "nova-clean-session-panel-v2";
    const ROW_ATTR = "data-nova-clean-session-row-v3";
    const ACTION_ATTR = "data-nova-clean-session-action-v3";

    if (window[MARK]) {
        return;
    }

    window[MARK] = true;
    window[OLD_MARK] = true;
    window[OLD_ISOLATED_MARK] = true;

    let panelOpen = false;
    let cachedSessions = [];

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function getSessionId(item) {
        return item && String(item.id || item.session_id || item.sessionId || "");
    }

    function getCurrentSessionId() {
        try {
            return (
                new URLSearchParams(location.search).get("session_id") ||
                localStorage.getItem("nova_mobile_active_session_id") ||
                localStorage.getItem("nova_active_session_id") ||
                localStorage.getItem("active_session_id") ||
                ""
            );
        } catch (_) {
            return "";
        }
    }

    function setCurrentSessionId(sessionId) {
        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("active_session_id", sessionId);
        } catch (_) {}
    }

    function openSession(sessionId) {
        if (!sessionId) {
            return;
        }

        setCurrentSessionId(sessionId);
        location.href = "/mobile?session_id=" + encodeURIComponent(sessionId) + "&v=clean-session-open-" + Date.now();
    }

    async function fetchJson(url, options) {
        const res = await fetch(url, Object.assign({
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        }, options || {}));

        if (!res.ok) {
            throw new Error("HTTP " + res.status + " for " + url);
        }

        const text = await res.text();

        if (!text) {
            return {};
        }

        try {
            return JSON.parse(text);
        } catch (_) {
            return { ok: true, text: text };
        }
    }

    async function postJson(url, body) {
        return await fetchJson(url, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body || {})
        });
    }

    async function postSessionAction(action, sessionId, payload) {
        const safeId = encodeURIComponent(sessionId);
        const body = Object.assign({
            id: sessionId,
            session_id: sessionId,
            sessionId: sessionId
        }, payload || {});

        const candidates = [
            {
                url: "/api/sessions/" + action,
                body: body
            },
            {
                url: "/api/sessions/" + safeId + "/" + action,
                body: payload || {}
            },
            {
                url: "/api/sessions/" + safeId,
                body: Object.assign({ action: action }, body)
            }
        ];

        let lastError = null;

        for (const candidate of candidates) {
            try {
                const result = await postJson(candidate.url, candidate.body);
                console.error("[Nova Clean Sessions] action ok", {
                    action: action,
                    url: candidate.url,
                    result: result
                });
                return result;
            } catch (err) {
                lastError = err;
                console.error("[Nova Clean Sessions] action failed candidate", {
                    action: action,
                    url: candidate.url,
                    error: String(err && err.message || err)
                });
            }
        }

        throw lastError || new Error("Session action failed: " + action);
    }

    async function fetchSessionById(sessionId) {
        if (!sessionId) {
            return null;
        }

        try {
            const data = await fetchJson("/api/sessions/" + encodeURIComponent(sessionId) + "?clean_drawer_session=" + Date.now());
            const session = data.session || data.item || data;

            if (session && !getSessionId(session)) {
                session.id = sessionId;
            }

            return session;
        } catch (err) {
            console.error("[Nova Clean Sessions] current session fetch failed", err);
            return {
                id: sessionId,
                title: "Current Session",
                message_count: "?"
            };
        }
    }

    async function fetchSessions() {
        const currentId = getCurrentSessionId();
        const data = await fetchJson("/api/sessions?clean_drawer=" + Date.now());
        const sessions = data.sessions || data.items || [];
        const map = new Map();

        function addSession(session) {
            const sessionId = getSessionId(session);

            if (!sessionId) {
                return;
            }

            map.set(sessionId, Object.assign({}, session, { id: sessionId }));
        }

        const currentSession = await fetchSessionById(currentId);

        if (currentSession) {
            addSession(currentSession);
        }

        sessions.forEach(addSession);

        if (currentId && !map.has(currentId)) {
            addSession({
                id: currentId,
                title: "Current Session",
                message_count: "?"
            });
        }

        const merged = Array.from(map.values());

        merged.sort(function (a, b) {
            const aId = getSessionId(a);
            const bId = getSessionId(b);

            if (aId === currentId) {
                return -1;
            }

            if (bId === currentId) {
                return 1;
            }

            if (!!b.pinned !== !!a.pinned) {
                return b.pinned ? 1 : -1;
            }

            const aTime = Date.parse(a.updated_at || a.updatedAt || "") || 0;
            const bTime = Date.parse(b.updated_at || b.updatedAt || "") || 0;

            return bTime - aTime;
        });

        cachedSessions = merged;

        return {
            currentId: currentId,
            activeSessionId: data.active_session_id || "",
            sessions: merged
        };
    }

    function getSessionTitle(session) {
        return session.title || "New Chat";
    }

    function getSessionCount(session) {
        return session.message_count == null ? 0 : session.message_count;
    }

    function actionControl(label, action) {
        return (
            "<span " + ACTION_ATTR + "='" + escapeHtml(action) + "' " +
            "style='display:inline-flex;align-items:center;justify-content:center;border:1px solid rgba(255,255,255,.18);background:#24242b;color:white;border-radius:999px;padding:7px 9px;font-size:12px;font-weight:750;margin-right:6px;margin-top:10px;'>" +
            escapeHtml(label) +
            "</span>"
        );
    }

    function rowHtml(session, currentId) {
        const sessionId = getSessionId(session);
        const title = getSessionTitle(session);
        const count = getSessionCount(session);
        const isActive = sessionId === currentId;
        const pin = session.pinned ? " · pinned" : "";
        const active = isActive ? " · active" : "";

        return (
            "<div style='font-weight:850;margin-bottom:4px;'>" + escapeHtml(title) + "</div>" +
            "<div style='opacity:.78;font-size:12px;overflow-wrap:anywhere;'>" + escapeHtml(sessionId) + "</div>" +
            "<div style='opacity:.78;font-size:12px;margin-top:4px;'>" + escapeHtml(count) + " messages" + pin + active + "</div>" +
            "<div style='display:flex;flex-wrap:wrap;gap:0;margin-top:2px;'>" +
                actionControl("Rename", "rename") +
                actionControl(session.pinned ? "Unpin" : "Pin", "pin") +
                actionControl("Delete", "delete") +
            "</div>"
        );
    }

    function makeButton() {
        let btn = document.getElementById(BUTTON_ID);

        if (btn) {
            return btn;
        }

        btn = document.createElement("button");
        btn.id = BUTTON_ID;
        btn.type = "button";
        btn.textContent = "Sessions";
        btn.style.cssText = [
            "position:fixed",
            "left:10px",
            "top:10px",
            "z-index:2147483647",
            "border:1px solid rgba(255,255,255,.25)",
            "background:#17171c",
            "color:white",
            "border-radius:999px",
            "padding:10px 14px",
            "font:600 14px system-ui,-apple-system,Segoe UI,sans-serif",
            "box-shadow:0 8px 24px rgba(0,0,0,.35)"
        ].join(";");

        btn.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            if (isPanelOpenVisible()) {
                closePanel();
                return;
            }

            renderDrawer();
        });

        document.body.appendChild(btn);
        forceVisibleButton();

        return btn;
    }

    function makePanel() {
        let panel = document.getElementById(PANEL_ID);

        if (panel) {
            return panel;
        }

        panel = document.createElement("div");
        panel.id = PANEL_ID;
        panel.style.cssText = [
            "position:fixed",
            "left:10px",
            "right:10px",
            "top:56px",
            "max-height:72vh",
            "overflow:auto",
            "z-index:2147483647",
            "background:#101014",
            "color:white",
            "border:1px solid rgba(255,255,255,.18)",
            "border-radius:16px",
            "box-shadow:0 18px 60px rgba(0,0,0,.55)",
            "padding:12px",
            "display:none",
            "font:14px system-ui,-apple-system,Segoe UI,sans-serif"
        ].join(";");

        document.body.appendChild(panel);

        return panel;
    }

    function closePanel() {
        panelOpen = false;

        const panel = document.getElementById(PANEL_ID);

        if (panel) {
            panel.style.setProperty("display", "none", "important");
            panel.style.setProperty("pointer-events", "none", "important");
            panel.style.setProperty("visibility", "hidden", "important");
            panel.style.setProperty("opacity", "0", "important");
        }
    }

    function isPanelOpenVisible() {
        const panel = document.getElementById(PANEL_ID);

        if (!panel || !panelOpen) {
            return false;
        }

        const style = getComputedStyle(panel);

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            style.opacity !== "0"
        );
    }

    function forceVisibleButton() {
        const btn = document.getElementById(BUTTON_ID);

        if (!btn) {
            return;
        }

        btn.removeAttribute("hidden");
        btn.removeAttribute("data-nova-hidden-by-session-owner");
        btn.removeAttribute("data-nova-hidden-by-sessions-final");
        btn.disabled = false;

        btn.style.setProperty("display", "inline-flex", "important");
        btn.style.setProperty("pointer-events", "auto", "important");
        btn.style.setProperty("visibility", "visible", "important");
        btn.style.setProperty("opacity", "1", "important");
        btn.style.setProperty("align-items", "center", "important");
        btn.style.setProperty("justify-content", "center", "important");
        btn.style.setProperty("position", "fixed", "important");
        btn.style.setProperty("left", "10px", "important");
        btn.style.setProperty("top", "10px", "important");
        btn.style.setProperty("z-index", "2147483647", "important");
    }

    function forceVisiblePanel() {
        const panel = document.getElementById(PANEL_ID);

        if (!panel || !panelOpen) {
            return;
        }

        panel.removeAttribute("hidden");
        panel.removeAttribute("data-nova-hidden-by-session-owner");
        panel.removeAttribute("data-nova-hidden-by-sessions-final");

        panel.style.setProperty("display", "block", "important");
        panel.style.setProperty("pointer-events", "auto", "important");
        panel.style.setProperty("visibility", "visible", "important");
        panel.style.setProperty("opacity", "1", "important");
        panel.style.setProperty("position", "fixed", "important");
        panel.style.setProperty("left", "10px", "important");
        panel.style.setProperty("right", "10px", "important");
        panel.style.setProperty("top", "56px", "important");
        panel.style.setProperty("z-index", "2147483647", "important");
    }

    function forceVisibleRows() {
        const panel = document.getElementById(PANEL_ID);

        if (!panel) {
            return;
        }

        panel.querySelectorAll("[" + ROW_ATTR + "]").forEach(function (row) {
            row.removeAttribute("hidden");
            row.removeAttribute("data-nova-hidden-by-session-owner");
            row.removeAttribute("data-nova-hidden-by-sessions-final");

            row.style.setProperty("display", "block", "important");
            row.style.setProperty("pointer-events", "auto", "important");
            row.style.setProperty("visibility", "visible", "important");
            row.style.setProperty("opacity", "1", "important");
            row.style.setProperty("position", "relative", "important");
            row.style.setProperty("z-index", "2147483647", "important");
        });

        panel.querySelectorAll("[" + ACTION_ATTR + "]").forEach(function (action) {
            action.style.setProperty("display", "inline-flex", "important");
            action.style.setProperty("pointer-events", "auto", "important");
            action.style.setProperty("visibility", "visible", "important");
            action.style.setProperty("opacity", "1", "important");
        });
    }

    function rescueOpenPanelSoon() {
        function run() {
            forceVisibleButton();
            forceVisiblePanel();
            forceVisibleRows();
        }

        run();
        setTimeout(run, 25);
        setTimeout(run, 100);
        setTimeout(run, 300);
        setTimeout(run, 700);
        setTimeout(run, 1200);
    }

    async function handleAction(event, session) {
        const actionEl = event.target && event.target.closest && event.target.closest("[" + ACTION_ATTR + "]");

        if (!actionEl) {
            return false;
        }

        event.preventDefault();
        event.stopPropagation();

        const action = actionEl.getAttribute(ACTION_ATTR);
        const sessionId = getSessionId(session);

        if (!sessionId) {
            return true;
        }

        try {
            if (action === "rename") {
                const oldTitle = getSessionTitle(session);
                const title = prompt("Rename session:", oldTitle);

                if (!title || !title.trim()) {
                    return true;
                }

                await postSessionAction("rename", sessionId, {
                    title: title.trim(),
                    name: title.trim()
                });

                await renderDrawer();
                return true;
            }

            if (action === "pin") {
                await postSessionAction("pin", sessionId, {
                    pinned: !session.pinned,
                    value: !session.pinned
                });

                await renderDrawer();
                return true;
            }

            if (action === "delete") {
                const title = getSessionTitle(session);

                if (!confirm("Delete session \"" + title + "\"?")) {
                    return true;
                }

                await postSessionAction("delete", sessionId, {});

                const currentId = getCurrentSessionId();

                if (sessionId === currentId) {
                    const next = cachedSessions.find(function (item) {
                        return getSessionId(item) && getSessionId(item) !== sessionId;
                    });

                    if (next) {
                        openSession(getSessionId(next));
                    } else {
                        location.href = "/mobile?v=clean-session-delete-" + Date.now();
                    }

                    return true;
                }

                await renderDrawer();
                return true;
            }
        } catch (err) {
            console.error("[Nova Clean Sessions] action failed final", err);
            alert("Session action failed. Check console for endpoint details.");
        }

        return true;
    }

    function currentSummaryHtml(data) {
        const currentId = data.currentId;
        const current = data.sessions.find(function (session) {
            return getSessionId(session) === currentId;
        });

        if (!current) {
            return "";
        }

        return (
            "<div style='border:1px solid rgba(140,120,255,.45);background:#19152b;border-radius:14px;padding:10px;margin-bottom:10px;'>" +
                "<div style='font-size:11px;opacity:.7;font-weight:800;text-transform:uppercase;letter-spacing:.04em;'>Current</div>" +
                "<div style='font-weight:900;margin-top:3px;'>" + escapeHtml(getSessionTitle(current)) + "</div>" +
                "<div style='opacity:.76;font-size:12px;overflow-wrap:anywhere;margin-top:3px;'>" + escapeHtml(currentId) + "</div>" +
                "<div style='opacity:.76;font-size:12px;margin-top:3px;'>" + escapeHtml(getSessionCount(current)) + " messages</div>" +
            "</div>"
        );
    }

    async function renderDrawer() {
        const panel = makePanel();

        panelOpen = true;
        panel.style.setProperty("display", "block", "important");
        panel.innerHTML = "<div style='padding:10px;'>Loading sessions...</div>";

        rescueOpenPanelSoon();

        try {
            const data = await fetchSessions();
            const currentId = data.currentId;

            const header = document.createElement("div");
            header.style.cssText = "display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px;";

            const title = document.createElement("div");
            title.textContent = "Sessions";
            title.style.cssText = "font-weight:900;font-size:16px;";

            const close = document.createElement("button");
            close.type = "button";
            close.textContent = "Close";
            close.style.cssText = "background:#24242b;color:white;border:1px solid rgba(255,255,255,.2);border-radius:10px;padding:8px 10px;";
            close.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                closePanel();
            });

            header.appendChild(title);
            header.appendChild(close);

            const summary = document.createElement("div");
            summary.innerHTML = currentSummaryHtml(data);

            const list = document.createElement("div");
            list.style.cssText = "display:flex;flex-direction:column;gap:8px;";

            data.sessions.forEach(function (session) {
                const sessionId = getSessionId(session);
                const isActive = sessionId === currentId;
                const row = document.createElement("div");

                row.setAttribute(ROW_ATTR, "true");
                row.tabIndex = 0;
                row.dataset.sessionId = sessionId;
                row.dataset.title = getSessionTitle(session);
                row.dataset.meta = getSessionCount(session) + " messages" + (session.pinned ? " · pinned" : "") + (isActive ? " · active" : "");

                row.style.cssText = [
                    "width:100%",
                    "box-sizing:border-box",
                    "text-align:left",
                    "border-radius:14px",
                    "border:1px solid " + (isActive ? "rgba(140,120,255,.85)" : "rgba(255,255,255,.14)"),
                    "background:" + (isActive ? "#27213f" : "#18181f"),
                    "color:white",
                    "padding:12px",
                    "display:block",
                    "cursor:pointer",
                    "user-select:none"
                ].join(";");

                row.innerHTML = rowHtml(session, currentId);

                row.addEventListener("click", async function (event) {
                    const handled = await handleAction(event, session);

                    if (handled) {
                        return;
                    }

                    openSession(sessionId);
                });

                row.addEventListener("keydown", function (event) {
                    if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        openSession(sessionId);
                    }
                });

                list.appendChild(row);
            });

            panel.innerHTML = "";
            panel.appendChild(header);
            panel.appendChild(summary);

            if (!data.sessions.length) {
                const empty = document.createElement("div");
                empty.textContent = "No sessions returned.";
                empty.style.cssText = "opacity:.75;padding:10px;";
                panel.appendChild(empty);
            } else {
                panel.appendChild(list);
            }

            rescueOpenPanelSoon();

            console.error("[Nova Clean Sessions V3] rendered", {
                count: data.sessions.length,
                currentId: currentId,
                activeSessionId: data.activeSessionId
            });
        } catch (err) {
            panel.innerHTML = "<div style='padding:10px;color:#ffb4b4;'>Failed to load sessions.</div>";
            console.error("[Nova Clean Sessions V3] failed", err);
        }
    }

    function installRescue() {
        forceVisibleButton();

        window.setInterval(function () {
            forceVisibleButton();
            forceVisiblePanel();
            forceVisibleRows();
        }, 1000);

        try {
            const observer = new MutationObserver(function () {
                forceVisibleButton();
                forceVisiblePanel();
                forceVisibleRows();
            });

            observer.observe(document.documentElement, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ["style", "hidden", "data-nova-hidden-by-session-owner", "data-nova-hidden-by-sessions-final"]
            });
        } catch (_) {}
    }

    window.NovaMobileSimpleSessionDrawerV1 = {
        version: "clean-v3-close-toggle",
        renderDrawer: renderDrawer,
        openSession: openSession
    };

    function boot() {
        makeButton();
        installRescue();
        console.error("[Nova Clean Sessions V3 Close Toggle] installed");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
