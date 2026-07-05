/* NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_V1_20260705 */
(function installNovaMobileUploadChangeAuthorityV1() {
    "use strict";

    if (window.__NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_V1_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_V1_20260705__ = true;

    function log() {
        try {
            console.log.apply(console, arguments);
        } catch (_) {}
    }

    function getInput() {
        return (
            document.getElementById("nova-mobile-file-input") ||
            document.querySelector("input[type='file'][id*='mobile']") ||
            document.querySelector("input[type='file']")
        );
    }

    function getPreviewOwner() {
        let owner = document.getElementById("nova-mobile-upload-preview-owner");

        if (!owner) {
            owner = document.createElement("div");
            owner.id = "nova-mobile-upload-preview-owner";
            owner.className = "nova-mobile-upload-preview-owner";

            const composer =
                document.querySelector(".mobile-composer") ||
                document.querySelector("#mobileComposer") ||
                document.querySelector(".mobile-input-area") ||
                document.body;

            composer.insertBefore(owner, composer.firstChild || null);
        }

        try {
            owner.hidden = false;
            owner.removeAttribute("hidden");
            owner.removeAttribute("aria-hidden");
            owner.style.setProperty("display", "flex", "important");
            owner.style.setProperty("visibility", "visible", "important");
            owner.style.setProperty("opacity", "1", "important");
            owner.style.setProperty("gap", "8px", "important");
            owner.style.setProperty("padding", "6px 10px", "important");
            owner.style.setProperty("overflow-x", "auto", "important");
        } catch (_) {}

        return owner;
    }

    function normalizeUploadResponse(data, file) {
        const url =
            data.url ||
            data.file_url ||
            data.upload_url ||
            data.path ||
            data.src ||
            data.href ||
            (data.filename ? "/api/uploads/" + encodeURIComponent(data.filename) : "");

        return {
            ok: data.ok !== false,
            name: data.name || data.original_filename || data.filename || file.name,
            filename: data.filename || data.name || file.name,
            original_filename: data.original_filename || file.name,
            type: data.type || data.mime_type || file.type || "application/octet-stream",
            mime_type: data.mime_type || data.type || file.type || "application/octet-stream",
            size: data.size || data.size_bytes || file.size || 0,
            size_bytes: data.size_bytes || data.size || file.size || 0,
            url: url,
            file_url: url,
            path: data.path || url,
            source: "nova-mobile-upload-change-authority-v1",
            raw: data
        };
    }

    function ensureQueues() {
        if (!Array.isArray(window.NovaMobileSharedAttachments)) {
            window.NovaMobileSharedAttachments = [];
        }

        if (!Array.isArray(window.__novaMobilePendingAttachments)) {
            window.__novaMobilePendingAttachments = [];
        }

        if (!Array.isArray(window.NovaMobilePendingAttachments)) {
            window.NovaMobilePendingAttachments = [];
        }

        if (!Array.isArray(window.__NOVA_MOBILE_PENDING_ATTACHMENTS__)) {
            window.__NOVA_MOBILE_PENDING_ATTACHMENTS__ = [];
        }
    }

    function pushAttachment(attachment) {
        ensureQueues();

        const queues = [
            window.NovaMobileSharedAttachments,
            window.__novaMobilePendingAttachments,
            window.NovaMobilePendingAttachments,
            window.__NOVA_MOBILE_PENDING_ATTACHMENTS__
        ];

        for (const queue of queues) {
            if (!Array.isArray(queue)) continue;

            const already = queue.some(function (item) {
                return (
                    item &&
                    (
                        item.url === attachment.url ||
                        item.file_url === attachment.file_url ||
                        item.filename === attachment.filename
                    )
                );
            });

            if (!already) {
                queue.push(attachment);
            }
        }

        log("[Nova Upload Change Authority] queued attachment", attachment);
    }

    function renderPreview(attachment) {
        const owner = getPreviewOwner();

        const chip = document.createElement("div");
        chip.className = "nova-mobile-upload-preview-chip";
        chip.setAttribute("data-nova-role", "attachment-preview-chip");
        chip.setAttribute("data-attachment-id", attachment.filename || attachment.name || String(Date.now()));

        chip.style.cssText = [
            "display:inline-flex",
            "align-items:center",
            "gap:8px",
            "max-width:220px",
            "padding:6px 8px",
            "border-radius:10px",
            "background:rgba(255,255,255,0.08)",
            "color:white",
            "font-size:12px",
            "white-space:nowrap",
            "overflow:hidden",
            "text-overflow:ellipsis"
        ].join(";");

        if (/^image\//i.test(attachment.mime_type || attachment.type || "") && attachment.url) {
            const img = document.createElement("img");
            img.src = attachment.url;
            img.alt = attachment.name || attachment.filename || "attachment";
            img.style.cssText = [
                "width:34px",
                "height:34px",
                "object-fit:cover",
                "border-radius:8px",
                "flex:0 0 auto"
            ].join(";");

            chip.appendChild(img);
        }

        const label = document.createElement("span");
        label.textContent = attachment.name || attachment.filename || "Attachment";
        label.style.cssText = [
            "overflow:hidden",
            "text-overflow:ellipsis",
            "max-width:160px"
        ].join(";");

        chip.appendChild(label);
        owner.appendChild(chip);
    }

    async function uploadFile(file) {
        const form = new FormData();
        form.append("file", file, file.name);

        log("[Nova Upload Change Authority] uploading", {
            name: file.name,
            type: file.type,
            size: file.size
        });

        const response = await fetch("/api/upload", {
            method: "POST",
            body: form,
            credentials: "include",
            cache: "no-store"
        });

        const text = await response.text();

        let data = {};

        try {
            data = JSON.parse(text);
        } catch (_) {
            data = {
                ok: response.ok,
                text: text
            };
        }

        log("[Nova Upload Change Authority] upload response", response.status, data);

        if (!response.ok || data.ok === false) {
            throw new Error(data.error || data.message || ("Upload failed: " + response.status));
        }

        const attachment = normalizeUploadResponse(data, file);

        pushAttachment(attachment);
        renderPreview(attachment);

        try {
            if (typeof window.NovaMobileReceiveUploadedAttachment === "function") {
                window.NovaMobileReceiveUploadedAttachment(attachment);
            }
        } catch (error) {
            log("[Nova Upload Change Authority] receiver failed", error);
        }

        return attachment;
    }

    async function handleChange(event) {
        const input = event.target || getInput();
        const files = Array.from((input && input.files) || []);

        log("[Nova Upload Change Authority] input change", files.length, files[0]);

        if (!files.length) return;

        for (const file of files) {
            try {
                await uploadFile(file);
            } catch (error) {
                console.error("[Nova Upload Change Authority] upload failed", error);
            }
        }
    }

    function bind() {
        const input = getInput();

        if (!input) {
            return false;
        }

        if (input.dataset.novaUploadChangeAuthorityBound === "1") {
            return true;
        }

        input.dataset.novaUploadChangeAuthorityBound = "1";
        input.addEventListener("change", handleChange, true);

        log("[Nova Upload Change Authority] bound", input.id || input.className || input);

        return true;
    }

    function bindLoop() {
        bind();
        setTimeout(bind, 300);
        setTimeout(bind, 1000);
        setTimeout(bind, 2500);
    }

    document.addEventListener("DOMContentLoaded", bindLoop);
    window.addEventListener("load", bindLoop);

    const observer = new MutationObserver(bind);
    observer.observe(document.documentElement || document.body, {
        childList: true,
        subtree: true
    });

    bindLoop();

    window.NovaMobileUploadChangeAuthorityV1 = {
        version: "NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_V1_20260705",
        bind: bind,
        uploadFile: uploadFile,
        handleChange: handleChange
    };

    log("[Nova Upload Change Authority] installed");
})();
