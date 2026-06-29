ma// NOVA_MOBILE_QUIET_REMAINING_ATTACHMENT_LOGS_20260608
window.NOVA_MOBILE_ATTACHMENT_DEBUG = window.NOVA_MOBILE_ATTACHMENT_DEBUG === true;

window.NovaMobileAttachmentDebugLog = window.NovaMobileAttachmentDebugLog || function () {
    if (!window.NOVA_MOBILE_ATTACHMENT_DEBUG) return;
    try {
        console.log.apply(console, arguments);
    } catch (e) {}
};

window.NovaMobileAttachmentDebugWarn = window.NovaMobileAttachmentDebugWarn || function () {
    if (!window.NOVA_MOBILE_ATTACHMENT_DEBUG) return;
    try {
        console.warn.apply(console, arguments);
    } catch (e) {}
};
(function () {
    "use strict";

    // NOVA_MOBILE_QUIET_ATTACHMENT_DEBUG_LOGS_20260608
    var NOVA_MOBILE_ATTACHMENT_DEBUG = false;
    function novaAttachmentDebugLog() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.log.apply(console, arguments);
        } catch (e) {}
    }
    function novaAttachmentDebugWarn() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.warn.apply(console, arguments);
        } catch (e) {}
    }

    const LOG_PREFIX = "[Nova Composer Inline Preview]";

    function $(id) {
        return document.getElementById(id);
    }

    function safeArray(value) {
        return Array.isArray(value) ? value : [];
    }

    function readJsonArray(key) {
        try {
            const raw = localStorage.getItem(key);
            if (!raw) return [];
            const parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed : [];
        } catch (_) {
            return [];
        }
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
            source.path ||
            source.href ||
            "";

        const filename =
            source.original_filename ||
            source.filename ||
            source.name ||
            source.title ||
            "attachment";

        const mimeType =
            source.mime_type ||
            source.mimeType ||
            source.type ||
            "";

        const size =
            source.size ||
            source.bytes ||
            null;

        if (!url && !filename) return null;

        return {
            url: String(url || ""),
            file_url: String(source.file_url || url || ""),
            filename: String(source.filename || filename || "attachment"),
            original_filename: String(source.original_filename || filename || "attachment"),
            name: String(filename || "attachment"),
            mime_type: String(mimeType || ""),
            size: size
        };
    }

    function collectAttachments() {
        const collected = [];

        function addMany(items) {
            safeArray(items).forEach(function (item) {
                const normalized = normalizeAttachment(item);
                if (normalized) collected.push(normalized);
            });
        }

        try { addMany(window.NovaMobileSharedAttachments); } catch (_) {}
        try { addMany(window.NovaMobilePendingAttachments); } catch (_) {}
        try { addMany(window.NovaPendingAttachments); } catch (_) {}
        try { addMany(window.__novaMobilePendingAttachments); } catch (_) {}
        try { addMany(window.__novaPendingAttachments); } catch (_) {}
        try { addMany(window.NovaMobileAttachmentStore); } catch (_) {}

        addMany(readJsonArray("nova_mobile_pending_attachments"));
        addMany(readJsonArray("nova_mobile_latest_attachments"));

        const seen = new Set();
        return collected.filter(function (item) {
            const key = [
                item.url,
                item.file_url,
                item.original_filename,
                item.filename,
                item.size
            ].join("|");

            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function findPreviewHost() {
        return (
            $("nova-mobile-attachment-preview") ||
            $("nova-mobile-attachments-preview") ||
            document.querySelector("[data-nova-attachment-preview]") ||
            document.querySelector(".nova-mobile-attachment-preview") ||
            document.querySelector(".nova-attachment-preview")
        );
    }

    function ensurePreviewHost() {
        let host = findPreviewHost();
        if (host) return host;

        const composer =
            $("nova-mobile-composer") ||
            document.querySelector(".nova-mobile-composer") ||
            document.querySelector(".mobile-composer") ||
            document.querySelector("form");

        if (!composer) return null;

        host = document.createElement("div");
        host.id = "nova-mobile-attachment-preview";
        host.className = "nova-mobile-attachment-preview";
        host.setAttribute("data-nova-attachment-preview", "true");

        const input =
            $("nova-mobile-input") ||
            composer.querySelector("textarea") ||
            composer.querySelector("input");

        if (input && input.parentNode) {
            input.parentNode.insertBefore(host, input);
        } else {
            composer.insertBefore(host, composer.firstChild);
        }

        return host;
    }

    function renderInlineComposerPreview() {
        const attachments = collectAttachments();
        const host = ensurePreviewHost();

        if (!host) {
            window.NovaMobileAttachmentDebugLog(LOG_PREFIX, "hidden no host");
            return;
        }

        if (!attachments.length) {
            host.innerHTML = "";
            host.hidden = true;
            host.style.display = "none";
            novaAttachmentDebugLog(LOG_PREFIX, "hidden no attachments");
            return;
        }

        host.hidden = false;
        host.style.display = "flex";
        host.style.flexWrap = "wrap";
        host.style.gap = "6px";
        host.style.margin = "6px 0";

        host.innerHTML = attachments.map(function (attachment, index) {
            const name = attachment.original_filename || attachment.filename || attachment.name || "attachment";
            const mime = attachment.mime_type ? " · " + attachment.mime_type : "";

            return (
                '<div class="nova-mobile-attachment-chip" data-attachment-index="' + index + '" ' +
                'style="display:flex;align-items:center;gap:6px;max-width:100%;padding:6px 8px;border:1px solid rgba(255,255,255,.16);border-radius:999px;font-size:12px;line-height:1.2;">' +
                    '<span aria-hidden="true">📎</span>' +
                    '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' +
                        escapeHtml(name + mime) +
                    '</span>' +
                '</div>'
            );
        }).join("");

        window.NovaMobileAttachmentDebugLog(LOG_PREFIX, "rendered", attachments.length, attachments);
    }

    window.NovaRenderComposerInlinePreview = renderInlineComposerPreview;
    window.NovaCollectComposerInlineAttachments = collectAttachments;

    window.addEventListener("nova-mobile-upload-complete", function () {
        setTimeout(renderInlineComposerPreview, 0);
        setTimeout(renderInlineComposerPreview, 150);
        setTimeout(renderInlineComposerPreview, 500);
    });

    window.addEventListener("nova-mobile-attachments-cleared", function () {
        setTimeout(renderInlineComposerPreview, 0);
    });

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(renderInlineComposerPreview, 0);
        setTimeout(renderInlineComposerPreview, 300);
        setTimeout(renderInlineComposerPreview, 900);
    });

    setTimeout(renderInlineComposerPreview, 1200);

    window.NovaMobileAttachmentDebugLog(LOG_PREFIX, "active");
})();


