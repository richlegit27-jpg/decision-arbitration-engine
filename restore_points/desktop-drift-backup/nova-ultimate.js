(() => {
  "use strict";

  if (window.__novaUltimateLoaded) return;
  window.__novaUltimateLoaded = true;

  if (!window.NovaCore) {
    console.error("NovaCore is required before nova-ultimate.js");
    return;
  }

  const {
    state,
    byId,
    safeText,
    escapeHtml,
    loadState,
    loadChat,
    loadMemory,
    createSession,
    renameSession,
    duplicateSession,
    deleteSession,
    pinSession,
    saveMemory,
    deleteMemory,
    sendMessage,
  } = window.NovaCore;

  function setStatus(text) {
    const el = byId("statusBar");
    if (el) el.textContent = text;
  }

  function setMemoryStatus(text) {
    const el = byId("memoryStatus");
    if (el) el.textContent = text;
  }

  function renderSessions() {
    const mount = byId("sessionList");
    if (!mount) return;

    const sessions = Array.isArray(state.sessions) ? [...state.sessions] : [];

    sessions.sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return Number(b.updated_at || b.created_at || 0) - Number(a.updated_at || a.created_at || 0);
    });

    if (!sessions.length) {
      mount.innerHTML = `
        <div class="session-empty">
          <div class="session-empty-title">No chats yet</div>
          <div class="session-empty-copy">Press New to start.</div>
        </div>
      `;
      return;
    }

    mount.innerHTML = sessions.map((session) => {
      const id = escapeHtml(session.id || "");
      const title = escapeHtml(session.title || "Untitled Chat");
      const active = session.id === state.activeSessionId ? "active" : "";
      const pinLabel = session.pinned ? "Unpin" : "Pin";

      return `
        <div class="session-card ${active}" data-session-id="${id}">
          <button class="session-main" type="button" data-action="open" data-session-id="${id}">
            <div class="session-title">${title}</div>
          </button>
          <div class="session-actions">
            <button class="mini-btn" type="button" data-action="pin" data-session-id="${id}">${pinLabel}</button>
            <button class="mini-btn" type="button" data-action="rename" data-session-id="${id}">Rename</button>
            <button class="mini-btn" type="button" data-action="duplicate" data-session-id="${id}">Duplicate</button>
            <button class="mini-btn danger" type="button" data-action="delete" data-session-id="${id}">Delete</button>
          </div>
        </div>
      `;
    }).join("");
  }

  function renderMessages() {
    const mount = byId("chatMessages");
    if (!mount) return;

    const messages = Array.isArray(state.messages) ? state.messages : [];

    if (!messages.length) {
      mount.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-title">Nova is ready.</div>
          <div class="empty-state-copy">Start a new chat or send a message.</div>
        </div>
      `;
      return;
    }

    mount.innerHTML = messages.map((message) => {
      const role = safeText(message.role || "assistant").toLowerCase();
      const cls = role === "user" ? "user" : "assistant";
      const content = escapeHtml(message.content || "").replace(/\n/g, "<br>");

      return `
        <div class="message-row ${cls}">
          <div class="message-bubble">${content}</div>
        </div>
      `;
    }).join("");

    mount.scrollTop = mount.scrollHeight;
  }

  function renderMemory() {
    const mount = byId("memoryList");
    if (!mount) return;

    const items = Array.isArray(state.memoryItems) ? state.memoryItems : [];

    if (!items.length) {
      mount.innerHTML = `<div class="memory-empty">No memory saved yet.</div>`;
      return;
    }

    mount.innerHTML = items.map((item) => `
      <div class="memory-card" data-memory-id="${escapeHtml(item.id || "")}">
        <div class="memory-card-top">
          <span class="memory-kind">${escapeHtml(item.kind || "memory")}</span>
          <button class="mini-btn danger" type="button" data-memory-delete="${escapeHtml(item.id || "")}">Delete</button>
        </div>
        <div class="memory-value">${escapeHtml(item.value || "")}</div>
      </div>
    `).join("");
  }

  function renderRouteMeta() {
    const meta = state.routeMeta || {};

    const routeEl = byId("routerRouteValue");
    const reasonEl = byId("routerReasonValue");
    const memoryEl = byId("routerMemoryValue");
    const modelEl = byId("routerModelValue");
    const modelSelect = byId("modelSelect");

    if (routeEl) routeEl.textContent = meta.route || meta.intent || "—";
    if (reasonEl) reasonEl.textContent = meta.reason || "—";
    if (memoryEl) memoryEl.textContent = meta.memory_scope || meta.memory || "—";
    if (modelEl) modelEl.textContent = meta.model || state.currentModel || "—";
    if (modelSelect) modelSelect.value = state.currentModel || "gpt-4.1-mini";
  }

  function autoGrowTextarea() {
    const input = byId("messageInput");
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 220)}px`;
  }

  function isDesktop() {
    return window.innerWidth > 1280;
  }

  function ensureDesktopPanels() {
    if (!isDesktop()) return;
    document.body.classList.add("left-open", "right-open");
  }

  function closeMobilePanels() {
    if (isDesktop()) return;
    document.body.classList.remove("left-open", "right-open");
  }

  function toggleSidebar(side) {
    const cls = side === "left" ? "left-open" : "right-open";

    if (isDesktop()) {
      document.body.classList.add("left-open", "right-open");
      return;
    }

    if (side === "left") {
      document.body.classList.remove("right-open");
      document.body.classList.toggle("left-open");
      return;
    }

    document.body.classList.remove("left-open");
    document.body.classList.toggle("right-open");
  }

  async function refreshAll() {
    setStatus("Loading...");

    await loadState();
    renderSessions();

    if (state.activeSessionId) {
      await loadChat(state.activeSessionId);
    } else {
      state.messages = [];
    }

    renderMessages();

    await loadMemory();
    renderMemory();

    renderRouteMeta();
    ensureDesktopPanels();

    setStatus("Ready");
    setMemoryStatus("Ready");
  }

  async function handleNewChat() {
    try {
      setStatus("Creating chat...");
      await createSession();
      await loadState();

      if (state.activeSessionId) {
        await loadChat(state.activeSessionId);
      } else {
        state.messages = [];
      }

      renderSessions();
      renderMessages();
      renderRouteMeta();
      ensureDesktopPanels();
      setStatus("Ready");
      closeMobilePanels();
    } catch (err) {
      console.error(err);
      setStatus("New chat failed");
    }
  }

  async function handleSessionAction(button) {
    const sessionId = safeText(button?.dataset?.sessionId || button?.closest("[data-session-id]")?.dataset?.sessionId || "");
    const action = safeText(button?.dataset?.action || "");

    if (!sessionId || !action) return;

    try {
      if (action === "open") {
        setStatus("Loading chat...");
        state.activeSessionId = sessionId;
        await loadChat(sessionId);
        renderMessages();
        renderSessions();
        renderRouteMeta();
        setStatus("Ready");
        closeMobilePanels();
        return;
      }

      if (action === "pin") {
        setStatus("Updating pin...");
        await pinSession(sessionId);
        await loadState();
      } else if (action === "rename") {
        const current = (state.sessions || []).find((s) => s.id === sessionId);
        const nextTitle = window.prompt("Rename chat", current?.title || "Untitled Chat");
        if (!safeText(nextTitle)) {
          setStatus("Ready");
          return;
        }
        setStatus("Renaming...");
        await renameSession(sessionId, safeText(nextTitle));
        await loadState();
      } else if (action === "duplicate") {
        setStatus("Duplicating...");
        await duplicateSession(sessionId);
        await loadState();
      } else if (action === "delete") {
        const ok = window.confirm("Delete this chat?");
        if (!ok) {
          setStatus("Ready");
          return;
        }
        setStatus("Deleting...");
        await deleteSession(sessionId);
        await loadState();
      }

      if (state.activeSessionId) {
        await loadChat(state.activeSessionId);
      } else {
        state.messages = [];
      }

      renderSessions();
      renderMessages();
      renderRouteMeta();
      ensureDesktopPanels();
      setStatus("Ready");
    } catch (err) {
      console.error(err);
      setStatus(`${action} failed`);
    }
  }

  async function handleSend(event) {
    event.preventDefault();

    const input = byId("messageInput");
    if (!input) return;

    const outgoing = safeText(input.value);
    if (!outgoing || state.sending) return;

    try {
      if (!state.activeSessionId) {
        setStatus("Creating chat...");
        await createSession();
        await loadState();
      }

      const userMessage = {
        id: `local-user-${Date.now()}`,
        role: "user",
        content: outgoing,
      };

      const assistantMessage = {
        id: `local-assistant-${Date.now()}`,
        role: "assistant",
        content: "",
      };

      state.messages = [...(Array.isArray(state.messages) ? state.messages : []), userMessage, assistantMessage];
      renderMessages();

      const assistantIndex = state.messages.length - 1;

      input.value = "";
      autoGrowTextarea();
      setStatus("Sending...");

      await sendMessage(outgoing, {
        onStart() {
          setStatus("Thinking...");
        },
        onChunk(chunk) {
          if (!state.messages[assistantIndex]) return;
          state.messages[assistantIndex].content = String(chunk || "");
          renderMessages();
        },
        onDone(text) {
          if (!state.messages[assistantIndex]) return;
          state.messages[assistantIndex].content = String(text || "");
          renderMessages();
        },
        onMeta() {
          renderRouteMeta();
        },
      });

      if (state.activeSessionId) {
        await loadChat(state.activeSessionId);
      }

      renderSessions();
      renderMessages();
      renderRouteMeta();
      ensureDesktopPanels();
      setStatus("Ready");
      closeMobilePanels();
    } catch (err) {
      console.error(err);
      setStatus("Send failed");
    }
  }

  async function handleSaveMemory(event) {
    event.preventDefault();

    const kind = safeText(byId("memoryKind")?.value || "memory");
    const input = byId("memoryValue");
    const value = safeText(input?.value || "");

    if (!value) {
      setMemoryStatus("Enter a memory value first.");
      return;
    }

    try {
      setMemoryStatus("Saving...");
      await saveMemory(kind, value);

      if (input) input.value = "";

      await loadMemory();
      renderMemory();
      setMemoryStatus("Memory saved.");
      closeMobilePanels();
    } catch (err) {
      console.error(err);
      setMemoryStatus("Memory save failed.");
    }
  }

  async function handleDeleteMemory(button) {
    const memoryId = safeText(button?.getAttribute("data-memory-delete") || "");
    if (!memoryId) return;

    try {
      setMemoryStatus("Deleting...");
      await deleteMemory(memoryId);
      await loadMemory();
      renderMemory();
      setMemoryStatus("Memory deleted.");
    } catch (err) {
      console.error(err);
      setMemoryStatus("Memory delete failed.");
    }
  }

  function wireEvents() {
    byId("newChatBtn")?.addEventListener("click", handleNewChat);
    byId("composerForm")?.addEventListener("submit", handleSend);
    byId("memoryForm")?.addEventListener("submit", handleSaveMemory);

    byId("refreshMemoryBtn")?.addEventListener("click", async () => {
      try {
        setMemoryStatus("Refreshing...");
        await loadMemory();
        renderMemory();
        setMemoryStatus("Ready");
      } catch (err) {
        console.error(err);
        setMemoryStatus("Memory refresh failed.");
      }
    });

    byId("sessionList")?.addEventListener("click", async (event) => {
      const button = event.target.closest("[data-action]");
      if (!button) return;
      await handleSessionAction(button);
    });

    byId("memoryList")?.addEventListener("click", async (event) => {
      const button = event.target.closest("[data-memory-delete]");
      if (!button) return;
      await handleDeleteMemory(button);
    });

    byId("showLeftBtn")?.addEventListener("click", () => toggleSidebar("left"));
    byId("showRightBtn")?.addEventListener("click", () => toggleSidebar("right"));
    byId("showLeftBtnInline")?.addEventListener("click", () => toggleSidebar("left"));
    byId("showRightBtnInline")?.addEventListener("click", () => toggleSidebar("right"));

    byId("messageInput")?.addEventListener("input", autoGrowTextarea);

    byId("modelSelect")?.addEventListener("change", (event) => {
      state.currentModel = event.target.value || "gpt-4.1-mini";
      renderRouteMeta();
    });

    window.addEventListener("resize", () => {
      ensureDesktopPanels();
    });
  }

  async function boot() {
    try {
      wireEvents();
      await refreshAll();
      ensureDesktopPanels();
      autoGrowTextarea();
    } catch (err) {
      console.error(err);
      setStatus("Bootstrap failed");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();