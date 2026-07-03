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

// NOVA_MOBILE_SESSION_MESSAGE_RESTORE_20260630
// Safe session restore layer.
// Fetches /api/sessions/<id> and repaints saved messages when a session is opened.
(() => {
    "use strict";

    console.warn("[NOVA_MOBILE_SESSION_MESSAGE_RESTORE_20260630] disabled - owned by main Controller.open render");
    return;


    
    console.warn("[NOVA_MOBILE_SESSION_MESSAGE_RESTORE_20260630] disabled for freeze recovery");
    return;
if (window.__NOVA_MOBILE_SESSION_MESSAGE_RESTORE_20260630__) return;
    window.__NOVA_MOBILE_SESSION_MESSAGE_RESTORE_20260630__ = true;

    function getChatContainer() {
        return (
            document.querySelector("#mobile-chat-messages") ||
            document.querySelector("#nova-mobile-chat-messages") ||
            document.querySelector("#chat-messages") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector(".chat-messages") ||
            document.querySelector("main")
        );
    }

    function normalizeText(value) {
        return String(value || "")
            .replace(/^Generated image for:\s*of\s+/i, "Generated image: ")
            .replace(/^Generated image for:\s*/i, "Generated image: ")
            .replace(/^Generated image:\s*of\s+/i, "Generated image: ")
            .trim();
    }

    function normalizeUrl(url) {
        const value = String(url || "").trim();

        if (!value) return "";
        if (value.startsWith("http://") || value.startsWith("https://")) return value;
        if (value.startsWith("/")) return value;

        return "/" + value.replace(/^\/+/, "");
    }

    function getMessageImageUrl(message) {
        if (!message || typeof message !== "object") return "";

        const direct = normalizeUrl(message.image_url || message.file_url || message.url || "");
        if (direct) return direct;

        const attachments = Array.isArray(message.attachments) ? message.attachments : [];

        for (const item of attachments) {
            if (!item || typeof item !== "object") continue;

            const mime = String(item.mime_type || item.type || "").toLowerCase();
            const url = normalizeUrl(item.image_url || item.file_url || item.url || "");

            if (url && (mime.startsWith("image/") || /\.(png|jpe?g|gif|webp)$/i.test(url))) {
                return url;
            }
        }

        return "";
    }

    function makeMessageKey(message, index) {
        const role = String(message.role || "assistant");
        const text = normalizeText(message.text || message.content || message.message || "");
        const image = getMessageImageUrl(message);

        return `${index}:${role}:${text.slice(0, 80)}:${image}`;
    }

    function renderOneMessage(message, index) {
        const role = String(message.role || "assistant").toLowerCase();
        const text = normalizeText(message.text || message.content || message.message || "");
        const imageUrl = getMessageImageUrl(message);

        const wrapper = document.createElement("div");
        wrapper.className = `mobile-chat-message ${role}`;
        wrapper.dataset.novaRestoredMessage = "1";
        wrapper.dataset.novaMessageKey = makeMessageKey(message, index);

        if (text) {
            const body = document.createElement("div");
            body.className = "mobile-chat-message-text";
            body.textContent = text;
            wrapper.appendChild(body);
        }

        if (imageUrl) {
            const card = document.createElement("div");
            card.className = "nova-mobile-session-restored-image-card";

            const img = document.createElement("img");
            img.className = "nova-mobile-session-restored-image";
            img.src = imageUrl;
            img.alt = text || "Generated image";
            img.loading = "lazy";

            img.addEventListener("click", () => {
                window.open(imageUrl, "_blank", "noopener,noreferrer");
            });

            card.appendChild(img);
            wrapper.appendChild(card);
        }

        return wrapper;
    }

    function getMessagesFromPayload(payload) {
        const data = payload && typeof payload === "object" ? payload : {};
        const session = data.session && typeof data.session === "object" ? data.session : data;

        if (Array.isArray(session.messages)) return session.messages;
        if (Array.isArray(data.messages)) return data.messages;

        return [];
    }

    function setActiveSessionId(sessionId) {
        const value = String(sessionId || "").trim();
        if (!value) return;

        localStorage.setItem("nova_mobile_active_session_id", value);
        localStorage.setItem("nova_active_session_id", value);

        window.NovaMobileActiveSessionId = value;
        window.__novaMobileActiveSessionId = value;
    }

    function getActiveSessionId() {
        return (
            String(window.NovaMobileActiveSessionId || "").trim() ||
            String(window.__novaMobileActiveSessionId || "").trim() ||
            String(localStorage.getItem("nova_mobile_active_session_id") || "").trim() ||
            String(localStorage.getItem("nova_active_session_id") || "").trim()
        );
    }

    function updateSessionTitle(session) {
        if (!session || typeof session !== "object") return;

        const title = String(session.title || session.name || session.id || "").trim();
        if (!title) return;

        const targets = [
            document.querySelector("#nova-mobile-session-title"),
            document.querySelector("#mobile-session-title"),
            document.querySelector(".nova-mobile-session-title"),
            document.querySelector(".mobile-session-title")
        ].filter(Boolean);

        for (const target of targets) {
            target.textContent = title;
        }
    }

    function restoreMessagesFromPayload(payload) {
        const data = payload && typeof payload === "object" ? payload : {};
        const session = data.session && typeof data.session === "object" ? data.session : data;
        const messages = getMessagesFromPayload(payload);

        const container = getChatContainer();

        if (!container || !messages.length) {
            return false;
        }

        const existingKeys = new Set(
            Array.from(container.querySelectorAll("[data-nova-message-key]"))
                .map((node) => String(node.dataset.novaMessageKey || ""))
                .filter(Boolean)
        );

        const shouldFullRepaint = messages.length > 1;

        if (shouldFullRepaint) {
            container.innerHTML = "";
            existingKeys.clear();
        }

        messages.forEach((message, index) => {
            if (!message || typeof message !== "object") return;

            const key = makeMessageKey(message, index);

            if (existingKeys.has(key)) return;

            const node = renderOneMessage(message, index);
            container.appendChild(node);
            existingKeys.add(key);
        });

        updateSessionTitle(session);

        try {
            container.scrollTop = container.scrollHeight;
        } catch (_) {}

        return true;
    }

    async function restoreSession(sessionId) {
        const id = String(sessionId || getActiveSessionId() || "").trim();

        if (!id) return false;

        setActiveSessionId(id);

        try {
            const response = await fetch(`/api/sessions/${encodeURIComponent(id)}`, {
                credentials: "same-origin",
                cache: "no-store"
            });

            const payload = await response.json();

            return restoreMessagesFromPayload(payload);
        } catch (error) {
            console.warn("[NOVA_MOBILE_SESSION_MESSAGE_RESTORE_20260630] restore failed", error);
            return false;
        }
    }

    function sessionIdFromElement(node) {
        let current = node;

        while (current && current !== document.documentElement) {
            const id =
                current.dataset?.sessionId ||
                current.dataset?.id ||
                current.getAttribute?.("data-session-id") ||
                current.getAttribute?.("data-id") ||
                "";

            if (id) return String(id).trim();

            current = current.parentElement;
        }

        return "";
    }

    function installSessionClickCapture() {
        document.addEventListener("click", (event) => {
            const sessionId = sessionIdFromElement(event.target);

            if (!sessionId) return;

            setTimeout(() => restoreSession(sessionId), 120);
            setTimeout(() => restoreSession(sessionId), 500);
            setTimeout(() => restoreSession(sessionId), 1200);
        }, true);
    }

    function installFetchCapture() {
        if (window.__NOVA_MOBILE_SESSION_MESSAGE_RESTORE_FETCH_20260630__) return;
        window.__NOVA_MOBILE_SESSION_MESSAGE_RESTORE_FETCH_20260630__ = true;

        const previousFetch = window.fetch;

        window.fetch = async function novaMobileSessionMessageRestoreFetch(input, init) {
            const response = await previousFetch.apply(this, arguments);

            try {
                const url = typeof input === "string" ? input : String(input && input.url || "");

                if (
                    url.includes("/api/sessions/") ||
                    url.includes("/api/state")
                ) {
                    response.clone().json().then((payload) => {
                        setTimeout(() => restoreMessagesFromPayload(payload), 80);
                        setTimeout(() => restoreMessagesFromPayload(payload), 300);
                    }).catch(() => {});
                }
            } catch (error) {
                console.warn("[NOVA_MOBILE_SESSION_MESSAGE_RESTORE_20260630] fetch capture skipped", error);
            }

            return response;
        };
    }

    installSessionClickCapture();
    installFetchCapture();

    setTimeout(() => restoreSession(), 400);
    setTimeout(() => restoreSession(), 1400);

    window.NovaMobileRestoreSessionMessages = restoreSession;

    console.log("[NOVA_MOBILE_SESSION_MESSAGE_RESTORE_20260630] ready");
})();

