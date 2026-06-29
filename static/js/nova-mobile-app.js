(() => {
    "use strict";

console.log("[NOVA FILE STARTED]");

let __novaModulesInternal = new Map();

Object.defineProperty(window, "__NOVA_MODULES__", {
    get() {
        return __novaModulesInternal;
    },
    set(v) {
        console.error("[Nova DEBUG] __NOVA_MODULES__ was overwritten!");
        console.trace("Overwrite stack trace:");
        debugger; // pauses exactly where corruption happens

        if (v instanceof Map) {
            __novaModulesInternal = v;
        } else {
            __novaModulesInternal = new Map();
        }
    }
});

// HARD IMMUNITY LOCK (keep this AFTER)
if (window.__NOVA_MODULE_SYSTEM_V1__) {
    console.warn("[Nova Modules] duplicate load blocked");
    return;
}
window.__NOVA_MODULE_SYSTEM_V1__ = true;

    /* =============================
       1. GLOBAL SAFE BOOT GUARD
    ============================= */
    if (window.__NOVA_APP_BOOTED__) return;
    window.__NOVA_APP_BOOTED__ = true;

    /* =============================
       2. EVENT BUS (SINGLE SOURCE)
    ============================= */
    const EventBus = {
        listeners: {},
        emit(event, data) {
            (this.listeners[event] || []).forEach(fn => fn(data));
        },
        on(event, fn) {
            if (!this.listeners[event]) this.listeners[event] = [];
            this.listeners[event].push(fn);
        }
    };

    window.__NOVA_EVENT_BUS__ = EventBus;

    /* =============================
       3. GLOBAL STATE
    ============================= */
const state = {
    pendingAttachments: [],
    abortController: null,
    sessionId: null
};

window.NovaMobileAttachments = window.NovaMobileAttachments || [];

    /* =============================
       4. DOM HELPERS
    ============================= */
    const $ = (id) => document.getElementById(id);

const chatBox = () =>
    document.getElementById("mobileChatMessages");

    const inputBox = () => $("nova-mobile-input");

    /* =============================
       5. SESSION SYSTEM
    ============================= */
function getSessionId() {
    return window.__ACTIVE_SESSION_ID__ || localStorage.getItem("nova_active_session_id");
}

function setSessionId(id) {
    window.__ACTIVE_SESSION_ID__ = id;
    localStorage.setItem("nova_active_session_id", id);
}

function ensureSessionId() {
    const id = localStorage.getItem("nova_active_session_id");
    return id; // only use existing backend session
}

async function switchSession(sessionId) {
    console.log("[Sessions] switching:", sessionId);

    const res = await fetch(`/api/sessions/${sessionId}`);
    const data = await res.json();

    if (!data.ok) {
        console.warn("[Sessions] backend rejected session:", sessionId);
        return;
    }

    window.__ACTIVE_SESSION_ID__ = sessionId;
    localStorage.setItem("nova_active_session_id", sessionId);

const chat =
    document.getElementById("mobileChatMessages");

    if (!chat) return;

    chat.innerHTML = "";

    const messages = data.session?.messages || data.messages || [];

    for (const msg of messages) {
        const div = document.createElement("div");

        div.className = msg.role === "user"
            ? "nova-message nova-message-user"
            : "nova-message nova-message-assistant";

        div.textContent = msg.content || msg.text || "";

        chat.appendChild(div);
    }

    chat.scrollTop = chat.scrollHeight;
}

function renderAttachmentPreview() {
    const el = document.getElementById("nova-mobile-attachment-preview");
    if (!el) return;

    const files = window.NovaMobileAttachments || [];

    el.innerHTML = "";

    if (!files.length) {
        el.style.display = "none";
        return;
    }

    el.style.display = "flex";

    for (const file of files) {
        const item = document.createElement("div");
        item.style.position = "relative";
        item.style.width = "64px";
        item.style.height = "64px";
        item.style.marginRight = "8px";
        item.style.borderRadius = "10px";
        item.style.overflow = "hidden";
        item.style.background = "#222";

        const img = document.createElement("img");
        img.src = file.file_url;
        img.style.width = "100%";
        img.style.height = "100%";
        img.style.objectFit = "cover";

        const remove = document.createElement("button");
        remove.textContent = "×";
        remove.style.position = "absolute";
        remove.style.top = "4px";
        remove.style.right = "4px";
        remove.style.width = "18px";
        remove.style.height = "18px";
        remove.style.borderRadius = "50%";
        remove.style.border = "none";
        remove.style.background = "red";
        remove.style.color = "white";
        remove.style.cursor = "pointer";

        remove.onclick = () => {
            window.NovaMobileAttachments =
                window.NovaMobileAttachments.filter(x => x.id !== file.id);

            renderAttachmentPreview();
        };

        item.appendChild(img);
        item.appendChild(remove);
        el.appendChild(item);
    }
}

function wireUpload() {
    const input = document.getElementById("nova-mobile-file-input");
    const attach = document.getElementById("nova-mobile-attach");

    if (attach) {
        attach.onclick = (e) => {
            e.preventDefault();
            input?.click();
        };
    }

    if (!input) return;

    input.onchange = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const form = new FormData();
        form.append("file", file);

        try {
            const res = await fetch("/api/upload", {
                method: "POST",
                body: form
            });

            const data = await res.json();
            if (!data.ok) return;

            const payload = {
                id: crypto.randomUUID(),
                file_url: data.file_url,
                filename: data.filename,
                mime_type: data.mime_type
            };

window.NovaMobileAttachments = window.NovaMobileAttachments || [];
window.NovaMobileAttachments.push(payload);
renderAttachmentPreview();

        } catch (err) {
            console.error(err);
        }

        input.value = "";
    };
}

function wireDragDrop() {
    document.addEventListener("dragover", e => e.preventDefault());

    document.addEventListener("drop", async (e) => {
        e.preventDefault();

        const files = e.dataTransfer.files;
        if (!files?.length) return;

        const form = new FormData();
        form.append("file", files[0]);

        const res = await fetch("/api/upload", {
            method: "POST",
            body: form
        });

        const data = await res.json();
        if (!data.ok) return;

        window.NovaMobileAttachments.push({
            id: crypto.randomUUID(),
            file_url: data.file_url,
            filename: data.filename
        });

        renderAttachmentPreview();
    });
}

async function uploadFile(file) {
console.log("🔥 uploadFile() CALLED");
    const form = new FormData();
    form.append("file", file);

    const res = await fetch("/api/upload", {
        method: "POST",
        body: form
    });

    const data = await res.json();

    if (!data.ok) return;

const payload = {
    id: crypto.randomUUID(),
    file_url: data.file_url,
    filename: data.filename,
    mime_type: data.mime_type,
    original_filename: data.original_filename
};

window.NovaMobileAttachments = window.NovaMobileAttachments || [];
window.NovaMobileAttachments.push(payload);

renderAttachmentPreview?.();
}

    /* =============================
       6. CHAT CORE
    ============================= */
    function addBubble(role, text) {
        const box = chatBox();
        if (!box) return;

        const el = document.createElement("div");
        el.className = role === "user"
            ? "nova-message nova-message-user"
            : "nova-message nova-message-assistant";

        el.textContent = text;
        box.appendChild(el);
        box.scrollTop = box.scrollHeight;

        return el;
    }

async function sendText(textOverride) {
    const input = inputBox();
    const text = (textOverride || input?.value || "").trim();
    if (!text) return;

    const sessionId =
        window.__ACTIVE_SESSION_ID__ ||
        localStorage.getItem("nova_active_session_id");

    if (input) input.value = "";

    addBubble("user", text);
    const thinking = addBubble("assistant", "");
    thinking.textContent = "Thinking...";

    state.abortController = new AbortController();

    EventBus.emit("send:click", { text });

    const attachments = window.NovaMobileAttachments || [];

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            signal: state.abortController.signal,
            body: JSON.stringify({
                user_text: text,
                session_id: sessionId,
                attachments: attachments
            })
        });

        const data = await res.json();

        const answer =
            data?.assistant_message?.text ||
            data?.text ||
            data?.message ||
            "No response.";

        thinking?.remove();
        addBubble("assistant", answer);

        EventBus.emit("response:done", data);

    } catch (err) {
        thinking?.remove();
        addBubble("assistant", err.name === "AbortError" ? "Stopped." : "Error.");
    } finally {
        state.abortController = null;

        window.NovaMobileAttachments = [];

        const el = document.getElementById("nova-mobile-attachment-preview");
        if (el) {
            el.innerHTML = "";
            el.style.display = "none";
        }
    }
}

    /* =============================
       7. WIRING (SINGLE PASS ONLY)
    ============================= */

