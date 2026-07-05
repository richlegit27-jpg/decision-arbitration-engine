(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACH_SAFE_OWNER_V5__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACH_SAFE_OWNER_V5__ = true;

    const LOG = "[Nova Attach Safe Owner V5]";
    const INPUT_ID = "nova-mobile-file-input";
    const BUTTON_ID = "nova-mobile-attach";
    const PREVIEW_ID = "nova-mobile-attach-preview-safe-v5";
    const STORE_KEY = "nova_mobile_upload";
    const ACCEPT = "image/*,.txt,.md,.json,.js,.py,.css,.html,.pdf,.docx";

    let input = null;
    let raf = 0;

    function button() {
        return document.getElementById(BUTTON_ID);
    }

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
            const stored = JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
            return dedupe(Array.isArray(stored) ? stored : []);
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

    function createFreshInput() {
        document.querySelectorAll("input[type='file']").forEach(function (old, index) {
            old.id = "nova-mobile-old-file-input-" + index;
            old.disabled = true;
            old.style.setProperty("display", "none", "important");
            old.style.setProperty("pointer-events", "none", "important");
        });

        input = document.createElement("input");
        input.type = "file";
        input.id = INPUT_ID;
        input.multiple = true;
        input.accept = ACCEPT;
        input.dataset.novaAttachOwner = "safe-v5";
        input.addEventListener("change", handleFiles);

        document.body.appendChild(input);
        return input;
    }

    function ensureInput() {
        if (input && document.body.contains(input)) {
            return input;
        }

        return createFreshInput();
    }

    function placeInputNow() {
        const btn = button();

        if (!btn) {
            return;
        }

        const fileInput = ensureInput();
        const rect = btn.getBoundingClientRect();

        fileInput.disabled = false;
        fileInput.removeAttribute("disabled");
        fileInput.removeAttribute("hidden");
        fileInput.removeAttribute("inert");

        fileInput.style.setProperty("display", "block", "important");
        fileInput.style.setProperty("visibility", "visible", "important");
        fileInput.style.setProperty("position", "fixed", "important");
        fileInput.style.setProperty("left", rect.left + "px", "important");
        fileInput.style.setProperty("top", rect.top + "px", "important");
        fileInput.style.setProperty("width", rect.width + "px", "important");
        fileInput.style.setProperty("height", rect.height + "px", "important");
        fileInput.style.setProperty("opacity", "0.01", "important");
        fileInput.style.setProperty("z-index", "2147483647", "important");
        fileInput.style.setProperty("pointer-events", "auto", "important");
        fileInput.style.setProperty("margin", "0", "important");
        fileInput.style.setProperty("padding", "0", "important");

        btn.disabled = false;
        btn.style.setProperty("z-index", "1", "important");
    }

    function placeInputSoon() {
        if (raf) {
            cancelAnimationFrame(raf);
        }

        raf = requestAnimationFrame(function () {
            raf = 0;
            placeInputNow();
        });
    }

    function normalize(data, file) {
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

    function isImage(item) {
        const type = String(item.type || item.mime_type || "").toLowerCase();
        const name = String(item.original_name || item.name || item.filename || "").toLowerCase();

        return type.startsWith("image/") || /\.(png|jpg|jpeg|gif|webp|bmp|svg)$/i.test(name);
    }

    function displayName(item) {
        return item.original_name || item.name || item.filename || "file";
    }

    function removeOldPreviewBars() {
        [
            "nova-mobile-attach-body-preview",
            "nova-mobile-attach-preview-owner-v2",
            "nova-mobile-attach-preview-owner-v3",
            "nova-mobile-attach-preview-owner-v4",
            "nova-mobile-upload-preview",
            "nova-mobile-preview-bar",
            "mobileAttachPreview",
            "mobile-attach-preview"
        ].forEach(function (id) {
            const el = document.getElementById(id);

            if (el) {
                el.remove();
            }
        });
    }

    function renderPreview() {
        removeOldPreviewBars();

        const queue = saveQueue(readQueue());
        let bar = document.getElementById(PREVIEW_ID);

        if (!bar) {
            bar = document.createElement("div");
            bar.id = PREVIEW_ID;
            document.body.appendChild(bar);
        }

        bar.innerHTML = "";

        bar.style.setProperty("position", "fixed", "important");
        bar.style.setProperty("left", "10px", "important");
        bar.style.setProperty("right", "10px", "important");
        bar.style.setProperty("bottom", "78px", "important");
        bar.style.setProperty("z-index", "999998", "important");
        bar.style.setProperty("gap", "8px", "important");
        bar.style.setProperty("align-items", "center", "important");
        bar.style.setProperty("overflow-x", "auto", "important");
        bar.style.setProperty("padding", "6px 2px", "important");
        bar.style.setProperty("pointer-events", "auto", "important");
        bar.style.setProperty("display", queue.length ? "flex" : "none", "important");

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
                img.alt = displayName(item);
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
            label.textContent = displayName(item);
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

        console.log(LOG, "preview rendered", queue.map(displayName));
    }

    async function uploadFile(file) {
        const form = new FormData();
        form.append("file", file, file.name);

        const response = await fetch("/api/upload", {
            method: "POST",
            body: form,
            credentials: "same-origin"
        });

        const data = await response.json();

        if (!response.ok || data.ok === false) {
            throw new Error(data.error || data.message || "Upload failed");
        }

        const attachment = normalize(data, file);
        const queue = readQueue();

        queue.push(attachment);
        saveQueue(queue);
        renderPreview();

        console.log(LOG, "uploaded", attachment);
    }

    async function handleFiles() {
        const files = Array.from(input.files || []);

        console.log(LOG, "selected files", files.map(function (file) {
            return file.name;
        }));

        for (const file of files) {
            try {
                await uploadFile(file);
            } catch (error) {
                console.error(LOG, "upload failed", error);
                alert("Upload failed: " + file.name);
            }
        }

        input.value = "";
        placeInputSoon();
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
            syncOverlay: placeInputNow,
            debug: function () {
                const btn = button();
                const fileInput = document.getElementById(INPUT_ID);
                const rect = btn ? btn.getBoundingClientRect() : null;
                const top = rect
                    ? document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)
                    : null;

                return {
                    installed: "safe-v5",
                    hasButton: !!btn,
                    hasInput: !!fileInput,
                    topId: top ? top.id : "",
                    topTag: top ? top.tagName : "",
                    topIsInput: top === fileInput,
                    inputOwner: fileInput ? fileInput.dataset.novaAttachOwner || "" : "",
                    queue: readQueue().map(function (item) {
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
        installApi();
        createFreshInput();
        placeInputNow();
        renderPreview();

        window.addEventListener("resize", placeInputSoon, { passive: true });
        window.addEventListener("orientationchange", placeInputSoon, { passive: true });

        if (window.visualViewport) {
            window.visualViewport.addEventListener("resize", placeInputSoon, { passive: true });
            window.visualViewport.addEventListener("scroll", placeInputSoon, { passive: true });
        }

        console.log(LOG, "installed");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", install, { once: true });
    } else {
        install();
    }
})();
