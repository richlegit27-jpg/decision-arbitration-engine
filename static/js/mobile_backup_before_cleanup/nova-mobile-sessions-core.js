/* =========================================
   NOVA SESSIONS SYSTEM — CLEAN REWRITE v1
   SINGLE SOURCE OF TRUTH
========================================= */

(() => {
    if (window.__NOVA_SESSIONS_V1__) return;
    window.__NOVA_SESSIONS_V1__ = true;

    // -----------------------------
    // STATE (ONLY SOURCE OF TRUTH)
    // -----------------------------
    let state = {
        sessions: [],
        activeId: localStorage.getItem("nova_active_session_id") || null
    };

    function setActive(id) {
        state.activeId = id;
        localStorage.setItem("nova_active_session_id", id);
    }

    function getActive() {
        return state.activeId;
    }

    function setSessions(list) {
        state.sessions = Array.isArray(list) ? list : [];
    }

    function getSessions() {
        return state.sessions;
    }

    // -----------------------------
    // API LAYER (NO GLOBAL PATCHING)
    // -----------------------------
    async function api(url, body) {
        const res = await fetch(url, {
            method: body ? "POST" : "GET",
            headers: { "Content-Type": "application/json" },
            body: body ? JSON.stringify(body) : undefined
        });

        return res.json();
    }

    // -----------------------------
    // SESSION LOADING
    // -----------------------------
    async function loadSessions() {
        const data = await api("/api/sessions");
        setSessions(data.sessions || []);
        render();
    }

    // -----------------------------
    // OPEN SESSION
    // -----------------------------
    async function openSession(id) {
        const data = await api("/api/sessions/" + id);
        const session = data.session || data;

        setActive(session.id);

        const chat =
            document.getElementById("nova-mobile-chat") ||
            document.getElementById("chat");

        if (!chat) return;

        chat.innerHTML = "";

        (session.messages || []).forEach(m => {
            const el = document.createElement("div");
            el.className = "msg " + (m.role || "assistant");
            el.textContent = m.text || "";
            chat.appendChild(el);
        });

        chat.scrollTop = chat.scrollHeight;
    }

    // -----------------------------
    // SESSION ACTIONS (SAFE)
    // -----------------------------
    async function rename(id, title) {
        await api("/api/sessions/rename", {
            session_id: id,
            title
        });

        await loadSessions();
    }

    async function pin(id, pinned) {
        await api("/api/sessions/pin", {
            session_id: id,
            pinned
        });

        await loadSessions();
    }

    async function remove(id) {
        await api("/api/sessions/delete", {
            session_id: id
        });

        await loadSessions();
    }

    // -----------------------------
    // RENDER UI (ONLY ONE SYSTEM)
    // -----------------------------
    function render() {
        const panel = document.getElementById("nova-mobile-sessions-panel");
        if (!panel) return;

        panel.innerHTML = "";

        const sessions = getSessions();

        sessions.forEach(s => {
            const row = document.createElement("div");
            row.className = "nova-session-row";

            const open = document.createElement("button");
            open.textContent = (s.pinned ? "📌 " : "") + (s.title || s.id);
            open.onclick = () => openSession(s.id);

            const manage = document.createElement("button");
            manage.textContent = "⋯";

            manage.onclick = async () => {
                const action = prompt("rename / pin / delete");
                if (!action) return;

                if (action === "rename") {
                    const t = prompt("New name?");
                    if (t) await rename(s.id, t);
                }

                if (action === "pin") {
                    await pin(s.id, !s.pinned);
                }

                if (action === "delete") {
                    await remove(s.id);
                }
            };

            row.appendChild(open);
            row.appendChild(manage);
            panel.appendChild(row);
        });
    }

    // -----------------------------
    // BOOT
    // -----------------------------
    document.addEventListener("DOMContentLoaded", loadSessions);

    // -----------------------------
    // EXPORT
    // -----------------------------
    window.NovaSessions = {
        loadSessions,
        openSession,
        rename,
        pin,
        remove,
        render,
        state: {
            getActive,
            getSessions
        }
    };

    console.log("[NOVA_SESSIONS_V1] clean rewrite loaded");
})();