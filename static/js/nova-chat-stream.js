(() => {
  "use strict";

  if (window.__novaChatStreamLoaded) return;
  window.__novaChatStreamLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.chat = Nova.chat || {};

  const API = {
    newSession: "/api/session/new",
    stream: "/api/chat/stream",
    state: "/api/state",
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function getStateBucket() {
    Nova.state = Nova.state || {};
    if (!Array.isArray(Nova.state.messages)) Nova.state.messages = [];
    if (!Array.isArray(Nova.state.sessions)) Nova.state.sessions = [];
    if (typeof Nova.state.activeSessionId !== "string") {
      Nova.state.activeSessionId = "";
    }
    if (typeof Nova.state.isStreaming !== "boolean") {
      Nova.state.isStreaming = false;
    }
    return Nova.state;
  }

  function getActiveModel() {
    const modelSelect = byId("modelSelect");
    const selected = modelSelect ? String(modelSelect.value || "").trim() : "";
    return selected || "gpt-5.4";
  }

  function getComposer() {
    return byId("composerInput");
  }

  function getSendBtn() {
    return byId("sendBtn");
  }

  function getMessagesApi() {
    return Nova.messages && typeof Nova.messages === "object" ? Nova.messages : null;
  }

  function getSessionsApi() {
    return Nova.sessions && typeof Nova.sessions === "object" ? Nova.sessions : null;
  }

  function makeId(prefix) {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function resolveSessionId(payload) {
    return String(
      payload?.session_id ||
      payload?.id ||
      payload?.session?.id ||
      payload?.data?.session_id ||
      payload?.data?.id ||
      ""
    ).trim();
  }

  function resolveMessages(payload) {
    const candidates = [
      payload?.messages,
      payload?.chat?.messages,
      payload?.session?.messages,
      payload?.data?.messages,
      payload?.items,
    ];

    for (const value of candidates) {
      if (Array.isArray(value)) return value;
    }

    return [];
  }

  function findSessionInState(sessionId) {
    const state = getStateBucket();
    return (state.sessions || []).find((item) => {
      const id = String(item?.id || item?.session_id || item?.uuid || "").trim();
      return id === String(sessionId || "").trim();
    });
  }

  async function parseJsonSafe(response) {
    const text = await response.text();
    try {
      return text ? JSON.parse(text) : {};
    } catch {
      return {};
    }
  }

  async function apiGet(url) {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      credentials: "same-origin",
    });

    const data = await parseJsonSafe(response);
    if (!response.ok) {
      throw new Error(data.error || `GET failed: ${url}`);
    }
    return data;
  }

  async function apiPost(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      credentials: "same-origin",
      body: JSON.stringify(payload || {}),
    });

    const data = await parseJsonSafe(response);
    if (!response.ok) {
      throw new Error(data.error || `POST failed: ${url}`);
    }
    return data;
  }

  function setStreamingUi(isStreaming) {
    const state = getStateBucket();
    const sendBtn = getSendBtn();
    const composer = getComposer();

    state.isStreaming = !!isStreaming;

    if (sendBtn) {
      sendBtn.disabled = !!isStreaming;
      sendBtn.textContent = isStreaming ? "Sending..." : "Send";
    }

    if (composer) {
      composer.disabled = !!isStreaming;
    }
  }

  function renderNow() {
    const messagesApi = getMessagesApi();
    if (messagesApi && typeof messagesApi.render === "function") {
      messagesApi.render();
    }
  }

  function scrollMessagesToBottom() {
    const chatMessages = byId("chatMessages");
    if (!chatMessages) return;

    requestAnimationFrame(() => {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    });
  }

  function upsertLocalUserMessage(text) {
    const state = getStateBucket();
    const message = {
      id: makeId("user"),
      role: "user",
      content: String(text || ""),
      created_at: new Date().toISOString(),
    };

    state.messages = Array.isArray(state.messages) ? state.messages : [];
    state.messages.push(message);
    renderNow();
    scrollMessagesToBottom();

    return message;
  }

  function addStreamingAssistantPlaceholder() {
    const state = getStateBucket();
    const assistant = {
      id: makeId("assistant"),
      role: "assistant",
      content: "",
      created_at: new Date().toISOString(),
      _streaming: true,
    };

    state.messages = Array.isArray(state.messages) ? state.messages : [];
    state.messages.push(assistant);
    renderNow();
    scrollMessagesToBottom();

    return assistant;
  }

  function removeStreamingAssistantIfEmpty(messageId) {
    const state = getStateBucket();
    state.messages = (state.messages || []).filter((item) => {
      const id = String(item?.id || item?.message_id || "").trim();
      const content = String(item?.content || item?.text || "").trim();
      if (id !== String(messageId || "").trim()) return true;
      return !!content;
    });
    renderNow();
  }

  function updateAssistantStream(messageId, delta, mode = "append") {
    const state = getStateBucket();
    const messages = Array.isArray(state.messages) ? state.messages : [];
    const target = messages.find((item) => String(item?.id || "").trim() === String(messageId || "").trim());
    if (!target) return;

    if (mode === "replace") {
      target.content = String(delta || "");
    } else {
      target.content = String(target.content || "") + String(delta || "");
    }

    target.updated_at = new Date().toISOString();
    renderNow();
    scrollMessagesToBottom();
  }

  function finalizeAssistantMessage(messageId, finalText = null) {
    const state = getStateBucket();
    const messages = Array.isArray(state.messages) ? state.messages : [];
    const target = messages.find((item) => String(item?.id || "").trim() === String(messageId || "").trim());
    if (!target) return;

    if (typeof finalText === "string" && finalText.length) {
      target.content = finalText;
    }

    delete target._streaming;
    target.updated_at = new Date().toISOString();

    renderNow();
    scrollMessagesToBottom();
  }

  function normalizeEventName(raw) {
    const value = String(raw || "").trim().toLowerCase();
    if (!value) return "message";
    return value;
  }

  function parseSseBuffer(buffer) {
    const events = [];
    const chunks = buffer.split(/\n\n/);
    const remainder = chunks.pop() || "";

    for (const chunk of chunks) {
      const lines = chunk.split(/\n/);
      let eventName = "message";
      const dataLines = [];

      for (const line of lines) {
        if (line.startsWith("event:")) {
          eventName = normalizeEventName(line.slice(6));
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trimStart());
        }
      }

      const rawData = dataLines.join("\n");
      let parsedData = rawData;

      try {
        parsedData = rawData ? JSON.parse(rawData) : {};
      } catch {
        parsedData = rawData;
      }

      events.push({
        event: eventName,
        data: parsedData,
        raw: rawData,
      });
    }

    return { events, remainder };
  }

  function extractDelta(payload) {
    if (typeof payload === "string") return payload;

    return String(
      payload?.delta ??
      payload?.content ??
      payload?.text ??
      payload?.token ??
      payload?.message ??
      payload?.data?.delta ??
      payload?.data?.content ??
      ""
    );
  }

  function extractDoneText(payload) {
    if (typeof payload === "string") return payload;

    return String(
      payload?.final ??
      payload?.content ??
      payload?.text ??
      payload?.message ??
      payload?.response ??
      payload?.data?.final ??
      payload?.data?.content ??
      ""
    );
  }

  async function ensureSession() {
    const state = getStateBucket();
    if (state.activeSessionId) {
      return state.activeSessionId;
    }

    const created = await apiPost(API.newSession, {});
    const sessionId = resolveSessionId(created);

    if (!sessionId) {
      throw new Error("Could not create session.");
    }

    state.activeSessionId = sessionId;

    const sessionsApi = getSessionsApi();
    if (sessionsApi && typeof sessionsApi.refresh === "function") {
      try {
        await sessionsApi.refresh();
      } catch (error) {
        console.error("Nova session refresh after create failed:", error);
      }
    }

    return sessionId;
  }

  async function refreshStateSessions() {
    const state = getStateBucket();

    try {
      const payload = await apiGet(API.state);
      const sessions =
        payload?.sessions ||
        payload?.data?.sessions ||
        payload?.items ||
        payload?.data?.items ||
        [];

      if (Array.isArray(sessions)) {
        state.sessions = sessions;
      }
    } catch (error) {
      console.error("Nova state refresh failed:", error);
    }
  }

  async function loadSession(sessionId) {
    const id = String(sessionId || "").trim();
    const state = getStateBucket();
    state.activeSessionId = id;

    const messagesApi = getMessagesApi();
    if (messagesApi && typeof messagesApi.loadSession === "function") {
      return messagesApi.loadSession(id);
    }

    return [];
  }

  function buildStreamPayload(options) {
    const state = getStateBucket();
    const prompt = String(options?.prompt || "").trim();
    const sessionId = String(options?.sessionId || state.activeSessionId || "").trim();
    const model = String(options?.model || getActiveModel()).trim();

    const payload = {
      session_id: sessionId,
      content: prompt,
      model,
    };

    if (options?.regenerate) {
      payload.regenerate = true;
      payload.prompt_override = prompt;
      payload.promptOverride = prompt;
    }

    return payload;
  }

  async function streamRequest(payload, onEvent) {
    const response = await fetch(API.stream, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream, application/json, text/plain",
      },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      let errorMessage = `POST failed: ${API.stream}`;

      try {
        const parsed = text ? JSON.parse(text) : {};
        errorMessage = parsed.error || errorMessage;
      } catch {
        if (text) errorMessage = text;
      }

      throw new Error(errorMessage);
    }

    if (!response.body) {
      throw new Error("Streaming response body missing.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const parsed = parseSseBuffer(buffer);
      buffer = parsed.remainder;

      for (const entry of parsed.events) {
        onEvent(entry);
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) {
      const parsed = parseSseBuffer(buffer + "\n\n");
      for (const entry of parsed.events) {
        onEvent(entry);
      }
    }
  }

  async function sendMessage(options = {}) {
    const state = getStateBucket();
    if (state.isStreaming) return false;

    const composer = getComposer();
    const rawPrompt =
      typeof options.promptOverride === "string"
        ? options.promptOverride
        : composer
          ? String(composer.value || "")
          : "";

    const prompt = String(rawPrompt || "").trim();
    if (!prompt) return false;

    const isRegenerate = !!options.regenerate;
    let sessionId = String(state.activeSessionId || "").trim();
    let assistantPlaceholderId = "";
    let sawAssistantContent = false;
    let finalTextFromDone = "";

    try {
      setStreamingUi(true);

      sessionId = await ensureSession();
      state.activeSessionId = sessionId;

      if (!isRegenerate) {
        upsertLocalUserMessage(prompt);
        if (composer) {
          composer.value = "";
          composer.style.height = "";
        }
      }

      const assistantPlaceholder = addStreamingAssistantPlaceholder();
      assistantPlaceholderId = assistantPlaceholder.id;

      const payload = buildStreamPayload({
        sessionId,
        prompt,
        model: options.model,
        regenerate: isRegenerate,
      });

      await streamRequest(payload, (entry) => {
        const eventName = normalizeEventName(entry.event);
        const data = entry.data;

        if (eventName === "start") {
          const incomingSessionId = resolveSessionId(data);
          if (incomingSessionId) {
            state.activeSessionId = incomingSessionId;
            sessionId = incomingSessionId;
          }

          const maybeMessages = resolveMessages(data);
          if (maybeMessages.length) {
            state.messages = maybeMessages;
            renderNow();
            scrollMessagesToBottom();
          }
          return;
        }

        if (eventName === "delta" || eventName === "message" || eventName === "token") {
          const delta = extractDelta(data);
          if (!delta) return;

          sawAssistantContent = true;
          updateAssistantStream(assistantPlaceholderId, delta, "append");
          return;
        }

        if (eventName === "replace") {
          const nextText = extractDelta(data);
          sawAssistantContent = !!nextText;
          updateAssistantStream(assistantPlaceholderId, nextText, "replace");
          return;
        }

        if (eventName === "done") {
          finalTextFromDone = extractDoneText(data) || finalTextFromDone;
          return;
        }

        if (eventName === "error") {
          const message =
            typeof data === "string"
              ? data
              : String(data?.error || data?.message || "Streaming error.");
          throw new Error(message);
        }
      });

      if (assistantPlaceholderId) {
        if (finalTextFromDone) {
          finalizeAssistantMessage(assistantPlaceholderId, finalTextFromDone);
        } else {
          finalizeAssistantMessage(assistantPlaceholderId);
        }

        if (!sawAssistantContent && !finalTextFromDone) {
          removeStreamingAssistantIfEmpty(assistantPlaceholderId);
        }
      }

      const sessionsApi = getSessionsApi();
      if (sessionsApi && typeof sessionsApi.refresh === "function") {
        try {
          await sessionsApi.refresh();
        } catch (error) {
          console.error("Nova sessions refresh after stream failed:", error);
        }
      } else {
        await refreshStateSessions();
      }

      return true;
    } catch (error) {
      console.error("Nova stream send failed:", error);

      if (assistantPlaceholderId) {
        removeStreamingAssistantIfEmpty(assistantPlaceholderId);
      }

      const stateRef = getStateBucket();
      stateRef.messages.push({
        id: makeId("system"),
        role: "system",
        content: `Error: ${String(error?.message || error || "Request failed.")}`,
        created_at: new Date().toISOString(),
      });
      renderNow();
      scrollMessagesToBottom();

      return false;
    } finally {
      setStreamingUi(false);
    }
  }

  async function regenerateLast(prompt) {
    const value = String(prompt || "").trim();
    if (!value) return false;

    return sendMessage({
      regenerate: true,
      promptOverride: value,
    });
  }

  function bindComposerAutoSize() {
    const composer = getComposer();
    if (!composer || composer.__novaAutoSizeBound) return;

    composer.__novaAutoSizeBound = true;

    const resize = () => {
      composer.style.height = "auto";
      const next = Math.min(composer.scrollHeight, 160);
      composer.style.height = `${Math.max(next, 42)}px`;
    };

    composer.addEventListener("input", resize);
    window.addEventListener("resize", resize);
    resize();
  }

  async function bootstrap() {
    bindComposerAutoSize();
    return true;
  }

  Nova.chat.sendMessage = sendMessage;
  Nova.chat.regenerateLast = regenerateLast;
  Nova.chat.loadSession = loadSession;
  Nova.chat.bootstrap = bootstrap;

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      () => {
        bootstrap().catch((error) => {
          console.error("Nova chat DOM bootstrap failed:", error);
        });
      },
      { once: true }
    );
  } else {
    bootstrap().catch((error) => {
      console.error("Nova chat immediate bootstrap failed:", error);
    });
  }
})();