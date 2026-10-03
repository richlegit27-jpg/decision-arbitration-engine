(function () {
    "use strict";

    var MARK = "NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_SINGLE_OWNER_20260705";
console.log("[NOVA PREVIEW OWNER LOADED 20260714]");

    if (window.__NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_SINGLE_OWNER_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_SINGLE_OWNER_20260705__ = true;

    var pendingAttachments = [];
    var removedClientIds = new Set();

try {
    var saved = localStorage.getItem("nova_mobile_upload");

    if (saved) {
        var parsed = JSON.parse(saved);

        if (Array.isArray(parsed)) {
            pendingAttachments = parsed.slice();
        }
    }
} catch (e) {}

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
            size_bytes: size,
            client_id: value.client_id || value.id || value.attachment_id || "",
            pending_upload: value.pending_upload === true,
            upload_error: value.upload_error === true,
            error_message: value.error_message || "",
            local_preview: String(value.local_preview || "").startsWith("blob:") ? "" : (value.local_preview || "")
        };
    }

    function savePending() {
        try {
            localStorage.setItem("nova_mobile_upload", JSON.stringify(pendingAttachments));
            localStorage.setItem("nova_mobile_pending_attachments", JSON.stringify(pendingAttachments));
        } catch (_) {}

        window.NovaMobilePendingAttachments = pendingAttachments;
        window.NovaMobileAttachments = pendingAttachments;
        window.novaMobilePendingAttachments = pendingAttachments;
        window.__novaMobilePendingAttachments = pendingAttachments;
        window.NovaMobileUploadedAttachments = pendingAttachments;
        window.NovaMobileAttachmentQueue = pendingAttachments;
        window.NovaMobileUploadQueue = pendingAttachments;
        window.NovaMobileSharedAttachments = pendingAttachments;
        window.NovaPendingAttachments = pendingAttachments;
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
                    if (clean) {
                        if (clean.pending_upload && !clean.url) {
                            clean.pending_upload = false;
                            clean.upload_error = true;
                            clean.error_message = "Upload stopped before the page was closed. Select the file again.";
                        }
                        pendingAttachments.push(clean);
                    }
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
                item.client_id || item.id || "",
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
            input.multiple = true;
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
                var files = Array.from(input.files || []);
                if (!files.length) {
                    log("no file selected");
                    return;
                }
                files.forEach(uploadFile);
                input.value = "";
            }, true);
        }

        return input;
    }

