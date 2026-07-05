(function () {
    "use strict";

    if (window.__NOVA_MOBILE_UPLOAD_NO_LAYOUT_OWNER_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_UPLOAD_NO_LAYOUT_OWNER_20260705__ = true;

    var pendingAttachments = [];
    var fileInput = null;
    var lastPickerOpenAt = 0;

    function log() {
        try {
            console.log.apply(console, ["[Nova Mobile Upload No Layout Owner]"].concat([].slice.call(arguments)));
        } catch (_) {}
    }

    function findAttachButton() {
        return (
            document.getElementById("nova-mobile-attach") ||
            document.querySelector("[aria-label='Attach']") ||
            document.querySelector("[title='Attach']") ||
            document.querySelector("[data-mobile-tool='attach']")
        );
    }

    function ensureFileInput() {
        if (fileInput && document.body.contains(fileInput)) {
            return fileInput;
        }

        fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.multiple = true;
        fileInput.id = "nova-mobile-file-input";
        fileInput.setAttribute("data-nova-upload-owner", "no-layout");

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
            file_url: data.file_url || url,
            path: data.path || url,
            upload: data
        };
    }

    function syncGlobals() {
        var clean = pendingAttachments.slice();

        window.NovaMobilePendingAttachments = clean;
        window.NovaMobileAttachments = clean;
        window.novaMobilePendingAttachments = clean;
        window.__novaMobilePendingAttachments = clean;

        try {
            localStorage.setItem("nova_mobile_upload", JSON.stringify(clean));
            localStorage.setItem("nova_mobile_attachment", JSON.stringify(clean));
            localStorage.setItem("nova_pending_attachment", JSON.stringify(clean));
        } catch (_) {}
    }

    function dispatch(name, detail) {
        try {
            window.dispatchEvent(new CustomEvent(name, { detail: detail }));
        } catch (_) {}
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
            data = { ok: false, error: "Upload response was not JSON" };
        }

        if (!response.ok || data.ok === false) {
            throw new Error(data.error || data.message || "Upload failed");
        }

        return normalizeUploadResponse(data, file);
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

                dispatch("nova-mobile-upload-complete", item);
                dispatch("nova-mobile-attachment-uploaded", item);
                dispatch("nova-mobile-attachments-changed", {
                    pendingAttachments: pendingAttachments.slice(),
                    attachments: pendingAttachments.slice()
                });

                log("uploaded", item.filename || item.name);
            } catch (error) {
                console.error("[Nova Mobile Upload No Layout Owner] upload failed", error);
                dispatch("nova-mobile-upload-error", {
                    error: String(error && error.message ? error.message : error),
                    file: files[i] ? files[i].name : ""
                });
            }
        }

        input.value = "";
    }

    function openUploadPicker() {
        var now = Date.now();

        if (now - lastPickerOpenAt < 1500) {
            log("duplicate picker blocked");
            return false;
        }

        lastPickerOpenAt = now;

        var input = ensureFileInput();

        try {
            input.click();
            log("picker opened");
            return true;
        } catch (error) {
            console.error("[Nova Mobile Upload No Layout Owner] picker failed", error);
            return false;
        }
    }

    function bindAttachButton() {
        var button = findAttachButton();

        if (!button || button.__novaUploadNoLayoutBound) {
            return;
        }

        button.__novaUploadNoLayoutBound = true;
        button.setAttribute("data-nova-upload-no-layout-owner", "true");

        button.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            if (event.stopImmediatePropagation) {
                event.stopImmediatePropagation();
            }

            openUploadPicker();
            return false;
        }, true);

        log("bound attach button");
    }

    function clearAttachments() {
        pendingAttachments = [];
        syncGlobals();

        dispatch("nova-mobile-attachments-cleared", {
            pendingAttachments: [],
            attachments: []
        });
    }

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
        bindAttachButton();
        syncGlobals();
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
        getPendingAttachments: function () {
            return pendingAttachments.slice();
        }
    };

    window.NovaClearMobileAttachmentsAfterSend = clearAttachments;

    log("installed");
})();
