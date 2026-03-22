(() => {
  "use strict";

  const API = {
    state: "/api/state",
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
    memory: "/api/memory",
    addMemory: "/api/memory/add",
    newSession: "/api/session/new",
    stream: "/api/chat/stream",
    upload: "/api/upload",
  };

  const app = {
    state: {
      sessions: [],
      messages: [],
      memoryItems: [],
      activeSessionId: null,
      currentModel: "gpt-4.1-mini",
      isSending: false,
      attachedFiles: [],
    },
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function safeText(value) {
    return String(value ?? "").trim();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function nowUnix() {
    return Math.floor(Date.now() / 1000);
  }

  function formatTime(ts) {
    if (!ts) return "";
    try {
      return new Date(Number(ts) * 1000).toLocaleString();
    } catch {
      return "";
    }
  }

  async function apiGet(url) {
    const res = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error(`GET failed: ${url}`);
    return res.json();
  }

  async function apiPost(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });

    if (!res.ok) {
      let msg = `POST failed: ${url}`;
      try {
        const data = await res.json();
        msg = data.detail || data.message || msg;
      } catch {}
      throw new Error(msg);
    }

    return res.json();
  }

  async function uploadFiles(files) {
    const list = Array.isArray(files) ? files : [];
    if (!list.length) return [];

    const formData = new FormData();
    for (const file of list) {
      formData.append("files", file);
    }

    const res = await fetch(API.upload, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      throw new Error("Upload failed");
    }

    const data = await res.json();
    return Array.isArray(data.files) ? data.files : [];
  }

  function setStatus(text) {
    const el = byId("mobileModelStatus");
    if (el) el.textContent = safeText(text || "Model ready");
  }

  function updateHeader() {
    const titleEl = byId("mobileChatTitle");
    const subtitleEl = byId("mobileChatSubtitle");
    const currentSession = app.state.sessions.find(
      (s) => s.session_id === app.state.activeSessionId
    );

    if (titleEl) titleEl.textContent = currentSession?.title || "Nova";

    if (subtitleEl) {
      subtitleEl.textContent = app.state.isSending
        ? "Thinking..."
        : `${app.state.messages.length || 0} messages`;
    }
  }

  function openScreen(screenId) {
    const el = byId(screenId);
    if (!el) return;
    el.classList.remove("hidden");
    el.setAttribute("aria-hidden", "false");
  }

  function closeScreen(screenId) {
    const el = byId(screenId);
    if (!el) return;
    el.classList.add("hidden");
    el.setAttribute("aria-hidden", "true");
  }

  function autosizeInput() {
    const input = byId("mobileMessageInput");
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
  }

  function renderAttachedFiles() {
    const bar = byId("mobileAttachedFiles");
    if (!bar) return;

    bar.innerHTML = "";
    if (!app.state.attachedFiles.length) {
      bar.classList.remove("has-files");
      return;
    }

    bar.classList.add("has-files");

    app.state.attachedFiles.forEach((file, index) => {
      const chip = document.createElement("div");
      chip.className = "mobile-file-chip";
      chip.innerHTML = `
        <span>${escapeHtml(file.name)} (${Math.max(1, Math.round(file.size / 1024))} KB)</span>
        <button type="button" data-file-index="${index}">✕</button>
      `;
      bar.appendChild(chip);
    });

    bar.querySelectorAll("[data-file-index]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const index = Number(btn.getAttribute("data-file-index"));
        app.state.attachedFiles.splice(index, 1);
        renderAttachedFiles();
      });
    });
  }

  function renderMessages() {
    const container = byId("mobileChatMessages");
    if (!container) return;

    if (!app.state.messages.length) {
      container.innerHTML = `
        <div class="mobile-empty-state">
          <div class="mobile-empty-card">
            <div class="mobile-empty-title">Nova Mobile is ready</div>
            <div class="mobile-empty-subtitle">Start a new message.</div>
          </div>
        </div>
      `;
      updateHeader();
      return;
    }

    container.innerHTML = app.state.messages.map((msg) => `
      <div class="mobile-message ${escapeHtml(msg.role || "assistant")}">
        <div class="mobile-message-role">${escapeHtml(msg.role || "assistant")}</div>
        <div>${escapeHtml(msg.content || "").replace(/\n/g, "<br>")}</div>
        <div class="mobile-message-time">${escapeHtml(formatTime(msg.timestamp || nowUnix()))}</div>
      </div>
    `).join("");

    container.scrollTop = container.scrollHeight;
    updateHeader();
  }

  function renderSessions() {
    const list = byId("mobileSessionList");
    if (!list) return;

    if (!app.state.sessions.length) {
      list.innerHTML = `<div class="mobile-card">No chats yet.</div>`;
      return;
    }

    list.innerHTML = app.state.sessions.map((session) => `
      <button class="mobile-session-item" data-session-id="${escapeHtml(session.session_id)}" type="button">
        <div class="mobile-session-title">${escapeHtml(session.title || "New Chat")}</div>
        <div class="mobile-session-meta">${escapeHtml(String(session.message_count || 0))} messages</div>
      </button>
    `).join("");

    list.querySelectorAll("[data-session-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const sessionId = btn.getAttribute("data-session-id");
        await loadSession(sessionId);
        closeScreen("mobileMenuScreen");
      });
    });
  }

  function renderMemory() {
    const list = byId("mobileMemoryList");
    const status = byId("mobileMemoryStatus");
    if (!list) return;

    if (status) {
      status.textContent = app.state.memoryItems.length
        ? `${app.state.memoryItems.length} memory item(s)`
        : "No saved memory yet.";
    }

    if (!app.state.memoryItems.length) {
      list.innerHTML = `<div class="mobile-card">No saved memory yet.</div>`;
      return;
    }

    list.innerHTML = app.state.memoryItems.map((item) => `
      <div class="mobile-memory-item">
        <div class="mobile-memory-kind">${escapeHtml(item.kind || "memory")}</div>
        <div class="mobile-memory-value">${escapeHtml(item.value || "")}</div>
        <div class="mobile-memory-meta">${escapeHtml(formatTime(item.updated_at || item.created_at || nowUnix()))}</div>
      </div>
    `).join("");
  }

  async function loadState() {
    const data = await apiGet(API.state);
    app.state.sessions = Array.isArray(data.sessions) ? data.sessions : [];

    if (!app.state.activeSessionId && app.state.sessions.length) {
      app.state.activeSessionId = app.state.sessions[0].session_id;
    }

    renderSessions();
    updateHeader();
  }

  async function loadSession(sessionId) {
    if (!sessionId) return;
    const data = await apiGet(API.getChat(sessionId));
    app.state.activeSessionId = data.session_id;
    app.state.messages = Array.isArray(data.messages) ? data.messages : [];
    renderMessages();
    renderSessions();
  }

  async function loadMemory() {
    const data = await apiGet(API.memory);
    app.state.memoryItems = Array.isArray(data.items) ? data.items : [];
    renderMemory();
  }

  async function createNewSession() {
    const data = await apiPost(API.newSession, {});
    await loadState();
    if (data.session_id) {
      await loadSession(data.session_id);
    }
  }

  async function addMemory(kind, value) {
    await apiPost(API.addMemory, { kind, value });
    await loadMemory();
  }

  async function sendMessage() {
    const input = byId("mobileMessageInput");
    if (!input || app.state.isSending) return;

    const content = safeText(input.value);
    const hasFiles = app.state.attachedFiles.length > 0;

    if (!content && !hasFiles) return;

    if (!app.state.activeSessionId) {
      await createNewSession();
    }

    app.state.isSending = true;
    setStatus("Responding...");
    updateHeader();

    try {
      let uploadedFiles = [];

      if (hasFiles) {
        setStatus("Uploading...");
        uploadedFiles = await uploadFiles(app.state.attachedFiles);
      }

      const model = app.state.currentModel || "gpt-4.1-mini";

      const res = await fetch(API.stream, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: app.state.activeSessionId,
          content,
          model,
          uploaded_files: uploadedFiles,
        }),
      });

      if (!res.ok) {
        throw new Error("Send failed");
      }

      input.value = "";
      app.state.attachedFiles = [];
      autosizeInput();
      renderAttachedFiles();

      await loadState();
      await loadSession(app.state.activeSessionId);
      await loadMemory();

      setStatus("Model ready");
    } catch (err) {
      console.error(err);
      setStatus("Send failed");
    } finally {
      app.state.isSending = false;
      updateHeader();
    }
  }

  function bindEvents() {
    byId("mobileMenuBtn")?.addEventListener("click", () => openScreen("mobileMenuScreen"));
    byId("closeMobileMenuBtn")?.addEventListener("click", () => closeScreen("mobileMenuScreen"));

    byId("mobileMemoryBtn")?.addEventListener("click", async () => {
      await loadMemory();
      openScreen("mobileMemoryScreen");
    });
    byId("closeMobileMemoryBtn")?.addEventListener("click", () => closeScreen("mobileMemoryScreen"));

    byId("mobileNewSessionBtn")?.addEventListener("click", async () => {
      await createNewSession();
      closeScreen("mobileMenuScreen");
    });

    byId("mobileRefreshSessionsBtn")?.addEventListener("click", loadState);
    byId("mobileRefreshMemoryBtn")?.addEventListener("click", loadMemory);

    byId("mobileAttachBtn")?.addEventListener("click", () => {
      byId("mobileFileInput")?.click();
    });

    byId("mobileFileInput")?.addEventListener("change", (event) => {
      const files = Array.from(event.target.files || []);
      app.state.attachedFiles = files;
      renderAttachedFiles();
    });

    byId("mobileSendBtn")?.addEventListener("click", sendMessage);

    byId("mobileMessageInput")?.addEventListener("input", autosizeInput);

    byId("mobileMessageInput")?.addEventListener("keydown", async (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        await sendMessage();
      }
    });

    byId("mobileMemoryForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const kind = safeText(byId("mobileMemoryKind")?.value || "memory");
      const value = safeText(byId("mobileMemoryValue")?.value || "");
      if (!value) return;
      await addMemory(kind, value);
      byId("mobileMemoryValue").value = "";
    });
  }

  async function bootstrap() {
    bindEvents();
    setStatus("Loading...");
    await loadState();

    if (app.state.activeSessionId) {
      await loadSession(app.state.activeSessionId);
    } else {
      renderMessages();
    }

    await loadMemory();
    renderAttachedFiles();
    autosizeInput();
    setStatus("Model ready");
  }

  document.addEventListener("DOMContentLoaded", () => {
    bootstrap().catch((err) => {
      console.error("Mobile bootstrap failed:", err);
      setStatus("Bootstrap failed");
    });
  });
})();