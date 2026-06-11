/* NOVA_MOBILE_SMFF_SESSIONS_STABLE_20260606 */

(function () {
    "use strict";

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

    function ensurePreviewBar() {
        let bar = $("nova-mobile-attachment-preview-bar");
        const composer = $("nova-mobile-composer");

        if (bar) return bar;
        if (!composer || !composer.parentNode) return null;

        bar = document.createElement("div");
        bar.id = "nova-mobile-attachment-preview-bar";
        bar.style.position = "fixed";
        bar.style.left = "8px";
        bar.style.right = "8px";
        bar.style.bottom = "124px";
        bar.style.zIndex = "45";
        bar.style.display = "none";
        bar.style.gap = "6px";
        bar.style.overflowX = "auto";
        bar.style.padding = "6px";
        bar.style.borderRadius = "14px";
        bar.style.background = "rgba(11,16,32,.96)";
        bar.style.border = "1px solid rgba(255,255,255,.14)";
        bar.style.color = "#f8fafc";
        bar.style.fontSize = "12px";

        composer.parentNode.appendChild(bar);
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

        state.pendingAttachments.forEach(function (fileData, index) {
            const item = document.createElement("button");
            const isImage = String(fileData.mime_type || "").startsWith("image/");
            const fileUrl = fileData.url || fileData.file_url || "";
            const fileName = fileData.original_filename || fileData.filename || "attachment";

            item.type = "button";

            if (isImage && fileUrl) {
                item.innerHTML =
                    '<img src="' +
                    fileUrl +
                    '" style="width:48px;height:48px;object-fit:cover;border-radius:8px;margin-right:8px;vertical-align:middle;"> ' +
                    fileName +
                    " ×";
            } else {
                item.textContent = "📎 " + fileName + " ×";
            }

            item.style.flex = "0 0 auto";
            item.style.maxWidth = "260px";
            item.style.overflow = "hidden";
            item.style.textOverflow = "ellipsis";
            item.style.whiteSpace = "nowrap";
            item.style.padding = "8px 10px";
            item.style.borderRadius = "999px";
            item.style.background = "rgba(124,92,255,.28)";
            item.style.border = "1px solid rgba(255,255,255,.14)";
            item.style.color = "#f8fafc";

            item.onclick = function () {
                state.pendingAttachments.splice(index, 1);
                renderAttachmentPreviews();
            };

            bar.appendChild(item);
        });
    }

    function addBubble(role, text) {
        const box = chatBox();
        if (!box) return null;

        const cleanText = String(text || "").trim();

        if (
            cleanText.startsWith("Attachment analysis:") ||
            cleanText.includes("This attachment appears to contain") ||
            cleanText.includes("extracted image/PDF content") ||
            cleanText.includes("[Attachment analysis failed:")
        ) {
            console.warn("[Nova Mobile] hidden noisy attachment analysis bubble");
            return null;
        }

        const bubble = document.createElement("div");
        bubble.dataset.role = role;
        bubble.style.margin = role === "user" ? "10px 0 10px auto" : "10px auto 10px 0";
        bubble.style.maxWidth = "90%";
        bubble.style.padding = "12px 14px";
        bubble.style.borderRadius = "16px";
        bubble.style.whiteSpace = "pre-wrap";
        bubble.style.background = role === "user" ? "rgba(124,92,255,.28)" : "rgba(255,255,255,.10)";
        bubble.style.color = "#f8fafc";

        if (isImageUrl(text)) {
            const img = document.createElement("img");
            img.src = String(text || "").trim();
            img.loading = "lazy";
            img.className = "nova-chat-image";
            img.style.display = "block";
            img.style.maxWidth = "100%";
            img.style.borderRadius = "12px";
            img.style.marginTop = "4px";
            bubble.appendChild(img);
        } else {
            bubble.textContent = text || "";
        }

        box.appendChild(bubble);
        scrollBottom();

        return bubble;
    }

    function latestAssistantText() {
        const box = chatBox();
        if (!box) return "";

        const nodes = Array.from(box.querySelectorAll("[data-role='assistant']"));
        const last = nodes[nodes.length - 1];

        return last ? String(last.textContent || "").trim() : "";
    }

    async function sendText(textOverride) {
        const input = $("nova-mobile-input");
        const text = String(textOverride || (input ? input.value : "") || "").trim();
        const attachments = state.pendingAttachments.slice();
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

        state.pendingAttachments = [];
        renderAttachmentPreviews();

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

// NOVA_FORCE_JSON_NEWS_CARDS_20260609
window.__lastNovaPayload = data;

if (
    data &&
    data.assistant_message &&
    data.assistant_message.meta &&
    (
        Array.isArray(data.assistant_message.meta.sources) ||
        Array.isArray(data.assistant_message.meta.source_urls)
    )
) {
    if (typeof window.renderWebSourcesFromPayload === "function") {
        window.renderWebSourcesFromPayload(data);
    } else {
        console.warn("[Nova Mobile Sources] renderWebSourcesFromPayload missing on JSON send");
    }
}

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
                    renderAttachmentPreviews();
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
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

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

            if (state.cachedMessages[session.id]) {
                box.innerHTML = state.cachedMessages[session.id];
            } else {
                try {
                    const res = await fetch("/api/sessions/" + encodeURIComponent(session.id));
                    const sessionData = await res.json();
                    const messages = Array.isArray(sessionData.messages) ? sessionData.messages : [];

                    messages.forEach(function (msg) {
                        addBubble(msg.role || "assistant", msg.text || msg.content || "");
                    });
                } catch (err) {
                    addBubble("assistant", "Failed to load session messages.");
                }
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
                    newChat();
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
const attach =
    $("mobileAttachBtn") ||
    $("nova-mobile-attach");

const upload =
    $("nova-mobile-upload-input") ||
    $("nova-mobile-file-input");
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

        window.NovaMobileAppSend = sendText;
        window.NovaMobileSendMessage = sendText;
        window.NovaMobileStop = stopEverything;
        window.NovaMobileSpeak = speakLatest;
        window.NovaMobileOpenSessions = function () {
            openSessionsPanel(sessionsPanel);
            loadSessionsPanel(sessionsPanel);
        };

        ensurePreviewBar();
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
        boot()
    }
})();











