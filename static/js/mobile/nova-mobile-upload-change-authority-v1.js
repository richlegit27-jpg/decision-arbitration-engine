(function () {
    "use strict";

    var MARK = "NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_SINGLE_OWNER_20260705";
console.log("[NOVA PREVIEW OWNER LOADED 20260714]");

    if (window.__NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_SINGLE_OWNER_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_UPLOAD_CHANGE_AUTHORITY_SINGLE_OWNER_20260705__ = true;

    var pendingAttachments = [];

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

if (
    file &&
    file.type &&
    file.type.indexOf("image/") === 0 &&
    !clean.local_preview
) {
    clean.local_preview = URL.createObjectURL(file);
}


                    pendingAttachments.length = 0;
                    pendingAttachments.push(clean);
                    savePending();
try {
    console.log("[PREVIEW DEBUG] calling renderPreview", clean);
    if (typeof renderPreview === "function") renderPreview(clean);
    console.log("[PREVIEW DEBUG] renderPreview finished");
} catch (e) {
    console.error("[PREVIEW DEBUG] renderPreview failed", e);
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
                log("upload failed", error);
                alert("Upload failed: " + (error && error.message ? error.message : String(error)));
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

function renderPreview(item) {
    var host = findPreviewHost();
    if (!host) return;

    host.innerHTML = "";

    var chip = document.createElement("div");
    chip.className = "nova-mobile-upload-preview-chip";
    chip.setAttribute("data-nova-role", "attachment-preview-chip");

    var thumb = document.createElement("div");
    thumb.className = "nova-mobile-upload-preview-thumb";

    if (item.local_preview && String(item.type || "").indexOf("image/") === 0) {
var img =
    document.createElement("img");

img.src =
    item.local_preview;

img.style.width = "48px";
img.style.height = "48px";
img.style.maxWidth = "48px";
img.style.maxHeight = "48px";
img.style.objectFit = "cover";
img.style.borderRadius = "8px";

        img.alt = item.filename || "attachment";
        thumb.appendChild(img);
    } else {
        thumb.textContent = "📎";
    }

    var name = document.createElement("div");
    name.className = "nova-mobile-upload-preview-name";
    name.textContent = item.filename || item.name || "attachment";

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

    window.dispatchEvent(
        new CustomEvent("nova-mobile-attachments-clear-request")
    );

    return false;

}, true);

    chip.appendChild(thumb);
    chip.appendChild(name);
    chip.appendChild(remove);

    host.innerHTML = "";
host.appendChild(chip);

host.style.display = "flex";
host.style.flexDirection = "row";
host.style.alignItems = "center";
host.style.height = "56px";
host.style.maxHeight = "56px";

chip.style.display = "flex";
chip.style.flexDirection = "row";
chip.style.alignItems = "center";
chip.style.gap = "8px";
chip.style.height = "48px";
chip.style.minHeight = "48px";
chip.style.maxHeight = "48px";
chip.style.width = "fit-content";

thumb.style.width = "64px";
thumb.style.height = "64px";
thumb.style.flex = "0 0 64px";

var previewImage = thumb.querySelector("img");
if (previewImage) {
    previewImage.style.width = "64px";
    previewImage.style.height = "64px";
    previewImage.style.maxWidth = "64px";
    previewImage.style.maxHeight = "64px";
    previewImage.style.objectFit = "cover";
}

name.style.whiteSpace = "nowrap";
name.style.overflow = "hidden";
name.style.textOverflow = "ellipsis";

remove.style.width = "28px";
remove.style.height = "28px";
remove.style.minWidth = "28px";
remove.style.minHeight = "28px";

    host.hidden = false;
    host.style.setProperty("display", "flex", "important");
    host.style.setProperty("visibility", "visible", "important");
    host.style.setProperty("opacity", "1", "important");

    host.setAttribute("data-has-attachment", "1");
    document.body.classList.add("nova-mobile-has-attachment");
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
            clear: clearPendingAttachments,
            reset: clearPendingAttachments,
            addAttachment: function (item) {
                var clean = normalizeAttachment(item);
                if (!clean) return false;
if (
    file &&
    file.type &&
    file.type.indexOf("image/") === 0 &&
    !clean.local_preview
) {
    clean.local_preview = URL.createObjectURL(file);
}
                pendingAttachments.length = 0;
                pendingAttachments.push(clean);
                savePending();
                if (typeof renderPreview === "function") renderPreview(clean);
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