
/* NOVA_MOBILE_APP_REMOVED_TOP_ATTACHMENT_GLOBALS_20260608 - removed unused global attachment helpers. sendText() local merge/clear path remains active. */
/* NOVA_MOBILE_SMFF_SESSIONS_STABLE_20260606 */

(function () {

    "use strict";
    function novaCleanBadDisplayText(value) {
        let text = String(value || "");

        const bannedPatterns = [
            /bukakke/gi,
            /bukkake/gi,
            /attachment analysis:\s*/gi,
            /this attachment appears to contain extracted image\/pdf content about:\s*/gi,
            /this attachment appears to contain image\/search\/pdf extraction text about:\s*/gi
        ];

        bannedPatterns.forEach(function (pattern) {
            text = text.replace(pattern, "");
        });

        text = text
            .replace(/\n{3,}/g, "\n\n")
            .replace(/[ \t]{2,}/g, " ")
            .trim();

        return text;
    }

    function novaCollectOutgoingAttachments() {
        const found = [];

        function addList(list) {
            if (!Array.isArray(list)) return;

            list.forEach(function (item) {
                if (!item) return;

                const url = item.url || item.file_url || item.path || "";
                const filename = item.filename || item.name || item.original_filename || "attachment";

                if (!url && !filename) return;

                found.push({
                    filename: filename,
                    original_filename: item.original_filename || item.name || filename,
                    name: item.name || item.original_filename || filename,
                    mime_type: item.mime_type || item.type || item.content_type || "",
                    type: item.type || item.mime_type || item.content_type || "",
                    size: item.size || 0,
                    url: url,
                    file_url: item.file_url || url
                });
            });
        }

        try { addList(window.NovaMobileSharedAttachments); } catch (e) {}
        try { addList(window.NovaMobilePendingAttachments); } catch (e) {}
        try { addList(window.NovaPendingAttachments); } catch (e) {}
        try { addList(window.__novaMobilePendingAttachments); } catch (e) {}
        try { addList(window.__novaPendingAttachments); } catch (e) {}
        try { addList(window.NovaMobileAttachmentStore); } catch (e) {}

        try {
            const raw = localStorage.getItem("nova_mobile_pending_attachments");
            if (raw) addList(JSON.parse(raw));
        } catch (e) {}

        const deduped = [];
        const seen = new Set();

        found.forEach(function (item) {
            const key = String(item.url || item.file_url || item.filename || item.name || "").trim();
            if (!key || seen.has(key)) return;
            seen.add(key);
            deduped.push(item);
        });

        console.log("[Nova Mobile Attachment Force Send] outgoing attachments", deduped.length, deduped);
        return deduped;
    }



    function addBubble(role, text) {
        text = novaCleanBadDisplayText(text);
        if (typeof window.NovaMobileAddBubble === "function") {
            return window.NovaMobileAddBubble(role, text);
        }

        const messages =
            document.getElementById("nova-mobile-messages") ||
            document.getElementById("nova-mobile-chat") ||
            document.getElementById("nova-mobile-chat-box") ||
            document.getElementById("nova-mobile-chat-log") ||
            document.getElementById("nova-mobile-thread") ||
            document.getElementById("mobile-chat") ||
            document.getElementById("chat-box") ||
            document.querySelector("[data-nova-mobile-messages]") ||
            document.querySelector("[data-mobile-messages]") ||
            document.querySelector(".nova-mobile-messages") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector(".mobile-chat") ||
            document.querySelector(".chat-messages") ||
            document.querySelector(".messages") ||
            (typeof chatBox === "function" ? chatBox() : null);

        if (!messages) {
            console.warn("[Nova Mobile] addBubble fallback could not find messages container");
            return document.createElement("div");
        }

        const bubble = document.createElement("div");
        bubble.className = "nova-mobile-message nova-mobile-message-" + String(role || "assistant");
        bubble.dataset.role = String(role || "assistant");

        const body = document.createElement("div");
        body.className = "nova-mobile-message-body";
        body.textContent = String(text || "");

        bubble.appendChild(body);
        messages.appendChild(bubble);

        try {
            messages.scrollTop = messages.scrollHeight;
        } catch (_) {}

        return bubble;
    }
    const state = {
        pendingAttachments: [],
        abortController: null,
        isSpeaking: false,
        recognition: null,
        cachedMessages: {},
        sessionTitles: {}
    };

    function $(id) {
        return document.getElementById(id);
    }

    function getSessionId() {
        let id = localStorage.getItem("nova_mobile_active_session_id") || "";

        if (!id) {
            id = "mobile_" + Date.now();
            localStorage.setItem("nova_mobile_active_session_id", id);
        }

        return id;
    }

    function chatBox() {
        return (
            $("mobileChatMessages") ||
            $("nova-mobile-messages") ||
            document.querySelector(".mobile-chat-messages")
        );
    }

    function scrollBottom() {
        const box = chatBox();
        if (!box) return;

        setTimeout(function () {

            box.scrollTop = box.scrollHeight;
            window.scrollTo(0, document.body.scrollHeight);
        }, 50);
    }

    function isImageUrl(text) {
        const value = String(text || "").trim();

        return (
            value.includes("/api/uploads/") ||
            /\.(png|jpg|jpeg|gif|webp)(\?.*)?$/i.test(value)
        );
    }

    function ensureActiveSessionBar() {
        let bar = $("nova-mobile-active-session");
        const box = chatBox();

        if (bar) return bar;
        if (!box || !box.parentNode) return null;

        bar = document.createElement("div");
        bar.id = "nova-mobile-active-session";
        bar.style.padding = "6px 12px";
        bar.style.color = "#f8fafc";
        bar.style.fontSize = "13px";
        bar.style.background = "rgba(11,16,32,.92)";
        bar.style.textAlign = "center";
        bar.style.borderRadius = "10px";
        bar.style.margin = "6px 8px";
        bar.style.border = "1px solid rgba(255,255,255,.12)";

        box.parentNode.insertBefore(bar, box);
        return bar;
    }

    function updateActiveSessionTitle(session) {
        const bar = ensureActiveSessionBar();
        const id = (session && session.id) || getSessionId();
        const title =
            (session && session.title) ||
            (state.sessionTitles && state.sessionTitles[id]) ||
            "New Chat";
        const shortId = String(id || "").slice(-6);

        if (bar) {
            bar.textContent = "Session: " + title + " · " + shortId;
        }
    }

    function ensureButton(id, label, title) {
        let btn = $(id);
        const composer = $("nova-mobile-composer");
        const send = $("nova-mobile-send");

        if (btn) return btn;
        if (!composer) return null;

        btn = document.createElement("button");
        btn.id = id;
        btn.type = "button";
        btn.textContent = label;
        btn.title = title || label;
        btn.style.flex = "0 0 auto";
        btn.style.width = "40px";
        btn.style.height = "40px";
        btn.style.borderRadius = "999px";
        btn.style.display = "inline-flex";
        btn.style.alignItems = "center";
        btn.style.justifyContent = "center";

        if (send && send.parentNode === composer) {
            composer.insertBefore(btn, send);
        } else {
            composer.appendChild(btn);
        }

        return btn;
    }
    function getPendingAttachmentsForSend() {
        const merged = [];

        function addMany(items) {
            if (!Array.isArray(items)) return;

            items.forEach(function (item) {
                if (!item) return;

                const url = String(item.url || item.file_url || "");
                const name = String(item.name || item.original_filename || item.filename || "");

                const exists = merged.some(function (existing) {
                    return String(existing.url || existing.file_url || "") === url &&
                        String(existing.name || existing.original_filename || existing.filename || "") === name;
                });

                if (!exists) {
                    merged.push(item);
                }
            });
        }

        addMany(window.NovaMobileSharedAttachments);

        try {
            addMany(JSON.parse(localStorage.getItem("nova_mobile_pending_attachments") || "[]"));
        } catch (_) {}

        try {
            addMany(JSON.parse(localStorage.getItem("nova_mobile_latest_attachments") || "[]"));
        } catch (_) {}

        try {
            addMany(state.pendingAttachments);
        } catch (_) {}

        return merged;
    }

    function clearPendingAttachmentsAfterSend() {
        window.NovaMobileSharedAttachments = [];

        try {
                        try { if (typeof state !== "undefined" && state) {
            state.pendingAttachments = [];
        }
         } catch (e) {}
            try { window.NovaMobilePendingAttachments = []; } catch (e) {}
            try { window.NovaPendingAttachments = []; } catch (e) {}
            try { window.__novaMobilePendingAttachments = []; } catch (e) {}
            try { window.__novaPendingAttachments = []; } catch (e) {}
            try { window.NovaMobileAttachmentStore = []; } catch (e) {}
            try { localStorage.removeItem("nova_mobile_pending_attachments"); } catch (e) {}
            try { sessionStorage.removeItem("nova_mobile_pending_attachments"); } catch (e) {}
            try {
                if (typeof window.NovaRenderComposerInlinePreview === "function") {
                    window.NovaRenderComposerInlinePreview();
                }
            } catch (e) {}
        } catch (_) {}

        try {
            localStorage.removeItem("nova_mobile_pending_attachments");
            localStorage.removeItem("nova_mobile_latest_attachments");
        } catch (_) {}

        if (typeof window.NovaRenderComposerInlinePreview === "function") {
            window.NovaRenderComposerInlinePreview();
        }

        window.dispatchEvent(new CustomEvent("nova-mobile-attachments-cleared"));
    }
async function sendText(textOverride) {
const input = $("nova-mobile-input");
        const text = String(textOverride || (input ? input.value : "") || "").trim();
        state.pendingAttachments = window.NovaMobileSharedAttachments || state.pendingAttachments || [];
        const attachments = getPendingAttachmentsForSend();
        const sessionId = getSessionId();

        if (!text && !attachments.length) return;

        if (input) input.value = "";

        addBubble("user", text || "Attachment sent.");

        if (!state.sessionTitles[sessionId]) {
            state.sessionTitles[sessionId] = text || "New Chat";
        }

        updateActiveSessionTitle({
            id: sessionId,
            title: state.sessionTitles[sessionId] || text || "New Chat"
        });

        const thinkingBubble = addBubble("assistant", "Thinking...");

        // CLEAR_ATTACHMENTS_AFTER_RESPONSE_LOCK_20260606
        // Do not clear pending attachments before fetch; payload guards and send snapshots may still need them.
        state.abortController = new AbortController();

        try {
const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                signal: state.abortController.signal,
                body: JSON.stringify({
                    user_text: text,
                    session_id: sessionId,
                    attachments: attachments
                })
            });

            const data = await response.json();

            clearPendingAttachmentsAfterSend();

            const imageUrl =
                window.NovaMobileImages &&
                typeof window.NovaMobileImages.extractImageUrlFromResponse === "function"
                    ? window.NovaMobileImages.extractImageUrlFromResponse(data)
                    : "";

            const answer =
                imageUrl ||
                data?.assistant_message?.text ||
                data?.assistant_message?.content ||
                data?.text ||
                data?.error ||
                "No response.";

            if (thinkingBubble) {
                thinkingBubble.innerHTML = "";

                if (
                    imageUrl &&
                    window.NovaMobileImages &&
                    typeof window.NovaMobileImages.renderImageIntoBubble === "function"
                ) {
                    window.NovaMobileImages.renderImageIntoBubble(
                        thinkingBubble,
                        imageUrl,
                        text || "Generated image"
                    );
                } else if (isImageUrl(answer)) {
                    const img = document.createElement("img");
                    img.src = String(answer || "").trim();
                    img.loading = "lazy";
                    img.className = "nova-chat-image";
                    img.style.display = "block";
                    img.style.maxWidth = "100%";
                    img.style.borderRadius = "12px";
                    img.style.marginTop = "4px";
                    thinkingBubble.appendChild(img);
                } else {
                    thinkingBubble.textContent = answer;
                }

                scrollBottom();
            }
        } catch (error) {
            if (thinkingBubble) {
                thinkingBubble.textContent =
                    error && error.name === "AbortError"
                        ? "Stopped."
                        : "Request failed: " + (error && error.message ? error.message : String(error));

                scrollBottom();
            }
        } finally {
            state.abortController = null;
        }
    }

    function stopEverything() {
        if (state.abortController) {
            state.abortController.abort();
        }

        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
            state.isSpeaking = false;
        }

        if (state.recognition) {
            try {
                state.recognition.stop();
            } catch (_) {}
        }
    }

    function latestAssistantText() {
        const box = chatBox();

        if (!box) return "";

        const candidates = Array.from(
            box.querySelectorAll(
                "[data-role='assistant'], .nova-mobile-message-assistant, .assistant, .message-assistant"
            )
        );

        for (let i = candidates.length - 1; i >= 0; i -= 1) {
            const text = String(candidates[i].innerText || candidates[i].textContent || "").trim();

            if (text) {
                return text;
            }
        }

        const fallback = Array.from(box.querySelectorAll("div, p, span"))
            .map(function (el) {
                return String(el.innerText || el.textContent || "").trim();
            })
            .filter(Boolean);

        return fallback.length ? fallback[fallback.length - 1] : "";
    }
    function speakLatest() {
        const text = latestAssistantText();

        if (!text || !window.speechSynthesis) return;

        if (state.isSpeaking) {
            window.speechSynthesis.cancel();
            state.isSpeaking = false;
            return;
        }

        const utterance = new SpeechSynthesisUtterance(text);

        utterance.onend = function () {
            state.isSpeaking = false;
        };

        utterance.onerror = function () {
            state.isSpeaking = false;
        };

        state.isSpeaking = true;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
    }

    // NOVA_MOBILE_APP_REMOVED_APP_OWNED_VOICE_20260608
    // Voice button/input ownership lives in static/js/mobile/nova-mobile-voice.js.

