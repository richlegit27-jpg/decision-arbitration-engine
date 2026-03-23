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
      attachedFiles: [],
      isSending: false,
      isBootstrapping: false,
      streamController: null,
      streamAssistantIndex: -1,
      panelLocked: false,
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
      .replaceAll("'", "&#039;");
  }

  function setStatus(text) {
    const value = safeText(text) || "Ready";
    const el = byId("statusText");
    const composer = byId("composerStatus");
    if (el) el.textContent = value;
    if (composer) composer.textContent = value;
  }

  function setMemoryStatus(text) {
    const el = byId("memoryStatus");
    if (el) el.textContent = safeText(text) || "Ready";
  }

  function setActiveSessionMeta(text) {
    const el = byId("activeSessionMeta");
    if (el) el.textContent = safeText(text) || "Mobile assistant";
  }

  function autoResizeTextarea(el) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(Math.max(el.scrollHeight, 44), 160)}px`;
  }

  function getChatScrollEl() {
    return byId("chatScroll");
  }

  function scrollToBottom(force = false) {
    const el = getChatScrollEl();
    if (!el) return;

    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
    if (force || nearBottom) {
      el.scrollTop = el.scrollHeight;
    }
  }

  function scheduleScrollToBottom(force = false) {
    requestAnimationFrame(() => scrollToBottom(force));
  }

  function syncViewportHeight() {
    const vv = window.visualViewport;
    const height = vv ? vv.height : window.innerHeight;
    document.documentElement.style.setProperty("--vvh", `${height}px`);
  }

  function lockBodyScroll(lock) {
    document.documentElement.classList.toggle("mobile-lock-scroll", !!lock);
    document.body.classList.toggle("mobile-lock-scroll", !!lock);
  }

  function closePanels() {
    if (app.state.panelLocked) return;
    document.body.classList.remove("mobile-left-open", "mobile-right-open", "panel-open");
    const backdrop = byId("panelBackdrop");
    if (backdrop) backdrop.hidden = true;
    byId("mobileSidebar")?.setAttribute("aria-hidden", "true");
    byId("mobileMemoryPanel")?.setAttribute("aria-hidden", "true");
    lockBodyScroll(false);
  }

  function openLeftPanel() {
    document.body.classList.remove("mobile-right-open");
    document.body.classList.add("mobile-left-open", "panel-open");
    const backdrop = byId("panelBackdrop");
    if (backdrop) backdrop.hidden = false;
    byId("mobileSidebar")?.setAttribute("aria-hidden", "false");
    byId("mobileMemoryPanel")?.setAttribute("aria-hidden", "true");
    lockBodyScroll(true);
  }

  function openRightPanel() {
    document.body.classList.remove("mobile-left-open");
    document.body.classList.add("mobile-right-open", "panel-open");
    const backdrop = byId("panelBackdrop");
    if (backdrop) backdrop.hidden = false;
    byId("mobileSidebar")?.setAttribute("aria-hidden", "true");
    byId("mobileMemoryPanel")?.setAttribute("aria-hidden", "false");
    lockBodyScroll(true);
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

  function extractText(value) {
    if (value == null) return "";

    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);

    if (Array.isArray(value)) {
      return value.map((item) => extractText(item)).filter(Boolean).join("\n");
    }

    if (typeof value === "object") {
      if (typeof value.content === "string") return value.content;
      if (typeof value.text === "string") return value.text;
      if (typeof value.message === "string") return value.message;
      if (typeof value.response === "string") return value.response;
      if (typeof value.delta === "string") return value.delta;
      if (typeof value.output_text === "string") return value.output_text;

      if (Array.isArray(value.content)) {
        const parts = value.content
          .map((part) => {
            if (typeof part === "string") return part;
            if (part && typeof part === "object") {
              if (typeof part.text === "string") return part.text;
              if (typeof part.content === "string") return part.content;
              if (typeof part.value === "string") return part.value;
            }
            return "";
          })
          .filter(Boolean);
        if (parts.length) return parts.join("\n");
      }

      if (Array.isArray(value.parts)) {
        const parts = value.parts.map((part) => extractText(part)).filter(Boolean);
        if (parts.length) return parts.join("\n");
      }

      try {
        return JSON.stringify(value, null, 2);
      } catch (_) {
        return "";
      }
    }

    return String(value);
  }

  function normalizeMessage(message) {
    if (!message || typeof message !== "object") {
      return {
        role: "assistant",
        content: extractText(message),
      };
    }

    return {
      role: message.role === "user" ? "user" : "assistant",
      content: extractText(
        message.content ??
        message.text ??
        message.message ??
        message.response ??
        ""
      ),
      router_meta: message.router_meta || message.router || null,
      created_at: message.created_at || null,
      streaming: !!message.streaming,
    };
  }

  function updateLastUserMessage() {
    const last = [...app.state.messages]
      .reverse()
      .find((msg) => safeText(msg.role).toLowerCase() === "user" && safeText(msg.content));

    app.state.lastUserMessage = last ? safeText(last.content) : "";

    const btn = byId("regenerateBtn");
    if (btn) {
      btn.disabled = app.state.isSending || !app.state.lastUserMessage;
      btn.classList.toggle("is-disabled", btn.disabled);
    }
  }

  function setSendingState(flag) {
    app.state.isSending = !!flag;

    const sendBtn = byId("sendBtn");
    const regenBtn = byId("regenerateBtn");
    const attachBtn = byId("attachBtn");
    const newSessionBtn = byId("newSessionBtn");
    const input = byId("messageInput");

    if (sendBtn) {
      sendBtn.disabled = app.state.isSending;
      sendBtn.classList.toggle("is-loading", app.state.isSending);
    }

    if (regenBtn) {
      regenBtn.disabled = app.state.isSending || !app.state.lastUserMessage;
      regenBtn.classList.toggle("is-loading", app.state.isSending);
      regenBtn.classList.toggle("is-disabled", regenBtn.disabled);
    }

    if (attachBtn) attachBtn.disabled = app.state.isSending;
    if (newSessionBtn) newSessionBtn.disabled = app.state.isSending;
    if (input) input.disabled = app.state.isSending;
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

    for (const rawMessage of app.state.messages) {
      const message = normalizeMessage(rawMessage);
      const node = tpl.content.firstElementChild.cloneNode(true);
      const role = node.querySelector(".message-role");
      const content = node.querySelector(".message-content");

      node.classList.add(message.role === "user" ? "user" : "assistant");
      if (message.streaming) {
        node.classList.add("streaming");
      }

      if (role) role.textContent = message.role === "user" ? "You" : "Nova";

      if (content) {
        const text = extractText(message.content);
        const cursor = message.streaming ? `<span class="nova-stream-cursor" aria-hidden="true">▍</span>` : "";
        content.innerHTML = escapeHtml(text).replace(/\n/g, "<br>") + cursor;
      }

      root.appendChild(node);
    }

    updateLastUserMessage();
    scheduleScrollToBottom();
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
        if (!session.id) return;
        app.state.activeSessionId = session.id;
        await loadChat(session.id);
        closePanels();
      });

      pinBtn?.addEventListener("click", async (event) => {
        event.stopPropagation();
        await fetchJson(API.pinSession, {
          method: "POST",
          body: {
            session_id: session.id,
            pinned: !session.pinned,
          },
        });
        await bootstrap();
      });

      renameBtn?.addEventListener("click", async (event) => {
        event.stopPropagation();
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

      duplicateBtn?.addEventListener("click", async (event) => {
        event.stopPropagation();
        await fetchJson(API.duplicateSession, {
          method: "POST",
          body: { session_id: session.id },
        });
        await bootstrap();
        closePanels();
      });

      deleteBtn?.addEventListener("click", async (event) => {
        event.stopPropagation();
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

  function pushMessage(role, content = "", extras = {}) {
    app.state.messages.push({
      role: role === "user" ? "user" : "assistant",
      content: extractText(content),
      ...extras,
    });
    renderMessages();
    return app.state.messages.length - 1;
  }

  function updateMessageAt(index, content, extras = null) {
    if (index < 0 || index >= app.state.messages.length) return;
    app.state.messages[index].content = extractText(content);
    if (extras && typeof extras === "object") {
      Object.assign(app.state.messages[index], extras);
    }
    renderMessages();
  }

  function appendToMessageAt(index, chunk) {
    if (index < 0 || index >= app.state.messages.length) return;
    const current = extractText(app.state.messages[index].content || "");
    app.state.messages[index].content = current + extractText(chunk || "");
    renderMessages();
  }

  async function loadState() {
    const data = await fetchJson(API.state);
    app.state.sessions = Array.isArray(data.sessions) ? data.sessions : [];
    app.state.activeSessionId = data.active_session_id || data.current_session_id || app.state.activeSessionId || null;
    app.state.currentModel = data.current_model || app.state.currentModel || "gpt-4.1-mini";
    renderSessions();
  }

  async function loadChat(sessionId) {
    if (!sessionId) return;

    const data = await fetchJson(API.getChat(sessionId));
    app.state.activeSessionId = data.session_id || data.session?.id || sessionId;
    app.state.messages = Array.isArray(data.messages) ? data.messages.map(normalizeMessage) : [];
    renderMessages();

    const session = app.state.sessions.find((item) => item.id === app.state.activeSessionId);
    setActiveSessionMeta(session?.title || "Mobile assistant");
    scheduleScrollToBottom(true);
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

  async function ensureActiveSession() {
    if (app.state.activeSessionId) return app.state.activeSessionId;

    const data = await fetchJson(API.newSession, {
      method: "POST",
      body: { model: app.state.currentModel },
    });

    app.state.activeSessionId = data.active_session_id || data.session_id || null;
    await loadState();
    return app.state.activeSessionId;
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
        size: data.size || file.size || 0,
      });
    }

    app.state.attachedFiles = uploaded;
    renderAttachedFiles();
  }

  function parseSseEvents(rawChunk, state) {
    state.buffer += rawChunk;
    const events = [];

    while (true) {
      const boundary = state.buffer.indexOf("\n\n");
      if (boundary === -1) break;

      const block = state.buffer.slice(0, boundary);
      state.buffer = state.buffer.slice(boundary + 2);

      const lines = block.split(/\r?\n/);
      const dataLines = [];

      for (const line of lines) {
        if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trimStart());
        }
      }

      if (!dataLines.length) continue;
      events.push(dataLines.join("\n"));
    }

    return events;
  }

  function getDeltaText(payload) {
    if (!payload || typeof payload !== "object") return "";
    return extractText(
      payload.delta ??
      payload.content ??
      payload.text ??
      payload.token ??
      payload.message ??
      payload.response ??
      ""
    );
  }

  function abortActiveStream() {
    try {
      app.state.streamController?.abort();
    } catch (_) {}
    app.state.streamController = null;
    app.state.streamAssistantIndex = -1;
    app.state.isSending = false;
    setSendingState(false);
  }

  async function streamSend(messageText, options = {}) {
    const sessionId = await ensureActiveSession();

    const suppressLocalUser = !!options.suppressLocalUser;

    const response = await fetch(API.stream, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message: messageText,
        model: app.state.currentModel,
        files: app.state.attachedFiles,
      }),
      signal: app.state.streamController?.signal,
    });

    if (!response.ok) {
      let errorText = `Stream failed (${response.status})`;
      try {
        const data = await response.json();
        errorText = data?.error || errorText;
      } catch (_) {}
      throw new Error(errorText);
    }

    if (!response.body) {
      throw new Error("Streaming response body missing");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    const streamState = { buffer: "" };

    if (!suppressLocalUser) {
      pushMessage("user", messageText);
    }

    const assistantIndex = pushMessage("assistant", "", { streaming: true, router_meta: null });
    app.state.streamAssistantIndex = assistantIndex;

    let done = false;

    try {
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        if (readerDone) break;

        const chunk = decoder.decode(value, { stream: true });
        const events = parseSseEvents(chunk, streamState);

        for (const eventData of events) {
          if (!eventData) continue;
          if (eventData === "[DONE]") {
            done = true;
            break;
          }

          let payload;
          try {
            payload = JSON.parse(eventData);
          } catch (_) {
            continue;
          }

          const type = String(payload?.type || "").toLowerCase();

          if (type === "meta") {
            if (payload?.session_id) {
              app.state.activeSessionId = payload.session_id;
            }

            if (payload?.router_meta) {
              window.__novaLastRouterMeta = payload.router_meta;
              window.dispatchEvent(
                new CustomEvent("nova:router-meta", { detail: payload.router_meta })
              );
              app.state.messages[assistantIndex].router_meta = payload.router_meta;
            }

            continue;
          }

          if (type === "delta") {
            const delta = getDeltaText(payload);
            if (delta) {
              appendToMessageAt(assistantIndex, delta);
              setStatus("Streaming...");
            }
            continue;
          }

          if (type === "done") {
            const finalText = extractText(
              payload?.response ??
              payload?.content ??
              payload?.message ??
              app.state.messages[assistantIndex]?.content ??
              ""
            );

            updateMessageAt(assistantIndex, finalText, {
              streaming: false,
              router_meta: payload?.router_meta || app.state.messages[assistantIndex]?.router_meta || null,
            });

            if (payload?.router_meta) {
              window.__novaLastRouterMeta = payload.router_meta;
              window.dispatchEvent(
                new CustomEvent("nova:router-meta", { detail: payload.router_meta })
              );
            }

            done = true;
            break;
          }

          if (type === "error") {
            throw new Error(payload?.error || payload?.message || "Streaming error");
          }

          const fallbackText = getDeltaText(payload);
          if (fallbackText) {
            appendToMessageAt(assistantIndex, fallbackText);
            setStatus("Streaming...");
          }
        }
      }

      const tail = decoder.decode();
      if (tail) {
        const finalEvents = parseSseEvents(tail, streamState);
        for (const eventData of finalEvents) {
          if (eventData === "[DONE]") break;
          try {
            const payload = JSON.parse(eventData);
            if (String(payload?.type || "").toLowerCase() === "delta") {
              appendToMessageAt(assistantIndex, getDeltaText(payload));
            }
          } catch (_) {}
        }
      }

      if (!safeText(app.state.messages[assistantIndex]?.content)) {
        updateMessageAt(assistantIndex, "No response received.", { streaming: false });
      } else {
        updateMessageAt(
          assistantIndex,
          app.state.messages[assistantIndex]?.content || "",
          { streaming: false }
        );
      }
    } catch (error) {
      const current = extractText(app.state.messages[assistantIndex]?.content || "");
      if (!current.trim()) {
        updateMessageAt(assistantIndex, "Send failed.", { streaming: false });
      } else {
        updateMessageAt(assistantIndex, current, { streaming: false });
      }
      throw error;
    } finally {
      try {
        reader.releaseLock();
      } catch (_) {}
      app.state.streamAssistantIndex = -1;
    }
  }

  async function handleSend(event) {
    event?.preventDefault?.();
    if (app.state.isSending) return;

    const input = byId("messageInput");
    const text = safeText(input?.value);
    if (!text) return;

    setSendingState(true);
    app.state.streamController = new AbortController();

    if (input) {
      input.value = "";
      autoResizeTextarea(input);
      input.blur();
    }

    setStatus("Connecting...");
    scheduleScrollToBottom(true);

    try {
      await streamSend(text);

      app.state.attachedFiles = [];
      renderAttachedFiles();

      await loadState();

      if (app.state.activeSessionId) {
        const session = app.state.sessions.find((item) => item.id === app.state.activeSessionId);
        setActiveSessionMeta(session?.title || "Mobile assistant");
      }

      setStatus("Ready");
      scheduleScrollToBottom(true);
    } catch (error) {
      console.error(error);
      setStatus(error?.message ? `Send failed: ${error.message}` : "Send failed");
    } finally {
      app.state.streamController = null;
      setSendingState(false);
    }
  }

  async function regenerateLastReply() {
    if (app.state.isSending) return;
    if (!app.state.lastUserMessage) return;

    setSendingState(true);
    app.state.streamController = new AbortController();
    setStatus("Regenerating...");

    try {
      await streamSend(app.state.lastUserMessage, { suppressLocalUser: false });
      await loadState();
      if (app.state.activeSessionId) {
        const session = app.state.sessions.find((item) => item.id === app.state.activeSessionId);
        setActiveSessionMeta(session?.title || "Mobile assistant");
      }
      setStatus("Ready");
      scheduleScrollToBottom(true);
    } catch (error) {
      console.error(error);
      setStatus(error?.message ? `Regenerate failed: ${error.message}` : "Regenerate failed");
    } finally {
      app.state.streamController = null;
      setSendingState(false);
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
    byId("regenerateBtn")?.addEventListener("click", regenerateLastReply);

    byId("attachBtn")?.addEventListener("click", () => {
      byId("fileInput")?.click();
    });

    byId("fileInput")?.addEventListener("change", async (event) => {
      try {
        await uploadFiles(event.target.files);
        event.target.value = "";
        setStatus("Files attached");
      } catch (error) {
        console.error(error);
        setStatus("Upload failed");
      }
    });

    byId("messageInput")?.addEventListener("input", (event) => {
      autoResizeTextarea(event.currentTarget);
    });

    byId("messageInput")?.addEventListener("focus", () => {
      closePanels();
      syncViewportHeight();
      setTimeout(() => scheduleScrollToBottom(true), 80);
      setTimeout(() => scheduleScrollToBottom(true), 220);
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
        syncViewportHeight();
        autoResizeTextarea(byId("messageInput"));
        scheduleScrollToBottom(true);
      }, 100);
    });

    window.addEventListener("resize", () => {
      syncViewportHeight();
      autoResizeTextarea(byId("messageInput"));
    });

    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", () => {
        syncViewportHeight();
        scheduleScrollToBottom();
      });

      window.visualViewport.addEventListener("scroll", () => {
        syncViewportHeight();
      });
    }

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        syncViewportHeight();
        scheduleScrollToBottom();
      }
    });
  }

  async function bootstrap() {
    if (app.state.isBootstrapping) return;
    app.state.isBootstrapping = true;

    try {
      setStatus("Loading...");
      setMemoryStatus("Loading...");
      syncViewportHeight();

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
      renderAttachedFiles();
      setSendingState(false);
      setStatus("Ready");
      setMemoryStatus("Ready");
      scheduleScrollToBottom(true);
    } catch (error) {
      console.error(error);
      setStatus("Bootstrap failed");
      setMemoryStatus("Bootstrap failed");
      setSendingState(false);
    } finally {
      app.state.isBootstrapping = false;
    }
  }

  bindEvents();
  bootstrap();

  window.__novaMobileApp = {
    app,
    bootstrap,
    closePanels,
    openLeftPanel,
    openRightPanel,
    abortActiveStream,
    regenerateLastReply,
  };
})();