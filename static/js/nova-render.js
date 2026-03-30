(function () {
  "use strict";

  const els = {
    messages: document.getElementById("messages"),
    emptyState: document.getElementById("novaEmptyState"),
  };

  const state = {
    pendingAssistantId: null,
  };

  function log(...args) {
    console.log("nova-render loaded", ...args);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function nowTime() {
    return new Date().toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function setEmptyStateVisible(visible) {
    if (!els.emptyState) return;
    els.emptyState.style.display = visible ? "" : "none";
  }

  function scrollMessagesToBottom() {
    if (!els.messages) return;
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function normalizeText(value) {
    if (value == null) return "";
    if (typeof value === "string") return value;

    if (typeof value === "object") {
      if (typeof value.content === "string") return value.content;
      if (typeof value.text === "string") return value.text;

      if (Array.isArray(value.parts)) {
        return value.parts.map((part) => {
          if (typeof part === "string") return part;
          if (part && typeof part.text === "string") return part.text;
          return "";
        }).join("\n");
      }
    }

    return String(value);
  }

  function extractAssistantText(payload) {
    if (!payload || typeof payload !== "object") return "";

    if (typeof payload.message === "string") return payload.message;
    if (typeof payload.reply === "string") return payload.reply;
    if (typeof payload.response === "string") return payload.response;
    if (typeof payload.output_text === "string") return payload.output_text;

    if (payload.assistant_message) {
      const direct =
        normalizeText(payload.assistant_message.content) ||
        normalizeText(payload.assistant_message);
      if (direct) return direct;
    }

    if (payload.data && typeof payload.data === "object") {
      const nested =
        payload.data.message ||
        payload.data.reply ||
        payload.data.response ||
        normalizeText(payload.data.assistant_message?.content) ||
        normalizeText(payload.data.assistant_message);
      if (nested) return normalizeText(nested);
    }

    return "";
  }

  function extractDebug(payload) {
    if (!payload || typeof payload !== "object") return null;
    return payload.debug || payload.meta || payload.assistant_message?.meta || null;
  }

  function extractAttachments(payload) {
    if (!payload || typeof payload !== "object") return [];
    if (Array.isArray(payload.attachments)) return payload.attachments;
    if (Array.isArray(payload.assistant_message?.attachments)) {
      return payload.assistant_message.attachments;
    }
    return [];
  }

  function normalizeAttachment(attachment) {
    if (!attachment || typeof attachment !== "object") {
      return {
        url: "#",
        label: "attachment",
      };
    }

    return {
      url:
        attachment.url ||
        attachment.file_url ||
        attachment.path ||
        attachment.href ||
        "#",
      label:
        attachment.name ||
        attachment.filename ||
        attachment.title ||
        "attachment",
    };
  }

  function createAttachmentsNode(attachments) {
    const list = safeArray(attachments).map(normalizeAttachment).filter(Boolean);
    if (!list.length) return null;

    const wrap = document.createElement("div");
    wrap.className = "nova-message-attachments";

    list.forEach((item) => {
      const chip = document.createElement("a");
      chip.className = "nova-attachment-chip";
      chip.href = item.url;
      chip.target = "_blank";
      chip.rel = "noreferrer";
      chip.textContent = item.label;
      wrap.appendChild(chip);
    });

    return wrap;
  }

  function createDebugNode(debug) {
    if (!debug) return null;

    const details = document.createElement("details");
    details.className = "nova-message-debug";

    const summary = document.createElement("summary");
    summary.textContent = "Debug";

    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(debug, null, 2);

    details.appendChild(summary);
    details.appendChild(pre);
    return details;
  }

  function createMessageElement({
    role = "assistant",
    content = "",
    time = "",
    debug = null,
    attachments = [],
    pending = false,
    pendingId = "",
    messageId = "",
  }) {
    const wrapper = document.createElement("div");
    wrapper.className = `nova-message nova-message-${role}`;

    if (pending) wrapper.dataset.pending = "true";
    if (pendingId) wrapper.dataset.pendingId = pendingId;
    if (messageId) wrapper.dataset.messageId = messageId;

    const inner = document.createElement("div");
    inner.className = "nova-message-inner";

    const head = document.createElement("div");
    head.className = "nova-message-head";

    const roleEl = document.createElement("div");
    roleEl.className = "nova-message-role";
    roleEl.textContent = role === "user" ? "YOU" : "NOVA";

    const timeEl = document.createElement("div");
    timeEl.className = "nova-message-time";
    timeEl.textContent = time || nowTime();

    head.appendChild(roleEl);
    head.appendChild(timeEl);

    const body = document.createElement("div");
    body.className = "nova-message-markdown";
    body.textContent = content || "";

    inner.appendChild(head);
    inner.appendChild(body);

    const attachmentsNode = createAttachmentsNode(attachments);
    if (attachmentsNode) {
      inner.appendChild(attachmentsNode);
    }

    const debugNode = createDebugNode(debug);
    if (debugNode) {
      inner.appendChild(debugNode);
    }

    wrapper.appendChild(inner);
    return wrapper;
  }

  function updateMessageElement(node, {
    content,
    debug,
    attachments,
    pending = false,
    pendingId = "",
    messageId = "",
  }) {
    if (!node) return;

    const body = node.querySelector(".nova-message-markdown");
    if (body) {
      body.textContent = content || "";
    }

    const existingAttachments = node.querySelector(".nova-message-attachments");
    if (existingAttachments) {
      existingAttachments.remove();
    }

    const attachmentsNode = createAttachmentsNode(attachments);
    if (attachmentsNode) {
      const inner = node.querySelector(".nova-message-inner");
      if (inner) inner.appendChild(attachmentsNode);
    }

    const existingDebug = node.querySelector(".nova-message-debug");
    if (existingDebug) {
      existingDebug.remove();
    }

    const debugNode = createDebugNode(debug);
    if (debugNode) {
      const inner = node.querySelector(".nova-message-inner");
      if (inner) inner.appendChild(debugNode);
    }

    if (pending) {
      node.dataset.pending = "true";
    } else {
      delete node.dataset.pending;
    }

    if (pendingId) {
      node.dataset.pendingId = pendingId;
    } else {
      delete node.dataset.pendingId;
    }

    if (messageId) {
      node.dataset.messageId = messageId;
    }

    scrollMessagesToBottom();
  }

  function findPendingAssistantNode(pendingId) {
    if (!els.messages) return null;

    if (pendingId) {
      try {
        const node = els.messages.querySelector(
          `.nova-message-assistant[data-pending-id="${CSS.escape(pendingId)}"]`
        );
        if (node) return node;
      } catch (error) {
        // ignore bad selector edge case
      }
    }

    return els.messages.querySelector('.nova-message-assistant[data-pending="true"]');
  }

  function appendMessage(message) {
    if (!els.messages) return null;
    setEmptyStateVisible(false);

    const node = createMessageElement(message);
    els.messages.appendChild(node);
    scrollMessagesToBottom();
    return node;
  }

  function replacePendingAssistant(message, options = {}) {
    if (!els.messages) return null;

    const pendingId =
      options.pendingId ||
      message.pendingId ||
      state.pendingAssistantId ||
      "";

    let node = findPendingAssistantNode(pendingId);

    if (node) {
      updateMessageElement(node, {
        content: message.content || "",
        debug: message.debug || null,
        attachments: safeArray(message.attachments),
        pending: false,
        pendingId: "",
        messageId: message.messageId || "",
      });
      state.pendingAssistantId = null;
      return node;
    }

    state.pendingAssistantId = null;
    return appendMessage({
      role: "assistant",
      content: message.content || "",
      time: message.time || nowTime(),
      debug: message.debug || null,
      attachments: safeArray(message.attachments),
      pending: false,
      pendingId: "",
      messageId: message.messageId || "",
    });
  }

  function createPendingAssistantBubble(content = "...", options = {}) {
    if (!els.messages) return null;

    const pendingId =
      options.pendingId ||
      `pending-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    const existing = findPendingAssistantNode(pendingId);
    if (existing) {
      state.pendingAssistantId = pendingId;
      return existing;
    }

    state.pendingAssistantId = pendingId;

    return appendMessage({
      role: "assistant",
      content,
      time: nowTime(),
      pending: true,
      pendingId,
      messageId: "",
    });
  }

  function renderUserMessage(content, options = {}) {
    return appendMessage({
      role: "user",
      content: normalizeText(content),
      time: options.time || nowTime(),
      debug: options.debug || null,
      attachments: safeArray(options.attachments),
      pending: false,
      pendingId: "",
      messageId: options.messageId || "",
    });
  }

  function renderAssistantMessage(content, options = {}) {
    const normalized = normalizeText(content);

    if (options.replacePending) {
      return replacePendingAssistant({
        content: normalized,
        time: options.time || nowTime(),
        debug: options.debug || null,
        attachments: safeArray(options.attachments),
        messageId: options.messageId || "",
      }, {
        pendingId: options.pendingId || "",
      });
    }

    return appendMessage({
      role: "assistant",
      content: normalized,
      time: options.time || nowTime(),
      debug: options.debug || null,
      attachments: safeArray(options.attachments),
      pending: !!options.pending,
      pendingId: options.pendingId || "",
      messageId: options.messageId || "",
    });
  }

  function renderAssistantPayload(payload, options = {}) {
    const text = extractAssistantText(payload) || "(empty response)";
    const debug = extractDebug(payload);
    const attachments = extractAttachments(payload);
    const messageId =
      payload?.assistant_message?.id ||
      payload?.message_id ||
      "";

    return renderAssistantMessage(text, {
      time: options.time || nowTime(),
      debug,
      attachments,
      replacePending: options.replacePending !== false,
      pendingId: options.pendingId || state.pendingAssistantId || "",
      messageId,
    });
  }

  function clearMessages() {
    if (!els.messages) return;

    Array.from(els.messages.children).forEach((child) => {
      if (child.id === "novaEmptyState") return;
      child.remove();
    });

    state.pendingAssistantId = null;
    setEmptyStateVisible(true);
  }

  function removeMessageByMessageId(messageId) {
    if (!els.messages || !messageId) return false;
    const node = els.messages.querySelector(`[data-message-id="${CSS.escape(messageId)}"]`);
    if (!node) return false;
    node.remove();
    setEmptyStateVisible(els.messages.children.length <= 1);
    return true;
  }

  function init() {
    if (!els.messages) {
      console.warn("nova-render: #messages missing");
      return;
    }

    setEmptyStateVisible(els.messages.children.length <= 1);
    log();
  }

  const NovaRender = {
    appendMessage,
    createMessageElement,
    updateMessageElement,
    renderUserMessage,
    renderAssistantMessage,
    renderAssistantPayload,
    createPendingAssistantBubble,
    replacePendingAssistant,
    clearMessages,
    removeMessageByMessageId,
    setEmptyStateVisible,
    scrollMessagesToBottom,
    extractAssistantText,
    extractDebug,
    extractAttachments,
    getState() {
      return {
        pendingAssistantId: state.pendingAssistantId,
      };
    },
    setPendingAssistantId(value) {
      state.pendingAssistantId = value || null;
    },
  };

  window.NovaRender = NovaRender;

  document.addEventListener("nova:render:user", (event) => {
    const detail = event.detail || {};
    NovaRender.renderUserMessage(detail.content || "", detail);
  });

  document.addEventListener("nova:render:assistant-pending", (event) => {
    const detail = event.detail || {};
    NovaRender.createPendingAssistantBubble(detail.content || "...", detail);
  });

  document.addEventListener("nova:render:assistant-final", (event) => {
    const detail = event.detail || {};
    if (detail.payload) {
      NovaRender.renderAssistantPayload(detail.payload, {
        ...detail,
        replacePending: true,
      });
      return;
    }

    NovaRender.renderAssistantMessage(detail.content || "", {
      ...detail,
      replacePending: true,
    });
  });

  document.addEventListener("nova:render:clear", () => {
    NovaRender.clearMessages();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();