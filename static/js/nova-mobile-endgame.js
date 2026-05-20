(function () {
    "use strict";

    const MOBILE_MAX_WIDTH = 760;

    let mediaRecorder = null;
    let recordedChunks = [];
    let isRecording = false;

    function isMobile() {
        return window.innerWidth <= MOBILE_MAX_WIDTH;
    }

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function qsa(selector, root) {
        return Array.from((root || document).querySelectorAll(selector));
    }

    function log() {
        try {
            console.log.apply(console, ["[NovaMobileEndgame]"].concat(Array.from(arguments)));
        } catch (_) {}
    }

    function createEl(tag, className, text) {
        const el = document.createElement(tag);

        if (className) {
            el.className = className;
        }

        if (text) {
            el.textContent = text;
        }

        return el;
    }

    function getComposerRoot() {
        return (
            qs(".nova-composer") ||
            qs("[data-composer]") ||
            qs(".composer") ||
            qs("form") ||
            document.body
        );
    }

    function getInput() {
        return (
            qs("#nova-composer-input") ||
            qs("[data-composer-input]") ||
            qs("textarea") ||
            qs("input[type='text']")
        );
    }

    function getUploadInput() {
        return (
            qs("input[type='file'][accept*='image']") ||
            qs("input[type='file']")
        );
    }

    function getSessionId() {
        return (
            window.__novaActiveSessionId ||
            window.activeSessionId ||
            window.sessionId ||
            localStorage.getItem("nova_active_session_id") ||
            null
        );
    }

function getLastAssistantText() {
    if (window.__novaLastReplyText) {
        return String(window.__novaLastReplyText || "").trim();
    }

    const selectors = [
        ".nova-mobile-message-assistant .nova-mobile-message-body",
        ".nova-mobile-message-assistant",
        "[data-role='assistant']",
        ".message.assistant",
        ".nova-message.assistant",
        ".assistant-message",
        ".assistant"
    ];

    for (const selector of selectors) {
        const candidates = qsa(selector);
        const last = candidates[candidates.length - 1];

        if (last) {
            const text = (last.innerText || last.textContent || "").trim();

            if (text) {
                window.__novaLastReplyText = text;
                return text;
            }
        }
    }

    return "";
}

    function getMessagesRoot() {
        return (
            qs("#nova-chat-messages") ||
            qs("[data-chat-messages]") ||
            qs(".nova-chat-messages") ||
            qs(".chat-messages") ||
            qs("main") ||
            document.body
        );
    }

function appendMobileMessage(role, text) {
    const root = getMessagesRoot();

    const wrap = createEl("div", "nova-mobile-message nova-mobile-message-" + role, "");
    const label = createEl("div", "nova-mobile-message-label", role === "user" ? "You" : "Nova");
    const body = createEl("div", "nova-mobile-message-body", text || "");

    wrap.setAttribute("data-role", role);
    wrap.appendChild(label);
    wrap.appendChild(body);

    root.appendChild(wrap);

    if (role === "assistant" && text) {
        window.__novaLastReplyText = String(text || "").trim();
    }

    try {
        wrap.scrollIntoView({
            behavior: "smooth",
            block: "end",
        });
    } catch (_) {}
}

    function setStatus(text) {
        const status = qs("#nova-mobile-status");

        if (status) {
            status.textContent = text || "";
        }
    }

    function ensureMobileBar() {
        let bar = qs("#nova-mobile-endgame-bar");

        if (bar) {
            return bar;
        }

        const root = getComposerRoot();

        bar = createEl("div", "nova-mobile-endgame-bar", "");
        bar.id = "nova-mobile-endgame-bar";

        const preview = createEl("div", "nova-mobile-preview-strip", "");
        preview.id = "nova-mobile-preview-strip";

        const status = createEl("div", "nova-mobile-status-line", "");
        status.id = "nova-mobile-status";

        const buttons = createEl("div", "nova-mobile-endgame-actions", "");

        const imageBtn = createEl("button", "nova-mobile-action-btn", "Image");
        imageBtn.id = "nova-mobile-image-btn";
        imageBtn.type = "button";

        const voiceBtn = createEl("button", "nova-mobile-action-btn", "Voice");
        voiceBtn.id = "nova-mobile-voice-btn";
        voiceBtn.type = "button";

        const speakBtn = createEl("button", "nova-mobile-action-btn", "Speak");
        speakBtn.id = "nova-mobile-speak-btn";
        speakBtn.type = "button";

        buttons.appendChild(imageBtn);
        buttons.appendChild(voiceBtn);
        buttons.appendChild(speakBtn);

        bar.appendChild(preview);
        bar.appendChild(status);
        bar.appendChild(buttons);

        root.appendChild(bar);

        return bar;
    }

    function ensureStyles() {
        if (qs("#nova-mobile-endgame-style")) {
            return;
        }

        const style = document.createElement("style");
        style.id = "nova-mobile-endgame-style";
        style.textContent = `
@media (max-width: 760px) {
    .nova-mobile-endgame-bar {
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 8px 10px;
        box-sizing: border-box;
    }

    .nova-mobile-preview-strip {
        display: flex;
        gap: 8px;
        overflow-x: auto;
        max-width: 100%;
    }

    .nova-mobile-preview-card {
        position: relative;
        flex: 0 0 auto;
        width: 72px;
        height: 72px;
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.16);
        background: rgba(255, 255, 255, 0.08);
    }

    .nova-mobile-preview-card img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }

    .nova-mobile-preview-remove {
        position: absolute;
        top: 4px;
        right: 4px;
        width: 22px;
        height: 22px;
        border: 0;
        border-radius: 999px;
        cursor: pointer;
        font-size: 13px;
        line-height: 22px;
        padding: 0;
        background: rgba(0, 0, 0, 0.72);
        color: white;
    }

    .nova-mobile-status-line {
        min-height: 18px;
        font-size: 12px;
        opacity: 0.75;
        padding: 0 4px;
    }

    .nova-mobile-endgame-actions {
        display: flex;
        gap: 8px;
        width: 100%;
    }

    .nova-mobile-action-btn {
        flex: 1;
        min-height: 38px;
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.08);
        color: inherit;
        font-weight: 700;
        cursor: pointer;
    }

    .nova-mobile-action-btn:active {
        transform: scale(0.98);
    }

    .nova-mobile-action-btn.is-recording {
        outline: 2px solid rgba(255, 80, 80, 0.85);
        background: rgba(255, 80, 80, 0.18);
    }

    .nova-mobile-message {
        max-width: 92%;
        margin: 10px;
        padding: 10px 12px;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
    }

    .nova-mobile-message-user {
        margin-left: auto;
    }

    .nova-mobile-message-assistant {
        margin-right: auto;
    }

    .nova-mobile-message-label {
        font-size: 11px;
        font-weight: 800;
        opacity: 0.7;
        margin-bottom: 4px;
    }

    .nova-mobile-message-body {
        white-space: pre-wrap;
        line-height: 1.45;
    }
}
        `.trim();

        document.head.appendChild(style);
    }

    function wireImagePreview() {
        const imageBtn = qs("#nova-mobile-image-btn");
        const uploadInput = getUploadInput();
        const previewStrip = qs("#nova-mobile-preview-strip");

        if (!imageBtn || !uploadInput || !previewStrip || imageBtn.__novaMobileImageWired) {
            return;
        }

        imageBtn.__novaMobileImageWired = true;

        imageBtn.addEventListener("click", function () {
            uploadInput.click();
        });

        uploadInput.addEventListener("change", function () {
            const files = Array.from(uploadInput.files || []);

            previewStrip.innerHTML = "";

            files.forEach(function (file, index) {
                if (!file || !file.type || !file.type.startsWith("image/")) {
                    return;
                }

                const url = URL.createObjectURL(file);
                const card = createEl("div", "nova-mobile-preview-card", "");
                const img = document.createElement("img");
                const remove = createEl("button", "nova-mobile-preview-remove", "×");

                remove.type = "button";
                img.src = url;
                img.alt = file.name || "Image preview";

                remove.addEventListener("click", function () {
                    card.remove();

                    try {
                        URL.revokeObjectURL(url);
                    } catch (_) {}

                    log("preview removed", index);
                });

                card.appendChild(img);
                card.appendChild(remove);
                previewStrip.appendChild(card);
            });

            log("image preview rendered", files.length);
        });
    }

async function speakText(text) {
    if (!text) {
        throw new Error("No text provided for TTS.");
    }

    const response = await fetch("/api/tts", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            text: text,
        }),
    });

    if (!response.ok) {
        throw new Error("TTS failed: " + response.status);
    }

    const contentType = response.headers.get("content-type") || "";
    let audioUrl = "";

    if (contentType.includes("application/json")) {
        const data = await response.json();

        audioUrl =
            data.audio_url ||
            data.url ||
            data.file_url ||
            "";

        if (!audioUrl) {
            throw new Error("TTS returned JSON but no audio_url.");
        }
    } else {
        const blob = await response.blob();
        audioUrl = URL.createObjectURL(blob);
    }

    const audio = new Audio(audioUrl);
    audio.setAttribute("playsinline", "true");

    audio.addEventListener("ended", function () {
        if (audioUrl.startsWith("blob:")) {
            try {
                URL.revokeObjectURL(audioUrl);
            } catch (_) {}
        }
    });

    await audio.play();
}

