(function () {
    "use strict";

    function createUploadProgress(file) {
        const wrapper = document.createElement("div");

        wrapper.className =
            "mobile-chat-message system mobile-upload-card";

        const content = document.createElement("div");

        content.className =
            "mobile-upload-card-content";

        const icon = document.createElement("div");

        icon.className = "mobile-upload-icon";
        icon.textContent = "â†‘";

        const meta = document.createElement("div");

        meta.className = "mobile-upload-meta";

        const title = document.createElement("div");

        title.className = "mobile-upload-title";

        title.textContent =
            file && file.name
                ? file.name
                : "Uploading file...";

        const label = document.createElement("div");

        label.className = "mobile-upload-label";
        label.textContent = "Uploading...";

        const progress = document.createElement("div");

        progress.className =
            "mobile-upload-progress";

        const bar = document.createElement("div");

        bar.className =
            "mobile-upload-progress-bar indeterminate";

        progress.appendChild(bar);

        meta.appendChild(title);
        meta.appendChild(label);
        meta.appendChild(progress);

        content.appendChild(icon);
        content.appendChild(meta);

        wrapper.appendChild(content);

        if (window.chatContainer) {
            window.chatContainer.appendChild(
                wrapper
            );
        }

        return {
            wrapper,
            content,
            icon,
            meta,
            title,
            label,
            progress,
            bar
        };
    }

    function markUploadSuccess(uploadUi, name) {
        if (!uploadUi) return;

        uploadUi.bar.classList.remove(
            "indeterminate"
        );

        uploadUi.bar.style.width = "100%";
        uploadUi.icon.textContent = "âœ“";
        uploadUi.label.textContent = "Uploaded";

        uploadUi.title.textContent =
            name || "Uploaded";

        setTimeout(function () {
            uploadUi.wrapper.remove();
        }, 1200);
    }

    function markUploadFailed(uploadUi) {
        if (!uploadUi) return;

        uploadUi.bar.classList.remove(
            "indeterminate"
        );

        uploadUi.icon.textContent = "!";
        uploadUi.label.textContent =
            "Upload failed.";

        setTimeout(function () {
            uploadUi.wrapper.remove();
        }, 2000);
    }

    function normalizeUploadedFiles(data) {
        if (!data) return [];

        if (Array.isArray(data.files)) {
            return data.files;
        }

        if (data.file) {
            return [data.file];
        }

        return [];
    }

    async function analyzeUploadedAttachment(fileMeta) {
        if (
            typeof window.sendMessage !==
            "function"
        ) {
            return;
        }

        await window.sendMessage({
            text: "Analyze uploaded attachment",
            attachments: [fileMeta],
            regenerate: false
        });
    }

    async function uploadAndAnalyzeFile(file, uploadUi) {
        const formData = new FormData();

        formData.append("file", file);

        const response = await fetch(
            "/api/upload",
            {
                method: "POST",
                body: formData
            }
        );

        if (!response.ok) {
            throw new Error("Upload failed");
        }

        const data = await response.json();

        const uploaded =
            normalizeUploadedFiles(data);

        if (!uploaded.length) {
            throw new Error(
                "Upload response missing file URL"
            );
        }

        for (const item of uploaded) {
            const name =
                item.name ||
                item.filename ||
                "Uploaded";

            const url =
                item.url ||
                item.file_url ||
                item.image_url ||
                "";

            markUploadSuccess(
                uploadUi,
                name
            );

            await analyzeUploadedAttachment({
                name,
                url,
                file_url: url,
                image_url: url,
                mime_type:
                    item.mime_type ||
                    item.type ||
                    ""
            });
        }
    }

    function openUploadPicker() {
        const input =
            document.createElement("input");

        input.type = "file";
        input.multiple = true;

        input.addEventListener(
            "change",
            async function () {
                const files = Array.from(
                    input.files || []
                );

                for (const file of files) {
                    const uploadUi =
                        createUploadProgress(file);

                    try {
                        await uploadAndAnalyzeFile(
                            file,
                            uploadUi
                        );
                    } catch (err) {
                        console.error(
                            "[Nova Mobile] upload/analyze failed:",
                            err
                        );

                        markUploadFailed(
                            uploadUi
                        );

                        if (
                            typeof window.showToast ===
                            "function"
                        ) {
                            window.showToast(
                                "Upload or analysis failed."
                            );
                        }
                    }
                }
            }
        );

        input.click();
    }

    window.NovaMobileUpload = {
        openUploadPicker
    };

    console.log(
        "[Nova Mobile] upload module ready"
    );

})();