window.registerModule = function (name, fn, deps = []) {
    if (window.__NOVA_MODULES__.has(name)) return;

    window.__NOVA_MODULES__.set(name, {
        fn,
        deps,
        initialized: false,
        instance: {}
    });
};

window.runModules = function () {
    const modules = window.__NOVA_MODULES__;

    if (!(modules instanceof Map)) {
        console.error("[Nova] Module registry corrupted");
        return;
    }

    function canRun(mod) {
        return mod.deps.every(d => modules.get(d)?.initialized);
    }

    let progress = true;

    while (progress) {
        progress = false;

        for (const [name, mod] of modules) {
            if (mod.initialized) continue;

            if (!canRun(mod)) {
                progress = true;
                continue;
            }

            try {
                const instance = mod.fn?.() || {};
                mod.instance = { ...mod.instance, ...instance };

                mod.initialized = true;

                mod.instance.init?.();
                mod.instance.mount?.();

                console.log("[Nova Module]", name, "loaded");
            } catch (e) {
                console.error("[Nova Module Error]", name, e);
            }
        }
    }

    for (const [name, mod] of modules) {
        try {
            mod.instance.ready?.();
        } catch (e) {
            console.error("[Nova Module Ready Error]", name, e);
        }
    }

    console.log("[Nova Modules] lifecycle complete");
};

