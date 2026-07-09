(function () {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.state = Nova.state || {};
  Nova.chatStream = Nova.chatStream || {};
  Nova.chat = Nova.chat || {};

  const CONFIG = {
    stateEndpoint: "/api/state",
    chatEndpoint: "/api/chat",
    sessionNewEndpoint: "/api/session/new",
    sessionGetBase: "/api/chat/",
    defaultModel: "gpt-5.4",
  };

  const state = Object.assign(
    {
      activeSessionId: null,
      sessions: [],
      messages: [],
      models: [],
      selectedModel: null,
      isSending: false,
      pendingAttachments: [],
      booted: false,
    },
    Nova.state || {}
  );

  Nova.state = state;

  const els = {};

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeString(value, fallback = "") {
    return typeof value === "string" ? value : fallback;
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function uid(prefix = "id") {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function pickOne(selectors) {
    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (el) return el;
    }
    return null;
  }

  function findComposer() {
    return pickOne([
      "#composerInput",
      "#composer",
      "#messageInput",
      "#chatInput",
      ".composer-input",
      "textarea",
    ]);
  }

  function findSendBtn() {
    return pickOne([
      "#sendBtn",
      "#sendButton",
      ".send-btn",
      "button[data-role='send']",
      "button[type='submit']",
    ]);
  }

  function findMessagesRoot() {
    return pickOne([
      "#chatMessages",
      "#messages",
      "#messageList",
      ".chat-messages",
      ".messages",
    ]);
  }

  function findSessionRoot() {
    return pickOne([
      "#sessionList",
      ".session-list",
      "[data-role='session-list']",
    ]);
  }

  function findModelSelect() {
    return pickOne([
      "#modelSelect",
      ".model-select",
      "select[data-role='model']",
      "select",
    ]);
  }

  function findNewChatBtn() {
    return pickOne([
      "#newChatBtn",
      ".new-chat-btn",
      "button[data-role='new-chat']",
    ]);
  }

  function findEmptyState() {
    return pickOne([
      "#emptyState",
      ".empty-state",
    ]);
  }

  function normalizeRole(role) {
    const value = safeString(role, "assistant").toLowerCase();
    if (value === "user" || value === "assistant" || value === "system") return value;
    return "assistant";
  }

  function normalizeMessage(message) {
    if (!message || typeof message !== "object") {
      return {
        id: uid("msg"),
        role: "assistant",
        content: "",
        created_at: nowIso(),
        attachments: [],
        meta: {},
      };
    }

    return {
      id: safeString(message.id, uid("msg")),
      role: normalizeRole(message.role),
      content:
        safeString(message.content, "") ||
        safeString(message.text, "") ||
        safeString(message.message, ""),
      created_at: safeString(message.created_at, nowIso()),
      attachments: safeArray(message.attachments),
      meta: message.meta && typeof message.meta === "object" ? message.meta : {},
    };
  }

  function normalizeSession(session) {
    if (!session || typeof session !== "object") {
      return {
        id: uid("session"),
        title: "New chat",
        created_at: nowIso(),
        updated_at: nowIso(),
        pinned: false,
        messages: [],
      };
    }

    return {
      id: safeString(session.id, uid("session")),
      title: safeString(session.title, "New chat"),
      created_at: safeString(session.created_at, nowIso()),
      updated_at: safeString(session.updated_at || session.created_at, nowIso()),
      pinned: !!session.pinned,
      messages: safeArray(session.messages).map(normalizeMessage),
    };
  }

  function renderInline(text) {
    return escapeHtml(text)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");
  }

  function renderParagraphs(text) {
    return safeString(text, "")
      .split(/\n{2,}/)
      .map((block) => {
        const trimmed = block.trim();
        if (!trimmed) return "";
        return `<p>${renderInline(trimmed).replace(/\n/g, "<br>")}</p>`;
      })
      .join("");
  }

  function renderMessageContent(text) {
    const value = safeString(text, "");
    if (!value) return "";

    const parts = [];
    const fence = /```([a-zA-Z0-9_-]+)?\n([\s\S]*?)```/g;
    let lastIndex = 0;
    let match;

    while ((match = fence.exec(value))) {
      const before = value.slice(lastIndex, match.index);
      if (before) parts.push(renderParagraphs(before));

      const lang = escapeHtml(match[1] || "");
      const code = escapeHtml(match[2] || "");
      parts.push(`<pre><code class="language-${lang}">${code}</code></pre>`);

      lastIndex = match.index + match[0].length;
    }

    const tail = value.slice(lastIndex);
    if (tail) parts.push(renderParagraphs(tail));

    return parts.join("");
  }

  function formatTime(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  function getActiveModel() {
    return (
      safeString(state.selectedModel, "") ||
      safeString(state.defaultModel, "") ||
      CONFIG.defaultModel
    );
  }

  function setBusy(isBusy) {
    state.isSending = !!isBusy;
    if (els.composer) els.composer.disabled = !!isBusy;
    if (els.sendBtn) els.sendBtn.disabled = !!isBusy;
    if (els.modelSelect) els.modelSelect.disabled = !!isBusy;
  }

  function autoResizeComposer() {
    if (!els.composer) return;
    if (els.composer.tagName !== "TEXTAREA") return;
    els.composer.style.height = "auto";
    const next = Math.min(Math.max(els.composer.scrollHeight, 42), 180);
    els.composer.style.height = `${next}px`;
  }

  function getComposerValue() {
    if (!els.composer) return "";
    return safeString(els.composer.value, "");
  }

  function setComposerValue(value) {
    if (!els.composer) return;
    els.composer.value = value || "";
    autoResizeComposer();
  }

  function updateEmptyState() {
    if (!els.emptyState) return;
    els.emptyState.classList.toggle("hidden", safeArray(state.messages).length > 0);
  }

  function scrollMessagesToBottom(force = false) {
    if (!els.messagesRoot) return;
    const nearBottom =
      els.messagesRoot.scrollHeight - els.messagesRoot.scrollTop - els.messagesRoot.clientHeight < 180;

    if (force || nearBottom) {
      els.messagesRoot.scrollTop = els.messagesRoot.scrollHeight;
    }
  }

  function createMessageNode(raw) {
    const msg = normalizeMessage(raw);

    const node = document.createElement("article");
    node.className = `chat-message ${msg.role}`;
    node.dataset.messageId = msg.id;

    const body = document.createElement("div");
    body.className = "message-body";

    const content = document.createElement("div");
    content.className = "message-content";
    content.innerHTML = renderMessageContent(msg.content);
    body.appendChild(content);

    if (safeArray(msg.attachments).length) {
      const attachments = document.createElement("div");
      attachments.className = "message-attachments";

      msg.attachments.forEach((att) => {
        const chip = document.createElement("div");
        chip.className = "message-attachment-chip";
        chip.textContent =
          safeString(att?.name, "") ||
          safeString(att?.filename, "") ||
          "attachment";
        attachments.appendChild(chip);
      });

      body.appendChild(attachments);
    }

    const footer = document.createElement("div");
    footer.className = "message-footer";
    footer.innerHTML = `
      <span class="message-role">${escapeHtml(msg.role)}</span>
      <span class="message-time">${escapeHtml(formatTime(msg.created_at))}</span>
    `;
    body.appendChild(footer);

    node.appendChild(body);

    if (msg.role === "assistant") {
      const actions = document.createElement("div");
      actions.className = "message-actions";

      const copyBtn = document.createElement("button");
      copyBtn.type = "button";
      copyBtn.className = "icon-btn";
      copyBtn.textContent = "Copy";
      copyBtn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(msg.content || "");
          copyBtn.textContent = "Copied";
          setTimeout(() => {
            copyBtn.textContent = "Copy";
          }, 1000);
        } catch (_err) {
          copyBtn.textContent = "Failed";
          setTimeout(() => {
            copyBtn.textContent = "Copy";
          }, 1000);
        }
      });

      actions.appendChild(copyBtn);
      node.appendChild(actions);
    }

    return node;
  }

  function renderMessages() {
    if (!els.messagesRoot) return;

    if (Nova.render && typeof Nova.render.renderMessages === "function") {
      try {
        Nova.render.renderMessages(state.messages, state.activeSessionId);
        updateEmptyState();
        scrollMessagesToBottom(true);
        return;
      } catch (_err) {}
    }

    els.messagesRoot.innerHTML = "";
    safeArray(state.messages).forEach((msg) => {
      els.messagesRoot.appendChild(createMessageNode(msg));
    });

    updateEmptyState();
    scrollMessagesToBottom(true);
  }

  function renderSessions() {
    if (!els.sessionRoot) return;

    if (Nova.render && typeof Nova.render.renderSessions === "function") {
      try {
        Nova.render.renderSessions(state.sessions, state.activeSessionId);
        return;
      } catch (_err) {}
    }

    els.sessionRoot.innerHTML = "";

    safeArray(state.sessions).forEach((session) => {
      const row = document.createElement("div");
      row.className = `session-item${session.id === state.activeSessionId ? " is-active" : ""}`;

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "session-main-btn";
      btn.dataset.sessionId = session.id;
      btn.innerHTML = `
        <span class="session-title">${escapeHtml(session.title || "New chat")}</span>
        <span class="session-meta">${escapeHtml(formatTime(session.updated_at || session.created_at))}</span>
      `;

      btn.addEventListener("click", () => {
        openSession(session.id);
      });

      row.appendChild(btn);
      els.sessionRoot.appendChild(row);
    });
  }

  function syncSessionMessages() {
    const session = state.sessions.find((item) => item.id === state.activeSessionId);
    if (!session) return;

    session.messages = state.messages.map((msg) => Object.assign({}, msg));
    session.updated_at = nowIso();

    if (!session.title || session.title === "New chat") {
      const firstUser = state.messages.find((msg) => msg.role === "user" && msg.content);
      if (firstUser) {
        session.title = firstUser.content.slice(0, 60);
      }
    }

    renderSessions();
  }

  async function safeReadText(response) {
    try {
      return await response.text();
    } catch (_err) {
      return "";
    }
  }

  async function apiGet(url) {
    const response = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });

    const text = await safeReadText(response);
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch (_err) {
      data = { raw: text };
    }

    if (!response.ok) {
      throw new Error(
        safeString(data.message, "") ||
          safeString(data.error, "") ||
          `GET failed (${response.status}) ${url}`
      );
    }

    return data;
  }

  async function apiPost(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload || {}),
    });

    const text = await safeReadText(response);
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch (_err) {
      data = { raw: text };
    }

    if (!response.ok) {
      throw new Error(
        safeString(data.message, "") ||
          safeString(data.error, "") ||
          safeString(text, "") ||
          `POST failed (${response.status}) ${url}`
      );
    }

    return data;
  }

  async function ensureSession() {
    if (state.activeSessionId) return state.activeSessionId;

    const data = await apiPost(CONFIG.sessionNewEndpoint, { title: "New chat" });
    const session = normalizeSession(data.session || data);

    state.activeSessionId = session.id;

    const existingIndex = state.sessions.findIndex((item) => item.id === session.id);
    if (existingIndex >= 0) {
      state.sessions[existingIndex] = session;
    } else {
      state.sessions.unshift(session);
    }

    state.messages = safeArray(session.messages);
    renderSessions();
    renderMessages();

    return state.activeSessionId;
  }

  async function loadState() {
    const data = await apiGet(CONFIG.stateEndpoint);

    state.sessions = safeArray(data.sessions).map(normalizeSession);
    state.models = safeArray(data.models);
    state.defaultModel = safeString(data.default_model, CONFIG.defaultModel);
    state.selectedModel = safeString(
      data.selected_model || state.selectedModel || state.defaultModel,
      state.defaultModel
    );

    if (!state.activeSessionId) {
      state.activeSessionId =
        safeString(data.active_session_id, "") ||
        safeString(data.session_id, "") ||
        (state.sessions[0] ? state.sessions[0].id : null);
    }

    const active = state.sessions.find((item) => item.id === state.activeSessionId);
    state.messages = active ? safeArray(active.messages) : [];

    renderModels();
    renderSessions();
    renderMessages();
  }

  function renderModels() {
    if (!els.modelSelect) return;

    const models = state.models.length ? state.models : [getActiveModel()];
    els.modelSelect.innerHTML = "";

    models.forEach((model) => {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      if (model === getActiveModel()) option.selected = true;
      els.modelSelect.appendChild(option);
    });

    els.modelSelect.value = getActiveModel();
  }

  async function openSession(sessionId) {
    if (!sessionId) return;

    const data = await apiGet(`${CONFIG.sessionGetBase}${encodeURIComponent(sessionId)}`);
    const session = normalizeSession(data.session || data);

    const index = state.sessions.findIndex((item) => item.id === session.id);
    if (index >= 0) {
      state.sessions[index] = session;
    } else {
      state.sessions.unshift(session);
    }

    state.activeSessionId = session.id;
    state.messages = safeArray(session.messages);
    renderSessions();
    renderMessages();
  }

  function pushUserMessage(text) {
    const message = normalizeMessage({
      id: uid("user"),
      role: "user",
      content: text,
      created_at: nowIso(),
      attachments: safeArray(state.pendingAttachments),
    });

    state.messages.push(message);
    renderMessages();
    return message;
  }

  function patchOrInsertAssistantMessage(raw) {
    const message = normalizeMessage(raw);
    const index = state.messages.findIndex((item) => item.id === message.id);

    if (index >= 0) {
      state.messages[index] = message;
    } else {
      state.messages.push(message);
    }

    renderMessages();
    return message;
  }

  function buildPayload(text) {
    return {
      session_id: state.activeSessionId,
      content: text,
      model: getActiveModel(),
      attachments: safeArray(state.pendingAttachments),
    };
  }

  async function sendCurrentMessage() {
    if (state.isSending) return;

    const text = getComposerValue().trim();
    const hasAttachments = safeArray(state.pendingAttachments).length > 0;

    if (!text && !hasAttachments) return;

    try {
      await ensureSession();

      pushUserMessage(text);
      setComposerValue("");
      state.pendingAttachments = [];
      setBusy(true);
      syncSessionMessages();

      const data = await apiPost(CONFIG.chatEndpoint, buildPayload(text));

      const assistantMessage = normalizeMessage(
        data.message ||
          data.reply ||
          data.assistant_message || {
            id: uid("assistant"),
            role: "assistant",
            content:
              safeString(data.content, "") ||
              safeString(data.text, "") ||
              "",
            created_at: nowIso(),
          }
      );

      patchOrInsertAssistantMessage(assistantMessage);

      if (data.session) {
        const session = normalizeSession(data.session);
        const existingIndex = state.sessions.findIndex((item) => item.id === session.id);
        if (existingIndex >= 0) {
          state.sessions[existingIndex] = session;
        } else {
          state.sessions.unshift(session);
        }
        state.activeSessionId = session.id;
        state.messages = safeArray(session.messages).map(normalizeMessage);
      }

      syncSessionMessages();
      renderSessions();
      renderMessages();
    } catch (err) {
      console.error("[nova-chat-stream] send failed:", err);

      patchOrInsertAssistantMessage({
        id: uid("assistant"),
        role: "assistant",
        content: `Error: ${safeString(err && err.message, "request failed")}`,
        created_at: nowIso(),
        meta: { error: true },
      });

      syncSessionMessages();
    } finally {
      setBusy(false);
      scrollMessagesToBottom(true);
    }
  }

  function handleComposerKeydown(event) {
    if (event.key !== "Enter") return;
    if (event.shiftKey) return;
    event.preventDefault();
    sendCurrentMessage();
  }

  function wireDom() {
    els.composer = findComposer();
    els.sendBtn = findSendBtn();
    els.messagesRoot = findMessagesRoot();
    els.sessionRoot = findSessionRoot();
    els.modelSelect = findModelSelect();
    els.newChatBtn = findNewChatBtn();
    els.emptyState = findEmptyState();

    if (els.composer) {
      els.composer.addEventListener("input", autoResizeComposer);
      els.composer.addEventListener("keydown", handleComposerKeydown);
      autoResizeComposer();
    }

    if (els.sendBtn) {
      els.sendBtn.addEventListener("click", function (event) {
        event.preventDefault();
        sendCurrentMessage();
      });
    }

    if (els.modelSelect) {
      els.modelSelect.addEventListener("change", function () {
        state.selectedModel = els.modelSelect.value || CONFIG.defaultModel;
      });
    }

    if (els.newChatBtn) {
      els.newChatBtn.addEventListener("click", async function () {
        state.activeSessionId = null;
        state.messages = [];
        renderMessages();
        await ensureSession();
      });
    }

    document.addEventListener("click", function (event) {
      const btn = event.target.closest("[data-session-id]");
      if (btn && btn.dataset.sessionId) {
        openSession(btn.dataset.sessionId);
      }
    });
  }

  function exposeApi() {
    Nova.chatStream.sendCurrentMessage = sendCurrentMessage;
    Nova.chatStream.loadState = loadState;
    Nova.chatStream.openSession = openSession;

    Nova.chat.sendCurrentMessage = sendCurrentMessage;
    Nova.chat.loadState = loadState;
    Nova.chat.openSession = openSession;
  }

  async function bootstrap() {
    if (state.booted) return;
    state.booted = true;

    wireDom();
    exposeApi();
    setBusy(false);

    try {
      await loadState();
    } catch (err) {
      console.error("[nova-chat-stream] bootstrap failed:", err);
      renderMessages();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
  } else {
    bootstrap();
  }
})();

