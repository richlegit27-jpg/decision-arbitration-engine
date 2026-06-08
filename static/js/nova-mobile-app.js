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
                        try { state.pendingAttachments = []; } catch (e) {}
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
        // NOVA_MOBILE_CLEAR_PREVIEW_AFTER_SEND_SAFE_20260607
        try {
            localStorage.setItem("nova_mobile_pending_attachments", "[]");

            if (window.NovaMobileState && Array.isArray(window.NovaMobileState.pendingAttachments)) {
                window.NovaMobileState.pendingAttachments = [];
            }

            if (typeof window.NovaMobileClearAttachmentPreviews === "function") {
                window.NovaMobileClearAttachmentPreviews();
            } else if (typeof window.NovaRenderComposerInlinePreview === "function") {
                window.NovaRenderComposerInlinePreview();
            } else if (typeof window.renderAttachmentPreviews === "function") {
                window.renderAttachmentPreviews();
            }
        } catch (error) {
            console.warn("[Nova Mobile] failed to clear attachment previews after send", error);
        }
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

    async function uploadFiles(files) {
        for (const file of files) {
            const form = new FormData();
            form.append("file", file);

            try {
                const response = await fetch("/api/upload", {
                    method: "POST",
                    body: form
                });

                const data = await response.json();

                if (data && data.ok) {
                    state.pendingAttachments.push(data);
                    if (typeof window.NovaRenderComposerInlinePreview === "function") {
            window.NovaRenderComposerInlinePreview();
        }
                    console.log("[Nova Mobile Final] attachment ready", data);
                }
            } catch (error) {
                console.error("[Nova Mobile Final] upload failed", error);
            }
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

    function startVoice() {
        const input = $("nova-mobile-input");
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!input || !SpeechRecognition) {
            addBubble("assistant", "Voice is not supported in this browser.");
            return;
        }

        const rec = new SpeechRecognition();
        state.recognition = rec;

        rec.lang = "en-US";
        rec.interimResults = false;
        rec.maxAlternatives = 1;

        rec.onresult = function (event) {
            const text = event.results?.[0]?.[0]?.transcript || "";
            input.value = text;
            input.focus();
        };

        rec.onerror = function (event) {
            addBubble("assistant", "Voice failed: " + (event.error || "unknown error"));
        };

        rec.start();
    }

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

    function ensureSessionsPanel() {
        let panel = $("nova-mobile-sessions-panel");

        if (panel) {
            return panel;
        }

        panel = document.createElement("div");
        panel.id = "nova-mobile-sessions-panel";
        panel.className = "hidden";
        panel.style.display = "none";

        document.body.appendChild(panel);

        return panel;
    }

function openSessionsPanel(panel) {
    if (!panel) return;

    panel.classList.remove("hidden");

    panel.setAttribute(
        "style",
        [
            "display:block !important",
            "visibility:visible !important",
            "opacity:1 !important",
            "position:fixed !important",
            "top:60px !important",
            "left:10px !important",
            "right:10px !important",
            "bottom:80px !important",
            "overflow-y:auto !important",
            "z-index:2147483647 !important",
            "background:rgba(11,16,32,.98) !important",
            "border:2px solid rgba(124,92,255,.95) !important",
            "border-radius:16px !important",
            "padding:10px !important",
            "color:#f8fafc !important",
            "box-shadow:0 20px 60px rgba(0,0,0,.65) !important"
        ].join(";")
    );
}

function closeSessionsPanel(panel) {
    if (!panel) return;

    panel.style.setProperty("display", "none", "important");
    panel.classList.add("hidden");
}

    function createSessionRow(session, sessionsPanel) {
        const row = document.createElement("div");
        row.style.display = "flex";
        row.style.gap = "6px";
        row.style.marginBottom = "6px";
        row.style.background = "rgba(255,255,255,.06)";
        row.style.border = "1px solid rgba(255,255,255,.14)";
        row.style.borderRadius = "12px";
        row.style.padding = "6px";

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "mobile-session-item";
        btn.style.flex = "1";
        btn.style.color = "#f8fafc";
        btn.style.background = "rgba(124,92,255,.22)";
        btn.style.border = "1px solid rgba(255,255,255,.16)";
        btn.style.borderRadius = "10px";
        btn.style.padding = "10px";
        btn.style.textAlign = "left";

        const pinBtn = document.createElement("button");
        pinBtn.type = "button";
        pinBtn.textContent = session.pinned ? "📌" : "📍";
        pinBtn.title = "Pin session";
        pinBtn.style.width = "42px";
        pinBtn.style.flex = "0 0 42px";
        pinBtn.style.color = "#f8fafc";
        pinBtn.style.background = "rgba(124,92,255,.35)";
        pinBtn.style.border = "1px solid rgba(255,255,255,.16)";
        pinBtn.style.borderRadius = "10px";

        const renameBtn = document.createElement("button");
        renameBtn.type = "button";
        renameBtn.textContent = "✏";
        renameBtn.title = "Rename session";
        renameBtn.style.width = "42px";
        renameBtn.style.flex = "0 0 42px";
        renameBtn.style.color = "#f8fafc";
        renameBtn.style.background = "rgba(124,92,255,.45)";
        renameBtn.style.border = "1px solid rgba(255,255,255,.16)";
        renameBtn.style.borderRadius = "10px";

        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.textContent = "🗑";
        deleteBtn.title = "Delete session";
        deleteBtn.style.width = "42px";
        deleteBtn.style.flex = "0 0 42px";
        deleteBtn.style.color = "#f8fafc";
        deleteBtn.style.background = "rgba(255,80,80,.35)";
        deleteBtn.style.border = "1px solid rgba(255,255,255,.16)";
        deleteBtn.style.borderRadius = "10px";

        const shortId = String(session.id || "").slice(-6);

        function currentTitle() {
            return (
                (state.sessionTitles && state.sessionTitles[session.id]) ||
                session.title ||
                "New Chat"
            );
        }

        function renderTitle() {
            const pinnedText = session.pinned ? "📌 " : "";
            btn.textContent = pinnedText + currentTitle() + " · " + shortId;
            pinBtn.textContent = session.pinned ? "📌" : "📍";
        }

        renderTitle();

        btn.onclick = async function () {
            const currentSessionId = getSessionId();
            const box = chatBox();

            if (currentSessionId && box) {
                state.cachedMessages[currentSessionId] = box.innerHTML;
            }

            localStorage.setItem("nova_mobile_active_session_id", session.id);
            updateActiveSessionTitle(session);

            if (!box) return;

            box.innerHTML = "";
            delete state.cachedMessages[session.id];

            try {
                const res = await fetch("/api/chat/" + encodeURIComponent(session.id));
                const sessionData = await res.json();
                const messages =
                    Array.isArray(sessionData.messages) ? sessionData.messages :
                    Array.isArray(sessionData.session && sessionData.session.messages) ? sessionData.session.messages :
                    Array.isArray(sessionData.data && sessionData.data.messages) ? sessionData.data.messages :
                    [];

                if (!messages.length) {
                    addBubble("assistant", "No saved messages found for this session.");
                }

                messages.forEach(function (msg) {
                    addBubble(msg.role || "assistant", msg.text || msg.content || "");
                });
            } catch (err) {
                console.error("[Nova Mobile] failed to restore session", err);
                addBubble("assistant", "Failed to load session messages.");
            }

            closeSessionsPanel(sessionsPanel);
            scrollBottom();
        };

        pinBtn.onclick = async function (event) {
            event.preventDefault();
            event.stopPropagation();

            const nextPinned = !session.pinned;

            try {
                const response = await fetch("/api/sessions/pin", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        session_id: session.id,
                        pinned: nextPinned
                    })
                });

                if (!response.ok) {
                    throw new Error("Pin failed with HTTP " + response.status);
                }

                session.pinned = nextPinned;
                renderTitle();
                loadSessionsPanel(sessionsPanel);
            } catch (err) {
                alert("Pin failed");
            }
        };

        renameBtn.onclick = async function (event) {
            event.preventDefault();
            event.stopPropagation();

            const newTitle = prompt("Rename session:", currentTitle());

            if (!newTitle) return;

            try {
                const response = await fetch("/api/sessions/rename", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        session_id: session.id,
                        title: newTitle
                    })
                });

                if (!response.ok) {
                    throw new Error("Rename failed with HTTP " + response.status);
                }

                session.title = newTitle;
                state.sessionTitles[session.id] = newTitle;
                renderTitle();

                if (getSessionId() === session.id) {
                    updateActiveSessionTitle({ id: session.id, title: newTitle });
                }
            } catch (err) {
                alert("Rename failed");
            }
        };

        deleteBtn.onclick = async function (event) {
            event.preventDefault();
            event.stopPropagation();

            const title = currentTitle();
            const ok = confirm("Delete session: " + title + "?");

            if (!ok) return;

            try {
                const response = await fetch("/api/sessions/delete", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        session_id: session.id
                    })
                });

                if (!response.ok) {
                    throw new Error("Delete failed with HTTP " + response.status);
                }

                delete state.cachedMessages[session.id];
                delete state.sessionTitles[session.id];

                if (getSessionId() === session.id) {
                    localStorage.removeItem("nova_mobile_active_session_id");
                    if (box) {
                        box.innerHTML = "";
                    }
                    updateActiveSessionTitle({
                        id: "",
                        title: "No active session"
                    });
                }

                loadSessionsPanel(sessionsPanel);
            } catch (err) {
                alert("Delete failed");
            }
        };

        row.appendChild(btn);
        row.appendChild(pinBtn);
        row.appendChild(renameBtn);
        row.appendChild(deleteBtn);

        return row;
    }

    async function loadSessionsPanel(sessionsPanel) {
        if (!sessionsPanel) return;

        sessionsPanel.innerHTML = "";

        const closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.className = "mobile-session-item";
        closeBtn.textContent = "Close Sessions";
        closeBtn.style.marginBottom = "10px";
        closeBtn.onclick = function () {
            closeSessionsPanel(sessionsPanel);
        };
        sessionsPanel.appendChild(closeBtn);

        try {
            const response = await fetch("/api/sessions");
            const data = await response.json();

            const sessions = (Array.isArray(data.sessions) ? data.sessions : [])
                .filter(function (session) {
                    return session && session.id;
                })

.sort(function (a, b) {
    if (!!a.pinned !== !!b.pinned) {
        return a.pinned ? -1 : 1;
    }

    const aTime = Date.parse(a.updated_at || a.created_at || "") || 0;
    const bTime = Date.parse(b.updated_at || b.created_at || "") || 0;

    return bTime - aTime;
})

                .slice(0, 25);

            console.log("[Nova Mobile Sessions]", sessions);

            if (!sessions.length) {
                addBubble("assistant", "No saved sessions found yet.");
                return;
            }

            sessions.forEach(function (session) {
                sessionsPanel.appendChild(createSessionRow(session, sessionsPanel));
            });
        } catch (error) {
            const err = document.createElement("button");
            err.type = "button";
            err.className = "mobile-session-item";
            err.textContent = "Failed to load sessions";
            sessionsPanel.appendChild(err);
        }
    }

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
        const sessionsPanel = ensureSessionsPanel();

        if (!input || !send) return false;

        const stop = ensureButton("nova-mobile-stop", "■", "Stop");
        const voice = ensureButton("nova-mobile-voice", "🎙", "Voice");
        const tts = ensureButton("nova-mobile-tts", "🔊", "Speak");

        send.onclick = function (event) {
            event.preventDefault();
            event.stopPropagation();
            sendText();
        };

        input.onkeydown = function (event) {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                sendText();
            }
        };

        if (attach && upload) {
            attach.onclick = function (event) {
                event.preventDefault();
                upload.click();
            };

            upload.onchange = async function () {
                const files = Array.from(upload.files || []);
                if (!files.length) return;

                await uploadFiles(files);
                upload.value = "";
            };
        }

        if (stop) stop.onclick = stopEverything;
        if (voice) voice.onclick = startVoice;
        if (tts) tts.onclick = speakLatest;
        if (newSession) newSession.onclick = newChat;
        if (newTop) newTop.onclick = newChat;

        if (sessionsToggle) {
            sessionsToggle.onclick = function (event) {
                event.preventDefault();
                event.stopPropagation();

                const isOpen =
                    sessionsPanel.style.display === "block" &&
                    !sessionsPanel.classList.contains("hidden");

                if (isOpen) {
                    closeSessionsPanel(sessionsPanel);
                    return;
                }

                openSessionsPanel(sessionsPanel);
                loadSessionsPanel(sessionsPanel);
            };
        } else {
            console.warn("[Nova Mobile Sessions] toggle button missing");
        }


        // UPLOAD_STORE_BRIDGE_LOCK_20260606
        // Keep uploaded files in the same stores sendText() reads.
        function novaStorePendingUploadAttachment(raw) {
            const source =
                raw && raw.attachment ? raw.attachment :
                raw && raw.file ? raw.file :
                raw && raw.data ? raw.data :
                raw;

            if (!source || typeof source !== "object") return null;

            const attachment = {
                ok: source.ok !== false,
                filename: source.filename || source.stored_name || source.name || source.original_filename || "",
                original_filename: source.original_filename || source.name || source.filename || "",
                mime_type: source.mime_type || source.type || "",
                type: source.type || source.mime_type || "",
                url: source.url || source.file_url || "",
                file_url: source.file_url || source.url || "",
                size: source.size || 0,
                name: source.name || source.original_filename || source.filename || "attachment"
            };

            if (!attachment.url && !attachment.filename && !attachment.name) {
                return null;
            }

            function merge(items, item) {
                const list = Array.isArray(items) ? items.slice() : [];
                const key = item.url || item.file_url || item.filename || item.name;

                const exists = list.some(function (existing) {
                    const existingKey = existing && (existing.url || existing.file_url || existing.filename || existing.name);
                    return existingKey && existingKey === key;
                });

                if (!exists) {
                    list.push(item);
                }

                return list;
            }

            window.NovaMobileSharedAttachments = merge(window.NovaMobileSharedAttachments, attachment);

            try {
                state.pendingAttachments = merge(state.pendingAttachments, attachment);
            } catch (_) {}

            try {
                const pending = merge(
                    JSON.parse(localStorage.getItem("nova_mobile_pending_attachments") || "[]"),
                    attachment
                );

                localStorage.setItem("nova_mobile_pending_attachments", JSON.stringify(pending));
                localStorage.setItem("nova_mobile_latest_attachments", JSON.stringify(pending));
            } catch (_) {}

            if (typeof window.NovaRenderComposerInlinePreview === "function") {
                window.NovaRenderComposerInlinePreview();
            }

            return attachment;
        }

        if (!window.__NovaMobileUploadStoreBridgeBound) {
            window.__NovaMobileUploadStoreBridgeBound = true;

            window.addEventListener("nova-mobile-upload-complete", function (event) {
                novaStorePendingUploadAttachment(event && event.detail ? event.detail : {});
            });

            window.NovaMobileStorePendingUploadAttachment = novaStorePendingUploadAttachment;
        }

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
        window.NovaMobileOpenSessions = function () {
            openSessionsPanel(sessionsPanel);
            loadSessionsPanel(sessionsPanel);
        };

        updateActiveSessionTitle();
        scrollBottom();

        console.log("[Nova Mobile SMFF] sessions stable wired");
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






