function wireSpeakButton() {
    const speakBtn = qs("#nova-mobile-speak-btn");

    if (!speakBtn || speakBtn.__novaMobileSpeakWired) {
        return;
    }

    speakBtn.__novaMobileSpeakWired = true;

    speakBtn.addEventListener("click", async function () {
        console.log("[NovaMobileEndgame] Speak tapped");

        const text =
            getLastAssistantText() ||
            window.__novaLastReplyText ||
            "Hello Nova";

        if (!text) {
            setStatus("No Nova reply found to speak yet.");
            return;
        }

        speakBtn.disabled = true;
        speakBtn.textContent = "Speaking";
        setStatus("Preparing speech...");

        try {
            await speakText(text);
            setStatus("Speaking complete.");
        } catch (error) {
            console.error("[NovaMobileEndgame] speak failed", error);
            setStatus("Speak failed. Check console.");
        } finally {
            speakBtn.disabled = false;
            speakBtn.textContent = "Speak";
        }
    });
}

    function normalizeUploadedAttachment(data, file) {
        const source =
            data.attachment ||
            data.upload ||
            data.file ||
            data.result ||
            data;

        const filename =
            source.filename ||
            source.name ||
            source.stored_name ||
            file.name;

        const url =
            source.url ||
            source.path ||
            source.file_url ||
            source.download_url ||
            (filename ? "/api/uploads/" + filename : "");

        return {
            id: source.id || "mobile_audio_" + Date.now(),
            name: source.name || file.name,
            filename: filename,
            stored_name: source.stored_name || filename,
            url: url,
            mime_type: source.mime_type || source.type || file.type || "audio/webm",
            size: source.size || file.size,
            status: "uploaded",
        };
    }

    async function uploadAudioBlob(blob) {
        const file = new File(
            [blob],
            "mobile-voice-" + Date.now() + ".webm",
            {
                type: blob.type || "audio/webm",
            }
        );

        const form = new FormData();
        form.append("file", file);

        const response = await fetch("/api/upload", {
            method: "POST",
            body: form,
        });

        if (!response.ok) {
            throw new Error("Upload failed: " + response.status);
        }

        const data = await response.json();
        return normalizeUploadedAttachment(data, file);
    }

    async function sendAudioToChat(attachment) {
        const payload = {
            user_text: "Transcribe this audio and respond.",
            text: "Transcribe this audio and respond.",
            message: "Transcribe this audio and respond.",
            attachments: [attachment],
        };

        const sessionId = getSessionId();

        if (sessionId) {
            payload.session_id = sessionId;
        }

        appendMobileMessage("user", "Voice message sent.");
        setStatus("Sending voice to Nova...");

        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error("Chat failed: " + response.status);
        }

        const data = await response.json();

        const assistant =
            data.assistant_message ||
            data.message ||
            data.reply ||
            {};

        const text =
            assistant.text ||
            assistant.content ||
            data.assistant_text ||
            data.text ||
            data.output_text ||
            "Voice sent, but no response text returned.";

        appendMobileMessage("assistant", text);
        setStatus("Voice response complete.");

        return data;
    }

    async function stopRecordingAndSend(voiceBtn) {
        return new Promise(function (resolve, reject) {
            if (!mediaRecorder) {
                resolve();
                return;
            }

            mediaRecorder.onstop = async function () {
                try {
                    const blob = new Blob(recordedChunks, {
                        type: "audio/webm",
                    });

                    recordedChunks = [];

                    setStatus("Uploading voice...");
                    const attachment = await uploadAudioBlob(blob);

                    setStatus("Voice uploaded. Asking Nova...");
                    await sendAudioToChat(attachment);

                    resolve();
                } catch (error) {
                    reject(error);
                } finally {
                    isRecording = false;
                    mediaRecorder = null;

                    if (voiceBtn) {
                        voiceBtn.classList.remove("is-recording");
                        voiceBtn.textContent = "Voice";
                        voiceBtn.disabled = false;
                    }
                }
            };

            mediaRecorder.stop();
        });
    }

    async function startRecording(voiceBtn) {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setStatus("Mic not supported in this browser.");
            return;
        }

        const stream = await navigator.mediaDevices.getUserMedia({
            audio: true,
        });

        recordedChunks = [];

        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = function (event) {
            if (event.data && event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.start();

        isRecording = true;

        voiceBtn.classList.add("is-recording");
        voiceBtn.textContent = "Stop";
        setStatus("Recording... tap Stop to send.");
    }

    function wireVoiceRecorder() {
        const voiceBtn = qs("#nova-mobile-voice-btn");

        if (!voiceBtn || voiceBtn.__novaMobileVoiceWired) {
            return;
        }

        voiceBtn.__novaMobileVoiceWired = true;

        voiceBtn.addEventListener("click", async function () {
            try {
                if (isRecording) {
                    voiceBtn.disabled = true;
                    voiceBtn.textContent = "Sending";
                    await stopRecordingAndSend(voiceBtn);
                    return;
                }

                await startRecording(voiceBtn);
            } catch (error) {
                console.error("[NovaMobileEndgame] voice failed", error);

                isRecording = false;
                mediaRecorder = null;

                voiceBtn.disabled = false;
                voiceBtn.classList.remove("is-recording");
                voiceBtn.textContent = "Voice";

                setStatus("Voice failed. Check mic permission or /api/upload.");
            }
        });
    }

    function boot() {
        if (!isMobile()) {
            return;
        }

        ensureStyles();
        ensureMobileBar();
        wireImagePreview();
        wireSpeakButton();
        wireVoiceRecorder();

        log("mobile endgame bridge ready");
    }

    document.addEventListener("DOMContentLoaded", boot);
    window.addEventListener("resize", boot);

    setTimeout(boot, 250);
    setTimeout(boot, 1000);
})();