console.log("🔥 REACHED WIRE SECTION");

function wire() {
window.__WIRED__ = window.__WIRED__ || false;
if (window.__WIRED__) return;
window.__WIRED__ = true;
    const send = $("nova-mobile-send");
    const stop = $("nova-mobile-stop") || $("nova-mobile-stop-generation");
    const attach = $("nova-mobile-attach");
    const input = inputBox();

    if (send) {
send.addEventListener("click", (e) => {
    e.preventDefault();
    sendText();
});
    }

    if (input) {
        input.onkeydown = (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendText();
            }
        };
    }

    if (stop) {
        stop.onclick = (e) => {
            e.preventDefault();
            state.abortController?.abort();
            state.abortController = null;
        };
    }

    if (attach) {
        attach.onclick = (e) => {
            e.preventDefault();
            $("nova-mobile-file-input")?.click();
        };
    }

// ✅ SESSION TOGGLE
const sessionsToggle = $("nova-mobile-sessions-toggle");

if (sessionsToggle) {
    sessionsToggle.onclick = async (e) => {
        e.preventDefault();

        const panel = document.getElementById("nova-mobile-sessions-panel");
        if (!panel) {
            console.warn("[Sessions] panel not found");
            return;
        }

        const isHidden = panel.classList.contains("hidden");

        // toggle correctly
        panel.classList.toggle("hidden", !isHidden);

        console.log("[Sessions] toggled:", isHidden ? "OPEN" : "CLOSE");

        // only load when opening
        if (isHidden) {
            await loadSessionsPanel();
        }
    };
}

