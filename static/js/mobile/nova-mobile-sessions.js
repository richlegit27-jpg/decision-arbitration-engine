(() => {
    if (window.__NOVA_SESSION_CONTROLLER_V2__) return;
    window.__NOVA_SESSION_CONTROLLER_V2__ = true;

    const API_SESSIONS = "/api/sessions";
    const API_SESSION = (id) => `/api/sessions/${encodeURIComponent(id)}`;
    const PANEL_ID = "nova-mobile-sessions-panel";
    const CHAT_IDS = ["nova-mobile-chat", "nova-mobile-messages", "mobileChatMessages"];

    function $(id) {
        return document.getElementById(id);
    }

    function chatBox() {
        return CHAT_IDS.map($).find(Boolean);
    }

    function getText(m) {
        return m?.text || m?.content || m?.message || "";
    }

    function getRole(m) {
        const role = String(m?.role || m?.sender || "assistant").toLowerCase();
        return role.includes("user") ? "user" : "assistant";
    }

    function renderMessage(m) {
        const el = document.createElement("div");
        const role = getRole(m);

        el.className = role === "user"
            ? "nova-message nova-message-user"
            : "nova-message nova-message-assistant";

        el.dataset.role = role;
        el.textContent = getText(m);

        return el;
    }

    const Controller = {
        activeId: localStorage.getItem("nova_active_session_id") || null,
        cache: {},
        requestId: 0,

        setActive(id) {
            const clean = String(id || "").trim();
            if (!clean) return;

            this.activeId = clean;

            try {
                localStorage.setItem("nova_active_session_id", clean);
                localStorage.setItem("nova_mobile_active_session_id", clean);
            } catch (e) {}

            window.currentSessionId = clean;
            window.NOVA_SESSION_ID = clean;

            window.dispatchEvent(new CustomEvent("nova:session-changed", {
                detail: { sessionId: clean }
            }));
        },

        render(sessionId, data) {
            const box = chatBox();
            if (!box) {
                console.warn("[Nova Sessions] chat box missing");
                return;
            }

            const messages =
                Array.isArray(data?.messages)
                    ? data.messages
                    : Array.isArray(data?.session?.messages)
                        ? data.session.messages
                        : Array.isArray(data?.data?.messages)
                            ? data.data.messages
                            : [];

            box.innerHTML = "";

            for (const m of messages) {
                box.appendChild(renderMessage(m));
            }

            requestAnimationFrame(() => {
                box.scrollTop = box.scrollHeight;
            });
        },

        async list() {
            const res = await fetch(API_SESSIONS, { cache: "no-store" });
            const data = await res.json();

            return data?.items || data?.sessions || data?.data?.sessions || [];
        },

async open(sessionId) {
    const clean = String(sessionId || "").trim();
    if (!clean) return;

    const requestId = ++this.requestId;

    this.setActive(clean);

    if (this.cache[clean]) {
        this.render(clean, this.cache[clean]);
    }

    try {
        const res = await fetch(`/api/sessions/${encodeURIComponent(clean)}`, {
            cache: "no-store"
        });

        const data = await res.json();

        console.log("[Nova Sessions] open", clean, data);

        const normalized = {
messages:
    Array.isArray(data?.messages)
        ? data.messages
        : Array.isArray(data?.session?.messages)
            ? data.session.messages
            : Array.isArray(data?.data?.messages)
                ? data.data.messages
                : Array.isArray(data?.chat?.messages)
                    ? data.chat.messages
                    : Array.isArray(data?.conversation)
                        ? data.conversation
                        : Array.isArray(data?.history)
                            ? data.history
                            : [],
            ts: Date.now()
        };

        this.cache[clean] = normalized;

        if (this.activeId === clean && requestId === this.requestId) {
            this.render(clean, normalized);
        }

        window.dispatchEvent(new CustomEvent("nova:session-opened", {
            detail: { sessionId: clean }
        }));
    } catch (err) {
        console.error("[Nova Sessions] open failed", err);
        this.render(clean, { messages: [] });
    }
}

    };

    function panel() {
        let el = $(PANEL_ID);

        if (!el) {
            el = document.createElement("div");
            el.id = PANEL_ID;
            document.body.appendChild(el);
        }

        el.style.cssText = `
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
            display:block;
            pointer-events:auto;
        `;

        return el;
    }

    async function openSessionsPanel() {
        const el = panel();
        el.style.display = "block";
        el.textContent = "Loading sessions...";

        try {
            const sessions = await Controller.list();
            el.innerHTML = "";

            const close = document.createElement("button");
            close.type = "button";
            close.textContent = "Close Sessions";
            close.style.cssText = `
                display:block;
                width:100%;
                padding:12px;
                margin-bottom:10px;
                background:#333;
                color:#fff;
                border:0;
                border-radius:8px;
                cursor:pointer;
            `;
            close.onclick = () => {
                el.style.display = "none";
            };
            el.appendChild(close);

            sessions.forEach((session) => {
                if (!session || !session.id) return;

                const row = document.createElement("button");
                row.type = "button";
                row.textContent = session.title || session.id;

                row.style.cssText = `
                    display:block;
                    width:100%;
                    text-align:left;
                    padding:12px;
                    margin-bottom:8px;
                    background:#222;
                    color:#fff;
                    border:0;
                    border-radius:8px;
                    cursor:pointer;
                    pointer-events:auto;
                `;
 
row.onclick = async (event) => {
    event.preventDefault();
    event.stopPropagation();

    const id = session.id || session.session_id || session.sessionId;
    if (!id) return;

    console.log("[Nova Sessions] click", id);

    row.style.opacity = "0.6";

    localStorage.setItem("nova_active_session_id", id);
    localStorage.setItem("nova_mobile_active_session_id", id);

    const box =
        document.getElementById("mobileChatMessages") ||
        document.getElementById("nova-mobile-chat") ||
        document.getElementById("nova-mobile-messages");

    if (box) box.innerHTML = "";

    try {
        const res = await fetch(`/api/sessions/${encodeURIComponent(id)}`, {
            cache: "no-store"
        });

        const data = await res.json();

        const messages =
            data.messages ||
            data.session?.messages ||
            data.data?.messages ||
            data.chat?.messages ||
            data.conversation ||
            data.history ||
            [];

        messages.forEach((m) => {
            const role = String(m.role || m.sender || "assistant").toLowerCase();
            const text = m.text || m.content || m.message || "";

            const bubble = document.createElement("div");

            bubble.className = role.includes("user")
                ? "nova-message nova-message-user"
                : "nova-message nova-message-assistant";

            bubble.dataset.role = role.includes("user") ? "user" : "assistant";
            bubble.textContent = text;

            if (box) box.appendChild(bubble);
        });

        if (box) {
            box.scrollTop = box.scrollHeight;
        }
    } catch (error) {
        console.error("[Nova Sessions] direct session load failed", error);
    }

    el.style.display = "none";
};

                el.appendChild(row);
            });

            if (!sessions.length) {
                const empty = document.createElement("div");
                empty.textContent = "No sessions found";
                empty.style.padding = "12px";
                el.appendChild(empty);
            }
        } catch (error) {
            console.error("[Nova Sessions] list failed", error);
            el.textContent = "Failed to load sessions";
        }
    }

    function closeSessionsPanel() {
        const el = $(PANEL_ID);
        if (el) el.style.display = "none";
    }

    window.NovaSessionController = Controller;
    window.NovaMobileSessions = {
        open: openSessionsPanel,
        close: closeSessionsPanel,
        controller: Controller
    };

    window.NovaMobileOpenSessions = openSessionsPanel;
    window.switchSession = (id) => Controller.open(id);

    console.log("[Nova Sessions] loaded clean v2");
})();