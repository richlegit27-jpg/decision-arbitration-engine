(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSION_CLEAN_OWNER_V1_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_CLEAN_OWNER_V1_20260705__ = true;

    const API = {
        list: "/api/sessions",
        create: "/api/sessions/new",
        rename: ["/api/sessions/rename"],
        pin: ["/api/sessions/pin"],
        delete: ["/api/sessions/delete"]
    };

    const IDS = {
        button: "nova-mobile-sessions-toggle",
        panel: "nova-clean-session-panel-v1",
        list: "nova-mobile-v10-sessions-body",
        status: "nova-clean-session-status-v1",
        close: "nova-clean-session-close-v1",
        newButton: "nova-clean-session-new-v1"
    };

    function $(id) {
        return document.getElementById(id);
    }

    function activeId() {
        return new URLSearchParams(location.search).get("session_id") ||
            localStorage.getItem("nova_mobile_active_session_id") ||
            "";
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    async function jsonFetch(url, options) {
        const res = await fetch(url, Object.assign({
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        }, options || {}));

        const text = await res.text();
        let data = {};

        try {
            data = text ? JSON.parse(text) : {};
        } catch (_) {
            data = { raw: text };
        }

        if (!res.ok || data.ok === false) {
            throw new Error(data.error || data.message || ("Request failed: " + res.status));
        }

        return data;
    }

    async function postFirst(urls, body) {
        let lastError = null;

        for (const url of urls) {
            try {
                return await jsonFetch(url, {
                    method: "POST",
                    body: JSON.stringify(body || {})
                });
            } catch (err) {
                lastError = err;
            }
        }

        throw lastError || new Error("No endpoint worked");
    }

    function normalizeSessions(data) {
        const raw =
            data.sessions ||
            data.items ||
            data.data ||
            data.results ||
            [];

        if (Array.isArray(raw)) {
            return raw;
        }

        if (raw && typeof raw === "object") {
            return Object.values(raw);
        }

        return [];
    }

    function setStatus(text) {
        const el = $(IDS.status);
        if (el) {
            el.textContent = text || "";
        }
    }

    function ensurePanel() {
        let panel = $(IDS.panel);

        if (panel) {
            return panel;
        }

        panel = document.createElement("div");
        panel.id = IDS.panel;
        panel.innerHTML = `
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <div style="flex:1;font-size:18px;font-weight:900;">Sessions</div>
                <button id="${IDS.newButton}" type="button" style="border:0;border-radius:10px;padding:8px 10px;font-weight:800;">New</button>
                <button id="${IDS.close}" type="button" style="border:0;border-radius:10px;padding:8px 10px;font-weight:800;">Close</button>
            </div>
            <div id="${IDS.status}" style="font-size:12px;color:rgba(255,255,255,.7);margin-bottom:10px;"></div>
            <div id="${IDS.list}" style="display:flex;flex-direction:column;gap:10px;overflow:auto;padding-bottom:30px;"></div>
        `;

        panel.style.cssText = [
            "position:fixed",
            "top:0",
            "right:0",
            "bottom:0",
            "width:min(430px,94vw)",
            "z-index:2147483647",
            "display:none",
            "flex-direction:column",
            "padding:18px",
            "box-sizing:border-box",
            "background:rgba(10,10,18,.98)",
            "color:#fff",
            "box-shadow:-20px 0 60px rgba(0,0,0,.45)",
            "overflow:hidden"
        ].join(";");

        document.body.appendChild(panel);

        $(IDS.close).addEventListener("click", function (event) {
    event.preventDefault();
    event.currentTarget.blur();
    closePanel();
});

        $(IDS.newButton).addEventListener("click", createSession);

        panel.addEventListener("click", handlePanelClick);

        return panel;
    }

function openPanel() {
    const panel = ensurePanel();

    // kill stale accessibility state from old session controllers
    panel.removeAttribute("aria-hidden");
    panel.removeAttribute("hidden");

    // 🔥 reset accessibility state BEFORE showing
    panel.removeAttribute("aria-hidden");

    // show panel
    panel.style.setProperty("display", "flex", "important");

    // ensure no stale focus conflicts
    setTimeout(() => {
        const closeBtn = document.getElementById("nova-clean-session-close-v1");
        closeBtn?.blur?.();
    }, 0);

    loadSessions().catch(err => {
        console.error(err);
        setStatus("Failed to load sessions");
    });
}

function closePanel() {
    const panel = $(IDS.panel);
    if (!panel) return;

    const active = document.activeElement;

    if (active) {
        active.blur();
    }

    panel.setAttribute("inert", "");

    panel.style.setProperty("display", "none", "important");

    panel.removeAttribute("aria-hidden");
    panel.removeAttribute("hidden");

    setTimeout(() => {
        panel.removeAttribute("inert");
    }, 50);
}

    async function loadSessions() {
        setStatus("Loading sessions...");
        const data = await jsonFetch(API.list + "?clean_owner=" + Date.now(), { method: "GET" });
        const sessions = normalizeSessions(data);
        const current = data.active_session_id || activeId();
        const list = $(IDS.list);

        if (!list) {
            return;
        }

        list.innerHTML = "";

        if (!sessions.length) {
            list.innerHTML = `<div style="color:rgba(255,255,255,.7);">No sessions found.</div>`;
            setStatus("No sessions found.");
            return;
        }

        sessions.forEach(function (s) {
            const id = s.id || s.session_id || s.key || "";
            if (!id) {
                return;
            }

            const title = s.title || s.name || "New Chat";
            const count = s.message_count || s.messages_count || (Array.isArray(s.messages) ? s.messages.length : 0);
            const pinned = !!(s.pinned || s.is_pinned);
            const active = id === current;

            const row = document.createElement("div");
            row.dataset.sessionId = id;
            row.style.cssText = [
                "border:1px solid rgba(255,255,255,.14)",
                "border-radius:14px",
                "padding:12px",
                "background:" + (active ? "rgba(130,90,255,.28)" : "rgba(255,255,255,.06)")
            ].join(";");

            row.innerHTML = `
                <button type="button" data-nova-action="open" style="display:block;width:100%;text-align:left;background:transparent;color:#fff;border:0;padding:0;margin:0 0 8px;font-size:14px;font-weight:900;">
                    ${pinned ? "PIN " : ""}${escapeHtml(title)}
                </button>
                <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                    <span style="flex:1;min-width:100px;color:rgba(255,255,255,.65);font-size:12px;">${escapeHtml(id.slice(-8))} · ${count} msgs</span>
                    <button type="button" data-nova-action="rename" style="border:0;border-radius:9px;padding:7px 9px;font-weight:800;">Rename</button>
                    <button type="button" data-nova-action="pin" data-pinned="${pinned ? "true" : "false"}" style="border:0;border-radius:9px;padding:7px 9px;font-weight:800;">${pinned ? "Unpin" : "Pin"}</button>
                    <button type="button" data-nova-action="delete" style="border:0;border-radius:9px;padding:7px 9px;font-weight:800;">Delete</button>
                </div>
            `;

            list.appendChild(row);
        });

        setStatus(sessions.length + " sessions loaded.");
    }

    async function createSession() {
        setStatus("Creating session...");
        const data = await jsonFetch(API.create + "?clean_new=" + Date.now(), { method: "POST", body: "{}" });
        const id = data.id || data.session_id || (data.session && (data.session.id || data.session.session_id));

if (id) {
    localStorage.setItem("nova_mobile_active_session_id", id);

    window.dispatchEvent(new CustomEvent("nova:session-selected", {
        detail: { session_id: id }
    }));

    closePanel();
    return;
}

        await loadSessions();
    }

    async function handlePanelClick(event) {
        const button = event.target.closest("[data-nova-action]");
        if (!button) {
            return;
        }

        const row = button.closest("[data-session-id]");
        const id = row ? row.dataset.sessionId : "";
        const action = button.dataset.novaAction;

if (action === "open" && id) {
    localStorage.setItem("nova_mobile_active_session_id", id);

    if (
        window.NovaMobileRestoreSession &&
        typeof window.NovaMobileRestoreSession.restore === "function"
    ) {
        await window.NovaMobileRestoreSession.restore(id);
    }

    window.dispatchEvent(new CustomEvent("nova:session-selected", {
        detail: { session_id: id }
    }));

    closePanel();
    return;
}

        if (action === "rename" && id) {
            const current = row.querySelector("[data-nova-action='open']")?.textContent || "";
            const title = prompt("Rename session", current.replace(/^PIN\s*/, "").trim() || "New Chat");
            if (!title) return;

            setStatus("Renaming...");
            await postFirst(API.rename.concat([
                "/api/sessions/" + encodeURIComponent(id) + "/rename"
            ]), { id, session_id: id, title });
            await loadSessions();
            return;
        }

        if (action === "pin" && id) {
            const nextPinned = button.dataset.pinned !== "true";
            setStatus(nextPinned ? "Pinning..." : "Unpinning...");
            await postFirst(API.pin.concat([
                "/api/sessions/" + encodeURIComponent(id) + "/pin"
            ]), { id, session_id: id, pinned: nextPinned });
            await loadSessions();
            return;
        }

        if (action === "delete" && id) {
            if (!confirm("Delete this session?")) return;

            setStatus("Deleting...");
            await postFirst(API.delete.concat([
                "/api/sessions/" + encodeURIComponent(id) + "/delete"
            ]), { id, session_id: id });
            await loadSessions();
        }
    }

    function bindHeader() {
        const button = $(IDS.button);
        if (!button || button.dataset.novaCleanSessionOwner === "1") {
            return;
        }

        button.dataset.novaCleanSessionOwner = "1";
        button.removeAttribute("data-nova-hidden-by-sessions-final");
        button.style.setProperty("display", "inline-flex", "important");
        button.style.setProperty("visibility", "visible", "important");
        button.style.setProperty("opacity", "1", "important");
        button.style.setProperty("pointer-events", "auto", "important");

        button.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            if (typeof event.stopImmediatePropagation === "function") {
                event.stopImmediatePropagation();
            }
            openPanel();
        }, true);
    }

    window.NovaCleanOpenSessions = openPanel;
    window.NovaCleanReloadSessions = loadSessions;
    window.NovaCleanCloseSessions = closePanel;

    bindHeader();
    document.addEventListener("DOMContentLoaded", bindHeader);
    window.addEventListener("load", bindHeader);
    setTimeout(bindHeader, 100);
    setTimeout(bindHeader, 500);
    setTimeout(bindHeader, 1200);

    console.log("[Nova Clean Sessions Owner V1] installed");
})();
