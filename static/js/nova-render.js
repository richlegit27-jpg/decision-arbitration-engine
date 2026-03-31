(function () {
  "use strict";

  const NovaRender = {
    state: {
      messageContainer: null,
      emptyState: null,
    },

    init() {
      this.state.messageContainer = document.getElementById("messages");
      this.state.emptyState = document.getElementById("novaEmptyState");
      this.bindGlobalHelpers();
      this.refreshEmptyState();
      console.log("nova-render loaded");
    },

    bindGlobalHelpers() {
      window.NovaRender = this;
    },

    normalizeText(value) {
      return String(value == null ? "" : value).replace(/\r\n/g, "\n");
    },

    escapeHtml(value) {
      return String(value == null ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    },

    slug(value) {
      return String(value || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "") || "file";
    },

    isImageType(type, mimeType, url, filename) {
      const t = String(type || "").toLowerCase();
      const m = String(mimeType || "").toLowerCase();
      const probe = `${url || ""} ${filename || ""}`.toLowerCase();
      return (
        t === "image" ||
        m.startsWith("image/") ||
        /\.(png|jpe?g|gif|webp|bmp|svg)(\?|#|$)/i.test(probe)
      );
    },

    isVideoType(type, mimeType, url, filename) {
      const t = String(type || "").toLowerCase();
      const m = String(mimeType || "").toLowerCase();
      const probe = `${url || ""} ${filename || ""}`.toLowerCase();
      return (
        t === "video" ||
        m.startsWith("video/") ||
        /\.(mp4|webm|mov|m4v|avi|mkv)(\?|#|$)/i.test(probe)
      );
    },

    isAudioType(type, mimeType, url, filename) {
      const t = String(type || "").toLowerCase();
      const m = String(mimeType || "").toLowerCase();
      const probe = `${url || ""} ${filename || ""}`.toLowerCase();
      return (
        t === "audio" ||
        m.startsWith("audio/") ||
        /\.(mp3|wav|m4a|ogg|flac|aac)(\?|#|$)/i.test(probe)
      );
    },

    normalizeAttachment(input) {
      if (!input) return null;

      if (typeof input === "string") {
        return {
          id: `att-${Math.random().toString(36).slice(2, 10)}`,
          type: "file",
          filename: "",
          stored_name: "",
          mime_type: "",
          url: input,
          source: "unknown",
          title: input,
          alt: input,
          size: null,
        };
      }

      const attachment = {
        id:
          input.id ||
          `att-${Math.random().toString(36).slice(2, 10)}`,
        type: String(input.type || input.kind || "file").toLowerCase(),
        filename: input.filename || input.name || input.title || "",
        stored_name: input.stored_name || input.stored_filename || "",
        mime_type: input.mime_type || input.content_type || input.mime || "",
        url: input.url || input.src || input.href || "",
        source: input.source || "unknown",
        title: input.title || input.filename || input.name || "",
        alt: input.alt || input.caption || input.filename || input.title || "",
        size: input.size ?? null,
      };

      if (!attachment.type || attachment.type === "unknown") {
        if (this.isImageType("", attachment.mime_type, attachment.url, attachment.filename)) {
          attachment.type = "image";
        } else if (this.isVideoType("", attachment.mime_type, attachment.url, attachment.filename)) {
          attachment.type = "video";
        } else if (this.isAudioType("", attachment.mime_type, attachment.url, attachment.filename)) {
          attachment.type = "audio";
        } else {
          attachment.type = "file";
        }
      }

      return attachment.url || attachment.filename ? attachment : null;
    },

    normalizeAttachments(value) {
      if (!value) return [];
      const raw = Array.isArray(value) ? value : [value];
      return raw
        .map((item) => this.normalizeAttachment(item))
        .filter(Boolean);
    },

    fileLabel(att) {
      return (
        att.filename ||
        att.title ||
        att.alt ||
        att.url ||
        `${att.type || "file"} attachment`
      );
    },

    formatBytes(size) {
      const value = Number(size);
      if (!Number.isFinite(value) || value <= 0) return "";
      const units = ["B", "KB", "MB", "GB"];
      let amount = value;
      let unitIndex = 0;
      while (amount >= 1024 && unitIndex < units.length - 1) {
        amount /= 1024;
        unitIndex += 1;
      }
      return `${amount.toFixed(amount >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
    },

    renderMarkdown(text) {
      let html = this.escapeHtml(this.normalizeText(text));

      html = html.replace(/^### (.*)$/gm, "<h3>$1</h3>");
      html = html.replace(/^## (.*)$/gm, "<h2>$1</h2>");
      html = html.replace(/^# (.*)$/gm, "<h1>$1</h1>");

      html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
      html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

      html = html.replace(
        /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
      );

      const lines = html.split("\n");
      const out = [];
      let inList = false;

      for (const line of lines) {
        if (/^\s*[-*]\s+/.test(line)) {
          if (!inList) {
            out.push("<ul>");
            inList = true;
          }
          out.push(`<li>${line.replace(/^\s*[-*]\s+/, "")}</li>`);
        } else {
          if (inList) {
            out.push("</ul>");
            inList = false;
          }
          if (line.trim()) {
            out.push(`<p>${line}</p>`);
          }
        }
      }

      if (inList) out.push("</ul>");

      return out.join("");
    },

    buildAttachmentCard(att) {
      const safeTitle = this.escapeHtml(this.fileLabel(att));
      const safeUrl = this.escapeHtml(att.url || "");
      const safeMime = this.escapeHtml(att.mime_type || "");
      const safeAlt = this.escapeHtml(att.alt || this.fileLabel(att));
      const typeClass = `attachment-type-${this.slug(att.type)}`;
      const metaBits = [
        att.type ? att.type.toUpperCase() : "",
        att.mime_type || "",
        this.formatBytes(att.size),
      ].filter(Boolean);

      if (this.isImageType(att.type, att.mime_type, att.url, att.filename)) {
        return `
          <figure class="nova-attachment-card nova-attachment-media ${typeClass}" data-attachment-id="${this.escapeHtml(att.id)}">
            <div class="nova-attachment-media-frame">
              <img
                class="nova-attachment-image"
                src="${safeUrl}"
                alt="${safeAlt}"
                loading="lazy"
                referrerpolicy="no-referrer"
              />
            </div>
            <figcaption class="nova-attachment-caption">
              <div class="nova-attachment-title-row">
                <span class="nova-attachment-kind-pill">IMAGE</span>
                <a class="nova-attachment-open" href="${safeUrl}" target="_blank" rel="noopener noreferrer">Open</a>
              </div>
              <div class="nova-attachment-title">${safeTitle}</div>
              ${metaBits.length ? `<div class="nova-attachment-meta">${this.escapeHtml(metaBits.join(" • "))}</div>` : ""}
            </figcaption>
          </figure>
        `;
      }

      if (this.isVideoType(att.type, att.mime_type, att.url, att.filename)) {
        return `
          <figure class="nova-attachment-card nova-attachment-media ${typeClass}" data-attachment-id="${this.escapeHtml(att.id)}">
            <div class="nova-attachment-media-frame">
              <video
                class="nova-attachment-video"
                controls
                preload="metadata"
                playsinline
                src="${safeUrl}"
              ></video>
            </div>
            <figcaption class="nova-attachment-caption">
              <div class="nova-attachment-title-row">
                <span class="nova-attachment-kind-pill">VIDEO</span>
                <a class="nova-attachment-open" href="${safeUrl}" target="_blank" rel="noopener noreferrer">Open</a>
              </div>
              <div class="nova-attachment-title">${safeTitle}</div>
              ${metaBits.length ? `<div class="nova-attachment-meta">${this.escapeHtml(metaBits.join(" • "))}</div>` : ""}
            </figcaption>
          </figure>
        `;
      }

      if (this.isAudioType(att.type, att.mime_type, att.url, att.filename)) {
        return `
          <figure class="nova-attachment-card nova-attachment-audio ${typeClass}" data-attachment-id="${this.escapeHtml(att.id)}">
            <figcaption class="nova-attachment-caption">
              <div class="nova-attachment-title-row">
                <span class="nova-attachment-kind-pill">AUDIO</span>
                <a class="nova-attachment-open" href="${safeUrl}" target="_blank" rel="noopener noreferrer">Open</a>
              </div>
              <div class="nova-attachment-title">${safeTitle}</div>
              ${metaBits.length ? `<div class="nova-attachment-meta">${this.escapeHtml(metaBits.join(" • "))}</div>` : ""}
            </figcaption>
            <audio class="nova-attachment-audio-player" controls preload="none" src="${safeUrl}"></audio>
          </figure>
        `;
      }

      return `
        <div class="nova-attachment-card nova-attachment-file ${typeClass}" data-attachment-id="${this.escapeHtml(att.id)}">
          <div class="nova-attachment-file-top">
            <span class="nova-attachment-kind-pill">${this.escapeHtml((att.type || "file").toUpperCase())}</span>
            ${safeUrl ? `<a class="nova-attachment-open" href="${safeUrl}" target="_blank" rel="noopener noreferrer">Open</a>` : ""}
          </div>
          <div class="nova-attachment-title">${safeTitle}</div>
          ${metaBits.length ? `<div class="nova-attachment-meta">${this.escapeHtml(metaBits.join(" • "))}</div>` : ""}
        </div>
      `;
    },

    renderAttachments(attachments, options = {}) {
      const normalized = this.normalizeAttachments(attachments);
      if (!normalized.length) return "";

      const compact = Boolean(options.compact);
      const modeClass = compact ? " compact" : "";

      return `
        <div class="nova-attachments${modeClass}">
          ${normalized.map((att) => this.buildAttachmentCard(att)).join("")}
        </div>
      `;
    },

    getRoleLabel(role) {
      return String(role || "assistant").toLowerCase() === "user" ? "You" : "Nova";
    },

    buildBadges(message) {
      const meta = message && message.meta ? message.meta : {};
      const debug = message && message.debug ? message.debug : {};
      const badges = [];

      if (meta.fallback_reason || debug.fallback_reason) {
        badges.push('<span class="nova-message-badge">Fallback</span>');
      }

      const attachments = this.normalizeAttachments(message && message.attachments);
      if (attachments.length) {
        badges.push(`<span class="nova-message-badge">Media ${attachments.length}</span>`);
      }

      if (meta.artifact_saved || debug.artifact_saved) {
        badges.push('<span class="nova-message-badge">Artifact Saved</span>');
      }

      return badges.join("");
    },

    buildMessageHtml(message) {
      const role = String(message.role || "assistant").toLowerCase();
      const contentHtml = this.renderMarkdown(message.content || "");
      const attachmentsHtml = this.renderAttachments(message.attachments || []);
      const createdAt = message.created_at
        ? this.escapeHtml(new Date(message.created_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }))
        : "";

      return `
        <article class="nova-message nova-message-${this.slug(role)}" data-message-id="${this.escapeHtml(message.id || "")}">
          <div class="nova-message-inner">
            <div class="nova-message-header">
              <div class="nova-message-author">${this.escapeHtml(this.getRoleLabel(role))}</div>
              ${createdAt ? `<div class="nova-message-time">${createdAt}</div>` : ""}
            </div>
            <div class="nova-message-badges">${this.buildBadges(message)}</div>
            <div class="nova-message-markdown">${contentHtml}</div>
            ${attachmentsHtml}
          </div>
        </article>
      `;
    },

    appendMessage(message) {
      if (!this.state.messageContainer) return null;

      const wrapper = document.createElement("div");
      wrapper.innerHTML = this.buildMessageHtml(message);
      const node = wrapper.firstElementChild;
      if (!node) return null;

      this.state.messageContainer.appendChild(node);
      this.refreshEmptyState();
      this.scrollToBottom();
      return node;
    },

    prependMessage(message) {
      if (!this.state.messageContainer) return null;

      const wrapper = document.createElement("div");
      wrapper.innerHTML = this.buildMessageHtml(message);
      const node = wrapper.firstElementChild;
      if (!node) return null;

      this.state.messageContainer.insertBefore(node, this.state.messageContainer.firstChild);
      this.refreshEmptyState();
      return node;
    },

    renderMessages(messages) {
      if (!this.state.messageContainer) return;
      const list = Array.isArray(messages) ? messages : [];
      this.state.messageContainer.innerHTML = list.map((msg) => this.buildMessageHtml(msg)).join("");
      this.refreshEmptyState();
      this.scrollToBottom();
    },

    clearMessages() {
      if (!this.state.messageContainer) return;
      this.state.messageContainer.innerHTML = "";
      this.refreshEmptyState();
    },

    normalizeIncomingResponse(payload) {
      const data = payload && typeof payload === "object" ? payload : {};
      const assistant =
        data.assistant_message ||
        data.message ||
        data.assistant ||
        null;

      if (assistant && !assistant.attachments && Array.isArray(data.attachments)) {
        assistant.attachments = data.attachments;
      }

      if (assistant && assistant.meta && !assistant.attachments) {
        assistant.attachments = assistant.meta.attachments || [];
      }

      return {
        ok: Boolean(data.ok !== false),
        assistant_message: assistant
          ? {
              id: assistant.id || `msg-${Math.random().toString(36).slice(2, 10)}`,
              role: assistant.role || "assistant",
              content: assistant.content || "",
              attachments: this.normalizeAttachments(assistant.attachments || []),
              created_at: assistant.created_at || new Date().toISOString(),
              meta: assistant.meta || {},
            }
          : null,
        session: data.session || null,
        debug: data.debug || {},
      };
    },

    refreshEmptyState() {
      if (!this.state.emptyState || !this.state.messageContainer) return;
      const hasMessages = this.state.messageContainer.children.length > 0;
      this.state.emptyState.style.display = hasMessages ? "none" : "";
    },

    scrollToBottom() {
      if (!this.state.messageContainer) return;
      const scroller =
        this.state.messageContainer.closest(".nova-chat-scroll") ||
        this.state.messageContainer.parentElement ||
        this.state.messageContainer;
      scroller.scrollTop = scroller.scrollHeight;
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      NovaRender.init();
    });
  } else {
    NovaRender.init();
  }
})();