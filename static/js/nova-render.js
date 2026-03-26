(() => {
  "use strict";

  if (window.__novaRenderLoaded) return;
  window.__novaRenderLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.render = Nova.render || {};
  Nova.state = Nova.state || {};
  Nova.dom = Nova.dom || {};
  Nova.api = Nova.api || {};
  Nova.panels = Nova.panels || {};
  Nova.sessions = Nova.sessions || {};
  Nova.messages = Nova.messages || {};
  Nova.memory = Nova.memory || {};
  Nova.chat = Nova.chat || {};

  const state = Nova.state;
  const dom = Nova.dom;
  const api = Nova.api;
  const panels = Nova.panels;
  const sessions = Nova.sessions;
  const messages = Nova.messages;
  const memory = Nova.memory;
  const chat = Nova.chat;
  const render = Nova.render;

  const byId =
    dom.byId ||
    function byId(id) {
      return document.getElementById(id);
    };

  const qs =
    dom.qs ||
    function qs(selector, root = document) {
      return root.querySelector(selector);
    };

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeString(value, fallback = "") {
    if (typeof value === "string") return value;
    if (value === null || value === undefined) return fallback;
    return String(value);
  }

  function isFn(value) {
    return typeof value === "function";
  }

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function ensureState() {
    if (!Array.isArray(state.sessions)) state.sessions = [];
    if (!Array.isArray(state.messages)) state.messages = [];
    if (!Array.isArray(state.memoryItems)) state.memoryItems = [];
    if (!Array.isArray(state.attachedFiles)) state.attachedFiles = [];
    if (typeof state.activeSessionId !== "string") state.activeSessionId = "";
    if (typeof state.currentModel !== "string" || !state.currentModel.trim()) {
      state.currentModel = "gpt-5.4";
    }
    if (typeof state.isSending !== "boolean") state.isSending = false;
    if (typeof state.sidebarOpen !== "boolean") state.sidebarOpen = true;
    if (typeof state.memoryOpen !== "boolean") state.memoryOpen = true;
    if (typeof state.lastUserMessage !== "string") state.lastUserMessage = "";
    if (typeof state.lastRouter !== "string") state.lastRouter = "ready";
    if (typeof state.theme !== "string" || !state.theme.trim()) {
      state.theme = "dark";
    }
  }

  function getEls() {
    return {
      app: byId("novaApp") || qs(".nova-app"),
      body: document.body,
      mainTopbar: qs(".main-topbar"),
      topbarRight: qs(".topbar-right"),
      chatMessages: byId("chatMessages"),
      emptyState: byId("emptyState"),
      sessionList: byId("sessionList"),
      memoryList: byId("memoryList"),
      memoryInput: byId("memoryInput"),
      addMemoryBtn: byId("addMemoryBtn"),
      composerInput: byId("composerInput"),
      sendBtn: byId("sendBtn"),
      voiceBtn: byId("voiceBtn"),
      attachBtn: byId("attachBtn"),
      fileInput: byId("fileInput"),
      attachmentBar: byId("attachmentBar"),
      newChatBtn: byId("newChatBtn"),
      modelSelect: byId("modelSelect"),
      routerBadge: byId("routerBadge"),
      toggleSidebarBtn: byId("toggleSidebarBtn"),
      toggleMemoryBtn: byId("toggleMemoryBtn") || byId("openMemoryBtn"),
      themeToggleBtn: byId("themeToggleBtn") || byId("toggleThemeBtn"),
    };
  }

  function setRouterBadge(text) {
    const els = getEls();
    if (!els.routerBadge) return;
    els.routerBadge.textContent = safeString(text || "ready");
  }

  function autosizeComposer() {
    const els = getEls();
    const input = els.composerInput;
    if (!input) return;

    input.style.height = "auto";
    const next = Math.min(Math.max(input.scrollHeight, 48), 220);
    input.style.height = `${next}px`;
  }

  function escapeHtml(value) {
    return safeString(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function syncComposerDisabledState() {
    const els = getEls();
    if (els.sendBtn) {
      els.sendBtn.disabled = !!state.isSending;
      els.sendBtn.textContent = state.isSending ? "Sending..." : "Send";
    }
    if (els.composerInput) {
      els.composerInput.disabled = !!state.isSending;
    }
  }

  function syncEmptyState() {
    const els = getEls();
    if (!els.emptyState) return;
    els.emptyState.classList.toggle("hidden", safeArray(state.messages).length > 0);
  }

  function normalizeSession(raw) {
    if (!raw || typeof raw !== "object") return null;

    const id = safeString(raw.id || raw.session_id || raw.sessionId || "").trim();
    if (!id) return null;

    const title = safeString(raw.title || raw.name || "New chat").trim() || "New chat";
    const preview = safeString(raw.preview || raw.last_message || raw.lastMessage || "").trim();
    const updatedAt = safeString(
      raw.updated_at || raw.updatedAt || raw.created_at || raw.createdAt || ""
    ).trim();
    const pinned = !!(raw.pinned || raw.is_pinned || raw.isPinned);

    return {
      id,
      title,
      preview,
      updated_at: updatedAt,
      pinned,
    };
  }

  function normalizeMessage(raw) {
    if (!raw || typeof raw !== "object") return null;

    const role = safeString(raw.role || "assistant").trim() || "assistant";
    const content = safeString(raw.content || raw.text || "");
    const createdAt = safeString(raw.created_at || raw.createdAt || "").trim();

    return {
      role,
      content,
      created_at: createdAt,
    };
  }

  function normalizeMemory(raw) {
    if (!raw || typeof raw !== "object") return null;

    const id = safeString(raw.id || raw.memory_id || raw.memoryId || "").trim();
    const kind = safeString(raw.kind || "memory").trim() || "memory";
    const value = safeString(raw.value || raw.text || "").trim();
    const createdAt = safeString(raw.created_at || raw.createdAt || "").trim();

    if (!id || !value) return null;

    return {
      id,
      kind,
      value,
      created_at: createdAt,
    };
  }

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";

    try {
      return date.toLocaleString([], {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_error) {
      return "";
    }
  }

  function renderSessionsFallback() {
    const els = getEls();
    if (!els.sessionList) return;

    const list = safeArray(state.sessions);
    els.sessionList.innerHTML = "";

    if (!list.length) {
      const empty = document.createElement("div");
      empty.className = "empty-panel-note";
      empty.textContent = "No sessions yet.";
      els.sessionList.appendChild(empty);
      return;
    }

    list.forEach((session) => {
      const item = document.createElement("article");
      item.className = `session-item${session.id === state.activeSessionId ? " is-active" : ""}`;

      item.innerHTML = `
        <button class="session-item-main" type="button" data-session-open="${escapeHtml(session.id)}">
          <div class="session-item-title">${escapeHtml(session.title || "New chat")}</div>
          <div class="session-item-preview">${escapeHtml(session.preview || "Open session")}</div>
          <div class="session-item-meta">
            <span>${escapeHtml(formatDate(session.updated_at) || "No date")}</span>
            <span class="session-item-pin">${session.pinned ? "Pinned" : ""}</span>
          </div>
        </button>
      `;

      els.sessionList.appendChild(item);
    });

    els.sessionList.querySelectorAll("[data-session-open]").forEach((button) => {
      if (button.dataset.novaBoundOpen === "true") return;
      button.dataset.novaBoundOpen = "true";

      button.addEventListener("click", async () => {
        const sessionId = button.getAttribute("data-session-open") || "";
        if (!sessionId) return;
        await loadSession(sessionId);
      });
    });
  }

  function renderMessagesFallback() {
    const els = getEls();
    if (!els.chatMessages) return;

    const existingEmpty = els.emptyState;
    els.chatMessages.innerHTML = "";

    if (existingEmpty && safeArray(state.messages).length === 0) {
      els.chatMessages.appendChild(existingEmpty);
      syncEmptyState();
      return;
    }

    safeArray(state.messages).forEach((message) => {
      const role = safeString(message.role || "assistant").trim().toLowerCase();
      const article = document.createElement("article");
      article.className = `message message-${role === "user" ? "user" : role === "system" ? "system" : "assistant"}`;

      article.innerHTML = `
        <div class="message-head">
          <div class="message-role">${escapeHtml(role)}</div>
          <div class="message-time">${escapeHtml(formatDate(message.created_at) || "")}</div>
        </div>
        <div class="message-body">
          <pre>${escapeHtml(message.content || "")}</pre>
        </div>
      `;

      els.chatMessages.appendChild(article);
    });

    syncEmptyState();
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
  }

  function renderMemoryFallback() {
    const els = getEls();
    if (!els.memoryList) return;

    els.memoryList.innerHTML = "";

    const list = safeArray(state.memoryItems);
    if (!list.length) {
      const empty = document.createElement("div");
      empty.className = "empty-panel-note";
      empty.textContent = "No memory saved yet.";
      els.memoryList.appendChild(empty);
      return;
    }

    list.forEach((item) => {
      const article = document.createElement("article");
      article.className = "memory-card";

      article.innerHTML = `
        <div class="memory-card-top">
          <span class="memory-kind">${escapeHtml(item.kind || "memory")}</span>
          <span class="memory-date">${escapeHtml(formatDate(item.created_at) || "")}</span>
        </div>
        <div class="memory-value">${escapeHtml(item.value || "")}</div>
      `;

      els.memoryList.appendChild(article);
    });
  }

  function renderAll() {
    syncThemeButtonLabel();
    ensureTopbarUtilityButtons();
    setRouterBadge(state.lastRouter || "ready");

    if (isFn(sessions.renderSessionList)) {
      try {
        sessions.renderSessionList();
      } catch (_error) {
        renderSessionsFallback();
      }
    } else {
      renderSessionsFallback();
    }

    if (isFn(messages.renderMessages)) {
      try {
        messages.renderMessages();
      } catch (_error) {
        renderMessagesFallback();
      }
    } else {
      renderMessagesFallback();
    }

    if (isFn(memory.renderMemoryList)) {
      try {
        memory.renderMemoryList();
      } catch (_error) {
        renderMemoryFallback();
      }
    } else {
      renderMemoryFallback();
    }

    syncComposerDisabledState();
    syncEmptyState();
    autosizeComposer();
  }

  async function fetchState() {
    if (!isFn(api.getState)) return null;

    try {
      return await api.getState();
    } catch (_error) {
      return null;
    }
  }

  async function fetchMemory() {
    if (!isFn(api.getMemory)) return null;

    try {
      return await api.getMemory();
    } catch (_error) {
      return null;
    }
  }

  async function fetchSession(sessionId) {
    if (!sessionId) return null;

    if (isFn(api.getChat)) {
      try {
        return await api.getChat(sessionId);
      } catch (_error) {
        return null;
      }
    }

    return null;
  }

  function hydrateStateFromStatePayload(payload) {
    if (!payload || typeof payload !== "object") return;

    const rawSessions =
      payload.sessions ||
      payload.items ||
      payload.data?.sessions ||
      [];

    const sessionList = safeArray(rawSessions)
      .map(normalizeSession)
      .filter(Boolean);

    if (sessionList.length || Array.isArray(rawSessions)) {
      state.sessions = sessionList;
    }

    const activeSessionId =
      payload.active_session_id ||
      payload.activeSessionId ||
      payload.session_id ||
      payload.sessionId ||
      "";

    if (activeSessionId) {
      state.activeSessionId = safeString(activeSessionId);
    } else if (!state.activeSessionId && sessionList[0]?.id) {
      state.activeSessionId = sessionList[0].id;
    }

    const model =
      payload.default_model ||
      payload.model ||
      payload.current_model ||
      payload.currentModel ||
      "";

    if (model) {
      state.currentModel = safeString(model);
    }
  }

  function hydrateMemoryFromPayload(payload) {
    if (!payload || typeof payload !== "object") return;

    const rawItems =
      payload.items ||
      payload.memory ||
      payload.data?.items ||
      [];

    state.memoryItems = safeArray(rawItems)
      .map(normalizeMemory)
      .filter(Boolean);
  }

  function hydrateMessagesFromPayload(payload) {
    if (!payload || typeof payload !== "object") return;

    const rawMessages =
      payload.messages ||
      payload.items ||
      payload.data?.messages ||
      [];

    state.messages = safeArray(rawMessages)
      .map(normalizeMessage)
      .filter(Boolean);
  }

  async function loadInitialState() {
    const payload = await fetchState();
    hydrateStateFromStatePayload(payload);

    const memoryPayload = await fetchMemory();
    hydrateMemoryFromPayload(memoryPayload);

    if (state.activeSessionId) {
      const sessionPayload = await fetchSession(state.activeSessionId);
      hydrateMessagesFromPayload(sessionPayload);
    }
  }

  async function loadSession(sessionId) {
    if (!sessionId) return;

    const payload = await fetchSession(sessionId);
    if (!payload) return;

    state.activeSessionId = safeString(sessionId);
    hydrateMessagesFromPayload(payload);
    renderAll();

    if (panels.isMobileViewport && panels.isMobileViewport()) {
      if (isFn(panels.closeAllPanels)) {
        panels.closeAllPanels();
      }
    }
  }

  async function createNewSession() {
    if (!isFn(api.createSession)) return;

    try {
      const payload = await api.createSession();
      const newId = safeString(
        payload?.session_id ||
        payload?.sessionId ||
        payload?.id ||
        ""
      ).trim();

      await refreshSessions();

      if (newId) {
        await loadSession(newId);
      } else if (state.sessions[0]?.id) {
        await loadSession(state.sessions[0].id);
      }
    } catch (_error) {
      // no-op fallback
    }
  }

  async function refreshSessions() {
    const payload = await fetchState();
    hydrateStateFromStatePayload(payload);
    renderAll();
  }

  async function refreshMemory() {
    const payload = await fetchMemory();
    hydrateMemoryFromPayload(payload);
    renderAll();
  }

  async function addMemoryFromInput() {
    const els = getEls();
    if (!els.memoryInput || !isFn(api.addMemory)) return;

    const value = safeString(els.memoryInput.value || "").trim();
    if (!value) return;

    els.memoryInput.disabled = true;
    if (els.addMemoryBtn) els.addMemoryBtn.disabled = true;

    try {
      await api.addMemory({ value });
      els.memoryInput.value = "";
      await refreshMemory();
    } catch (_error) {
      // no-op fallback
    } finally {
      els.memoryInput.disabled = false;
      if (els.addMemoryBtn) els.addMemoryBtn.disabled = false;
    }
  }

  function renderAttachmentBar() {
    const els = getEls();
    if (!els.attachmentBar) return;

    const files = safeArray(state.attachedFiles);
    els.attachmentBar.innerHTML = "";

    if (!files.length) {
      els.attachmentBar.classList.add("hidden");
      return;
    }

    els.attachmentBar.classList.remove("hidden");

    files.forEach((file, index) => {
      const chip = document.createElement("div");
      chip.className = "attachment-chip";
      chip.innerHTML = `
        <span class="attachment-chip-name">${escapeHtml(file?.name || `file-${index + 1}`)}</span>
        <button
          type="button"
          class="attachment-chip-remove"
          data-attachment-remove="${index}"
          aria-label="Remove attachment"
        >
          ✕
        </button>
      `;
      els.attachmentBar.appendChild(chip);
    });

    els.attachmentBar.querySelectorAll("[data-attachment-remove]").forEach((button) => {
      if (button.dataset.novaBoundRemove !== "true") {
        button.dataset.novaBoundRemove = "true";
        button.addEventListener("click", () => {
          const idx = Number(button.getAttribute("data-attachment-remove"));
          if (Number.isNaN(idx)) return;
          state.attachedFiles = safeArray(state.attachedFiles).filter((_, i) => i !== idx);

          if (els.fileInput) {
            try {
              els.fileInput.value = "";
            } catch (_error) {
              // no-op
            }
          }

          renderAttachmentBar();
        });
      }
    });
  }

  function syncModelSelect() {
    const els = getEls();
    if (!els.modelSelect) return;

    const model = state.currentModel || "gpt-5.4";
    const hasOption = Array.from(els.modelSelect.options).some((option) => option.value === model);

    if (!hasOption) {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      els.modelSelect.appendChild(option);
    }

    els.modelSelect.value = model;
  }

  function getPreferredTheme() {
    try {
      const stored = localStorage.getItem("nova-theme");
      if (stored === "light" || stored === "dark") {
        return stored;
      }
    } catch (_error) {
      // no-op
    }

    if (document.body.getAttribute("data-theme") === "light") {
      return "light";
    }

    return "dark";
  }

  function applyTheme(theme) {
    const nextTheme = theme === "light" ? "light" : "dark";
    state.theme = nextTheme;
    document.body.setAttribute("data-theme", nextTheme);
    document.documentElement.setAttribute("data-theme", nextTheme);

    try {
      localStorage.setItem("nova-theme", nextTheme);
    } catch (_error) {
      // no-op
    }

    syncThemeButtonLabel();
  }

  function toggleTheme() {
    applyTheme(state.theme === "light" ? "dark" : "light");
  }

  function syncThemeButtonLabel() {
    const els = getEls();
    const button = els.themeToggleBtn;
    if (!button) return;

    const isLight = state.theme === "light";
    button.setAttribute("aria-label", isLight ? "Switch to dark theme" : "Switch to light theme");
    button.setAttribute("title", isLight ? "Dark mode" : "Light mode");
    button.textContent = isLight ? "☾" : "☀";
  }

  function ensureTopbarUtilityButtons() {
    const els = getEls();
    const topbarRight = els.topbarRight;
    if (!topbarRight) return;

    if (!els.toggleMemoryBtn) {
      const memoryBtn = document.createElement("button");
      memoryBtn.id = "toggleMemoryBtn";
      memoryBtn.className = "icon-btn";
      memoryBtn.type = "button";
      memoryBtn.setAttribute("aria-label", "Toggle memory panel");
      memoryBtn.setAttribute("data-action", "toggle-memory");
      memoryBtn.textContent = "⟫";
      topbarRight.appendChild(memoryBtn);
    }

    if (!els.themeToggleBtn) {
      const themeBtn = document.createElement("button");
      themeBtn.id = "themeToggleBtn";
      themeBtn.className = "icon-btn";
      themeBtn.type = "button";
      themeBtn.setAttribute("aria-label", "Toggle theme");
      themeBtn.setAttribute("title", "Toggle theme");
      themeBtn.textContent = "☀";
      topbarRight.appendChild(themeBtn);
    }
  }

  async function sendMessage(options = {}) {
    const els = getEls();
    if (!els.composerInput && !safeString(options.contentOverride).trim()) return;
    if (state.isSending) return;

    const overrideContent = safeString(options.contentOverride || "").trim();
    const content = overrideContent || safeString(els.composerInput?.value || "").trim();
    if (!content) return;

    const shouldClearComposer = !overrideContent;

    state.isSending = true;
    state.lastUserMessage = content;
    syncComposerDisabledState();

    const optimisticUserMessage = {
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    if (!options.regenerate) {
      state.messages = [...safeArray(state.messages), optimisticUserMessage];
    }

    if (shouldClearComposer && els.composerInput) {
      els.composerInput.value = "";
      autosizeComposer();
    }

    renderAll();

    try {
      if (isFn(chat.sendMessage)) {
        await chat.sendMessage({
          content,
          sessionId: state.activeSessionId,
          model: state.currentModel,
          regenerate: !!options.regenerate,
        });
      } else if (isFn(api.sendChat)) {
        const payload = await api.sendChat({
          content,
          session_id: state.activeSessionId,
          model: state.currentModel,
        });

        const returnedSessionId = safeString(
          payload?.session_id ||
          payload?.sessionId ||
          state.activeSessionId ||
          ""
        ).trim();

        if (returnedSessionId) {
          state.activeSessionId = returnedSessionId;
        }

        if (payload?.router || payload?.route) {
          state.lastRouter = safeString(payload.router || payload.route || "ready");
        }

        if (payload?.messages) {
          hydrateMessagesFromPayload(payload);
        } else if (payload?.answer || payload?.content) {
          state.messages = [
            ...safeArray(state.messages),
            {
              role: "assistant",
              content: safeString(payload.answer || payload.content || ""),
              created_at: new Date().toISOString(),
            },
          ];
        }
      }

      await refreshSessions();

      if (state.activeSessionId) {
        const sessionPayload = await fetchSession(state.activeSessionId);
        if (sessionPayload) {
          hydrateMessagesFromPayload(sessionPayload);
        }
      }
    } catch (_error) {
      state.messages = [
        ...safeArray(state.messages),
        {
          role: "system",
          content: "Something went wrong sending that message.",
          created_at: new Date().toISOString(),
        },
      ];
    } finally {
      state.isSending = false;
      syncComposerDisabledState();
      renderAll();
    }
  }

  function bindComposer() {
    const els = getEls();

    if (els.composerInput && els.composerInput.dataset.novaBoundInput !== "true") {
      els.composerInput.dataset.novaBoundInput = "true";

      els.composerInput.addEventListener("input", autosizeComposer);

      els.composerInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage();
        }
      });
    }

    if (els.sendBtn && els.sendBtn.dataset.novaBoundSend !== "true") {
      els.sendBtn.dataset.novaBoundSend = "true";
      els.sendBtn.addEventListener("click", () => sendMessage());
    }
  }

  function bindSessionControls() {
    const els = getEls();

    if (els.newChatBtn && els.newChatBtn.dataset.novaBoundNewChat !== "true") {
      els.newChatBtn.dataset.novaBoundNewChat = "true";
      els.newChatBtn.addEventListener("click", createNewSession);
    }

    if (els.modelSelect && els.modelSelect.dataset.novaBoundModel !== "true") {
      els.modelSelect.dataset.novaBoundModel = "true";

      els.modelSelect.addEventListener("change", () => {
        state.currentModel = safeString(els.modelSelect.value || "gpt-5.4");
      });
    }
  }

  function bindMemoryControls() {
    const els = getEls();

    if (els.addMemoryBtn && els.addMemoryBtn.dataset.novaBoundAddMemory !== "true") {
      els.addMemoryBtn.dataset.novaBoundAddMemory = "true";
      els.addMemoryBtn.addEventListener("click", addMemoryFromInput);
    }

    if (els.memoryInput && els.memoryInput.dataset.novaBoundMemoryInput !== "true") {
      els.memoryInput.dataset.novaBoundMemoryInput = "true";

      els.memoryInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          addMemoryFromInput();
        }
      });
    }
  }

  function bindAttachmentControls() {
    const els = getEls();
    if (!els.attachBtn || !els.fileInput) return;

    if (els.attachBtn.dataset.novaBoundAttach !== "true") {
      els.attachBtn.dataset.novaBoundAttach = "true";
      els.attachBtn.addEventListener("click", () => {
        els.fileInput.click();
      });
    }

    if (els.fileInput.dataset.novaBoundFileInput !== "true") {
      els.fileInput.dataset.novaBoundFileInput = "true";
      els.fileInput.addEventListener("change", () => {
        state.attachedFiles = Array.from(els.fileInput.files || []);
        renderAttachmentBar();
      });
    }
  }

  function bindThemeControl() {
    const els = getEls();
    if (!els.themeToggleBtn) return;

    if (els.themeToggleBtn.dataset.novaBoundTheme !== "true") {
      els.themeToggleBtn.dataset.novaBoundTheme = "true";
      els.themeToggleBtn.addEventListener("click", toggleTheme);
    }
  }

  function bindUtilityRecovery() {
    const observerTarget = document.body;
    if (!observerTarget || observerTarget.dataset.novaUtilityObserver === "true") return;
    observerTarget.dataset.novaUtilityObserver = "true";

    const observer = new MutationObserver(() => {
      ensureTopbarUtilityButtons();
      bindThemeControl();

      const els = getEls();
      if (els.toggleMemoryBtn && els.toggleMemoryBtn.dataset.novaPanelNudge !== "true") {
        els.toggleMemoryBtn.dataset.novaPanelNudge = "true";

        els.toggleMemoryBtn.addEventListener("click", () => {
          window.setTimeout(() => {
            if (isFn(panels.syncPanelState)) {
              panels.syncPanelState();
            }
          }, 0);
        });
      }
    });

    observer.observe(observerTarget, {
      childList: true,
      subtree: true,
    });
  }

  async function bootstrap() {
    ensureState();

    ensureTopbarUtilityButtons();
    state.theme = getPreferredTheme();
    applyTheme(state.theme);

    setRouterBadge("loading");

    bindComposer();
    bindSessionControls();
    bindMemoryControls();
    bindAttachmentControls();
    bindThemeControl();
    bindUtilityRecovery();

    if (isFn(panels.init)) {
      try {
        panels.init();
      } catch (_error) {
        // no-op fallback
      }
    }

    await loadInitialState();

    syncModelSelect();
    renderAttachmentBar();
    renderAll();

    setRouterBadge(state.lastRouter || "ready");
  }

  render.bootstrap = bootstrap;
  render.renderAll = renderAll;
  render.loadSession = loadSession;
  render.refreshSessions = refreshSessions;
  render.refreshMemory = refreshMemory;
  render.sendMessage = sendMessage;
  render.autosizeComposer = autosizeComposer;
  render.applyTheme = applyTheme;
  render.toggleTheme = toggleTheme;
  render.ensureTopbarUtilityButtons = ensureTopbarUtilityButtons;

  Nova.loadSession = loadSession;
  Nova.refreshSessions = refreshSessions;
  Nova.refreshMemory = refreshMemory;
  Nova.renderAll = renderAll;
  Nova.sendMessage = sendMessage;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
  } else {
    bootstrap();
  }
})();