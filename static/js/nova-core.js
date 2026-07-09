(() => {
    if (window.__NOVA_SESSIONS_FINAL__) return;
    window.__NOVA_SESSIONS_FINAL__ = true;

    const PANEL_ID = "nova-mobile-sessions-panel";

    // -----------------------------
    // STATE (SINGLE SOURCE)
    // -----------------------------
    const State = {
        activeId: localStorage.getItem("nova_active_session_id") || null,

        set(id) {
            if (!id) return;
            this.activeId = id;
            localStorage.setItem("nova_active_session_id", id);
            localStorage.setItem("nova_mobile_active_session_id", id);
        },

        get() {
            return this.activeId;
        }
    };

    // -----------------------------
    // PANEL
    // -----------------------------
    function getPanel() {
        let panel = document.getElementById(PANEL_ID);

        if (!panel) {
            panel = document.createElement("div");
            panel.id = PANEL_ID;
            document.body.appendChild(panel);
        }

        panel.style.cssText = `
            position:fixed;
            top:60px;
            left:10px;
            right:10px;
            bottom:80px;
            z-index:2147483647;
            background:#111;
            color:#fff;
            padding:12px;
            overflow-y:auto;
            border-radius:12px;
        `;

        return panel;
    }

    // -----------------------------
    // LOAD SESSIONS
    // -----------------------------
    async function load(panel) {
        panel.innerHTML = "Loading...";

        try {
            const res = await fetch("/api/sessions");
            const data = await res.json();

            const sessions = Array.isArray(data.sessions) ? data.sessions : [];

            panel.innerHTML = "";

            const close = document.createElement("button");
            close.textContent = "Close";
            close.onclick = () => (panel.style.display = "none");
            panel.appendChild(close);

            sessions.forEach(s => {
                if (!s?.id) return;

                const row = document.createElement("div");
                row.textContent = s.title || s.id;
                row.style.cssText = `
                    padding:10px;
                    margin:6px 0;
                    background:#222;
                    border-radius:8px;
                    cursor:pointer;
                `;

                row.onclick = () => {
                    State.set(s.id);
                    window.location.href = "/mobile?session_id=" + encodeURIComponent(s.id);
                };

                panel.appendChild(row);
            });

        } catch (e) {
            panel.innerHTML = "Failed to load sessions";
        }
    }

    // -----------------------------
    // OPEN
    // -----------------------------
    function open() {
        const panel = getPanel();
        panel.style.display = "block";
        load(panel);
    }

    function close() {
        const panel = document.getElementById(PANEL_ID);
        if (panel) panel.style.display = "none";
    }

    // -----------------------------
    // PUBLIC API (NO OVERWRITES, NO DUPES)
    // -----------------------------
    window.NovaMobileSessions = {
        open,
        close,
        state: State
    };

    window.NovaMobileOpenSessions = open;

    console.log("[SESSIONS SMFF FINAL] loaded");
})();