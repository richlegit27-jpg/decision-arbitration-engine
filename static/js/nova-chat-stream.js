(() => {
  "use strict";

  if (window.__novaChatStreamLoaded) return;
  window.__novaChatStreamLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.chat = Nova.chat || {};
  Nova.state = Nova.state || {};
  Nova.api = Nova.api || {};
  Nova.render = Nova.render || {};
  Nova.sessions = Nova.sessions || {};
  Nova.debug = Nova.debug || {};
  Nova.constants = Nova.constants || {};
  Nova.dom = Nova.dom || {};

  const state = Nova.state;
  const api = Nova.api;
  const sessions = Nova.sessions;
  const dom = Nova.dom;

  const byId = dom.byId || ((id) => document.getElementById(id));

  const STREAM_ENDPOINT =
    (api.API && api.API.stream) ||
    Nova.constants.STREAM_ENDPOINT ||
    "/api/chat/stream";

  function safeText(value) {
    if (Nova.utils && typeof Nova.utils.safeText === "function") {
      return Nova.utils.safeText(value);
    }
    return String(value ?? "").trim();
  }

  function nowUnix() {
    if (Nova.utils && typeof Nova.utils.nowUnix === "function") {
      return Nova.utils.nowUnix();
    }
    return Math.floor(Date.now() / 1000);
  }

  function setStatus(text) {
    if (api && typeof api.setStatus === "function") {
      api.setStatus(text);
      return;
    }
    if (Nova.utils && typeof Nova.utils.setStatus === "function") {
      Nova.utils.setStatus(text);
    }
  }

  function setSendingState(value) {
    if (Nova.utils && typeof Nova.utils.setSendingState === "function") {
      Nova.utils.setSendingState(value);
      return;
    }
    state.isSending = Boolean(value);
  }

  function autosizeInput() {
    if (Nova.utils && typeof Nova.utils.autosizeInput === "function") {
      Nova.utils.autosizeInput();
    }
  }

  function scrollChatToBottom() {
    if (Nova.utils && typeof Nova.utils.scrollChatToBottom === "function") {
      Nova.utils.scrollChatToBottom();
    }
  }

  function updateLastUserMessage() {
    if (Nova.utils && typeof Nova.utils.updateLastUserMessage === "function") {
      Nova.utils.updateLastUserMessage();
    }
  }

  function renderMessages() {
    if (Nova.render && typeof Nova.render.renderMessages === "function") {
      Nova.render.renderMessages();
    }
  }

  function renderAttachedFiles() {
    if (Nova.render && typeof Nova.render.renderAttachedFiles === "function") {
      Nova.render.renderAttachedFiles();
    }
  }

  function getInputEl() {
    return byId("messageInput");
  }

  function getCurrentInputValue() {
    return String(getInputEl()?.value ?? "");
  }

  function clearComposer() {
    const input = getInputEl();
    if (input) {
      input.value = "";
      autosizeInput();
    }
  }

  function getSessionId() {
    return safeText(state.activeSessionId || "");
  }

  function ensureSessionUpsert(sessionId, fallbackTitle = "New chat") {
    const id = safeText(sessionId);
    if (!id) return;

    const existing = Array.isArray(state.sessions)
      ? state.sessions.find((item) => safeText(item.id) === id)
      : null;

    const preview = safeText(
      [...(state.messages || [])]
        .reverse()
        .find((msg) => safeText(msg.content))
        ?.content || ""
    ).slice(0, 140);

    const payload = {
      id,
      title: safeText(existing?.title || fallbackTitle) || "New chat",
      preview,
      updated_at: Date.now(),
      message_count: Array.isArray(state.messages) ? state.messages.length : 0,
      pinned: Boolean(existing?.pinned),
    };

    if (sessions && typeof sessions.upsertSession === "function") {
      sessions.upsertSession(payload);
      return;
    }

    const current = Array.isArray(state.sessions) ? [...state.sessions] : [];
    const index = current.findIndex((item) => safeText(item.id) === id);

    if (index >= 0) current[index] = { ...current[index], ...payload };
    else current.unshift(payload);

    state.sessions = current;
  }

  function createUserMessage(content) {
    return {
      role: "user",
      content: String(content ?? ""),
      timestamp: nowUnix(),
      router: null,
      web_results: [],
    };
  }

  function createAssistantPlaceholder() {
    return {
      role: "assistant",
      content: "",
      timestamp: nowUnix(),
      router: null,
      web_results: [],
    };
  }

  function appendUserMessage(content) {
    const message = createUserMessage(content);
    state.messages = [...(Array.isArray(state.messages) ? state.messages : []), message];
    renderMessages();
    updateLastUserMessage();
    return state.messages.length - 1;
  }

  function appendAssistantPlaceholder() {
    const message = createAssistantPlaceholder();
    state.messages = [...(Array.isArray(state.messages) ? state.messages : []), message];
    renderMessages();
    return state.messages.length - 1;
  }

  function getAssistantMessage(index) {
    return Array.isArray(state.messages) ? state.messages[index] : null;
  }

  function setAssistantContent(index, content) {
    if (!Array.isArray(state.messages) || !state.messages[index]) return;

    state.messages[index] = {
      ...state.messages[index],
      role: "assistant",
      content: String(content ?? ""),
    };

    renderMessages();
  }

  function appendAssistantDelta(index, delta) {
    if (!Array.isArray(state.messages) || !state.messages[index]) return;

    const current = String(state.messages[index].content ?? "");
    state.messages[index] = {
      ...state.messages[index],
      role: "assistant",
      content: current + String(delta ?? ""),
    };

    renderMessages();
  }

  function applyAssistantMeta(index, meta = {}) {
    if (!Array.isArray(state.messages) || !state.messages[index]) return;

    const router =
      meta.router ??
      meta.route ??
      state.messages[index].router ??
      null;

    const webResults = Array.isArray(meta.web_results)
      ? meta.web_results
      : Array.isArray(meta.webResults)
      ? meta.webResults
      : Array.isArray(state.messages[index].web_results)
      ? state.messages[index].web_results
      : [];

    const timestamp =
      meta.timestamp ??
      meta.created_at ??
      meta.createdAt ??
      state.messages[index].timestamp ??
      nowUnix();

    state.messages[index] = {
      ...state.messages[index],
      role: "assistant",
      router,
      web_results: webResults,
      timestamp,
    };

    if (
      router &&
      Nova.debug &&
      typeof Nova.debug.applyIncomingRouterMeta === "function"
    ) {
      try {
        Nova.debug.applyIncomingRouterMeta(router);
      } catch (err) {
        console.warn("Router meta apply failed:", err);
      }
    }

    renderMessages();
  }

  function removeTrailingAssistantPlaceholderIfEmpty(index) {
    if (!Array.isArray(state.messages) || index < 0) return;

    const item = state.messages[index];
    if (!item) return;

    const isAssistant = safeText(item.role).toLowerCase() === "assistant";
    const isEmpty = !safeText(item.content);

    if (isAssistant && isEmpty) {
      state.messages.splice(index, 1);
      renderMessages();
    }
  }

  function extractFinalAssistantPayload(payload) {
    const value = payload && typeof payload === "object" ? payload : {};

    return {
      content:
        value.content ??
        value.message ??
        value.text ??
        value.reply ??
        null,
      router:
        value.router ??
        value.route ??
        null,
      web_results:
        value.web_results ??
        value.webResults ??
        value.sources ??
        [],
      session_id:
        value.session_id ??
        value.sessionId ??
        null,
      title:
        value.title ??
        value.session_title ??
        null,
      timestamp:
        value.timestamp ??
        value.created_at ??
        value.createdAt ??
        null,
    };
  }

  function splitSseChunks(buffer) {
    const normalized = String(buffer || "").replace(/\r\n/g, "\n");
    return normalized.split("\n\n");
  }

  function parseSseEvent(rawBlock) {
    const lines = String(rawBlock || "").split("\n");
    let event = "message";
    const dataLines = [];

    for (const line of lines) {
      if (line.startsWith("event:")) {
        event = safeText(line.slice(6)) || "message";
        continue;
      }
      if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }

    const rawData = dataLines.join("\n").trim();
    let data = rawData;

    if (rawData) {
      try {
        data = JSON.parse(rawData);
      } catch {
        data = rawData;
      }
    }

    return { event, data, raw: rawData };
  }

  async function ensureSessionForSend() {
    const currentId = getSessionId();
    if (currentId) return currentId;

    if (sessions && typeof sessions.createSession === "function") {
      const created = await sessions.createSession();
      const newId = safeText(created?.id || state.activeSessionId || "");
      if (newId) return newId;
    }

    const fallbackId = safeText(state.activeSessionId || "");
    if (!fallbackId) {
      throw new Error("No active session available");
    }
    return fallbackId;
  }

  function buildStreamPayload({ content, sessionId, regenerate = false }) {
    const payload = {
      content: String(content ?? ""),
      session_id: safeText(sessionId || ""),
      model: safeText(state.currentModel || ""),
    };

    if (regenerate) {
      payload.regenerate = true;
    }

    const attachedFiles = Array.isArray(state.attachedFiles) ? state.attachedFiles : [];
    if (attachedFiles.length) {
      payload.files = attachedFiles.map((file) => ({
        name: safeText(file?.name || ""),
        size: Number(file?.size || 0) || 0,
        type: safeText(file?.type || ""),
      }));
    }

    return payload;
  }

  async function streamSend({ content, regenerate = false } = {}) {
    const messageText = String(content ?? "");
    const trimmed = safeText(messageText);

    if (state.isSending) return;
    if (!regenerate && !trimmed) return;

    let assistantIndex = -1;

    try {
      setSendingState(true);
      setStatus(regenerate ? "Regenerating..." : "Sending...");

      const sessionId = await ensureSessionForSend();

      if (regenerate) {
        assistantIndex = appendAssistantPlaceholder();
      } else {
        appendUserMessage(messageText);
        assistantIndex = appendAssistantPlaceholder();
        clearComposer();
        state.attachedFiles = [];
        renderAttachedFiles();
      }

      ensureSessionUpsert(sessionId);

      const response = await fetch(STREAM_ENDPOINT, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          Accept: "text/event-stream",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(buildStreamPayload({
          content: messageText,
          sessionId,
          regenerate,
        })),
      });

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(safeText(text) || `${response.status} ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error("Streaming response body missing");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let doneReceived = false;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = splitSseChunks(buffer);
        buffer = parts.pop() || "";

        for (const rawPart of parts) {
          const part = safeText(rawPart);
          if (!part) continue;

          const parsed = parseSseEvent(rawPart);
          const eventName = safeText(parsed.event).toLowerCase();
          const data = parsed.data;

          if (eventName === "start") {
            if (data && typeof data === "object") {
              const payload = extractFinalAssistantPayload(data);
              const nextSessionId = safeText(payload.session_id || sessionId);
              if (nextSessionId && nextSessionId !== safeText(state.activeSessionId)) {
                state.activeSessionId = nextSessionId;
                if (sessions && typeof sessions.setActiveSessionId === "function") {
                  sessions.setActiveSessionId(nextSessionId);
                }
              }
              applyAssistantMeta(assistantIndex, payload);
              ensureSessionUpsert(nextSessionId, payload.title || "New chat");
            }
            continue;
          }

          if (eventName === "delta") {
            if (typeof data === "string") {
              appendAssistantDelta(assistantIndex, data);
            } else if (data && typeof data === "object") {
              const deltaText =
                data.delta ??
                data.content ??
                data.text ??
                "";
              if (deltaText) appendAssistantDelta(assistantIndex, deltaText);
              applyAssistantMeta(assistantIndex, data);
            }
            scrollChatToBottom();
            continue;
          }

          if (eventName === "done") {
            doneReceived = true;

            if (data && typeof data === "object") {
              const payload = extractFinalAssistantPayload(data);

              if (payload.content !== null && payload.content !== undefined) {
                setAssistantContent(assistantIndex, payload.content);
              }

              applyAssistantMeta(assistantIndex, payload);

              const nextSessionId = safeText(payload.session_id || sessionId);
              if (nextSessionId) {
                if (sessions && typeof sessions.setActiveSessionId === "function") {
                  sessions.setActiveSessionId(nextSessionId);
                } else {
                  state.activeSessionId = nextSessionId;
                }
                ensureSessionUpsert(nextSessionId, payload.title || "New chat");
              }
            }

            continue;
          }

          if (eventName === "error") {
            const message =
              typeof data === "string"
                ? data
                : safeText(data?.error || data?.message || "Streaming failed");
            throw new Error(message || "Streaming failed");
          }

          if (eventName === "message") {
            if (typeof data === "string" && data) {
              appendAssistantDelta(assistantIndex, data);
              scrollChatToBottom();
            } else if (data && typeof data === "object") {
              const payload = extractFinalAssistantPayload(data);

              if (payload.content !== null && payload.content !== undefined) {
                setAssistantContent(assistantIndex, payload.content);
              } else {
                const maybeDelta =
                  data.delta ??
                  data.text ??
                  "";
                if (maybeDelta) {
                  appendAssistantDelta(assistantIndex, maybeDelta);
                }
              }

              applyAssistantMeta(assistantIndex, payload);

              const nextSessionId = safeText(payload.session_id || sessionId);
              if (nextSessionId) {
                ensureSessionUpsert(nextSessionId, payload.title || "New chat");
              }

              scrollChatToBottom();
            }
          }
        }
      }

      const tail = safeText(buffer);
      if (tail) {
        const parsed = parseSseEvent(buffer);
        const eventName = safeText(parsed.event).toLowerCase();
        const data = parsed.data;

        if (eventName === "done" && data && typeof data === "object") {
          doneReceived = true;
          const payload = extractFinalAssistantPayload(data);

          if (payload.content !== null && payload.content !== undefined) {
            setAssistantContent(assistantIndex, payload.content);
          }

          applyAssistantMeta(assistantIndex, payload);

          const nextSessionId = safeText(payload.session_id || sessionId);
          if (nextSessionId) {
            if (sessions && typeof sessions.setActiveSessionId === "function") {
              sessions.setActiveSessionId(nextSessionId);
            } else {
              state.activeSessionId = nextSessionId;
            }
            ensureSessionUpsert(nextSessionId, payload.title || "New chat");
          }
        }
      }

      if (!doneReceived) {
        const current = getAssistantMessage(assistantIndex);
        if (!safeText(current?.content)) {
          throw new Error("No assistant response received");
        }
      }

      updateLastUserMessage();
      ensureSessionUpsert(getSessionId());
      setStatus("Ready");
      return true;
    } catch (err) {
      console.error("Nova chat stream failed:", err);

      if (assistantIndex >= 0) {
        const current = getAssistantMessage(assistantIndex);
        if (!safeText(current?.content)) {
          setAssistantContent(assistantIndex, `Error: ${safeText(err?.message || "Send failed")}`);
        }
      }

      if (regenerate && assistantIndex >= 0) {
        const current = getAssistantMessage(assistantIndex);
        if (!safeText(current?.content)) {
          removeTrailingAssistantPlaceholderIfEmpty(assistantIndex);
        }
      }

      setStatus(safeText(err?.message || "Send failed"));
      return false;
    } finally {
      setSendingState(false);
      updateLastUserMessage();
      scrollChatToBottom();
      ensureSessionUpsert(getSessionId());
    }
  }

  async function sendMessage() {
    const raw = getCurrentInputValue();
    const trimmed = safeText(raw);

    if (!trimmed) return false;
    return streamSend({ content: raw, regenerate: false });
  }

  async function regenerateLastReply() {
    if (state.isSending) return false;

    const fallback = safeText(state.lastUserMessage || "");
    if (!fallback) return false;

    return streamSend({
      content: fallback,
      regenerate: true,
    });
  }

  Nova.chat = {
    ...Nova.chat,
    streamSend,
    sendMessage,
    regenerateLastReply,
  };
})();