async function loadSessionsPanel() {
    const panel = document.getElementById("nova-mobile-sessions-panel");
    if (!panel) return;

    const res = await fetch("/api/sessions");
    const data = await res.json();

    const sessions = data.sessions || [];

    panel.innerHTML = "";

    for (const s of sessions) {
        const div = document.createElement("div");
        div.className = "session-item";
        div.setAttribute("data-session-id", s.id);
        div.textContent = s.title || s.id;
        panel.appendChild(div);
    }
}
window.boot = function () {
    console.log("🔥 REACHED BOOT SECTION");
    wire();
    ensureSessionId?.();
    window.runModules?.();
    console.log("[Nova Clean App] boot complete");
};

document.addEventListener("click", (e) => {
    const all = e.target.closest("*");
    console.log("[CLICK ELEMENT]", all);
});
}
console.log("[NOVA FILE ENDED]");

})(); 

/* NOVA_MOBILE_CHAT_SEND_FINAL_OWNER_20260629 */
(() => {
    if (window.__NOVA_MOBILE_CHAT_SEND_FINAL_OWNER_20260629__) return;
    window.__NOVA_MOBILE_CHAT_SEND_FINAL_OWNER_20260629__ = true;

    function $(id) {
        return document.getElementById(id);
    }

    function inputBox() {
        return $("nova-mobile-input") ||
            $("mobileInput") ||
            document.querySelector("textarea") ||
            document.querySelector("input[type='text']");
    }

    function sendButton() {
        return $("nova-mobile-send");
    }

    function chatBox() {
        return $("mobileChatMessages") ||
            $("nova-mobile-messages") ||
            $("nova-mobile-chat");
    }

    function getSessionId() {
        let id =
            localStorage.getItem("nova_active_session_id") ||
            localStorage.getItem("nova_mobile_active_session_id") ||
            window.currentSessionId ||
            window.NOVA_SESSION_ID ||
            "";

        id = String(id || "").trim();

        if (!id) {
            id = "mobile_" + Date.now() + "_" + Math.random().toString(16).slice(2);
        }

        localStorage.setItem("nova_active_session_id", id);
        localStorage.setItem("nova_mobile_active_session_id", id);

        window.currentSessionId = id;
        window.NOVA_SESSION_ID = id;

        return id;
    }

function messageTextFromResponse(data, userText) {
    console.log("[Nova Send Final Owner] raw response", data);

    const originalUserText = String(userText || "").trim();

    function isGoodString(value) {
        const text = String(value || "").trim();

        if (!text) return false;
        if (text === originalUserText) return false;
        if (text === "ok") return false;
        if (text === "true") return false;
        if (text === "false") return false;

        return true;
    }

    function pickFromObject(obj) {
        if (!obj || typeof obj !== "object") return "";

        const keys = [
            "reply",
            "response",
            "answer",
            "assistant_reply",
            "assistant_response",
            "assistant_text",
            "assistantMessage",
            "assistant_message",
            "ai_response",
            "output",
            "result",
            "content",
            "text",
            "message"
        ];

        for (const key of keys) {
            const value = obj[key];

            if (typeof value === "string" && isGoodString(value)) {
                return value.trim();
            }

            if (value && typeof value === "object") {
                const nested = pickFromObject(value);
                if (nested) return nested;
            }
        }

        return "";
    }

    if (!data || typeof data !== "object") return "";

    const direct = pickFromObject(data);
    if (direct) return direct;

    const messages =
        Array.isArray(data.messages)
            ? data.messages
            : Array.isArray(data.session?.messages)
                ? data.session.messages
                : Array.isArray(data.data?.messages)
                    ? data.data.messages
                    : Array.isArray(data.chat?.messages)
                        ? data.chat.messages
                        : Array.isArray(data.history)
                            ? data.history
                            : [];

    for (const m of [...messages].reverse()) {
        const role = String(m?.role || m?.sender || "").toLowerCase();

        if (
            role.includes("assistant") ||
            role.includes("nova") ||
            role.includes("bot")
        ) {
            const text =
                m.text ||
                m.content ||
                m.message ||
                m.reply ||
                m.response;

            if (isGoodString(text)) {
                return String(text).trim();
            }
        }
    }

    if (Array.isArray(data.choices)) {
        const choice =
            data.choices[0]?.message?.content ||
            data.choices[0]?.text ||
            data.choices[0]?.delta?.content;

        if (isGoodString(choice)) {
            return String(choice).trim();
        }
    }

    return "";
}

    function appendBubble(role, text) {
        const box = chatBox();
        if (!box) return null;

        const bubble = document.createElement("div");
        const cleanRole = role === "user" ? "user" : "assistant";

        bubble.className = cleanRole === "user"
            ? "nova-message nova-message-user"
            : "nova-message nova-message-assistant";

        bubble.dataset.role = cleanRole;
        bubble.textContent = text;

        box.appendChild(bubble);

        requestAnimationFrame(() => {
            box.scrollTop = box.scrollHeight;
        });

        return bubble;
    }

    function pendingAttachments() {
        try {
            if (Array.isArray(window.NovaMobilePendingAttachments)) {
                return window.NovaMobilePendingAttachments.slice();
            }

            if (Array.isArray(window.__novaMobilePendingAttachments)) {
                return window.__novaMobilePendingAttachments.slice();
            }

            const stored = JSON.parse(localStorage.getItem("nova_mobile_pending_attachments") || "[]");
            return Array.isArray(stored) ? stored : [];
        } catch (e) {
            return [];
        }
    }

function clearAttachmentsAfterSend() {
    try {
        window.NovaMobileAttachments = [];
        window.NovaMobilePendingAttachments = [];
        window.__novaMobilePendingAttachments = [];
        window.NovaMobileUploadedAttachments = [];
        window.NovaMobileSharedAttachments = [];
        window.NovaMobileFinalAttachmentPayloadQueue = [];
        window.NovaMobileAttachmentQueue = [];
        window.novaMobileAttachments = [];
        window.NovaMobileUploadQueue = [];

        localStorage.removeItem("nova_mobile_pending_attachments");
        localStorage.removeItem("nova_mobile_last_uploaded_attachment");

        const visiblePreview = document.getElementById("nova-main-visible-attachment-preview");
        if (visiblePreview) {
            visiblePreview.remove();
        }

        const oldPreview = document.getElementById("nova-mobile-attachment-preview");
        if (oldPreview) {
            oldPreview.remove();
        }
    } catch (e) {
        console.warn("[Nova Send Final Owner] clear attachments failed", e);
    }
}

function currentAttachmentsForSend() {
    function safeArray(value) {
        return Array.isArray(value) ? value : [];
    }

    const all = [
        ...safeArray(window.NovaMobileAttachments),
        ...safeArray(window.NovaMobilePendingAttachments),
        ...safeArray(window.__novaMobilePendingAttachments),
        ...safeArray(window.NovaMobileFinalAttachmentPayloadQueue),
        ...safeArray(window.NovaMobileUploadedAttachments),
        ...safeArray(window.NovaMobileAttachmentQueue),
        ...safeArray(window.novaMobileAttachments),
        ...safeArray(window.NovaMobileSharedAttachments),
        ...safeArray(window.NovaMobileUploadQueue)
    ];

    const seen = new Set();

    return all.filter((item) => {
        if (!item || typeof item !== "object") return false;

        const key =
            item.id ||
            item.file_url ||
            item.url ||
            item.filename ||
            item.name ||
            JSON.stringify(item);

        if (seen.has(key)) return false;
        seen.add(key);

        return true;
    });
}

let sending = false;

async function sendNow(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();

        if (typeof event.stopImmediatePropagation === "function") {
            event.stopImmediatePropagation();
        }
    }

    if (sending) return false;

    const input = inputBox();

    if (!input) {
        console.warn("[Nova Send Final Owner] input missing");
        return false;
    }

    const text = String(input.value || "").trim();

    if (!text) return false;

    const sessionId = getSessionId();
const attachments = currentAttachmentsForSend();

console.log("[Nova Send Final Owner] sending attachments", attachments);

clearAttachmentsAfterSend();

    sending = true;

    input.value = "";
    input.dispatchEvent(new Event("input", { bubbles: true }));

    appendBubble("user", text);

    const assistantBubble = appendBubble("assistant", "Thinking...");

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            credentials: "same-origin",
            cache: "no-store",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: text,
                text: text,
                user_text: text,
                session_id: sessionId,
                sessionId: sessionId,
                attachments: attachments
            })
        });

        const data = await res.json().catch(() => ({}));

        console.log("[Nova Send Final Owner] raw response", data);

        if (!res.ok) {
            throw new Error(data?.error || data?.message || "Chat request failed");
        }

        const reply = messageTextFromResponse(data, text) || "No response text returned.";

        if (assistantBubble) {
            assistantBubble.textContent = reply;
        } else {
            appendBubble("assistant", reply);
        }

        window.dispatchEvent(new CustomEvent("nova:chat-sent", {
            detail: {
                sessionId,
                text,
                response: data
            }
        }));
    } catch (error) {
        console.error("[Nova Send Final Owner] send failed", error);

        if (assistantBubble) {
            assistantBubble.textContent = "Send failed: " + (error?.message || "unknown error");
        }
    } finally {
        sending = false;
    }

    return false;
}