/* NOVA_MOBILE_ATTACHMENT_PREVIEW_FINAL_CONTROLLER_20260607 */
(function () {
    "use strict";

    // NOVA_MOBILE_QUIET_ATTACHMENT_DEBUG_LOGS_20260608
    var NOVA_MOBILE_ATTACHMENT_DEBUG = false;
    function novaAttachmentDebugLog() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.log.apply(console, arguments);
        } catch (e) {}
    }
    function novaAttachmentDebugWarn() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.warn.apply(console, arguments);
        } catch (e) {}
    }

    if (window.NovaMobileAttachmentPreviewFinalControllerInstalled) {
        return;
    }

    window.NovaMobileAttachmentPreviewFinalControllerInstalled = true;

    var MAX_ATTACHMENTS = 5;

    function safeJson(value, fallback) {
        try {
            return value ? JSON.parse(value) : fallback;
        } catch (error) {
            return fallback;
        }
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function getComposer() {
        return document.getElementById("nova-mobile-composer") ||
            document.querySelector(".nova-mobile-composer") ||
            document.querySelector(".mobile-composer") ||
            document.querySelector(".composer");
    }

    function getStoredAttachments() {
        var values = [];

        [
            window.NovaMobileState && window.NovaMobileState.pendingAttachments,
            window.NovaMobileSharedAttachments,
            window.NovaMobilePendingAttachments,
            window.NovaPendingAttachments,
            safeJson(localStorage.getItem("nova_mobile_pending_attachments"), []),
            safeJson(localStorage.getItem("nova_mobile_latest_attachments"), [])
        ].forEach(function (list) {
            if (Array.isArray(list)) {
                list.forEach(function (item) {
                    if (item && typeof item === "object") {
                        values.push(item);
                    }
                });
            }
        });

        return dedupeAttachments(values).slice(0, MAX_ATTACHMENTS);
    }

    function getName(attachment) {
        attachment = attachment || {};
        return attachment.original_filename ||
            attachment.originalName ||
            attachment.name ||
            attachment.filename ||
            "attachment";
    }

    function getSize(attachment) {
        attachment = attachment || {};
        return attachment.size || attachment.file_size || 0;
    }

    function getUrl(attachment) {
        attachment = attachment || {};
        return attachment.url ||
            attachment.file_url ||
            attachment.preview_url ||
            attachment.path ||
            "";
    }

    function getMime(attachment) {
        attachment = attachment || {};
        return attachment.mime_type ||
            attachment.mimeType ||
            attachment.mime ||
            attachment.type ||
            "";
    }

    function attachmentKey(attachment) {
        return [
            getName(attachment),
            getSize(attachment),
            getMime(attachment),
            getUrl(attachment)
        ].join("|");
    }

    function dedupeAttachments(list) {
        var seen = {};
        var clean = [];

        (Array.isArray(list) ? list : []).forEach(function (attachment) {
            if (!attachment || typeof attachment !== "object") {
                return;
            }

            var key = attachmentKey(attachment);

            if (seen[key]) {
                return;
            }

            seen[key] = true;
            clean.push(attachment);
        });

        return clean;
    }

    function saveAttachments(attachments) {
        attachments = dedupeAttachments(attachments).slice(0, MAX_ATTACHMENTS);

        if (!window.NovaMobileState) {
            window.NovaMobileState = {};
        }

        window.NovaMobileState.pendingAttachments = attachments;
        window.NovaMobileSharedAttachments = attachments;
        window.NovaMobilePendingAttachments = attachments;
        window.NovaPendingAttachments = attachments;

        try {
            localStorage.setItem("nova_mobile_pending_attachments", JSON.stringify(attachments));
            localStorage.setItem("nova_mobile_latest_attachments", JSON.stringify(attachments));
        } catch (error) {}

        return attachments;
    }

    function cleanName(value) {
        var name = String(value || "attachment").trim();

        name = name.replace(/^Attachment\s+/i, "");
        name = name.replace(/[<>]/g, "");
        name = name.replace(/\s+/g, " ");

        return name || "attachment";
    }

    function shortName(value) {
        var name = cleanName(value);
        var max = 28;

        if (name.length <= max) {
            return name;
        }

        var dot = name.lastIndexOf(".");
        var ext = dot > 0 ? name.slice(dot) : "";
        var base = dot > 0 ? name.slice(0, dot) : name;

        if (ext.length > 8) {
            ext = "";
            base = name;
        }

        return base.slice(0, Math.max(8, max - ext.length - 3)) + "..." + ext;
    }

    function removeOldPreviewContainers() {
        document.querySelectorAll(
            "#nova-mobile-attachment-preview, " +
            "#nova-mobile-attachment-preview-bottom, " +
            ".nova-mobile-attachment-preview, " +
            "[data-attachment-preview], " +
            "[data-attachment-preview-bottom]"
        ).forEach(function (node) {
            if (node.id === "nova-mobile-single-attachment-preview") {
                return;
            }

            node.innerHTML = "";
            node.style.display = "none";
            node.setAttribute("data-nova-disabled-preview", "true");
        });
    }

    function getLane() {
        var existing = document.getElementById("nova-mobile-single-attachment-preview");

        if (existing) {
            return existing;
        }

        var composer = getComposer();

        if (!composer) {
            return null;
        }

        var lane = document.createElement("div");
        lane.id = "nova-mobile-single-attachment-preview";
        lane.className = "nova-mobile-single-attachment-preview";
        lane.setAttribute("data-single-attachment-preview", "true");

        composer.insertBefore(lane, composer.firstChild);

        return lane;
    }

    function updateScrollShadows() {
        var lane = document.getElementById("nova-mobile-single-attachment-preview");

        if (!lane || !lane.parentNode) {
            return;
        }

        var wrap = lane.parentNode;

        if (!wrap.classList.contains("nova-mobile-attachment-scroll-wrap")) {
            return;
        }

        wrap.classList.toggle("has-left-shadow", lane.scrollLeft > 2);
        wrap.classList.toggle("has-right-shadow", lane.scrollLeft + lane.clientWidth < lane.scrollWidth - 2);
    }

    function ensureScrollWrap(lane) {
        if (!lane || !lane.parentNode) {
            return;
        }

        if (lane.parentNode.classList.contains("nova-mobile-attachment-scroll-wrap")) {
            return;
        }

        var wrap = document.createElement("div");
        wrap.className = "nova-mobile-attachment-scroll-wrap";

        lane.parentNode.insertBefore(wrap, lane);
        wrap.appendChild(lane);

        lane.addEventListener("scroll", updateScrollShadows, { passive: true });
    }

    function render() {
        removeOldPreviewContainers();

        var lane = getLane();

        if (!lane) {
            return;
        }

        ensureScrollWrap(lane);

        var attachments = saveAttachments(getStoredAttachments());

        if (!attachments.length) {
            lane.innerHTML = "";
            lane.style.display = "none";
            updateScrollShadows();
            return;
        }

        lane.style.display = "flex";

        lane.innerHTML = attachments.map(function (attachment, index) {
            var full = cleanName(getName(attachment));
            var shown = shortName(full);
            var url = getUrl(attachment);
            var mime = getMime(attachment);
            var isImage = mime.indexOf("image/") === 0 || /\.(png|jpg|jpeg|gif|webp)$/i.test(url || full);

            var media = isImage && url
                ? '<img src="' + escapeHtml(url) + '" alt="' + escapeHtml(full) + '" class="nova-mobile-attachment-thumb">'
                : '<span class="nova-mobile-attachment-icon">📎</span>';

            return '' +
                '<div class="nova-mobile-attachment-chip" data-attachment-index="' + index + '" title="' + escapeHtml(full) + '">' +
                    media +
                    '<span class="nova-mobile-attachment-name" title="' + escapeHtml(full) + '" data-full-name="' + escapeHtml(full) + '">' + escapeHtml(shown) + '</span>' +
                    '<button type="button" class="nova-mobile-attachment-remove" data-remove-attachment-index="' + index + '" aria-label="Remove attachment">×</button>' +
                '</div>';
        }).join("");

        setTimeout(updateScrollShadows, 0);
    }

    function removeAttachment(index) {
        index = Number(index);

        var attachments = getStoredAttachments();

        if (!Number.isFinite(index) || index < 0 || index >= attachments.length) {
            return;
        }

        attachments.splice(index, 1);
        saveAttachments(attachments);
        render();

        window.dispatchEvent(new CustomEvent("nova-mobile-attachments-changed", {
            detail: {
                pendingAttachments: attachments
            }
        }));
    }

    function clearAttachments() {
        saveAttachments([]);

        [
            "nova_mobile_pending_attachments",
            "nova_mobile_latest_attachments",
            "nova_pending_attachments"
        ].forEach(function (key) {
            try {
                localStorage.removeItem(key);
            } catch (error) {}
        });

        render();

        window.dispatchEvent(new CustomEvent("nova-mobile-attachments-cleared", {
            detail: {
                pendingAttachments: []
            }
        }));
    }

    function addAttachment(fileOrAttachment) {
        if (!fileOrAttachment) {
            return;
        }

        var current = getStoredAttachments();

        if (current.length >= MAX_ATTACHMENTS) {
            window.NovaMobileAttachmentDebugWarn("[Nova Mobile] max attachments reached");
            return;
        }

        var attachment = fileOrAttachment;

        if (typeof File !== "undefined" && fileOrAttachment instanceof File) {
            attachment = {
                original_filename: fileOrAttachment.name,
                name: fileOrAttachment.name,
                size: fileOrAttachment.size,
                mime_type: fileOrAttachment.type,
                url: URL.createObjectURL(fileOrAttachment)
            };
        }

        current.push(attachment);
        saveAttachments(current);
        render();

        window.dispatchEvent(new CustomEvent("nova-mobile-attachments-changed", {
            detail: {
                pendingAttachments: getStoredAttachments()
            }
        }));
    }

    document.addEventListener("click", function (event) {
        var button = event.target && event.target.closest
            ? event.target.closest("[data-remove-attachment-index], .nova-mobile-attachment-remove")
            : null;

        if (!button) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        removeAttachment(button.getAttribute("data-remove-attachment-index"));
    }, true);

    function bindDragDrop() {
        var composer = getComposer();

        if (!composer || composer.getAttribute("data-nova-drag-drop-bound") === "true") {
            return;
        }

        composer.setAttribute("data-nova-drag-drop-bound", "true");

        composer.addEventListener("dragover", function (event) {
            event.preventDefault();
            composer.classList.add("drag-over");
        });

        composer.addEventListener("dragleave", function () {
            composer.classList.remove("drag-over");
        });

        composer.addEventListener("drop", function (event) {
            event.preventDefault();
            composer.classList.remove("drag-over");

            var files = event.dataTransfer && event.dataTransfer.files
                ? Array.prototype.slice.call(event.dataTransfer.files)
                : [];

            files.forEach(addAttachment);
            render();
        });
    }

    window.NovaRenderComposerInlinePreview = render;
    window.renderAttachmentPreviews = render;
    window.NovaMobileClearAttachmentPreviews = clearAttachments;
    window.NovaMobileRemoveAttachmentPreview = removeAttachment;
    window.NovaMobileAddAttachment = addAttachment;
    window.NovaMobileUpdateAttachmentLaneShadows = updateScrollShadows;

    document.addEventListener("DOMContentLoaded", function () {
        bindDragDrop();
        setTimeout(render, 0);
        setTimeout(render, 250);
    });

    window.addEventListener("nova-mobile-upload-complete", function () {
        setTimeout(render, 0);
        setTimeout(render, 120);
    });

    window.addEventListener("nova-mobile-attachments-changed", function () {
        setTimeout(render, 0);
    });

    window.addEventListener("nova-mobile-attachments-cleared", function () {
        setTimeout(render, 0);
    });

    window.addEventListener("resize", function () {
        setTimeout(updateScrollShadows, 0);
    });

    window.NovaMobileAttachmentDebugLog("[Nova Mobile Attachment] final clean controller ready");
})();



