/* NOVA_MOBILE_APP_CLEAN_OWNER_20260627 */

(() => {
    if (window.__NOVA_MOBILE_APP_CLEAN_OWNER_20260627__) return;
    window.__NOVA_MOBILE_APP_CLEAN_OWNER_20260627__ = true;

    console.log("[Nova Mobile App] clean owner loaded");

    const state = {
        pendingAttachments: [],
        abortController: null
    };

    function $(id) {
        return document.getElementById(id);
    }

    function chatBox() {
        return (
            $("nova-mobile-chat") ||
            $("nova-mobile-messages") ||
            $("mobileChatMessages") ||
            document.querySelector(".mobile-chat-messages")
        );
    }

    function inputBox() {
        return $("nova-mobile-input");
    }

    function getSessionId() {
        return (
            localStorage.getItem("nova_active_session_id") ||
            localStorage.getItem("nova_mobile_active_session_id") ||
            window.currentSessionId ||
            window.NOVA_SESSION_ID ||
            null
        );
    }

    function setSessionId(id) {
        const clean = String(id || "").trim();
        if (!clean) return;

        localStorage.setItem("nova_active_session_id", clean);
        localStorage.setItem("nova_mobile_active_session_id", clean);

        window.currentSessionId = clean;
        window.NOVA_SESSION_ID = clean;
    }

    function ensureSessionId() {
        let id = getSessionId();

        if (!id) {
            id = "mobile_" + Date.now() + "_" + Math.random().toString(16).slice(2, 10);
            setSessionId(id);
        }

        return id;
    }

    function scrollBottom() {
        const box = chatBox();
        if (!box) return;

        requestAnimationFrame(() => {
            box.scrollTop = box.scrollHeight;
        });
    }

    function addBubble(role, text) {
        const box = chatBox();
        if (!box) return null;

        const el = document.createElement("div");
        el.className = role === "user"
            ? "nova-message nova-message-user"
            : "nova-message nova-message-assistant";

        el.dataset.role = role;
        el.textContent = text || "";

        box.appendChild(el);
        scrollBottom();

        return el;
    }

    function ensurePreviewBar() {
        let bar = $("nova-mobile-attachment-preview-bar");
        const composer = $("nova-mobile-composer");

        if (bar) return bar;
        if (!composer || !composer.parentNode) return null;

        bar = document.createElement("div");
        bar.id = "nova-mobile-attachment-preview-bar";
        composer.parentNode.insertBefore(bar, composer);

        return bar;
    }

    function renderAttachmentPreviews() {
        const bar = ensurePreviewBar();
        if (!bar) return;

        bar.innerHTML = "";

        if (!state.pendingAttachments.length) {
            bar.style.display = "none";
            return;
        }

        bar.style.display = "flex";

        state.pendingAttachments.forEach((fileData, index) => {
            const item = document.createElement("button");
            item.type = "button";
            item.textContent = (fileData.original_filename || fileData.filename || "attachment") + " ×";

            item.onclick = () => {
                state.pendingAttachments.splice(index, 1);
                renderAttachmentPreviews();
            };

            bar.appendChild(item);
        });
    }

    async function uploadFiles(files) {
        for (const file of files) {
            const form = new FormData();
            form.append("file", file);

            try {
                const res = await fetch("/api/upload", {
                    method: "POST",
                    body: form
                });

                const data = await res.json();

                if (data && data.ok) {
                    state.pendingAttachments.push(data);
                    renderAttachmentPreviews();
                }
            } catch (error) {
                console.error("[Nova Mobile App] upload failed", error);
            }
        }
    }

    async function sendText(textOverride) {
        const input = inputBox();
        const text = String(textOverride || input?.value || "").trim();

        if (!text) return;

        const sessionId = ensureSessionId();

        if (input) input.value = "";

        localStorage.setItem("nova_last_user_message", text);

        addBubble("user", text);

        const thinking = addBubble("assistant", "Thinking...");

        state.abortController = new AbortController();

        const stop = $("nova-mobile-stop");
        if (stop) stop.style.display = "";

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                signal: state.abortController.signal,
                body: JSON.stringify({
                    user_text: text,
                    session_id: sessionId,
                    attachments: state.pendingAttachments
                })
            });

            const data = await res.json();

            const answer =
                data?.assistant_message?.text ||
                data?.assistant_message ||
                data?.text ||
                data?.message ||
                "No response.";

            if (thinking) thinking.remove();

            addBubble("assistant", String(answer || ""));
        } catch (error) {
            if (thinking) thinking.remove();

            addBubble(
                "assistant",
                error.name === "AbortError" ? "Stopped." : "Request failed."
            );
        } finally {
            state.abortController = null;

            if (stop) stop.style.display = "none";

            state.pendingAttachments = [];
            renderAttachmentPreviews();
        }
    }

    function wireSend() {
        const input = inputBox();
        const send = $("nova-mobile-send");

        if (!input || !send) return false;

        send.onclick = (event) => {
            event.preventDefault();
            event.stopPropagation();
            sendText();
        };

        input.onkeydown = (event) => {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                sendText();
            }
        };

        return true;
    }

    function wireStop() {
        const stop = $("nova-mobile-stop");
        if (!stop) return;

        stop.onclick = (event) => {
            event.preventDefault();
            event.stopPropagation();

            if (state.abortController) {
                state.abortController.abort();
                state.abortController = null;
            }

            stop.style.display = "none";
        };
    }

    function wireAttach() {
        const attach = $("nova-mobile-attach");
        const fileInput =
            $("nova-mobile-file-input") ||
            $("nova-mobile-upload") ||
            document.querySelector("input[type='file']");

        if (!attach || !fileInput) return;

        attach.onclick = (event) => {
            event.preventDefault();
            event.stopPropagation();
            fileInput.click();
        };

        fileInput.onchange = () => {
            const files = Array.from(fileInput.files || []);
            if (files.length) uploadFiles(files);
            fileInput.value = "";
        };
    }

