(function () {
    "use strict";

    function appendStreamDelta(thinking, textOutRef, delta) {
        if (!delta) return;

        textOutRef.value += delta;

        if (textOutRef.renderScheduled) {
            return;
        }

        textOutRef.renderScheduled = true;

        requestAnimationFrame(function () {
            const content =
                thinking &&
                thinking.querySelector(".mobile-message-content");

            if (content) {
                content.innerHTML = `
                    <div class="nova-streaming-text">
                        ${window.NovaMobileBridge.renderMarkdown(textOutRef.value)}
                        <span class="nova-stream-cursor"></span>
                    </div>
                `;
            }

            if (thinking) {
                thinking.classList.add("nova-streaming-active");
                window.NovaMobileBridge.enhanceCodeBlocks(thinking);
            }

            window.NovaMobileBridge.scrollBottom(false);

            textOutRef.renderScheduled = false;
        });
    }

async function readChatStream(response, thinking) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let buffer = "";

    const textOutRef = {
        value: "",
        renderScheduled: false
    };

    while (true) {
        const part = await reader.read();

        if (part.done) break;

        buffer += decoder.decode(part.value || new Uint8Array(), {
            stream: true
        });

        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";

        blocks.forEach(function (block) {
            const dataLine = block
                .split(/\r?\n/)
                .find(function (line) {
                    return line.startsWith("data:");
                });

            if (!dataLine) return;

            const raw = dataLine.slice(5).trim();

            if (!raw || raw === "[DONE]") return;

            try {
                const data = JSON.parse(raw);

                window.NovaMobileBridge.syncSessionFromResponse(data);

                if (typeof window.renderWebSourcesFromPayload === "function") {
                    window.renderWebSourcesFromPayload(data);
                }

                if (data.type === "token") {
                    appendStreamDelta(thinking, textOutRef, data.content || "");
                    return;
                }

                if (data.type === "message") {
                    textOutRef.value = "";
                    appendStreamDelta(thinking, textOutRef, data.content || "");
                    return;
                }

                if (data.type === "done") {
                    return;
                }

            } catch (e) {
                console.warn("[Nova Stream Parse Error]", e, raw);
            }
        });
    }

    return textOutRef.value;
}

    function pickGeneratedImageUrl(payload) {
        if (!payload || typeof payload !== "object") {
            return "";
        }

        if (payload.image_url) return String(payload.image_url);
        if (payload.imageUrl) return String(payload.imageUrl);
        if (payload.preview) return String(payload.preview);

        const assistant = payload.assistant_message;

        if (assistant && typeof assistant === "object") {
            if (assistant.image_url) return String(assistant.image_url);
            if (assistant.imageUrl) return String(assistant.imageUrl);
            if (assistant.preview) return String(assistant.preview);
            if (assistant.url) return String(assistant.url);
        }

        const artifact = payload.saved_artifact || payload.artifact;

        if (artifact && typeof artifact === "object") {
            if (artifact.image_url) return String(artifact.image_url);
            if (artifact.imageUrl) return String(artifact.imageUrl);
            if (artifact.preview) return String(artifact.preview);
            if (artifact.url) return String(artifact.url);

            if (artifact.viewer && artifact.viewer.image_url) {
                return String(artifact.viewer.image_url);
            }

            if (artifact.meta && artifact.meta.image_url) {
                return String(artifact.meta.image_url);
            }
        }

        return "";
    }

    function renderGeneratedImagePayload(payload) {
        const imageUrl = pickGeneratedImageUrl(payload);

        if (!imageUrl) {
            return;
        }

        if (
            window.NovaMobileImages &&
            typeof window.NovaMobileImages.appendImage === "function"
        ) {
            window.NovaMobileImages.appendImage(imageUrl, "Generated image");

            console.log(
                "[Nova Mobile Stream] rendered generated image",
                imageUrl
            );

            return;
        }

        console.warn(
            "[Nova Mobile Stream] NovaMobileImages.appendImage unavailable",
            imageUrl
        );
    }

    async function sendChatJsonFallback(message, thinking, attachments) {
        const safeAttachments = Array.isArray(attachments) ? attachments : [];

        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                session_id: window.__novaActiveSessionId,
                user_text: message,
                message: message,
                attachments: safeAttachments
            })
        });

        if (!response.ok) {
            throw new Error("Backend failed");
        }

        const payload = await response.json();

        window.NovaMobileBridge.syncSessionFromResponse(payload);

        if (typeof window.renderWebSourcesFromPayload === "function") {
            window.renderWebSourcesFromPayload(payload);
        }

        renderGeneratedImagePayload(payload);

        // NOVA_STREAM_CLEAR_ATTACHMENTS_AFTER_SUCCESS_20260611
        // The real JSON fallback path must clear composer attachment state after
        // a successful /api/chat response, otherwise fetch wrappers can re-inject
        // stale attachments into later messages.
        try {
            if (typeof window.NovaClearMobileAttachmentsAfterSend === "function") {
                window.NovaClearMobileAttachmentsAfterSend();
            } else {
                try { localStorage.removeItem("nova_mobile_pending_attachments"); } catch (_) {}
                try { localStorage.removeItem("nova_mobile_last_uploaded_attachment"); } catch (_) {}
                try { localStorage.removeItem("nova_mobile_latest_attachments"); } catch (_) {}
                window.NovaMobileSharedAttachments = [];
                window.NovaMobilePendingAttachments = [];
                window.__novaMobilePendingAttachments = [];
                window.NovaPendingAttachments = [];
                window.__novaPendingAttachments = [];
                window.pendingAttachments = [];

                try {
                    window.dispatchEvent(new CustomEvent("nova-mobile-attachments-cleared", {
                        detail: {
                            source: "nova-mobile-stream-success",
                            pendingAttachments: []
                        }
                    }));
                } catch (_) {}
            }
        } catch (clearError) {
            console.warn("[Nova Mobile Stream] failed to clear attachments after send", clearError);
        }

        return payload;
    }

    window.NovaMobileStream = {
        appendStreamDelta,
        readChatStream,
        sendChatJsonFallback
    };

    console.log("[Nova Mobile] stream handler module ready");
})();


/* NOVA_MOBILE_RESTORE_BUBBLE_ACTIONS_20260609 */
(function() {
    const attachBubbleActions = function(bubble) {
        if (!bubble) return;
        if (bubble.querySelector('.nova-mobile-message-actions')) return; // already added

        const row = document.createElement('div');
        row.className = 'nova-mobile-message-actions';

        // Copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'nova-mobile-copy-chat';
        copyBtn.textContent = 'Copy';
        copyBtn.onclick = function() {
            if (window.copyText) window.copyText(bubble.textContent || '');
        };
        row.appendChild(copyBtn);

        // Regenerate button
        const regenBtn = document.createElement('button');
        regenBtn.className = 'nova-mobile-regen-chat';
        regenBtn.textContent = 'Regenerate';
        regenBtn.onclick = function() {
            if (window.NovaComposerBundle && window.NovaComposerBundle.regenBubble) {
                window.NovaComposerBundle.regenBubble(bubble);
            }
        };
        row.appendChild(regenBtn);

        bubble.appendChild(row);
    };

    // Expose globally for render calls
    window.NovaAttachBubbleActions = attachBubbleActions;
})();

