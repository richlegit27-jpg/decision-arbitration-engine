(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACH_NATIVE_LABEL_V1__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACH_NATIVE_LABEL_V1__ = true;

    const LOG = "[Nova Attach Native Label V1]";
    const BUTTON_ID = "nova-mobile-attach";
    const INPUT_ID = "nova-mobile-file-input";
    const PREVIEW_ID = "nova-mobile-attach-preview-native-v1";
    const STORE_KEY = "nova_mobile_upload";
    const ACCEPT = "image/*,.txt,.md,.json,.js,.py,.css,.html,.pdf,.docx";

    let fileInput = null;

    function keyOf(item) {
        return [
            item.original_name || item.name || item.filename || "",
            item.size || "",
            item.type || item.mime_type || ""
        ].join("::");
    }

    function dedupe(items) {
        const seen = new Set();
        const output = [];

        (items || []).forEach(function (item) {
            const key = keyOf(item);

            if (!key || seen.has(key)) {
                return;
            }

            seen.add(key);
            output.push(item);
        });

        return output;
    }

    function readQueue() {
        let stored = [];

        try {
            stored = JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
            if (!Array.isArray(stored)) {
                stored = [];
            }
        } catch (error) {
            stored = [];
        }

        return dedupe(stored);
    }

    function saveQueue(queue) {
        const clean = dedupe(queue);

        window.NovaMobilePendingAttachments = clean;

        try {
            localStorage.setItem(STORE_KEY, JSON.stringify(clean));
        } catch (error) {
            console.warn(LOG, "queue save failed", error);
        }

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

        const attachment = normalizeUpload(data, file);
        const queue = readQueue();

        queue.push(attachment);
        saveQueue(queue);
        renderPreview();

        console.log(LOG, "uploaded", attachment);
    }

    async function handleFiles() {
        const files = Array.from(fileInput.files || []);

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

        fileInput.value = "";
    }

    function replaceAttachButtonWithLabel() {
        const existing = document.getElementById(BUTTON_ID);

        if (!existing) {
            console.warn(LOG, "attach button missing");
            return false;
        }

        if (existing.tagName === "LABEL" && existing.dataset.novaAttachOwner === "native-label-v1") {
            fileInput = document.getElementById(INPUT_ID);
            return true;
        }

        document.querySelectorAll("input[type='file']").forEach(function (old, index) {
            old.id = "nova-mobile-old-file-input-" + index;
            old.disabled = true;
            old.style.setProperty("display", "none", "important");
        });

        const label = document.createElement("label");

        label.id = BUTTON_ID;
        label.className = existing.className;
        label.innerHTML = existing.innerHTML || "＋";
        label.title = existing.title || "Attach file";
        label.setAttribute("role", "button");
        label.setAttribute("aria-label", "Attach file");
        label.dataset.novaAttachOwner = "native-label-v1";

        label.style.cssText = existing.style.cssText || "";
        label.style.setProperty("position", "relative", "important");
        label.style.setProperty("overflow", "hidden", "important");
        label.style.setProperty("display", getComputedStyle(existing).display === "none" ? "flex" : getComputedStyle(existing).display, "important");
        label.style.setProperty("align-items", "center", "important");
        label.style.setProperty("justify-content", "center", "important");
        label.style.setProperty("pointer-events", "auto", "important");
        label.style.setProperty("cursor", "pointer", "important");

        fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.id = INPUT_ID;
        fileInput.multiple = true;
        fileInput.accept = ACCEPT;
        fileInput.dataset.novaAttachOwner = "native-label-v1";
        fileInput.addEventListener("change", handleFiles);

        fileInput.style.setProperty("position", "absolute", "important");
        fileInput.style.setProperty("inset", "0", "important");
        fileInput.style.setProperty("width", "100%", "important");
        fileInput.style.setProperty("height", "100%", "important");
        fileInput.style.setProperty("opacity", "0.01", "important");
        fileInput.style.setProperty("z-index", "5", "important");
        fileInput.style.setProperty("pointer-events", "auto", "important");
        fileInput.style.setProperty("cursor", "pointer", "important");

        label.appendChild(fileInput);
        existing.replaceWith(label);

        return true;
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
                const attach = document.getElementById(BUTTON_ID);
                const input = document.getElementById(INPUT_ID);
                const rect = attach ? attach.getBoundingClientRect() : null;
                const top = rect
                    ? document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)
                    : null;

                return {
                    installed: "native-label-v1",
                    attachTag: attach ? attach.tagName : "",
                    hasInput: !!input,
                    topId: top ? top.id : "",
                    topTag: top ? top.tagName : "",
                    topIsInput: top === input,
                    inputOwner: input ? input.dataset.novaAttachOwner || "" : "",
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
        installApi();

        if (!replaceAttachButtonWithLabel()) {
            return;
        }

        renderPreview();

        console.log(LOG, "installed");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", install, { once: true });
    } else {
        install();
    }
})();