/* NOVA_MOBILE_HARD_ATTACH_BUTTON_BRIDGE_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileHardAttachButtonBridgeInstalled) {
        return;
    }

    window.NovaMobileHardAttachButtonBridgeInstalled = true;

    function getOrCreateFileInput() {
        var input = document.getElementById("nova-mobile-hard-file-input");

        if (input) {
            return input;
        }

        input = document.createElement("input");
        input.id = "nova-mobile-hard-file-input";
        input.type = "file";
        input.multiple = true;
        input.style.position = "fixed";
        input.style.left = "-9999px";
        input.style.top = "-9999px";
        input.style.width = "1px";
        input.style.height = "1px";
        input.style.opacity = "0";

        document.body.appendChild(input);

        input.addEventListener("change", function () {
            var files = Array.from(input.files || []);

            if (!files.length) {
                return;
            }

            files.forEach(function (file) {
                var form = new FormData();
                form.append("file", file);

                fetch("/api/upload", {
                    method: "POST",
                    body: form
                })
                    .then(function (response) {
                        return response.json();
                    })
                    .then(function (data) {
                        console.log("[Nova Mobile Hard Attach Button Bridge] uploaded", data);

                        if (typeof window.NovaMobileHardAttachmentPayloadStore === "function") {
                            window.NovaMobileHardAttachmentPayloadStore(data);
                        }

                        window.dispatchEvent(new CustomEvent("nova-mobile-upload-complete", {
                            detail: data
                        }));

                        window.dispatchEvent(new CustomEvent("nova-mobile-attachment-uploaded", {
                            detail: data
                        }));
                    })
                    .catch(function (error) {
                        console.error("[Nova Mobile Hard Attach Button Bridge] upload failed", error);
                    });
            });

            input.value = "";
        });

        return input;
    }

    function isAttachButton(button) {
        if (!button) {
            return false;
        }

        var id = String(button.id || "").toLowerCase();
        var cls = String(button.className || "").toLowerCase();
        var label = String(
            button.getAttribute("aria-label") ||
            button.getAttribute("title") ||
            button.textContent ||
            ""
        ).toLowerCase();

        return (
            id.indexOf("attach") !== -1 ||
            cls.indexOf("attach") !== -1 ||
            label.indexOf("attach") !== -1 ||
            label.indexOf("upload") !== -1 ||
            label.indexOf("file") !== -1
        );
    }

    function bindAttachButtons() {
        Array.from(document.querySelectorAll("button, [role='button']")).forEach(function (button) {
            if (!isAttachButton(button)) {
                return;
            }

            if (button.dataset.novaHardAttachBridge === "1") {
                return;
            }

            button.dataset.novaHardAttachBridge = "1";

            button.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();

                var input = getOrCreateFileInput();
                input.click();

                console.log("[Nova Mobile Hard Attach Button Bridge] attach click handled", button.id || button.textContent || button.className);
            }, true);
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(bindAttachButtons, 0);
        setTimeout(bindAttachButtons, 500);
        setTimeout(bindAttachButtons, 1500);
    });

    document.addEventListener("click", function () {
        setTimeout(bindAttachButtons, 0);
    }, true);

    window.NovaMobileHardAttachBind = bindAttachButtons;
    window.NovaMobileHardAttachInput = getOrCreateFileInput;

    console.log("[Nova Mobile Hard Attach Button Bridge] ready");
})();


/* NOVA_MOBILE_UPLOAD_HARD_STORE_PAYLOAD_20260610 */
(function () {
    "use strict";

    if (window.NovaMobileUploadHardStorePayloadInstalled) {
        return;
    }
    window.NovaMobileUploadHardStorePayloadInstalled = true;

    function normalizeUploadPayload(data, file) {
        data = data && typeof data === "object" ? data : {};
        file = file && typeof file === "object" ? file : {};

        var filename = String(
            data.filename ||
            data.name ||
            data.original_filename ||
            data.stored_name ||
            data.saved_name ||
            file.name ||
            ""
        ).trim();

        var storedName = String(
            data.stored_name ||
            data.saved_name ||
            data.filename ||
            filename ||
            ""
        ).trim();

        var url = String(
            data.url ||
            data.file_url ||
            data.path ||
            (storedName ? "/api/uploads/" + storedName : "")
        ).trim();

        var mimeType = String(
            data.mime_type ||
            data.content_type ||
            data.type ||
            file.type ||
            "application/octet-stream"
        ).trim();

        var size = data.size || data.size_bytes || file.size || 0;

        return {
            id: String(data.id || data.upload_id || "").trim(),
            filename: filename || storedName || "attachment",
            name: filename || storedName || "attachment",
            original_filename: String(data.original_filename || file.name || filename || "").trim(),
            stored_name: storedName || filename,
            saved_name: storedName || filename,
            mime_type: mimeType,
            content_type: mimeType,
            size: size,
            size_bytes: size,
            url: url,
            file_url: url
        };
    }

function storeUploadPayload(data, file) {
    var item = normalizeUploadPayload(data, file);

    if (!item.url && !item.file_url && !item.filename) {
        return null;
    }

    if (typeof window.NovaMobileHardAttachmentPayloadStore === "function") {
        try {
            window.NovaMobileHardAttachmentPayloadStore(item);
        } catch (e) {}
    }

    var clean = [item];

    window.NovaMobilePendingAttachments = clean;
    window.__novaMobilePendingAttachments = clean;

    try {
        localStorage.setItem("nova_mobile_pending_attachments", JSON.stringify(clean));
        localStorage.setItem("nova_mobile_last_uploaded_attachment", JSON.stringify(item));
    } catch (e) {}

    try {
        window.dispatchEvent(new CustomEvent("nova-mobile-upload-complete", { detail: item }));
        window.dispatchEvent(new CustomEvent("nova-mobile-attachments-changed", { detail: clean }));
    } catch (e) {}

    try {
        if (typeof window.NovaRenderComposerInlinePreview === "function") {
            window.NovaRenderComposerInlinePreview();
        }
    } catch (e) {}

    console.log("[Nova Mobile Upload Hard Store] stored upload payload", item);

    return item;
}

    var originalFetch = window.fetch;

    window.fetch = function (input, init) {
        var url = "";
        try {
            url = typeof input === "string" ? input : String((input && input.url) || "");
        } catch (e) {
            url = "";
        }

        var maybeFile = null;
        try {
            if (init && init.body && typeof FormData !== "undefined" && init.body instanceof FormData) {
                var formFile = init.body.get("file");
                if (formFile) {
                    maybeFile = formFile;
                }
            }
        } catch (e) {}

        return originalFetch.apply(this, arguments).then(function (response) {
            if (url.indexOf("/api/upload") !== -1 && response && response.clone) {
                response.clone().json().then(function (data) {
                    storeUploadPayload(data, maybeFile);
                }).catch(function () {});
            }

            return response;
        });
    };

    window.NovaMobileUploadHardStorePayload = storeUploadPayload;

    console.log("[Nova Mobile Upload Hard Store] ready");
})();