/* NOVA_MOBILE_SINGLE_ATTACHMENT_PREVIEW_LOCK_20260607 */
(function () {
    "use strict";

    // NOVA_MOBILE_QUIET_ATTACHMENT_DEBUG_LOGS_20260608
    var NOVA_MOBILE_ATTACHMENT_DEBUG = false;
    function novaAttachmentDebugLog() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.log.apply(console, arguments);
        } catch (e) {}
    }
    function novaAttachmentDebugWarn() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.warn.apply(console, arguments);
        } catch (e) {}
    }

    if (window.NovaMobileSingleAttachmentPreviewLockInstalled) {
        return;
    }

    window.NovaMobileSingleAttachmentPreviewLockInstalled = true;

    function getPendingAttachments() {
        function parseJson(value, fallback) {
            try {
                return JSON.parse(value);
            } catch (e) {
                return fallback;
            }
        }

        var found = [];

        var localPending = parseJson(localStorage.getItem("nova_mobile_pending_attachments") || "[]", []);
        if (Array.isArray(localPending)) {
            found = found.concat(localPending);
        }

        if (Array.isArray(window.NovaMobilePendingAttachments)) {
            found = found.concat(window.NovaMobilePendingAttachments);
        }

        if (Array.isArray(window.__novaMobilePendingAttachments)) {
            found = found.concat(window.__novaMobilePendingAttachments);
        }

        var clean = [];
        var seen = {};

        found.forEach(function (item) {
            if (!item || typeof item !== "object") {
                return;
            }

            var key = String(item.url || item.file_url || item.filename || item.name || "").toLowerCase();

            if (!key || seen[key]) {
                return;
            }

            seen[key] = true;
            clean.push(item);
        });

        return clean;
    }

    function removeDuplicatePreviewContainers() {
        var selectors = [
            "#nova-mobile-attachment-preview",
            "#nova-mobile-attachment-preview-bar",
            ".nova-mobile-attachment-preview",
            ".nova-mobile-attachment-preview-bar",
            ".mobile-attachment-preview",
            ".mobile-attachment-preview-bar",
            ".composer-attachment-preview",
            ".composer-inline-preview",
            ".nova-composer-inline-preview"
        ];

        selectors.forEach(function (selector) {
            var nodes = Array.from(document.querySelectorAll(selector));

            if (nodes.length <= 1) {
                return;
            }

            nodes.slice(0, -1).forEach(function (node) {
                try {
                    node.remove();
                } catch (e) {}
            });
        });
    }

    function clearPreviewWhenNoPending() {
        var pending = getPendingAttachments();

        if (pending.length > 0) {
            return;
        }

        var selectors = [
            "#nova-mobile-attachment-preview",
            "#nova-mobile-attachment-preview-bar",
            ".nova-mobile-attachment-preview",
            ".nova-mobile-attachment-preview-bar",
            ".mobile-attachment-preview",
            ".mobile-attachment-preview-bar",
            ".composer-attachment-preview",
            ".composer-inline-preview",
            ".nova-composer-inline-preview"
        ];

        selectors.forEach(function (selector) {
            Array.from(document.querySelectorAll(selector)).forEach(function (node) {
                try {
                    node.innerHTML = "";
                    node.style.display = "none";
                    node.hidden = true;
                    node.setAttribute("aria-hidden", "true");
                } catch (e) {}
            });
        });
    }

    function normalizePreviewState() {
        removeDuplicatePreviewContainers();
        clearPreviewWhenNoPending();
    }

    document.addEventListener("change", function (event) {
        var target = event.target;

        if (!target || target.type !== "file") {
            return;
        }

        if (!target.files || target.files.length === 0) {
            localStorage.removeItem("nova_mobile_pending_attachments");
            localStorage.removeItem("nova_mobile_last_uploaded_attachment");
            window.NovaMobilePendingAttachments = [];
            window.__novaMobilePendingAttachments = [];

            setTimeout(normalizePreviewState, 0);
            setTimeout(normalizePreviewState, 100);
            setTimeout(normalizePreviewState, 300);
        }
    }, true);

    document.addEventListener("click", function (event) {
        var target = event.target;
        var text = String(target && target.textContent || "").toLowerCase();
        var label = String(
            target && (
                target.getAttribute("aria-label") ||
                target.getAttribute("title") ||
                target.id ||
                target.className ||
                ""
            ) || ""
        ).toLowerCase();

        if (
            text.indexOf("cancel") !== -1 ||
            text.indexOf("remove") !== -1 ||
            text.indexOf("clear") !== -1 ||
            label.indexOf("cancel") !== -1 ||
            label.indexOf("remove") !== -1 ||
            label.indexOf("clear") !== -1 ||
            label.indexOf("attachment") !== -1 && label.indexOf("close") !== -1
        ) {
            localStorage.removeItem("nova_mobile_pending_attachments");
            localStorage.removeItem("nova_mobile_last_uploaded_attachment");
            window.NovaMobilePendingAttachments = [];
            window.__novaMobilePendingAttachments = [];

            setTimeout(normalizePreviewState, 0);
            setTimeout(normalizePreviewState, 100);
            setTimeout(normalizePreviewState, 300);
        }
    }, true);

    window.addEventListener("nova-mobile-upload-complete", function () {
        setTimeout(normalizePreviewState, 0);
        setTimeout(normalizePreviewState, 100);
        setTimeout(normalizePreviewState, 300);
    }, true);

    window.addEventListener("nova-mobile-attachment-uploaded", function () {
        setTimeout(normalizePreviewState, 0);
        setTimeout(normalizePreviewState, 100);
        setTimeout(normalizePreviewState, 300);
    }, true);

    window.NovaMobileSingleAttachmentPreviewNormalize = normalizePreviewState;

    setInterval(normalizePreviewState, 1500);

    window.NovaMobileAttachmentDebugLog("[Nova Mobile Single Attachment Preview Lock] ready");
})();