function wireSessionsButton() {
    const btn = $("nova-mobile-sessions-toggle");
    if (!btn) return;

    btn.style.setProperty("pointer-events", "auto", "important");
    btn.style.setProperty("visibility", "visible", "important");
    btn.style.setProperty("opacity", "1", "important");
    btn.style.setProperty("z-index", "2147483647", "important");

    const open = (event) => {
        event.preventDefault();
        event.stopPropagation();

        if (typeof event.stopImmediatePropagation === "function") {
            event.stopImmediatePropagation();
        }

        console.log("[Nova Mobile App] sessions button clicked");

if (window.NovaMobileSessions?.open) {
    window.NovaMobileSessions.open();

    setTimeout(() => {
        const panel = document.getElementById("nova-mobile-sessions-panel");

        if (panel) {
            panel.classList.remove("hidden");
            panel.removeAttribute("aria-hidden");

            panel.style.setProperty("display", "block", "important");
            panel.style.setProperty("visibility", "visible", "important");
            panel.style.setProperty("opacity", "1", "important");
            panel.style.setProperty("pointer-events", "auto", "important");
            panel.style.setProperty("z-index", "2147483647", "important");
        }
    }, 80);

    return;
}

if (window.NovaMobileOpenSessions) {
    window.NovaMobileOpenSessions();
}
    };

    btn.onclick = open;
    btn.addEventListener("click", open, true);
    btn.addEventListener("pointerdown", open, true);
}
    function boot() {
        wireSend();
        wireStop();
        wireAttach();
        wireSessionsButton();
        ensurePreviewBar();

        console.log("[Nova Mobile App] wired", {
            input: !!inputBox(),
            send: !!$("nova-mobile-send"),
            stop: !!$("nova-mobile-stop"),
            attach: !!$("nova-mobile-attach"),
            sessions: !!$("nova-mobile-sessions-toggle"),
            activeSession: getSessionId()
        });
    }

window.NovaMobileApp = {
    sendText,
    getSessionId,
    setSessionId,
    state
};

window.sendText = sendText;
window.getSessionId = getSessionId;
window.setSessionId = setSessionId;

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
    boot();
}
})();

