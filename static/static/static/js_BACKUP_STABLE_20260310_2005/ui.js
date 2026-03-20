// C:\Users\Owner\nova\static\js\ui.js

window.NovaUI = (() => {
  const { state, els } = window.NovaState;

  marked.setOptions({
    breaks: true,
    gfm: true,
    highlight(code, lang) {
      try {
        if (lang && hljs.getLanguage(lang)) {
          return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
      } catch {
        return code;
      }
    },
  });

  function escapeHtml(text = "") {
    return text
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function renderMarkdown(text) {
    return marked.parse(text || "");
  }

  function autosizeTextarea() {
    els.input.style.height = "auto";
    els.input.style.height = Math.min(els.input.scrollHeight, 240) + "px";
  }

  function applyTheme() {
    document.body.classList.toggle("light", state.theme === "light");
    localStorage.setItem("nova_theme", state.theme);
  }

  function setTopTitle() {
    const active = state.chats.find((c) => c.chat_id === state.chatId);
    els.chatTitleTop.textContent = active?.title || "Ready";
  }

  function setEmptyState() {
    els.messages.innerHTML = `
      <div class="empty-state">
        <div class="empty-kicker">Nova local workspace</div>
        <div class="empty-title">Fast local chat shell. Clean. Stable. Ready.</div>
        <div class="empty-copy">
          Your UI is now focused on getting finished fast. Chat locally, switch conversations, polish the shell,
          and keep momentum without OpenAI blocking the build.
        </div>

        <div class="empty-grid">
          <div class="empty-card">
            <div class="empty-card-title">Start a chat</div>
            <div class="empty-card-copy">Type into the composer and send your first message.</div>
          </div>
          <div class="empty-card">
            <div class="empty-card-title">Use local AI</div>
            <div class="empty-card-copy">Flask talks to Ollama while the frontend stays clean and stable.</div>
          </div>
          <div class="empty-card">
            <div class="empty-card-title">Real attachments</div>
            <div class="empty-card-copy">Text and code files are now uploaded, saved, and included in the prompt.</div>
          </div>
        </div>
      </div>
    `;
  }

  function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;

    els.toastHost.appendChild(toast);

    requestAnimationFrame(() => {
      toast.classList.add("show");
    });

    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 180);
    }, 1800);
  }

  function scrollMessagesToBottom() {
    els.messages.scrollTop = els.messages.scrollHeight;
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  }

  function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleString();
  }

  function messageActions(role, content) {
    if (role === "assistant") {
      return `
        <div class="message-actions">
          <button class="msg-action" data-action="copy" data-content="${escapeHtml(content)}">Copy</button>
        </div>
      `;
    }

    return `
      <div class="message-actions">
        <button class="msg-action" data-action="copy" data-content="${escapeHtml(content)}">Copy</button>
        <button class="msg-action" data-action="edit" data-content="${escapeHtml(content)}">Edit</button>
      </div>
    `;
  }

  function renderAttachmentBadges(attachments = []) {
    if (!attachments.length) {
      return "";
    }

    return `
      <div class="attachment-tray">
        ${attachments.map((file) => `
          <div class="attachment-chip">
            <span>📎</span>
            <span class="attachment-chip-name">${escapeHtml(file.name)}</span>
          </div>
        `).join("")}
      </div>
    `;
  }

  function appendMessage(role, content, attachments = []) {
    const row = document.createElement("div");
    row.className = `message-row ${role}`;

    row.innerHTML = `
      <div class="message-bubble">
        <div class="message-header">
          <div class="message-role">${role}</div>
          ${messageActions(role, content)}
        </div>
        ${renderAttachmentBadges(attachments)}
        <div class="message-markdown">${renderMarkdown(content)}</div>
      </div>
    `;

    els.messages.appendChild(row);
    scrollMessagesToBottom();
    return row;
  }

  function appendTypingBubble() {
    const row = document.createElement("div");
    row.className = "message-row assistant";

    row.innerHTML = `
      <div class="message-bubble">
        <div class="message-header">
          <div class="message-role">assistant</div>
        </div>
        <div class="message-markdown">
          <span class="typing-dot-wrap">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </span>
        </div>
      </div>
    `;

    els.messages.appendChild(row);
    scrollMessagesToBottom();
    return row;
  }

  function renderMessages(messages) {
    els.messages.innerHTML = "";

    if (!messages || !messages.length) {
      setEmptyState();
      return;
    }

    for (const msg of messages) {
      appendMessage(msg.role, msg.content, msg.attachments || []);
    }
  }

  function renderChatList() {
    els.chatList.innerHTML = "";

    for (const chat of state.chats) {
      const btn = document.createElement("button");
      btn.className = "chat-item" + (chat.chat_id === state.chatId ? " active" : "");
      btn.innerHTML = `
        <div class="chat-title">${escapeHtml(chat.title || "New chat")}</div>
        <div class="chat-meta">${escapeHtml(formatDate(chat.updated))}</div>
      `;
      btn.addEventListener("click", () => window.NovaChat.loadChat(chat.chat_id));
      els.chatList.appendChild(btn);
    }

    setTopTitle();
  }

  function renderAttachmentTray() {
    if (!state.attachments.length) {
      els.attachmentTray.innerHTML = "";
      els.attachmentTray.classList.add("hidden");
      return;
    }

    els.attachmentTray.classList.remove("hidden");
    els.attachmentTray.innerHTML = state.attachments
      .map((file, index) => {
        return `
          <div class="attachment-chip">
            <span>📎</span>
            <span class="attachment-chip-name">${escapeHtml(file.name)}</span>
            <button class="attachment-chip-remove" data-remove-attachment="${index}" title="Remove">✕</button>
          </div>
        `;
      })
      .join("");
  }

  function clearAttachments() {
    state.attachments = [];
    els.fileUpload.value = "";
    renderAttachmentTray();
  }

  function openSidebarMobile() {
    els.sidebar.classList.add("open");
    els.mobileOverlay.classList.add("show");
  }

  function closeSidebarMobile() {
    els.sidebar.classList.remove("open");
    if (!els.settingsPanel.classList.contains("open")) {
      els.mobileOverlay.classList.remove("show");
    }
  }

  function openSettings() {
    els.settingsPanel.classList.add("open");
    els.settingsPanel.setAttribute("aria-hidden", "false");
    els.mobileOverlay.classList.add("show");
  }

  function closeSettings() {
    els.settingsPanel.classList.remove("open");
    els.settingsPanel.setAttribute("aria-hidden", "true");
    if (!els.sidebar.classList.contains("open")) {
      els.mobileOverlay.classList.remove("show");
    }
  }

  function setSending(isSending) {
    state.isSending = isSending;
    els.sendBtn.disabled = isSending;
    els.regenBtn.disabled = isSending;
    els.input.disabled = isSending;
    els.attachBtn.disabled = isSending;
    els.sendBtn.classList.toggle("is-loading", isSending);
  }

  async function animateAssistantMessage(row, fullText) {
    const header = row.querySelector(".message-header");
    const body = row.querySelector(".message-markdown");

    header.innerHTML = `
      <div class="message-role">assistant</div>
      <div class="message-actions">
        <button class="msg-action" data-action="copy" data-content="">Copy</button>
      </div>
    `;

    let live = "";
    const copyBtn = row.querySelector('[data-action="copy"]');
    const pieces = (fullText || "").split(/(\s+)/);

    for (let i = 0; i < pieces.length; i++) {
      live += pieces[i];
      body.innerHTML = renderMarkdown(live);

      if (copyBtn) {
        copyBtn.setAttribute("data-content", live);
      }

      if (i < 10) await sleep(20);
      else if (i < 35) await sleep(12);
      else await sleep(7);

      scrollMessagesToBottom();
    }

    body.innerHTML = renderMarkdown(fullText || "");
    if (copyBtn) {
      copyBtn.setAttribute("data-content", fullText || "");
    }
  }

  function handleMessageActions(e) {
    const actionBtn = e.target.closest("[data-action]");
    if (actionBtn) {
      const action = actionBtn.getAttribute("data-action");
      const content = actionBtn.getAttribute("data-content") || "";

      if (action === "copy") {
        navigator.clipboard.writeText(content);
        actionBtn.textContent = "Copied";
        showToast("Copied to clipboard");
        setTimeout(() => {
          actionBtn.textContent = "Copy";
        }, 900);
      }

      if (action === "edit") {
        els.input.value = content;
        autosizeTextarea();
        els.input.focus();
        window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
        showToast("Message loaded into composer");
      }

      return;
    }

    const removeBtn = e.target.closest("[data-remove-attachment]");
    if (removeBtn) {
      const index = Number(removeBtn.getAttribute("data-remove-attachment"));
      state.attachments.splice(index, 1);
      renderAttachmentTray();
      showToast("Attachment removed");
    }
  }

  return {
    autosizeTextarea,
    applyTheme,
    setTopTitle,
    setEmptyState,
    showToast,
    scrollMessagesToBottom,
    renderMessages,
    renderChatList,
    renderAttachmentTray,
    clearAttachments,
    openSidebarMobile,
    closeSidebarMobile,
    openSettings,
    closeSettings,
    setSending,
    animateAssistantMessage,
    handleMessageActions,
    appendMessage,
    appendTypingBubble,
  };
})();