/* NOVA_MOBILE_UI_MEDIA_SANITIZER_20260607 */
(function () {
    "use strict";

    function sanitizeOversizedMedia() {
        document.querySelectorAll("img, video, iframe").forEach(function (node) {
            var rect = node.getBoundingClientRect ? node.getBoundingClientRect() : null;

            if (!rect) {
                return;
            }

            if (rect.width > window.innerWidth * 0.96 || rect.height > 420) {
                node.style.maxWidth = "340px";
                node.style.maxHeight = "280px";
                node.style.objectFit = "contain";
                node.style.borderRadius = "14px";
                node.style.overflow = "hidden";
            }
        });
    }

    var observer = new MutationObserver(function () {
        sanitizeOversizedMedia();
    });

    document.addEventListener("DOMContentLoaded", function () {
        sanitizeOversizedMedia();

        if (document.body) {
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    });

    window.NovaMobileSanitizeOversizedMedia = sanitizeOversizedMedia;

    console.log("[Nova Mobile UI] media sanitizer ready");
})();


/* NOVA_MOBILE_FETCH_CLEAR_AFTER_SEND_LOCK_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileFetchClearAfterSendInstalled) {
        return;
    }

    window.NovaMobileFetchClearAfterSendInstalled = true;

    var originalFetch = window.fetch;

    function clearPendingAttachmentsAfterSend() {
        try {
            localStorage.setItem("nova_mobile_pending_attachments", "[]");
            localStorage.setItem("nova_pending_attachments", "[]");

            if (window.NovaMobileState && Array.isArray(window.NovaMobileState.pendingAttachments)) {
                window.NovaMobileState.pendingAttachments = [];
            }

            if (typeof window.NovaMobileClearAttachmentPreviews === "function") {
                window.NovaMobileClearAttachmentPreviews();
            } else if (typeof window.NovaRenderComposerInlinePreview === "function") {
                window.NovaRenderComposerInlinePreview();
            } else if (typeof window.renderAttachmentPreviews === "function") {
                window.renderAttachmentPreviews();
            }

            document.querySelectorAll(
                "#nova-mobile-attachment-preview, " +
                "#nova-mobile-attachment-preview-bottom, " +
                ".nova-mobile-attachment-preview, " +
                "[data-attachment-preview], " +
                "[data-attachment-preview-bottom]"
            ).forEach(function (node) {
                node.innerHTML = "";
                node.style.display = "none";
            });
        } catch (error) {
            console.warn("[Nova Mobile] fetch clear-after-send failed", error);
        }
    }

    window.fetch = function () {
        var args = Array.prototype.slice.call(arguments);
        var input = args[0];
        var init = args[1] || {};
        var url = "";

        try {
            if (typeof input === "string") {
                url = input;
            } else if (input && input.url) {
                url = input.url;
            }
        } catch (error) {
            url = "";
        }

        var method = String(init.method || "GET").toUpperCase();
        var isChatSend = method === "POST" && (
            url.indexOf("/api/chat") !== -1 ||
            url.indexOf("/api/chat/stream") !== -1
        );

        var result = originalFetch.apply(this, args);

        if (isChatSend) {
            setTimeout(clearPendingAttachmentsAfterSend, 0);
        }

        return result;
    };

    window.NovaMobileForceClearPendingAttachments = clearPendingAttachmentsAfterSend;

    console.log("[Nova Mobile] fetch clear-after-send lock ready");
})();


/* NOVA_MOBILE_COMPOSER_AUTORE_SIZE_JS_20260607 */
(function () {
    "use strict";

    var inputEl = document.getElementById("nova-mobile-input") || document.querySelector(".nova-mobile-input");

    if (!inputEl) return;

    function autoResizeInput() {
        inputEl.style.height = "36px";
        inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + "px";
    }

    inputEl.addEventListener("input", autoResizeInput, false);
    inputEl.addEventListener("focus", autoResizeInput, false);
    inputEl.addEventListener("blur", autoResizeInput, false);

    window.NovaMobileAutoResizeComposer = autoResizeInput;

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(autoResizeInput, 0);
    });

    console.log("[Nova Mobile] composer auto-resize ready");
})();