/* NOVA_MOBILE_FINAL_SESSIONS_PANEL_DIRECT_20260627 */
(() => {
    if (window.__NOVA_MOBILE_FINAL_SESSIONS_PANEL_DIRECT_20260627__) return;
    window.__NOVA_MOBILE_FINAL_SESSIONS_PANEL_DIRECT_20260627__ = true;

    function box() {
        return (
            document.getElementById("mobileChatMessages") ||
            document.getElementById("nova-mobile-chat") ||
            document.getElementById("nova-mobile-messages")
        );
    }

function messageRole(message) {
    return String(message?.role || message?.sender || "assistant")
        .toLowerCase()
        .includes("user")
        ? "user"
        : "assistant";
}

function messageText(message) {
    return message?.text || message?.content || message?.message || "";
}

function cleanSessionMessageText(value) {
    return String(value || "")
        .replace(/(?:Copy\s*Regen\s*)+/gi, "")
        .replace(/(?:Copy\s*){2,}/gi, "")
        .replace(/(?:Regen\s*){2,}/gi, "")
        .replace(/\bCopy\b/gi, "")
        .replace(/\bRegen\b/gi, "")
        .replace(/\s{3,}/g, "\n\n")
        .trim();
}

function renderSessionMessage(chat, message) {
    if (!chat) return;

    const role = messageRole(message);
    const text = cleanSessionMessageText(messageText(message));

    if (!text) return;

    const bubble = document.createElement("div");

    bubble.className = role === "user"
        ? "nova-session-message nova-session-message-user"
        : "nova-session-message nova-session-message-assistant";

    bubble.dataset.role = role;
    bubble.dataset.novaNoActions = "1";
    bubble.textContent = text;

    chat.appendChild(bubble);
}

async function loadSession(id, panel) {
    console.log("[Nova Final Sessions] openPanel ENTER");


    const cleanId = String(id || "").trim();
    if (!cleanId) return;

    localStorage.setItem("nova_active_session_id", cleanId);
    localStorage.setItem("nova_mobile_active_session_id", cleanId);

    const chat = box();
    if (chat) chat.innerHTML = "";

    try {
        const res = await fetch(`/api/sessions/${encodeURIComponent(cleanId)}`, {
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

        messages.forEach((message) => {
            renderSessionMessage(chat, message);
        });

        if (chat) chat.scrollTop = chat.scrollHeight;
    } catch (error) {
        console.error("[Nova Final Sessions] load failed", error);
    }

    if (panel) panel.remove();
}

async function openPanel() {
    let panel = document.getElementById("nova-mobile-final-sessions-panel");

    if (!panel) {
        panel = document.createElement("div");
        panel.id = "nova-mobile-final-sessions-panel";
        document.body.appendChild(panel);
    }

panel.style.cssText = `
    position:fixed!important;
    top:58px!important;
    left:10px!important;
    right:10px!important;
    bottom:90px!important;
    z-index:2147483647!important;
    display:flex!important;
    flex-direction:column!important;
    gap:8px!important;
    overflow-y:auto!important;
    background:rgba(15,23,42,.98)!important;
    color:#fff!important;
    padding:12px!important;
    border-radius:18px!important;
    border:1px solid rgba(168,85,247,.35)!important;
    box-sizing:border-box!important;
`;

    panel.innerHTML = "Loading sessions...";

    try {
        const res = await fetch("/api/sessions", { cache: "no-store" });
        const data = await res.json();
        const sessions = data.sessions || data.items || data.data?.sessions || [];

        panel.innerHTML = "";

        const close = document.createElement("button");
        close.type = "button";
        close.textContent = "Close Sessions";
        close.onclick = () => panel.remove();
        panel.appendChild(close);

        sessions.forEach((session) => {
            const id = session.id || session.session_id || session.sessionId;
            if (!id) return;

            const row = document.createElement("button");
            row.type = "button";
            row.textContent = session.title || id;

            row.onclick = async (event) => {
                event.preventDefault();
                event.stopPropagation();

                console.log("[Nova Final Sessions] row clicked", id);
                await loadSession(id, panel);
            };

            panel.appendChild(row);
        });

        if (!sessions.length) {
            const empty = document.createElement("div");
            empty.textContent = "No sessions found.";
            panel.appendChild(empty);
        }
    } catch (error) {
        console.error("[Nova Final Sessions] panel failed", error);
        panel.innerHTML = "Failed to load sessions.";
    }
}

function wire() {
    const btn =
        document.getElementById("nova-mobile-sessions-toggle") ||
        document.getElementById("nova-mobile-floating-sessions-button");

    if (!btn) return;

    btn.textContent = "Sessions";
    btn.onclick = (event) => {
        event.preventDefault();
        event.stopPropagation();

        openPanel();
    };
}

wire();
setTimeout(wire, 700);

window.NovaMobileOpenFinalSessionsPanel = openPanel;

console.log("[Nova Final Sessions] ready");
})();

/* NOVA_MOBILE_SESSIONS_BUTTON_FALLBACK_20260627 */
(() => {
    function ensureSessionsButton() {
        let btn =
            document.getElementById("nova-mobile-sessions-toggle") ||
            document.getElementById("nova-mobile-floating-sessions-button");

        if (!btn) {
            btn = document.createElement("button");
            btn.id = "nova-mobile-floating-sessions-button";
            btn.type = "button";
            btn.textContent = "Sessions";
            document.body.appendChild(btn);
        }

        btn.onclick = (event) => {
            event.preventDefault();
            event.stopPropagation();
            window.NovaMobileOpenFinalSessionsPanel?.();
        };
    }

    ensureSessionsButton();
    setTimeout(ensureSessionsButton, 700);
})();

/* NOVA_MOBILE_COPY_REGEN_SIMPLE_20260628 */
(() => {
    if (window.__NOVA_MOBILE_COPY_REGEN_SIMPLE_20260628__) return;
    window.__NOVA_MOBILE_COPY_REGEN_SIMPLE_20260628__ = true;

    function chatBox() {
        return document.getElementById("mobileChatMessages") ||
            document.getElementById("nova-mobile-chat") ||
            document.getElementById("nova-mobile-messages");
    }

    function inputBox() {
        return document.getElementById("nova-mobile-input") ||
            document.querySelector("textarea");
    }

    function sendButton() {
        return document.getElementById("nova-mobile-send");
    }

    function lastUserText() {
        const box = chatBox();
        if (!box) return "";

        const users = [...box.querySelectorAll(".nova-message-user, [data-role='user']")];
        const last = users[users.length - 1];

        return (last?.innerText || last?.textContent || "").trim();
    }

    function ensureActions() {
        const box = chatBox();
        if (!box) return;

        [...box.querySelectorAll(".nova-message-assistant")].forEach((msg) => {
            if (msg.querySelector(".nova-mobile-copy-regen-actions")) return;

            const actions = document.createElement("div");
            actions.className = "nova-mobile-copy-regen-actions";
            actions.style.cssText = `
                display:flex;
                gap:6px;
                margin-top:8px;
                opacity:.9;
            `;

            const copy = document.createElement("button");
            copy.type = "button";
            copy.textContent = "Copy";
            copy.style.cssText = `
                padding:6px 10px;
                border:0;
                border-radius:8px;
                background:#333;
                color:#fff;
                font-size:12px;
            `;

            const regen = document.createElement("button");
            regen.type = "button";
            regen.textContent = "Regen";
            regen.style.cssText = copy.style.cssText;

            copy.onclick = async (event) => {
                event.preventDefault();
                event.stopPropagation();

                const clone = msg.cloneNode(true);
                clone.querySelectorAll(".nova-mobile-copy-regen-actions").forEach(el => el.remove());

                const text = (clone.innerText || clone.textContent || "").trim();

                try {
                    await navigator.clipboard.writeText(text);
                    copy.textContent = "Copied";
                    setTimeout(() => copy.textContent = "Copy", 900);
                } catch (err) {
                    console.error("[Nova Copy] failed", err);
                }
            };

            regen.onclick = (event) => {
                event.preventDefault();
                event.stopPropagation();

                const text = lastUserText();
                const input = inputBox();
                const send = sendButton();

                if (!text || !input || !send) return;

                input.value = text;
                input.dispatchEvent(new Event("input", { bubbles: true }));
                send.click();
            };

            actions.appendChild(copy);
            actions.appendChild(regen);
            msg.appendChild(actions);
        });
    }

    const observer = new MutationObserver(ensureActions);

    function boot() {
        const box = chatBox();
        if (!box) return;

        ensureActions();
        observer.observe(box, { childList: true, subtree: true });
    }

    setTimeout(boot, 300);
    setTimeout(boot, 1000);

    console.log("[NOVA_MOBILE_COPY_REGEN_SIMPLE_20260628] ready");
})();