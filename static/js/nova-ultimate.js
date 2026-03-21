(() => {
  "use strict";

  const state = {
    activeSessionId: null,
    sessions: [],
    selectedAttachment: null,
    isSending: false,
  };

  const sessionListEl = document.getElementById("sessionList");
  const chatMessagesEl = document.getElementById("chatMessages");
  const activeSessionTitleEl = document.getElementById("activeSessionTitle");
  const messageInputEl = document.getElementById("messageInput");
  const sendBtnEl = document.getElementById("sendBtn");
  const attachBtnEl = document.getElementById("attachBtn");
  const fileInputEl = document.getElementById("fileInput");
  const attachmentPreviewEl = document.getElementById("attachmentPreview");

  const newSessionBtnEl = document.getElementById("newSessionBtn");
  const renameSessionBtnEl = document.getElementById("renameSessionBtn");
  const deleteSessionBtnEl = document.getElementById("deleteSessionBtn");

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatTime(ts) {
    if (!ts) return "";
    const d = new Date(ts * 1000);
    return d.toLocaleString();
  }

  function formatFileSize(size) {
    const n = Number(size || 0);
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  }

  function autoResizeTextarea() {
    messageInputEl.style.height = "auto";
    messageInputEl.style.height = `${Math.min(messageInputEl.scrollHeight, 180)}px`;
  }

  function setSending(flag) {
    state.isSending = flag;
    sendBtnEl.disabled = flag;
    attachBtnEl.disabled = flag;
    messageInputEl.disabled = flag;
    sendBtnEl.textContent = flag ? "Sending..." : "Send";
  }

  function renderSessions() {
    sessionListEl.innerHTML = "";

    if (!state.sessions.length) {
      sessionListEl.innerHTML = `<div class="empty-state">No sessions yet.</div>`;
      return;
    }

    state.sessions.forEach((session) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = `session-item ${session.id === state.activeSessionId ? "active" : ""}`;
      item.innerHTML = `
        <div class="session-item-title">${escapeHtml(session.title || "New Chat")}</div>
        <div class="session-item-meta">${session.message_count || 0} msgs</div>
      `;
      item.addEventListener("click", () => loadSession(session.id));
      sessionListEl.appendChild(item);
    });
  }

  function renderAttachmentBlock(attachment) {
    if (!attachment) return "";

    const name = escapeHtml(attachment.original_name || "file");
    const size = formatFileSize(attachment.file_size);
    const url = escapeHtml(attachment.file_url || "#");
    const type = escapeHtml(attachment.file_type || "file");

    if (attachment.file_type === "image") {
      return `
        <div class="message-attachment image-attachment">
          <a href="${url}" target="_blank" rel="noopener noreferrer">
            <img src="${url}" alt="${name}">
          </a>
          <div class="attachment-meta">
            <span>${name}</span>
            <span>${size}</span>
          </div>
        </div>
      `;
    }

    return `
      <div class="message-attachment file-attachment">
        <div class="file-badge">${type.toUpperCase()}</div>
        <div class="file-info">
          <div class="file-name">${name}</div>
          <div class="file-size">${size}</div>
        </div>
        <a class="file-open" href="${url}" target="_blank" rel="noopener noreferrer">Open</a>
      </div>
    `;
  }

  function renderMessage(msg) {
    const row = document.createElement("div");
    row.className = `message-row ${msg.role === "assistant" ? "assistant" : "user"}`;

    const content = escapeHtml(msg.content || "").replace(/\n/g, "<br>");
    const attachmentHtml = renderAttachmentBlock(msg.attachment);

    row.innerHTML = `
      <article class="message-bubble">
        ${attachmentHtml}
        ${content ? `<div class="message-content">${content}</div>` : ""}
        <div class="message-time">${formatTime(msg.timestamp)}</div>
      </article>
    `;

    chatMessagesEl.appendChild(row);
  }

  function renderMessages(messages) {
    chatMessagesEl.innerHTML = "";
    if (!messages || !messages.length) {
      chatMessagesEl.innerHTML = `<div class="empty-chat">Start a message or attach a file.</div>`;
      return;
    }

    messages.forEach(renderMessage);
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
  }

  function renderAttachmentPreview() {
    if (!state.selectedAttachment) {
      attachmentPreviewEl.classList.add("hidden");
      attachmentPreviewEl.innerHTML = "";
      return;
    }

    const attachment = state.selectedAttachment;
    const name = escapeHtml(attachment.original_name || "file");
    const size = formatFileSize(attachment.file_size);
    const url = escapeHtml(attachment.file_url || "#");

    if (attachment.file_type === "image") {
      attachmentPreviewEl.innerHTML = `
        <div class="preview-card">
          <img class="preview-thumb" src="${url}" alt="${name}">
          <div class="preview-info">
            <div class="preview-name">${name}</div>
            <div class="preview-size">${size}</div>
          </div>
          <button id="removeAttachmentBtn" class="remove-attachment-btn" type="button">Remove</button>
        </div>
      `;
    } else {
      attachmentPreviewEl.innerHTML = `
        <div class="preview-card">
          <div class="preview-file-badge">${escapeHtml(attachment.file_type || "file").toUpperCase()}</div>
          <div class="preview-info">
            <div class="preview-name">${name}</div>
            <div class="preview-size">${size}</div>
          </div>
          <button id="removeAttachmentBtn" class="remove-attachment-btn" type="button">Remove</button>
        </div>
      `;
    }

    attachmentPreviewEl.classList.remove("hidden");

    const removeBtn = document.getElementById("removeAttachmentBtn");
    if (removeBtn) {
      removeBtn.addEventListener("click", clearSelectedAttachment);
    }
  }

  function clearSelectedAttachment() {
    state.selectedAttachment = null;
    fileInputEl.value = "";
    renderAttachmentPreview();
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    return data;
  }

  async function loadState() {
    const data = await fetchJson("/api/state");
    state.activeSessionId = data.active_session_id;
    state.sessions = Array.isArray(data.sessions) ? data.sessions : [];
    renderSessions();

    if (state.activeSessionId) {
      await loadSession(state.activeSessionId);
    }
  }

  async function loadSession(sessionId) {
    const data = await fetchJson(`/api/chat/${encodeURIComponent(sessionId)}`);
    const session = data.session;

    state.activeSessionId = session.id;
    activeSessionTitleEl.textContent = session.title || "New Chat";

    state.sessions = state.sessions.map((s) =>
      s.id === session.id
        ? { ...s, title: session.title || s.title }
        : s
    );
    renderSessions();
    renderMessages(session.messages || []);
  }

  async function createNewSession() {
    const data = await fetchJson("/api/session/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });

    state.activeSessionId = data.active_session_id;
    await refreshSessionsOnly();
    await loadSession(state.activeSessionId);
    messageInputEl.focus();
  }

  async function refreshSessionsOnly() {
    const data = await fetchJson("/api/state");
    state.activeSessionId = data.active_session_id;
    state.sessions = Array.isArray(data.sessions) ? data.sessions : [];
    renderSessions();
  }

  async function renameSession() {
    if (!state.activeSessionId) return;

    const current = state.sessions.find((s) => s.id === state.activeSessionId);
    const nextTitle = window.prompt("Rename chat", current?.title || "New Chat");
    if (nextTitle === null) return;

    await fetchJson("/api/session/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.activeSessionId,
        title: nextTitle,
      }),
    });

    await refreshSessionsOnly();
    await loadSession(state.activeSessionId);
  }

  async function deleteSession() {
    if (!state.activeSessionId) return;
    const ok = window.confirm("Delete this session?");
    if (!ok) return;

    const data = await fetchJson("/api/session/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.activeSessionId,
      }),
    });

    state.activeSessionId = data.active_session_id;
    await refreshSessionsOnly();
    await loadSession(state.activeSessionId);
  }

  async function uploadSelectedFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || "Upload failed.");
    }

    return data.attachment;
  }

  async function sendMessage() {
    if (state.isSending) return;

    const content = messageInputEl.value.trim();
    const attachment = state.selectedAttachment;

    if (!content && !attachment) return;
    if (!state.activeSessionId) await createNewSession();

    setSending(true);

    try {
      const data = await fetchJson("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.activeSessionId,
          content,
          attachment,
        }),
      });

      if (data.user_message) renderMessage(data.user_message);
      if (data.assistant_message) renderMessage(data.assistant_message);

      messageInputEl.value = "";
      autoResizeTextarea();
      clearSelectedAttachment();

      await refreshSessionsOnly();
      activeSessionTitleEl.textContent = data.session_title || "New Chat";
      chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
    } catch (error) {
      window.alert(error.message || "Send failed.");
    } finally {
      setSending(false);
      messageInputEl.focus();
    }
  }

  attachBtnEl.addEventListener("click", () => {
    if (!state.isSending) fileInputEl.click();
  });

  fileInputEl.addEventListener("change", async (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    try {
      setSending(true);
      const attachment = await uploadSelectedFile(file);
      state.selectedAttachment = attachment;
      renderAttachmentPreview();
    } catch (error) {
      window.alert(error.message || "Upload failed.");
      clearSelectedAttachment();
    } finally {
      setSending(false);
    }
  });

  sendBtnEl.addEventListener("click", sendMessage);

  messageInputEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  messageInputEl.addEventListener("input", autoResizeTextarea);

  newSessionBtnEl.addEventListener("click", createNewSession);
  renameSessionBtnEl.addEventListener("click", renameSession);
  deleteSessionBtnEl.addEventListener("click", deleteSession);

  loadState().catch((error) => {
    console.error(error);
    window.alert(error.message || "Failed to load app state.");
  });

  autoResizeTextarea();
})();