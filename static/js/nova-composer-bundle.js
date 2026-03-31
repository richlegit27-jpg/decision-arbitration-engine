(function () {
  "use strict";

  const API = {
    chat: "/api/chat",
    upload: "/api/upload",
    state: "/api/state",
    sessions: "/api/sessions",
    session(sessionId) {
      return `/api/sessions/${encodeURIComponent(sessionId)}`;
    },
  };

  const state = {
    activeSessionId: "",
    sending: false,
    uploading: false,
    sessions: [],
    stagedAttachments: [],
    lastRequest: {},
    lastResponse: {},
  };

  const els = {
    appShell: null,
    chatInput: null,
    sendBtn: null,
    uploadBtn: null,
    fileInput: null,
    messages: null,
    activeSessionTitle: null,
    connectionStatus: null,
    newSessionBtn: null,
    refreshSessionsBtn: null,
    sessionList: null,
    collapsedSessionRail: null,
  };

  function q(id) {
    return document.getElementById(id);
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function safeJsonParse(text, fallback) {
    try {
      return text ? JSON.parse(text) : fallback;
    } catch (_) {
      return fallback;
    }
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function clampText(value, limit) {
    const text = String(value == null ? "" : value).trim();
    if (text.length <= limit) return text;
    return text.slice(0, Math.max(0, limit - 1)).trimEnd() + "…";
  }

  function formatTime(value) {
    try {
      return new Date(value).toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_) {
      return "";
    }
  }

  function formatDateTime(value) {
    try {
      return new Date(value).toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_) {
      return "";
    }
  }

  function isObject(value) {
    return !!value && typeof value === "object" && !Array.isArray(value);
  }

  function setConnectionStatus(text) {
    if (els.connectionStatus) {
      els.connectionStatus.textContent = String(text || "Ready");
    }
  }

  function setBusyFlags() {
    if (els.sendBtn) {
      els.sendBtn.disabled = state.sending || state.uploading;
      els.sendBtn.textContent = state.sending ? "Sending…" : "Send";
    }

    if (els.uploadBtn) {
      els.uploadBtn.disabled = state.sending || state.uploading;
      els.uploadBtn.textContent = state.uploading ? "Uploading…" : "Upload";
    }
  }

  function updateDebug(requestValue, responseValue) {
    if (requestValue !== undefined) {
      state.lastRequest = requestValue || {};
      window.__novaLastRequest = state.lastRequest;
    }
    if (responseValue !== undefined) {
      state.lastResponse = responseValue || {};
      window.__novaLastResponse = state.lastResponse;
    }
    window.dispatchEvent(new CustomEvent("nova:debug-update"));
  }

  function getStoredSessionId() {
    try {
      return localStorage.getItem("nova.activeSessionId") || "";
    } catch (_) {
      return "";
    }
  }

  function setStoredSessionId(sessionId) {
    try {
      if (sessionId) {
        localStorage.setItem("nova.activeSessionId", sessionId);
      } else {
        localStorage.removeItem("nova.activeSessionId");
      }
    } catch (_) {}
  }

  function normalizeAttachment(raw) {
    if (!raw) return null;

    if (typeof raw === "string") {
      return {
        id: `att-${Math.random().toString(36).slice(2, 10)}`,
        type: "file",
        filename: "",
        stored_name: "",
        mime_type: "",
        url: raw,
        size: null,
        source: "unknown",
        title: raw,
        alt: raw,
      };
    }

    const filename = raw.filename || raw.name || raw.title || "";
    const mimeType = raw.mime_type || raw.content_type || raw.mime || "";
    let type = String(raw.type || raw.kind || "").toLowerCase();
    const url = raw.url || raw.src || raw.href || "";
    const storedName = raw.stored_name || raw.stored_filename || raw.path || "";

    if (!type) {
      const probe = `${filename} ${url}`.toLowerCase();
      if (mimeType.startsWith("image/") || /\.(png|jpg|jpeg|gif|webp|bmp|svg)(\?|#|$)/i.test(probe)) {
        type = "image";
      } else if (mimeType.startsWith("video/") || /\.(mp4|webm|mov|m4v|avi|mkv)(\?|#|$)/i.test(probe)) {
        type = "video";
      } else if (mimeType.startsWith("audio/") || /\.(mp3|wav|m4a|ogg|flac|aac)(\?|#|$)/i.test(probe)) {
        type = "audio";
      } else {
        type = "file";
      }
    }

    const item = {
      id: raw.id || `att-${Math.random().toString(36).slice(2, 10)}`,
      type,
      filename,
      stored_name: storedName,
      mime_type: mimeType,
      url,
      size: raw.size ?? null,
      source: raw.source || "unknown",
      title: raw.title || filename || type,
      alt: raw.alt || raw.caption || filename || raw.title || type,
    };

    if (!item.url && !item.filename && !item.stored_name) return null;
    return item;
  }

  function normalizeAttachments(value) {
    if (!value) return [];
    const raw = Array.isArray(value) ? value : [value];
    return raw.map(normalizeAttachment).filter(Boolean);
  }

  function getStagedAttachments() {
    if (window.NovaUploadStage && typeof window.NovaUploadStage.get === "function") {
      return normalizeAttachments(window.NovaUploadStage.get());
    }
    return normalizeAttachments(state.stagedAttachments);
  }

  function setStagedAttachments(items) {
    const normalized = normalizeAttachments(items);
    state.stagedAttachments = normalized;

    if (window.NovaUploadStage && typeof window.NovaUploadStage.set === "function") {
      window.NovaUploadStage.set(normalized);
    }
  }

  function addStagedAttachments(items) {
    const merged = getStagedAttachments().concat(normalizeAttachments(items));
    setStagedAttachments(merged);
  }

  function clearStagedAttachments() {
    state.stagedAttachments = [];
    if (window.NovaUploadStage && typeof window.NovaUploadStage.clear === "function") {
      window.NovaUploadStage.clear();
    } else if (window.NovaUploadStage && typeof window.NovaUploadStage.set === "function") {
      window.NovaUploadStage.set([]);
    }
    if (els.fileInput) {
      els.fileInput.value = "";
    }
  }

  function normalizeSessionSummary(raw) {
    if (!isObject(raw)) return null;
    return {
      id: String(raw.id || ""),
      title: String(raw.title || "New Chat"),
      created_at: raw.created_at || "",
      updated_at: raw.updated_at || raw.created_at || "",
      pinned: Boolean(raw.pinned),
      message_count: Number(raw.message_count || (Array.isArray(raw.messages) ? raw.messages.length : 0) || 0),
      last_message_preview: String(raw.last_message_preview || ""),
      messages: Array.isArray(raw.messages) ? raw.messages : [],
    };
  }

  async function requestJson(url, options) {
    const finalOptions = options || {};
    const response = await fetch(url, {
      method: finalOptions.method || "GET",
      headers: {
        ...(finalOptions.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(finalOptions.headers || {}),
      },
      body: finalOptions.body,
    });

    const text = await response.text();
    const data = safeJsonParse(text, { ok: false, raw: text, status: response.status });

    if (!response.ok) {
      const error = new Error(data.message || `Request failed: ${response.status}`);
      error.response = response;
      error.data = data;
      throw error;
    }

    return data;
  }

  function buildLocalUserMessage(text, attachments) {
    return {
      id: `local-user-${Math.random().toString(36).slice(2, 10)}`,
      role: "user",
      content: String(text || ""),
      attachments: normalizeAttachments(attachments),
      created_at: nowIso(),
      meta: {
        local_echo: true,
      },
    };
  }

  function ensureRender() {
    return window.NovaRender && typeof window.NovaRender.appendMessage === "function";
  }

  function appendMessageToUi(message) {
    if (!ensureRender()) return null;
    return window.NovaRender.appendMessage(message);
  }

  function renderMessagesToUi(messages) {
    if (!ensureRender()) return;
    window.NovaRender.renderMessages(messages || []);
  }

  function normalizeIncomingResponse(payload) {
    if (window.NovaRender && typeof window.NovaRender.normalizeIncomingResponse === "function") {
      return window.NovaRender.normalizeIncomingResponse(payload);
    }

    const assistant = payload && payload.assistant_message ? payload.assistant_message : null;
    return {
      ok: payload && payload.ok !== false,
      assistant_message: assistant
        ? {
            id: assistant.id || `msg-${Math.random().toString(36).slice(2, 10)}`,
            role: assistant.role || "assistant",
            content: assistant.content || "",
            attachments: normalizeAttachments(assistant.attachments || []),
            created_at: assistant.created_at || nowIso(),
            meta: assistant.meta || {},
          }
        : null,
      session: payload && payload.session ? payload.session : null,
      debug: payload && payload.debug ? payload.debug : {},
    };
  }

  function buildPayload(content) {
    const payload = {
      content: String(content || ""),
      session_id: state.activeSessionId || "",
      attachments: getStagedAttachments(),
      route_meta: {
        source: "nova-composer-bundle",
        timestamp: nowIso(),
        attachments_count: getStagedAttachments().length,
        attachments_types: getStagedAttachments().map((item) => item.type),
      },
    };

    console.log("[NovaComposerBundle] buildPayload", payload);
    return payload;
  }

  function setActiveSessionTitle(title) {
    if (els.activeSessionTitle) {
      els.activeSessionTitle.textContent = String(title || "New Chat");
    }
  }

  function sessionCardHtml(session) {
    const id = String(session.id || "");
    const title = escapeHtml(session.title || "New Chat");
    const preview = escapeHtml(session.last_message_preview || "");
    const metaBits = [
      session.pinned ? "Pinned" : "",
      session.message_count ? `${session.message_count} msg` : "0 msg",
      session.updated_at ? formatDateTime(session.updated_at) : "",
    ].filter(Boolean);

    const activeClass = state.activeSessionId === id ? " is-active" : "";

    return `
      <div class="nova-session-card${activeClass}" data-session-id="${escapeHtml(id)}">
        <div class="nova-session-card-top">
          <div class="nova-session-card-title">${title}</div>
        </div>
        <div class="nova-session-card-preview">${preview || "&nbsp;"}</div>
        <div class="nova-session-card-meta">
          ${metaBits.map((bit) => `<span>${escapeHtml(bit)}</span>`).join("")}
        </div>
        <div class="nova-session-card-actions">
          <button class="nova-chip-btn" type="button" data-session-action="pin" data-session-id="${escapeHtml(id)}">
            ${session.pinned ? "Unpin" : "Pin"}
          </button>
          <button class="nova-chip-btn" type="button" data-session-action="rename" data-session-id="${escapeHtml(id)}">
            Rename
          </button>
          <button class="nova-chip-btn" type="button" data-session-action="delete" data-session-id="${escapeHtml(id)}">
            Delete
          </button>
        </div>
      </div>
    `;
  }

  function collapsedMarkerHtml(session, index) {
    const id = String(session.id || "");
    const title = String(session.title || "New Chat");
    const label = title.trim().charAt(0).toUpperCase() || String(index + 1);
    const activeClass = state.activeSessionId === id ? " is-active" : "";

    return `
      <button
        class="nova-collapsed-marker${activeClass}"
        type="button"
        title="${escapeHtml(title)}"
        data-session-id="${escapeHtml(id)}"
      >
        <span>${escapeHtml(label)}</span>
        ${state.activeSessionId === id ? '<span class="nova-collapsed-marker-dot"></span>' : ""}
      </button>
    `;
  }

  function renderSessionRail() {
    if (els.sessionList) {
      els.sessionList.innerHTML = state.sessions.map(sessionCardHtml).join("");
    }

    if (els.collapsedSessionRail) {
      els.collapsedSessionRail.innerHTML = state.sessions
        .slice(0, 24)
        .map(collapsedMarkerHtml)
        .join("");
    }

    const active = state.sessions.find((item) => item.id === state.activeSessionId) || null;
    setActiveSessionTitle(active ? active.title : "New Chat");
  }

  async function reloadSessionsFromBackend() {
    const data = await requestJson(API.sessions);
    const sessions = Array.isArray(data.sessions) ? data.sessions : [];
    state.sessions = sessions.map(normalizeSessionSummary).filter(Boolean);
    renderSessionRail();
    return state.sessions;
  }

  function findSessionById(sessionId) {
    return state.sessions.find((item) => item.id === sessionId) || null;
  }

  function applySessionPayload(sessionPayload) {
    const normalized = normalizeSessionSummary(sessionPayload);
    if (!normalized) return null;

    const idx = state.sessions.findIndex((item) => item.id === normalized.id);
    if (idx >= 0) {
      state.sessions[idx] = {
        ...state.sessions[idx],
        ...normalized,
      };
    } else {
      state.sessions.unshift(normalized);
    }

    state.activeSessionId = normalized.id;
    setStoredSessionId(normalized.id);
    renderSessionRail();
    return normalized;
  }

  async function restoreSessionFromBackend(sessionId, options) {
    const opts = options || {};
    if (!sessionId) return null;

    console.log("[NovaComposerBundle] restoreSessionFromBackend start", { sessionId, options: opts });
    setConnectionStatus("Restoring…");

    const data = await requestJson(API.session(sessionId));
    const session = normalizeSessionSummary(data.session);

    if (!session) {
      throw new Error("Session payload missing");
    }

    state.activeSessionId = session.id;
    setStoredSessionId(session.id);

    const existingIdx = state.sessions.findIndex((item) => item.id === session.id);
    if (existingIdx >= 0) {
      state.sessions[existingIdx] = {
        ...state.sessions[existingIdx],
        ...session,
      };
    } else {
      state.sessions.unshift(session);
    }

    renderSessionRail();
    renderMessagesToUi(session.messages || []);
    setActiveSessionTitle(session.title || "New Chat");
    setConnectionStatus("Ready");

    if (opts.openArtifacts && window.NovaPanels && typeof window.NovaPanels.open === "function") {
      window.NovaPanels.open("artifacts");
    }

    console.log("[NovaComposerBundle] restoreSessionFromBackend done", { sessionId: session.id });
    return session;
  }

  async function createSession(title) {
    const data = await requestJson(API.sessions, {
      method: "POST",
      body: JSON.stringify({
        title: String(title || "New Chat"),
      }),
    });

    const session = applySessionPayload(data.session);
    renderMessagesToUi([]);
    return session;
  }

  async function patchSession(sessionId, patch) {
    const data = await requestJson(API.session(sessionId), {
      method: "PATCH",
      body: JSON.stringify(patch || {}),
    });
    const session = applySessionPayload(data.session);
    await reloadSessionsFromBackend();
    return session;
  }

  async function deleteSession(sessionId) {
    const data = await requestJson(API.session(sessionId), {
      method: "DELETE",
    });

    state.sessions = Array.isArray(data.sessions) ? data.sessions.map(normalizeSessionSummary).filter(Boolean) : [];
    if (state.activeSessionId === sessionId) {
      const next = state.sessions[0] || null;
      state.activeSessionId = next ? next.id : "";
      setStoredSessionId(state.activeSessionId);
      if (next) {
        await restoreSessionFromBackend(next.id, { source: "delete-fallback" });
      } else {
        renderMessagesToUi([]);
        setActiveSessionTitle("New Chat");
      }
    } else {
      renderSessionRail();
    }
  }

  async function uploadFiles(files) {
    const fileList = Array.from(files || []).filter(Boolean);
    if (!fileList.length) return [];

    const formData = new FormData();
    fileList.forEach((file) => {
      formData.append("files", file);
    });

    state.uploading = true;
    setBusyFlags();
    setConnectionStatus("Uploading…");

    const requestMeta = {
      at: nowIso(),
      url: API.upload,
      method: "POST",
      files: fileList.map((file) => ({
        name: file.name,
        size: file.size,
        type: file.type,
      })),
    };
    updateDebug(requestMeta, undefined);

    try {
      const data = await requestJson(API.upload, {
        method: "POST",
        body: formData,
      });

      const attachments = normalizeAttachments(data.attachments || data.files || []);
      addStagedAttachments(attachments);
      updateDebug(requestMeta, data);
      setConnectionStatus("Ready");

      console.log("[NovaComposerBundle] uploadFiles success", {
        count: attachments.length,
        attachments,
      });

      return attachments;
    } finally {
      state.uploading = false;
      setBusyFlags();
      if (!state.sending) {
        setConnectionStatus("Ready");
      }
    }
  }

  async function sendMessage() {
    const text = String(els.chatInput ? els.chatInput.value : "").trim();
    const attachments = getStagedAttachments();

    if (state.sending) return;
    if (!text && !attachments.length) return;

    state.sending = true;
    setBusyFlags();
    setConnectionStatus("Sending…");

    if (!state.activeSessionId) {
      const created = await createSession("New Chat");
      if (!created || !created.id) {
        state.sending = false;
        setBusyFlags();
        throw new Error("Failed to create session");
      }
    }

    const localUserMessage = buildLocalUserMessage(text, attachments);
    appendMessageToUi(localUserMessage);

    if (els.chatInput) {
      els.chatInput.value = "";
      els.chatInput.style.height = "";
    }

    const payload = buildPayload(text);
    const requestMeta = {
      id: `req-${Math.random().toString(36).slice(2, 10)}`,
      at: nowIso(),
      url: API.chat,
      method: "POST",
      body: payload,
    };

    console.log("[NovaComposerBundle] sendMessage start", requestMeta);
    updateDebug(requestMeta, undefined);

    try {
      const raw = await requestJson(API.chat, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      const normalized = normalizeIncomingResponse(raw);
      updateDebug(requestMeta, normalized);

      if (normalized.session) {
        applySessionPayload(normalized.session);
      }

      if (normalized.assistant_message) {
        appendMessageToUi(normalized.assistant_message);
      }

      clearStagedAttachments();
      await reloadSessionsFromBackend();

      if (window.dispatchEvent) {
        window.dispatchEvent(new CustomEvent("nova:artifact-saved", { detail: normalized }));
        window.dispatchEvent(new CustomEvent("nova:artifacts-refresh"));
      }

      setConnectionStatus("Ready");
      console.log("[NovaComposerBundle] sendMessage done", normalized);
      return normalized;
    } catch (error) {
      console.error("[NovaComposerBundle] sendMessage failed", error);
      const errorPayload = {
        ok: false,
        message: error.message || "Request failed",
        debug: error.data || {},
      };
      updateDebug(requestMeta, errorPayload);

      const fallbackMessage = {
        id: `msg-error-${Math.random().toString(36).slice(2, 10)}`,
        role: "assistant",
        content: `Request failed.\n\n${error.message || "Unknown error"}`,
        attachments: [],
        created_at: nowIso(),
        meta: {
          fallback_reason: "request_failed",
        },
      };
      appendMessageToUi(fallbackMessage);
      setConnectionStatus("Error");
      throw error;
    } finally {
      state.sending = false;
      setBusyFlags();
    }
  }

  function autosizeTextarea() {
    if (!els.chatInput) return;
    els.chatInput.style.height = "auto";
    els.chatInput.style.height = Math.min(els.chatInput.scrollHeight, 260) + "px";
  }

  async function handleNewSession() {
    const session = await createSession("New Chat");
    await reloadSessionsFromBackend();
    if (session && session.id) {
      await restoreSessionFromBackend(session.id, { source: "new-session" });
    }
    clearStagedAttachments();
    if (els.chatInput) els.chatInput.focus();
  }

  async function handleSessionAction(action, sessionId) {
    const session = findSessionById(sessionId);
    if (!sessionId || !session) return;

    if (action === "pin") {
      await patchSession(sessionId, { pinned: !session.pinned });
      return;
    }

    if (action === "rename") {
      const nextTitle = window.prompt("Rename session", session.title || "New Chat");
      if (nextTitle == null) return;
      await patchSession(sessionId, { title: nextTitle });
      return;
    }

    if (action === "delete") {
      const ok = window.confirm(`Delete session "${session.title || "New Chat"}"?`);
      if (!ok) return;
      await deleteSession(sessionId);
    }
  }

  function bindSessionRailClicks() {
    if (els.sessionList) {
      els.sessionList.addEventListener("click", async function (event) {
        const actionBtn = event.target.closest("[data-session-action]");
        if (actionBtn) {
          event.preventDefault();
          event.stopPropagation();
          const action = actionBtn.getAttribute("data-session-action");
          const sessionId = actionBtn.getAttribute("data-session-id");
          await handleSessionAction(action, sessionId);
          return;
        }

        const card = event.target.closest("[data-session-id]");
        if (!card) return;
        const sessionId = card.getAttribute("data-session-id");
        if (!sessionId) return;
        await restoreSessionFromBackend(sessionId, { source: "rail-click", force: true });
      });
    }

    if (els.collapsedSessionRail) {
      els.collapsedSessionRail.addEventListener("click", async function (event) {
        const marker = event.target.closest("[data-session-id]");
        if (!marker) return;
        const sessionId = marker.getAttribute("data-session-id");
        if (!sessionId) return;
        await restoreSessionFromBackend(sessionId, { source: "collapsed-rail-click", force: true });
      });
    }
  }

  function bindUploadFlow() {
    if (els.uploadBtn && els.fileInput) {
      els.uploadBtn.addEventListener("click", function () {
        els.fileInput.click();
      });

      els.fileInput.addEventListener("change", async function (event) {
        const files = event.target && event.target.files ? event.target.files : [];
        if (!files || !files.length) return;

        try {
          await uploadFiles(files);
        } catch (error) {
          console.error("[NovaComposerBundle] upload failed", error);
          const fallbackMessage = {
            id: `msg-upload-error-${Math.random().toString(36).slice(2, 10)}`,
            role: "assistant",
            content: `Upload failed.\n\n${error.message || "Unknown upload error"}`,
            attachments: [],
            created_at: nowIso(),
            meta: {
              fallback_reason: "upload_failed",
            },
          };
          appendMessageToUi(fallbackMessage);
          setConnectionStatus("Upload Error");
        } finally {
          if (els.fileInput) {
            els.fileInput.value = "";
          }
        }
      });
    }
  }

  function bindComposer() {
    if (els.chatInput) {
      els.chatInput.addEventListener("input", autosizeTextarea);
      els.chatInput.addEventListener("keydown", async function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          await sendMessage();
        }
      });
      autosizeTextarea();
    }

    if (els.sendBtn) {
      els.sendBtn.addEventListener("click", async function () {
        await sendMessage();
      });
    }

    if (els.newSessionBtn) {
      els.newSessionBtn.addEventListener("click", async function () {
        await handleNewSession();
      });
    }

    if (els.refreshSessionsBtn) {
      els.refreshSessionsBtn.addEventListener("click", async function () {
        await reloadSessionsFromBackend();
      });
    }
  }

  async function bootstrapState() {
    console.log("[NovaComposerBundle] bootstrapState start");
    setConnectionStatus("Loading…");

    try {
      const data = await requestJson(API.state);
      const sessions = Array.isArray(data.sessions) ? data.sessions : [];
      state.sessions = sessions.map(normalizeSessionSummary).filter(Boolean);

      const remembered = getStoredSessionId();
      const initial =
        state.sessions.find((item) => item.id === remembered) ||
        state.sessions[0] ||
        null;

      renderSessionRail();

      if (initial && initial.id) {
        await restoreSessionFromBackend(initial.id, { source: "bootstrap-restore" });
      } else {
        renderMessagesToUi([]);
        setActiveSessionTitle("New Chat");
      }

      updateDebug(
        {
          at: nowIso(),
          url: API.state,
          method: "GET",
        },
        data
      );

      setConnectionStatus("Ready");
      console.log("[NovaComposerBundle] bootstrapState done", {
        sessions: state.sessions.length,
        activeSessionId: state.activeSessionId,
      });
    } catch (error) {
      console.error("[NovaComposerBundle] bootstrapState failed", error);
      setConnectionStatus("State Error");
      updateDebug(
        {
          at: nowIso(),
          url: API.state,
          method: "GET",
        },
        error.data || { ok: false, message: error.message || "State load failed" }
      );
    }
  }

  function bindGlobalEvents() {
    window.addEventListener("nova:session-select", async function (event) {
      const detail = event && event.detail ? event.detail : {};
      const sessionId = detail.sessionId || detail.id || "";
      if (!sessionId) return;
      await restoreSessionFromBackend(sessionId, detail);
    });

    window.addEventListener("nova:session-created", async function (event) {
      const detail = event && event.detail ? event.detail : {};
      const sessionId = detail.sessionId || detail.id || "";
      if (!sessionId) return;
      await restoreSessionFromBackend(sessionId, { source: "session-created-event" });
    });
  }

  function bindEls() {
    els.appShell = q("novaAppShell");
    els.chatInput = q("chatInput");
    els.sendBtn = q("sendBtn");
    els.uploadBtn = q("uploadBtn");
    els.fileInput = q("fileInput");
    els.messages = q("messages");
    els.activeSessionTitle = q("activeSessionTitle");
    els.connectionStatus = q("connectionStatus");
    els.newSessionBtn = q("newSessionBtn");
    els.refreshSessionsBtn = q("refreshSessionsBtn");
    els.sessionList = q("sessionList");
    els.collapsedSessionRail = q("collapsedSessionRail");
  }

  const NovaComposerBundle = {
    init() {
      bindEls();
      bindComposer();
      bindUploadFlow();
      bindSessionRailClicks();
      bindGlobalEvents();
      setBusyFlags();
      bootstrapState();
      console.log("nova-composer-bundle loaded");
    },

    buildPayload,

    collectHistoryFromDom() {
      const nodes = Array.from(document.querySelectorAll("#messages .nova-message"));
      return nodes.map((node) => {
        const author = node.querySelector(".nova-message-author");
        const body = node.querySelector(".nova-message-markdown");
        return {
          role: author && /you/i.test(author.textContent || "") ? "user" : "assistant",
          content: body ? body.textContent || "" : "",
        };
      });
    },

    async sendMessage() {
      return sendMessage();
    },

    async uploadFiles(files) {
      return uploadFiles(files);
    },

    async restoreSessionFromBackend(sessionId, options) {
      return restoreSessionFromBackend(sessionId, options);
    },

    getActiveSessionId() {
      return state.activeSessionId;
    },

    getState() {
      return {
        ...state,
        stagedAttachments: getStagedAttachments(),
      };
    },

    clearStagedAttachments() {
      clearStagedAttachments();
    },
  };

  window.NovaComposerBundle = NovaComposerBundle;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      NovaComposerBundle.init();
    });
  } else {
    NovaComposerBundle.init();
  }
})();