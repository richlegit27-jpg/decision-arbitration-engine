(() => {
  "use strict";

  if (window.__novaChatLoaded) {
    console.warn("Nova chat already loaded. Skipping duplicate module.");
    return;
  }
  window.__novaChatLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  const state = (Nova.state = Nova.state || {});
  const dom = (Nova.dom = Nova.dom || {});
  const api = (Nova.api = Nova.api || {});
  const chat = (Nova.chat = Nova.chat || {});
  const sessions = (Nova.sessions = Nova.sessions || {});
  const render = (Nova.render = Nova.render || {});
  const util = (Nova.util = Nova.util || {});

  const API = {
    stream: "/api/chat/stream",
    newSession: "/api/session/new",
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function asString(value, fallback = "") {
    return typeof value === "string" ? value : fallback;
  }

  function safeJsonParse(text, fallback = null) {
    if (typeof util.safeJsonParse === "function") {
      return util.safeJsonParse(text, fallback);
    }
    try {
      return JSON.parse(text);
    } catch (_) {
      return fallback;
    }
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function extractMessageText(message) {
    if (typeof util.extractMessageText === "function") {
      return util.extractMessageText(message);
    }

    if (!message) return "";
    if (typeof message.content === "string") return message.content;
    if (typeof message.text === "string") return message.text;

    if (Array.isArray(message.content)) {
      return message.content
        .map((part) => {
          if (typeof part === "string") return part;
          if (part && typeof part.text === "string") return part.text;
          if (part && typeof part.content === "string") return part.content;
          return "";
        })
        .filter(Boolean)
        .join("\n");
    }

    return "";
  }

  function cacheDom() {
    dom.composerInput = dom.composerInput || byId("composerInput");
    dom.sendBtn = dom.sendBtn || byId("sendBtn");
    dom.regenerateBtn = dom.regenerateBtn || byId("regenerateBtn");
    dom.voiceBtn = dom.voiceBtn || byId("voiceBtn");
    dom.attachBtn = dom.attachBtn || byId("attachBtn");
    dom.fileInput = dom.fileInput || byId("fileInput");
    dom.attachmentBar = dom.attachmentBar || byId("attachmentBar");
    dom.routerBadge = dom.routerBadge || byId("routerBadge");
    return dom;
  }

  function autosizeComposer() {
    if (typeof util.autosizeComposer === "function") {
      util.autosizeComposer();
      return;
    }

    cacheDom();
    if (!dom.composerInput) return;
    dom.composerInput.style.height = "auto";
    dom.composerInput.style.height = `${Math.min(Math.max(dom.composerInput.scrollHeight, 44), 220)}px`;
  }

  function renderAllSafe() {
    if (typeof render.all === "function") {
      render.all();
    } else if (typeof render.messagesImpl === "function") {
      render.messagesImpl();
    }
  }

  function setRouterBadge(label, tone = "neutral") {
    cacheDom();
    state.lastRouter = {
      ...(state.lastRouter || {}),
      label: asString(label, "Ready"),
      tone: asString(tone, "neutral"),
    };

    if (dom.routerBadge) {
      dom.routerBadge.textContent = state.lastRouter.label;
      dom.routerBadge.dataset.tone = state.lastRouter.tone;
    }
  }

  function setSendingUi(flag) {
    state.isSending = !!flag;
    renderAllSafe();
  }

  function normalizeAttachments(list) {
    return asArray(list)
      .map((item, index) => {
        if (!item) return null;

        if (item instanceof File) {
          return {
            id: item.name ? `file-${Date.now()}-${index}` : `file-${index}`,
            name: item.name || `file-${index + 1}`,
            filename: item.name || `file-${index + 1}`,
            type: item.type || "",
            size: Number(item.size || 0) || 0,
          };
        }

        if (typeof item !== "object") {
          return {
            id: `file-${Date.now()}-${index}`,
            name: `file-${index + 1}`,
            filename: `file-${index + 1}`,
            type: "",
            size: 0,
          };
        }

        return {
          id: item.id || `file-${Date.now()}-${index}`,
          name: item.name || item.filename || `file-${index + 1}`,
          filename: item.filename || item.name || `file-${index + 1}`,
          type: item.type || item.mime_type || "",
          size: Number(item.size || 0) || 0,
          url: item.url || item.file_url || "",
        };
      })
      .filter(Boolean);
  }

  function buildLocalUserMessage(content, attachments) {
    const message = {
      id: `user-local-${Date.now()}`,
      role: "user",
      content: asString(content, ""),
      created_at: nowIso(),
    };

    if (attachments.length) {
      message.attachments = attachments;
    }

    return message;
  }

  function buildStreamingAssistantMessage() {
    return {
      id: `assistant-stream-${Date.now()}`,
      role: "assistant",
      content: "",
      created_at: nowIso(),
      __streaming: true,
    };
  }

  function persistUiStateSafe() {
    if (typeof util.persistUiState === "function") {
      util.persistUiState();
    }
  }

  async function createSessionIfNeeded() {
    if (state.activeSessionId) return state.activeSessionId;

    if (typeof sessions.create === "function") {
      const maybe = await sessions.create();
      if (state.activeSessionId) return state.activeSessionId;
      if (typeof maybe === "string" && maybe) return maybe;
    }

    if (typeof api.post === "function") {
      const data = await api.post(API.newSession, { title: "New Chat" });
      const sessionId = asString(data?.session_id || data?.session?.id, "");
      if (sessionId) {
        state.activeSessionId = sessionId;
        return sessionId;
      }
    }

    throw new Error("Could not create a chat session.");
  }

  async function refreshAfterSend(sessionId) {
    if (typeof api.get === "function") {
      try {
        const stateData = await api.get("/api/state");
        state.sessions = asArray(stateData?.sessions);
        state.memoryItems = asArray(stateData?.memory || stateData?.items || state.memoryItems);
      } catch (error) {
        console.warn("State refresh after send failed:", error);
      }
    }

    if (sessionId && typeof sessions.load === "function") {
      try {
        await sessions.load(sessionId);
        return;
      } catch (error) {
        console.warn("Session reload after send failed:", error);
      }
    }

    renderAllSafe();
  }

  function finalizeStreamingAssistant(finalText, fallbackMessage) {
    const text = asString(finalText, "").trimEnd();
    const messages = asArray(state.messages);
    const last = messages[messages.length - 1];

    if (last && last.role === "assistant" && last.__streaming) {
      last.content = text || asString(last.content, "");
      delete last.__streaming;
      state.lastAssistantMessage = asString(last.content, "");
      return;
    }

    if (fallbackMessage && typeof fallbackMessage === "object") {
      const cloned = { ...fallbackMessage };
      delete cloned.__streaming;
      cloned.content = text || asString(cloned.content, "");
      state.messages.push(cloned);
      state.lastAssistantMessage = asString(cloned.content, "");
      return;
    }

    if (text) {
      state.messages.push({
        id: `assistant-final-${Date.now()}`,
        role: "assistant",
        content: text,
        created_at: nowIso(),
      });
      state.lastAssistantMessage = text;
    }
  }

  async function parseSseStream(response) {
    if (!response.body) {
      throw new Error("Streaming response body missing.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let assistantText = "";
    let assistantMessage = null;

    const ensureAssistant = () => {
      const last = state.messages[state.messages.length - 1];
      if (last && last.role === "assistant" && last.__streaming) {
        assistantMessage = last;
        return last;
      }

      assistantMessage = buildStreamingAssistantMessage();
      state.messages.push(assistantMessage);
      return assistantMessage;
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        const lines = block.split("\n");
        let eventName = "message";
        const dataLines = [];

        for (const line of lines) {
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trim());
          }
        }

        const rawData = dataLines.join("\n");
        const data = safeJsonParse(rawData, {});

        if (eventName === "start") {
          const incomingSessionId = asString(data?.session_id, "");
          if (incomingSessionId) {
            state.activeSessionId = incomingSessionId;
          }
          continue;
        }

        if (eventName === "delta") {
          const delta = asString(data?.delta, "");
          if (!delta) continue;

          assistantText += delta;
          const msg = ensureAssistant();
          msg.content = assistantText;
          renderAllSafe();
          continue;
        }

        if (eventName === "done") {
          assistantText = asString(data?.content, assistantText);
          finalizeStreamingAssistant(assistantText, data?.message || assistantMessage);
          renderAllSafe();
          continue;
        }

        if (eventName === "error") {
          throw new Error(asString(data?.error, "Stream error."));
        }
      }
    }

    if (buffer.trim()) {
      const trailing = safeJsonParse(buffer.trim(), null);
      if (trailing && typeof trailing === "object" && trailing.content) {
        assistantText = asString(trailing.content, assistantText);
      }
    }

    finalizeStreamingAssistant(assistantText, assistantMessage);
    renderAllSafe();

    return assistantText;
  }

  async function sendMessage(options = {}) {
    if (state.isSending) return;

    cacheDom();

    const useOverride = Object.prototype.hasOwnProperty.call(options, "content");
    const rawContent = useOverride ? options.content : dom.composerInput?.value;
    const content = asString(rawContent, "").trim();
    const attachments = normalizeAttachments(
      Object.prototype.hasOwnProperty.call(options, "attachments")
        ? options.attachments
        : state.attachedFiles
    );

    if (!content && !attachments.length) return;

    setSendingUi(true);
    setRouterBadge("Thinking...", "working");

    const localUserMessage = buildLocalUserMessage(content, attachments);

    try {
      const sessionId = await createSessionIfNeeded();
      state.activeSessionId = sessionId;
      state.lastUserMessage = content || state.lastUserMessage || "";

      state.messages = asArray(state.messages);
      state.messages.push(localUserMessage);

      if (dom.composerInput && !useOverride) {
        dom.composerInput.value = "";
        autosizeComposer();
      }

      state.attachedFiles = [];
      renderAllSafe();

      const payload = {
        session_id: sessionId,
        content,
        model: asString(state.currentModel, "gpt-5.4"),
        attachments,
        files: attachments,
      };

      const response = await fetch(API.stream, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        credentials: "same-origin",
      });

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        const data = text ? safeJsonParse(text, null) : null;
        throw new Error(
          asString(data?.error || data?.message, `Stream request failed: ${response.status}`)
        );
      }

      await parseSseStream(response);
      await refreshAfterSend(sessionId);
      setRouterBadge("Ready", "success");
      persistUiStateSafe();
    } catch (error) {
      console.error("Nova send failed:", error);
      setRouterBadge("Error", "danger");

      const text = error instanceof Error ? error.message : "Send failed.";
      state.messages.push({
        id: `system-error-${Date.now()}`,
        role: "system",
        content: text,
        created_at: nowIso(),
      });
      renderAllSafe();
    } finally {
      setSendingUi(false);
      persistUiStateSafe();
    }
  }

  async function regenerateLast() {
    if (state.isSending) return;

    const lastUser = asString(state.lastUserMessage, "").trim();
    if (!lastUser) return;

    cacheDom();
    if (dom.composerInput) {
      dom.composerInput.value = lastUser;
      autosizeComposer();
    }

    await sendMessage({
      content: lastUser,
      attachments: [],
    });
  }

  function handleFileSelection(event) {
    const files = Array.from(event?.target?.files || []);
    if (!files.length) return;

    const normalized = normalizeAttachments(files);
    state.attachedFiles = normalized;
    renderAllSafe();
  }

  function bind() {
    cacheDom();

    if (dom.composerInput && !dom.composerInput.__novaChatBound) {
      dom.composerInput.__novaChatBound = true;
      dom.composerInput.addEventListener("input", autosizeComposer);
      dom.composerInput.addEventListener("keydown", async (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          await sendMessage();
        }
      });
    }

    if (dom.sendBtn && !dom.sendBtn.__novaChatBound) {
      dom.sendBtn.__novaChatBound = true;
      dom.sendBtn.addEventListener("click", async () => {
        await sendMessage();
      });
    }

    if (dom.regenerateBtn && !dom.regenerateBtn.__novaChatBound) {
      dom.regenerateBtn.__novaChatBound = true;
      dom.regenerateBtn.addEventListener("click", async () => {
        await regenerateLast();
      });
    }

    if (dom.attachBtn && dom.fileInput && !dom.attachBtn.__novaChatBound) {
      dom.attachBtn.__novaChatBound = true;
      dom.attachBtn.addEventListener("click", () => {
        dom.fileInput.click();
      });
    }

    if (dom.fileInput && !dom.fileInput.__novaChatBound) {
      dom.fileInput.__novaChatBound = true;
      dom.fileInput.addEventListener("change", handleFileSelection);
    }

    if (dom.attachmentBar && !dom.attachmentBar.__novaChatBound) {
      dom.attachmentBar.__novaChatBound = true;
      dom.attachmentBar.addEventListener("click", (event) => {
        const button = event.target.closest("[data-remove-attachment]");
        if (!button) return;

        const index = Number(button.getAttribute("data-remove-attachment"));
        if (Number.isNaN(index)) return;

        state.attachedFiles = asArray(state.attachedFiles).filter((_, i) => i !== index);
        renderAllSafe();
      });
    }
  }

  chat.send = sendMessage;
  chat.regenerate = regenerateLast;
  chat.bind = bind;
  chat.normalizeAttachments = normalizeAttachments;

  bind();
})();