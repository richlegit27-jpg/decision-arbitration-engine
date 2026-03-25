// C:\Users\Owner\nova\static\js\nova-api.js

(() => {
  "use strict";

  window.Nova = window.Nova || {};

  if (window.Nova.apiModuleLoaded) {
    console.warn("nova-api.js already loaded");
    return;
  }
  window.Nova.apiModuleLoaded = true;

  const apiPaths = window.Nova.apiPaths || {};

  function normalizeErrorMessage(error, fallback = "Request failed") {
    if (!error) return fallback;
    if (typeof error === "string") return error;
    if (error instanceof Error && error.message) return error.message;
    if (typeof error.message === "string" && error.message.trim()) return error.message;
    return fallback;
  }

  async function parseJsonResponse(response) {
    const text = await response.text();
    if (!text) return {};
    try {
      return JSON.parse(text);
    } catch (_error) {
      return { raw: text };
    }
  }

  async function ensureOk(response, label = "Request failed") {
    const data = await parseJsonResponse(response);

    if (!response.ok) {
      const message =
        (data && (data.error || data.message)) ||
        `${label}: ${response.status} ${response.statusText}`;
      throw new Error(message);
    }

    if (data && data.ok === false) {
      throw new Error(data.error || data.message || label);
    }

    return data;
  }

  async function apiGet(url) {
    const response = await window.fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      credentials: "same-origin",
    });

    return ensureOk(response, `GET failed: ${url}`);
  }

  async function apiPost(url, body = {}) {
    const response = await window.fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      credentials: "same-origin",
      body: JSON.stringify(body || {}),
    });

    return ensureOk(response, `POST failed: ${url}`);
  }

  async function apiUpload(url, formData) {
    const response = await window.fetch(url, {
      method: "POST",
      credentials: "same-origin",
      body: formData,
    });

    return ensureOk(response, `UPLOAD failed: ${url}`);
  }

  function createSseParser({ onEvent, onError }) {
    const decoder = new TextDecoder();
    let buffer = "";

    return {
      push(chunk) {
        buffer += decoder.decode(chunk, { stream: true });

        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const rawPart of parts) {
          const lines = rawPart.split("\n");
          let eventName = "message";
          const dataLines = [];

          for (const line of lines) {
            if (line.startsWith("event:")) {
              eventName = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataLines.push(line.slice(5).trimStart());
            }
          }

          const rawData = dataLines.join("\n");
          let parsed = rawData;

          if (rawData) {
            try {
              parsed = JSON.parse(rawData);
            } catch (_error) {
              parsed = rawData;
            }
          }

          try {
            onEvent?.(eventName, parsed, rawPart);
          } catch (error) {
            onError?.(error);
          }
        }
      },
      flush() {
        if (!buffer.trim()) return;
        try {
          onEvent?.("message", buffer.trim(), buffer.trim());
        } catch (error) {
          onError?.(error);
        }
        buffer = "";
      },
    };
  }

  async function streamJson(url, payload, handlers = {}) {
    const controller = new AbortController();

    const response = await window.fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      credentials: "same-origin",
      body: JSON.stringify(payload || {}),
      signal: controller.signal,
    });

    if (!response.ok || !response.body) {
      const data = await parseJsonResponse(response);
      const message =
        (data && (data.error || data.message)) ||
        `STREAM failed: ${url} ${response.status} ${response.statusText}`;
      throw new Error(message);
    }

    const reader = response.body.getReader();
    const parser = createSseParser({
      onEvent: handlers.onEvent,
      onError: handlers.onError,
    });

    async function pump() {
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          if (value) parser.push(value);
        }
        parser.flush();
        handlers.onDone?.();
      } catch (error) {
        if (controller.signal.aborted) {
          handlers.onAbort?.();
          return;
        }
        handlers.onError?.(error);
        throw error;
      }
    }

    return {
      controller,
      done: pump(),
      abort() {
        controller.abort();
      },
    };
  }

  async function getState() {
    return apiGet(apiPaths.state);
  }

  async function getHealth() {
    return apiGet(apiPaths.health);
  }

  async function getModels() {
    return apiGet(apiPaths.models);
  }

  async function getMemory() {
    return apiGet(apiPaths.memory);
  }

  async function addMemory(payload) {
    return apiPost(apiPaths.addMemory, payload);
  }

  async function deleteMemory(payload) {
    return apiPost(apiPaths.deleteMemory, payload);
  }

  async function newSession(payload = {}) {
    return apiPost(apiPaths.newSession, payload);
  }

  async function renameSession(payload) {
    return apiPost(apiPaths.renameSession, payload);
  }

  async function deleteSession(payload) {
    return apiPost(apiPaths.deleteSession, payload);
  }

  async function duplicateSession(payload) {
    return apiPost(apiPaths.duplicateSession, payload);
  }

  async function pinSession(payload) {
    return apiPost(apiPaths.pinSession, payload);
  }

  async function getChat(sessionId) {
    return apiGet(apiPaths.getChat(sessionId));
  }

  async function sendChat(payload) {
    if (apiPaths.send) {
      return apiPost(apiPaths.send, payload);
    }
    return apiPost(apiPaths.stream, payload);
  }

  async function startChatStream(payload, handlers = {}) {
    return streamJson(apiPaths.stream, payload, handlers);
  }

  async function uploadFiles(files = []) {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }
    return apiUpload(apiPaths.upload, formData);
  }

  async function getAuthMe() {
    if (!apiPaths.authMe) return { ok: true, authenticated: false };
    return apiGet(apiPaths.authMe);
  }

  async function login(payload) {
    return apiPost(apiPaths.authLogin, payload);
  }

  async function register(payload) {
    return apiPost(apiPaths.authRegister, payload);
  }

  async function logout() {
    return apiPost(apiPaths.authLogout, {});
  }

  window.Nova.api = {
    normalizeErrorMessage,
    parseJsonResponse,
    ensureOk,
    apiGet,
    apiPost,
    apiUpload,
    createSseParser,
    streamJson,
    getState,
    getHealth,
    getModels,
    getMemory,
    addMemory,
    deleteMemory,
    newSession,
    renameSession,
    deleteSession,
    duplicateSession,
    pinSession,
    getChat,
    sendChat,
    startChatStream,
    uploadFiles,
    getAuthMe,
    login,
    register,
    logout,
  };
})();