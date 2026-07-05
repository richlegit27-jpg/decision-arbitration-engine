(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACH_BODY_OWNER_V2__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACH_BODY_OWNER_V2__ = true;

    const LOG = "[Nova Attach Body Owner V2]";
    const INPUT_ID = "nova-mobile-file-input";
    const BUTTON_ID = "nova-mobile-attach";
    const PREVIEW_ID = "nova-mobile-attach-preview-owner-v2";
    const STORE_KEY = "nova_mobile_upload";
    const ACCEPT = "image/*,.txt,.md,.json,.js,.py,.css,.html,.pdf,.docx";

    let input = null;
    let syncBusy = false;

    function getButton() {
        return document.getElementById(BUTTON_ID);
    }

    function attachmentKey(item) {
        if (!item) {
            return "";
        }

        return String(
            item.id ||
            item.url ||
            item.file_url ||
            item.filename ||
            item.saved_filename ||
            item.original_name ||
            item.name ||
            ""
        ) + "::" + String(item.size || "");
    }

    function uniqueAttachments(items) {
        const seen = new Set();
        const output = [];

        (items || []).forEach(function (item) {
            if (!item) {
                return;
            }

            const key = attachmentKey(item);

            if (!key || seen.has(key)) {
                return;
            }

            seen.add(key);
            output.push(item);
        });

        return output;
    }

    function readStoredQueue() {
        try {
            const parsed = JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
            return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
            console.warn(LOG, "bad stored queue", error);
            return [];
        }
    }

    function getQueue() {
        const globalQueue = Array.isArray(window.NovaMobilePendingAttachments)
            ? window.NovaMobilePendingAttachments
            : [];

        const storedQueue = readStoredQueue();
        const queue = uniqueAttachments(globalQueue.concat(storedQueue));

        window.NovaMobilePendingAttachments = queue;
        return queue;
    }

    function saveQueue(queue) {
        const clean = uniqueAttachments(queue);

        window.NovaMobilePendingAttachments = clean;

        try {
            localStorage.setItem(STORE_KEY, JSON.stringify(clean));
        } catch (error) {
            console.warn(LOG, "could not save queue", error);
        }

        return clean;
    }

    function clearQueue() {
        saveQueue([]);
        renderPreview();
    }

    function removeAttachment(key) {
        const queue = getQueue().filter(function (item) {
            return attachmentKey(item) !== key;
        });

        saveQueue(queue);
        renderPreview();
    }

    function normalizeAttachment(data, file) {
        const filename =
            data.filename ||
            data.saved_filename ||
            data.file_name ||
            data.name ||
            file.name;

        const url =
            data.url ||
            data.file_url ||
            data.public_url ||
            data.path ||
            "/api/uploads/" + encodeURIComponent(filename);

        return {
            ok: data.ok !== false,
            id: data.id || data.attachment_id || url || filename,
            filename: filename,
            saved_filename: data.saved_filename || filename,
            original_name: data.original_name || data.originalName || file.name,
            name: file.name,
            type: data.type || data.mime_type || file.type || "application/octet-stream",
            mime_type: data.mime_type || data.type || file.type || "application/octet-stream",
            size: data.size || file.size || 0,
            url: url,
            uploaded_at: new Date().toISOString()
        };
    }

    function addAttachment(attachment) {
        const queue = getQueue();
        queue.push(attachment);

        const clean = saveQueue(queue);
        renderPreview();

        return clean;
    }

    function removeOldPreviewBars() {
        [
            "nova-mobile-attach-body-preview",
            "nova-mobile-upload-preview",
            "nova-mobile-preview-bar",
            "mobileAttachPreview",
            "mobile-attach-preview"
        ].forEach(function (id) {
            const el = document.getElementById(id);

            if (el && el.id !== PREVIEW_ID) {
                el.remove();
            }
        });
    }

    function isImageAttachment(item) {
        const type = String(item.type || item.mime_type || "").toLowerCase();
        const name = String(item.original_name || item.filename || item.name || "").toLowerCase();

        return (
            type.startsWith("image/") ||
            /\.(png|jpg|jpeg|gif|webp|bmp|svg)$/i.test(name)
        );
    }

    function displayName(item) {
        return item.original_name || item.name || item.filename || "file";
    }

    function ensurePreviewBar() {
        removeOldPreviewBars();

        let bar = document.getElementById(PREVIEW_ID);

        if (!bar) {
            bar = document.createElement("div");
            bar.id = PREVIEW_ID;
            bar.dataset.novaAttachPreviewOwner = "body-owner-v2";
            document.body.appendChild(bar);
        }

        bar.style.setProperty("position", "fixed", "important");
        bar.style.setProperty("left", "10px", "important");
        bar.style.setProperty("right", "10px", "important");
        bar.style.setProperty("bottom", "78px", "important");
        bar.style.setProperty("z-index", "999998", "important");
        bar.style.setProperty("display", "flex", "important");
        bar.style.setProperty("gap", "8px", "important");
        bar.style.setProperty("align-items", "center", "important");
        bar.style.setProperty("overflow-x", "auto", "important");
        bar.style.setProperty("padding", "6px 2px", "important");
        bar.style.setProperty("pointer-events", "auto", "important");
        bar.style.setProperty("-webkit-overflow-scrolling", "touch", "important");

        return bar;
    }

    function renderPreview() {
        const queue = saveQueue(getQueue());
        const bar = ensurePreviewBar();

        bar.innerHTML = "";

        if (!queue.length) {
            bar.style.setProperty("display", "none", "important");
            return;
        }

        bar.style.setProperty("display", "flex", "important");

        queue.forEach(function (item) {
            const key = attachmentKey(item);

            const chip = document.createElement("div");
            chip.dataset.attachmentKey = key;

            chip.style.setProperty("display", "flex", "important");
            chip.style.setProperty("align-items", "center", "important");
            chip.style.setProperty("gap", "7px", "important");
            chip.style.setProperty("min-width", "0", "important");
            chip.style.setProperty("max-width", "240px", "important");
            chip.style.setProperty("padding", "7px 9px", "important");
            chip.style.setProperty("border-radius", "14px", "important");
            chip.style.setProperty("background", "rgba(20,20,28,0.94)", "important");
            chip.style.setProperty("border", "1px solid rgba(255,255,255,0.18)", "important");
            chip.style.setProperty("box-shadow", "0 8px 22px rgba(0,0,0,0.28)", "important");
            chip.style.setProperty("color", "#fff", "important");
            chip.style.setProperty("font-size", "12px", "important");
            chip.style.setProperty("line-height", "1.2", "important");
            chip.style.setProperty("flex", "0 0 auto", "important");

            if (isImageAttachment(item)) {
                const img = document.createElement("img");
                img.alt = displayName(item);
                img.src = item.url;
                img.style.setProperty("width", "34px", "important");
                img.style.setProperty("height", "34px", "important");
                img.style.setProperty("object-fit", "cover", "important");
                img.style.setProperty("border-radius", "9px", "important");
                img.style.setProperty("background", "rgba(255,255,255,0.08)", "important");
                chip.appendChild(img);
            } else {
                const icon = document.createElement("span");
                icon.textContent = "📎";
                icon.style.setProperty("font-size", "17px", "important");
                chip.appendChild(icon);
            }

            const label = document.createElement("span");
            label.textContent = displayName(item);
            label.style.setProperty("overflow", "hidden", "important");
            label.style.setProperty("text-overflow", "ellipsis", "important");
            label.style.setProperty("white-space", "nowrap", "important");
            label.style.setProperty("min-width", "0", "important");
            label.style.setProperty("max-width", "150px", "important");
            chip.appendChild(label);

            const remove = document.createElement("button");
            remove.type = "button";
            remove.textContent = "×";
            remove.setAttribute("aria-label", "Remove attachment");
            remove.style.setProperty("width", "22px", "important");
            remove.style.setProperty("height", "22px", "important");
            remove.style.setProperty("border", "0", "important");
            remove.style.setProperty("border-radius", "999px", "important");
            remove.style.setProperty("background", "rgba(255,255,255,0.14)", "important");
            remove.style.setProperty("color", "#fff", "important");
            remove.style.setProperty("font-size", "16px", "important");
            remove.style.setProperty("line-height", "20px", "important");
            remove.style.setProperty("padding", "0", "important");
            remove.style.setProperty("cursor", "pointer", "important");
            remove.style.setProperty("pointer-events", "auto", "important");

            remove.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                removeAttachment(key);
            });

            chip.appendChild(remove);
            bar.appendChild(chip);
        });

        console.log(LOG, "preview rendered", queue.map(function (item) {
            return displayName(item);
        }));
    }

    function disableOldFileInputs() {
        document.querySelectorAll("input[type='file']").forEach(function (el, index) {
            if (el === input) {
                return;
            }

            el.id = "nova-mobile-old-file-input-" + index;
            el.disabled = true;
            el.style.setProperty("display", "none", "important");
            el.style.setProperty("visibility", "hidden", "important");
            el.style.setProperty("pointer-events", "none", "important");
        });
    }

    function ensureInput() {
        if (input && document.body.contains(input)) {
            return input;
        }

        input = document.createElement("input");
        input.type = "file";
        input.id = INPUT_ID;
        input.multiple = true;
        input.accept = ACCEPT;
        input.autocomplete = "off";
        input.setAttribute("aria-label", "Attach file");

        input.removeAttribute("hidden");
        input.removeAttribute("disabled");
        input.removeAttribute("inert");
        input.disabled = false;

        input.style.setProperty("display", "block", "important");
        input.style.setProperty("visibility", "visible", "important");
        input.style.setProperty("position", "fixed", "important");
        input.style.setProperty("opacity", "0.01", "important");
        input.style.setProperty("z-index", "2147483647", "important");
        input.style.setProperty("pointer-events", "auto", "important");
        input.style.setProperty("margin", "0", "important");
        input.style.setProperty("padding", "0", "important");

        input.addEventListener("change", handleSelectedFiles);

        document.body.appendChild(input);
        return input;
    }

    function syncOverlay() {
        if (syncBusy) {
            return;
        }

        syncBusy = true;

        try {
            const button = getButton();

            if (!button) {
                if (input) {
                    input.style.setProperty("display", "none", "important");
                }

                return;
            }

            ensureInput();
            disableOldFileInputs();

            const rect = button.getBoundingClientRect();

            if (!rect.width || !rect.height) {
                input.style.setProperty("display", "none", "important");
                return;
            }

            button.disabled = false;
            button.style.setProperty("pointer-events", "none", "important");
            button.style.setProperty("z-index", "1", "important");

            input.disabled = false;
            input.style.setProperty("display", "block", "important");
            input.style.setProperty("visibility", "visible", "important");
            input.style.setProperty("position", "fixed", "important");
            input.style.setProperty("left", rect.left + "px", "important");
            input.style.setProperty("top", rect.top + "px", "important");
            input.style.setProperty("width", rect.width + "px", "important");
            input.style.setProperty("height", rect.height + "px", "important");
            input.style.setProperty("opacity", "0.01", "important");
            input.style.setProperty("z-index", "2147483647", "important");
            input.style.setProperty("pointer-events", "auto", "important");
        } finally {
            syncBusy = false;
        }
    }

    async function uploadFile(file) {
        const form = new FormData();
        form.append("file", file, file.name);

        const response = await fetch("/api/upload", {
            method: "POST",
            body: form,
            credentials: "same-origin"
        });

        let data = {};

        try {
            data = await response.json();
        } catch (error) {
            data = {
                ok: false,
                error: "Upload response was not JSON"
            };
        }

        if (!response.ok || data.ok === false) {
            throw new Error(data.error || data.message || "Upload failed");
        }

        const attachment = normalizeAttachment(data, file);
        addAttachment(attachment);

        console.log(LOG, "uploaded", attachment);
        return attachment;
    }

    async function handleSelectedFiles() {
        const files = Array.from(input.files || []);

        console.log(LOG, "selected files", files.map(function (file) {
            return {
                name: file.name,
                type: file.type,
                size: file.size
            };
        }));

        if (!files.length) {
            return;
        }

        for (const file of files) {
            try {
                await uploadFile(file);
            } catch (error) {
                console.error(LOG, "upload failed", file.name, error);
                alert("Upload failed: " + file.name);
            }
        }

        input.value = "";
        syncOverlay();
        renderPreview();
    }

    function installPublicApi() {
        const existing = window.NovaMobileUpload || {};

        window.NovaMobileUpload = Object.assign(existing, {
            getPendingAttachments: getQueue,
            addPendingAttachment: addAttachment,
            clearPendingAttachments: clearQueue,
            removePendingAttachment: removeAttachment,
            renderPendingAttachments: renderPreview
        });

        window.NovaMobileAttachOwner = {
            getQueue: getQueue,
            clearQueue: clearQueue,
            renderPreview: renderPreview,
            syncOverlay: syncOverlay,
            debug: function () {
                const button = getButton();
                const currentInput = document.getElementById(INPUT_ID);
                const rect = button ? button.getBoundingClientRect() : null;
                const top = rect
                    ? document.elementFromPoint(
                        rect.left + rect.width / 2,
                        rect.top + rect.height / 2
                    )
                    : null;

                return {
                    installed: true,
                    hasButton: !!button,
                    hasInput: !!currentInput,
                    topId: top ? top.id : "",
                    topTag: top ? top.tagName : "",
                    topIsInput: top === currentInput,
                    queue: getQueue().map(function (item) {
                        return {
                            name: displayName(item),
                            url: item.url,
                            type: item.type || item.mime_type,
                            size: item.size
                        };
                    }),
                    previewChildren: document.getElementById(PREVIEW_ID)
                        ? document.getElementById(PREVIEW_ID).children.length
                        : 0
                };
            }
        };
    }

    function install() {
        installPublicApi();
        ensureInput();
        syncOverlay();
        renderPreview();

        window.addEventListener("resize", syncOverlay, true);
        window.addEventListener("scroll", syncOverlay, true);
        window.addEventListener("orientationchange", syncOverlay, true);

        document.addEventListener("touchstart", syncOverlay, true);
        document.addEventListener("pointerdown", syncOverlay, true);
        document.addEventListener("click", syncOverlay, true);

        setInterval(function () {
            syncOverlay();
            renderPreview();
        }, 1000);

        const observer = new MutationObserver(function () {
            syncOverlay();
        });

        observer.observe(document.documentElement, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["style", "class", "id"]
        });

        console.log(LOG, "installed");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", install);
    } else {
        install();
    }
})();