// NOVA_MOBILE_CLEAR_ATTACHMENT_AFTER_SEND_20260611
// Clears composer attachment state and preview after a mobile message is sent.
(function () {
    "use strict";

    if (window.NovaMobileClearAttachmentAfterSendInstalled) {
        return;
    }
    window.NovaMobileClearAttachmentAfterSendInstalled = true;

    function clearMobileAttachmentsAfterSend() {
        try {
            var state = window.NovaMobileState || window.mobileState || window.state || null;

            if (state && Array.isArray(state.pendingAttachments)) {
                state.pendingAttachments.length = 0;
            }

            if (Array.isArray(window.NovaMobilePendingAttachments)) {
                window.NovaMobilePendingAttachments.length = 0;
            }

            if (Array.isArray(window.NovaPendingAttachments)) {
                window.NovaPendingAttachments.length = 0;
            }

            if (Array.isArray(window.pendingAttachments)) {
                window.pendingAttachments.length = 0;
            }

            window.NovaMobileAttachments = [];
            window.NovaPendingAttachments = [];
            window.pendingAttachments = [];

            try {
                localStorage.removeItem("nova_mobile_pending_attachments");
                localStorage.removeItem("nova-mobile-pending-attachments");
                localStorage.removeItem("nova_pending_attachments");
                localStorage.removeItem("novaPendingAttachments");
            } catch (storageError) {}

            var previewBoxes = [
                document.getElementById("nova-mobile-attachment-preview"),
                document.querySelector(".nova-clean-attachment-preview"),
                document.querySelector("[data-nova-attachment-preview='true']")
            ].filter(Boolean);

            previewBoxes.forEach(function (box) {
                box.innerHTML = "";
                box.setAttribute("data-nova-empty", "true");
                box.setAttribute("data-empty", "true");
            });

            if (typeof window.NovaRenderComposerInlinePreview === "function") {
                window.NovaRenderComposerInlinePreview();
            }

            window.dispatchEvent(new CustomEvent("nova-mobile-attachments-cleared"));
        } catch (error) {
            console.warn("[Nova Mobile Clear Attachment After Send] failed", error);
        }
    }

    window.NovaClearMobileAttachmentsAfterSend = clearMobileAttachmentsAfterSend;

    window.addEventListener("nova-mobile-after-send", clearMobileAttachmentsAfterSend);
    window.addEventListener("nova-mobile-message-sent", clearMobileAttachmentsAfterSend);
    window.addEventListener("nova-mobile-send-complete", clearMobileAttachmentsAfterSend);

    console.log("[Nova Mobile Clear Attachment After Send] ready");
})();