function wireSend() {
    const input = inputBox();
    const send = sendButton();

    if (send) {
        send.disabled = false;
        send.removeAttribute("disabled");
        send.style.pointerEvents = "auto";
        send.onclick = sendNow;

        if (send.dataset.novaSendFinalOwnerCapture !== "1") {
            send.dataset.novaSendFinalOwnerCapture = "1";
            send.addEventListener("click", sendNow, true);
        }
    }

    if (input) {
        input.disabled = false;
        input.removeAttribute("disabled");

        if (input.dataset.novaSendFinalOwnerKeydown !== "1") {
            input.dataset.novaSendFinalOwnerKeydown = "1";

            input.addEventListener("keydown", (event) => {
                if (event.key !== "Enter") return;
                if (event.shiftKey) return;

                sendNow(event);
            }, true);
        }
    }

    console.log("[Nova Send Final Owner] wired", {
        input: !!input,
        send: !!send
    });
}

window.NovaMobileSendNow = sendNow;

wireSend();

setTimeout(wireSend, 50);
setTimeout(wireSend, 250);
setTimeout(wireSend, 1000);

console.log("[Nova Send Final Owner] ready");
})();

/* NOVA_MOBILE_MAIN_ATTACH_BUTTON_OWNER_20260629 */
(() => {
    if (window.__NOVA_MOBILE_MAIN_ATTACH_BUTTON_OWNER_20260629__) return;
    window.__NOVA_MOBILE_MAIN_ATTACH_BUTTON_OWNER_20260629__ = true;

    function $(id) {
        return document.getElementById(id);
    }

function wireMainFileInputUpload() {
    const input =
        $("nova-mobile-file-input") ||
        $("mobileFileInput") ||
        $("fileInput");

    if (!input) {
        console.warn("[Nova Main Attach Owner] file input missing");
        return false;
    }

    if (input.dataset.novaMainUploadOwner === "1") {
        return true;
    }

    input.dataset.novaMainUploadOwner = "1";

    async function handleMainFileInputChange(event) {
        const file = event.target.files && event.target.files[0];

        if (!file) {
            console.warn("[Nova Main Attach Owner] no file selected");
            return;
        }

        console.log("[Nova Main Attach Owner] selected file", {
            name: file.name,
            type: file.type,
            size: file.size
        });

        const form = new FormData();
        form.append("file", file);

        try {
            const res = await fetch("/api/upload", {
                method: "POST",
                credentials: "same-origin",
                body: form
            });

            const data = await res.json().catch(() => ({}));

            console.log("[Nova Main Attach Owner] upload response", data);

            if (!res.ok || data.ok === false) {
                throw new Error(data.error || data.message || "Upload failed");
            }

            const payload = {
                id: data.id || crypto.randomUUID(),
                file_url: data.file_url || data.url || data.path || "",
                url: data.file_url || data.url || data.path || "",
                filename: data.filename || data.original_filename || file.name,
                original_filename: data.original_filename || file.name,
                mime_type: data.mime_type || file.type || "application/octet-stream",
                type: data.mime_type || file.type || "application/octet-stream"
            };

            window.NovaMobileAttachments = [payload];
            window.NovaMobilePendingAttachments = [payload];
            window.__novaMobilePendingAttachments = [payload];
            window.NovaMobileUploadedAttachments = [payload];
            window.NovaMobileSharedAttachments = [payload];

            try {
                localStorage.setItem("nova_mobile_pending_attachments", JSON.stringify([payload]));
                localStorage.setItem("nova_mobile_last_uploaded_attachment", JSON.stringify(payload));
            } catch (e) {}

            renderMainAttachmentPreview(payload);

            console.log("[Nova Main Attach Owner] attachment stored", payload);
        } catch (error) {
            console.error("[Nova Main Attach Owner] upload failed", error);
        } finally {
            input.value = "";
        }
}

input.onchange = handleMainFileInputChange;

    console.log("[Nova Main Attach Owner] upload input wired", input.id);

    return true;
}

function renderMainAttachmentPreview(payload) {
    let preview = document.getElementById("nova-main-visible-attachment-preview");

    if (!preview) {
        preview = document.createElement("div");
        preview.id = "nova-main-visible-attachment-preview";
        document.body.appendChild(preview);

        console.log("[Nova Main Attach Owner] visible preview created");
    }

    document.body.appendChild(preview);

    function important(name, value) {
        preview.style.setProperty(name, value, "important");
    }

    preview.innerHTML = "";

important("position", "fixed");
important("top", "auto");
important("bottom", "92px");
important("left", "10px");
important("right", "10px");
important("width", "calc(100vw - 20px)");
important("height", "58px");
important("z-index", "2147483647");
important("display", "flex");
important("visibility", "visible");
important("opacity", "1");
important("align-items", "center");
important("gap", "10px");
important("padding", "8px");
important("box-sizing", "border-box");
important("border-radius", "14px");
important("background", "rgba(30,20,45,0.96)");
important("border", "1px solid rgba(255,255,255,0.16)");
important("box-shadow", "0 8px 28px rgba(0,0,0,0.35)");
important("outline", "none");
important("color", "#fff");
important("font-size", "14px");
important("font-weight", "700");
important("pointer-events", "auto");

    if (payload.file_url || payload.url) {
        const img = document.createElement("img");
        img.src = payload.file_url || payload.url;
        img.alt = payload.original_filename || payload.filename || "attachment";

        img.style.setProperty("width", "44px", "important");
        img.style.setProperty("height", "44px", "important");
        img.style.setProperty("object-fit", "cover", "important");
        img.style.setProperty("border-radius", "10px", "important");
        img.style.setProperty("background", "#111", "important");
        img.style.setProperty("flex", "0 0 auto", "important");

        preview.appendChild(img);
    }

    const label = document.createElement("div");
    label.textContent = "ATTACHED: " + (payload.original_filename || payload.filename || "file");

    label.style.setProperty("overflow", "hidden", "important");
    label.style.setProperty("white-space", "nowrap", "important");
    label.style.setProperty("text-overflow", "ellipsis", "important");

    preview.appendChild(label);

const close = document.createElement("button");
close.type = "button";
close.textContent = "×";

close.style.setProperty("margin-left", "auto", "important");
close.style.setProperty("width", "32px", "important");
close.style.setProperty("height", "32px", "important");
close.style.setProperty("border", "0", "important");
close.style.setProperty("border-radius", "999px", "important");
close.style.setProperty("background", "rgba(255,255,255,0.14)", "important");
close.style.setProperty("color", "#fff", "important");
close.style.setProperty("font-size", "22px", "important");
close.style.setProperty("line-height", "28px", "important");
close.style.setProperty("cursor", "pointer", "important");

close.onclick = (event) => {
    event.preventDefault();
    event.stopPropagation();

    preview.remove();

    window.NovaMobileAttachments = [];
    window.NovaMobilePendingAttachments = [];
    window.__novaMobilePendingAttachments = [];
    window.NovaMobileUploadedAttachments = [];
    window.NovaMobileSharedAttachments = [];
    window.NovaMobileFinalAttachmentPayloadQueue = [];
    window.NovaMobileAttachmentQueue = [];
    window.novaMobileAttachments = [];
    window.NovaMobileUploadQueue = [];

    localStorage.removeItem("nova_mobile_pending_attachments");
    localStorage.removeItem("nova_mobile_last_uploaded_attachment");

    console.log("[Nova Main Attach Owner] preview closed and attachments cleared");
};

preview.appendChild(close);

    console.log("[Nova Main Attach Owner] visible preview rendered", {
        preview,
        parent: preview.parentElement,
        rect: preview.getBoundingClientRect(),
        style: {
            display: getComputedStyle(preview).display,
            visibility: getComputedStyle(preview).visibility,
            opacity: getComputedStyle(preview).opacity,
            zIndex: getComputedStyle(preview).zIndex,
            position: getComputedStyle(preview).position,
            top: getComputedStyle(preview).top,
            width: getComputedStyle(preview).width,
            height: getComputedStyle(preview).height
        }
    });
}



    function wireMainAttachButton() {
        const attach = $("nova-mobile-attach");
        const input =
            $("nova-mobile-file-input") ||
            $("mobileFileInput") ||
            $("fileInput");

        if (!attach || !input) {
            console.warn("[Nova Main Attach Owner] missing", {
                attach: !!attach,
                input: !!input
            });
            return false;
        }

        attach.disabled = false;
        attach.removeAttribute("disabled");
        attach.style.pointerEvents = "auto";
        attach.style.visibility = "visible";
        attach.style.opacity = "1";
        attach.style.zIndex = "2147483647";

        attach.onclick = (event) => {
            event.preventDefault();
            event.stopPropagation();

            if (typeof event.stopImmediatePropagation === "function") {
                event.stopImmediatePropagation();
            }

            console.log("[Nova Main Attach Owner] opening file picker");
            input.click();

            return false;
        };

        if (attach.dataset.novaMainAttachCapture !== "1") {
            attach.dataset.novaMainAttachCapture = "1";

            attach.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();

                if (typeof event.stopImmediatePropagation === "function") {
                    event.stopImmediatePropagation();
                }

                console.log("[Nova Main Attach Owner] capture opening file picker");
                input.click();

                return false;
            }, true);
        }

        console.log("[Nova Main Attach Owner] wired", {
            attach: attach.id,
            input: input.id
        });

        return true;
    }

wireMainAttachButton();
wireMainFileInputUpload();

setTimeout(() => {
    wireMainAttachButton();
    wireMainFileInputUpload();
}, 100);

setTimeout(() => {
    wireMainAttachButton();
    wireMainFileInputUpload();
}, 500);

setTimeout(() => {
    wireMainAttachButton();
    wireMainFileInputUpload();
}, 1200);

})();