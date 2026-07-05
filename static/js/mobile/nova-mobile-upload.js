(function () {
    "use strict";

    if (window.__NOVA_MOBILE_UPLOAD_SINGLE_OWNER_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_UPLOAD_SINGLE_OWNER_20260705__ = true;

    var pendingAttachments = [];
    var fileInput = null;
    var previewHost = null;
    var boundButtons = new WeakSet();

    function log() {
        try {
            console.log.apply(console, ["[Nova Mobile Upload Single Owner]"].concat([].slice.call(arguments)));
        } catch (_) {}
    }

    function findComposer() {
        return (
            document.getElementById("nova-mobile-composer") ||
            document.querySelector(".nova-mobile-composer") ||
            document.querySelector(".mobile-composer")
        );
    }

    function findAttachButtons() {
        return Array.from(document.querySelectorAll([
            "#nova-mobile-attach",
            "[data-mobile-tool='upload']",
            "[data-mobile-tool='attach']",
            "[aria-label='Attach']",
            "[title='Attach']"
        ].join(","))).filter(Boolean);
    }

    function ensureFileInput() {
        if (fileInput && document.body.contains(fileInput)) {
            return fileInput;
        }

        fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.multiple = true;
        fileInput.id = "nova-mobile-file-input";
        fileInput.className = "nova-hidden-file-input";
        fileInput.setAttribute("data-nova-upload-owner", "single");

        fileInput.style.setProperty("position", "fixed", "important");
        fileInput.style.setProperty("left", "-9999px", "important");
        fileInput.style.setProperty("top", "-9999px", "important");
        fileInput.style.setProperty("width", "1px", "important");
        fileInput.style.setProperty("height", "1px", "important");
        fileInput.style.setProperty("opacity", "0", "important");
        fileInput.style.setProperty("pointer-events", "none", "important");

        fileInput.addEventListener("change", handleFileChange);

        document.body.appendChild(fileInput);
        return fileInput;
    }

    function normalizeUploadResponse(data, file) {
        data = data || {};

        var url =
            data.url ||
            data.file_url ||
            data.path ||
            data.upload_url ||
            data.href ||
            "";

        var filename =
            data.filename ||
            data.name ||
            file.name ||
            "attachment";

        return {
            ok: data.ok !== false,
            filename: filename,
            name: filename,
            original_name: file.name || filename,
            type: file.type || data.type || data.mime_type || "",
            mime_type: file.type || data.mime_type || data.type || "",
            size: file.size || data.size || 0,
            url: url,
            path: data.path || url,
            file_url: data.file_url || url,
            upload: data
        };
    }

    async function uploadOne(file) {
        var form = new FormData();
        form.append("file", file);
        form.append("attachment", file);

        var response = await fetch("/api/upload", {
            method: "POST",
            body: form,
            credentials: "include",
            cache: "no-store"
        });

        var data = {};
        try {
            data = await response.json();
        } catch (_) {
            data = {
                ok: false,
                error: "Upload response was not JSON"
            };
        }

        if (!response.ok || data.ok === false) {
            throw new Error(data.error || data.message || "Upload failed");
        }

        return normalizeUploadResponse(data, file);
    }

    function syncGlobals() {
        window.NovaMobilePendingAttachments = pendingAttachments.slice();
        window.NovaMobileAttachments = pendingAttachments.slice();
        window.novaMobilePendingAttachments = pendingAttachments.slice();

        try {
            localStorage.setItem("nova_mobile_upload", JSON.stringify(pendingAttachments));
            localStorage.setItem("nova_mobile_attachment", JSON.stringify(pendingAttachments));
            localStorage.setItem("nova_pending_attachment", JSON.stringify(pendingAttachments));
        } catch (_) {}
    }

    function dispatchAttachmentEvent(name, detail) {
        try {
            window.dispatchEvent(new CustomEvent(name, {
                detail: detail
            }));
        } catch (_) {}
    }

    function notifyChanged(extra) {
        var detail = Object.assign({
            pendingAttachments: pendingAttachments.slice(),
            attachments: pendingAttachments.slice()
        }, extra || {});

        syncGlobals();

        dispatchAttachmentEvent("nova-mobile-attachments-changed", detail);
    }

    function ensurePreviewHost() {
        if (previewHost && document.body.contains(previewHost)) {
            return previewHost;
        }

        previewHost =
            document.getElementById("nova-mobile-attachment-preview") ||
            document.getElementById("mobileAttachmentPreview") ||
            document.querySelector("[data-mobile-attachment-preview-owner='true']");

        if (previewHost) {
            previewHost.setAttribute("data-mobile-attachment-preview-owner", "true");
            return previewHost;
        }

        var composer = findComposer();

        if (!composer) {
            return null;
        }

        previewHost = document.createElement("div");
        previewHost.id = "nova-mobile-attachment-preview";
        previewHost.className = "nova-mobile-attachment-preview";
        previewHost.setAttribute("data-mobile-attachment-preview-owner", "true");
        previewHost.hidden = true;
        previewHost.style.display = "none";

        composer.insertBefore(previewHost, composer.firstChild);
        return previewHost;
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function isImage(item) {
        return /^image\//i.test(item.mime_type || item.type || "");
    }

    function renderPreview() {
        var host = ensurePreviewHost();

        if (!host) {
            return;
        }

        if (!pendingAttachments.length) {
            host.innerHTML = "";
            host.hidden = true;
            host.style.display = "none";
            host.setAttribute("data-empty", "true");
            return;
        }

        host.hidden = false;
        host.style.display = "flex";
        host.removeAttribute("data-empty");

        host.innerHTML = pendingAttachments.map(function (item, index) {
            var name = escapeHtml(item.filename || item.name || "attachment");
            var url = item.url || item.file_url || "";

            var thumb = "";
            if (isImage(item) && url) {
                thumb = '<img src="' + escapeHtml(url) + '" alt="">';
            }

            return (
                '<div class="nova-mobile-attachment-chip" data-upload-preview-index="' + index + '">' +
                    thumb +
                    '<span>' + name + '</span>' +
                    '<button type="button" data-remove-upload-preview="' + index + '" aria-label="Remove attachment">×</button>' +
                '</div>'
            );
        }).join("");
    }

    async function handleFileChange(event) {
        var input = event.target;
        var files = Array.from(input.files || []);

        if (!files.length) {
            return;
        }

        log("uploading", files.length, "file(s)");

        for (var i = 0; i < files.length; i += 1) {
            try {
                var item = await uploadOne(files[i]);
                pendingAttachments.push(item);

                syncGlobals();
                renderPreview();

                dispatchAttachmentEvent("nova-mobile-upload-complete", item);
                dispatchAttachmentEvent("nova-mobile-attachment-uploaded", item);

                log("uploaded", item.filename || item.name);
            } catch (error) {
                console.error("[Nova Mobile Upload Single Owner] upload failed", error);
                dispatchAttachmentEvent("nova-mobile-upload-error", {
                    error: String(error && error.message ? error.message : error),
                    file: files[i] ? files[i].name : ""
                });
            }
        }

        input.value = "";
        notifyChanged();
        renderPreview();
    }

    function openUploadPicker() {
        var input = ensureFileInput();

        try {
            input.click();
            return true;
        } catch (error) {
            console.error("[Nova Mobile Upload Single Owner] picker failed", error);
            return false;
        }
    }

    function bindAttachButtons() {
        findAttachButtons().forEach(function (button) {
            if (!button || boundButtons.has(button)) {
                return;
            }

            boundButtons.add(button);
            button.setAttribute("data-nova-upload-single-owner", "true");

            button.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();

                openUploadPicker();
                return false;
            }, true);
        });
    }

    function removeAttachment(index) {
        if (index < 0 || index >= pendingAttachments.length) {
            return;
        }

        pendingAttachments.splice(index, 1);
        notifyChanged();
        renderPreview();
    }

    function clearAttachments() {
        pendingAttachments = [];
        syncGlobals();
        renderPreview();

        dispatchAttachmentEvent("nova-mobile-attachments-cleared", {
            pendingAttachments: []
        });
    }

    document.addEventListener("click", function (event) {
        var button = event.target && event.target.closest
            ? event.target.closest("[data-remove-upload-preview]")
            : null;

        if (!button) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        removeAttachment(Number(button.getAttribute("data-remove-upload-preview")));
    }, true);

    [
        "nova-mobile-after-send",
        "nova-mobile-message-sent",
        "nova-mobile-send-complete",
        "nova-mobile-attachments-clear-request"
    ].forEach(function (eventName) {
        window.addEventListener(eventName, clearAttachments);
    });

    function boot() {
        ensureFileInput();
        bindAttachButtons();
        renderPreview();
    }

    boot();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    }

    window.addEventListener("load", boot);

    setTimeout(boot, 250);
    setTimeout(boot, 750);

    window.NovaMobileUpload = {
        openUploadPicker: openUploadPicker,
        clearAttachments: clearAttachments,
        renderPreview: renderPreview,
        getPendingAttachments: function () {
            return pendingAttachments.slice();
        }
    };

    window.NovaClearMobileAttachmentsAfterSend = clearAttachments;
    window.NovaRenderComposerInlinePreview = renderPreview;

    log("installed");
})();