// NOVA_MOBILE_ACTIVE_SESSION_SEND_BRIDGE_20260630
// Keeps active session id locked across session clicks, state fetches, and /api/chat sends.
(() => {
    "use strict";

    
    console.warn("[NOVA_MOBILE_ACTIVE_SESSION_SEND_BRIDGE_20260630] disabled for freeze recovery");
    return;
if (window.__NOVA_MOBILE_ACTIVE_SESSION_SEND_BRIDGE_20260630__) return;
    window.__NOVA_MOBILE_ACTIVE_SESSION_SEND_BRIDGE_20260630__ = true;

    function cleanId(value) {
        return String(value || "").trim();
    }

    function getStoredSessionId() {
        return (
            cleanId(window.NovaMobileActiveSessionId) ||
            cleanId(window.__novaMobileActiveSessionId) ||
            cleanId(localStorage.getItem("nova_mobile_active_session_id")) ||
            cleanId(localStorage.getItem("nova_active_session_id")) ||
            cleanId(sessionStorage.getItem("nova_mobile_active_session_id")) ||
            ""
        );
    }

    function setStoredSessionId(sessionId) {
        const id = cleanId(sessionId);
        if (!id) return "";

        window.NovaMobileActiveSessionId = id;
        window.__novaMobileActiveSessionId = id;

        localStorage.setItem("nova_mobile_active_session_id", id);
        localStorage.setItem("nova_active_session_id", id);
        sessionStorage.setItem("nova_mobile_active_session_id", id);

        return id;
    }

    function sessionIdFromPayload(payload) {
        const data = payload && typeof payload === "object" ? payload : {};

        return cleanId(
            data.active_session_id ||
            data.session_id ||
            data.id ||
            data.session?.id ||
            data.session?.active_session_id ||
            data.meta?.session_id ||
            ""
        );
    }

    function sessionIdFromElement(node) {
        let current = node;

        while (current && current !== document.documentElement) {
            const id =
                current.dataset?.sessionId ||
                current.dataset?.id ||
                current.getAttribute?.("data-session-id") ||
                current.getAttribute?.("data-id") ||
                "";

            if (id) return cleanId(id);

            current = current.parentElement;
        }

        return "";
    }

    function updateVisibleSessionLabel(sessionId) {
        const id = cleanId(sessionId);
        if (!id) return;

        const shortId = id.length > 8 ? id.slice(-8) : id;

        const targets = [
            document.querySelector("#nova-mobile-session-id"),
            document.querySelector("#mobile-session-id"),
            document.querySelector(".nova-mobile-active-session-id"),
            document.querySelector(".mobile-active-session-id")
        ].filter(Boolean);

        for (const target of targets) {
            target.textContent = shortId;
        }
    }

    document.addEventListener("click", (event) => {
        const id = sessionIdFromElement(event.target);

        if (!id) return;

        setStoredSessionId(id);
        updateVisibleSessionLabel(id);

        console.log("[NOVA_MOBILE_ACTIVE_SESSION_SEND_BRIDGE_20260630] selected", id);
    }, true);

    function patchChatBody(input, init) {
        const url = typeof input === "string" ? input : String(input && input.url || "");

        if (!url.includes("/api/chat")) {
            return init;
        }

        const nextInit = init && typeof init === "object" ? { ...init } : {};
        const method = String(nextInit.method || "GET").toUpperCase();

        if (method !== "POST") {
            return init;
        }

        const activeSessionId = getStoredSessionId();
        if (!activeSessionId) {
            return init;
        }

        try {
            let body = nextInit.body;

            if (typeof body === "string" && body.trim().startsWith("{")) {
                const data = JSON.parse(body);

                data.session_id = activeSessionId;
                data.active_session_id = activeSessionId;

                nextInit.body = JSON.stringify(data);

                console.log("[NOVA_MOBILE_ACTIVE_SESSION_SEND_BRIDGE_20260630] forced /api/chat session", activeSessionId);
                return nextInit;
            }

            if (!body || typeof body !== "string") {
                const data = {
                    session_id: activeSessionId,
                    active_session_id: activeSessionId
                };

                nextInit.body = JSON.stringify(data);
                nextInit.headers = {
                    ...(nextInit.headers || {}),
                    "Content-Type": "application/json"
                };

                return nextInit;
            }
        } catch (error) {
            console.warn("[NOVA_MOBILE_ACTIVE_SESSION_SEND_BRIDGE_20260630] body patch skipped", error);
        }

        return init;
    }

    if (!window.__NOVA_MOBILE_ACTIVE_SESSION_SEND_FETCH_PATCHED_20260630__) {
        window.__NOVA_MOBILE_ACTIVE_SESSION_SEND_FETCH_PATCHED_20260630__ = true;

        const previousFetch = window.fetch;

        window.fetch = async function novaMobileActiveSessionSendFetch(input, init) {
            const patchedInit = patchChatBody(input, init);
            const response = await previousFetch.call(this, input, patchedInit);

            try {
                const url = typeof input === "string" ? input : String(input && input.url || "");

                if (
                    url.includes("/api/chat") ||
                    url.includes("/api/state") ||
                    url.includes("/api/sessions")
                ) {
                    response.clone().json().then((payload) => {
                        const id = sessionIdFromPayload(payload);

                        if (id) {
                            setStoredSessionId(id);
                            updateVisibleSessionLabel(id);
                        }
                    }).catch(() => {});
                }
            } catch (_) {}

            return response;
        };
    }

    const bootId = getStoredSessionId();
    if (bootId) {
        setStoredSessionId(bootId);
        updateVisibleSessionLabel(bootId);
    }

    window.NovaMobileGetActiveSessionId = getStoredSessionId;
    window.NovaMobileSetActiveSessionId = setStoredSessionId;

    console.log("[NOVA_MOBILE_ACTIVE_SESSION_SEND_BRIDGE_20260630] ready");
})();

