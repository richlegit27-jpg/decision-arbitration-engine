(() => {
  "use strict";

  if (window.__novaApiLoaded) return;
  window.__novaApiLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.api = Nova.api || {};

  const api = Nova.api;

  const DEFAULT_HEADERS = {
    Accept: "application/json",
  };

  const ROUTES = {
    state: "/api/state",
    memory: "/api/memory",
    addMemory: "/api/memory",
    deleteMemory: "/api/memory/delete",
    newSession: "/api/session/new",
    renameSession: "/api/session/rename",
    deleteSession: "/api/session/delete",
    duplicateSession: "/api/session/duplicate",
    pinSession: "/api/session/pin",
    getChat(sessionId) {
      return `/api/chat/${encodeURIComponent(sessionId)}`;
    },
    sendChat: "/api/chat/send",
    streamChat: "/api/chat/stream",
    upload: "/api/upload",
    models: "/api/models",
  };

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function safeString(value, fallback = "") {
    if (typeof value === "string") return value;
    if (value === null || value === undefined) return fallback;
    return String(value);
  }

  function tryParseJson(text) {
    if (!text || typeof text !== "string") return null;

    try {
      return JSON.parse(text);
    } catch (_error) {
      return null;
    }
  }

  async function readResponseBody(response) {
    const contentType = safeString(response.headers.get("content-type")).toLowerCase();

    if (contentType.includes("application/json")) {
      try {
        return await response.json();
      } catch (_error) {
        return null;
      }
    }

    try {
      const text = await response.text();
      const parsed = tryParseJson(text);
      return parsed !== null ? parsed : text;
    } catch (_error) {
      return null;
    }
  }

  function buildError(message, extra = {}) {
    const error = new Error(message || "Request failed");
    Object.assign(error, extra);
    return error;
  }

  async function request(url, options = {}) {
    const method = safeString(options.method || "GET").toUpperCase();
    const headers = {
      ...DEFAULT_HEADERS,
      ...(isObject(options.headers) ? options.headers : {}),
    };

    const fetchOptions = {
      method,
      headers,
      cache: "no-store",
    };

    if (options.signal) {
      fetchOptions.signal = options.signal;
    }

    if (options.body !== undefined) {
      fetchOptions.body = options.body;
    }

    let response;
    try {
      response = await fetch(url, fetchOptions);
    } catch (error) {
      throw buildError(`Network error: ${error?.message || "request failed"}`, {
        cause: error,
        url,
        method,
      });
    }

    const payload = await readResponseBody(response);

    if (!response.ok) {
      const payloadMessage =
        (isObject(payload) && safeString(payload.error || payload.message).trim()) ||
        (typeof payload === "string" ? payload.trim() : "");

      throw buildError(
        payloadMessage || `${method} failed: ${url}`,
        {
          status: response.status,
          statusText: response.statusText,
          url,
          method,
          payload,
        }
      );
    }

    return payload;
  }

  async function get(url, options = {}) {
    return request(url, {
      ...options,
      method: "GET",
    });
  }

  async function post(url, data = {}, options = {}) {
    return request(url, {
      ...options,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(isObject(options.headers) ? options.headers : {}),
      },
      body: JSON.stringify(isObject(data) ? data : {}),
    });
  }

  async function postForm(url, formData, options = {}) {
    return request(url, {
      ...options,
      method: "POST",
      body: formData,
    });
  }

  function normalizeStatePayload(payload) {
    if (!isObject(payload)) {
      return {
        ok: true,
        sessions: [],
        active_session_id: "",
        default_model: "gpt-5.4",
      };
    }

    return {
      ok: payload.ok !== false,
      sessions: Array.isArray(payload.sessions)
        ? payload.sessions
        : Array.isArray(payload.items)
          ? payload.items
          : Array.isArray(payload.data?.sessions)
            ? payload.data.sessions
            : [],
      active_session_id: safeString(
        payload.active_session_id ||
          payload.activeSessionId ||
          payload.session_id ||
          payload.sessionId ||
          ""
      ),
      default_model: safeString(
        payload.default_model ||
          payload.defaultModel ||
          payload.model ||
          payload.current_model ||
          payload.currentModel ||
          "gpt-5.4"
      ),
      raw: payload,
    };
  }

  function normalizeMemoryPayload(payload) {
    if (!isObject(payload)) {
      return {
        ok: true,
        items: [],
      };
    }

    return {
      ok: payload.ok !== false,
      items: Array.isArray(payload.items)
        ? payload.items
        : Array.isArray(payload.memory)
          ? payload.memory
          : Array.isArray(payload.data?.items)
            ? payload.data.items
            : [],
      raw: payload,
    };
  }

  function normalizeChatPayload(payload) {
    if (!isObject(payload)) {
      return {
        ok: true,
        session_id: "",
        messages: [],
        answer: typeof payload === "string" ? payload : "",
      };
    }

    const messages = Array.isArray(payload.messages)
      ? payload.messages
      : Array.isArray(payload.items)
        ? payload.items
        : Array.isArray(payload.data?.messages)
          ? payload.data.messages
          : [];

    return {
      ok: payload.ok !== false,
      session_id: safeString(
        payload.session_id ||
          payload.sessionId ||
          payload.id ||
          ""
      ),
      router: safeString(payload.router || payload.route || ""),
      messages,
      answer: safeString(payload.answer || payload.content || payload.message || ""),
      raw: payload,
    };
  }

  function normalizeModelsPayload(payload) {
    if (!isObject(payload)) {
      return {
        ok: true,
        models: ["gpt-5.4", "gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"],
        default_model: "gpt-5.4",
      };
    }

    const models = Array.isArray(payload.models)
      ? payload.models
      : Array.isArray(payload.items)
        ? payload.items
        : [];

    return {
      ok: payload.ok !== false,
      models,
      default_model: safeString(
        payload.default_model ||
          payload.defaultModel ||
          payload.model ||
          "gpt-5.4"
      ),
      raw: payload,
    };
  }

  function parseStreamEventBlock(block) {
    const lines = safeString(block)
      .split("\n")
      .map((line) => line.replace(/\r/g, ""));

    let eventName = "message";
    const dataLines = [];

    lines.forEach((line) => {
      if (!line) return;

      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim() || "message";
        return;
      }

      if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    });

    const dataText = dataLines.join("\n").trim();
    const data = tryParseJson(dataText);

    return {
      event: eventName,
      data: data !== null ? data : dataText,
      raw: block,
    };
  }

  async function getState() {
    const payload = await get(ROUTES.state);
    return normalizeStatePayload(payload);
  }

  async function getMemory() {
    const payload = await get(ROUTES.memory);
    return normalizeMemoryPayload(payload);
  }

  async function addMemory(data = {}) {
    const value = safeString(data.value || "").trim();
    const kind = safeString(data.kind || "preference").trim() || "preference";

    const payload = await post(ROUTES.addMemory, {
      value,
      kind,
    });

    return normalizeMemoryPayload(payload);
  }

  async function deleteMemory(memoryId) {
    const payload = await post(ROUTES.deleteMemory, {
      id: safeString(memoryId).trim(),
    });

    return normalizeMemoryPayload(payload);
  }

  async function createSession(data = {}) {
    const payload = await post(ROUTES.newSession, {
      title: safeString(data.title || "").trim(),
    });

    return normalizeChatPayload(payload).raw || payload;
  }

  async function renameSession(sessionId, title) {
    const payload = await post(ROUTES.renameSession, {
      session_id: safeString(sessionId).trim(),
      title: safeString(title).trim(),
    });

    return normalizeChatPayload(payload).raw || payload;
  }

  async function deleteSession(sessionId) {
    const payload = await post(ROUTES.deleteSession, {
      session_id: safeString(sessionId).trim(),
    });

    return normalizeChatPayload(payload).raw || payload;
  }

  async function duplicateSession(sessionId) {
    const payload = await post(ROUTES.duplicateSession, {
      session_id: safeString(sessionId).trim(),
    });

    return normalizeChatPayload(payload).raw || payload;
  }

  async function pinSession(sessionId, pinned = true) {
    const payload = await post(ROUTES.pinSession, {
      session_id: safeString(sessionId).trim(),
      pinned: !!pinned,
    });

    return normalizeChatPayload(payload).raw || payload;
  }

  async function getChat(sessionId) {
    const payload = await get(ROUTES.getChat(sessionId));
    return normalizeChatPayload(payload);
  }

  async function sendChat(data = {}) {
    const payload = await post(ROUTES.sendChat, {
      content: safeString(data.content || "").trim(),
      session_id: safeString(data.session_id || data.sessionId || "").trim(),
      model: safeString(data.model || "").trim(),
    });

    return normalizeChatPayload(payload);
  }

  async function uploadFiles(files) {
    const fileList = Array.isArray(files) ? files : Array.from(files || []);
    const formData = new FormData();

    fileList.forEach((file) => {
      if (file) {
        formData.append("files", file);
      }
    });

    return postForm(ROUTES.upload, formData);
  }

  async function getModels() {
    const payload = await get(ROUTES.models);
    return normalizeModelsPayload(payload);
  }

  async function streamChat(data = {}, handlers = {}) {
    const response = await fetch(ROUTES.streamChat, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream, application/json, text/plain",
      },
      cache: "no-store",
      body: JSON.stringify({
        content: safeString(data.content || "").trim(),
        session_id: safeString(data.session_id || data.sessionId || "").trim(),
        model: safeString(data.model || "").trim(),
      }),
      signal: handlers.signal,
    });

    if (!response.ok) {
      const payload = await readResponseBody(response);
      const payloadMessage =
        (isObject(payload) && safeString(payload.error || payload.message).trim()) ||
        (typeof payload === "string" ? payload.trim() : "");

      throw buildError(
        payloadMessage || `POST failed: ${ROUTES.streamChat}`,
        {
          status: response.status,
          statusText: response.statusText,
          payload,
        }
      );
    }

    if (!response.body) {
      const payload = await readResponseBody(response);
      return {
        ok: true,
        fallback: true,
        payload,
      };
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        const trimmed = part.trim();
        if (!trimmed) continue;

        const parsed = parseStreamEventBlock(trimmed);
        const eventName = safeString(parsed.event || "message");
        const eventData = parsed.data;

        if (eventName === "delta" && typeof handlers.onDelta === "function") {
          handlers.onDelta(eventData, parsed);
          continue;
        }

        if (eventName === "start" && typeof handlers.onStart === "function") {
          handlers.onStart(eventData, parsed);
          continue;
        }

        if (eventName === "done" && typeof handlers.onDone === "function") {
          handlers.onDone(eventData, parsed);
          continue;
        }

        if (eventName === "error" && typeof handlers.onError === "function") {
          handlers.onError(eventData, parsed);
          continue;
        }

        if (typeof handlers.onEvent === "function") {
          handlers.onEvent(parsed);
        }
      }
    }

    if (buffer.trim()) {
      const parsed = parseStreamEventBlock(buffer.trim());
      if (typeof handlers.onEvent === "function") {
        handlers.onEvent(parsed);
      }
    }

    return {
      ok: true,
      streamed: true,
    };
  }

  api.ROUTES = ROUTES;
  api.request = request;
  api.get = get;
  api.post = post;
  api.postForm = postForm;
  api.getState = getState;
  api.getMemory = getMemory;
  api.addMemory = addMemory;
  api.deleteMemory = deleteMemory;
  api.createSession = createSession;
  api.renameSession = renameSession;
  api.deleteSession = deleteSession;
  api.duplicateSession = duplicateSession;
  api.pinSession = pinSession;
  api.getChat = getChat;
  api.sendChat = sendChat;
  api.streamChat = streamChat;
  api.uploadFiles = uploadFiles;
  api.getModels = getModels;
  api.normalizeStatePayload = normalizeStatePayload;
  api.normalizeMemoryPayload = normalizeMemoryPayload;
  api.normalizeChatPayload = normalizeChatPayload;
  api.normalizeModelsPayload = normalizeModelsPayload;
})();