if (
    event &&
    event.target &&
    event.target.closest &&
    event.target.closest("[data-nova-upload-remove='1']")
) {
    return false;
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
        var clientId = "mobile-" + Date.now() + "-" + Math.random().toString(36).slice(2, 9);
        var localItem = {
            id: clientId,
            client_id: clientId,
            filename: file.name || "Attachment",
            name: file.name || "Attachment",
            mime_type: file.type || "",
            type: file.type || "",
            size: Number(file.size) || 0,
            local_preview: file.type && file.type.indexOf("image/") === 0 ? URL.createObjectURL(file) : "",
            pending_upload: true
        };
        removedClientIds.delete(clientId);
        pendingAttachments.push(localItem);
        savePending();
        renderPreview(pendingAttachments);
        log("selected attachment", { filename: localItem.filename, type: localItem.type, size: localItem.size });

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
                        payload = { ok: false };
                    }

                    if (!response.ok || payload.ok === false) {
                        var uploadError = new Error(
                            response.status === 401 || response.status === 403 ? "Your session expired. Sign in again, then retry this file." :
                            response.status === 413 ? "This file is too large to upload." :
                            response.status === 415 ? "This file type is not supported." :
                            response.status === 400 ? "Nova could not accept this file. Check its type and try again." :
                            "The upload did not finish. Check your connection and try again."
                        );
                        uploadError.status = response.status;
                        throw uploadError;
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

if (
    file &&
    file.type &&
    file.type.indexOf("image/") === 0 &&
    !clean.local_preview
) {
    clean.local_preview = URL.createObjectURL(file);
}


                    clean.client_id = clientId;
                    clean.pending_upload = false;
                    if (localItem.local_preview && String(localItem.local_preview).startsWith("blob:")) URL.revokeObjectURL(localItem.local_preview);
                    clean.local_preview = "";
                    if (removedClientIds.has(clientId)) return;
                    var itemIndex = pendingAttachments.findIndex(function (item) { return item.client_id === clientId; });
                    if (itemIndex >= 0) pendingAttachments.splice(itemIndex, 1, clean);
                    else return;
                    savePending();
try {
    renderPreview(pendingAttachments);
} catch (e) {
    console.error("[NOVA PREVIEW] render failed", e);
}
                    if (typeof window.NovaMobileReceiveUploadedAttachment === "function") {
                        try {
                            window.NovaMobileReceiveUploadedAttachment(clean);
                        } catch (_) {}
                    }

                    log("uploaded and queued", clean);
                });
            })
            .catch(function (error) {
                console.error("[NOVA MOBILE UPLOAD] upload failed", { status: error?.status || 0, message: error?.message || "Upload failed" });
                if (removedClientIds.has(clientId)) return;
                var current = pendingAttachments.find(function (item) { return item.client_id === clientId; });
                if (current) {
                    current.pending_upload = false;
                    current.upload_error = true;
                    current.error_message = error?.message || "The upload did not finish. Check your connection and try again.";
                    savePending();
                    renderPreview(pendingAttachments);
                }
            });
    }

 function findPreviewHost() {
    var existing = document.querySelector("#nova-mobile-upload-preview-owner");

    if (existing) {
        return existing;
    }

    var composer =
        document.getElementById("nova-mobile-composer") ||
        document.querySelector(".mobile-composer") ||
        document.querySelector(".mobile-composer-shell") ||
        document.querySelector(".mobile-input-bar");

    if (!composer) {
        console.error("[NOVA PREVIEW] composer missing");
        return null;
    }

    var host = document.createElement("div");

    host.id = "nova-mobile-upload-preview-owner";
    host.setAttribute("data-mobile-attachment-preview", "true");

    composer.insertBefore(host, composer.firstChild);

    return host;
}