// NOVA_MOBILE_SESSION_TITLE_REFRESH_20260630
// Keeps the mobile session title/sidebar fresh after switching, sending, rename, new chat, and state reload.
(() => {
    "use strict";

    
    console.warn("[NOVA_MOBILE_SESSION_TITLE_REFRESH_20260630] disabled for freeze recovery");
    return;
if (window.__NOVA_MOBILE_SESSION_TITLE_REFRESH_20260630__) return;
    window.__NOVA_MOBILE_SESSION_TITLE_REFRESH_20260630__ = true;

    function clean(value) {
        return String(value || "").trim();
    }

    function cleanTitle(value, fallbackId) {
        let title = clean(value);

        title = title
            .replace(/^Web Fetch$/i, "")
            .replace(/^New Chat$/i, "")
            .replace(/^Generated Image$/i, "Generated image")
            .trim();

        if (!title && fallbackId) {
            title = "Session " + String(fallbackId).slice(-6);
        }

        return title || "Current session";
    }

    function getSessionFromPayload(payload) {
        const data = payload && typeof payload === "object" ? payload : {};

        if (data.session && typeof data.session === "object") {
            return data.session;
        }

        if (data.id || data.title || data.messages) {
            return data;
        }

        return null;
    }

    function getSessionId(session, payload) {
        const data = payload && typeof payload === "object" ? payload : {};
        const s = session && typeof session === "object" ? session : {};

        return clean(
            s.id ||
            s.session_id ||
            s.active_session_id ||
            data.session_id ||
            data.active_session_id ||
            data.id ||
            localStorage.getItem("nova_mobile_active_session_id") ||
            localStorage.getItem("nova_active_session_id") ||
            ""
        );
    }

    function setActiveId(id) {
        const value = clean(id);
        if (!value) return;

        window.NovaMobileActiveSessionId = value;
        window.__novaMobileActiveSessionId = value;

        localStorage.setItem("nova_mobile_active_session_id", value);
        localStorage.setItem("nova_active_session_id", value);
        sessionStorage.setItem("nova_mobile_active_session_id", value);
    }

    function findOrCreateTitleNode() {
        const existing =
            document.querySelector("#nova-mobile-session-title") ||
            document.querySelector("#mobile-session-title") ||
            document.querySelector(".nova-mobile-session-title") ||
            document.querySelector(".mobile-session-title");

        if (existing) return existing;

        const header =
            document.querySelector(".nova-mobile-header") ||
            document.querySelector(".mobile-header") ||
            document.querySelector("header") ||
            document.body;

        const node = document.createElement("div");
        node.id = "nova-mobile-session-title";
        node.className = "nova-mobile-session-title";
        node.textContent = "Current session";

        if (header.firstChild) {
            header.insertBefore(node, header.firstChild.nextSibling);
        } else {
            header.appendChild(node);
        }

        return node;
    }

    function updateTitleFromSession(session, payload) {
        const s = session && typeof session === "object" ? session : getSessionFromPayload(payload);
        if (!s) return false;

        const id = getSessionId(s, payload);
        if (id) setActiveId(id);

        const title = cleanTitle(s.title || s.name || "", id);
        const node = findOrCreateTitleNode();

        node.textContent = id ? `${title} · ${id.slice(-6)}` : title;
        node.dataset.sessionId = id || "";

        document.title = `Nova - ${title}`;

        return true;
    }

    function updateSessionRowsFromList(payload) {
        const data = payload && typeof payload === "object" ? payload : {};
        const sessions = Array.isArray(data.sessions)
            ? data.sessions
            : Array.isArray(data)
                ? data
                : [];

        if (!sessions.length) return;

        for (const session of sessions) {
            if (!session || typeof session !== "object") continue;

            const id = clean(session.id || session.session_id || "");
            if (!id) continue;

            const title = cleanTitle(session.title || session.name || "", id);

            const row = document.querySelector(
                `[data-session-id="${CSS.escape(id)}"], [data-id="${CSS.escape(id)}"]`
            );

            if (!row) continue;

            row.dataset.sessionTitle = title;

            const titleNode =
                row.querySelector(".session-title") ||
                row.querySelector(".nova-session-title") ||
                row.querySelector(".mobile-session-row-title") ||
                row.querySelector("span") ||
                row;

            if (titleNode && titleNode.textContent !== title) {
                titleNode.textContent = title;
            }
        }
    }

    function refreshSessionsListSoon() {
        const candidates = [
            window.NovaMobileLoadSessions,
            window.NovaMobileRefreshSessions,
            window.NovaMobileRenderSessions,
            window.NovaMobileReloadSessions
        ];

        for (const fn of candidates) {
            if (typeof fn === "function") {
                try {
                    setTimeout(() => fn(), 100);
                    return;
                } catch (_) {}
            }
        }

        fetch("/api/sessions", {
            credentials: "same-origin",
            cache: "no-store"
        })
            .then((res) => res.json())
            .then((payload) => updateSessionRowsFromList(payload))
            .catch(() => {});
    }

    function sessionIdFromElement(node) {
        let current = node;

        while (current && current !== document.documentElement) {
            const id =
                current.dataset?.sessionId ||
                current.dataset?.id ||
                current.getAttribute?.("data-session-id") ||
                current.getAttribute?.("data-id") ||
                "";

            if (id) return clean(id);

            current = current.parentElement;
        }

        return "";
    }

    function fetchAndUpdateSession(id) {
        const sessionId = clean(id);
        if (!sessionId) return;

        fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
            credentials: "same-origin",
            cache: "no-store"
        })
            .then((res) => res.json())
            .then((payload) => {
                updateTitleFromSession(null, payload);
                refreshSessionsListSoon();
            })
            .catch(() => {});
    }

    document.addEventListener("click", (event) => {
        const id = sessionIdFromElement(event.target);
        if (!id) return;

        setActiveId(id);

        setTimeout(() => fetchAndUpdateSession(id), 120);
        setTimeout(() => fetchAndUpdateSession(id), 700);
    }, true);

    if (!window.__NOVA_MOBILE_SESSION_TITLE_REFRESH_FETCH_20260630__) {
        window.__NOVA_MOBILE_SESSION_TITLE_REFRESH_FETCH_20260630__ = true;

        const previousFetch = window.fetch;

        window.fetch = async function novaMobileSessionTitleRefreshFetch(input, init) {
            const response = await previousFetch.apply(this, arguments);

            try {
                const url = typeof input === "string" ? input : String(input && input.url || "");

                if (
                    url.includes("/api/chat") ||
                    url.includes("/api/state") ||
                    url.includes("/api/sessions")
                ) {
                    response.clone().json().then((payload) => {
                        const session = getSessionFromPayload(payload);

                        if (session) {
                            updateTitleFromSession(session, payload);
                        }

                        if (url.includes("/api/sessions")) {
                            updateSessionRowsFromList(payload);
                        }

                        if (
                            url.includes("/api/chat") ||
                            url.includes("/api/sessions/new") ||
                            url.includes("/rename") ||
                            url.includes("/delete")
                        ) {
                            setTimeout(refreshSessionsListSoon, 250);
                        }
                    }).catch(() => {});
                }
            } catch (error) {
                console.warn("[NOVA_MOBILE_SESSION_TITLE_REFRESH_20260630] fetch skipped", error);
            }

            return response;
        };
    }

    const bootId =
        clean(localStorage.getItem("nova_mobile_active_session_id")) ||
        clean(localStorage.getItem("nova_active_session_id"));

    if (bootId) {
        setTimeout(() => fetchAndUpdateSession(bootId), 300);
        setTimeout(() => fetchAndUpdateSession(bootId), 1200);
    }

    window.NovaMobileRefreshSessionTitle = fetchAndUpdateSession;
    window.NovaMobileRefreshSessionsListSoon = refreshSessionsListSoon;

    console.log("[NOVA_MOBILE_SESSION_TITLE_REFRESH_20260630] ready");
})();

