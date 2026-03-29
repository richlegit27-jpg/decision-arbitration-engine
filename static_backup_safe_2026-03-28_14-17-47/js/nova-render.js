(function () {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.render = Nova.render || {};

  const renderApi = Nova.render;

  function qs(id) {
    return document.getElementById(id);
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeString(value, fallback = "") {
    return typeof value === "string" ? value : fallback;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatTime(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  function getMessagesRoot() {
    return (
      qs("chatMessages") ||
      qs("messages") ||
      qs("messageList") ||
      document.querySelector(".chat-messages")
    );
  }

  function getSessionRoot() {
    return (
      qs("sessionList") ||
      document.querySelector(".session-list")
    );
  }

  function getEmptyState() {
    return (
      qs("emptyState") ||
      document.querySelector(".empty-state")
    );
  }

  function scrollMessagesToBottom(force = false) {
    const root = getMessagesRoot();
    if (!root) return;

    const nearBottom =
      root.scrollHeight - root.scrollTop - root.clientHeight < 180;

    if (force || nearBottom) {
      root.scrollTop = root.scrollHeight;
    }
  }

  function updateEmptyState() {
    const root = getMessagesRoot();
    const empty = getEmptyState();
    if (!root || !empty) return;

    const hasMessages = root.children.length > 0;
    empty.classList.toggle("hidden", hasMessages);
  }

  function normalizeRole(role) {
    const r = safeString(role, "assistant").toLowerCase();
    if (r === "user" || r === "assistant" || r === "system") return r;
    return "assistant";
  }

  function normalizeMessage(msg) {
    if (!msg || typeof msg !== "object") {
      return {
        id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        role: "assistant",
        content: "",
        created_at: new Date().toISOString(),
        attachments: [],
        meta: {},
      };
    }

    return {
      id: safeString(msg.id, `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`),
      role: normalizeRole(msg.role),
      content:
        safeString(msg.content, "") ||
        safeString(msg.text, "") ||
        safeString(msg.message, ""),
      created_at: safeString(msg.created_at, new Date().toISOString()),
      attachments: safeArray(msg.attachments),
      meta: msg.meta && typeof msg.meta === "object" ? msg.meta : {},
    };
  }

  function renderInline(text) {
    return escapeHtml(text)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");
  }

  function renderParagraphBlock(text) {
    const trimmed = safeString(text, "");
    if (!trimmed) return "";

    return trimmed
      .split(/\n{2,}/)
      .map((block) => {
        if (!block.trim()) return "";
        return `<p>${renderInline(block).replace(/\n/g, "<br>")}</p>`;
      })
      .join("");
  }

  function renderMessageHtml(content) {
    const text = safeString(content, "");
    if (!text) return "";

    const parts = [];
    const fence = /```([a-zA-Z0-9_-]+)?\n([\s\S]*?)```/g;
    let lastIndex = 0;
    let match;

    while ((match = fence.exec(text))) {
      const before = text.slice(lastIndex, match.index);
      if (before) {
        parts.push(renderParagraphBlock(before));
      }

      const lang = escapeHtml(match[1] || "");
      const code = escapeHtml(match[2] || "");
      parts.push(`<pre class="nova-codeblock"><code class="language-${lang}">${code}</code></pre>`);

      lastIndex = match.index + match[0].length;
    }

    const tail = text.slice(lastIndex);
    if (tail) {
      parts.push(renderParagraphBlock(tail));
    }

    return parts.join("");
  }

  function createAttachmentChip(att) {
    const div = document.createElement("div");
    div.className = "message-attachment-chip";

    const name =
      safeString(att?.name, "") ||
      safeString(att?.filename, "") ||
      "attachment";

    const url =
      safeString(att?.url, "") ||
      safeString(att?.path, "");

    if (url) {
      const link = document.createElement("a");
      link.href = url;
      link.target = "_blank";
      link.rel = "noreferrer noopener";
      link.textContent = name;
      div.appendChild(link);
    } else {
      div.textContent = name;
    }

    return div;
  }

  function createMessageActions(msg) {
    const wrap = document.createElement("div");
    wrap.className = "message-actions";

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "icon-btn";
    copyBtn.textContent = "Copy";
    copyBtn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(safeString(msg.content, ""));
        copyBtn.textContent = "Copied";
        setTimeout(() => {
          copyBtn.textContent = "Copy";
        }, 1200);
      } catch (_err) {
        copyBtn.textContent = "Failed";
        setTimeout(() => {
          copyBtn.textContent = "Copy";
        }, 1200);
      }
    });

    wrap.appendChild(copyBtn);
    return wrap;
  }

  function createMessageNode(rawMsg) {
    const msg = normalizeMessage(rawMsg);

    const node = document.createElement("article");
    node.className = `chat-message ${msg.role}`;
    node.dataset.messageId = msg.id;
    node.dataset.role = msg.role;

    const bubble = document.createElement("div");
    bubble.className = "message-body";

    const content = document.createElement("div");
    content.className = "message-content";
    content.innerHTML = renderMessageHtml(msg.content);

    bubble.appendChild(content);

    const attachments = safeArray(msg.attachments);
    if (attachments.length) {
      const attachmentWrap = document.createElement("div");
      attachmentWrap.className = "message-attachments";
      attachments.forEach((att) => {
        attachmentWrap.appendChild(createAttachmentChip(att));
      });
      bubble.appendChild(attachmentWrap);
    }

    const footer = document.createElement("div");
    footer.className = "message-footer";
    footer.innerHTML = `
      <span class="message-role">${escapeHtml(msg.role)}</span>
      <span class="message-time">${escapeHtml(formatTime(msg.created_at))}</span>
    `;
    bubble.appendChild(footer);

    node.appendChild(bubble);

    if (msg.role === "assistant") {
      node.appendChild(createMessageActions(msg));
    }

    return node;
  }

  function replaceMessageNode(messageId, rawMsg) {
    const root = getMessagesRoot();
    if (!root) return;

    const existing = root.querySelector(`[data-message-id="${CSS.escape(messageId)}"]`);
    const nextNode = createMessageNode(rawMsg);

    if (existing && existing.parentNode) {
      existing.parentNode.replaceChild(nextNode, existing);
    } else {
      root.appendChild(nextNode);
    }
  }

  function patchMessage(messageId, rawMsg) {
    const root = getMessagesRoot();
    if (!root) return;

    const existing = root.querySelector(`[data-message-id="${CSS.escape(messageId)}"]`);
    if (!existing) {
      root.appendChild(createMessageNode(rawMsg));
      updateEmptyState();
      scrollMessagesToBottom(false);
      return;
    }

    const msg = normalizeMessage(rawMsg);
    existing.dataset.role = msg.role;
    existing.className = `chat-message ${msg.role}`;

    let bubble = existing.querySelector(".message-body");
    if (!bubble) {
      bubble = document.createElement("div");
      bubble.className = "message-body";
      existing.appendChild(bubble);
    }

    let content = bubble.querySelector(".message-content");
    if (!content) {
      content = document.createElement("div");
      content.className = "message-content";
      bubble.prepend(content);
    }

    content.innerHTML = renderMessageHtml(msg.content);

    let attachmentWrap = bubble.querySelector(".message-attachments");
    const attachments = safeArray(msg.attachments);

    if (attachments.length) {
      if (!attachmentWrap) {
        attachmentWrap = document.createElement("div");
        attachmentWrap.className = "message-attachments";
        bubble.appendChild(attachmentWrap);
      }
      attachmentWrap.innerHTML = "";
      attachments.forEach((att) => {
        attachmentWrap.appendChild(createAttachmentChip(att));
      });
    } else if (attachmentWrap) {
      attachmentWrap.remove();
    }

    let footer = bubble.querySelector(".message-footer");
    if (!footer) {
      footer = document.createElement("div");
      footer.className = "message-footer";
      bubble.appendChild(footer);
    }

    footer.innerHTML = `
      <span class="message-role">${escapeHtml(msg.role)}</span>
      <span class="message-time">${escapeHtml(formatTime(msg.created_at))}</span>
    `;

    let actions = existing.querySelector(".message-actions");
    if (msg.role === "assistant") {
      if (!actions) {
        actions = createMessageActions(msg);
        existing.appendChild(actions);
      } else {
        actions.remove();
        existing.appendChild(createMessageActions(msg));
      }
    } else if (actions) {
      actions.remove();
    }

    updateEmptyState();
    scrollMessagesToBottom(false);
  }

  function renderMessages(messages) {
    const root = getMessagesRoot();
    if (!root) return;

    root.innerHTML = "";
    safeArray(messages).forEach((msg) => {
      root.appendChild(createMessageNode(msg));
    });

    updateEmptyState();
    scrollMessagesToBottom(true);
  }

  function renderSessions(sessions, activeSessionId) {
    const root = getSessionRoot();
    if (!root) return;

    root.innerHTML = "";

    safeArray(sessions).forEach((session) => {
      const id = safeString(session.id, "");
      const title = safeString(session.title, "New chat");
      const updatedAt = safeString(session.updated_at || session.created_at, "");
      const count = safeArray(session.messages).length;
      const isActive = id === activeSessionId;

      const row = document.createElement("div");
      row.className = `session-item${isActive ? " is-active" : ""}`;
      row.dataset.sessionId = id;

      const mainBtn = document.createElement("button");
      mainBtn.type = "button";
      mainBtn.className = "session-main-btn";
      mainBtn.dataset.sessionId = id;
      mainBtn.innerHTML = `
        <span class="session-title">${escapeHtml(title)}</span>
        <span class="session-meta">${escapeHtml(`${count} msg${count === 1 ? "" : "s"}${updatedAt ? ` · ${formatTime(updatedAt)}` : ""}`)}</span>
      `;

      row.appendChild(mainBtn);
      root.appendChild(row);
    });
  }

  renderApi.createMessageNode = createMessageNode;
  renderApi.renderMessages = renderMessages;
  renderApi.renderChatMessages = renderMessages;
  renderApi.renderSessions = renderSessions;
  renderApi.patchMessage = patchMessage;
  renderApi.updateMessage = patchMessage;
  renderApi.replaceMessageNode = replaceMessageNode;
  renderApi.scrollMessagesToBottom = scrollMessagesToBottom;
})();