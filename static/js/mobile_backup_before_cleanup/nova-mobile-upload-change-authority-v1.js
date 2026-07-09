(function () {
    "use strict";

    var MARK = "NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_SINGLE_OWNER_20260705";

    if (window.__NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_SINGLE_OWNER_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_SINGLE_OWNER_20260705__ = true;

    var pendingAttachments = [];

    function log() {
        try {
            console.log.apply(console, ["[" + MARK + "]"].concat(Array.from(arguments)));
        } catch (_) {}
    }

    function normalizeAttachment(value) {
        if (!value || typeof value !== "object") return null;

        var filename =
            value.filename ||
            value.name ||
            value.file_name ||
            value.original_filename ||
            value.original_name ||
            "";

        var url =
            value.url ||
            value.file_url ||
            value.fileUrl ||
            value.path ||
            value.upload_path ||
            value.saved_path ||
            value.file_path ||
            "";

        var mimeType =
            value.mime_type ||
            value.mimeType ||
            value.type ||
            value.content_type ||
            "";

        var size =
            value.size ||
            value.size_bytes ||
            value.sizeBytes ||
            0;

        if (!filename && !url) return null;

        return {
            id: value.id || value.attachment_id || value.file_id || "",
            attachment_id: value.attachment_id || value.id || value.file_id || "",
            filename: filename,
            name: filename,
            url: url,
            file_url: url,
            path: value.path || value.upload_path || value.saved_path || value.file_path || url,
            mime_type: mimeType,
            type: mimeType,
            content_type: mimeType,
            size: size,
            size_bytes: size
        };
    }

    function savePending() {
        try {
            localStorage.setItem("nova_mobile_upload", JSON.stringify(pendingAttachments));
            localStorage.setItem("nova_mobile_pending_attachments", JSON.stringify(pendingAttachments));
        } catch (_) {}

        window.NovaMobilePendingAttachments = pendingAttachments;
        window.NovaMobileUploadedAttachments = pendingAttachments;
        window.NovaMobileAttachmentQueue = pendingAttachments;
        window.NovaMobileUploadQueue = pendingAttachments;
        window.NovaMobileSharedAttachments = pendingAttachments;
    }

    function loadPending() {
        var keys = [
            "nova_mobile_upload",
            "nova_mobile_pending_attachments",
            "nova_mobile_uploaded_attachments",
            "nova_mobile_attachment_queue"
        ];

        keys.forEach(function (key) {
            try {
                var raw = localStorage.getItem(key);
                if (!raw) return;

                var parsed = JSON.parse(raw);
                if (!Array.isArray(parsed)) return;

                parsed.forEach(function (item) {
                    var clean = normalizeAttachment(item);
                    if (clean) pendingAttachments.push(clean);
                });
            } catch (_) {}
        });

        dedupePending();
        savePending();
    }

    function dedupePending() {
        var seen = {};
        var clean = [];

        pendingAttachments.forEach(function (item) {
            var key = [
                item.filename || "",
                item.url || item.file_url || item.path || "",
                item.mime_type || item.type || "",
                item.size || ""
            ].join("|");

            if (seen[key]) return;

            seen[key] = true;
            clean.push(item);
        });

        pendingAttachments.length = 0;
        clean.forEach(function (item) {
            pendingAttachments.push(item);
        });
    }

    function getOrCreateInput() {
        var input = document.getElementById("nova-mobile-upload-authority-input");

        if (!input) {
            input = document.createElement("input");
            input.id = "nova-mobile-upload-authority-input";
            input.type = "file";
            input.multiple = false;
            input.style.position = "fixed";
            input.style.left = "-10000px";
            input.style.top = "0";
            input.style.width = "1px";
            input.style.height = "1px";
            input.style.opacity = "0";
            input.style.pointerEvents = "none";
            document.body.appendChild(input);
        }

        if (input.dataset.novaUploadAuthorityBound !== "1") {
            input.dataset.novaUploadAuthorityBound = "1";

            input.addEventListener("change", function () {
                var file = input.files && input.files[0];

                if (!file) {
                    log("no file selected");
                    return;
                }

                uploadFile(file);
            }, true);
        }

        return input;
    }

    function openPicker(event) {
        try {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
            }
        } catch (_) {}

        var input = getOrCreateInput();

        try {
            input.value = "";
        } catch (_) {}

        input.click();

        log("picker opened");

        return false;
    }

    function uploadFile(file) {
        var form = new FormData();
        form.append("file", file);
        form.append("attachment", file);

        log("uploading", {
            name: file.name,
            type: file.type,
            size: file.size
        });

        fetch("/api/upload", {
            method: "POST",
            credentials: "include",
            body: form
        })
            .then(function (response) {
                return response.text().then(function (raw) {
                    var payload = {};

                    try {
                        payload = JSON.parse(raw);
                    } catch (_) {
                        payload = {
                            ok: response.ok,
                            filename: file.name,
                            name: file.name,
                            mime_type: file.type,
                            size: file.size,
                            raw: raw
                        };
                    }

                    if (!response.ok || payload.ok === false) {
                        throw new Error(payload.error || payload.message || raw || "Upload failed");
                    }

                    var clean =
                        normalizeAttachment(payload) ||
                        normalizeAttachment(payload.file) ||
                        normalizeAttachment(payload.attachment) ||
                        normalizeAttachment({
                            filename: file.name,
                            name: file.name,
                            mime_type: file.type,
                            type: file.type,
                            size: file.size,
                            url: payload.url || payload.file_url || payload.path || ""
                        });

                    if (!clean) {
                        clean = {
                            filename: file.name,
                            name: file.name,
                            mime_type: file.type,
                            type: file.type,
                            size: file.size,
                            size_bytes: file.size,
                            url: "",
                            file_url: "",
                            path: ""
                        };
                    }

                    pendingAttachments.length = 0;
                    pendingAttachments.push(clean);
                    savePending();
                    renderPreview(clean);

                    if (typeof window.NovaMobileReceiveUploadedAttachment === "function") {
                        try {
                            window.NovaMobileReceiveUploadedAttachment(clean);
                        } catch (_) {}
                    }

                    log("uploaded and queued", clean);
                });
            })
            .catch(function (error) {
                log("upload failed", error);
                alert("Upload failed: " + (error && error.message ? error.message : String(error)));
            });
    }

    function findPreviewHost() {
        var selectors = [
            "#nova-mobile-upload-preview-owner",
            "#nova-mobile-attachment-preview",
            "#mobileAttachmentPreview",
            ".nova-mobile-upload-preview-owner",
            ".nova-mobile-attachment-preview",
            ".mobile-attachment-preview",
            "[data-mobile-attachment-preview]",
            "#nova-mobile-preview-bar"
        ];

        for (var i = 0; i < selectors.length; i += 1) {
            var el = document.querySelector(selectors[i]);
            if (el) return el;
        }

        var composer = document.getElementById("nova-mobile-composer");
        var host = document.createElement("div");

        host.id = "nova-mobile-upload-preview-owner";
        host.setAttribute("data-mobile-attachment-preview", "true");

        if (composer && composer.parentNode) {
            composer.parentNode.insertBefore(host, composer);
        } else {
            document.body.appendChild(host);
        }

        return host;
    }

    function renderPreview(item) {
        var host = findPreviewHost();
        if (!host) return;

        host.innerHTML = "";

        var chip = document.createElement("div");
        chip.className = "nova-mobile-upload-preview-chip";
        chip.setAttribute("data-nova-role", "attachment-preview-chip");
        chip.textContent = "Attached: " + (item.filename || item.name || "file");

        var clear = document.createElement("button");
        clear.type = "button";
        clear.textContent = "×";
        clear.setAttribute("aria-label", "Clear attachment");
        clear.style.marginLeft = "8px";

        clear.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            clearPendingAttachments();
        }, true);

        chip.appendChild(clear);
        host.appendChild(chip);

        host.hidden = false;
        host.style.setProperty("display", "flex", "important");
        host.style.setProperty("visibility", "visible", "important");
        host.style.setProperty("opacity", "1", "important");
        host.setAttribute("data-has-attachment", "1");

        document.body.classList.add("nova-mobile-has-attachment");
    }

    function clearPendingAttachments() {
        pendingAttachments.length = 0;
        savePending();

        [
            "nova_mobile_upload",
            "nova_mobile_uploads",
            "nova_mobile_pending_attachments",
            "nova_mobile_uploaded_attachments",
            "nova_mobile_attachment_queue",
            "nova_mobile_last_uploaded_attachment",
            "nova_mobile_pending_attachment",
            "nova_mobile_attachment",
            "nova_pending_attachment",
            "pending_attachment",
            "pending_attachments"
        ].forEach(function (key) {
            try {
                localStorage.removeItem(key);
                sessionStorage.removeItem(key);
            } catch (_) {}
        });

        document.querySelectorAll("input[type='file']").forEach(function (input) {
            try {
                input.value = "";
            } catch (_) {}
        });

        document.querySelectorAll([
            "#nova-mobile-upload-preview-owner",
            ".nova-mobile-upload-preview-owner",
            ".nova-mobile-upload-preview-chip",
            "[data-nova-role='attachment-preview-chip']",
            "#nova-mobile-attachment-preview",
            ".nova-mobile-attachment-preview",
            "#mobileAttachmentPreview",
            ".mobile-attachment-preview",
            "[data-mobile-attachment-preview]",
            "#nova-mobile-preview-bar",
            ".nova-mobile-preview-bar",
            ".nova-mobile-preview-strip",
            ".nova-mobile-upload-preview",
            ".nova-mobile-attachment-chip",
            ".nova-mobile-upload-chip",
            "[data-nova-attachment-preview]",
            "[data-nova-upload-preview]",
            "[data-nova-attachment-chip]",
            "[data-upload-preview]",
            "[data-attachment-preview]"
        ].join(",")).forEach(function (node) {
            try {
                node.innerHTML = "";
                node.hidden = true;
                node.style.setProperty("display", "none", "important");
                node.style.setProperty("visibility", "hidden", "important");
                node.style.setProperty("opacity", "0", "important");
                node.removeAttribute("data-has-attachment");
                node.classList.remove("open", "is-open", "active", "visible", "show", "has-attachment", "is-visible");
            } catch (_) {}
        });

        document.body.classList.remove(
            "nova-has-attachment",
            "nova-mobile-has-attachment",
            "nova-upload-active",
            "nova-attachment-active"
        );

        log("cleared pending attachments");
    }

    function isUploadButton(button) {
        if (!button) return false;

        var hay = [
            button.id,
            button.className,
            button.textContent,
            button.getAttribute("aria-label"),
            button.getAttribute("title"),
            button.getAttribute("data-action")
        ].join(" ").toLowerCase();

        if (hay.indexOf("send") >= 0) return false;
        if (hay.indexOf("session") >= 0) return false;
        if (hay.indexOf("voice") >= 0) return false;
        if (hay.indexOf("speak") >= 0) return false;
        if (hay.indexOf("stop") >= 0) return false;
        if (hay.indexOf("copy") >= 0) return false;
        if (hay.indexOf("regen") >= 0) return false;
        if (hay.indexOf("menu") >= 0 && hay.indexOf("upload") < 0 && hay.indexOf("attach") < 0) return false;

        return (
            button.id === "nova-mobile-attach" ||
            hay.indexOf("attach") >= 0 ||
            hay.indexOf("upload") >= 0 ||
            String(button.textContent || "").trim() === "+"
        );
    }

    function bindUploadButtons() {
        getOrCreateInput();

        Array.from(document.querySelectorAll("button, [role='button'], a")).forEach(function (button) {
            if (!isUploadButton(button)) return;
            if (button.dataset.novaUploadAuthorityBound === "1") return;

            button.dataset.novaUploadAuthorityBound = "1";
            button.removeAttribute("onclick");

            button.addEventListener("click", openPicker, true);

            button.style.setProperty("pointer-events", "auto", "important");
            button.style.setProperty("visibility", "visible", "important");
            button.style.setProperty("opacity", "1", "important");

            log("bound upload button", {
                id: button.id,
                text: String(button.textContent || "").trim()
            });
        });
    }

    function boot() {
        loadPending();
        bindUploadButtons();

        window.NovaMobileUpload = {
            version: MARK,
            openPicker: openPicker,
            open: openPicker,
            getPendingAttachments: function () {
                dedupePending();
                return pendingAttachments.slice();
            },
            clearPendingAttachments: clearPendingAttachments,
            clear: clearPendingAttachments,
            reset: clearPendingAttachments,
            addAttachment: function (item) {
                var clean = normalizeAttachment(item);
                if (!clean) return false;
                pendingAttachments.length = 0;
                pendingAttachments.push(clean);
                savePending();
                renderPreview(clean);
                return true;
            }
        };

        window.NovaMobileOpenUploadPicker = openPicker;
        window.NovaMobileClearPendingAttachments = clearPendingAttachments;

        log("ready");
    }

    document.addEventListener("DOMContentLoaded", boot);
    document.addEventListener("click", function () {
        setTimeout(bindUploadButtons, 50);
    }, true);

    var observer = new MutationObserver(function () {
        bindUploadButtons();
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true
    });

    setTimeout(boot, 50);
    setTimeout(boot, 250);
    setTimeout(boot, 900);

    boot();
})();