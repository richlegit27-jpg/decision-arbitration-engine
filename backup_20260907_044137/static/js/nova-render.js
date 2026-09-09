(function () {
  "use strict";

  function q(id) {
    return document.getElementById(id);
  }

  const state = {
    initialized: false,
  };

  const els = {
    messages: null,
    emptyState: null,
  };

  function nowIso() {
    return new Date().toISOString();
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function normalizeText(value) {
    return String(value == null ? "" : value).replace(/\r\n/g, "\n");
  }

  function formatTime(value) {
    try {
      const d = value ? new Date(value) : new Date();
      return d.toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_) {
      return "";
    }
  }

  function guessAttachmentType(filename, mimeType, url) {
    const probe = `${filename || ""} ${url || ""}`.toLowerCase();
    const mime = String(mimeType || "").toLowerCase();

    if (
      mime.startsWith("image/") ||
      /\.(png|jpg|jpeg|gif|webp|bmp|svg)(\?|#|$)/i.test(probe)
    ) {
      return "image";
    }

    if (
      mime.startsWith("video/") ||
      /\.(mp4|webm|mov|m4v|avi|mkv)(\?|#|$)/i.test(probe)
    ) {
      return "video";
    }

    if (
      mime.startsWith("audio/") ||
      /\.(mp3|wav|m4a|ogg|flac|aac)(\?|#|$)/i.test(probe)
    ) {
      return "audio";
    }

    return "file";
  }

  function normalizeAttachment(raw) {
    if (!raw) return null;

    if (typeof raw === "string") {
      return {
        id: `att-${Math.random().toString(36).slice(2, 10)}`,
        type: guessAttachmentType("", "", raw),
        filename: "",
        stored_name: "",
        mime_type: "",
        url: raw,
        size: null,
        source: "unknown",
        title: raw,
        alt: raw,
      };
    }

    const filename = String(raw.filename || raw.name || raw.title || "");
    const mimeType = String(raw.mime_type || raw.content_type || raw.mime || "");
    const url = String(raw.url || raw.src || raw.href || "");
    const storedName = String(raw.stored_name || raw.stored_filename || raw.path || "");
    let type = String(raw.type || raw.kind || "").toLowerCase();

    if (!type || !["image", "video", "audio", "file"].includes(type)) {
      type = guessAttachmentType(filename, mimeType, url);
    }

    const item = {
      id: String(raw.id || `att-${Math.random().toString(36).slice(2, 10)}`),
      type,
      filename,
      stored_name: storedName,
      mime_type: mimeType,
      url,
      size: raw.size ?? null,
      source: String(raw.source || "unknown"),
      title: String(raw.title || filename || type),
      alt: String(raw.alt || raw.caption || filename || raw.title || type),
    };

    if (!item.url && !item.filename && !item.stored_name) {
      return null;
    }

    return item;
  }

  function normalizeAttachments(value) {
    if (!value) return [];
    const raw = Array.isArray(value) ? value : [value];
    return raw.map(normalizeAttachment).filter(Boolean);
  }

  function normalizeMessage(raw) {
    const item = raw && typeof raw === "object" ? { ...raw } : {};
    return {
      id: String(item.id || `msg-${Math.random().toString(36).slice(2, 10)}`),
      role: String(item.role || "assistant"),
      content: normalizeText(item.content || ""),
      attachments: normalizeAttachments(item.attachments),
      created_at: item.created_at || nowIso(),
      meta: item.meta && typeof item.meta === "object" ? item.meta : {},
    };
  }

  function normalizeIncomingResponse(payload) {
    const raw = payload && typeof payload === "object" ? payload : {};
    return {
      ok: raw.ok !== false,
      assistant_message: raw.assistant_message ? normalizeMessage(raw.assistant_message) : null,
      session: raw.session || null,
      debug: raw.debug || {},
      message: raw.message || "",
    };
  }

  function renderMarkdownLite(text) {
    const escaped = escapeHtml(normalizeText(text));

    return escaped
      .replace(/^### (.*)$/gm, "<h3>$1</h3>")
      .replace(/^## (.*)$/gm, "<h2>$1</h2>")
      .replace(/^# (.*)$/gm, "<h1>$1</h1>")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/`([^`]+?)`/g, "<code>$1</code>")
      .replace(/\[(.+?)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/\n/g, "<br>");
  }

  function badgeHtml(text, variant) {
    return `<span class="nova-badge nova-badge-${escapeHtml(variant || "default")}">${escapeHtml(text)}</span>`;
  }

  function renderBadges(message) {
    const badges = [];
    const meta = message.meta || {};
    const attachments = safeArray(message.attachments);

    if (attachments.length) {
      badges.push(badgeHtml(`${attachments.length} attachment${attachments.length === 1 ? "" : "s"}`, "media"));
    }
    if (meta.artifact_saved) {
      badges.push(badgeHtml("Artifact", "artifact"));
    }
    if (meta.web_used || meta.web || meta.has_urls) {
      badges.push(badgeHtml("Web", "web"));
    }
    if (meta.memory_used) {
      badges.push(badgeHtml("Memory", "memory"));
    }
    if (meta.fallback_reason) {
      badges.push(badgeHtml("Fallback", "warn"));
    }

    return badges.length
      ? `<div class="nova-message-badges">${badges.join("")}</div>`
      : "";
  }

  function renderImageAttachment(att) {
    const title = escapeHtml(att.title || att.filename || "Image");
    const alt = escapeHtml(att.alt || att.filename || att.title || "Image");
    const url = escapeHtml(att.url || "");

    return `
      <a class="nova-media-card nova-media-link" href="${url}" target="_blank" rel="noopener">
        <img class="nova-media-image" src="${url}" alt="${alt}" loading="lazy">
        <div class="nova-media-caption">${title}</div>
      </a>
    `;
  }

  function renderVideoAttachment(att) {
    const title = escapeHtml(att.title || att.filename || "Video");
    const url = escapeHtml(att.url || "");
    const mime = escapeHtml(att.mime_type || "video/mp4");

    return `
      <div class="nova-media-card">
        <video class="nova-media-video" controls preload="metadata">
          <source src="${url}" type="${mime}">
        </video>
        <div class="nova-media-caption">${title}</div>
      </div>
    `;
  }

  function renderAudioAttachment(att) {
    const title = escapeHtml(att.title || att.filename || "Audio");
    const url = escapeHtml(att.url || "");
    const mime = escapeHtml(att.mime_type || "audio/mpeg");

    return `
      <div class="nova-media-card nova-media-card-audio">
        <div class="nova-media-caption nova-media-caption-top">${title}</div>
        <audio class="nova-media-audio" controls preload="metadata">
          <source src="${url}" type="${mime}">
        </audio>
      </div>
    `;
  }

  function renderFileAttachment(att) {
    const title = escapeHtml(att.title || att.filename || "File");
    const url = escapeHtml(att.url || "#");
    const mime = escapeHtml(att.mime_type || "");
    const size = att.size != null ? ` â€¢ ${escapeHtml(String(att.size))} bytes` : "";

    return `
      <a class="nova-file-chip" href="${url}" target="_blank" rel="noopener">
        <span class="nova-file-chip-icon">ðŸ“Ž</span>
        <span class="nova-file-chip-body">
          <span class="nova-file-chip-title">${title}</span>
          <span class="nova-file-chip-meta">${mime || "file"}${size}</span>
        </span>
      </a>
    `;
  }

  function renderAttachment(att) {
    if (!att || !att.url) {
      return "";
    }

    if (att.type === "image") return renderImageAttachment(att);
    if (att.type === "video") return renderVideoAttachment(att);
    if (att.type === "audio") return renderAudioAttachment(att);
    return renderFileAttachment(att);
  }

  function renderAttachments(attachments) {
    const items = normalizeAttachments(attachments);
    if (!items.length) return "";

    const imageLike = items.filter((item) => item.type === "image");
    const videoLike = items.filter((item) => item.type === "video");
    const audioLike = items.filter((item) => item.type === "audio");
    const fileLike = items.filter((item) => item.type === "file");

    let html = "";

    if (imageLike.length) {
      html += `
        <div class="nova-message-media nova-media-grid ${imageLike.length === 1 ? "is-single" : ""}">
          ${imageLike.map(renderAttachment).join("")}
        </div>
      `;
    }

    if (videoLike.length) {
      html += `
        <div class="nova-message-media nova-media-stack">
          ${videoLike.map(renderAttachment).join("")}
        </div>
      `;
    }

    if (audioLike.length) {
      html += `
        <div class="nova-message-media nova-media-stack">
          ${audioLike.map(renderAttachment).join("")}
        </div>
      `;
    }

    if (fileLike.length) {
      html += `
        <div class="nova-message-media nova-file-chip-list">
          ${fileLike.map(renderAttachment).join("")}
        </div>
      `;
    }

    return html;
  }

  function messageHtml(message) {
    const item = normalizeMessage(message);
    const roleClass = item.role === "user" ? "is-user" : "is-assistant";
    const roleLabel = item.role === "user" ? "You" : "Nova";
    const textHtml = item.content
      ? `<div class="nova-message-markdown">${renderMarkdownLite(item.content)}</div>`
      : "";
    const attachmentsHtml = renderAttachments(item.attachments);
    const badges = renderBadges(item);
    const time = formatTime(item.created_at);

    return `
      <article class="nova-message ${roleClass}" data-message-id="${escapeHtml(item.id)}" data-role="${escapeHtml(item.role)}">
        <div class="nova-message-inner">
          <div class="nova-message-head">
            <div class="nova-message-author">${escapeHtml(roleLabel)}</div>
            <div class="nova-message-time">${escapeHtml(time)}</div>
          </div>
          ${badges}
          ${textHtml}
          ${attachmentsHtml}
        </div>
      </article>
    `;
  }

  function scrollMessagesToBottom() {
    if (!els.messages) return;
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  function refreshEmptyState() {
    if (!els.emptyState || !els.messages) return;
    const hasMessages = Boolean(els.messages.children.length);
    els.emptyState.style.display = hasMessages ? "none" : "";
  }

  function appendMessage(message) {
    if (!els.messages) return null;
    const item = normalizeMessage(message);
    els.messages.insertAdjacentHTML("beforeend", messageHtml(item));
    refreshEmptyState();
    scrollMessagesToBottom();
    return item;
  }

  function renderMessages(messages) {
    if (!els.messages) return;
    const items = safeArray(messages).map(normalizeMessage);
    els.messages.innerHTML = items.map(messageHtml).join("");
    refreshEmptyState();
    scrollMessagesToBottom();
  }

  function bindEls() {
    els.messages = q("messages");
    els.emptyState = q("novaEmptyState");
  }

  const NovaRender = {
    init() {
      if (state.initialized) return;
      bindEls();
      state.initialized = true;
      refreshEmptyState();
      console.log("nova-render loaded");
    },

    appendMessage,

    renderMessages,

    refreshEmptyState,

    normalizeIncomingResponse,

    normalizeMessage,

    normalizeAttachments,

    renderAttachments,
  };

  window.NovaRender = NovaRender;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      NovaRender.init();
    });
  } else {
    NovaRender.init();
  }
})();