/* NOVA_MOBILE_SEND_BUTTON_STATE_LOCK_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileSendButtonStateInstalled) {
        return;
    }

    window.NovaMobileSendButtonStateInstalled = true;

    function safeJson(value, fallback) {
        try {
            return value ? JSON.parse(value) : fallback;
        } catch (error) {
            return fallback;
        }
    }

    function getInput() {
        return document.getElementById("nova-mobile-input") ||
            document.querySelector(".nova-mobile-input") ||
            document.querySelector("textarea") ||
            document.querySelector("input[type='text']");
    }

    function getSendButton() {
        return document.getElementById("nova-mobile-send") ||
            document.getElementById("mobileSendBtn") ||
            document.querySelector("[data-mobile-send]") ||
            document.querySelector(".nova-mobile-send") ||
            document.querySelector(".send-button");
    }

    function getPendingAttachmentCount() {
        if (window.NovaMobileState && Array.isArray(window.NovaMobileState.pendingAttachments)) {
            return window.NovaMobileState.pendingAttachments.length;
        }

        var stored = safeJson(localStorage.getItem("nova_mobile_pending_attachments"), []);
        return Array.isArray(stored) ? stored.length : 0;
    }

    function updateSendButtonState() {
        var input = getInput();
        var send = getSendButton();

        if (!send) {
            return;
        }

        var text = input ? String(input.value || "").trim() : "";
        var hasAttachments = getPendingAttachmentCount() > 0;
        var canSend = Boolean(text || hasAttachments);

        send.disabled = !canSend;
        send.classList.toggle("nova-mobile-send-disabled", !canSend);
        send.setAttribute("aria-disabled", canSend ? "false" : "true");
    }

    function bind() {
        var input = getInput();

        if (input && input.getAttribute("data-send-state-bound") !== "true") {
            input.setAttribute("data-send-state-bound", "true");
            input.addEventListener("input", updateSendButtonState);
            input.addEventListener("keyup", updateSendButtonState);
            input.addEventListener("change", updateSendButtonState);
        }

        updateSendButtonState();
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(bind, 0);
        setTimeout(bind, 250);
    });

    window.addEventListener("nova-mobile-upload-complete", updateSendButtonState);
    window.addEventListener("nova-mobile-attachments-changed", updateSendButtonState);
    window.addEventListener("nova-mobile-attachments-cleared", updateSendButtonState);

    document.addEventListener("click", function () {
        setTimeout(updateSendButtonState, 0);
    }, true);

    window.NovaMobileUpdateSendButtonState = updateSendButtonState;

    console.log("[Nova Mobile] send button state lock ready");
})();


/* NOVA_MOBILE_WHITE_BLOB_CLEANUP_JS_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileWhiteBlobCleanupInstalled) {
        return;
    }

    window.NovaMobileWhiteBlobCleanupInstalled = true;

    function looksLikeGiantBlankMedia(node) {
        if (!node || !node.getBoundingClientRect) {
            return false;
        }

        var rect = node.getBoundingClientRect();
        var tag = String(node.tagName || "").toLowerCase();

        if (!["img", "video", "canvas", "iframe"].includes(tag)) {
            return false;
        }

        if (rect.width > window.innerWidth * 0.95 || rect.height > 420) {
            return true;
        }

        return false;
    }

    function cleanupWhiteBlobs() {
        document.querySelectorAll("img, video, canvas, iframe").forEach(function (node) {
            if (!looksLikeGiantBlankMedia(node)) {
                return;
            }

            node.style.maxWidth = "320px";
            node.style.maxHeight = "240px";
            node.style.width = "auto";
            node.style.height = "auto";
            node.style.objectFit = "contain";
            node.style.borderRadius = "12px";
            node.style.overflow = "hidden";
        });

        document.querySelectorAll("[class*='blob'], [class*='glow'], [class*='orb'], [class*='splash']").forEach(function (node) {
            if (!node || !node.getBoundingClientRect) {
                return;
            }

            var rect = node.getBoundingClientRect();

            if (rect.width > window.innerWidth * 1.2 || rect.height > window.innerHeight * 1.2) {
                node.style.maxWidth = "100vw";
                node.style.maxHeight = "100vh";
                node.style.overflow = "hidden";
                node.style.pointerEvents = "none";
                node.style.zIndex = "0";
            }
        });
    }

    var observer = new MutationObserver(function () {
        window.requestAnimationFrame(cleanupWhiteBlobs);
    });

    document.addEventListener("DOMContentLoaded", function () {
        cleanupWhiteBlobs();

        if (document.body) {
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ["style", "class", "src"]
            });
        }

        setInterval(cleanupWhiteBlobs, 1200);
    });

    window.NovaMobileCleanupWhiteBlobs = cleanupWhiteBlobs;

    console.log("[Nova Mobile UI] white blob cleanup ready");
})();


/* NOVA_MOBILE_RUNTIME_INPUT_HEIGHT_LOCK_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileRuntimeInputHeightLockInstalled) {
        return;
    }

    window.NovaMobileRuntimeInputHeightLockInstalled = true;

    function lockInputHeight() {
        var inputs = Array.from(document.querySelectorAll(
            "#mobileInput, " +
            "#mobileMessageInput, " +
            "#nova-mobile-input, " +
            "textarea#nova-mobile-input, " +
            "input#nova-mobile-input, " +
            ".mobile-composer textarea, " +
            ".mobile-composer input, " +
            ".nova-mobile-composer textarea, " +
            ".nova-mobile-composer input, " +
            ".composer textarea, " +
            ".composer input, " +
            ".chat-composer textarea, " +
            ".chat-composer input, " +
            "textarea[placeholder], " +
            "input[placeholder], " +
            "[contenteditable='true']"
        ));

        inputs.forEach(function (el) {
            el.style.setProperty("min-height", "44px", "important");
            el.style.setProperty("height", "44px", "important");
            el.style.setProperty("max-height", "110px", "important");
            el.style.setProperty("padding", "10px 14px", "important");
            el.style.setProperty("line-height", "1.35", "important");
            el.style.setProperty("font-size", "16px", "important");
            el.style.setProperty("border-radius", "16px", "important");
            el.style.setProperty("box-sizing", "border-box", "important");
            el.style.setProperty("resize", "none", "important");
        });

        var rows = Array.from(document.querySelectorAll(
            ".mobile-composer-inner, " +
            ".nova-mobile-composer-inner, " +
            ".composer-row, " +
            ".mobile-composer-actions, " +
            ".mobile-composer-buttons, " +
            "#nova-mobile-composer, " +
            ".mobile-composer, " +
            ".nova-mobile-composer, " +
            ".composer, " +
            ".chat-composer"
        ));

        rows.forEach(function (el) {
            el.style.setProperty("min-height", "54px", "important");
        });

        var buttons = Array.from(document.querySelectorAll(
            ".mobile-composer-btn, " +
            ".mobile-composer button, " +
            ".nova-mobile-composer button, " +
            "#nova-mobile-composer button, " +
            ".composer button, " +
            ".chat-composer button"
        ));

        buttons.forEach(function (button) {
            button.style.setProperty("width", "42px", "important");
            button.style.setProperty("min-width", "42px", "important");
            button.style.setProperty("max-width", "42px", "important");
            button.style.setProperty("height", "42px", "important");
            button.style.setProperty("min-height", "42px", "important");
            button.style.setProperty("max-height", "42px", "important");
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(lockInputHeight, 0);
        setTimeout(lockInputHeight, 250);
        setTimeout(lockInputHeight, 750);
    });

    document.addEventListener("input", function () {
        setTimeout(lockInputHeight, 0);
    }, true);

    window.addEventListener("resize", function () {
        setTimeout(lockInputHeight, 0);
    });

    window.NovaMobileLockInputHeight = lockInputHeight;

    console.log("[Nova Mobile] runtime input height lock ready");
})();


/* NOVA_MOBILE_RUNTIME_ICON_REPAIR_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileRuntimeIconRepairInstalled) {
        return;
    }

    window.NovaMobileRuntimeIconRepairInstalled = true;

    function setButtonIcon(id, html, label) {
        var button = document.getElementById(id);
        if (!button) {
            return;
        }

        button.innerHTML = html;
        button.setAttribute("aria-label", label);
        button.setAttribute("title", label);
    }

    function repairIcons() {
        setButtonIcon("nova-mobile-send", "&#10148;", "Send");
        setButtonIcon("nova-mobile-voice", "&#127908;", "Voice");
        setButtonIcon("nova-mobile-tts", "&#128266;", "Speak");
        setButtonIcon("nova-mobile-attach", "&#65291;", "Attach");
        setButtonIcon("nova-mobile-tools-toggle", "&#8943;", "Tools");

        var stopGeneration = document.getElementById("nova-mobile-stop-generation");
        if (stopGeneration) {
            stopGeneration.textContent = "Stop";
            stopGeneration.setAttribute("aria-label", "Stop generation");
            stopGeneration.setAttribute("title", "Stop generation");
        }

        var stopSpeech = document.getElementById("nova-mobile-stop-speech");
        if (stopSpeech) {
            stopSpeech.textContent = "Stop";
            stopSpeech.setAttribute("aria-label", "Stop speech");
            stopSpeech.setAttribute("title", "Stop speech");
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(repairIcons, 0);
        setTimeout(repairIcons, 250);
        setTimeout(repairIcons, 750);
    });

    window.addEventListener("load", function () {
        setTimeout(repairIcons, 0);
    });

    window.NovaMobileRepairIcons = repairIcons;

    console.log("[Nova Mobile] runtime icon repair ready");
})();



/* NOVA_MOBILE_COMPACT_INPUT_FINAL_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileCompactInputFinalInstalled) {
        return;
    }

    window.NovaMobileCompactInputFinalInstalled = true;

    function compactInputFinal() {
        var input = document.getElementById("nova-mobile-input");

        if (input) {
            input.style.setProperty("height", "40px", "important");
            input.style.setProperty("min-height", "40px", "important");
            input.style.setProperty("max-height", "90px", "important");
            input.style.setProperty("padding", "8px 12px", "important");
            input.style.setProperty("line-height", "1.25", "important");
            input.style.setProperty("font-size", "16px", "important");
            input.style.setProperty("border-radius", "14px", "important");
            input.style.setProperty("box-sizing", "border-box", "important");
            input.style.setProperty("resize", "none", "important");
            input.style.setProperty("overflow-y", "auto", "important");
        }

        [
            "nova-mobile-send",
            "nova-mobile-stop-generation",
            "nova-mobile-voice",
            "nova-mobile-stop-speech",
            "nova-mobile-tts",
            "nova-mobile-attach",
            "nova-mobile-tools-toggle"
        ].forEach(function (id) {
            var button = document.getElementById(id);
            if (!button) {
                return;
            }

            button.style.setProperty("width", "40px", "important");
            button.style.setProperty("min-width", "40px", "important");
            button.style.setProperty("max-width", "40px", "important");
            button.style.setProperty("height", "40px", "important");
            button.style.setProperty("min-height", "40px", "important");
            button.style.setProperty("max-height", "40px", "important");
            button.style.setProperty("flex", "0 0 40px", "important");
            button.style.setProperty("padding", "0", "important");
        });

        Array.from(document.querySelectorAll(
            ".mobile-composer-inner, .nova-mobile-composer-inner, .composer-row, .mobile-composer-actions, .mobile-composer-buttons"
        )).forEach(function (row) {
            row.style.setProperty("height", "48px", "important");
            row.style.setProperty("min-height", "48px", "important");
            row.style.setProperty("max-height", "48px", "important");
            row.style.setProperty("align-items", "center", "important");
        });

        Array.from(document.querySelectorAll(
            "#nova-mobile-composer, .mobile-composer, .nova-mobile-composer, .chat-composer, .composer"
        )).forEach(function (bar) {
            bar.style.setProperty("min-height", "52px", "important");
            bar.style.setProperty("max-height", "64px", "important");
            bar.style.setProperty("padding-top", "4px", "important");
            bar.style.setProperty("padding-bottom", "4px", "important");
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(compactInputFinal, 0);
        setTimeout(compactInputFinal, 250);
        setTimeout(compactInputFinal, 750);
        setTimeout(compactInputFinal, 1500);
    });

    document.addEventListener("input", function () {
        setTimeout(compactInputFinal, 0);
        setTimeout(compactInputFinal, 50);
    }, true);

    window.addEventListener("resize", function () {
        setTimeout(compactInputFinal, 0);
    });

    setInterval(compactInputFinal, 1000);

    window.NovaMobileCompactInputFinal = compactInputFinal;

    console.log("[Nova Mobile] compact input final ready");
})();