async function newChat(event) {
    if (!event || !event.isTrusted) {
        console.warn("[Nova Mobile] blocked automatic newChat call without trusted user click");
        return null;
    }

    event.preventDefault();
    event.stopPropagation();

    const currentSessionId = getSessionId();
    const box = chatBox();

    if (currentSessionId && box) {
        state.cachedMessages[currentSessionId] = box.innerHTML;
    }

    let id = "mobile_" + Date.now();
    let title = "New Chat";

    try {
        const response = await fetch("/api/sessions/new", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title: title
            })
        });

        const data = await response.json();

        id =
            data?.session?.id ||
            data?.id ||
            data?.session_id ||
            id;

        title =
            data?.session?.title ||
            data?.title ||
            title;
    } catch (err) {
        console.warn("[Nova Mobile] backend session create failed, using local session", err);
    }

    localStorage.setItem("nova_mobile_active_session_id", id);
    state.sessionTitles[id] = title;

    if (box) {
        box.innerHTML = "";
    }

    updateActiveSessionTitle({
        id: id,
        title: title
    });

    addBubble("assistant", "New chat started and saved to Sessions.");

    scrollBottom();

    console.log("[Nova Mobile] new session saved", id);
}

    // NOVA_MOBILE_APP_SESSION_MODULE_CLEANUP_20260608
    // Session panel ownership moved to static/js/mobile/nova-mobile-sessions.js.
    // nova-mobile-app.js must not create, render, rename, pin, delete, or hard-open sessions.

