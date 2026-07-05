(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSIONS_FINAL_OWNER_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_SESSIONS_FINAL_OWNER_V1_20260703__ = true;

    const API = {
        list: "/api/sessions",
        detail: (id) => "/api/sessions/" + encodeURIComponent(id),
        newSession: "/api/sessions/new",
        rename: "/api/sessions/rename",
        pin: "/api/sessions/pin",
        delete: "/api/sessions/delete"
    };

    const IDS = {
        button: "nova-mobile-sessions-final-button-v1",
        panel: "nova-mobile-sessions-final-panel-v1",
        list: "nova-mobile-sessions-final-list-v1",
        status: "nova-mobile-sessions-final-status-v1",
        title: "nova-mobile-sessions-final-title-v1"
    };

    function $(id) {
        return document.getElementById(id);
    }

    function jsonFetch(url, options) {
        return fetch(url, Object.assign({
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        }, options || {})).then(async function (response) {
            const text = await response.text();
            let data = {};
            try {
                data = text ? JSON.parse(text) : {};
            } catch (error) {
                data = { ok: false, error: text || String(error) };
            }

            if (!response.ok || data.ok === false) {
                throw new Error(data.error || ("HTTP " + response.status));
            }

            return data;
        });
    }

    function getSessions(payload) {
        if (!payload) {
            return [];
        }

        if (Array.isArray(payload.sessions)) {
            return payload.sessions;
        }

        if (Array.isArray(payload.items)) {
            return payload.items;
        }

        if (Array.isArray(payload)) {
            return payload;
        }

        return [];
    }

    function setStatus(message) {
        const el = $(IDS.status);
        if (el) {
            el.textContent = message || "";
        }
    }

    function activeIdFromStorage() {
        return (
            localStorage.getItem("nova_mobile_active_session_id") ||
            localStorage.getItem("nova_active_session_id") ||
            ""
        );
    }

    function setActiveId(id) {
        if (!id) {
            return;
        }

        localStorage.setItem("nova_mobile_active_session_id", id);
        localStorage.setItem("nova_active_session_id", id);
        window.NOVA_ACTIVE_SESSION_ID = id;
        window.novaActiveSessionId = id;
    }

    function removeOldSessionUi() {
        const knownBad = [
            "nova-session-fallback-button-v1",
            "nova-session-fallback-panel-v1",
            "nova-mobile-session-drawer-v2-button",
            "nova-mobile-session-drawer-v2-panel",
            "nova-mobile-sessions-v10-button",
            "nova-mobile-sessions-v10-panel",
            "nova-mobile-session-v10-button",
            "nova-mobile-session-v10-panel"
        ];

        knownBad.forEach(function (id) {
            const el = document.getElementById(id);
            if (el) {
                el.remove();
            }
        });

        document.querySelectorAll("button").forEach(function (button) {
            if (button.id === IDS.button) {
                return;
            }

            if (button.closest("#" + IDS.panel)) {
                return;
            }

            const text = [
                button.id || "",
                button.textContent || "",
                button.getAttribute("aria-label") || "",
                button.getAttribute("title") || ""
            ].join(" ");

${indent}if (button.id === "nova-mobile-sessions-toggle") {
${indent}    button.removeAttribute("data-nova-hidden-by-sessions-final");
${indent}    button.style.removeProperty("display");
${indent}    button.style.setProperty("display", "inline-flex", "important");
${indent}    button.style.setProperty("pointer-events", "auto", "important");
${indent}    return;
${indent}}

${indent}if (/session/i.test(text)) {
${indent}    button.style.display = "none";
${indent}    button.dataset.novaHiddenBySessionsFinal = "1";
${indent}}
        });
    }

    function ensureButton() {
        removeOldSessionUi();

        let button = $(IDS.button);
        if (button) {
            return button;
        }

        button = document.createElement("button");
        button.id = IDS.button;
        button.type = "button";
        button.textContent = "Sessions";
        button.setAttribute("aria-label", "Open sessions");
        button.style.cssText = [
            "position:fixed",
            "top:10px",
            "right:10px",
            "z-index:2147483647",
            "height:38px",
            "padding:0 12px",
            "border-radius:999px",
            "border:1px solid rgba(255,255,255,.18)",
            "background:rgba(18,18,24,.96)",
            "color:#fff",
            "font-size:13px",
            "font-weight:700",
            "box-shadow:0 8px 24px rgba(0,0,0,.35)"
        ].join(";");

        button.addEventListener("click", function () {
            openPanel();
        });

        document.body.appendChild(button);
        return button;
    }

    function ensurePanel() {
        let panel = $(IDS.panel);
        if (panel) {
            return panel;
        }

        panel = document.createElement("div");
        panel.id = IDS.panel;
        panel.style.cssText = [
            "position:fixed",
            "top:56px",
            "right:10px",
            "left:10px",
            "bottom:84px",
            "z-index:2147483647",
            "display:none",
            "flex-direction:column",
            "background:rgba(14,14,20,.98)",
            "color:#fff",
            "border:1px solid rgba(255,255,255,.14)",
            "border-radius:18px",
            "box-shadow:0 16px 60px rgba(0,0,0,.55)",
            "overflow:hidden",
            "font-family:system-ui,-apple-system,Segoe UI,sans-serif"
        ].join(";");

        panel.innerHTML = `
            <div style="display:flex;align-items:center;gap:8px;padding:12px;border-bottom:1px solid rgba(255,255,255,.1);">
                <strong id="${IDS.title}" style="font-size:15px;flex:1;">Sessions</strong>
                <button type="button" data-nova-action="new" style="height:34px;border-radius:10px;border:0;padding:0 10px;font-weight:800;">New</button>
                <button type="button" data-nova-action="close" style="height:34px;border-radius:10px;border:0;padding:0 10px;font-weight:800;">Close</button>
            </div>
            <div id="${IDS.status}" style="min-height:20px;padding:8px 12px;color:rgba(255,255,255,.72);font-size:12px;"></div>
            <div id="${IDS.list}" style="overflow:auto;-webkit-overflow-scrolling:touch;padding:8px 10px 14px;"></div>
        `;

        panel.addEventListener("click", async function (event) {
            const target = event.target.closest("[data-nova-action]");
            if (!target) {
                return;
            }

            const action = target.getAttribute("data-nova-action");
            const row = target.closest("[data-session-id]");
            const id = row ? row.getAttribute("data-session-id") : "";

            try {
                if (action === "close") {
                    closePanel();
                    return;
                }

                if (action === "new") {
                    await createNewSession();
                    return;
                }

                if (action === "open" && id) {
                    await openSession(id);
                    return;
                }

                if (action === "rename" && id) {
                    await renameSession(id, row);
                    return;
                }

                if (action === "pin" && id) {
                    const pinned = target.getAttribute("data-pinned") !== "true";
                    await pinSession(id, pinned);
                    return;
                }

                if (action === "delete" && id) {
                    await deleteSession(id, row);
                    return;
                }
            } catch (error) {
                setStatus("Error: " + (error && error.message ? error.message : String(error)));
            }
        });

        document.body.appendChild(panel);
        return panel;
    }

    function sessionRow(session, activeId) {
        const id = String(session.id || session.session_id || "");
        const title = String(session.title || "New Chat");
        const pinned = !!session.pinned;
        const count = session.message_count ?? (
            Array.isArray(session.messages) ? session.messages.length : 0
        );

        const active = id && id === activeId;

        return `
            <div data-session-id="${escapeHtml(id)}"
                 style="border:1px solid ${active ? "rgba(255,255,255,.45)" : "rgba(255,255,255,.1)"};
                        border-radius:14px;
                        padding:10px;
                        margin:0 0 8px;
                        background:${active ? "rgba(255,255,255,.12)" : "rgba(255,255,255,.05)"};">
                <button type="button" data-nova-action="open"
                        style="display:block;width:100%;text-align:left;background:transparent;color:#fff;border:0;padding:0;margin:0 0 8px;font-size:14px;font-weight:800;">
                    ${pinned ? "📌 " : ""}${escapeHtml(title)}
                </button>
                <div style="display:flex;align-items:center;gap:6px;">
                    <span style="flex:1;color:rgba(255,255,255,.62);font-size:12px;">${escapeHtml(id.slice(-8))} · ${count} msgs</span>
                    <button type="button" data-nova-action="rename" style="border:0;border-radius:9px;padding:7px 9px;font-weight:700;">Rename</button>
                    <button type="button" data-nova-action="pin" data-pinned="${pinned ? "true" : "false"}" style="border:0;border-radius:9px;padding:7px 9px;font-weight:700;">${pinned ? "Unpin" : "Pin"}</button>
                    <button type="button" data-nova-action="delete" style="border:0;border-radius:9px;padding:7px 9px;font-weight:700;">Delete</button>
                </div>
            </div>
        `;
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    async function loadSessions() {
        setStatus("Loading sessions…");
        const data = await jsonFetch(API.list + "?ui_final=" + Date.now(), { method: "GET" });
        const sessions = getSessions(data);
        const activeId = data.active_session_id || activeIdFromStorage();

        if (activeId) {
            setActiveId(activeId);
        }

        const list = $(IDS.list);
        if (!list) {
            return;
        }

        if (!sessions.length) {
            list.innerHTML = `<div style="padding:18px;color:rgba(255,255,255,.7);">No sessions found.</div>`;
        } else {
            list.innerHTML = sessions.map(function (session) {
                return sessionRow(session, activeId);
            }).join("");
        }

        setStatus(`${sessions.length} sessions`);
    }

    async function createNewSession() {
        setStatus("Creating session…");

        const data = await jsonFetch(API.newSession + "?ui_final_new=" + Date.now(), {
            method: "POST",
            body: JSON.stringify({ title: "New Chat" })
        });

        const session = data.session || {};
        const id = session.id || data.session_id || data.active_session_id;

        if (id) {
            setActiveId(id);
        }

        await loadSessions();
        setStatus("New session created");
    }

    async function openSession(id) {
        setStatus("Opening session…");
        const data = await jsonFetch(API.detail(id) + "?ui_final_detail=" + Date.now(), { method: "GET" });

        setActiveId(id);

        if (Array.isArray(data.session && data.session.messages)) {
            window.dispatchEvent(new CustomEvent("nova:session-selected", {
                detail: {
                    session_id: id,
                    session: data.session
                }
            }));
        }

        setStatus("Opened " + id.slice(-8));

        const url = new URL(window.location.href);
        url.searchParams.set("session_id", id);
        history.replaceState({}, "", url.toString());

        setTimeout(function () {
            window.location.href = url.toString();
        }, 120);
    }

    async function renameSession(id, row) {
        const current = row ? (row.querySelector("[data-nova-action='open']")?.textContent || "") : "";
        const title = prompt("Rename session", current.replace(/^📌\s*/, "").trim() || "New Chat");

        if (!title) {
            return;
        }

        setStatus("Renaming…");

        await jsonFetch(API.rename, {
            method: "POST",
            body: JSON.stringify({
                session_id: id,
                title: title
            })
        });

        await loadSessions();
        setStatus("Renamed");
    }

    async function pinSession(id, pinned) {
        setStatus(pinned ? "Pinning…" : "Unpinning…");

        await jsonFetch(API.pin, {
            method: "POST",
            body: JSON.stringify({
                session_id: id,
                pinned: !!pinned
            })
        });

        await loadSessions();
        setStatus(pinned ? "Pinned" : "Unpinned");
    }

    async function deleteSession(id, row) {
        const title = row ? (row.querySelector("[data-nova-action='open']")?.textContent || "").trim() : id;

        if (!confirm("Delete this session?\n\n" + title)) {
            return;
        }

        setStatus("Deleting…");

        await jsonFetch(API.delete, {
            method: "POST",
            body: JSON.stringify({
                session_id: id
            })
        });

        if (activeIdFromStorage() === id) {
            localStorage.removeItem("nova_mobile_active_session_id");
            localStorage.removeItem("nova_active_session_id");
        }

        await loadSessions();
        setStatus("Deleted");
    }

    function openPanel() {
        const panel = ensurePanel();
        panel.style.display = "flex";
        loadSessions().catch(function (error) {
            setStatus("Error: " + (error && error.message ? error.message : String(error)));
        });
    }

    function closePanel() {
        const panel = $(IDS.panel);
        if (panel) {
            panel.style.display = "none";
        }
    }

    // NOVA_MOBILE_SESSIONS_FINAL_GLOBAL_LOCK_20260703
    // NOVA_MOBILE_SESSIONS_FINAL_GLOBAL_HARD_LOCK_20260703
    function lockFinalGlobal(name, value) {
        try {
            Object.defineProperty(window, name, {
                value: value,
                writable: false,
                configurable: false,
                enumerable: true
            });
        } catch (error) {
            try {
                window[name] = value;
            } catch (_) {}
        }
    }

    function installFinalSessionGlobals() {
        lockFinalGlobal("NovaMobileOpenSessions", openPanel);
        lockFinalGlobal("NovaMobileCloseSessions", closePanel);
        lockFinalGlobal("NovaMobileReloadSessions", loadSessions);
    }

    installFinalSessionGlobals();

    function boot() {
        removeOldSessionUi();
        ensureButton();
        ensurePanel();
        console.log("[NOVA_MOBILE_SESSIONS_FINAL_OWNER_V1_20260703] ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    setTimeout(boot, 500);
    setTimeout(boot, 1500);
    setTimeout(boot, 3000);
    setTimeout(boot, 6000);

    let finalLockCount = 0;
    const finalLockTimer = setInterval(function () {
        finalLockCount += 1;
        installFinalSessionGlobals();
        removeOldSessionUi();
        ensureButton();

        if (finalLockCount >= 20) {
            clearInterval(finalLockTimer);
        }
    }, 750);
})();

