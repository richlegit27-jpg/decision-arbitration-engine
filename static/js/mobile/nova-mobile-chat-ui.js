(function () {
    "use strict";

    function appendMessage(role, text, message) {
        if (!window.chatContainer) {
            return null;
        }

        const emptyState = window.chatContainer.querySelector(
            ".nova-mobile-empty-state"
        );

        if (emptyState) {
            emptyState.remove();
        }

        const wrapper = document.createElement("div");
        wrapper.className = "mobile-chat-message " + role;

        const content = document.createElement("div");
        content.className = "mobile-message-content";

        function renderBody(value) {
            if (window.NovaAnswerPayload && typeof window.NovaAnswerPayload.renderAnswerPayload === "function") {
                return window.NovaAnswerPayload.renderAnswerPayload(value || "", { messageId: message && message.id });
            }
            if (window.NovaMobileCore && typeof window.NovaMobileCore.renderMarkdown === "function") {
                return window.NovaMobileCore.renderMarkdown(value || "");
            }
            return window.NovaMobileCore && typeof window.NovaMobileCore.escapeHtml === "function"
                ? window.NovaMobileCore.escapeHtml(value || "")
                : String(value || "");
        }

        if (role === "assistant") {
            content.innerHTML = message && message.status === "tool_approval_required" && window.NovaAnswerPayload && typeof window.NovaAnswerPayload.renderToolApprovalCard === "function"
                ? window.NovaAnswerPayload.renderToolApprovalCard(message, window.__novaActiveSessionId || "")
                : renderBody(text);
        } else {
            content.textContent = text || "";
        }

        const videoStatus = String(message && message.meta && message.meta.video_status || "").toLowerCase();
        if (role === "assistant" && message && message.meta && message.meta.video_job_id && ["queued", "generating", "pending", "processing"].includes(videoStatus)) {
            const status = document.createElement("div");
            status.className = "nova-video-job-status";
            status.setAttribute("role", "status");
            status.textContent = videoStatus === "queued" ? "Video queued…" : "Generating your video…";
            content.prepend(status);
        }

        const attachments =
            message &&
            Array.isArray(message.attachments)
                ? message.attachments
                : [];

        if (
            message &&
            message.image_url &&
            !attachments.length
        ) {
            attachments.push({
                url: message.image_url,
                filename: "Generated image"
            });
        }

        attachments.forEach(function (attachment) {
            const mediaType = String(attachment && (attachment.type || attachment.kind || attachment.mime_type) || "").toLowerCase();
            const imageUrl = String(
                attachment &&
                (
                    attachment.url ||
                    attachment.image_url ||
                    ""
                )
            ).trim();

            if (!imageUrl) return;

            if (mediaType === "video" || mediaType.startsWith("video/")) {
                const videoCard = document.createElement("div");
                videoCard.className = "nova-media-card";
                const video = document.createElement("video");
                video.className = "nova-media-video";
                video.controls = true;
                video.preload = "metadata";
                const source = document.createElement("source");
                source.src = imageUrl;
                source.type = attachment.mime_type || "video/mp4";
                video.appendChild(source);
                const caption = document.createElement("div");
                caption.className = "nova-media-caption";
                caption.textContent = attachment.title || attachment.filename || "Generated video";
                videoCard.append(video, caption);
                content.appendChild(videoCard);
                return;
            }

            if (mediaType && !mediaType.startsWith("image/") && !mediaType.startsWith("video/") && (attachment.filename || attachment.name)) {
                let safeUrl = "";
                try {
                    const parsed = new URL(imageUrl, window.location.origin);
                    if (["http:", "https:"].includes(parsed.protocol)) safeUrl = parsed.href;
                } catch (_error) {}
                if (safeUrl) {
                    const fileCard = document.createElement("div");
                    fileCard.className = "nova-mobile-artifact-message-card";
                    const filename = document.createElement("span");
                    filename.className = "nova-mobile-artifact-filename";
                    filename.textContent = attachment.filename || attachment.name;
                    const open = document.createElement("a");
                    open.href = safeUrl;
                    open.target = "_blank";
                    open.rel = "noopener noreferrer";
                    open.textContent = "Open file";
                    fileCard.append(filename, open);
                    content.appendChild(fileCard);
                }
                return;
            }

            if (
                !window.NovaMobileImages ||
                typeof window.NovaMobileImages
                    .renderImageIntoBubble !== "function"
            ) {
                return;
            }

            const imageHost =
                document.createElement("div");

            imageHost.className =
                "mobile-message-image-host";

            content.appendChild(imageHost);

            window.NovaMobileImages
                .renderImageIntoBubble(
                    imageHost,
                    imageUrl,
                    attachment.filename ||
                    attachment.name ||
                    "Generated image"
                );
        });

        wrapper.appendChild(content);
        window.chatContainer.appendChild(wrapper);

        if (
            role !== "system" &&
            !window.__NOVA_SESSION_RENDERING__ &&
            !window.__NOVA_SUPPRESS_SAVE
        ) {
            setTimeout(function () {
                if (
                    window.NovaMobileBridge &&
                    typeof window.NovaMobileBridge.saveCurrentMessages === "function"
                ) {
                    window.NovaMobileBridge.saveCurrentMessages();
                    return;
                }

                if (typeof window.saveCurrentMessages === "function") {
                    window.saveCurrentMessages();
                }
            }, 0);
        }

        return wrapper;
    }

    function createThinkingBubble(label) {
        const bubble = appendMessage("assistant", "");

        if (!bubble && window.__NOVA_SESSION_RENDERING__) {
            return null;
        }

        if (!bubble) {
            return null;
        }

        bubble.classList.add("mobile-thinking-bubble");

        const content = bubble.querySelector(".mobile-message-content");

        if (content) {
            content.innerHTML = `
                <span class="nova-typing-label">${label || "Nova is thinking"}</span>
                <span class="nova-typing-dots">
                    <span></span><span></span><span></span>
                </span>
            `;
        }

        return bubble;
    }

    function updateThinkingBubble(bubble, text) {
        if (!bubble) {
            return;
        }

        const content = bubble.querySelector(".mobile-message-content");

        bubble.classList.add("mobile-thinking-bubble");

        if (content) {
            content.innerHTML =
                window.NovaAnswerPayload && typeof window.NovaAnswerPayload.renderAnswerPayload === "function"
                    ? window.NovaAnswerPayload.renderAnswerPayload(text || "", { messageId: bubble.dataset.messageId })
                    : window.NovaMobileCore && typeof window.NovaMobileCore.renderMarkdown === "function"
                        ? window.NovaMobileCore.renderMarkdown(text || "")
                        : window.NovaMobileCore.escapeHtml(text || "");

            if (
                window.NovaMobileBridge &&
                typeof window.NovaMobileBridge.enhanceCodeBlocks === "function"
            ) {
                window.NovaMobileBridge.enhanceCodeBlocks(bubble);
            }
        }

        if (
            window.NovaMobileBridge &&
            typeof window.NovaMobileBridge.scrollBottom === "function"
        ) {
            window.NovaMobileBridge.scrollBottom();
        }
    }

    function renderSessionPayload(payload, reason) {
        const detail = payload || {};

        const session =
            detail.session && typeof detail.session === "object"
                ? detail.session
                : detail;

        const sessionId =
            detail.session_id ||
            session.id ||
            session.session_id ||
            "";

        const messages =
            Array.isArray(detail.messages)
                ? detail.messages
                : Array.isArray(session.messages)
                    ? session.messages
                    : [];


        console.trace("🚨 CHAT UI DIRECT RESTORE SOURCE");

console.trace("🚨 CHAT UI DIRECT RESTORE SOURCE");

console.log("[CHAT UI DIRECT RESTORE]", {
    id: session?.id,
            reason: reason || "unknown",
            session_id: sessionId,
            messages: messages.length
        });

        const resolvedChatContainer =
            document.getElementById("nova-mobile-chat") ||
            document.getElementById("nova-chat") ||
            document.getElementById("chat-container") ||
            document.getElementById("chatContainer") ||
            document.querySelector("[data-nova-chat-container]") ||
            document.querySelector(".nova-mobile-chat") ||
            document.querySelector(".chat-container") ||
            window.chatContainer;

        if (!resolvedChatContainer || !document.body.contains(resolvedChatContainer)) {
            console.warn("[CHAT UI DIRECT RESTORE] missing visible chatContainer", {
                oldExists: !!window.chatContainer,
                oldConnected: !!window.chatContainer?.isConnected
            });

            return false;
        }

        window.chatContainer = resolvedChatContainer;

        window.__NOVA_SESSION_RENDERING__ = true;
        window.__NOVA_SUPPRESS_SAVE = true;

        window.chatContainer.innerHTML = "";
        window.NOVA_MESSAGES = messages.slice();

        if (
            session &&
            session.meta &&
            session.meta.onboarding &&
            window.NovaMobileOnboardingActions &&
            typeof window.NovaMobileOnboardingActions.render === "function"
        ) {
            window.NovaMobileOnboardingActions.render({
                onboarding: true,
                welcome_message:
                    session.meta.onboarding.welcome_message ||
                    "",
                actions:
                    session.meta.onboarding.actions ||
                    [],
            });
        }


        let renderedCount = 0;

        messages.forEach(function (msg, index) {
            try {
                appendMessage(
                    msg.role || "assistant",
                    msg.content ?? msg.text ?? "",
                    msg
                );

                renderedCount += 1;
            } catch (err) {
                console.error("[CHAT UI DIRECT RESTORE APPEND FAILED]", {
                    index: index,
                    role: msg && msg.role,
                    text: String((msg && (msg.content ?? msg.text)) || "").slice(0, 120),
                    error: err
                });
            }
        });

        console.log("[CHAT UI DIRECT RESTORE DONE]", {
            session_id: sessionId,
            messages: messages.length,
            rendered: renderedCount,
            children: window.chatContainer ? window.chatContainer.children.length : null,
            text: window.chatContainer ? window.chatContainer.textContent.trim().slice(0, 200) : ""
        });

        try {
            if (
                window.NovaMobileBridge &&
                typeof window.NovaMobileBridge.scrollBottom === "function"
            ) {
                window.NovaMobileBridge.scrollBottom(true);
            }
        } catch (err) {
            console.warn("[CHAT UI DIRECT RESTORE SCROLL FAILED]", err);
        }

console.log("[CHAT UI DIRECT RESTORE AFTER SCROLL]");

try {
    if (typeof window.NovaMobileInstallCopyRegenerateActions === "function") {
        window.NovaMobileInstallCopyRegenerateActions();
    }
} catch (err) {
    console.warn("[CHAT UI ACTION RESTORE FAILED]", err);
}

setTimeout(function () {
            window.__NOVA_SESSION_RENDERING__ = false;
            window.__NOVA_SUPPRESS_SAVE = false;
        }, 250);

        return true;
    }

    window.NovaMobileChatUI = {
        appendMessage: appendMessage,
        createThinkingBubble: createThinkingBubble,
        updateThinkingBubble: updateThinkingBubble,
        renderSessionPayload: renderSessionPayload
    };

    if (!window.__novaMobileApprovalActionsBound) {
        window.__novaMobileApprovalActionsBound = true;
        document.addEventListener("click", function (event) {
            const button = event.target && event.target.closest ? event.target.closest("[data-action='tool-approve'], [data-action='tool-deny']") : null;
            if (!button) return;
            event.preventDefault();
            event.stopPropagation();
            const actions = window.NovaToolApprovalActions;
            if (!actions) return;
            const messageId = button.dataset.messageId || "";
            const sessionId = button.dataset.sessionId || window.__novaActiveSessionId || "";
            if (button.dataset.action === "tool-approve") actions.approve(messageId, button, sessionId);
            else actions.deny(messageId, button, sessionId);
        });
    }

    window.NovaMobileRenderSession = function (session, sessionId) {
        return renderSessionPayload(
            {
                session_id: sessionId || session?.id || session?.session_id || "",
                session: session || {},
                messages: Array.isArray(session?.messages) ? session.messages : []
            },
            "direct-call"
        );
    };

window.addEventListener("nova:session-selected", function (event) {

    console.trace("🚨 SESSION SELECT EVENT");
        console.log("[CHAT UI LISTENER FIRED]", event.detail);
        return renderSessionPayload(event.detail || {}, "event");
    });
})();
