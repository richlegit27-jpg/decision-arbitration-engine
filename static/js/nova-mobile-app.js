(() => {
  "use strict";

  if (window.__novaMobileAppLoaded) return;
  window.__novaMobileAppLoaded = true;

  const API = {
    state: "/api/state",
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
    memory: "/api/memory",
    memoryDelete: "/api/memory/delete",
    newSession: "/api/session/new",
    deleteSession: "/api/session/delete",
    renameSession: "/api/session/rename",
    duplicateSession: "/api/session/duplicate",
    pinSession: "/api/session/pin",
    send: "/api/chat/send",
    upload: "/api/upload",
  };

  const app = {
    state: {
      sessions: [],
      messages: [],
      memoryItems: [],
      activeSessionId: null,
      currentModel: "gpt-4.1-mini",
      attachedFiles: [],
      isSending: false,
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
      .replaceAll("'", "&#039;");
  }

  function setStatus(text) {
    const el = byId("statusText");
    const composer = byId("composerStatus");
    if (el) el.textContent = text;
    if (composer) composer.textContent = text;
  }

  function setMemoryStatus(text) {
    const el = byId("memoryStatus");
    if (el) el.textContent = text;
  }

  function setActiveSessionMeta(text) {
    const el = byId("activeSessionMeta");
    if (el) el.textContent = text;
  }

  function autoResizeTextarea(el) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  function scrollToBottom() {
    const el = byId("chatScroll");
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }

  function closePanels() {
    document.body.classList.remove("mobile-left-open", "mobile-right-open", "panel-open");
    const backdrop = byId("panelBackdrop");
    if (backdrop) backdrop.hidden = true;
    byId("mobileSidebar")?.setAttribute("aria-hidden", "true");
    byId("mobileMemoryPanel")?.setAttribute("aria-hidden", "true");
  }

  function openLeftPanel() {
    document.body.classList.remove("mobile-right-open");
    document.body.classList.add("mobile-left-open", "panel-open");
    const backdrop = byId("panelBackdrop");
    if (backdrop) backdrop.hidden = false;
    byId("mobileSidebar")?.setAttribute("aria-hidden", "false");
    byId("mobileMemoryPanel")?.setAttribute("aria-hidden", "true");
  }

  function openRightPanel() {
    document.body.classList.remove("mobile-left-open");
    document.body.classList.add("mobile-right-open", "panel-open");
    const backdrop = byId("panelBackdrop");
    if (backdrop) backdrop.hidden = false;
    byId("mobileSidebar")?.setAttribute("aria-hidden", "true");
    byId("mobileMemoryPanel")?.setAttribute("aria-hidden", "false");
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, {
      method: options.method || "GET",
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data?.error || "Request failed");
    }

    return data;
  }

  function renderAttachedFiles() {
    const bar = byId("attachedFilesBar");
    if (!bar) return;

    if (!app.state.attachedFiles.length) {
      bar.hidden = true;
      bar.textContent = "";
      return;
    }

    bar.hidden = false;
    bar.textContent = `Attached: ${app.state.attachedFiles.map((f) => f.name).join(", ")}`;
  }

  function renderMessages() {
    const root = byId("messageList");
    const tpl = byId("messageItemTemplate");
    const welcome = byId("welcomeState");
    if (!root || !tpl) return;

    root.innerHTML = "";
    if (welcome) welcome.hidden = app.state.messages.length > 0;

    for (const message of app.state.messages) {
      const node = tpl.content.firstElementChild.cloneNode(true);
      const role = node.querySelector(".message-role");
      const content = node.querySelector(".message-content");

      node.classList.add(message.role === "user" ? "user" : "assistant");
      if (role) role.textContent = message.role === "user" ? "You" : "Nova";
      if (content) content.innerHTML = escapeHtml(message.content || "").replace(/\n/g, "<br>");

      root.appendChild(node);
    }

    requestAnimationFrame(scrollToBottom);
  }

  function renderSessions() {
    const root = byId("sessionList");
    const tpl = byId("sessionItemTemplate");
    if (!root || !tpl) return;

    root.innerHTML = "";

    const sessions = [...app.state.sessions].sort((a, b) => {
      if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;
      return String(b.updated_at || "").localeCompare(String(a.updated_at || ""));
    });

    for (const session of sessions) {
      const node = tpl.content.firstElementChild.cloneNode(true);

      const main = node.querySelector(".session-main");
      const title = node.querySelector(".session-title");
      const meta = node.querySelector(".session-meta");
      const pinBtn = node.querySelector(".session-pin");
      const renameBtn = node.querySelector(".session-rename");
      const duplicateBtn = node.querySelector(".session-duplicate");
      const deleteBtn = node.querySelector(".session-delete");

      if (title) title.textContent = safeText(session.title) || "New Chat";
      if (meta) meta.textContent = `${session.pinned ? "Pinned · " : ""}${session.message_count || 0} msgs`;

      main?.addEventListener("click", async () => {
        app.state.activeSessionId = session.id;
        await loadChat(session.id);
        closePanels();
      });

      pinBtn?.addEventListener("click", async () => {
        await fetchJson(API.pinSession, {
          method: "POST",
          body: {
            session_id: session.id,
            pinned: !session.pinned,
          },
        });
        await bootstrap();
      });

      renameBtn?.addEventListener("click", async () => {
        const nextTitle = window.prompt("Rename session", session.title || "New Chat");
        if (!safeText(nextTitle)) return;

        await fetchJson(API.renameSession, {
          method: "POST",
          body: {
            session_id: session.id,
            title: nextTitle,
          },
        });

        await bootstrap();
      });

      duplicateBtn?.addEventListener("click", async () => {
        await fetchJson(API.duplicateSession, {
          method: "POST",
          body: { session_id: session.id },
        });
        await bootstrap();
        closePanels();
      });

      deleteBtn?.addEventListener("click", async () => {
        const ok = window.confirm(`Delete "${session.title || "New Chat"}"?`);
        if (!ok) return;

        await fetchJson(API.deleteSession, {
          method: "POST",
          body: { session_id: session.id },
        });

        await bootstrap();
      });

      root.appendChild(node);
    }
  }

  function renderMemory() {
    const root = byId("memoryList");
    const tpl = byId("memoryItemTemplate");
    if (!root || !tpl) return;

    root.innerHTML = "";

    for (const item of app.state.memoryItems) {
      const node = tpl.content.firstElementChild.cloneNode(true);
      const kind = node.querySelector(".memory-kind");
      const value = node.querySelector(".memory-value");
      const deleteBtn = node.querySelector(".memory-delete-btn");

      if (kind) kind.textContent = safeText(item.kind) || "memory";
      if (value) value.textContent = safeText(item.value);

      deleteBtn?.addEventListener("click", async () => {
        await fetchJson(API.memoryDelete, {
          method: "POST",
          body: { id: item.id },
        });
        await loadMemory();
      });

      root.appendChild(node);
    }
  }

  async function loadState() {
    const data = await fetchJson(API.state);
    app.state.sessions = Array.isArray(data.sessions) ? data.sessions : [];
    app.state.activeSessionId = data.active_session_id || null;
    app.state.currentModel = data.current_model || "gpt-4.1-mini";
    renderSessions();
  }

  async function loadChat(sessionId) {
    if (!sessionId) return;

    const data = await fetchJson(API.getChat(sessionId));
    app.state.activeSessionId = data.session_id || sessionId;
    app.state.messages = Array.isArray(data.messages) ? data.messages : [];
    renderMessages();

    const session = app.state.sessions.find((item) => item.id === app.state.activeSessionId);
    setActiveSessionMeta(session?.title || "Mobile assistant");
  }

  async function loadMemory() {
    const data = await fetchJson(API.memory);
    app.state.memoryItems = Array.isArray(data.memory) ? data.memory : [];
    renderMemory();
  }

  async function createSession() {
    const data = await fetchJson(API.newSession, {
      method: "POST",
      body: { model: app.state.currentModel },
    });

    app.state.activeSessionId = data.active_session_id || data.session_id || null;
    await bootstrap();
    closePanels();
  }

  async function uploadFiles(fileList) {
    const uploaded = [];

    for (const file of Array.from(fileList || [])) {
      const form = new FormData();
      form.append("file", file);

      const response = await fetch(API.upload, {
        method: "POST",
        body: form,
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.error || `Upload failed for ${file.name}`);
      }

      uploaded.push({
        id: data.id,
        name: data.name,
      });
    }

    app.state.attachedFiles = uploaded;
    renderAttachedFiles();
  }

  async function handleSend(event) {
    event?.preventDefault?.();
    if (app.state.isSending) return;

    const input = byId("messageInput");
    const text = safeText(input?.value);
    if (!text) return;

    app.state.isSending = true;
    setStatus("Sending...");

    try {
      await fetchJson(API.send, {
        method: "POST",
        body: {
          session_id: app.state.activeSessionId,
          message: text,
          model: app.state.currentModel,
          files: app.state.attachedFiles,
        },
      });

      if (input) {
        input.value = "";
        autoResizeTextarea(input);
      }

      app.state.attachedFiles = [];
      renderAttachedFiles();

      await loadState();
      if (app.state.activeSessionId) {
        await loadChat(app.state.activeSessionId);
      }

      setStatus("Ready");
    } catch (error) {
      console.error(error);
      setStatus("Send failed");
    } finally {
      app.state.isSending = false;
    }
  }

  async function handleSaveMemory(event) {
    event?.preventDefault?.();

    const kind = safeText(byId("memoryKind")?.value || "memory");
    const valueEl = byId("memoryValue");
    const value = safeText(valueEl?.value || "");

    if (!value) {
      setMemoryStatus("Enter a memory value first.");
      return;
    }

    try {
      setMemoryStatus("Saving...");
      await fetchJson(API.memory, {
        method: "POST",
        body: { kind, value },
      });

      if (valueEl) valueEl.value = "";
      setMemoryStatus("Saved");
      await loadMemory();
    } catch (error) {
      console.error(error);
      setMemoryStatus("Save failed");
    }
  }

  function bindEvents() {
    byId("openLeftPanelBtn")?.addEventListener("click", openLeftPanel);
    byId("openRightPanelBtn")?.addEventListener("click", openRightPanel);
    byId("closeLeftPanelBtn")?.addEventListener("click", closePanels);
    byId("closeRightPanelBtn")?.addEventListener("click", closePanels);
    byId("panelBackdrop")?.addEventListener("click", closePanels);

    byId("newSessionBtn")?.addEventListener("click", createSession);
    byId("refreshMemoryBtn")?.addEventListener("click", loadMemory);
    byId("composerForm")?.addEventListener("submit", handleSend);
    byId("memoryForm")?.addEventListener("submit", handleSaveMemory);

    byId("attachBtn")?.addEventListener("click", () => {
      byId("fileInput")?.click();
    });

    byId("fileInput")?.addEventListener("change", async (event) => {
      try {
        await uploadFiles(event.target.files);
        event.target.value = "";
      } catch (error) {
        console.error(error);
        setStatus("Upload failed");
      }
    });

    byId("messageInput")?.addEventListener("input", (event) => {
      autoResizeTextarea(event.currentTarget);
    });

    byId("messageInput")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSend(event);
      }
    });

    window.addEventListener("orientationchange", () => {
      setTimeout(() => {
        closePanels();
        autoResizeTextarea(byId("messageInput"));
        scrollToBottom();
      }, 80);
    });

    window.addEventListener("resize", () => {
      autoResizeTextarea(byId("messageInput"));
    });
  }

  async function bootstrap() {
    try {
      setStatus("Loading...");
      setMemoryStatus("Loading...");

      await loadState();

      if (app.state.activeSessionId) {
        await loadChat(app.state.activeSessionId);
      } else {
        app.state.messages = [];
        renderMessages();
        setActiveSessionMeta("Mobile assistant");
      }

      await loadMemory();

      autoResizeTextarea(byId("messageInput"));
      setStatus("Ready");
      setMemoryStatus("Ready");
    } catch (error) {
      console.error(error);
      setStatus("Bootstrap failed");
      setMemoryStatus("Bootstrap failed");
    }
  }

  bindEvents();
  bootstrap();
})();