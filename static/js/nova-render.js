(() => {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.render = Nova.render || {};

  function $(selector, root = document) {
    return root.querySelector(selector);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function safeText(content) {
    if (content == null) return "";

    if (typeof content === "string") {
      return content;
    }

    if (typeof content === "number" || typeof content === "boolean") {
      return String(content);
    }

    if (Array.isArray(content)) {
      return content
        .map((item) => {
          if (item == null) return "";
          if (typeof item === "string") return item;
          if (typeof item === "number" || typeof item === "boolean") return String(item);

          if (typeof item === "object") {
            if (typeof item.text === "string") return item.text;
            if (typeof item.content === "string") return item.content;

            if (Array.isArray(item.content)) {
              return item.content
                .map((part) => {
                  if (typeof part === "string") return part;
                  if (part && typeof part.text === "string") return part.text;
                  try {
                    return JSON.stringify(part, null, 2);
                  } catch {
                    return String(part);
                  }
                })
                .join("\n");
            }

            try {
              return JSON.stringify(item, null, 2);
            } catch {
              return String(item);
            }
          }

          return String(item);
        })
        .filter(Boolean)
        .join("\n");
    }

    if (typeof content === "object") {
      if (typeof content.text === "string") return content.text;
      if (typeof content.content === "string") return content.content;
      if (typeof content.message === "string") return content.message;

      if (content.message && typeof content.message === "object") {
        if (typeof content.message.content === "string") return content.message.content;
        if (typeof content.message.text === "string") return content.message.text;
      }

      if (Array.isArray(content.output)) {
        const outputText = content.output
          .map((entry) => {
            if (!entry) return "";

            if (typeof entry.text === "string") return entry.text;

            if (Array.isArray(entry.content)) {
              return entry.content
                .map((part) => {
                  if (!part) return "";
                  if (typeof part.text === "string") return part.text;
                  if (typeof part.content === "string") return part.content;
                  try {
                    return JSON.stringify(part, null, 2);
                  } catch {
                    return String(part);
                  }
                })
                .filter(Boolean)
                .join("\n");
            }

            try {
              return JSON.stringify(entry, null, 2);
            } catch {
              return String(entry);
            }
          })
          .filter(Boolean)
          .join("\n");

        if (outputText.trim()) return outputText;
      }

      try {
        return JSON.stringify(content, null, 2);
      } catch {
        return String(content);
      }
    }

    return String(content);
  }

  function formatTimestamp(value) {
    if (!value) return "";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  function getRoleLabel(role) {
    const normalized = String(role || "").toLowerCase();
    if (normalized === "assistant") return "CHAT";
    if (normalized === "user") return "USER";
    if (normalized === "system") return "SYSTEM";
    return normalized ? normalized.toUpperCase() : "CHAT";
  }

  function normalizeMessage(input) {
    const raw = input || {};
    return {
      id: raw.id || `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      role: raw.role || "assistant",
      content: safeText(raw.content),
      created_at: raw.created_at || "",
      attachments: Array.isArray(raw.attachments) ? raw.attachments : [],
      debug: raw.debug || null,
      meta: raw.meta || null,
      raw,
    };
  }

  function renderAttachments(attachments) {
    if (!Array.isArray(attachments) || !attachments.length) return "";

    return `
      <div class="nova-message-attachments">
        ${attachments
          .map((file) => {
            const name = escapeHtml(file?.name || file?.filename || "attachment");
            const url = file?.url ? escapeHtml(file.url) : "";
            if (url) {
              return `<a class="nova-attachment-chip" href="${url}" target="_blank" rel="noopener noreferrer">${name}</a>`;
            }
            return `<span class="nova-attachment-chip">${name}</span>`;
          })
          .join("")}
      </div>
    `;
  }

  function renderDebugBlock(message) {
    if (!message.debug) return "";
    return `
      <details class="nova-message-debug">
        <summary>debug</summary>
        <pre>${escapeHtml(safeText(message.debug))}</pre>
      </details>
    `;
  }

  function messageHtml(message) {
    const roleLabel = getRoleLabel(message.role);
    const content = escapeHtml(message.content || "");
    const time = formatTimestamp(message.created_at);

    return `
      <article class="nova-message nova-message-${escapeHtml(String(message.role || "assistant").toLowerCase())}" data-message-id="${escapeHtml(message.id)}">
        <div class="nova-message-inner">
          <div class="nova-message-head">
            <div class="nova-message-role">${roleLabel}</div>
            ${time ? `<div class="nova-message-time">${escapeHtml(time)}</div>` : ""}
          </div>
          <div class="nova-message-markdown">${content.replace(/\n/g, "<br>")}</div>
          ${renderAttachments(message.attachments)}
          ${renderDebugBlock(message)}
        </div>
      </article>
    `;
  }

  function renderMessages(messages, options = {}) {
    const container =
      options.container ||
      $("#messages") ||
      $("#novaMessages") ||
      $('[data-messages]');

    if (!container) {
      console.warn("Nova render: message container not found");
      return;
    }

    const normalized = Array.isArray(messages)
      ? messages.map(normalizeMessage)
      : [];

    container.innerHTML = normalized.map(messageHtml).join("");

    const emptyState =
      $("#novaEmptyState") ||
      $('[data-empty-state]');

    if (emptyState) {
      emptyState.style.display = normalized.length ? "none" : "";
    }

    container.scrollTop = container.scrollHeight;
  }

  function appendMessage(message, options = {}) {
    const container =
      options.container ||
      $("#messages") ||
      $("#novaMessages") ||
      $('[data-messages]');

    if (!container) {
      console.warn("Nova render: message container not found");
      return;
    }

    const normalized = normalizeMessage(message);
    container.insertAdjacentHTML("beforeend", messageHtml(normalized));

    const emptyState =
      $("#novaEmptyState") ||
      $('[data-empty-state]');

    if (emptyState) {
      emptyState.style.display = "none";
    }

    container.scrollTop = container.scrollHeight;
    return normalized;
  }

  function clearMessages(options = {}) {
    const container =
      options.container ||
      $("#messages") ||
      $("#novaMessages") ||
      $('[data-messages]');

    if (!container) return;
    container.innerHTML = "";

    const emptyState =
      $("#novaEmptyState") ||
      $('[data-empty-state]');

    if (emptyState) {
      emptyState.style.display = "";
    }
  }

  Nova.render.safeText = safeText;
  Nova.render.normalizeMessage = normalizeMessage;
  Nova.render.renderMessages = renderMessages;
  Nova.render.appendMessage = appendMessage;
  Nova.render.clearMessages = clearMessages;

  console.log("nova-render loaded");
})();