/* =========================================================
   NOVA MOBILE UPLOAD PREVIEW OWNER 20260630
   Single visible phone preview owned by nova-mobile-upload.js.
========================================================= */
(() => {
    "use strict";

    if (window.__NOVA_MOBILE_UPLOAD_PREVIEW_OWNER_20260630__) return;
    window.__NOVA_MOBILE_UPLOAD_PREVIEW_OWNER_20260630__ = true;

    const PREVIEW_ID = "nova-mobile-upload-preview-owner";

    function safeArray(value) {
        return Array.isArray(value) ? value : [];
    }

    function readJson(key, fallback) {
        try {
            const raw = localStorage.getItem(key);
            if (!raw) return fallback;
            const parsed = JSON.parse(raw);
            return parsed || fallback;
        } catch (_) {
            return fallback;
        }
    }

    function writeJson(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (_) {}
    }

    function removeKey(key) {
        try {
            localStorage.removeItem(key);
        } catch (_) {}
    }

    function normalizeAttachment(raw) {
        if (!raw || typeof raw !== "object") return null;

        const source =
            raw.attachment && typeof raw.attachment === "object" ? raw.attachment :
            raw.file && typeof raw.file === "object" ? raw.file :
            raw.data && typeof raw.data === "object" ? raw.data :
            raw;

        const url =
            source.url ||
            source.file_url ||
            source.preview_url ||
            source.path ||
            "";

        const filename =
            source.original_filename ||
            source.filename ||
            source.name ||
            source.title ||
            (url ? String(url).split("/").pop() : "") ||
            "attachment";

        const mimeType =
            source.mime_type ||
            source.mimeType ||
            source.type ||
            source.mime ||
            "";

        return {
            url: String(url || ""),
            file_url: String(source.file_url || url || ""),
            filename: String(source.filename || filename || "attachment"),
            original_filename: String(source.original_filename || filename || "attachment"),
            name: String(filename || "attachment"),
            mime_type: String(mimeType || ""),
            size: source.size || source.file_size || source.bytes || 0
        };
    }

    function attachmentKey(item) {
        return [
            item.url,
            item.file_url,
            item.original_filename,
            item.filename,
            item.name,
            item.size
        ].join("|").toLowerCase();
    }

    function collectAttachments() {
        const found = [];

        function addMany(items) {
            safeArray(items).forEach((item) => {
                const clean = normalizeAttachment(item);
                if (clean) found.push(clean);
            });
        }

        addMany(window.NovaMobileAttachments);
        addMany(window.NovaMobilePendingAttachments);
        addMany(window.__novaMobilePendingAttachments);
        addMany(window.NovaMobileUploadedAttachments);
        addMany(window.NovaMobileSharedAttachments);
        addMany(window.NovaMobileAttachmentQueue);
        addMany(window.NovaMobileUploadQueue);
        addMany(window.NovaPendingAttachments);
        addMany(window.pendingAttachments);

        addMany(readJson("nova_mobile_pending_attachments", []));
        addMany(readJson("nova_mobile_latest_attachments", []));
        addMany(readJson("novaPendingAttachments", []));

        const last = readJson("nova_mobile_last_uploaded_attachment", null);
        if (last && typeof last === "object") {
            const clean = normalizeAttachment(last);
            if (clean) found.push(clean);
        }

        const seen = new Set();
        return found.filter((item) => {
            const key = attachmentKey(item);
            if (!key || seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }

    function saveAttachments(attachments) {
        const clean = safeArray(attachments).map(normalizeAttachment).filter(Boolean);

        window.NovaMobileAttachments = clean;
        window.NovaMobilePendingAttachments = clean;
        window.__novaMobilePendingAttachments = clean;
        window.NovaMobileUploadedAttachments = clean;
        window.NovaMobileSharedAttachments = clean;
        window.NovaPendingAttachments = clean;
        window.pendingAttachments = clean;

        if (window.NovaMobileState && typeof window.NovaMobileState === "object") {
            window.NovaMobileState.pendingAttachments = clean;
        }

        if (clean.length) {
            writeJson("nova_mobile_pending_attachments", clean);
            writeJson("nova_mobile_latest_attachments", clean);
            writeJson("novaPendingAttachments", clean);
            writeJson("nova_mobile_last_uploaded_attachment", clean[clean.length - 1]);
        } else {
            removeKey("nova_mobile_pending_attachments");
            removeKey("nova_mobile_latest_attachments");
            removeKey("novaPendingAttachments");
            removeKey("nova_mobile_last_uploaded_attachment");
        }

        return clean;
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function getComposer() {
        return (
            document.getElementById("nova-mobile-composer") ||
            document.querySelector(".nova-mobile-composer") ||
            document.querySelector(".mobile-composer") ||
            document.querySelector("[data-mobile-composer]") ||
            document.querySelector("form")
        );
    }

    function ensurePreviewHost() {
        let host = document.getElementById(PREVIEW_ID);
        if (host) return host;

        const composer = getComposer();
        if (!composer) return null;

        host = document.createElement("div");
        host.id = PREVIEW_ID;
        host.className = "nova-mobile-upload-preview-owner";
        host.setAttribute("data-mobile-attachment-preview-owner", "true");

        composer.insertBefore(host, composer.firstChild);

        return host;
    }

    function isImageAttachment(item) {
        const name = item.original_filename || item.filename || item.name || "";
        const url = item.url || item.file_url || "";
        const mime = item.mime_type || "";

        return (
            mime.indexOf("image/") === 0 ||
            /\.(png|jpg|jpeg|gif|webp|bmp)$/i.test(name) ||
            /\.(png|jpg|jpeg|gif|webp|bmp)$/i.test(url)
        );
    }

    function shortName(value) {
        const name = String(value || "attachment").trim() || "attachment";
        if (name.length <= 30) return name;

        const dot = name.lastIndexOf(".");
        const ext = dot > 0 ? name.slice(dot) : "";
        const base = dot > 0 ? name.slice(0, dot) : name;

        return base.slice(0, Math.max(10, 27 - ext.length)) + "..." + ext;
    }

    function renderUploadPreview() {
        const host = ensurePreviewHost();
        if (!host) return;

        const attachments = saveAttachments(collectAttachments());

        if (!attachments.length) {
            host.innerHTML = "";
            host.hidden = true;
            host.style.display = "none";
            return;
        }

        host.hidden = false;
        host.style.display = "flex";

        host.innerHTML = attachments.map((item, index) => {
            const fullName = item.original_filename || item.filename || item.name || "attachment";
            const name = shortName(fullName);
            const url = item.url || item.file_url || "";
            const image = isImageAttachment(item) && url
                ? `<img class="nova-mobile-upload-preview-thumb" src="${escapeHtml(url)}" alt="${escapeHtml(fullName)}">`
                : `<span class="nova-mobile-upload-preview-icon" aria-hidden="true">📎</span>`;

            return (
                `<div class="nova-mobile-upload-preview-chip" data-upload-preview-index="${index}" title="${escapeHtml(fullName)}">` +
                    image +
                    `<span class="nova-mobile-upload-preview-name">${escapeHtml(name)}</span>` +
                    `<button type="button" class="nova-mobile-upload-preview-remove" data-remove-upload-preview="${index}" aria-label="Remove attachment">×</button>` +
                `</div>`
            );
        }).join("");
    }

    function removeAttachment(index) {
        const current = collectAttachments();
        const cleanIndex = Number(index);

        if (!Number.isFinite(cleanIndex)) return;

        current.splice(cleanIndex, 1);
        saveAttachments(current);
        renderUploadPreview();

        window.dispatchEvent(new CustomEvent("nova-mobile-attachments-changed", {
            detail: {
                pendingAttachments: current
            }
        }));
    }

    function clearUploadPreview() {
        saveAttachments([]);

        const host = document.getElementById(PREVIEW_ID);
        if (host) {
            host.innerHTML = "";
            host.hidden = true;
            host.style.display = "none";
        }

        window.dispatchEvent(new CustomEvent("nova-mobile-attachments-cleared", {
            detail: {
                pendingAttachments: []
            }
        }));
    }

    document.addEventListener("click", (event) => {
        const button = event.target && event.target.closest
            ? event.target.closest("[data-remove-upload-preview]")
            : null;

        if (!button) return;

        event.preventDefault();
        event.stopPropagation();

        removeAttachment(button.getAttribute("data-remove-upload-preview"));
    }, true);

    [
        "nova-mobile-upload-complete",
        "nova-mobile-attachment-uploaded",
        "nova-mobile-attachments-changed"
    ].forEach((eventName) => {
        window.addEventListener(eventName, () => {
            setTimeout(renderUploadPreview, 0);
            setTimeout(renderUploadPreview, 120);
            setTimeout(renderUploadPreview, 400);
        }, true);
    });

    document.addEventListener("change", (event) => {
        if (event.target && event.target.type === "file") {
            setTimeout(renderUploadPreview, 120);
            setTimeout(renderUploadPreview, 500);
        }
    }, true);

    const oldClear =
        window.NovaMobileClearAttachmentsAfterSend ||
        window.NovaClearMobileAttachmentsAfterSend ||
        window.NovaMobileCleanAttachmentChipOnlyClear ||
        null;

    window.NovaMobileRenderUploadPreview = renderUploadPreview;
    window.NovaMobileClearUploadPreview = clearUploadPreview;
    window.NovaMobileClearAttachmentsAfterSend = function () {
        try {
            if (typeof oldClear === "function") oldClear();
        } catch (_) {}

        clearUploadPreview();
    };

    document.addEventListener("DOMContentLoaded", () => {
        setTimeout(renderUploadPreview, 0);
        setTimeout(renderUploadPreview, 300);
        setTimeout(renderUploadPreview, 900);
    });

    setTimeout(renderUploadPreview, 1000);

    console.log("[Nova Mobile Upload Preview Owner] ready");
})();


