(() => {
  "use strict";

  if (window.__novaMobileLoaded) return;
  window.__novaMobileLoaded = true;

  const API = {
    state: "/api/state",
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
    memory: "/api/memory",
    addMemory: "/api/memory/add",
    newSession: "/api/session/new",
    stream: "/api/chat/stream",
    upload: "/api/upload",
  };

  const DEFAULT_MODEL = "gpt-4.1-mini";
  const MAX_INPUT_HEIGHT = 120;

  const app = {
    state: {
      sessions: [],
      messages: [],
      memoryItems: [],
      activeSessionId: null,
      currentModel: DEFAULT_MODEL,
      isSending: false,
      attachedFiles: [],
      lastUserMessage: "",
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

  function isHidden(el) {
    return !el || el.classList.contains("hidden");
  }

  function setStatus(text) {
    const el = byId("mobileModelStatus");
    if (el) el.textContent = safeText(text || "Model ready");
  }

  function setSendingState(isSending) {
    app.state.isSending = Boolean(isSending);

    const sendBtn = byId("mobileSendBtn");
    const input = byId("mobileMessageInput");
    const attachBtn = byId("mobileAttachBtn");
    const newSessionBtn = byId("mobileNewSessionBtn");
    const regenBtn = byId("mobileRegenerateBtn");

    if (sendBtn) {
      sendBtn.disabled = app.state.isSending;
      sendBtn.setAttribute("aria-busy", app.state.isSending ? "true" : "false");
    }

    if (input) {
      input.disabled = app.state.isSending;
    }

    if (attachBtn) {
      attachBtn.disabled = app.state.isSending;
    }

    if (newSessionBtn) {
      newSessionBtn.disabled = app.state.isSending;
    }

    if (regenBtn) {
      regenBtn.disabled = app.state.isSending || !app.state.lastUserMessage;
    }

    updateHeader();
  }

  function updateHeader() {
    const titleEl = byId("mobileChatTitle");
    const subtitleEl = byId("mobileChatSubtitle");

    const currentSession = app.state.sessions.find(
      (s) => s.session_id === app.state.activeSessionId
    );

    if (titleEl) {
      titleEl.textContent = currentSession?.title || "Nova";
    }

    if (subtitleEl) {
      if (app.state.isSending) {
        subtitleEl.textContent = "Thinking...";
      } else {
        subtitleEl.textContent = `${app.state.messages.length || 0} messages`;
      }
    }
  }

  function updateLastUserMessage() {
    const lastUser = [...app.state.messages]
      .reverse()
      .find((msg) => safeText(msg.role).toLowerCase() === "user" && safeText(msg.content));
    app.state.lastUserMessage = lastUser ? String(lastUser.content || "") : "";

    const regenBtn = byId("mobileRegenerateBtn");
    if (regenBtn) {
      regenBtn.disabled = app.state.isSending || !app.state.lastUserMessage;
    }
  }

  function openScreen(screenId) {
    const el = byId(screenId);
    if (!el) return;
    el.classList.remove("hidden");
    el.setAttribute("aria-hidden", "false");
    document.body.classList.add("mobile-screen-open");
  }

  function closeScreen(screenId) {
    const el = byId(screenId);
    if (!el) return;
    el.classList.add("hidden");
    el.setAttribute("aria-hidden", "true");

    const menuOpen = !isHidden(byId("mobileMenuScreen"));
    const memoryOpen = !isHidden(byId("mobileMemoryScreen"));

    if (!menuOpen && !memoryOpen) {
      document.body.classList.remove("mobile-screen-open");
    }
  }

  function closeAllScreens() {
    closeScreen("mobileMenuScreen");
    closeScreen("mobileMemoryScreen");
  }

  function autosizeInput() {
    const input = byId("mobileMessageInput");
    if (!input) return;

    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, MAX_INPUT_HEIGHT)}px`;
  }

  function scrollMessagesToBottom() {
    const container = byId("mobileChatMessages");
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }

  function clearFileInput() {
    const input = byId("mobileFileInput");
    if (input) input.value = "";
  }

  function normalizeUploadedFiles(files) {
    return Array.isArray(files)
      ? files.map((file) => ({
          name: safeText(file.name || file.filename || "file"),
          size: Number(file.size || 0),
          path: file.path || "",
          type: file.type || "",
        }))
      : [];
  }

  async function apiGet(url) {
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
    });

    if (!res.ok) {
      throw new Error(`GET failed: ${url}`);
    }

    return res.json();
  }

  async function apiPost(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
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
    return normalizeUploadedFiles(data.files);
  }

  async function copyTextToClipboard(text) {
    const value = String(text ?? "");
    if (!value) return false;

    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
        return true;
      }
    } catch {}

    try {
      const temp = document.createElement("textarea");
      temp.value = value;
      temp.setAttribute("readonly", "readonly");
      temp.style.position = "fixed";
      temp.style.left = "-9999px";
      document.body.appendChild(temp);
      temp.focus();
      temp.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(temp);
      return ok;
    } catch {
      return false;
    }
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
        <span>${escapeHtml(file.name)} (${Math.max(1, Math.round((Number(file.size) || 0) / 1024))} KB)</span>
        <button type="button" data-file-index="${index}" aria-label="Remove file">✕</button>
      `;
      bar.appendChild(chip);
    });

    bar.querySelectorAll("[data-file-index]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const index = Number(btn.getAttribute("data-file-index"));
        if (Number.isNaN(index)) return;
        app.state.attachedFiles.splice(index, 1);
        renderAttachedFiles();
        if (!app.state.attachedFiles.length) {
          clearFileInput();
        }
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
      updateLastUserMessage();
      updateHeader();
      return;
    }

    container.innerHTML = app.state.messages
      .map((msg, index) => {
        const role = safeText(msg.role || "assistant").toLowerCase();
        const contentRaw = String(msg.content ?? "");
        const content = escapeHtml(contentRaw).replace(/\n/g, "<br>");
        const time = formatTime(msg.timestamp || nowUnix());
        const isAssistant = role === "assistant";

        return `
          <div class="mobile-message ${escapeHtml(role)}">
            <div class="mobile-message-role">${escapeHtml(role)}</div>
            <div class="mobile-message-content">${content || "&nbsp;"}</div>
            <div class="mobile-message-footer">
              <div class="mobile-message-time">${escapeHtml(time)}</div>
              ${
                isAssistant
                  ? `
                <div class="mobile-message-actions">
                  <button
                    type="button"
                    class="mobile-message-action-btn"
                    data-copy-index="${index}"
                    aria-label="Copy message"
                  >
                    Copy
                  </button>
                </div>
              `
                  : ""
              }
            </div>
          </div>
        `;
      })
      .join("");

    container.querySelectorAll("[data-copy-index]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const index = Number(btn.getAttribute("data-copy-index"));
        if (Number.isNaN(index)) return;

        const msg = app.state.messages[index];
        if (!msg) return;

        const ok = await copyTextToClipboard(msg.content || "");
        const original = btn.textContent;
        btn.textContent = ok ? "Copied" : "Failed";

        setTimeout(() => {
          btn.textContent = original || "Copy";
        }, 1200);
      });
    });

    updateLastUserMessage();
    scrollMessagesToBottom();
    updateHeader();
  }

  function renderSessions() {
    const list = byId("mobileSessionList");
    if (!list) return;

    if (!app.state.sessions.length) {
      list.innerHTML = `<div class="mobile-card">No chats yet.</div>`;
      return;
    }

    list.innerHTML = app.state.sessions
      .map((session) => {
        const isActive = session.session_id === app.state.activeSessionId;
        return `
          <button
            class="mobile-session-item ${isActive ? "active" : ""}"
            data-session-id="${escapeHtml(session.session_id)}"
            type="button"
          >
            <div class="mobile-session-title">${escapeHtml(session.title || "New Chat")}</div>
            <div class="mobile-session-meta">${escapeHtml(String(session.message_count || 0))} messages</div>
          </button>
        `;
      })
      .join("");

    list.querySelectorAll("[data-session-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const sessionId = btn.getAttribute("data-session-id");
        if (!sessionId || sessionId === app.state.activeSessionId) {
          closeScreen("mobileMenuScreen");
          return;
        }

        try {
          setStatus("Loading chat...");
          await loadSession(sessionId);
          closeScreen("mobileMenuScreen");
          setStatus("Model ready");
        } catch (err) {
          console.error(err);
          setStatus("Load failed");
        }
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

    list.innerHTML = app.state.memoryItems
      .map((item) => `
        <div class="mobile-memory-item">
          <div class="mobile-memory-kind">${escapeHtml(item.kind || "memory")}</div>
          <div class="mobile-memory-value">${escapeHtml(item.value || "")}</div>
          <div class="mobile-memory-meta">${escapeHtml(
            formatTime(item.updated_at || item.created_at || nowUnix())
          )}</div>
        </div>
      `)
      .join("");
  }

  function addLocalMessage(role, content) {
    app.state.messages.push({
      role: safeText(role || "assistant"),
      content: String(content ?? ""),
      timestamp: nowUnix(),
    });
    renderMessages();
  }

  async function loadState() {
    const data = await apiGet(API.state);
    const sessions = Array.isArray(data.sessions) ? data.sessions : [];

    app.state.sessions = sessions;

    if (app.state.activeSessionId) {
      const exists = sessions.some((s) => s.session_id === app.state.activeSessionId);
      if (!exists) {
        app.state.activeSessionId = sessions[0]?.session_id || null;
      }
    } else if (sessions.length) {
      app.state.activeSessionId = sessions[0].session_id;
    }

    renderSessions();
    updateHeader();
  }

  async function loadSession(sessionId) {
    if (!sessionId) return;

    const data = await apiGet(API.getChat(sessionId));
    app.state.activeSessionId = data.session_id || sessionId;
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
    } else {
      app.state.messages = [];
      renderMessages();
    }
  }

  async function addMemory(kind, value) {
    await apiPost(API.addMemory, { kind, value });
    await loadMemory();
  }

  async function streamSend(content, attachedFilesOverride = null) {
    const input = byId("mobileMessageInput");
    const hasFiles = Array.isArray(attachedFilesOverride)
      ? attachedFilesOverride.length > 0
      : app.state.attachedFiles.length > 0;

    const normalizedContent = safeText(content);

    if (!normalizedContent && !hasFiles) return;

    if (!app.state.activeSessionId) {
      await createNewSession();
    }

    setSendingState(true);
    setStatus("Responding...");

    const pendingContent = normalizedContent;
    const pendingFiles = Array.isArray(attachedFilesOverride)
      ? [...attachedFilesOverride]
      : [...app.state.attachedFiles];

    try {
      if (pendingContent) {
        addLocalMessage("user", pendingContent);
      } else if (pendingFiles.length) {
        addLocalMessage("user", `[Uploaded ${pendingFiles.length} file(s)]`);
      }

      if (input && attachedFilesOverride === null) {
        input.value = "";
        autosizeInput();
      }

      let uploadedFiles = [];
      if (pendingFiles.length) {
        setStatus("Uploading...");
        uploadedFiles = await uploadFiles(pendingFiles);
      }

      const model = safeText(app.state.currentModel) || DEFAULT_MODEL;

      const res = await fetch(API.stream, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/plain, */*",
        },
        body: JSON.stringify({
          session_id: app.state.activeSessionId,
          content: pendingContent,
          model,
          uploaded_files: uploadedFiles,
        }),
      });

      if (!res.ok) {
        throw new Error("Send failed");
      }

      if (res.body && typeof res.body.getReader === "function") {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          decoder.decode(value, { stream: true });
        }
      } else {
        try {
          await res.text();
        } catch {}
      }

      if (attachedFilesOverride === null) {
        app.state.attachedFiles = [];
        renderAttachedFiles();
        clearFileInput();
      }

      await loadState();
      await loadSession(app.state.activeSessionId);
      await loadMemory();

      setStatus("Model ready");
    } catch (err) {
      console.error(err);
      addLocalMessage("assistant", "Something went wrong sending that message.");
      setStatus("Send failed");
    } finally {
      setSendingState(false);
      renderMessages();
    }
  }

  async function sendMessage() {
    const input = byId("mobileMessageInput");
    if (!input || app.state.isSending) return;
    await streamSend(input.value, null);
  }

  async function regenerateLastReply() {
    if (app.state.isSending) return;

    const content = safeText(app.state.lastUserMessage);
    if (!content) {
      setStatus("Nothing to regenerate");
      return;
    }

    await streamSend(content, []);
  }

  function bindScreenDismiss(screenId) {
    const screen = byId(screenId);
    if (!screen) return;

    screen.addEventListener("click", (event) => {
      if (event.target === screen) {
        closeScreen(screenId);
      }
    });
  }

  function ensureRegenerateButton() {
    const inputBar =
      byId("mobileInputBar") ||
      byId("mobileComposerBar") ||
      document.querySelector(".mobile-input-bar");

    if (!inputBar || byId("mobileRegenerateBtn")) return;

    const sendBtn = byId("mobileSendBtn");
    const regenBtn = document.createElement("button");

    regenBtn.type = "button";
    regenBtn.id = "mobileRegenerateBtn";
    regenBtn.className = "mobile-btn icon mobile-regenerate-btn";
    regenBtn.textContent = "↻";

    if (sendBtn && sendBtn.parentNode === inputBar) {
      inputBar.insertBefore(regenBtn, sendBtn);
    } else {
      inputBar.appendChild(regenBtn);
    }
  }

  function bindEvents() {
    ensureRegenerateButton();

    byId("mobileMenuBtn")?.addEventListener("click", () => openScreen("mobileMenuScreen"));
    byId("closeMobileMenuBtn")?.addEventListener("click", () => closeScreen("mobileMenuScreen"));

    byId("mobileMemoryBtn")?.addEventListener("click", async () => {
      try {
        setStatus("Loading memory...");
        await loadMemory();
        openScreen("mobileMemoryScreen");
        setStatus("Model ready");
      } catch (err) {
        console.error(err);
        setStatus("Memory failed");
      }
    });

    byId("closeMobileMemoryBtn")?.addEventListener("click", () => closeScreen("mobileMemoryScreen"));

    byId("mobileNewSessionBtn")?.addEventListener("click", async () => {
      try {
        setStatus("Creating chat...");
        await createNewSession();
        closeScreen("mobileMenuScreen");
        setStatus("Model ready");
      } catch (err) {
        console.error(err);
        setStatus("Create failed");
      }
    });

    byId("mobileRefreshSessionsBtn")?.addEventListener("click", async () => {
      try {
        setStatus("Refreshing chats...");
        await loadState();
        setStatus("Model ready");
      } catch (err) {
        console.error(err);
        setStatus("Refresh failed");
      }
    });

    byId("mobileRefreshMemoryBtn")?.addEventListener("click", async () => {
      try {
        setStatus("Refreshing memory...");
        await loadMemory();
        setStatus("Model ready");
      } catch (err) {
        console.error(err);
        setStatus("Refresh failed");
      }
    });

    byId("mobileAttachBtn")?.addEventListener("click", () => {
      if (app.state.isSending) return;
      byId("mobileFileInput")?.click();
    });

    byId("mobileFileInput")?.addEventListener("change", (event) => {
      const files = Array.from(event.target.files || []);
      if (!files.length) return;

      const existing = new Map(
        app.state.attachedFiles.map((file) => [`${file.name}__${file.size}`, file])
      );

      for (const file of files) {
        existing.set(`${file.name}__${file.size}`, file);
      }

      app.state.attachedFiles = Array.from(existing.values());
      renderAttachedFiles();
      clearFileInput();
    });

    byId("mobileSendBtn")?.addEventListener("click", sendMessage);
    byId("mobileRegenerateBtn")?.addEventListener("click", regenerateLastReply);

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
      const valueEl = byId("mobileMemoryValue");
      const value = safeText(valueEl?.value || "");

      if (!value) return;

      try {
        setStatus("Saving memory...");
        await addMemory(kind, value);
        if (valueEl) valueEl.value = "";
        setStatus("Model ready");
      } catch (err) {
        console.error(err);
        setStatus("Save failed");
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeAllScreens();
      }
    });

    bindScreenDismiss("mobileMenuScreen");
    bindScreenDismiss("mobileMemoryScreen");
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
    setSendingState(false);
    setStatus("Model ready");
  }

  document.addEventListener("DOMContentLoaded", () => {
    bootstrap().catch((err) => {
      console.error("Mobile bootstrap failed:", err);
      setStatus("Bootstrap failed");
      setSendingState(false);
    });
  });
})();