function renderPreview(inputItems) {
    var host = findPreviewHost();
    if (!host) return;

    host.innerHTML = "";
    var items = Array.isArray(inputItems) ? inputItems : (inputItems ? [inputItems] : []);
    if (!items.length) {
        host.hidden = true;
        host.style.display = "none";
        host.removeAttribute("data-has-attachment");
        document.body.classList.remove("nova-mobile-has-attachment");
        return;
    }
    var chips = document.createElement("div");
    chips.className = "nova-mobile-upload-preview-list";
    items.forEach(function (item) {
    var chip = document.createElement("div");
    chip.className = "nova-mobile-upload-preview-chip";
    chip.setAttribute("data-nova-role", "attachment-preview-chip");

    var thumb = document.createElement("div");
    thumb.className = "nova-mobile-upload-preview-thumb";

    if ((item.local_preview || item.url) && String(item.type || item.mime_type || "").indexOf("image/") === 0) {
var img =
    document.createElement("img");

img.src =
    item.local_preview || item.url;

img.style.width = "48px";
img.style.height = "48px";
img.style.maxWidth = "48px";
img.style.maxHeight = "48px";
img.style.objectFit = "cover";
img.style.borderRadius = "8px";

        img.alt = item.filename || "attachment";
        thumb.appendChild(img);
} else {
    var ext = String(item.filename || item.name || "")
        .split(".")
        .pop()
        .toLowerCase();

    var icon = "📄";

    if (ext === "pdf") {
        icon = "📕";
    } else if (
        ext === "doc" ||
        ext === "docx"
    ) {
        icon = "📘";
    } else if (
        ext === "xls" ||
        ext === "xlsx"
    ) {
        icon = "📊";
    } else if (
        ext === "txt" ||
        ext === "md"
    ) {
        icon = "📄";
    }

    thumb.textContent = icon;
    thumb.style.display = "flex";
    thumb.style.alignItems = "center";
    thumb.style.justifyContent = "center";
    thumb.style.fontSize = "24px";
}

    var name = document.createElement("div");
    name.className = "nova-mobile-upload-preview-name";
    name.textContent = item.filename || item.name || "attachment";

    var meta = document.createElement("div");
    meta.className = "nova-mobile-upload-preview-meta";
    meta.appendChild(name);
    var info = document.createElement("small");
    info.className = "nova-mobile-upload-preview-info";
    var byteCount = Number(item.size || item.size_bytes || 0);
    var sizeLabel = byteCount >= 1048576 ? (byteCount / 1048576).toFixed(1) + " MB" : byteCount >= 1024 ? Math.round(byteCount / 1024) + " KB" : (byteCount ? byteCount + " B" : "");
    var typeLabel = String(item.mime_type || item.type || "File").split("/").pop();
    info.textContent = [typeLabel, sizeLabel].filter(Boolean).join(" · ");
    meta.appendChild(info);
    var uploadState = document.createElement("small");
    uploadState.className = "nova-mobile-upload-preview-state";
    uploadState.textContent = item.pending_upload ? "Uploading…" : item.upload_error ? "Upload failed" : "Ready to send";
    meta.appendChild(uploadState);

    var remove = document.createElement("button");
    remove.className = "nova-mobile-upload-preview-remove";
    remove.type = "button";
remove.setAttribute("data-nova-upload-remove", "1");
    remove.textContent = "×";
    remove.setAttribute("aria-label", "Remove attachment");

remove.addEventListener("click", function (event) {
    event.preventDefault();

    if (event.stopImmediatePropagation) {
        event.stopImmediatePropagation();
    }

    event.stopPropagation();

    removeAttachment(item.client_id || item.id);

    return false;

}, true);

    chip.appendChild(thumb);
    chip.dataset.uploadState = item.upload_error ? "failed" : item.pending_upload ? "uploading" : "ready";
    chip.appendChild(meta);
    chip.appendChild(remove);
    if (item.error_message) {
        var message = document.createElement("small");
        message.className = "nova-mobile-upload-error";
        message.textContent = item.error_message;
        chip.appendChild(message);
    }
    chips.appendChild(chip);
    });
    host.appendChild(chips);
    host.style.display = "flex";
    host.style.alignItems = "center";
    host.style.height = "auto";
    host.style.maxHeight = "92px";
    host.style.overflowX = "auto";

chip.style.display = "flex";
chip.style.alignItems = "center";
chip.style.gap = "10px";
chip.style.padding = "6px 10px";
chip.style.borderRadius = "12px";
chip.style.maxWidth = "88vw";
chip.style.background = "rgba(255,255,255,.08)";

thumb.style.width = "40px";
thumb.style.height = "40px";
thumb.style.flex = "0 0 40px";

var previewImage = thumb.querySelector("img");
if (previewImage) {
    previewImage.style.width = "40px";
    previewImage.style.height = "40px";
    previewImage.style.objectFit = "cover";
    previewImage.style.borderRadius = "8px";
}

name.style.maxWidth = "48vw";
name.style.whiteSpace = "nowrap";
name.style.overflow = "hidden";
name.style.textOverflow = "ellipsis";
name.style.fontSize = "13px";

remove.style.marginLeft = "auto";
remove.style.width = "28px";
remove.style.height = "28px";
remove.style.borderRadius = "50%";
    host.hidden = false;
    host.style.setProperty("display", "flex", "important");
    host.style.setProperty("visibility", "visible", "important");
    host.style.setProperty("opacity", "1", "important");

    host.setAttribute("data-has-attachment", "1");
    document.body.classList.add("nova-mobile-has-attachment");
}