// NOVA_MOBILE_SESSION_ACTIONS_POLISH_20260630
// Safe mobile handlers for rename / pin / delete session actions.
// Tries multiple backend endpoint shapes so it works with current Nova session routes.
(() => {
    "use strict";

    
    console.warn("[NOVA_MOBILE_SESSION_ACTIONS_POLISH_20260630] disabled for freeze recovery");
    return;
if (window.__NOVA_MOBILE_SESSION_ACTIONS_POLISH_20260630__) return;
    window.__NOVA_MOBILE_SESSION_ACTIONS_POLISH_20260630__ = true;

    function clean(value) {
        return String(value || "").trim();
    }

    function getActiveSessionId() {
        return (
            clean(window.NovaMobileActiveSessionId) ||
            clean(window.__novaMobileActiveSessionId) ||
            clean(localStorage.getItem("nova_mobile_active_session_id")) ||
            clean(localStorage.getItem("nova_active_session_id")) ||
            clean(sessionStorage.getItem("nova_mobile_active_session_id")) ||
            ""
        );
    }

    function setActiveSessionId(sessionId) {
        const id = clean(sessionId);
        if (!id) return "";

        window.NovaMobileActiveSessionId = id;
        window.__novaMobileActiveSessionId = id;

        localStorage.setItem("nova_mobile_active_session_id", id);
        localStorage.setItem("nova_active_session_id", id);
        sessionStorage.setItem("nova_mobile_active_session_id", id);

        return id;
    }

    function sessionIdFromElement(node) {
        let current = node;

        while (current && current !== document.documentElement) {
            const id =
                current.dataset?.sessionId ||
                current.dataset?.id ||
                current.getAttribute?.("data-session-id") ||
                current.getAttribute?.("data-id") ||
                "";

            if (id) return clean(id);

            current = current.parentElement;
        }

        return "";
    }

    function actionFromElement(node) {
        let current = node;

        while (current && current !== document.documentElement) {
            const action =
                current.dataset?.action ||
                current.dataset?.sessionAction ||
                current.getAttribute?.("data-action") ||
                current.getAttribute?.("data-session-action") ||
                "";

            const text = clean(
                action ||
                current.getAttribute?.("aria-label") ||
                current.getAttribute?.("title") ||
                current.textContent ||
                ""
            ).toLowerCase();

            if (text.includes("rename")) return "rename";
            if (text.includes("delete") || text.includes("trash") || text.includes("remove")) return "delete";
            if (text.includes("pin") || text.includes("unpin")) return "pin";

            if (
                current.matches?.("button") ||
                current.matches?.("[role='button']") ||
                current.matches?.("a")
            ) {
                break;
            }

            current = current.parentElement;
        }

        return "";
    }

    async function postJson(url, body) {
        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            cache: "no-store",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body || {})
        });

        let payload = {};

        try {
            payload = await response.json();
        } catch (_) {
            payload = {};
        }

        if (!response.ok || payload.ok === false) {
            throw new Error(`Request failed: ${url}`);
        }

        return payload;
    }

    async function tryPostMany(requests) {
        let lastError = null;

        for (const request of requests) {
            try {
                return await postJson(request.url, request.body);
            } catch (error) {
                lastError = error;
            }
        }

        throw lastError || new Error("All session action endpoints failed");
    }

    function showToast(message, kind) {
        const text = clean(message);
        if (!text) return;

        const toastFn =
            window.NovaMobileToast ||
            window.showToast ||
            window.toast ||
            null;

        if (typeof toastFn === "function") {
            try {
                toastFn(text, kind || "info");
                return;
            } catch (_) {}
        }

        console.log(`[NOVA_MOBILE_SESSION_ACTIONS_POLISH_20260630] ${text}`);
    }

    function refreshSessions() {
        const refreshers = [
            window.NovaMobileRefreshSessionsListSoon,
            window.NovaMobileLoadSessions,
            window.NovaMobileRefreshSessions,
            window.NovaMobileReloadSessions,
            window.NovaMobileRenderSessions
        ];

        for (const fn of refreshers) {
            if (typeof fn === "function") {
                try {
                    setTimeout(() => fn(), 100);
                    return;
                } catch (_) {}
            }
        }

        fetch("/api/sessions", {
            credentials: "same-origin",
            cache: "no-store"
        }).catch(() => {});
    }

    function restoreActiveSession() {
        const id = getActiveSessionId();

        if (!id) return;

        if (typeof window.NovaMobileRestoreSessionMessages === "function") {
            try {
                setTimeout(() => window.NovaMobileRestoreSessionMessages(id), 150);
            } catch (_) {}
        }

        if (typeof window.NovaMobileRefreshSessionTitle === "function") {
            try {
                setTimeout(() => window.NovaMobileRefreshSessionTitle(id), 200);
            } catch (_) {}
        }
    }

    async function renameSession(sessionId) {
        const id = clean(sessionId || getActiveSessionId());
        if (!id) return;

        const currentTitle =
            clean(
                document.querySelector(`[data-session-id="${CSS.escape(id)}"]`)?.dataset?.sessionTitle ||
                document.querySelector(`[data-id="${CSS.escape(id)}"]`)?.dataset?.sessionTitle ||
                ""
            );

        const nextTitle = clean(window.prompt("Rename session", currentTitle || ""));

        if (!nextTitle) return;

        await tryPostMany([
            {
                url: `/api/sessions/${encodeURIComponent(id)}/rename`,
                body: {
                    title: nextTitle,
                    name: nextTitle,
                    session_id: id
                }
            },
            {
                url: "/api/sessions/rename",
                body: {
                    session_id: id,
                    id,
                    title: nextTitle,
                    name: nextTitle
                }
            },
            {
                url: "/api/session/rename",
                body: {
                    session_id: id,
                    id,
                    title: nextTitle,
                    name: nextTitle
                }
            }
        ]);

        setActiveSessionId(id);
        showToast("Session renamed", "success");
        refreshSessions();
        restoreActiveSession();
    }

    async function deleteSession(sessionId) {
        const id = clean(sessionId || getActiveSessionId());
        if (!id) return;

        const ok = window.confirm("Delete this session?");
        if (!ok) return;

        await tryPostMany([
            {
                url: `/api/sessions/${encodeURIComponent(id)}/delete`,
                body: {
                    session_id: id,
                    id
                }
            },
            {
                url: "/api/sessions/delete",
                body: {
                    session_id: id,
                    id
                }
            },
            {
                url: "/api/session/delete",
                body: {
                    session_id: id,
                    id
                }
            }
        ]);

        const activeId = getActiveSessionId();

        if (activeId === id) {
            localStorage.removeItem("nova_mobile_active_session_id");
            localStorage.removeItem("nova_active_session_id");
            sessionStorage.removeItem("nova_mobile_active_session_id");

            window.NovaMobileActiveSessionId = "";
            window.__novaMobileActiveSessionId = "";
        }

        showToast("Session deleted", "success");
        refreshSessions();

        if (activeId === id) {
            const chat =
                document.querySelector("#mobile-chat-messages") ||
                document.querySelector("#nova-mobile-chat-messages") ||
                document.querySelector(".mobile-chat-messages") ||
                document.querySelector(".chat-messages");

            if (chat) chat.innerHTML = "";
        }
    }

    async function pinSession(sessionId) {
        const id = clean(sessionId || getActiveSessionId());
        if (!id) return;

        await tryPostMany([
            {
                url: `/api/sessions/${encodeURIComponent(id)}/pin`,
                body: {
                    session_id: id,
                    id
                }
            },
            {
                url: "/api/sessions/pin",
                body: {
                    session_id: id,
                    id
                }
            },
            {
                url: "/api/session/pin",
                body: {
                    session_id: id,
                    id
                }
            }
        ]);

        setActiveSessionId(id);
        showToast("Session pin updated", "success");
        refreshSessions();
        restoreActiveSession();
    }

    document.addEventListener("click", (event) => {
        const action = actionFromElement(event.target);
        if (!action) return;

        const sessionId = sessionIdFromElement(event.target) || getActiveSessionId();
        if (!sessionId) return;

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        if (action === "rename") {
            renameSession(sessionId).catch((error) => {
                console.warn("[NOVA_MOBILE_SESSION_ACTIONS_POLISH_20260630] rename failed", error);
                showToast("Rename failed", "error");
            });
            return;
        }

        if (action === "delete") {
            deleteSession(sessionId).catch((error) => {
                console.warn("[NOVA_MOBILE_SESSION_ACTIONS_POLISH_20260630] delete failed", error);
                showToast("Delete failed", "error");
            });
            return;
        }

        if (action === "pin") {
            pinSession(sessionId).catch((error) => {
                console.warn("[NOVA_MOBILE_SESSION_ACTIONS_POLISH_20260630] pin failed", error);
                showToast("Pin failed", "error");
            });
        }
    }, true);

    window.NovaMobileRenameSession = renameSession;
    window.NovaMobileDeleteSession = deleteSession;
    window.NovaMobilePinSession = pinSession;

    console.log("[NOVA_MOBILE_SESSION_ACTIONS_POLISH_20260630] ready");
})();

