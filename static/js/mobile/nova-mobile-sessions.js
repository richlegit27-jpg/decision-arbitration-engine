(() => {
    if (window.__NOVA_SESSION_CONTROLLER_V2__) return;
    window.__NOVA_SESSION_CONTROLLER_V2__ = true;

    const API_SESSIONS = "/api/sessions";
    const API_SESSION = (id) => `/api/sessions/${encodeURIComponent(id)}`;
    const PANEL_ID = "nova-mobile-sessions-panel";
const CHAT_IDS = ["mobileChatMessages", "nova-mobile-messages", "nova-mobile-chat"];

    function $(id) {
        return document.getElementById(id);
    }

function chatBox() {
    return CHAT_IDS
        .map($)
        .find((el) => el && document.body.contains(el));
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

if (!messages.length) {
    const empty = document.createElement("div");
    empty.className = "nova-mobile-empty-chat";
    empty.textContent = "Start a new conversation.";
    box.appendChild(empty);
    return;
}

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
    position:fixed !important;
    left:10px !important;
    right:10px !important;
    top:70px !important;
    bottom:90px !important;
    z-index:2147483647 !important;
    background:#111 !important;
    color:#fff !important;
    padding:12px !important;
    overflow-y:auto !important;
    border-radius:12px !important;
    pointer-events:auto !important;
    display:none !important;
    visibility:visible !important;
    opacity:1 !important;
`;

el.style.display = "none";

        return el;
    }

    async function openSessionsPanel() {
const el = panel();

el.hidden = false;
el.removeAttribute("aria-hidden");
el.style.setProperty("display", "block", "important");
el.style.setProperty("visibility", "visible", "important");
el.style.setProperty("opacity", "1", "important");
el.style.setProperty("pointer-events", "auto", "important");

el.textContent = "Loading sessions...";

        try {
            const sessions = await Controller.list();
sessions.sort((a, b) => {
    if (!!a.pinned !== !!b.pinned) {
        return a.pinned ? -1 : 1;
    }

    return String(b.updated_at || b.created_at || "")
        .localeCompare(String(a.updated_at || a.created_at || ""));
});
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
el.style.setProperty("display", "none", "important");
el.setAttribute("aria-hidden", "true");
el.innerHTML = "";
            };
            el.appendChild(close);

            sessions.forEach((session) => {
                if (!session || !session.id) return;

                const row = document.createElement("button");
                row.type = "button";
const title = session.title || session.id;

row.textContent =
    title.length > 40
        ? title.slice(0, 37) + "..."
        : title;

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

const active =
    localStorage.getItem("nova_active_session_id") === session.id;

if (active) {
    row.style.background = "#3b82f6";
    row.style.fontWeight = "600";
}

row.onclick = async (event) => {
    event.preventDefault();
    event.stopPropagation();

    const id = session.id || session.session_id || session.sessionId;
    if (!id) return;

    console.log("[Nova Sessions] click", id);

    row.style.opacity = "0.6";

    await Controller.open(id);

    row.style.opacity = "1";

    el.style.setProperty("display", "none", "important");
    el.setAttribute("aria-hidden", "true");
    el.innerHTML = "";
};

const actions = document.createElement("div");
actions.style.cssText = `
    display:flex;
    gap:6px;
    margin:0 0 10px 0;
`;

function tinyButton(label) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label;
    btn.style.cssText = `
        flex:1;
        padding:8px;
        background:#333;
        color:#fff;
        border:0;
        border-radius:8px;
        font-size:12px;
        cursor:pointer;
    `;
    return btn;
}

const pin = tinyButton(session.pinned ? "📌 Unpin" : "📌 Pin");
const rename = tinyButton("✏️ Rename");
const del = tinyButton("🗑 Delete");
del.style.background = "#7f1d1d";

pin.onclick = async (event) => {
    event.preventDefault();
    event.stopPropagation();

    await fetch("/api/sessions/pin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            session_id: session.id
        })
    });

    openSessionsPanel();
};

rename.onclick = async (event) => {
    event.preventDefault();
    event.stopPropagation();

    const title = prompt("Rename session:", session.title || "");
    if (!title) return;

    await fetch("/api/sessions/rename", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            session_id: session.id,
            title: title
        })
    });

    openSessionsPanel();
};

del.onclick = async (event) => {
    event.preventDefault();
    event.stopPropagation();

    if (!confirm("Delete this session?")) return;

    await fetch("/api/sessions/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            session_id: session.id
        })
    });

    openSessionsPanel();
};

actions.appendChild(pin);
actions.appendChild(rename);
actions.appendChild(del);

el.appendChild(row);
el.appendChild(actions);
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



function handleSessionsButtonClick(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();

        if (typeof event.stopImmediatePropagation === "function") {
            event.stopImmediatePropagation();
        }
    }

    openSessionsPanel();

    return false;
}

function wireSessionsButtons() {
    const ids = [
        "nova-mobile-sessions-toggle",
        "nova-mobile-sessions",
        "nova-mobile-sessions-btn",
        "nova-mobile-sessions-button",
        "mobile-sessions",
        "mobile-sessions-btn",
        "sessions-btn",
        "sessionsButton"
    ];

    let wired = 0;

    ids.forEach((id) => {
        const btn = document.getElementById(id);
        if (!btn) return;

        btn.onclick = handleSessionsButtonClick;

        if (btn.dataset.novaSessionsCaptureWired !== "1") {
            btn.dataset.novaSessionsCaptureWired = "1";
            btn.addEventListener("click", handleSessionsButtonClick, true);
            wired += 1;
        }
    });

    console.log("[Nova Sessions] buttons wired", wired);
}

wireSessionsButtons();

setTimeout(wireSessionsButtons, 50);
setTimeout(wireSessionsButtons, 250);
setTimeout(wireSessionsButtons, 1000);

document.addEventListener("click", (event) => {
    const target = event.target?.closest?.(
        "#nova-mobile-sessions-toggle, #nova-mobile-sessions, #nova-mobile-sessions-btn, #nova-mobile-sessions-button, #mobile-sessions, #mobile-sessions-btn, #sessions-btn, #sessionsButton, [data-nova-open-sessions]"
    );

    if (!target) return;

    handleSessionsButtonClick(event);
}, true);

    console.log("[Nova Sessions] loaded clean v2");
})();