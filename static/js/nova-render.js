(() => {
  "use strict";

  if (window.__novaRenderMessagesLoaded) {
    console.warn("Nova render messages already loaded. Skipping duplicate module.");
    return;
  }
  window.__novaRenderMessagesLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  const state = (Nova.state = Nova.state || {});
  const dom = (Nova.dom = Nova.dom || {});
  const render = (Nova.render = Nova.render || {});
  const util = (Nova.util = Nova.util || {});

  function byId(id) {
    return document.getElementById(id);
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function asString(value, fallback = "") {
    return typeof value === "string" ? value : fallback;
  }

  function escapeHtml(value) {
    if (typeof util.escapeHtml === "function") {
      return util.escapeHtml(value);
    }

    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function extractMessageText(message) {
    if (typeof util.extractMessageText === "function") {
      return util.extractMessageText(message);
    }

    if (!message) return "";
    if (typeof message.content === "string") return message.content;
    if (typeof message.text === "string") return message.text;

    if (Array.isArray(message.content)) {
      return message.content
        .map((part) => {
          if (typeof part === "string") return part;
          if (part && typeof part.text === "string") return part.text;
          if (part && typeof part.content === "string") return part.content;
          return "";
        })
        .filter(Boolean)
        .join("\n");
    }

    return "";
  }

  function formatDateLoose(value) {
    if (typeof util.formatDateLoose === "function") {
      return util.formatDateLoose(value);
    }

    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    try {
      return date.toLocaleString();
    } catch (_) {
      return "";
    }
  }

  function cacheDom() {
    dom.chatMessages = dom.chatMessages || byId("chatMessages");
    dom.emptyState = dom.emptyState || byId("emptyState");
    return dom;
  }

  function show(node) {
    if (node) node.classList.remove("hidden");
  }

  function hide(node) {
    if (node) node.classList.add("hidden");
  }

  function roleLabel(role) {
    const normalized = asString(role, "assistant").toLowerCase();
    if (normalized === "user") return "You";
    if (normalized === "system") return "System";
    return "Nova";
  }

  function normalizeRole(role) {
    const normalized = asString(role, "assistant").toLowerCase();
    if (normalized === "user" || normalized === "assistant" || normalized === "system") {
      return normalized;
    }
    return "assistant";
  }

  function buildAttachmentHtml(message) {
    const attachments = asArray(message?.attachments);
    if (!attachments.length) return "";

    return `
      <div class="message-attachments">
        ${attachments
          .map((file, index) => {
            const name = escapeHtml(asString(file?.name || file?.filename, `file-${index + 1}`));
            const type = escapeHtml(asString(file?.type || file?.mime_type, ""));
            const size = Number(file?.size || 0) || 0;
            const url = asString(file?.url || file?.file_url, "");
            const meta = [type, size ? `${size} bytes` : ""].filter(Boolean).join(" • ");

            return `
              <div class="message-attachment">
                ${
                  url
                    ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${name}</a>`
                    : `<span>${name}</span>`
                }
                ${meta ? `<div class="message-attachment-meta">${escapeHtml(meta)}</div>` : ""}
              </div>
            `;
          })
          .join("")}
      </div>
    `;
  }

  function buildActionsHtml(message, index) {
    const role = normalizeRole(message?.role);
    if (role !== "assistant") return "";

    const isStreaming = Boolean(message?.__streaming);

    return `
      <div class="message-actions">
        <button
          class="message-action-btn"
          type="button"
          data-copy-message="${index}"
          aria-label="Copy message"
          title="Copy message"
          ${isStreaming ? "disabled" : ""}
        >
          ${isStreaming ? "Copying..." : "Copy"}
        </button>
      </div>
    `;
  }

  function buildMessageHtml(message, index) {
    const role = normalizeRole(message?.role);
    const label = roleLabel(role);
    const text = escapeHtml(extractMessageText(message));
    const createdAt = escapeHtml(formatDateLoose(message?.created_at || ""));
    const isStreaming = Boolean(message?.__streaming);

    return `
      <article
        class="message message-${role} ${isStreaming ? "is-streaming" : ""}"
        data-message-index="${index}"
      >
        <div class="message-head">
          <div class="message-role">${escapeHtml(label)}</div>
          ${createdAt ? `<div class="message-time">${createdAt}</div>` : ""}
        </div>

        <div class="message-body">
          <pre>${text}</pre>
        </div>

        ${buildAttachmentHtml(message)}
        ${buildActionsHtml(message, index)}
      </article>
    `;
  }

  function renderMessages() {
    cacheDom();
    if (!dom.chatMessages) return;

    const messages = asArray(state.messages);

    if (!messages.length) {
      if (dom.emptyState) show(dom.emptyState);
      dom.chatMessages.innerHTML = dom.emptyState ? dom.emptyState.outerHTML : "";
      return;
    }

    if (dom.emptyState) hide(dom.emptyState);

    const emptyHtml = dom.emptyState ? dom.emptyState.outerHTML : "";
    const html = messages.map((message, index) => buildMessageHtml(message, index)).join("");
    dom.chatMessages.innerHTML = emptyHtml + html;
    dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
  }

  render.messagesImpl = renderMessages;
})();