/* NOVA_MOBILE_CLEAN_ATTACHMENT_CHIP_ONLY_20260607 */
(function () {
    "use strict";

    // NOVA_MOBILE_QUIET_ATTACHMENT_DEBUG_LOGS_20260608
    var NOVA_MOBILE_ATTACHMENT_DEBUG = false;
    function novaAttachmentDebugLog() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.log.apply(console, arguments);
        } catch (e) {}
    }
    function novaAttachmentDebugWarn() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.warn.apply(console, arguments);
        } catch (e) {}
    }

    if (window.NovaMobileCleanAttachmentChipOnlyInstalled) {
        return;
    }

    window.NovaMobileCleanAttachmentChipOnlyInstalled = true;

    function parseJson(value, fallback) {
        try {
            return JSON.parse(value);
        } catch (e) {
            return fallback;
        }
    }

    function getPendingAttachments() {
        var found = [];

        var localPending = parseJson(localStorage.getItem("nova_mobile_pending_attachments") || "[]", []);
        if (Array.isArray(localPending)) {
            found = found.concat(localPending);
        }

        var localLast = parseJson(localStorage.getItem("nova_mobile_last_uploaded_attachment") || "null", null);
        if (localLast && typeof localLast === "object") {
            found.push(localLast);
        }

        if (Array.isArray(window.NovaMobilePendingAttachments)) {
            found = found.concat(window.NovaMobilePendingAttachments);
        }

        if (Array.isArray(window.__novaMobilePendingAttachments)) {
            found = found.concat(window.__novaMobilePendingAttachments);
        }

        var clean = [];
        var seen = {};

        found.forEach(function (item) {
            if (!item || typeof item !== "object") {
                return;
            }

            var filename = item.original_filename || item.filename || item.name || "";
            var url = item.url || item.file_url || item.path || "";

            if (!filename && url) {
                filename = String(url).split("/").pop();
            }

            if (!filename && !url) {
                return;
            }

            var key = String(url || filename).toLowerCase();

            if (!key || seen[key]) {
                return;
            }

            seen[key] = true;

            clean.push({
                filename: filename,
                url: url,
                mime_type: item.mime_type || item.type || "",
                size: item.size || 0
            });
        });

        return clean;
    }

    function clearPendingAttachments() {
        localStorage.removeItem("nova_mobile_pending_attachments");
        localStorage.removeItem("nova_mobile_last_uploaded_attachment");

        window.NovaMobilePendingAttachments = [];
        window.__novaMobilePendingAttachments = [];

        renderCleanAttachmentPreview();
    }

    function findPreviewHost() {
        var selectors = [
            "#nova-mobile-attachment-preview",
            "#nova-mobile-attachment-preview-bar",
            ".nova-mobile-attachment-preview",
            ".nova-mobile-attachment-preview-bar",
            ".mobile-attachment-preview",
            ".mobile-attachment-preview-bar",
            ".composer-attachment-preview",
            ".composer-inline-preview",
            ".nova-composer-inline-preview"
        ];

        for (var i = 0; i < selectors.length; i += 1) {
            var found = document.querySelector(selectors[i]);

            if (found) {
                return found;
            }
        }

        var composer = (
            document.querySelector(".mobile-composer") ||
            document.querySelector(".nova-mobile-composer") ||
            document.querySelector("#nova-mobile-composer") ||
            document.querySelector(".chat-composer") ||
            document.querySelector(".composer")
        );

        if (!composer) {
            return null;
        }

        var created = document.createElement("div");
        created.id = "nova-mobile-clean-attachment-preview";
        created.className = "nova-mobile-attachment-preview mobile-attachment-preview nova-clean-attachment-preview";

        composer.parentNode.insertBefore(created, composer);

        return created;
    }

    function hideOtherPreviewNodes(host) {
        var selectors = [
            "#nova-mobile-attachment-preview",
            "#nova-mobile-attachment-preview-bar",
            ".nova-mobile-attachment-preview",
            ".nova-mobile-attachment-preview-bar",
            ".mobile-attachment-preview",
            ".mobile-attachment-preview-bar",
            ".composer-attachment-preview",
            ".composer-inline-preview",
            ".nova-composer-inline-preview"
        ];

        selectors.forEach(function (selector) {
            Array.from(document.querySelectorAll(selector)).forEach(function (node) {
                if (node === host) {
                    return;
                }

                try {
                    node.innerHTML = "";
                    node.style.display = "none";
                    node.hidden = true;
                    node.setAttribute("aria-hidden", "true");
                } catch (e) {}
            });
        });
    }

    function renderCleanAttachmentPreview() {
        var attachments = getPendingAttachments();
        var host = findPreviewHost();

        if (!host) {
            return;
        }

        hideOtherPreviewNodes(host);

        host.innerHTML = "";
        host.className = "nova-clean-attachment-preview";
        host.removeAttribute("aria-hidden");

        if (!attachments.length) {
            host.style.display = "none";
            host.hidden = true;
            return;
        }

        host.hidden = false;
        host.style.display = "flex";
        host.style.alignItems = "center";
        host.style.gap = "8px";
        host.style.padding = "6px 10px";
        host.style.margin = "6px 10px";
        host.style.borderRadius = "12px";
        host.style.background = "rgba(255,255,255,0.08)";
        host.style.border = "1px solid rgba(255,255,255,0.12)";
        host.style.maxHeight = "42px";
        host.style.overflow = "hidden";

        attachments.slice(0, 1).forEach(function (attachment) {
            var chip = document.createElement("div");
            chip.className = "nova-clean-attachment-chip";
            chip.style.display = "flex";
            chip.style.alignItems = "center";
            chip.style.gap = "8px";
            chip.style.maxWidth = "100%";
            chip.style.fontSize = "13px";
            chip.style.lineHeight = "1.2";
            chip.style.color = "rgba(255,255,255,0.92)";

            var icon = document.createElement("span");
            icon.textContent = "📎";
            icon.setAttribute("aria-hidden", "true");

            var name = document.createElement("span");
            name.textContent = attachment.filename || "attachment";
            name.style.overflow = "hidden";
            name.style.textOverflow = "ellipsis";
            name.style.whiteSpace = "nowrap";
            name.style.maxWidth = "220px";

            var remove = document.createElement("button");
            remove.type = "button";
            remove.textContent = "×";
            remove.setAttribute("aria-label", "Remove attachment");
            remove.style.width = "24px";
            remove.style.height = "24px";
            remove.style.minWidth = "24px";
            remove.style.borderRadius = "999px";
            remove.style.border = "0";
            remove.style.background = "rgba(255,255,255,0.14)";
            remove.style.color = "#fff";
            remove.style.cursor = "pointer";
            remove.style.display = "flex";
            remove.style.alignItems = "center";
            remove.style.justifyContent = "center";
            remove.style.fontSize = "16px";

            remove.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                clearPendingAttachments();
            }, true);

            chip.appendChild(icon);
            chip.appendChild(name);
            chip.appendChild(remove);

            host.appendChild(chip);
        });
    }

    function scrubBukakkeTextNodes() {
        var badPatterns = [
            "Attachment analysis:",
            "This uploaded attachment contains readable text",
            "Key points:",
            "Preview:",
            "[Content_Types].xml",
            "PK\u0003\u0004"
        ];

        Array.from(document.querySelectorAll("body *")).forEach(function (node) {
            if (!node || !node.textContent) {
                return;
            }

            var text = String(node.textContent || "");

            if (text.length < 40) {
                return;
            }

            var isBad = badPatterns.some(function (pattern) {
                return text.indexOf(pattern) !== -1;
            });

            if (!isBad) {
                return;
            }

            var cls = String(node.className || "").toLowerCase();
            var id = String(node.id || "").toLowerCase();

            if (
                cls.indexOf("attachment") !== -1 ||
                cls.indexOf("preview") !== -1 ||
                cls.indexOf("composer") !== -1 ||
                id.indexOf("attachment") !== -1 ||
                id.indexOf("preview") !== -1
            ) {
                node.innerHTML = "";
                node.style.display = "none";
                node.hidden = true;
            }
        });
    }

    function run() {
        renderCleanAttachmentPreview();
        scrubBukakkeTextNodes();
    }

    window.addEventListener("nova-mobile-upload-complete", function () {
        setTimeout(run, 0);
        setTimeout(run, 100);
        setTimeout(run, 300);
    }, true);

    window.addEventListener("nova-mobile-attachment-uploaded", function () {
        setTimeout(run, 0);
        setTimeout(run, 100);
        setTimeout(run, 300);
    }, true);

    document.addEventListener("change", function (event) {
        if (event.target && event.target.type === "file") {
            setTimeout(run, 0);
            setTimeout(run, 100);
            setTimeout(run, 300);
        }
    }, true);

    document.addEventListener("click", function () {
        setTimeout(run, 100);
    }, true);

    window.NovaMobileCleanAttachmentChipOnlyRender = run;
    window.NovaMobileCleanAttachmentChipOnlyClear = clearPendingAttachments;

    setInterval(run, 1500);

    window.NovaMobileAttachmentDebugLog("[Nova Mobile Clean Attachment Chip Only] ready");
})();




