(() => {
"use strict";

/* -----------------------------
   EVENT BUS (SINGLE SOURCE)
------------------------------*/
window.__NOVA_EVENT_BUS__ = {
    listeners: {},
    emit(event, data) {
        (this.listeners[event] || []).forEach(fn => fn(data));
    },
    on(event, fn) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(fn);
    }
};

/* -----------------------------
   DOM ENGINE
------------------------------*/
window.__NOVA_DOM_ENGINE__ = {
    locked: false,
    lock() {
        this.locked = true;
        console.log("[Nova DOM] LOCKED");
    }
};

/* -----------------------------
   STATE
------------------------------*/
const state = {
    pendingAttachments: [],
    abortController: null
};

/* -----------------------------
   HELPERS
------------------------------*/
const $ = (id) => document.getElementById(id);

function chatBox() {
    return $("nova-mobile-chat") ||
        $("nova-mobile-messages") ||
        $("mobileChatMessages") ||
        document.querySelector(".mobile-chat-messages");
}

function inputBox() {
    return $("nova-mobile-input");
}

/* -----------------------------
   SESSION ID
------------------------------*/
function getSessionId() {
    return localStorage.getItem("nova_active_session_id") ||
        localStorage.getItem("nova_mobile_active_session_id") ||
        null;
}

function setSessionId(id) {
    const clean = String(id || "").trim();
    if (!clean) return;
    localStorage.setItem("nova_active_session_id", clean);
    localStorage.setItem("nova_mobile_active_session_id", clean);
}

/* -----------------------------
   UI HELPERS
------------------------------*/
function scrollBottom() {
    const box = chatBox();
    if (!box) return;
    requestAnimationFrame(() => {
        box.scrollTop = box.scrollHeight;
    });
}

function addBubble(role, text) {
    const box = chatBox();
    if (!box) return;

    const el = document.createElement("div");
    el.className = role === "user"
        ? "nova-message nova-message-user"
        : "nova-message nova-message-assistant";

    el.textContent = text || "";
    box.appendChild(el);
    scrollBottom();
    return el;
}

/* -----------------------------
   SEND LOGIC
------------------------------*/
async function sendText(textOverride) {
    const input = inputBox();
    const text = String(textOverride || input?.value || "").trim();
    if (!text) return;

    const sessionId = getSessionId() || ("mobile_" + Date.now());

    if (input) input.value = "";

    addBubble("user", text);
    const thinking = addBubble("assistant", "Thinking...");

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_text: text,
                session_id: sessionId
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

    } catch (err) {
        thinking?.remove();
        addBubble("assistant", "Request failed.");
    }
}

/* -----------------------------
   WIRING
------------------------------*/
function wireSend() {
    const input = inputBox();
    const send = $("nova-mobile-send");
    if (!input || !send) return;

    send.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        sendText();
    };

    input.onkeydown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendText();
        }
    };
}

function wireStop() {
    const stop = $("nova-mobile-stop");
    if (!stop) return;

    stop.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        state.abortController?.abort();
        state.abortController = null;
    };
}

function wireAttach() {
    const attach = $("nova-mobile-attach");
    const fileInput = $("nova-mobile-file-input");
    if (!attach || !fileInput) return;

    attach.onclick = () => fileInput.click();
}

/* -----------------------------
   COMPOSER FIX (SINGLE OWNER)
------------------------------*/
function fixComposerLayout() {
    const composer = $("nova-mobile-composer");
    const input = inputBox();
    if (!composer || !input) return;

    composer.style.display = "flex";
    composer.style.flexDirection = "column";

    const row = document.getElementById("nova-mobile-composer-row")
        || document.createElement("div");

    row.id = "nova-mobile-composer-row";

    if (input.parentNode !== row) {
        row.appendChild(input);
    }

    composer.appendChild(row);
}

/* -----------------------------
   THINKING INDICATOR (SINGLE)
------------------------------*/
(() => {
    window.__NOVA_EVENT_BUS__?.on("send:click", () => {
        const box = chatBox();
        if (!box || document.getElementById("nova-thinking")) return;

        const el = document.createElement("div");
        el.id = "nova-thinking";
        el.textContent = "Nova is thinking...";
        box.appendChild(el);
    });
})();

/* -----------------------------
   SESSION PANEL (SINGLE)
------------------------------*/
function openSessions() {
    alert("Sessions panel placeholder (clean build)");
}

/* -----------------------------
   BOOT
------------------------------*/
function boot() {
    wireSend();
    wireStop();
    wireAttach();
    fixComposerLayout();

    console.log("[Nova Mobile] CLEAN BUILD READY");

    window.__NOVA_DOM_ENGINE__?.lock();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
    boot();
}

})();