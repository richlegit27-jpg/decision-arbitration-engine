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
    if (typeof window.NovaMobileSendNow === "function") {
        const input =
            document.getElementById("nova-mobile-input") ||
            document.getElementById("mobileInput");

        if (typeof textOverride === "string" && input) {
            input.value = textOverride;
        }

        return window.NovaMobileSendNow();
    }

    console.warn("[Nova Chat Owner] old sendText blocked; final send owner missing");
    return false;
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
console.log("[Nova Send Final Owner] response data json", JSON.stringify(data, null, 2));

function novaFindGeneratedImageUrl(value, depth = 0) {
    if (!value || depth > 8) return "";

    if (typeof value === "string") {
        const textValue = value.trim();

        if (
            textValue.startsWith("data:image/") ||
            textValue.startsWith("blob:") ||
            textValue.startsWith("/uploads/") ||
            textValue.startsWith("/api/uploads/") ||
            /^https?:\/\/.+\.(png|jpg|jpeg|webp|gif)(\?|#|$)/i.test(textValue)
        ) {
            return textValue;
        }

        const match = textValue.match(
            /(\/(?:api\/)?uploads\/[^"'`\s)]+|https?:\/\/[^"'`\s)]+\.(?:png|jpg|jpeg|webp|gif)(?:\?[^"'`\s)]*)?)/i
        );

        return match ? match[1] : "";
    }

    if (Array.isArray(value)) {
        for (const item of value) {
            const found = novaFindGeneratedImageUrl(item, depth + 1);
            if (found) return found;
        }
        return "";
    }

    if (typeof value === "object") {
        const preferredKeys = [
            "image_url",
            "imageUrl",
            "generated_image_url",
            "generatedImageUrl",
            "output_url",
            "outputUrl",
            "file_url",
            "fileUrl",
            "src",
            "url"
        ];

        for (const key of preferredKeys) {
            if (Object.prototype.hasOwnProperty.call(value, key)) {
                const found = novaFindGeneratedImageUrl(value[key], depth + 1);
                if (found) return found;
            }
        }

        for (const key in value) {
            const found = novaFindGeneratedImageUrl(value[key], depth + 1);
            if (found) return found;
        }
    }

    return "";
}

function novaGeneratedImageAlreadyRendered(imageUrl) {
    try {
        const absolute = new URL(imageUrl, window.location.origin).href;

        return Array.from(document.images || []).some((img) => {
            return img.src === absolute || img.dataset.novaGeneratedImageUrl === imageUrl;
        });
    } catch (e) {
        return false;
    }
}

function novaRenderGeneratedImageFromResponse(responseData) {
    let imageUrl = novaFindGeneratedImageUrl(responseData);

    if (!imageUrl) {
        console.warn("[Nova Send Final Owner] no generated image url found in response");
        return false;
    }

    if (imageUrl.startsWith("uploads/")) {
        imageUrl = "/" + imageUrl;
    }

    if (novaGeneratedImageAlreadyRendered(imageUrl)) {
        console.log("[Nova Send Final Owner] generated image already rendered", imageUrl);
        return true;
    }

    const label =
        responseData?.prompt ||
        responseData?.assistant_message?.prompt ||
        responseData?.assistant_message?.content ||
        responseData?.assistant_message?.text ||
        responseData?.text ||
        text ||
        "Generated image";

    if (window.NovaMobileImages?.appendImage) {
        window.NovaMobileImages.appendImage(imageUrl, label);
        console.log("[Nova Send Final Owner] rendered generated image via NovaMobileImages", imageUrl);
        return true;
    }

    const box =
        document.getElementById("mobileChatMessages") ||
        document.getElementById("nova-mobile-chat") ||
        document.getElementById("nova-mobile-messages");

    if (!box) {
        console.warn("[Nova Send Final Owner] no chat box found for generated image");
        return false;
    }

    const wrap = document.createElement("div");
    wrap.className = "nova-message nova-message-assistant";
    wrap.dataset.role = "assistant";

    const img = document.createElement("img");
    img.src = imageUrl;
    img.alt = "Generated image";
    img.dataset.novaGeneratedImageUrl = imageUrl;
    img.style.maxWidth = "100%";
    img.style.borderRadius = "12px";
    img.style.display = "block";
    img.style.marginTop = "8px";

    wrap.appendChild(img);
    box.appendChild(wrap);
    box.scrollTop = box.scrollHeight;

    console.log("[Nova Send Final Owner] rendered generated image fallback", imageUrl);
    return true;
}

try {
    novaRenderGeneratedImageFromResponse(data);
} catch (e) {
    console.warn("[Nova Send Final Owner] generated image render failed", e);
}

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

function escapeNovaMobileHtml(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderNovaMobileMarkdown(text) {
    const raw = String(text || "");
    const blocks = [];
    let safe = raw.replace(/```([a-zA-Z0-9_-]*)\s*\n([\s\S]*?)```/g, function (_, lang, code) {
        const index = blocks.length;
        blocks.push({
            lang: String(lang || "").trim(),
            code: String(code || "").replace(/\n$/, "")
        });
        return "\n@@NOVA_CODE_BLOCK_" + index + "@@\n";
    });

    safe = escapeNovaMobileHtml(safe);

    safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
    safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    const lines = safe.split("\n");
    const out = [];
    let inList = false;

    lines.forEach(function (line) {
        const codeMatch = line.match(/^@@NOVA_CODE_BLOCK_(\d+)@@$/);

        if (codeMatch) {
            if (inList) {
                out.push("</ul>");
                inList = false;
            }

            const block = blocks[Number(codeMatch[1])] || {};
            const lang = escapeNovaMobileHtml(block.lang || "");
            const code = escapeNovaMobileHtml(block.code || "");

            out.push(
                '<pre class="nova-mobile-code-block">' +
                    (lang ? '<div class="nova-mobile-code-lang">' + lang + '</div>' : "") +
                    '<code>' + code + '</code>' +
                '</pre>'
            );
            return;
        }

        const bullet = line.match(/^\s*[-*]\s+(.+)$/);

        if (bullet) {
            if (!inList) {
                out.push("<ul>");
                inList = true;
            }

            out.push("<li>" + bullet[1] + "</li>");
            return;
        }

        if (inList) {
            out.push("</ul>");
            inList = false;
        }

        if (line.trim()) {
            out.push("<p>" + line + "</p>");
        }
    });

    if (inList) {
        out.push("</ul>");
    }

    return out.join("");
}

function setNovaMobileBubbleHtml(bubble, text) {
    if (!bubble) return;

    const raw = String(text || "");

    console.log("[Nova Chat Markdown HARD] rendering", raw.slice(0, 120));

    function esc(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    const fence = raw.match(/^```([a-zA-Z0-9_-]*)\s*\n([\s\S]*?)\n?```$/);

    if (fence) {
        const lang = esc(fence[1] || "");
        const code = esc(fence[2] || "");

        bubble.innerHTML =
            '<pre class="nova-mobile-code-block">' +
                (lang ? '<div class="nova-mobile-code-lang">' + lang + '</div>' : "") +
                '<code>' + code + '</code>' +
            '</pre>';
    } else {
        let safe = esc(raw);

        safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
        safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

        const lines = safe.split("\n");
        const out = [];
        let inList = false;

        lines.forEach((line) => {
            const bullet = line.match(/^\s*[-*]\s+(.+)$/);

            if (bullet) {
                if (!inList) {
                    out.push("<ul>");
                    inList = true;
                }

                out.push("<li>" + bullet[1] + "</li>");
                return;
            }

            if (inList) {
                out.push("</ul>");
                inList = false;
            }

            if (line.trim()) {
                out.push("<p>" + line + "</p>");
            }
        });

        if (inList) {
            out.push("</ul>");
        }

        bubble.innerHTML = out.join("");
    }

    Array.from(bubble.querySelectorAll("pre")).forEach((pre) => {
        pre.style.setProperty("display", "block", "important");
        pre.style.setProperty("width", "100%", "important");
        pre.style.setProperty("max-width", "100%", "important");
        pre.style.setProperty("overflow-x", "auto", "important");
        pre.style.setProperty("white-space", "pre", "important");
        pre.style.setProperty("background", "rgba(0, 0, 0, 0.36)", "important");
        pre.style.setProperty("border", "1px solid rgba(255, 255, 255, 0.12)", "important");
        pre.style.setProperty("border-radius", "12px", "important");
        pre.style.setProperty("padding", "10px", "important");
        pre.style.setProperty("box-sizing", "border-box", "important");
        pre.style.setProperty("margin", "4px 0 0", "important");
    });

    Array.from(bubble.querySelectorAll(".nova-mobile-code-lang")).forEach((lang) => {
        lang.style.setProperty("font-size", "11px", "important");
        lang.style.setProperty("opacity", "0.72", "important");
        lang.style.setProperty("margin-bottom", "6px", "important");
        lang.style.setProperty("text-transform", "uppercase", "important");
    });

    Array.from(bubble.querySelectorAll("code")).forEach((code) => {
        code.style.setProperty("font-family", "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace", "important");
        code.style.setProperty("font-size", "13px", "important");
        code.style.setProperty("line-height", "1.45", "important");
    });
}

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

console.log("[Nova Send Final Owner] response data", data);

try {
    const imageUrl =
        data?.image_url ||
        data?.imageUrl ||
        data?.url ||
        data?.preview ||
        data?.assistant_message?.image_url ||
        data?.assistant_message?.imageUrl ||
        data?.artifact?.image_url ||
        data?.artifact?.imageUrl ||
        data?.artifact?.viewer?.image_url ||
        data?.artifacts?.[0]?.image_url ||
        data?.artifacts?.[0]?.viewer?.image_url ||
        "";

    if (imageUrl && window.NovaMobileImages?.appendImage) {
        window.NovaMobileImages.appendImage(
            imageUrl,
            data?.prompt || data?.text || text || "Generated image"
        );

        console.log("[Nova Send Final Owner] rendered generated image", imageUrl);
    }
} catch (e) {
    console.warn("[Nova Send Final Owner] generated image render failed", e);
}

        console.log("[Nova Send Final Owner] raw response", data);

        if (!res.ok) {
            throw new Error(data?.error || data?.message || "Chat request failed");
        }

        const reply = messageTextFromResponse(data, text) || "No response text returned.";

if (assistantBubble) {
    setNovaMobileBubbleHtml(assistantBubble, reply);
} else {
    const bubble = appendBubble("assistant", "");
    setNovaMobileBubbleHtml(bubble, reply);
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

window.NovaMobileSendText = function (text) {
    const input =
        document.getElementById("nova-mobile-input") ||
        document.getElementById("mobileInput");

    if (typeof text === "string" && input) {
        input.value = text;
    }

    return sendNow();
};

window.sendText = window.NovaMobileSendText;

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

console.log("[Nova Send Final Owner] response data", data);

try {
    const imageUrl =
        data?.image_url ||
        data?.imageUrl ||
        data?.assistant_message?.image_url ||
        data?.assistant_message?.imageUrl ||
        data?.artifact?.image_url ||
        data?.artifact?.imageUrl ||
        data?.artifact?.viewer?.image_url ||
        data?.artifacts?.[0]?.image_url ||
        data?.artifacts?.[0]?.viewer?.image_url ||
        "";

    if (imageUrl) {
        if (window.NovaMobileImages?.appendImage) {
            window.NovaMobileImages.appendImage(
                imageUrl,
                data?.prompt || data?.text || text || "Generated image"
            );
        } else {
            const box =
                document.getElementById("mobileChatMessages") ||
                document.getElementById("nova-mobile-chat") ||
                document.getElementById("nova-mobile-messages");

            if (box) {
                const wrap = document.createElement("div");
                wrap.className = "nova-message nova-message-assistant";
                wrap.dataset.role = "assistant";

                const img = document.createElement("img");
                img.src = imageUrl;
                img.alt = "Generated image";
                img.style.maxWidth = "100%";
                img.style.borderRadius = "12px";
                img.style.display = "block";

                wrap.appendChild(img);
                box.appendChild(wrap);
                box.scrollTop = box.scrollHeight;
            }
        }

        console.log("[Nova Send Final Owner] rendered generated image", imageUrl);
    }
} catch (e) {
    console.warn("[Nova Send Final Owner] generated image render failed", e);
}

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
/* -------------------------------------------------
   NOVA MOBILE COMPOSER FINAL GEOMETRY OVERRIDE
   Input on top, buttons inside composer underneath.
   Order: Send / Stop / Mic / Stop Speech / TTS / Attach / Menu
   20260629
-------------------------------------------------- */
(() => {
    if (window.__NOVA_MOBILE_COMPOSER_FINAL_GEOMETRY_20260629_V2__) return;
    window.__NOVA_MOBILE_COMPOSER_FINAL_GEOMETRY_20260629_V2__ = true;

    function $(id) {
        return document.getElementById(id);
    }

    function firstExisting(ids) {
        for (const id of ids) {
            const el = $(id);
            if (el) return el;
        }
        return null;
    }

    function installFinalComposerStyle() {
        let style = $("nova-mobile-composer-final-geometry-style");

        if (!style) {
            style = document.createElement("style");
            style.id = "nova-mobile-composer-final-geometry-style";
            document.head.appendChild(style);
        }

        style.textContent = `
            #nova-mobile-composer {
                position: fixed !important;
                left: 50% !important;
                right: auto !important;
                bottom: calc(10px + env(safe-area-inset-bottom)) !important;
                width: min(calc(100vw - 16px), 760px) !important;
                max-width: 760px !important;
                transform: translateX(-50%) !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: stretch !important;
                justify-content: flex-end !important;
                gap: 8px !important;
                height: auto !important;
                min-height: 0 !important;
                max-height: 45vh !important;
                overflow: visible !important;
                box-sizing: border-box !important;
                z-index: 2147483646 !important;
            }

            #nova-mobile-input,
            #mobileInput,
            textarea#nova-mobile-input {
                width: 100% !important;
                min-height: 44px !important;
                max-height: 130px !important;
                box-sizing: border-box !important;
                flex: 0 0 auto !important;
            }

            #nova-mobile-composer-actions {
                display: flex !important;
                position: relative !important;
                left: auto !important;
                right: auto !important;
                top: auto !important;
                bottom: auto !important;
                width: 100% !important;
                height: 44px !important;
                min-height: 44px !important;
                align-items: center !important;
                justify-content: center !important;
                gap: 7px !important;
                padding: 0 !important;
                margin: 0 !important;
                box-sizing: border-box !important;
                visibility: visible !important;
                opacity: 1 !important;
                pointer-events: auto !important;
                overflow: visible !important;
                transform: none !important;
                z-index: 2147483647 !important;
            }

            #nova-mobile-composer-actions button,
            #nova-mobile-send,
            #nova-mobile-stop-generation,
            #nova-mobile-stop,
            #nova-mobile-voice,
            #nova-mobile-stop-speech,
            #nova-mobile-tts,
            #nova-mobile-attach,
            #nova-mobile-tools-toggle {
                display: inline-flex !important;
                visibility: visible !important;
                opacity: 1 !important;
                pointer-events: auto !important;
                position: relative !important;
                width: 39px !important;
                height: 39px !important;
                min-width: 39px !important;
                min-height: 39px !important;
                max-width: 39px !important;
                max-height: 39px !important;
                border-radius: 999px !important;
                align-items: center !important;
                justify-content: center !important;
                padding: 0 !important;
                margin: 0 !important;
                flex: 0 0 auto !important;
                transform: none !important;
                z-index: 2147483647 !important;
            }

            #nova-mobile-send,
            .nova-mobile-send-action {
                animation: novaMobileSendGlow 1.8s ease-in-out infinite !important;
            }

            @keyframes novaMobileSendGlow {
                0% { filter: brightness(1); }
                50% { filter: brightness(1.18); }
                100% { filter: brightness(1); }
            }

            #nova-mobile-menu-rescue-btn,
            #nova-mobile-voice-stop-rescue-btn,
            #nova-mobile-bottom-rescue-rail {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                pointer-events: none !important;
            }
        `;
    }

    function normalizeFinalComposerGeometry() {
        installFinalComposerStyle();

        const composer =
            $("nova-mobile-composer") ||
            document.querySelector(".nova-mobile-composer") ||
            document.querySelector("[data-nova-mobile-composer]");

        if (!composer) return false;

        const input =
            $("nova-mobile-input") ||
            $("mobileInput") ||
            composer.querySelector("textarea") ||
            composer.querySelector("input[type='text']");

        if (!input) return false;

        let row = $("nova-mobile-composer-actions");

        if (!row) {
            row = document.createElement("div");
            row.id = "nova-mobile-composer-actions";
            row.className = "nova-mobile-composer-actions";
        }

        const sendButton = firstExisting(["nova-mobile-send"]);
        const generationStopButton = firstExisting(["nova-mobile-stop-generation", "nova-mobile-stop"]);
        const micButton = firstExisting(["nova-mobile-voice"]);
        const speechStopButton = firstExisting(["nova-mobile-stop-speech"]);
        const ttsButton = firstExisting(["nova-mobile-tts"]);
        const attachButton = firstExisting(["nova-mobile-attach"]);
        const menuButton = firstExisting([
            "nova-mobile-tools-toggle",
            "nova-mobile-menu",
            "nova-mobile-menu-btn",
            "nova-mobile-sessions-toggle"
        ]);

        const buttons = [
            sendButton,
            generationStopButton,
            micButton,
            speechStopButton,
            ttsButton,
            attachButton,
            menuButton
        ].filter(Boolean);

        composer.hidden = false;
        composer.removeAttribute("hidden");
        composer.removeAttribute("aria-hidden");

        composer.style.setProperty("position", "fixed", "important");
        composer.style.setProperty("left", "50%", "important");
        composer.style.setProperty("right", "auto", "important");
        composer.style.setProperty("bottom", "calc(10px + env(safe-area-inset-bottom))", "important");
        composer.style.setProperty("width", "min(calc(100vw - 16px), 760px)", "important");
        composer.style.setProperty("max-width", "760px", "important");
        composer.style.setProperty("transform", "translateX(-50%)", "important");
        composer.style.setProperty("display", "flex", "important");
        composer.style.setProperty("flex-direction", "column", "important");
        composer.style.setProperty("gap", "8px", "important");
        composer.style.setProperty("height", "auto", "important");
        composer.style.setProperty("overflow", "visible", "important");
        composer.style.setProperty("box-sizing", "border-box", "important");

        if (input.parentNode !== composer) {
            composer.insertBefore(input, composer.firstChild);
        }

        input.style.setProperty("width", "100%", "important");
        input.style.setProperty("box-sizing", "border-box", "important");

        if (row.parentNode !== composer) {
            composer.appendChild(row);
        }

        row.hidden = false;
        row.removeAttribute("hidden");
        row.removeAttribute("aria-hidden");

        row.style.setProperty("display", "flex", "important");
        row.style.setProperty("position", "relative", "important");
        row.style.setProperty("left", "auto", "important");
        row.style.setProperty("right", "auto", "important");
        row.style.setProperty("top", "auto", "important");
        row.style.setProperty("bottom", "auto", "important");
        row.style.setProperty("width", "100%", "important");
        row.style.setProperty("height", "44px", "important");
        row.style.setProperty("min-height", "44px", "important");
        row.style.setProperty("align-items", "center", "important");
        row.style.setProperty("justify-content", "center", "important");
        row.style.setProperty("gap", "7px", "important");
        row.style.setProperty("padding", "0", "important");
        row.style.setProperty("margin", "0", "important");
        row.style.setProperty("overflow", "visible", "important");
        row.style.setProperty("transform", "none", "important");

        buttons.forEach((button) => {
            if (button.parentNode !== row) {
                row.appendChild(button);
            }

            button.hidden = false;
            button.removeAttribute("hidden");
            button.removeAttribute("aria-hidden");

            button.classList.remove(
                "nova-mobile-send-action",
                "nova-mobile-generation-stop-action",
                "nova-mobile-mic-action",
                "nova-mobile-speech-stop-action",
                "nova-mobile-tts-action",
                "nova-mobile-attach-action",
                "nova-mobile-menu-action"
            );

            if (button === sendButton) button.classList.add("nova-mobile-send-action");
            if (button === generationStopButton) button.classList.add("nova-mobile-generation-stop-action");
            if (button === micButton) button.classList.add("nova-mobile-mic-action");
            if (button === speechStopButton) button.classList.add("nova-mobile-speech-stop-action");
            if (button === ttsButton) button.classList.add("nova-mobile-tts-action");
            if (button === attachButton) button.classList.add("nova-mobile-attach-action");
            if (button === menuButton) button.classList.add("nova-mobile-menu-action");

            button.style.setProperty("display", "inline-flex", "important");
            button.style.setProperty("visibility", "visible", "important");
            button.style.setProperty("opacity", "1", "important");
            button.style.setProperty("pointer-events", "auto", "important");
            button.style.setProperty("position", "relative", "important");
            button.style.setProperty("width", "39px", "important");
            button.style.setProperty("height", "39px", "important");
            button.style.setProperty("min-width", "39px", "important");
            button.style.setProperty("min-height", "39px", "important");
            button.style.setProperty("max-width", "39px", "important");
            button.style.setProperty("max-height", "39px", "important");
            button.style.setProperty("border-radius", "999px", "important");
            button.style.setProperty("align-items", "center", "important");
            button.style.setProperty("justify-content", "center", "important");
            button.style.setProperty("padding", "0", "important");
            button.style.setProperty("margin", "0", "important");
            button.style.setProperty("flex", "0 0 auto", "important");
            button.style.setProperty("transform", "none", "important");
        });

        const chat =
            $("nova-mobile-chat") ||
            $("nova-mobile-messages") ||
            $("mobileChatMessages") ||
            document.querySelector(".nova-mobile-chat") ||
            document.querySelector(".nova-mobile-messages");

        if (chat) {
            chat.style.setProperty("padding-bottom", "155px", "important");
            chat.style.setProperty("scroll-padding-bottom", "155px", "important");
        }

        console.log("[Nova Mobile Composer Final Geometry] ready", {
            composer: !!composer,
            input: !!input,
            rowParent: row.parentElement ? row.parentElement.id : "",
            buttons: buttons.map((button) => button.id)
        });

        return true;
    }

    normalizeFinalComposerGeometry();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", normalizeFinalComposerGeometry, { once: true });
    }

    setTimeout(normalizeFinalComposerGeometry, 100);
    setTimeout(normalizeFinalComposerGeometry, 500);
    setTimeout(normalizeFinalComposerGeometry, 1200);
    setTimeout(normalizeFinalComposerGeometry, 2500);
    setTimeout(normalizeFinalComposerGeometry, 4500);

    window.addEventListener("resize", normalizeFinalComposerGeometry);
    window.addEventListener("orientationchange", normalizeFinalComposerGeometry);

    if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", normalizeFinalComposerGeometry);
        window.visualViewport.addEventListener("scroll", normalizeFinalComposerGeometry);
    }

    window.NovaMobileNormalizeFinalComposerGeometry = normalizeFinalComposerGeometry;
})();

/* -------------------------------------------------
   NOVA MOBILE CHAT TOP SAFE AREA FINAL
   Layout only. Stops first message hiding under header.
   20260629
-------------------------------------------------- */
(() => {
    if (window.__NOVA_MOBILE_CHAT_TOP_SAFE_AREA_20260629__) return;
    window.__NOVA_MOBILE_CHAT_TOP_SAFE_AREA_20260629__ = true;

    function $(id) {
        return document.getElementById(id);
    }

    function chatRoot() {
        return (
            $("mobileChatMessages") ||
            $("nova-mobile-messages") ||
            $("nova-mobile-chat") ||
            document.querySelector("[data-mobile-chat-messages]") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector(".nova-mobile-messages") ||
            document.querySelector(".nova-mobile-chat")
        );
    }

    function headerHeight() {
        const header =
            $("nova-mobile-header") ||
            $("nova-mobile-topbar") ||
            $("nova-mobile-top-bar") ||
            $("nova-mobile-app-header") ||
            document.querySelector(".nova-mobile-header") ||
            document.querySelector(".nova-mobile-topbar") ||
            document.querySelector(".nova-mobile-top-bar") ||
            document.querySelector("header");

        const height = header ? Math.ceil(header.getBoundingClientRect().height || 0) : 0;

        return Math.max(height, 72);
    }

function fixChatTopSafeArea() {
    const chat = chatRoot();
    if (!chat) return false;

    const top = Math.max(headerHeight() - 18, 44);

    chat.style.setProperty(
        "padding-top",
        "calc(" + top + "px + env(safe-area-inset-top))",
        "important"
    );

    chat.style.setProperty(
        "scroll-padding-top",
        "calc(" + top + "px + env(safe-area-inset-top))",
        "important"
    );

    chat.style.setProperty("box-sizing", "border-box", "important");

    const first = chat.firstElementChild;
    if (first) {
        first.style.setProperty("margin-top", "4px", "important");
    }

    console.log("[Nova Mobile Chat Top Safe Area] ready", {
        top,
        chat: chat.id || chat.className || "chat"
    });

    return true;
}

    fixChatTopSafeArea();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", fixChatTopSafeArea, { once: true });
    }

    setTimeout(fixChatTopSafeArea, 100);
    setTimeout(fixChatTopSafeArea, 500);
    setTimeout(fixChatTopSafeArea, 1200);
    setTimeout(fixChatTopSafeArea, 2500);

    window.addEventListener("resize", fixChatTopSafeArea);
    window.addEventListener("orientationchange", fixChatTopSafeArea);

    if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", fixChatTopSafeArea);
        window.visualViewport.addEventListener("scroll", fixChatTopSafeArea);
    }

    window.NovaMobileFixChatTopSafeArea = fixChatTopSafeArea;
})();

/* -------------------------------------------------
   NOVA MOBILE CHAT STACK FINAL CLEANUP
   Removes old inline overlap geometry from messages.
   20260629
-------------------------------------------------- */
(() => {
    if (window.__NOVA_MOBILE_CHAT_STACK_CLEANUP_20260629__) return;
    window.__NOVA_MOBILE_CHAT_STACK_CLEANUP_20260629__ = true;

    function $(id) {
        return document.getElementById(id);
    }

    function chatRoot() {
        return (
            $("mobileChatMessages") ||
            $("nova-mobile-messages") ||
            $("nova-mobile-chat") ||
            document.querySelector("[data-mobile-chat-messages]") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector(".nova-mobile-messages") ||
            document.querySelector(".nova-mobile-chat")
        );
    }

    function normalizeChatStack() {
        const chat = chatRoot();
        if (!chat) return false;

        chat.style.setProperty("display", "flex", "important");
        chat.style.setProperty("flex-direction", "column", "important");
        chat.style.setProperty("align-items", "stretch", "important");
        chat.style.setProperty("justify-content", "flex-start", "important");
        chat.style.setProperty("gap", "10px", "important");
        chat.style.setProperty("overflow-y", "auto", "important");
        chat.style.setProperty("overflow-x", "hidden", "important");
        chat.style.setProperty("box-sizing", "border-box", "important");

        const messages = Array.from(chat.children || []);

        messages.forEach((el) => {
            el.style.setProperty("position", "relative", "important");
            el.style.setProperty("top", "auto", "important");
            el.style.setProperty("right", "auto", "important");
            el.style.setProperty("bottom", "auto", "important");
            el.style.setProperty("left", "auto", "important");
            el.style.setProperty("transform", "none", "important");
            el.style.setProperty("flex", "0 0 auto", "important");
            el.style.setProperty("height", "auto", "important");
            el.style.setProperty("min-height", "0", "important");
            el.style.setProperty("max-height", "none", "important");
            el.style.setProperty("overflow", "visible", "important");
            el.style.setProperty("box-sizing", "border-box", "important");
            el.style.setProperty("white-space", "pre-wrap", "important");
            el.style.setProperty("word-break", "break-word", "important");
            el.style.setProperty("overflow-wrap", "anywhere", "important");
            el.style.setProperty("line-height", "1.42", "important");
        });

        console.log("[Nova Mobile Chat Stack Cleanup] ready", {
            chat: chat.id || chat.className || "chat",
            messages: messages.length
        });

        return true;
    }

    normalizeChatStack();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", normalizeChatStack, { once: true });
    }

    setTimeout(normalizeChatStack, 100);
    setTimeout(normalizeChatStack, 500);
    setTimeout(normalizeChatStack, 1200);
    setTimeout(normalizeChatStack, 2500);

    window.addEventListener("resize", normalizeChatStack);
    window.addEventListener("orientationchange", normalizeChatStack);

    const chat = chatRoot();
    if (chat && window.MutationObserver) {
        const observer = new MutationObserver(() => {
            requestAnimationFrame(normalizeChatStack);
        });

        observer.observe(chat, {
            childList: true,
            subtree: false
        });

        window.__NovaMobileChatStackCleanupObserver = observer;
    }

    window.NovaMobileNormalizeChatStack = normalizeChatStack;
})();

/* -------------------------------------------------
   NOVA MOBILE CHAT BUBBLE ROLE TAGGER + POLISH
   Runtime visual polish for real live message nodes.
   20260629
-------------------------------------------------- */
(() => {
    if (window.__NOVA_MOBILE_CHAT_BUBBLE_POLISH_20260629__) return;
    window.__NOVA_MOBILE_CHAT_BUBBLE_POLISH_20260629__ = true;

    function $(id) {
        return document.getElementById(id);
    }

    function chatRoot() {
        return (
            $("mobileChatMessages") ||
            $("nova-mobile-messages") ||
            $("nova-mobile-chat") ||
            document.querySelector("[data-mobile-chat-messages]") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector(".nova-mobile-messages") ||
            document.querySelector(".nova-mobile-chat")
        );
    }

    function detectRole(el) {
        const raw = [
            el.dataset.role,
            el.dataset.messageRole,
            el.getAttribute("role"),
            el.className,
            el.getAttribute("class")
        ].join(" ").toLowerCase();

        if (raw.includes("user")) return "user";
        if (raw.includes("assistant") || raw.includes("bot") || raw.includes("nova")) return "assistant";

        const text = String(el.textContent || "").trim();

        if (text === "Thinking..." || text.startsWith("Send failed:")) {
            return "assistant";
        }

        const children = Array.from(el.parentElement?.children || []);
        const index = children.indexOf(el);

        return index % 2 === 0 ? "user" : "assistant";
    }

    function polishBubble(el) {
        if (!el || el.nodeType !== 1) return;

        const role = detectRole(el);

        el.classList.add("nova-mobile-polished-bubble");
        el.classList.toggle("nova-mobile-polished-user", role === "user");
        el.classList.toggle("nova-mobile-polished-assistant", role === "assistant");

        el.dataset.novaPolishedRole = role;

        el.style.setProperty("position", "relative", "important");
        el.style.setProperty("display", "block", "important");
        el.style.setProperty("width", "fit-content", "important");
        el.style.setProperty("max-width", "min(86%, 720px)", "important");
        el.style.setProperty("padding", "11px 13px", "important");
        el.style.setProperty("border-radius", "18px", "important");
        el.style.setProperty("font-size", "15px", "important");
        el.style.setProperty("line-height", "1.45", "important");
        el.style.setProperty("white-space", "pre-wrap", "important");
        el.style.setProperty("word-break", "break-word", "important");
        el.style.setProperty("overflow-wrap", "anywhere", "important");
        el.style.setProperty("box-sizing", "border-box", "important");
        el.style.setProperty("height", "auto", "important");
        el.style.setProperty("min-height", "0", "important");
        el.style.setProperty("max-height", "none", "important");
        el.style.setProperty("overflow", "visible", "important");
        el.style.setProperty("box-shadow", "0 8px 22px rgba(0, 0, 0, 0.18)", "important");

        if (role === "user") {
            el.style.setProperty("align-self", "flex-end", "important");
            el.style.setProperty("margin-left", "auto", "important");
            el.style.setProperty("margin-right", "0", "important");
            el.style.setProperty("border-bottom-right-radius", "6px", "important");
            el.style.setProperty("background", "linear-gradient(135deg, rgba(123, 92, 255, 0.96), rgba(75, 126, 255, 0.94))", "important");
            el.style.setProperty("color", "#ffffff", "important");
        } else {
            el.style.setProperty("align-self", "flex-start", "important");
            el.style.setProperty("margin-left", "0", "important");
            el.style.setProperty("margin-right", "auto", "important");
            el.style.setProperty("border-bottom-left-radius", "6px", "important");
            el.style.setProperty("background", "rgba(12, 22, 42, 0.9)", "important");
            el.style.setProperty("border", "1px solid rgba(255, 255, 255, 0.08)", "important");
            el.style.setProperty("color", "rgba(255, 255, 255, 0.94)", "important");
        }

        Array.from(el.querySelectorAll("*")).forEach((child) => {
            child.style.setProperty("max-width", "100%", "important");
            child.style.setProperty("box-sizing", "border-box", "important");
            child.style.setProperty("line-height", "1.45", "important");
        });

        Array.from(el.querySelectorAll("img")).forEach((img) => {
            img.style.setProperty("max-width", "100%", "important");
            img.style.setProperty("height", "auto", "important");
            img.style.setProperty("display", "block", "important");
            img.style.setProperty("border-radius", "14px", "important");
            img.style.setProperty("margin-top", "6px", "important");
        });
    }

    function polishChatBubbles() {
        const chat = chatRoot();
        if (!chat) return false;

        chat.style.setProperty("display", "flex", "important");
        chat.style.setProperty("flex-direction", "column", "important");
        chat.style.setProperty("align-items", "stretch", "important");
        chat.style.setProperty("justify-content", "flex-start", "important");
        chat.style.setProperty("gap", "12px", "important");
        chat.style.setProperty("padding-left", "10px", "important");
        chat.style.setProperty("padding-right", "10px", "important");
        chat.style.setProperty("box-sizing", "border-box", "important");

        const nodes = Array.from(chat.children || []).filter((el) => {
            const text = String(el.textContent || "").trim();
            return text || el.querySelector("img");
        });

        nodes.forEach(polishBubble);

        console.log("[Nova Mobile Chat Bubble Polish] ready", {
            chat: chat.id || chat.className || "chat",
            bubbles: nodes.length
        });

        return true;
    }

    polishChatBubbles();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", polishChatBubbles, { once: true });
    }

    setTimeout(polishChatBubbles, 100);
    setTimeout(polishChatBubbles, 500);
    setTimeout(polishChatBubbles, 1200);
    setTimeout(polishChatBubbles, 2500);

    const chat = chatRoot();
    if (chat && window.MutationObserver) {
        const observer = new MutationObserver(() => {
            requestAnimationFrame(polishChatBubbles);
        });

        observer.observe(chat, {
            childList: true,
            subtree: true
        });

        window.__NovaMobileChatBubblePolishObserver = observer;
    }

    window.NovaMobilePolishChatBubbles = polishChatBubbles;
})();

/* -------------------------------------------------
   NOVA MOBILE FINAL MARKDOWN NORMALIZER
   Converts raw ```code``` and dash bullets after bubbles render.
   20260629
-------------------------------------------------- */
(() => {
    if (window.__NOVA_MOBILE_FINAL_MARKDOWN_NORMALIZER_20260629__) return;
    window.__NOVA_MOBILE_FINAL_MARKDOWN_NORMALIZER_20260629__ = true;

    function $(id) {
        return document.getElementById(id);
    }

    function chatRoot() {
        return (
            $("mobileChatMessages") ||
            $("nova-mobile-messages") ||
            $("nova-mobile-chat") ||
            document.querySelector("[data-mobile-chat-messages]") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector(".nova-mobile-messages") ||
            document.querySelector(".nova-mobile-chat")
        );
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function looksLikeAssistantBubble(el) {
        const raw = [
            el.dataset.role,
            el.dataset.messageRole,
            el.dataset.novaPolishedRole,
            el.className,
            el.getAttribute("class")
        ].join(" ").toLowerCase();

        return raw.includes("assistant") || raw.includes("bot") || raw.includes("nova-message-assistant");
    }

    function renderMarkdownLite(text) {
        const raw = String(text || "");
        const blocks = [];

        let safe = raw.replace(/```([a-zA-Z0-9_-]*)\s*\n([\s\S]*?)```/g, function (_, lang, code) {
            const index = blocks.length;
            blocks.push({
                lang: String(lang || "").trim(),
                code: String(code || "").replace(/\n$/, "")
            });
            return "\n@@NOVA_CODE_BLOCK_" + index + "@@\n";
        });

        safe = escapeHtml(safe);
        safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
        safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

        const lines = safe.split("\n");
        const out = [];
        let inList = false;

        lines.forEach((line) => {
            const codeMatch = line.match(/^@@NOVA_CODE_BLOCK_(\d+)@@$/);

            if (codeMatch) {
                if (inList) {
                    out.push("</ul>");
                    inList = false;
                }

                const block = blocks[Number(codeMatch[1])] || {};
                const lang = escapeHtml(block.lang || "");
                const code = escapeHtml(block.code || "");

                out.push(
                    '<pre class="nova-mobile-code-block">' +
                        (lang ? '<div class="nova-mobile-code-lang">' + lang + '</div>' : "") +
                        '<code>' + code + '</code>' +
                    '</pre>'
                );
                return;
            }

            const bullet = line.match(/^\s*[-*]\s+(.+)$/);

            if (bullet) {
                if (!inList) {
                    out.push("<ul>");
                    inList = true;
                }

                out.push("<li>" + bullet[1] + "</li>");
                return;
            }

            if (inList) {
                out.push("</ul>");
                inList = false;
            }

            if (line.trim()) {
                out.push("<p>" + line + "</p>");
            }
        });

        if (inList) out.push("</ul>");

        return out.join("");
    }

    function normalizeMarkdownBubble(el) {
        if (!el || el.nodeType !== 1) return;

        if (!looksLikeAssistantBubble(el)) return;

        if (el.querySelector("pre, ul, ol")) return;

        const raw = String(el.textContent || "").trim();

        if (!raw) return;

        const hasMarkdown =
            raw.includes("```") ||
            /^\s*[-*]\s+/m.test(raw) ||
            raw.includes("**") ||
            /`[^`]+`/.test(raw);

        if (!hasMarkdown) return;

        el.innerHTML = renderMarkdownLite(raw);

        Array.from(el.querySelectorAll("pre")).forEach((pre) => {
            pre.style.setProperty("max-width", "100%", "important");
            pre.style.setProperty("overflow-x", "auto", "important");
            pre.style.setProperty("white-space", "pre", "important");
            pre.style.setProperty("background", "rgba(0, 0, 0, 0.34)", "important");
            pre.style.setProperty("border", "1px solid rgba(255, 255, 255, 0.1)", "important");
            pre.style.setProperty("border-radius", "12px", "important");
            pre.style.setProperty("padding", "10px", "important");
            pre.style.setProperty("box-sizing", "border-box", "important");
            pre.style.setProperty("margin", "6px 0 0", "important");
        });

        Array.from(el.querySelectorAll(".nova-mobile-code-lang")).forEach((lang) => {
            lang.style.setProperty("font-size", "11px", "important");
            lang.style.setProperty("opacity", "0.72", "important");
            lang.style.setProperty("margin-bottom", "6px", "important");
            lang.style.setProperty("text-transform", "uppercase", "important");
        });

        Array.from(el.querySelectorAll("code")).forEach((code) => {
            code.style.setProperty("font-family", "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace", "important");
            code.style.setProperty("font-size", "13px", "important");
        });

        console.log("[Nova Mobile Final Markdown] normalized", raw.slice(0, 80));
    }

    function normalizeAllMarkdown() {
        const chat = chatRoot();
        if (!chat) return false;

        Array.from(chat.children || []).forEach(normalizeMarkdownBubble);
        return true;
    }

    normalizeAllMarkdown();

    setTimeout(normalizeAllMarkdown, 100);
    setTimeout(normalizeAllMarkdown, 500);
    setTimeout(normalizeAllMarkdown, 1200);

    const chat = chatRoot();
    if (chat && window.MutationObserver) {
        const observer = new MutationObserver(() => {
            requestAnimationFrame(normalizeAllMarkdown);
        });

        observer.observe(chat, {
            childList: true,
            subtree: true,
            characterData: true
        });

        window.__NovaMobileFinalMarkdownObserver = observer;
    }

    window.NovaMobileNormalizeMarkdown = normalizeAllMarkdown;
})();

/* -------------------------------------------------
   NOVA MOBILE REAL MESSAGE ACTIONS FINAL
   Adds visible Copy + Regen buttons to real assistant bubbles.
   20260629
-------------------------------------------------- */
(() => {
    if (window.__NOVA_MOBILE_REAL_MESSAGE_ACTIONS_FINAL_20260629__) return;
    window.__NOVA_MOBILE_REAL_MESSAGE_ACTIONS_FINAL_20260629__ = true;

    function $(id) {
        return document.getElementById(id);
    }

    function chatRoot() {
        return (
            $("mobileChatMessages") ||
            $("nova-mobile-messages") ||
            $("nova-mobile-chat") ||
            document.querySelector("[data-mobile-chat-messages]") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector(".nova-mobile-messages") ||
            document.querySelector(".nova-mobile-chat")
        );
    }

    function inputBox() {
        return (
            $("nova-mobile-input") ||
            $("mobileInput") ||
            document.querySelector("textarea") ||
            document.querySelector("input[type='text']")
        );
    }

    function isAssistantBubble(el) {
        if (!el || el.nodeType !== 1) return false;

        const raw = [
            el.dataset.role,
            el.dataset.messageRole,
            el.dataset.novaPolishedRole,
            el.className,
            el.getAttribute("class")
        ].join(" ").toLowerCase();

        if (raw.includes("assistant")) return true;
        if (raw.includes("bot")) return true;
        if (raw.includes("nova-mobile-polished-assistant")) return true;

        return false;
    }

    function isUserBubble(el) {
        if (!el || el.nodeType !== 1) return false;

        const raw = [
            el.dataset.role,
            el.dataset.messageRole,
            el.dataset.novaPolishedRole,
            el.className,
            el.getAttribute("class")
        ].join(" ").toLowerCase();

        return raw.includes("user");
    }

    function previousUserText(el) {
        const siblings = Array.from(el.parentElement?.children || []);
        const index = siblings.indexOf(el);

        for (let i = index - 1; i >= 0; i -= 1) {
            if (isUserBubble(siblings[i])) {
                return String(siblings[i].innerText || siblings[i].textContent || "").trim();
            }
        }

        return "";
    }

    function styleButton(button) {
        button.style.setProperty("display", "inline-flex", "important");
        button.style.setProperty("align-items", "center", "important");
        button.style.setProperty("justify-content", "center", "important");
        button.style.setProperty("height", "28px", "important");
        button.style.setProperty("min-width", "34px", "important");
        button.style.setProperty("padding", "0 10px", "important");
        button.style.setProperty("border-radius", "999px", "important");
        button.style.setProperty("border", "1px solid rgba(255, 255, 255, 0.14)", "important");
        button.style.setProperty("background", "rgba(255, 255, 255, 0.08)", "important");
        button.style.setProperty("color", "rgba(245, 248, 255, 0.92)", "important");
        button.style.setProperty("font-size", "12px", "important");
        button.style.setProperty("line-height", "1", "important");
        button.style.setProperty("cursor", "pointer", "important");
        button.style.setProperty("box-shadow", "none", "important");
    }

    function addActions(el) {
        if (!isAssistantBubble(el)) return;
        if (el.querySelector(":scope > .nova-real-message-actions")) return;

        el.style.setProperty("color", "rgba(245, 248, 255, 0.96)", "important");

        const row = document.createElement("div");
        row.className = "nova-real-message-actions";

        row.style.setProperty("display", "flex", "important");
        row.style.setProperty("align-items", "center", "important");
        row.style.setProperty("justify-content", "flex-start", "important");
        row.style.setProperty("gap", "7px", "important");
        row.style.setProperty("margin-top", "9px", "important");
        row.style.setProperty("padding-top", "4px", "important");
        row.style.setProperty("border-top", "1px solid rgba(255, 255, 255, 0.08)", "important");

        const copy = document.createElement("button");
        copy.type = "button";
        copy.textContent = "Copy";
        copy.title = "Copy message";
        copy.setAttribute("aria-label", "Copy message");
        styleButton(copy);

        copy.addEventListener("click", async (event) => {
            event.preventDefault();
            event.stopPropagation();

            const clone = el.cloneNode(true);
            clone.querySelectorAll(".nova-real-message-actions").forEach((node) => node.remove());

            const text = String(clone.innerText || clone.textContent || "").trim();

            try {
                await navigator.clipboard.writeText(text);
                copy.textContent = "Copied";
                setTimeout(() => {
                    copy.textContent = "Copy";
                }, 900);
            } catch (e) {
                console.warn("[Nova Mobile Actions] copy failed", e);
                copy.textContent = "Fail";
                setTimeout(() => {
                    copy.textContent = "Copy";
                }, 900);
            }
        });

        const regen = document.createElement("button");
        regen.type = "button";
        regen.textContent = "Regen";
        regen.title = "Regenerate response";
        regen.setAttribute("aria-label", "Regenerate response");
        styleButton(regen);

        regen.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();

            const text = previousUserText(el);
            const input = inputBox();

            if (!text || !input) {
                console.warn("[Nova Mobile Actions] regen missing previous user text or input");
                return;
            }

            input.value = text;
            input.dispatchEvent(new Event("input", { bubbles: true }));

            if (typeof window.NovaMobileSendNow === "function") {
                window.NovaMobileSendNow();
                return;
            }

            if (typeof window.NovaMobileSendText === "function") {
                window.NovaMobileSendText(text);
                return;
            }

            const send =
                $("nova-mobile-send") ||
                $("mobileSend") ||
                document.querySelector("[data-send]");

            send?.click?.();
        });

        row.appendChild(copy);
        row.appendChild(regen);
        el.appendChild(row);
    }

    function normalizeActions() {
        const chat = chatRoot();
        if (!chat) return false;

        Array.from(chat.children || []).forEach(addActions);

        console.log("[Nova Mobile Real Message Actions] ready", {
            chat: chat.id || chat.className || "chat",
            bubbles: Array.from(chat.children || []).length
        });

        return true;
    }

    normalizeActions();

    setTimeout(normalizeActions, 100);
    setTimeout(normalizeActions, 500);
    setTimeout(normalizeActions, 1200);
    setTimeout(normalizeActions, 2500);

    const chat = chatRoot();
    if (chat && window.MutationObserver) {
        const observer = new MutationObserver(() => {
            requestAnimationFrame(normalizeActions);
        });

        observer.observe(chat, {
            childList: true,
            subtree: true
        });

        window.__NovaMobileRealMessageActionsObserver = observer;
    }

    window.NovaMobileNormalizeRealMessageActions = normalizeActions;
})();