function findSessionsToggle() {
    let btn =
        $("nova-mobile-sessions-toggle") ||
        $("nova-mobile-sessions") ||
        $("mobileSessionsBtn") ||
        document.querySelector("[data-mobile-sessions-toggle]") ||
        document.querySelector("[data-action='sessions']");

    if (btn) {
        return btn;
    }

    btn = document.createElement("button");
    btn.id = "nova-mobile-sessions-toggle";
    btn.type = "button";
    btn.textContent = "☰";
    btn.title = "Sessions";

    btn.style.position = "fixed";
    btn.style.top = "12px";
    btn.style.left = "12px";
    btn.style.width = "44px";
    btn.style.height = "44px";
    btn.style.borderRadius = "999px";
    btn.style.zIndex = "10000";
    btn.style.background = "rgba(124,92,255,.95)";
    btn.style.color = "#ffffff";
    btn.style.border = "1px solid rgba(255,255,255,.25)";
    btn.style.fontSize = "22px";
    btn.style.display = "flex";
    btn.style.alignItems = "center";
    btn.style.justifyContent = "center";

    document.body.appendChild(btn);

    return btn;
}

    function wire() {
        const input = $("nova-mobile-input");
        const send = $("nova-mobile-send");
        const attach = $("mobileAttachBtn");
        const upload = $("nova-mobile-upload-input");
        const newSession = $("nova-mobile-new-session");
        const newTop = $("nova-mobile-new-chat");
        const sessionsToggle = findSessionsToggle();
        // NOVA_MOBILE_APP_SESSION_TOGGLE_DELEGATE_20260608
        // Session panel is owned by static/js/mobile/nova-mobile-sessions.js.

        if (!input || !send) return false;

        const stop = ensureButton("nova-mobile-stop", "■", "Stop");
        const voice = ensureButton("nova-mobile-voice", "🎙", "Voice");
        const tts = ensureButton("nova-mobile-tts", "🔊", "Speak");

        // NOVA_MOBILE_APP_CORE_HANDLERS_DELEGATED_20260608
        // Send button and input Enter key are owned by static/js/mobile/nova-mobile-events.js.

        if (stop) stop.onclick = stopEverything;
        if (tts) tts.onclick = speakLatest;
        // NOVA_MOBILE_APP_NEW_SESSION_DELEGATED_20260608
        // New session click ownership lives in static/js/mobile/nova-mobile-events.js.

        // NOVA_MOBILE_APP_SESSIONS_TOGGLE_DELEGATED_20260608
        // Sessions toggle click ownership lives in static/js/mobile/nova-mobile-events.js.

        // NOVA_MOBILE_APP_REMOVED_APP_OWNED_UPLOAD_PATH_20260608
        // Upload picker/upload storage is owned by static/js/mobile/nova-mobile-upload.js
        // and static/js/mobile/nova-mobile-attachment-payload.js.

        window.NovaMobileAppSend = sendText;
        window.NovaMobileSendMessage = sendText;
        window.NovaMobileStop = stopEverything;
        window.NovaMobileSpeak = speakLatest;
        if (!window.__NovaMobileSendFallbackBound) {
            window.__NovaMobileSendFallbackBound = true;

            document.addEventListener("click", function (event) {
                const target = event.target && event.target.closest
                    ? event.target.closest("#nova-mobile-send, [data-nova-mobile-send], [data-mobile-send], .nova-mobile-send-button")
                    : null;

                if (!target) return;

                event.preventDefault();
                event.stopPropagation();
sendText();
            }, true);

            document.addEventListener("keydown", function (event) {
                const target = event.target;
                const isInput =
                    target &&
                    (
                        target.id === "nova-mobile-input" ||
                        target.matches?.("#nova-mobile-input, textarea, [contenteditable='true']")
                    );

                if (!isInput) return;
                if (event.key !== "Enter" || event.shiftKey) return;

                event.preventDefault();
                event.stopPropagation();
sendText();
            }, true);
}
        // NOVA_MOBILE_APP_SESSION_DELEGATE_20260608
        // Session opening is owned by static/js/mobile/nova-mobile-sessions.js.
        if (window.NovaMobileSessions && typeof window.NovaMobileSessions.wire === "function") {
            try {
                window.NovaMobileSessions.wire();
            } catch (error) {
                console.warn("[Nova Mobile] session module wire failed", error);
            }
        }

        if (!window.NovaOpenMobileSessions && typeof window.NovaMobileOpenSessions === "function") {
            window.NovaOpenMobileSessions = window.NovaMobileOpenSessions;
        }

        updateActiveSessionTitle();
        scrollBottom();

        console.log("[Nova Mobile SMFF] sessions deferred to module");
        return true;
    }

    function boot() {
        let tries = 0;

        const timer = setInterval(function () {

            tries += 1;

            if (wire() || tries > 50) {
                clearInterval(timer);

                if (tries > 50) {
                    console.warn("[Nova Mobile SMFF] failed to wire required elements");
                }
            }
        }, 100);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();






























/* NOVA_MOBILE_APP_REMOVED_FETCH_CLEAR_AFTER_SEND_WRAPPER_20260608 - duplicate global fetch clearing removed. sendText() and static/js/mobile/nova-mobile-attachment-preview.js own clearing. */

/* NOVA_MOBILE_APP_REMOVED_DUPLICATE_ATTACHMENT_PAYLOAD_BRIDGE_20260608 - ownership lives in static/js/mobile/nova-mobile-attachment-payload.js */



/* NOVA_MOBILE_APP_REMOVED_DUPLICATE_UPLOAD_RESPONSE_CAPTURE_BRIDGE_20260608 - ownership lives in static/js/mobile/nova-mobile-attachment-payload.js */








/* NOVA_MOBILE_APP_REMOVED_DEAD_SESSION_BRIDGE_FRAGMENT_20260608 - dead addSessionBubble-only fragment removed. Session module owns session behavior. */\n