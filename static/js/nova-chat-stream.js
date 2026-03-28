// notepad C:\Users\Owner\nova\static\js\nova-chat-stream.js
(function () {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.state = Nova.state || {};
  Nova.chatStream = Nova.chatStream || {};
  Nova.chat = Nova.chat || {};

  const CONFIG = {
    stateEndpoint: "/api/state",
    chatEndpoint: "/api/chat",
    streamEndpoint: "/api/chat/stream",
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
      defaultModel: CONFIG.defaultModel,
      isSending: false,
      isStreaming: false,
      pendingAttachments: [],
      pendingAssistantMessageId: null,
      currentAbortController: null,
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

  function safeObject(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function uid(prefix = "id") {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
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
      "#novaComposer",
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
      "#novaSendBtn",
      "#sendButton",
      ".send-btn",
      "button[data-role='send']",
      "button[data-action='send-message']",
      "button[type='submit']",
    ]);
  }

  function findStopBtn() {
    return pickOne([
      "#stopBtn",
      "#novaStopBtn",
      "button[data-action='stop-stream']",
    ]);
  }

  function findMessagesRoot() {
    return pickOne([
      "#novaMessages",
      "#chatMessages",
      "#messages",
      "#messageList",
      ".chat-messages",
      ".messages",
      "[data-nova-messages]",
    ]);
  }

  function findSessionRoot() {
    return pickOne([
      "#novaSessionList",
      "#sessionList",
      ".session-list",
      "[data-role='session-list']",
      "[data-nova-sessions]",
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
    if (value === "user" || value === "assistant" || value === "system" || value === "tool") {
      return value;
    }
    return "assistant";
  }

  function normalizeMessage(message) {
    const item = safeObject(message);

    return {
      id: safeString(item.id, uid("msg")),
      role: normalizeRole(item.role),
      content:
        safeString(item.content, "") ||
        safeString(item.text, "") ||
        safeString(item.message, ""),
      created_at: safeString(item.created_at, nowIso()),
      attachments: safeArray(item.attachments),
      images: safeArray(item.images),
      videos: safeArray(item.videos),
      audios: safeArray(item.audios),
      media: safeArray(item.media),
      meta: safeObject(item.meta),
      error: !!item.error || !!safeObject(item.meta).error,
    };
  }

  function normalizeSession(session) {
    const item = safeObject(session);

    return {
      id: safeString(item.id, uid("session")),
      title: safeString(item.title, "New chat"),
      created_at: safeString(item.created_at, nowIso()),
      updated_at: safeString(item.updated_at || item.created_at, nowIso()),
      pinned: !!item.pinned,
      messages: safeArray(item.messages).map(normalizeMessage),
    };
  }

  function emit(name, detail) {
    document.dispatchEvent(
      new CustomEvent(name, {
        bubbles: true,
        cancelable: false,
        detail: detail || {},
      })
    );
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

  function setStreaming(isStreaming, pendingAssistantMessageId) {
    state.isStreaming = !!isStreaming;
    state.pendingAssistantMessageId = pendingAssistantMessageId || null;

    if (els.stopBtn) {
      els.stopBtn.hidden = !state.isStreaming;
      els.stopBtn.disabled = !state.isStreaming;
    }

    emit("nova:streaming:update", {
      isStreaming: state.isStreaming,
      pendingAssistantMessageId: state.pendingAssistantMessageId,
    });
  }

  function autoResizeComposer() {
    if (!els.composer || els.composer.tagName !== "TEXTAREA") return;
    els.composer.style.height = "auto";
    const next = Math.min(Math.max(els.composer.scrollHeight, 42), 220);
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

    if (force || nearBottom || state.isStreaming) {
      els.messagesRoot.scrollTop = els.messagesRoot.scrollHeight;
    }
  }

  function renderAll() {
    if (Nova.render && typeof Nova.render.syncState === "function") {
      Nova.render.syncState({
        activeSessionId: state.activeSessionId,
        sessions: state.sessions,
        messages: state.messages,
        isStreaming: state.isStreaming,
        composerLocked: state.isSending,
        pendingAssistantMessageId: state.pendingAssistantMessageId,
      });
      return;
    }

    renderSessionsFallback();
    renderMessagesFallback();
  }

  function renderMessages() {
    if (Nova.render && typeof Nova.render.replaceMessages === "function") {
      Nova.render.replaceMessages(state.messages);
      updateEmptyState();
      scrollMessagesToBottom(true);
      return;
    }

    renderMessagesFallback();
  }

  function renderSessions() {
    if (Nova.render && typeof Nova.render.replaceSessions === "function") {
      Nova.render.replaceSessions(state.sessions);
      return;
    }

    renderSessionsFallback();
  }

  function renderMessagesFallback() {
    if (!els.messagesRoot) return;

    els.messagesRoot.innerHTML = "";

    safeArray(state.messages).forEach((raw) => {
      const msg = normalizeMessage(raw);

      const node = document.createElement("article");
      node.className = `chat-message ${msg.role}${msg.error ? " is-error" : ""}`;
      node.dataset.messageId = msg.id;

      const body = document.createElement("div");
      body.className = "message-body";

      const content = document.createElement("div");
      content.className = "message-content";
      content.textContent = msg.content || "";
      body.appendChild(content);

      const footer = document.createElement("div");
      footer.className = "message-footer";
      footer.textContent = `${msg.role} • ${msg.created_at || ""}`;
      body.appendChild(footer);

      node.appendChild(body);
      els.messagesRoot.appendChild(node);
    });

    updateEmptyState();
    scrollMessagesToBottom(true);
  }

  function renderSessionsFallback() {
    if (!els.sessionRoot) return;

    els.sessionRoot.innerHTML = "";

    safeArray(state.sessions).forEach((raw) => {
      const session = normalizeSession(raw);

      const row = document.createElement("button");
      row.type = "button";
      row.className = `session-item${session.id === state.activeSessionId ? " is-active" : ""}`;
      row.dataset.sessionId = session.id;
      row.textContent = session.title || "New chat";

      row.addEventListener("click", function () {
        openSession(session.id);
      });

      els.sessionRoot.appendChild(row);
    });
  }

  function replaceOrUpsertSession(session) {
    const normalized = normalizeSession(session);
    const index = state.sessions.findIndex((item) => item.id === normalized.id);

    if (index >= 0) {
      state.sessions[index] = normalized;
    } else {
      state.sessions.unshift(normalized);
    }

    return normalized;
  }

  function syncSessionMessages() {
    const session = state.sessions.find((item) => item.id === state.activeSessionId);
    if (!session) return;

    session.messages = state.messages.map((msg) => Object.assign({}, normalizeMessage(msg)));
    session.updated_at = nowIso();

    if (!session.title || session.title === "New chat") {
      const firstUser = state.messages.find((msg) => normalizeRole(msg.role) === "user" && safeString(msg.content, "").trim());
      if (firstUser) {
        session.title = safeString(firstUser.content, "New chat").trim().slice(0, 60) || "New chat";
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

  async function apiPost(url, payload, signal) {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      signal,
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
    const session = replaceOrUpsertSession(data.session || data);

    state.activeSessionId = session.id;
    state.messages = safeArray(session.messages).map(normalizeMessage);

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
    state.messages = active ? safeArray(active.messages).map(normalizeMessage) : [];

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
    const session = replaceOrUpsertSession(data.session || data);

    state.activeSessionId = session.id;
    state.messages = safeArray(session.messages).map(normalizeMessage);

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

  function createPendingAssistantMessage() {
    const message = normalizeMessage({
      id: uid("assistant"),
      role: "assistant",
      content: "",
      created_at: nowIso(),
      meta: { pending: true },
    });

    state.messages.push(message);
    state.pendingAssistantMessageId = message.id;
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

  function patchPendingAssistantContent(content, meta) {
    const messageId = state.pendingAssistantMessageId;
    if (!messageId) return null;

    const index = state.messages.findIndex((item) => safeString(item.id) === messageId);
    if (index < 0) return null;

    const current = normalizeMessage(state.messages[index]);
    current.content = safeString(content, current.content);
    current.meta = Object.assign({}, current.meta, safeObject(meta));
    state.messages[index] = current;

    renderMessages();
    return current;
  }

  function finalizePendingAssistant(raw) {
    const pendingId = state.pendingAssistantMessageId;
    const message = normalizeMessage(
      Object.assign({}, safeObject(raw), pendingId && !safeObject(raw).id ? { id: pendingId } : {})
    );

    const index = state.messages.findIndex((item) => safeString(item.id) === message.id);
    if (index >= 0) {
      state.messages[index] = message;
    } else {
      state.messages.push(message);
    }

    state.pendingAssistantMessageId = null;
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

  async function sendViaStandardEndpoint(text) {
    const data = await apiPost(CONFIG.chatEndpoint, buildPayload(text), state.currentAbortController?.signal);

    const assistantMessage = normalizeMessage(
      data.message ||
        data.reply ||
        data.assistant_message || {
          id: state.pendingAssistantMessageId || uid("assistant"),
          role: "assistant",
          content: safeString(data.content, "") || safeString(data.text, "") || "",
          created_at: nowIso(),
        }
    );

    finalizePendingAssistant(assistantMessage);

    if (data.session) {
      const session = replaceOrUpsertSession(data.session);
      state.activeSessionId = session.id;
      state.messages = safeArray(session.messages).map(normalizeMessage);
    }

    syncSessionMessages();
    renderSessions();
    renderMessages();
  }

  async function sendCurrentMessage() {
    if (state.isSending || state.isStreaming) return;

    const text = getComposerValue().trim();
    const hasAttachments = safeArray(state.pendingAttachments).length > 0;

    if (!text && !hasAttachments) return;

    try {
      await ensureSession();

      pushUserMessage(text);
      setComposerValue("");
      state.pendingAttachments = [];
      syncSessionMessages();

      state.currentAbortController = new AbortController();
      setBusy(true);
      setStreaming(true, null);

      createPendingAssistantMessage();
      setStreaming(true, state.pendingAssistantMessageId);

      await sendViaStandardEndpoint(text);
    } catch (err) {
      console.error("[nova-chat-stream] send failed:", err);

      if (safeString(err && err.name) === "AbortError") {
        finalizePendingAssistant({
          id: state.pendingAssistantMessageId || uid("assistant"),
          role: "assistant",
          content: "[stopped]",
          created_at: nowIso(),
          meta: { stopped: true },
        });
      } else {
        finalizePendingAssistant({
          id: state.pendingAssistantMessageId || uid("assistant"),
          role: "assistant",
          content: `Error: ${safeString(err && err.message, "request failed")}`,
          created_at: nowIso(),
          meta: { error: true },
          error: true,
        });
      }

      syncSessionMessages();
    } finally {
      setBusy(false);
      setStreaming(false, null);
      state.currentAbortController = null;
      scrollMessagesToBottom(true);
    }
  }

  function stopCurrentStream() {
    if (state.currentAbortController) {
      try {
        state.currentAbortController.abort();
      } catch (_err) {}
    }
  }

  function retryFromMessage(messageId) {
    const messages = safeArray(state.messages);
    let retryText = "";

    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const msg = normalizeMessage(messages[i]);
      if (messageId && msg.id === messageId) {
        for (let j = i - 1; j >= 0; j -= 1) {
          const candidate = normalizeMessage(messages[j]);
          if (candidate.role === "user" && safeString(candidate.content).trim()) {
            retryText = candidate.content;
            break;
          }
        }
        break;
      }
    }

    if (!retryText) {
      const lastUser = [...messages].reverse().map(normalizeMessage).find((msg) => msg.role === "user" && safeString(msg.content).trim());
      retryText = lastUser ? lastUser.content : "";
    }

    if (!retryText) return;

    setComposerValue(retryText);
    sendCurrentMessage();
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
    els.stopBtn = findStopBtn();
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

    if (els.stopBtn) {
      els.stopBtn.addEventListener("click", function (event) {
        event.preventDefault();
        stopCurrentStream();
      });
      els.stopBtn.hidden = true;
      els.stopBtn.disabled = true;
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
      const sessionBtn = event.target.closest("[data-session-id]");
      if (sessionBtn && sessionBtn.dataset.sessionId) {
        if (
          sessionBtn.dataset.action === "rename-session" ||
          sessionBtn.dataset.action === "delete-session" ||
          sessionBtn.dataset.action === "toggle-session-pin"
        ) {
          return;
        }
        openSession(sessionBtn.dataset.sessionId);
      }
    });

    document.addEventListener("nova:chat:send", function () {
      sendCurrentMessage();
    });

    document.addEventListener("nova:chat:stop", function () {
      stopCurrentStream();
    });

    document.addEventListener("nova:session:open", function (event) {
      const sessionId = safeString(event && event.detail && event.detail.sessionId, "");
      if (sessionId) openSession(sessionId);
    });

    document.addEventListener("nova:message:retry", function (event) {
      const messageId = safeString(event && event.detail && event.detail.messageId, "");
      retryFromMessage(messageId);
    });
  }

  function exposeApi() {
    Nova.chatStream.sendCurrentMessage = sendCurrentMessage;
    Nova.chatStream.loadState = loadState;
    Nova.chatStream.openSession = openSession;
    Nova.chatStream.stopCurrentStream = stopCurrentStream;
    Nova.chatStream.retryFromMessage = retryFromMessage;
    Nova.chatStream.patchPendingAssistantContent = patchPendingAssistantContent;

    Nova.chat.sendCurrentMessage = sendCurrentMessage;
    Nova.chat.loadState = loadState;
    Nova.chat.openSession = openSession;
    Nova.chat.stopCurrentStream = stopCurrentStream;
  }

  async function bootstrap() {
    if (state.booted) return;
    state.booted = true;

    wireDom();
    exposeApi();
    setBusy(false);
    setStreaming(false, null);

    try {
      await loadState();
    } catch (err) {
      console.error("[nova-chat-stream] bootstrap failed:", err);
      renderAll();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
  } else {
    bootstrap();
  }
})();