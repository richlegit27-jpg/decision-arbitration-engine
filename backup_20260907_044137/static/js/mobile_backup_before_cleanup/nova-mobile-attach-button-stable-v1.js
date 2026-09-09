(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACH_BUTTON_STABLE_V1_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACH_BUTTON_STABLE_V1_20260704__ = true;

    const LOG = "[Nova Mobile Attach Button Stable V1]";
    const INPUT_ID = "nova-mobile-stable-attach-input-v1";

    let opening = false;
    let uploading = false;
    let lastOpenAt = 0;

    function currentSessionId() {
        try {
            return new URLSearchParams(location.search).get("session_id") || "";
        } catch (_) {
            return "";
        }
    }

    function textOf(el) {
        return String(
            (el && (
                el.id + " " +
                el.className + " " +
                el.getAttribute("aria-label") + " " +
                el.getAttribute("title") + " " +
                el.textContent
            )) || ""
        ).toLowerCase();
    }

    function isBadMatch(el) {
        const t = textOf(el);

        return /send|stop|voice|speak|tts|session|rename|delete|pin|logout|account|new|copy|regen|regenerate|close/.test(t);
    }

    function isAttachButton(el) {
        if (!el || !el.closest) {
            return false;
        }

        const target = el.closest("button,a,label,[role='button'],.mobile-header-btn,.mobile-icon-btn");

        if (!target) {
            return false;
        }

        const t = textOf(target);

        if (isBadMatch(target)) {
            return false;
        }

        return /attach|upload|file|image|photo|picture|paperclip|clip|📎/.test(t);
    }

    function ensureInput() {
        let input = document.getElementById(INPUT_ID);

        if (input) {
            return input;
        }

        input = document.createElement("input");
        input.id = INPUT_ID;
        input.type = "file";
        input.accept = "image/*,.png,.jpg,.jpeg,.webp,.gif,.txt,.md,.pdf,.doc,.docx,.json,.csv";
        input.style.position = "fixed";
        input.style.left = "-9999px";
        input.style.top = "-9999px";
        input.style.width = "1px";
        input.style.height = "1px";
        input.style.opacity = "0";
        input.style.pointerEvents = "none";
        input.tabIndex = -1;

        input.addEventListener("change", onFileChange, true);

        document.body.appendChild(input);

        return input;
    }

    function getUploadUrl() {
        return "/api/upload";
    }

    function normalizeUploadPayload(data, file) {
        if (!data || typeof data !== "object") {
            data = {};
        }

        const filename = data.filename || data.name || file.name;
        const url = data.url || data.file_url || data.path || data.upload_url || "";

        return Object.assign({}, data, {
            ok: data.ok !== false,
            filename: filename,
            name: filename,
            url: url,
            file_url: data.file_url || url,
            path: data.path || url,
            mime_type: data.mime_type || data.type || file.type || "",
            type: data.type || data.mime_type || file.type || "",
            size: data.size || data.size_bytes || file.size || null,
            source: "stable-mobile-attach"
        });
    }

    async function uploadFile(file) {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("filename", file.name || "attachment");
        fd.append("session_id", currentSessionId());

        const response = await fetch(getUploadUrl(), {
            method: "POST",
            body: fd,
            credentials: "include",
            cache: "no-store"
        });

        let data = null;

        try {
            data = await response.clone().json();
        } catch (_) {
            data = {};
        }

        if (!response.ok || data.ok === false) {
            throw new Error((data && (data.error || data.message)) || ("Upload failed: " + response.status));
        }

        return normalizeUploadPayload(data, file);
    }

    function handToPreviewAndQueue(payload) {
        try {
            if (window.NovaMobileAttachmentSendBridgeV1 && typeof window.NovaMobileAttachmentSendBridgeV1.remember === "function") {
                window.NovaMobileAttachmentSendBridgeV1.remember(payload);
            }
        } catch (err) {
            console.warn(LOG, "queue handoff failed", err);
        }

        try {
            if (typeof window.NovaMobileReceiveUploadedAttachment === "function") {
                window.NovaMobileReceiveUploadedAttachment(payload);
            }
        } catch (err) {
            console.warn(LOG, "preview receiver failed", err);
        }

        try {
            document.dispatchEvent(new CustomEvent("nova-mobile-attachment-uploaded", {
                detail: payload
            }));
        } catch (_) {}

        console.log(LOG, "uploaded and queued", payload);
    }

    async function onFileChange(event) {
        const input = event.currentTarget;
        const file = input && input.files && input.files[0];

        if (!file || uploading) {
            return;
        }

        uploading = true;

        try {
            console.log(LOG, "uploading", {
                name: file.name,
                type: file.type,
                size: file.size
            });

            const payload = await uploadFile(file);
            handToPreviewAndQueue(payload);
        } catch (err) {
            console.error(LOG, err);
            alert("Attachment upload failed: " + (err && err.message ? err.message : err));
        } finally {
            uploading = false;

            try {
                input.value = "";
            } catch (_) {}
        }
    }

    function openPicker() {
        const now = Date.now();

        if (opening || now - lastOpenAt < 500) {
            return;
        }

        opening = true;
        lastOpenAt = now;

        const input = ensureInput();

        try {
            input.click();
            console.log(LOG, "picker opened");
        } catch (err) {
            console.error(LOG, "picker open failed", err);
        } finally {
            setTimeout(function () {
                opening = false;
            }, 650);
        }
    }

    function handleAttachTap(event) {
        const target = event.target && event.target.closest
            ? event.target.closest("button,a,label,[role='button'],.mobile-header-btn,.mobile-icon-btn")
            : null;

        if (!isAttachButton(target)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        if (typeof event.stopImmediatePropagation === "function") {
            event.stopImmediatePropagation();
        }

        openPicker();
    }

    function stabilizeVisibleAttachButtons() {
        document.querySelectorAll("button,a,label,[role='button'],.mobile-header-btn,.mobile-icon-btn").forEach(function (el) {
            if (!isAttachButton(el)) {
                return;
            }

            el.dataset.novaAttachStable = "true";
            el.style.setProperty("touch-action", "manipulation", "important");
            el.style.setProperty("-webkit-tap-highlight-color", "transparent", "important");
            el.style.setProperty("user-select", "none", "important");
            el.style.setProperty("-webkit-user-select", "none", "important");
            el.style.setProperty("transform", "none", "important");
            el.style.setProperty("transition", "none", "important");
            el.style.setProperty("animation", "none", "important");
        });
    }

    document.addEventListener("pointerup", handleAttachTap, true);
    document.addEventListener("click", handleAttachTap, true);
    document.addEventListener("touchend", handleAttachTap, true);

    stabilizeVisibleAttachButtons();

    new MutationObserver(function () {
        stabilizeVisibleAttachButtons();
    }).observe(document.documentElement, {
        childList: true,
        subtree: true
    });

    window.NovaMobileAttachButtonStableV1 = {
        open: openPicker,
        input: ensureInput,
        stabilize: stabilizeVisibleAttachButtons
    };

    console.log(LOG, "installed");
})();