// NOVA_MOBILE_SESSION_FINAL_OWNER_SHIELD_20260630
// Final owner for the Sessions button.
// Prevents older duplicate/emergency session handlers from fighting the current session drawer.
(() => {
    "use strict";

    
    console.warn("[NOVA_MOBILE_SESSION_FINAL_OWNER_SHIELD_20260630] disabled for freeze recovery");
    return;
if (window.__NOVA_MOBILE_SESSION_FINAL_OWNER_SHIELD_20260630__) return;
    window.__NOVA_MOBILE_SESSION_FINAL_OWNER_SHIELD_20260630__ = true;

    function textOf(node) {
        return String(
            node?.textContent ||
            node?.ariaLabel ||
            node?.title ||
            node?.getAttribute?.("aria-label") ||
            node?.getAttribute?.("title") ||
            ""
        ).toLowerCase().trim();
    }

    function isSessionsTrigger(node) {
        let current = node;

        while (current && current !== document.documentElement) {
            const text = textOf(current);

            if (
                text === "sessions" ||
                text.includes("sessions")
            ) {
                return true;
            }

            if (
                current.id &&
                String(current.id).toLowerCase().includes("session")
            ) {
                return true;
            }

            if (
                current.className &&
                String(current.className).toLowerCase().includes("session")
            ) {
                return true;
            }

            current = current.parentElement;
        }

        return false;
    }

    function openSessionsFinal() {
        const openers = [
            window.NovaMobileOpenSessionsPanelFinal,
            window.NovaMobileOpenSessionsPanel,
            window.NovaMobileShowSessionsPanel,
            window.NovaMobileOpenSessions,
            window.showSessionsPanel,
            window.openSessionsPanel
        ];

        for (const opener of openers) {
            if (typeof opener !== "function") continue;

            try {
                opener();
                return true;
            } catch (error) {
                console.warn("[NOVA_MOBILE_SESSION_FINAL_OWNER_SHIELD_20260630] opener failed", error);
            }
        }

        const panel =
            document.querySelector("#nova-mobile-sessions-panel") ||
            document.querySelector("#mobile-sessions-panel") ||
            document.querySelector(".nova-mobile-sessions-panel") ||
            document.querySelector(".mobile-sessions-panel");

        if (panel) {
            panel.hidden = false;
            panel.classList.add("open", "active", "visible");
            panel.style.display = "";
            return true;
        }

        return false;
    }

    document.addEventListener("click", (event) => {
        if (!isSessionsTrigger(event.target)) return;

        const opened = openSessionsFinal();

        if (!opened) return;

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }, true);

    window.NovaMobileOpenSessionsPanelFinal = openSessionsFinal;

    // Force old aliases to point at the same final owner.
    window.NovaMobileEmergencySessionsOpen = openSessionsFinal;
    window.NovaMobileOpenSessionsPanel = openSessionsFinal;

    console.log("[NOVA_MOBILE_SESSION_FINAL_OWNER_SHIELD_20260630] ready");
})();


