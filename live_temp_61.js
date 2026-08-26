
(function () {
    "use strict";

    if (window.__NOVA_DESKTOP_ATTACHMENT_PREVIEW_POLISH_20260622__) return;
    window.__NOVA_DESKTOP_ATTACHMENT_PREVIEW_POLISH_20260622__ = true;

    function esc(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function formatBytes(value) {
        var bytes = Number(value || 0);
        if (!bytes || bytes < 0) return "";
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }

    function getAttachmentList() {
        try {
            if (Array.isArray(pendingDesktopAttachments)) {
                return pendingDesktopAttachments;
            }
        } catch (_) {}
        return [];
    }

    function getFileIcon(attachment) {
        var mime = String(attachment && (attachment.mime_type || attachment.type || "") || "").toLowerCase();
        var name = String(attachment && (attachment.name || attachment.filename || attachment.original_filename || "") || "").toLowerCase();

        if (mime.indexOf("image/") === 0 || /\.(png|jpe?g|gif|webp|bmp|svg)$/.test(name)) return "image";
        if (mime.indexOf("pdf") >= 0 || /\.pdf$/.test(name)) return "PDF";
        if (mime.indexOf("text") >= 0 || /\.(txt|md|csv|json|py|js|html|css)$/.test(name)) return "PDF";
        return "PDF";
    }

    function getAttachmentUrl(attachment) {
        return String(
            attachment && (
                attachment.url ||
                attachment.file_url ||
                attachment.preview_url ||
                attachment.image_url ||
                ""
            ) || ""
        );
    }

    function buildPreviewHtml(attachment, count) {
        attachment = attachment || {};

        var name = attachment.original_filename || attachment.name || attachment.filename || "Attached file";
        var mime = attachment.mime_type || attachment.content_type || attachment.type || "file";
        var size = formatBytes(attachment.size || attachment.size_bytes);
        var url = getAttachmentUrl(attachment);
        var icon = getFileIcon(attachment);

        var thumb = icon === "image" && url
            ? '<img src="' + esc(url) + '" alt="">'
            : esc(icon === "image" ? "IMG" : icon);

        var extra = count > 1 ? " +" + String(count - 1) + " more" : "";
        var meta = [mime, size].filter(Boolean).join(" - ") + extra;

        return [
            '<div class="nova-attachment-preview-card">',
                '<div class="nova-attachment-preview-thumb">' + thumb + '</div>',
                '<div class="nova-attachment-preview-main">',
                    '<div class="nova-attachment-preview-label">Attachment ready</div>',
                    '<div class="nova-attachment-preview-name" title="' + esc(name) + '">' + esc(name) + '</div>',
                    '<div class="nova-attachment-preview-meta" title="' + esc(meta) + '">' + esc(meta) + '</div>',
                '</div>',
                '<button type="button" class="nova-attachment-preview-remove" id="desktopAttachmentDeleteBtn" title="Remove attachment" aria-label="Remove attachment">&times;</button>',
            '</div>'
        ].join("");
    }

    window.showDesktopAttachmentChip = function () {
        var chip = document.getElementById("desktopAttachmentChip");

        if (!chip) {
            chip = document.createElement("div");
            chip.id = "desktopAttachmentChip";

            var composer = document.querySelector(".composer") || document.getElementById("input")?.parentElement || document.body;
            if (composer && composer.parentElement) {
                composer.parentElement.insertBefore(chip, composer);
            } else {
                document.body.appendChild(chip);
            }
        }

        var attachments = getAttachmentList();

        if (!attachments.length) {
            chip.hidden = true;
            chip.style.display = "none";
            chip.innerHTML = "";
            return;
        }

        chip.hidden = false;
        chip.style.display = "block";
        chip.innerHTML = buildPreviewHtml(attachments[attachments.length - 1], attachments.length);

        var remove = document.getElementById("desktopAttachmentDeleteBtn");
        if (remove) {
            remove.onclick = function (event) {
                event.preventDefault();
                event.stopPropagation();

                if (typeof window.clearDesktopAttachments === "function") {
                    window.clearDesktopAttachments();
                } else {
                    try { pendingDesktopAttachments = []; } catch (_) {}
                    chip.hidden = true;
                    chip.style.display = "none";
                    chip.innerHTML = "";
                }
            };
        }
    };

    window.renderDesktopAttachmentChip = window.showDesktopAttachmentChip;
    window.renderDesktopAttachments = window.showDesktopAttachmentChip;

    console.log("[Nova Desktop Attachment Preview Polish] ready");
})();
