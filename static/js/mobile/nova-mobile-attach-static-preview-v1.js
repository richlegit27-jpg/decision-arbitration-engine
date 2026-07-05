(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACH_STATIC_PREVIEW_V1__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACH_STATIC_PREVIEW_V1__ = true;

    const LOG = "[Nova Attach Static Preview V1]";
    const INPUT_ID = "nova-mobile-file-input";
    const ATTACH_ID = "nova-mobile-attach";
    const PREVIEW_ID = "nova-mobile-attach-preview-static-v1";
    const STORE_KEY = "nova_mobile_upload";

    function keyOf(item) {
        return [
            item.original_name || item.name || item.filename || "",
            item.size || "",
            item.type || item.mime_type || ""
        ].join("::");
    }

    function dedupe(items) {
        const seen = new Set();

        return (items || []).filter(function (item) {
            const key = keyOf(item);

            if (!key || seen.has(key)) {
                return false;
            }

            seen.add(key);
            return true;
        });
    }

    function readQueue() {
        try {
            const parsed = JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
            return dedupe(Array.isArray(parsed) ? parsed : []);
        } catch (error) {
            return [];
        }
    }

    function saveQueue(queue) {
        const clean = dedupe(queue);

        window.NovaMobilePendingAttachments = clean;
        localStorage.setItem(STORE_KEY, JSON.stringify(clean));

        return clean;
    }

    function clearQueue() {
        saveQueue([]);
        renderPreview();
    }

    function nameOf(item) {
        return item.original_name || item.name || item.filename || "file";
    }

    function isImage(item) {
        const type = String(item.type || item.mime_type || "").toLowerCase();
        const name = String(nameOf(item)).toLowerCase();

        return type.startsWith("image/") || /\.(png|jpg|jpeg|gif|webp|bmp|svg)$/i.test(name);
    }

    function normalizeUpload(data, file) {
        const filename =
            data.filename ||
            data.saved_filename ||
            data.file_name ||
            data.name ||
            file.name;

        return {
            ok: data.ok !== false,
            id: data.id || data.attachment_id || filename,
            filename: filename,
            saved_filename: data.saved_filename || filename,
            original_name: data.original_name || data.originalName || file.name,
            name: file.name,
            type: data.type || data.mime_type || file.type || "application/octet-stream",
            mime_type: data.mime_type || data.type || file.type || "application/octet-stream",
            size: data.size || file.size || 0,
            url: data.url || data.file_url || data.public_url || data.path || "/api/uploads/" + encodeURIComponent(filename),
            uploaded_at: new Date().toISOString()
        };
    }

    function removeOldPreviewBars() {
        [
            "nova-mobile-attach-body-preview",
            "nova-mobile-attach-preview-owner-v2",
            "nova-mobile-attach-preview-owner-v3",
            "nova-mobile-attach-preview-owner-v4",
            "nova-mobile-attach-preview-safe-v5",
            "nova-mobile-attach-preview-native-v1",
            "nova-mobile-attach-preview-native-v2",
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

    function ensurePreviewBar() {
        removeOldPreviewBars();

        let bar = document.getElementById(PREVIEW_ID);

        if (!bar) {
            bar = document.createElement("div");
            bar.id = PREVIEW_ID;
            document.body.appendChild(bar);
        }

        bar.style.setProperty("position", "fixed", "important");
        bar.style.setProperty("left", "10px", "important");
        bar.style.setProperty("right", "10px", "important");
        bar.style.setProperty("bottom", "78px", "important");
        bar.style.setProperty("z-index", "999998", "important");
        bar.style.setProperty("display", "none", "important");
        bar.style.setProperty("gap", "8px", "important");
        bar.style.setProperty("align-items", "center", "important");
        bar.style.setProperty("overflow-x", "auto", "important");
        bar.style.setProperty("padding", "6px 2px", "important");
        bar.style.setProperty("pointer-events", "auto", "important");

        return bar;
    }

    function renderPreview() {
        const queue = saveQueue(readQueue());
        const bar = ensurePreviewBar();

        bar.innerHTML = "";

        if (!queue.length) {
            bar.style.setProperty("display", "none", "important");
            return;
        }

        bar.style.setProperty("display", "flex", "important");

        queue.forEach(function (item) {
            const chip = document.createElement("div");

            chip.style.setProperty("display", "flex", "important");
            chip.style.setProperty("align-items", "center", "important");
            chip.style.setProperty("gap", "7px", "important");
            chip.style.setProperty("max-width", "240px", "important");
            chip.style.setProperty("padding", "7px 9px", "important");
            chip.style.setProperty("border-radius", "14px", "important");
            chip.style.setProperty("background", "rgba(20,20,28,0.94)", "important");
            chip.style.setProperty("border", "1px solid rgba(255,255,255,0.18)", "important");
            chip.style.setProperty("color", "#fff", "important");
            chip.style.setProperty("font-size", "12px", "important");
            chip.style.setProperty("flex", "0 0 auto", "important");

            if (isImage(item)) {
                const img = document.createElement("img");
                img.src = item.url;
                img.alt = nameOf(item);
                img.style.setProperty("width", "34px", "important");
                img.style.setProperty("height", "34px", "important");
                img.style.setProperty("object-fit", "cover", "important");
                img.style.setProperty("border-radius", "9px", "important");
                chip.appendChild(img);
            } else {
                const icon = document.createElement("span");
                icon.textContent = "📎";
                chip.appendChild(icon);
            }

            const label = document.createElement("span");
            label.textContent = nameOf(item);
            label.style.setProperty("max-width", "150px", "important");
            label.style.setProperty("overflow", "hidden", "important");
            label.style.setProperty("white-space", "nowrap", "important");
            label.style.setProperty("text-overflow", "ellipsis", "important");
            chip.appendChild(label);

            const close = document.createElement("button");
            close.type = "button";
            close.textContent = "×";
            close.style.setProperty("width", "22px", "important");
            close.style.setProperty("height", "22px", "important");
            close.style.setProperty("border", "0", "important");
            close.style.setProperty("border-radius", "999px", "important");
            close.style.setProperty("background", "rgba(255,255,255,0.14)", "important");
            close.style.setProperty("color", "#fff", "important");
            close.style.setProperty("font-size", "16px", "important");
            close.style.setProperty("line-height", "20px", "important");
            close.style.setProperty("padding", "0", "important");

            close.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();

                saveQueue(readQueue().filter(function (queued) {
                    return keyOf(queued) !== keyOf(item);
                }));

                renderPreview();
            });

            chip.appendChild(close);
            bar.appendChild(chip);
        });

        console.log(LOG, "preview rendered", queue.map(nameOf));
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

        const queue = readQueue();
        queue.push(normalizeUpload(data, file));
        saveQueue(queue);
        renderPreview();
    }

    async function handleChange(event) {
        const input = event.currentTarget;
        const files = Array.from(input.files || []);

        console.log(LOG, "selected files", files.map(function (file) {
            return file.name;
        }));

        for (const file of files) {
            try {
                await uploadFile(file);
            } catch (error) {
                console.error(LOG, "upload failed", file.name, error);
                alert("Upload failed: " + file.name);
            }
        }

        input.value = "";
    }

    function installStyles() {
        const styleId = "nova-mobile-attach-static-style-v1";

        if (document.getElementById(styleId)) {
            return;
        }

        const style = document.createElement("style");
        style.id = styleId;
        style.textContent = `
            #nova-mobile-attach {
                position: relative !important;
                overflow: hidden !important;
                pointer-events: auto !important;
                cursor: pointer !important;
            }

            #nova-mobile-attach .nova-mobile-native-file-input,
            #nova-mobile-file-input {
                display: block !important;
                visibility: visible !important;
                position: absolute !important;
                inset: 0 !important;
                width: 100% !important;
                height: 100% !important;
                opacity: 0.01 !important;
                z-index: 999999 !important;
                pointer-events: auto !important;
                cursor: pointer !important;
            }
        `;

        document.head.appendChild(style);
    }

    function installApi() {
        window.NovaMobileUpload = Object.assign(window.NovaMobileUpload || {}, {
            getPendingAttachments: readQueue,
            clearPendingAttachments: clearQueue,
            renderPendingAttachments: renderPreview
        });

        window.NovaMobileAttachOwner = {
            clearQueue: clearQueue,
            getQueue: readQueue,
            renderPreview: renderPreview,
            debug: function () {
                const attach = document.getElementById(ATTACH_ID);
                const input = document.getElementById(INPUT_ID);
                const rect = attach ? attach.getBoundingClientRect() : null;
                const top = rect
                    ? document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)
                    : null;

                return {
                    installed: "static-preview-v1",
                    attachTag: attach ? attach.tagName : "",
                    hasInput: !!input,
                    topId: top ? top.id : "",
                    topTag: top ? top.tagName : "",
                    topIsInput: top === input,
                    queue: readQueue().map(function (item) {
                        return {
                            name: nameOf(item),
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
        const attach = document.getElementById(ATTACH_ID);
        const input = document.getElementById(INPUT_ID);

        if (!attach || !input) {
            console.warn(LOG, "missing attach/input", {
                attach: !!attach,
                input: !!input
            });
            return;
        }

        input.disabled = false;
        input.onchange = handleChange;

        installStyles();
        installApi();
        renderPreview();

        console.log(LOG, "installed");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", install, { once: true });
    } else {
        install();
    }
})();