/* ============================================================
 * NOVA_MOBILE_NEW_CHAT_AUTH_PRESERVER_20260702
 * Prevent New Chat from wiping login/auth state.
 * Keeps auth-ish localStorage/sessionStorage keys during new-chat flow
 * and forces /api requests to include credentials.
 * ============================================================ */
(function () {
    var MARKER = "__NOVA_MOBILE_NEW_CHAT_AUTH_PRESERVER_20260702__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    var protectUntil = 0;
    var AUTH_KEY_RE = /(auth|login|token|jwt|user|username|email|owner|account|profile|nova_auth|nova_user|nova_owner|local_auth)/i;

    function now() {
        return Date.now ? Date.now() : new Date().getTime();
    }

    function isProtectedNow() {
        return now() < protectUntil;
    }

    function beginProtection(reason) {
        protectUntil = now() + 15000;

        try {
            window.__novaLastAuthProtectReason = reason || "unknown";
        } catch (e) {}
    }

    function safeStores() {
        var stores = [];

        try {
            if (window.localStorage) {
                stores.push(window.localStorage);
            }
        } catch (e) {}

        try {
            if (window.sessionStorage) {
                stores.push(window.sessionStorage);
            }
        } catch (e) {}

        return stores;
    }

    function snapshotAuth() {
        var snap = [];

        safeStores().forEach(function (store, storeIndex) {
            try {
                for (var i = 0; i < store.length; i += 1) {
                    var key = store.key(i);

                    if (!key || !AUTH_KEY_RE.test(String(key))) {
                        continue;
                    }

                    var value = store.getItem(key);

                    if (value !== null && value !== undefined && String(value) !== "") {
                        snap.push({
                            storeIndex: storeIndex,
                            key: key,
                            value: value
                        });
                    }
                }
            } catch (e) {}
        });

        return snap;
    }

    function restoreAuth(snap) {
        if (!snap || !snap.length) {
            return;
        }

        var stores = safeStores();

        snap.forEach(function (item) {
            try {
                var store = stores[item.storeIndex];

                if (!store || !item || !item.key) {
                    return;
                }

                var current = store.getItem(item.key);

                if (current === null || current === undefined || String(current) === "") {
                    store.setItem(item.key, item.value);
                }
            } catch (e) {}
        });
    }

    var lastSnapshot = snapshotAuth();

    function refreshSnapshot() {
        var snap = snapshotAuth();

        if (snap && snap.length) {
            lastSnapshot = snap;
        }

        return lastSnapshot;
    }

    function looksLikeNewChatTarget(target) {
        try {
            var node = target;

            for (var depth = 0; node && depth < 6; depth += 1) {
                var text = String(node.textContent || "").toLowerCase();
                var id = String(node.id || "").toLowerCase();
                var cls = String(node.className || "").toLowerCase();
                var aria = String(node.getAttribute && node.getAttribute("aria-label") || "").toLowerCase();
                var title = String(node.getAttribute && node.getAttribute("title") || "").toLowerCase();

                var joined = [text, id, cls, aria, title].join(" ");

                if (
                    joined.indexOf("new chat") !== -1 ||
                    joined.indexOf("new-chat") !== -1 ||
                    joined.indexOf("new_session") !== -1 ||
                    joined.indexOf("new-session") !== -1 ||
                    joined.indexOf("create session") !== -1
                ) {
                    return true;
                }

                node = node.parentElement;
            }
        } catch (e) {}

        return false;
    }

    try {
        document.addEventListener("pointerdown", function (event) {
            if (looksLikeNewChatTarget(event.target)) {
                refreshSnapshot();
                beginProtection("new-chat-pointerdown");
            }
        }, true);

        document.addEventListener("click", function (event) {
            if (looksLikeNewChatTarget(event.target)) {
                var snap = refreshSnapshot();
                beginProtection("new-chat-click");

                setTimeout(function () {
                    restoreAuth(snap);
                }, 0);

                setTimeout(function () {
                    restoreAuth(snap);
                }, 300);

                setTimeout(function () {
                    restoreAuth(snap);
                }, 1200);
            }
        }, true);
    } catch (e) {}

    safeStores().forEach(function (store) {
        try {
            var originalClear = store.clear.bind(store);
            var originalRemoveItem = store.removeItem.bind(store);

            store.clear = function () {
                var snap = refreshSnapshot();

                originalClear();

                if (isProtectedNow()) {
                    restoreAuth(snap);
                }
            };

            store.removeItem = function (key) {
                if (isProtectedNow() && key && AUTH_KEY_RE.test(String(key))) {
                    return;
                }

                return originalRemoveItem(key);
            };
        } catch (e) {}
    });

    try {
        var originalFetch = window.fetch;

        if (typeof originalFetch === "function") {
            window.fetch = function (input, init) {
                var url = "";

                try {
                    url = typeof input === "string" ? input : String(input && input.url || "");
                } catch (e) {
                    url = "";
                }

                var isApi = url.indexOf("/api/") === 0 || url.indexOf(window.location.origin + "/api/") === 0;
                var isNewSession = url.indexOf("/api/sessions") !== -1 || url.indexOf("/api/chat") !== -1;

                if (isApi) {
                    init = init || {};
                    init.credentials = init.credentials || "include";

                    if (isNewSession) {
                        refreshSnapshot();
                        beginProtection("api-session-or-chat");
                    }
                }

                return originalFetch(input, init).then(function (response) {
                    if (isNewSession) {
                        var snap = lastSnapshot;

                        setTimeout(function () {
                            restoreAuth(snap);
                        }, 0);

                        setTimeout(function () {
                            restoreAuth(snap);
                        }, 500);
                    }

                    return response;
                });
            };
        }
    } catch (e) {}

    try {
        window.addEventListener("pageshow", function () {
            restoreAuth(lastSnapshot);
            refreshSnapshot();
        });

        window.addEventListener("load", function () {
            restoreAuth(lastSnapshot);
            refreshSnapshot();
        });
    } catch (e) {}

    try {
        console.log("[NOVA_MOBILE_NEW_CHAT_AUTH_PRESERVER_20260702] active");
    } catch (e) {}
})();