function removeAttachment(clientId) {
    var index = pendingAttachments.findIndex(function (item) { return (item.client_id || item.id) === clientId; });
    if (clientId) removedClientIds.add(clientId);
    if (index < 0) return;
    var removed = pendingAttachments.splice(index, 1)[0];
    if (removed?.local_preview && String(removed.local_preview).startsWith("blob:")) URL.revokeObjectURL(removed.local_preview);
    savePending();
    renderPreview(pendingAttachments);
}

window.NovaMobileRenderPreview = renderPreview;

if (!window.__NOVA_PREVIEW_EVENT_BOUND__) {
    window.__NOVA_PREVIEW_EVENT_BOUND__ = true;

window.addEventListener("nova-mobile-attachment-preview", function (event) {
    try {
        if (!event.detail) return;

        console.log("[PREVIEW EVENT RECEIVED]", event.detail);

        var item = event.detail;

        if (
            !item.local_preview &&
            item.type &&
            item.type.indexOf("image/") === 0 &&
            item.url
        ) {
            item.local_preview = item.url;
        }

        if (typeof window.NovaMobileRenderPreview === "function") {
            window.NovaMobileRenderPreview(item);
        }

    } catch (error) {
        console.error("[PREVIEW EVENT FAILED]", error);
    }
});
}

function clearPendingAttachments() {
    pendingAttachments.forEach(function (item) {
        if (item?.client_id || item?.id) removedClientIds.add(item.client_id || item.id);
    });
    pendingAttachments.forEach(function (item) {
        if (item?.local_preview && String(item.local_preview).startsWith("blob:")) URL.revokeObjectURL(item.local_preview);
    });
    pendingAttachments.length = 0;

    window.NovaMobilePendingAttachments = [];
    window.NovaMobileAttachments = [];
    window.novaMobilePendingAttachments = [];
    window.__novaMobilePendingAttachments = [];

    try {
        localStorage.removeItem("nova_mobile_upload");
        localStorage.removeItem("nova_mobile_attachment");
        localStorage.removeItem("nova_pending_attachment");
        localStorage.removeItem("nova_mobile_pending_attachments");
        localStorage.removeItem("nova_mobile_uploaded_attachments");
        localStorage.removeItem("nova_mobile_attachment_queue");
    } catch (_) {}

    document.querySelectorAll([
        "#nova-mobile-upload-preview-owner",
        ".nova-mobile-upload-preview-chip",
        "[data-nova-role='attachment-preview-chip']"
    ].join(",")).forEach(function (node) {
        node.innerHTML = "";
        node.hidden = true;
        node.style.setProperty("display", "none", "important");
    });

    document.body.classList.remove("nova-mobile-has-attachment");

    log("cleared all attachment state");
}

window.addEventListener("nova-mobile-attachments-clear-request", function () {
    clearPendingAttachments();
});

["nova-mobile-after-send", "nova-mobile-message-sent", "nova-mobile-send-complete", "nova-mobile-attachments-cleared"].forEach(function (eventName) {
    window.addEventListener(eventName, clearPendingAttachments);
});

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
    if (pendingAttachments.length) {
        return pendingAttachments.slice();
    }

    try {
        var saved = localStorage.getItem("nova_mobile_upload");

        if (saved) {
            var parsed = JSON.parse(saved);

            if (Array.isArray(parsed)) {
                return parsed.slice();
            }
        }
    } catch (e) {}

    return [];
},

            clearPendingAttachments: clearPendingAttachments,
            removeAttachment: removeAttachment,
            clear: clearPendingAttachments,
            reset: clearPendingAttachments,
            addAttachment: function (item) {
                var clean = normalizeAttachment(item);
                if (!clean) return false;
                clean.client_id = clean.client_id || clean.id || ("mobile-" + Date.now());
                pendingAttachments.push(clean);
                savePending();
                if (typeof renderPreview === "function") renderPreview(pendingAttachments);
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