/* ============================================================
 * NOVA_MOBILE_SESSION_DRAWER_V2_ROUTE_TO_REAL_OWNER_20260703
 * Keep the one visible drawer-v2 button, but route it to the
 * real /api/sessions owner that already has Open/Rename/Pin/Delete.
 * ============================================================ */
(function () {
    "use strict";

    var MARKER = "__NOVA_MOBILE_SESSION_DRAWER_V2_ROUTE_TO_REAL_OWNER_20260703__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    function isDrawerV2Trigger(target) {
        var node = target;

        while (node && node !== document.documentElement) {
            try {
                if (
                    node.id === "nova-session-drawer-v2-button" ||
                    node.getAttribute("data-nova-session-drawer-v2") === "true"
                ) {
                    return true;
                }
            } catch (error) {}

            node = node.parentElement;
        }

        return false;
    }

    function openRealSessionsDrawer() {
        if (typeof window.NovaMobileOpenSessions === "function") {
            window.NovaMobileOpenSessions();
            return true;
        }

        return false;
    }

    document.addEventListener("click", function (event) {
        if (!isDrawerV2Trigger(event.target)) {
            return;
        }

        var opened = openRealSessionsDrawer();

        if (!opened) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }, true);

    console.log("[NOVA_MOBILE_SESSION_DRAWER_V2_ROUTE_TO_REAL_OWNER_20260703] active");
})();

