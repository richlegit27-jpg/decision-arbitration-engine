(function () {
  "use strict";

  const LOG = "[NovaComposerBundle]";
  const API = {
    state: "/api/state",
    chat: "/api/chat",
    upload: "/api/upload"
  };

  const state = {
    booted: false,
    sessionId: "",
    sessions: [],
    sessionMap: new Map(),
    activeSession: null,
    messages: [],
    memoryItems: [],
    webItems: [],
    pendingFiles: [],
    sending: false,
    refreshing: false,
    refreshQueued: false,
    refreshTimer: null,
    lastRenderedSessionId: "",
    lastRenderedMessageHash: "",
    lastRenderedSessionHash: "",
    lastRenderedMemoryHash: "",
    lastRenderedWebHash: "",
    panel: "",
    debug: {
      lastRequest: null,
      lastResponse: null
    }
  };

  function log() {
    try {
      console.log(LOG, ...arguments);
    } catch (_) {}
  }

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function safe(value) {
    return value == null ? "" : String(value);
  }

  function esc(value) {
    return safe(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function nl2br(value) {
    return esc(value).replace(/\n/g, "<br>");
  }

  function dispatch(name, detail) {
    try {
      window.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
    } catch (_) {}
  }

  function setBusy(isBusy) {
    state.sending = !!isBusy;

    const sendBtn = byId("sendBtn");
    const chatInput = byId("chatInput");
    const uploadBtn = byId("uploadBtn");

    if (sendBtn) {
      sendBtn.disabled = state.sending;
      sendBtn.classList.toggle("is-busy", state.sending);
      sendBtn.setAttribute("aria-busy", state.sending ? "true" : "false");
    }

    if (chatInput) {
      chatInput.disabled = state.sending;
    }

    if (uploadBtn) {
      uploadBtn.disabled = state.sending;
    }
  }

  function getChatInputValue() {
    const el = byId("chatInput");
    return el ? el.value : "";
  }

  function setChatInputValue(value) {
    const el = byId("chatInput");
    if (!el) return;
    el.value = value || "";
    autosizeComposer();
  }

  function autosizeComposer() {
    const el = byId("chatInput");
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 280) + "px";
  }

  function normalizeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function hash(value) {
    try {
      return JSON.stringify(value || null);
    } catch (_) {
      return String(Date.now());
    }
  }

  function getStatePayloadSession(payload) {
    if (!payload || typeof payload !== "object") return null;
    if (payload.session && typeof payload.session === "object") return payload.session;
    if (payload.active_session && typeof payload.active_session === "object") return payload.active_session;
    return null;
  }

  function normalizeSession(raw, fallbackIndex) {
    const item = raw || {};
    return {
      id: safe(item.id || item.session_id || item.uuid || `session-${fallbackIndex || 0}`),
      title: safe(item.title || item.name || item.label || "New Chat"),
      pinned: !!item.pinned,
      created_at: safe(item.created_at || item.createdAt || ""),
      updated_at: safe(item.updated_at || item.updatedAt || ""),
      message_count: Number(item.message_count || item.messageCount || normalizeArray(item.messages).length || 0),
      last_message_preview: safe(item.last_message_preview || item.preview || item.last_preview || ""),
      messages: normalizeArray(item.messages).map(normalizeMessage)
    };
  }

  function normalizeMessage(raw, fallbackIndex) {
    const item = raw || {};
    const attachments = normalizeArray(item.attachments).map(function (att, i) {
      const a = att || {};
      return {
        id: safe(a.id || a.attachment_id || `att-${fallbackIndex || 0}-${i}`),
        name: safe(a.name || a.filename || a.stored_name || "attachment"),
        url: safe(a.url || a.path || a.src || ""),
        mime_type: safe(a.mime_type || a.mime || a.content_type || ""),
        kind: safe(a.kind || "")
      };
    });

    return {
      id: safe(item.id || item.message_id || item.uuid || `message-${fallbackIndex || 0}`),
      role: safe(item.role || item.type || "assistant"),
      content: safe(item.content || item.text || item.message || ""),
      created_at: safe(item.created_at || item.createdAt || item.timestamp || ""),
      attachments: attachments,
      meta: item.meta || {},
      badges: normalizeArray(item.badges)
    };
  }

  function normalizeMemoryItem(raw, index) {
    const item = raw || {};
    return {
      id: safe(item.id || `memory-${index}`),
      text: safe(item.text || item.content || item.value || ""),
      created_at: safe(item.created_at || item.createdAt || ""),
      source: safe(item.source || "")
    };
  }

  function normalizeWebItem(raw, index) {
    const item = raw || {};
    return {
      id: safe(item.id || `web-${index}`),
      title: safe(item.title || item.name || item.url || "Web result"),
      url: safe(item.url || ""),
      preview: safe(item.preview || item.summary || item.content || ""),
      created_at: safe(item.created_at || item.createdAt || "")
    };
  }

  function applyPayload(payload) {
    const sessionsRaw = normalizeArray(payload && (payload.sessions || payload.session_list));
    const sessions = sessionsRaw.map(normalizeSession);

    state.sessions = sessions;
    state.sessionMap = new Map(
      sessions.map(function (session) {
        return [session.id, session];
      })
    );

    const payloadSession = getStatePayloadSession(payload);
    const normalizedPayloadSession = payloadSession ? normalizeSession(payloadSession, 0) : null;

    let preferredSessionId =
      safe(
        (payload && (payload.active_session_id || payload.session_id || payload.current_session_id)) ||
          state.sessionId ||
          (normalizedPayloadSession && normalizedPayloadSession.id) ||
          (sessions[0] && sessions[0].id) ||
          ""
      );

    if (normalizedPayloadSession && normalizedPayloadSession.id) {
      state.sessionMap.set(normalizedPayloadSession.id, normalizedPayloadSession);
      const existingIndex = sessions.findIndex(function (s) {
        return s.id === normalizedPayloadSession.id;
      });
      if (existingIndex >= 0) {
        sessions[existingIndex] = normalizedPayloadSession;
      } else {
        sessions.unshift(normalizedPayloadSession);
      }
    }

    state.sessionId = preferredSessionId;
    state.activeSession =
      state.sessionMap.get(state.sessionId) ||
      normalizedPayloadSession ||
      sessions[0] ||
      null;

    state.messages = normalizeArray(
      (state.activeSession && state.activeSession.messages) ||
        (normalizedPayloadSession && normalizedPayloadSession.messages) ||
        payload.messages
    ).map(normalizeMessage);

    state.memoryItems = normalizeArray(payload && (payload.memory || payload.memory_items)).map(
      normalizeMemoryItem
    );

    state.webItems = normalizeArray(payload && (payload.web || payload.web_items || payload.web_results)).map(
      normalizeWebItem
    );
  }

  function renderAll(force) {
    renderSessions(force);
    renderMessages(force);
    renderMemory(force);
    renderWeb(force);
    renderPendingFiles();
    renderEmptyState();
    syncPanelVisibility();
  }

  function renderSessions(force) {
    const root =
      byId("sessionList") ||
      byId("sessionsList") ||
      qs("[data-role='session-list']") ||
      qs(".nova-session-list");

    if (!root) return;

    const nextHash = hash(
      state.sessions.map(function (s) {
        return {
          id: s.id,
          title: s.title,
          pinned: s.pinned,
          updated_at: s.updated_at,
          count: s.message_count,
          preview: s.last_message_preview,
          active: s.id === state.sessionId
        };
      })
    );

    if (!force && nextHash === state.lastRenderedSessionHash) return;
    state.lastRenderedSessionHash = nextHash;

    if (!state.sessions.length) {
      root.innerHTML = '<div class="nova-empty-list">No sessions yet.</div>';
      return;
    }

    root.innerHTML = state.sessions
      .map(function (session) {
        const active = session.id === state.sessionId;
        const title = session.title || "New Chat";
        const preview = session.last_message_preview || "";
        const count = session.message_count || 0;

        return (
          '<button class="nova-session-item' +
          (active ? " is-active" : "") +
          '" type="button" data-session-id="' +
          esc(session.id) +
          '">' +
          '<span class="nova-session-title">' +
          esc(title) +
          "</span>" +
          '<span class="nova-session-meta">' +
          (session.pinned ? '<span class="nova-session-pin">📌</span>' : "") +
          '<span class="nova-session-count">' +
          esc(count) +
          "</span>" +
          "</span>" +
          (preview ? '<span class="nova-session-preview">' + esc(preview) + "</span>" : "") +
          "</button>"
        );
      })
      .join("");
  }

  function renderMessages(force) {
    const root = byId("messages") || qs("[data-role='messages']");
    if (!root) return;

    const nextHash = hash({
      sessionId: state.sessionId,
      messages: state.messages
    });

    if (!force && nextHash === state.lastRenderedMessageHash) return;
    state.lastRenderedMessageHash = nextHash;
    state.lastRenderedSessionId = state.sessionId;

    if (!state.messages.length) {
      root.innerHTML = "";
      return;
    }

    root.innerHTML = state.messages
      .map(function (message, index) {
        return renderMessageHtml(message, index);
      })
      .join("");

    scrollMessagesToBottom();
  }

  function renderMessageHtml(message, index) {
    const role = message.role || "assistant";
    const content = message.content || "";
    const createdAt = message.created_at ? '<div class="nova-message-time">' + esc(message.created_at) + "</div>" : "";
    const badges = buildMessageBadges(message);
    const attachments = buildAttachmentChips(message.attachments);

    return (
      '<article class="nova-message nova-message-' +
      esc(role) +
      '" data-message-id="' +
      esc(message.id || "msg-" + index) +
      '">' +
      '<div class="nova-message-inner">' +
      '<div class="nova-message-head">' +
      '<div class="nova-message-role">' +
      esc(role === "user" ? "You" : "Nova") +
      "</div>" +
      (badges ? '<div class="nova-message-badges">' + badges + "</div>" : "") +
      "</div>" +
      '<div class="nova-message-markdown">' +
      formatMessageContent(content) +
      "</div>" +
      (attachments ? '<div class="nova-message-attachments">' + attachments + "</div>" : "") +
      createdAt +
      "</div>" +
      "</article>"
    );
  }

  function buildMessageBadges(message) {
    const out = [];
    const meta = message.meta || {};

    normalizeArray(message.badges).forEach(function (badge) {
      if (badge) {
        out.push('<span class="nova-badge">' + esc(badge) + "</span>");
      }
    });

    if (meta.artifact_kind) {
      out.push('<span class="nova-badge">Artifact</span>');
    }
    if (meta.web_used || meta.web || message.role === "web_result") {
      out.push('<span class="nova-badge">Web</span>');
    }
    if (meta.memory_used) {
      out.push('<span class="nova-badge">Memory</span>');
    }

    return out.join("");
  }

  function buildAttachmentChips(attachments) {
    const list = normalizeArray(attachments);
    if (!list.length) return "";

    return list
      .map(function (item) {
        const url = item.url ? esc(item.url) : "";
        const name = esc(item.name || "attachment");
        const mime = safe(item.mime_type || "").toLowerCase();

        if (mime.startsWith("image/") && url) {
          return (
            '<a class="nova-attachment-chip is-image" href="' +
            url +
            '" target="_blank" rel="noreferrer">' +
            '<img src="' +
            url +
            '" alt="' +
            name +
            '">' +
            '<span>' +
            name +
            "</span>" +
            "</a>"
          );
        }

        return (
          '<a class="nova-attachment-chip" href="' +
          (url || "#") +
          '" target="_blank" rel="noreferrer">' +
          "<span>" +
          name +
          "</span>" +
          "</a>"
        );
      })
      .join("");
  }

  function formatMessageContent(content) {
    const text = safe(content);

    if (!text) return "";

    let html = esc(text);

    html = html.replace(
      /!\[([^\]]*)\]\((attachment:\/\/[^)]+|https?:\/\/[^)]+)\)/gi,
      function (_match, alt, url) {
        const safeUrl = esc(url.replace(/^attachment:\/\//i, "/api/uploads/"));
        return '<img class="nova-inline-image" src="' + safeUrl + '" alt="' + esc(alt || "image") + '">';
      }
    );

    html = html.replace(
      /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/gi,
      function (_match, label, url) {
        return '<a href="' + esc(url) + '" target="_blank" rel="noreferrer">' + esc(label) + "</a>";
      }
    );

    html = html
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\n/g, "<br>");

    return html;
  }

  function renderMemory(force) {
    const root =
      byId("memoryList") ||
      byId("memoryItems") ||
      qs("[data-role='memory-list']") ||
      qs("#memoryPanel .nova-panel-scroll");

    if (!root) return;

    const nextHash = hash(state.memoryItems);
    if (!force && nextHash === state.lastRenderedMemoryHash) return;
    state.lastRenderedMemoryHash = nextHash;

    if (!state.memoryItems.length) {
      root.innerHTML = '<div class="nova-empty-list">No memory yet.</div>';
      return;
    }

    root.innerHTML = state.memoryItems
      .map(function (item) {
        return (
          '<article class="nova-list-card">' +
          '<div class="nova-list-text">' +
          nl2br(item.text) +
          "</div>" +
          (item.created_at || item.source
            ? '<div class="nova-list-meta">' +
              esc([item.source, item.created_at].filter(Boolean).join(" • ")) +
              "</div>"
            : "") +
          "</article>"
        );
      })
      .join("");
  }

  function renderWeb(force) {
    const root =
      byId("webList") ||
      byId("webItems") ||
      qs("[data-role='web-list']") ||
      qs("#webPanel .nova-panel-scroll");

    if (!root) return;

    const nextHash = hash(state.webItems);
    if (!force && nextHash === state.lastRenderedWebHash) return;
    state.lastRenderedWebHash = nextHash;

    if (!state.webItems.length) {
      root.innerHTML = '<div class="nova-empty-list">No web results yet.</div>';
      return;
    }

    root.innerHTML = state.webItems
      .map(function (item) {
        return (
          '<article class="nova-list-card">' +
          (item.url
            ? '<a class="nova-list-title" href="' +
              esc(item.url) +
              '" target="_blank" rel="noreferrer">' +
              esc(item.title) +
              "</a>"
            : '<div class="nova-list-title">' + esc(item.title) + "</div>") +
          (item.preview ? '<div class="nova-list-text">' + nl2br(item.preview) + "</div>" : "") +
          (item.created_at ? '<div class="nova-list-meta">' + esc(item.created_at) + "</div>" : "") +
          "</article>"
        );
      })
      .join("");
  }

  function renderPendingFiles() {
    const root =
      byId("attachmentTray") ||
      byId("pendingUploads") ||
      qs("[data-role='pending-files']");

    if (!root) return;

    if (!state.pendingFiles.length) {
      root.innerHTML = "";
      root.hidden = true;
      return;
    }

    root.hidden = false;
    root.innerHTML = state.pendingFiles
      .map(function (item, index) {
        return (
          '<div class="nova-pending-file" data-file-index="' +
          index +
          '">' +
          '<span class="nova-pending-file-name">' +
          esc(item.name) +
          "</span>" +
          '<button class="nova-pending-file-remove" type="button" data-remove-file-index="' +
          index +
          '">×</button>' +
          "</div>"
        );
      })
      .join("");
  }

  function renderEmptyState() {
    const empty = byId("novaEmptyState");
    const messages = byId("messages");
    if (!empty || !messages) return;
    empty.hidden = !!state.messages.length;
  }

  function scrollMessagesToBottom() {
    const root = byId("messages");
    if (!root) return;
    root.scrollTop = root.scrollHeight;
  }

  function openPanel(name) {
    state.panel = safe(name);
    syncPanelVisibility();
  }

  function closePanel() {
    state.panel = "";
    syncPanelVisibility();
  }

  function syncPanelVisibility() {
    const rightRail = byId("rightRail");
    const panels = {
      memory: byId("memoryPanel"),
      artifacts: byId("artifactsPanel"),
      web: byId("webPanel")
    };

    Object.keys(panels).forEach(function (key) {
      const panel = panels[key];
      if (!panel) return;
      const active = state.panel === key;
      panel.hidden = !active;
      panel.setAttribute("aria-hidden", active ? "false" : "true");
      panel.classList.toggle("is-active", active);
    });

    if (rightRail) {
      const open = !!state.panel;
      rightRail.classList.toggle("is-open", open);
      rightRail.classList.toggle("is-collapsed", !open);
      rightRail.setAttribute("aria-hidden", open ? "false" : "true");
    }

    const memoryBtn = byId("memoryPanelToggle");
    const artifactsBtn = byId("artifactsPanelToggle");
    const webBtn = byId("webPanelToggle");
    const closeBtn = byId("rightRailClose");

    if (memoryBtn) memoryBtn.classList.toggle("is-active", state.panel === "memory");
    if (artifactsBtn) artifactsBtn.classList.toggle("is-active", state.panel === "artifacts");
    if (webBtn) webBtn.classList.toggle("is-active", state.panel === "web");
    if (closeBtn) closeBtn.hidden = !state.panel;
  }

  function scheduleRefresh(delay) {
    const wait = typeof delay === "number" ? delay : 0;
    if (state.refreshTimer) {
      clearTimeout(state.refreshTimer);
      state.refreshTimer = null;
    }
    state.refreshTimer = setTimeout(function () {
      state.refreshTimer = null;
      refreshState();
    }, wait);
  }

  async function refreshState() {
    if (state.refreshing) {
      state.refreshQueued = true;
      return;
    }

    state.refreshing = true;

    try {
      const url = new URL(API.state, window.location.origin);
      if (state.sessionId) {
        url.searchParams.set("session_id", state.sessionId);
      }

      log("refreshState request", { url: url.toString(), sessionId: state.sessionId });

      const res = await fetch(url.toString(), {
        method: "GET",
        credentials: "same-origin",
        headers: {
          Accept: "application/json"
        }
      });

      const payload = await res.json();

      state.debug.lastResponse = payload;
      log("refreshState response", payload);

      if (!res.ok || payload.ok === false) {
        throw new Error(payload.error || payload.message || "Failed to refresh state.");
      }

      applyPayload(payload);
      renderAll(false);

      dispatch("nova:state-refreshed", {
        sessionId: state.sessionId,
        sessions: state.sessions,
        messages: state.messages,
        memory: state.memoryItems,
        web: state.webItems
      });

      dispatch("nova:artifacts-refresh-request", {
        sessionId: state.sessionId,
        reason: "state-refresh"
      });
    } catch (error) {
      console.error(LOG, "refreshState failed", error);
    } finally {
      state.refreshing = false;
      if (state.refreshQueued) {
        state.refreshQueued = false;
        refreshState();
      }
    }
  }

  async function uploadFiles(files) {
    const list = Array.from(files || []).filter(Boolean);
    if (!list.length) return [];

    const formData = new FormData();
    list.forEach(function (file) {
      formData.append("files", file, file.name);
    });

    const res = await fetch(API.upload, {
      method: "POST",
      credentials: "same-origin",
      body: formData
    });

    const payload = await res.json().catch(function () {
      return {};
    });

    if (!res.ok || payload.ok === false) {
      throw new Error(payload.error || payload.message || "Upload failed.");
    }

    return normalizeArray(payload.files || payload.attachments || payload.uploads).map(function (item, index) {
      return {
        id: safe(item.id || item.attachment_id || `upload-${Date.now()}-${index}`),
        name: safe(item.name || item.filename || item.stored_name || "attachment"),
        url: safe(item.url || item.path || ""),
        stored_name: safe(item.stored_name || item.filename || ""),
        mime_type: safe(item.mime_type || item.mime || item.content_type || "")
      };
    });
  }

  async function sendMessage() {
    if (state.sending) return;

    const rawText = getChatInputValue();
    const text = safe(rawText).trim();

    if (!text && !state.pendingFiles.length) {
      return;
    }

    setBusy(true);

    const queuedFiles = state.pendingFiles.slice();
    const previousText = rawText;

    try {
      let uploadedAttachments = [];

      if (queuedFiles.length) {
        uploadedAttachments = await uploadFiles(
          queuedFiles.map(function (item) {
            return item.file;
          })
        );
      }

      const optimisticUserMessage = normalizeMessage({
        id: "local-user-" + Date.now(),
        role: "user",
        content: text,
        attachments: uploadedAttachments
      });

      state.messages = state.messages.concat([optimisticUserMessage]);
      renderMessages(true);
      renderEmptyState();

      state.pendingFiles = [];
      renderPendingFiles();
      setChatInputValue("");

      const body = {
        session_id: state.sessionId || "",
        content: text,
        attachments: uploadedAttachments
      };

      state.debug.lastRequest = body;
      log("sendMessage request", body);

      const res = await fetch(API.chat, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json"
        },
        body: JSON.stringify(body)
      });

      const payload = await res.json();
      state.debug.lastResponse = payload;
      log("sendMessage ok", payload);

      if (!res.ok || payload.ok === false) {
        throw new Error(payload.error || payload.message || "Send failed.");
      }

      applyChatResponse(payload);
      renderAll(true);

      dispatch("nova:message-sent", {
        sessionId: state.sessionId,
        response: payload
      });

      dispatch("nova:artifacts-refresh-request", {
        sessionId: state.sessionId,
        reason: "chat-send"
      });
    } catch (error) {
      console.error(LOG, "sendMessage failed", error);

      const fallbackErrorMessage = normalizeMessage({
        id: "local-error-" + Date.now(),
        role: "assistant",
        content: "Send failed.\n\n" + safe(error && error.message ? error.message : error)
      });

      state.messages = state.messages.concat([fallbackErrorMessage]);
      renderMessages(true);
      renderEmptyState();

      if (previousText && !getChatInputValue()) {
        setChatInputValue(previousText);
      }
    } finally {
      setBusy(false);
      scheduleRefresh(120);
    }
  }

  function applyChatResponse(payload) {
    const assistantMessage =
      (payload && (payload.assistant_message || payload.reply || payload.message)) || null;

    const payloadSession = getStatePayloadSession(payload);
    const normalizedPayloadSession = payloadSession ? normalizeSession(payloadSession, 0) : null;

    if (normalizedPayloadSession) {
      const existingIndex = state.sessions.findIndex(function (s) {
        return s.id === normalizedPayloadSession.id;
      });

      if (existingIndex >= 0) {
        state.sessions[existingIndex] = normalizedPayloadSession;
      } else {
        state.sessions.unshift(normalizedPayloadSession);
      }

      state.sessionMap.set(normalizedPayloadSession.id, normalizedPayloadSession);
      state.sessionId = normalizedPayloadSession.id;
      state.activeSession = normalizedPayloadSession;
      state.messages = normalizedPayloadSession.messages.slice();
    } else if (assistantMessage) {
      const normalizedAssistant = normalizeMessage(assistantMessage, state.messages.length + 1);

      const hasAssistantAlready = state.messages.some(function (msg) {
        return msg.id && msg.id === normalizedAssistant.id;
      });

      if (!hasAssistantAlready) {
        state.messages = state.messages.concat([normalizedAssistant]);
      }
    }

    if (payload && payload.memory_items) {
      state.memoryItems = normalizeArray(payload.memory_items).map(normalizeMemoryItem);
    }

    if (payload && (payload.web_items || payload.web_results)) {
      state.webItems = normalizeArray(payload.web_items || payload.web_results).map(normalizeWebItem);
    }
  }

  function bindUi() {
    const sendBtn = byId("sendBtn");
    const chatInput = byId("chatInput");
    const uploadBtn = byId("uploadBtn");
    const fileInput = byId("fileInput");
    const sessionRoot =
      byId("sessionList") ||
      byId("sessionsList") ||
      qs("[data-role='session-list']") ||
      qs(".nova-session-list");
    const memoryToggle = byId("memoryPanelToggle");
    const artifactsToggle = byId("artifactsPanelToggle");
    const webToggle = byId("webPanelToggle");
    const closeBtn = byId("rightRailClose");

    if (sendBtn) {
      sendBtn.addEventListener("click", function () {
        sendMessage();
      });
    }

    if (chatInput) {
      chatInput.addEventListener("input", autosizeComposer);
      chatInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage();
        }
      });
      autosizeComposer();
    }

    if (uploadBtn && fileInput) {
      uploadBtn.addEventListener("click", function () {
        fileInput.click();
      });
    }

    if (fileInput) {
      fileInput.addEventListener("change", function (event) {
        const files = Array.from((event.target && event.target.files) || []);
        if (!files.length) return;

        const next = files.map(function (file) {
          return {
            id: "pending-" + Date.now() + "-" + Math.random().toString(36).slice(2),
            name: file.name,
            file: file,
            size: file.size,
            type: file.type
          };
        });

        state.pendingFiles = state.pendingFiles.concat(next);
        renderPendingFiles();
        fileInput.value = "";
      });
    }

    document.addEventListener("click", function (event) {
      const removeBtn = event.target.closest("[data-remove-file-index]");
      if (removeBtn) {
        const index = Number(removeBtn.getAttribute("data-remove-file-index"));
        if (!Number.isNaN(index)) {
          state.pendingFiles.splice(index, 1);
          renderPendingFiles();
        }
        return;
      }

      const sessionBtn = event.target.closest("[data-session-id]");
      if (sessionBtn) {
        const sessionId = safe(sessionBtn.getAttribute("data-session-id"));
        if (sessionId && sessionId !== state.sessionId) {
          state.sessionId = sessionId;
          state.activeSession = state.sessionMap.get(sessionId) || null;
          state.messages = normalizeArray(state.activeSession && state.activeSession.messages);
          renderAll(true);
          scheduleRefresh(0);
        }
        return;
      }
    });

    if (sessionRoot) {
      sessionRoot.addEventListener("keydown", function (event) {
        const item = event.target.closest("[data-session-id]");
        if (!item) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          item.click();
        }
      });
    }

    if (memoryToggle) {
      memoryToggle.addEventListener("click", function () {
        openPanel(state.panel === "memory" ? "" : "memory");
      });
    }

    if (artifactsToggle) {
      artifactsToggle.addEventListener("click", function () {
        openPanel(state.panel === "artifacts" ? "" : "artifacts");
      });
    }

    if (webToggle) {
      webToggle.addEventListener("click", function () {
        openPanel(state.panel === "web" ? "" : "web");
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        closePanel();
      });
    }

    window.addEventListener("nova:open-panel", function (event) {
      const panel = safe(event.detail && event.detail.panel);
      if (panel) openPanel(panel);
    });

    window.addEventListener("nova:artifact-owning-session-request", function (event) {
      const owningSessionId = safe(
        event.detail && (event.detail.sessionId || event.detail.session_id || event.detail.owning_session_id)
      );
      if (!owningSessionId) return;
      if (owningSessionId === state.sessionId) return;

      state.sessionId = owningSessionId;
      renderSessions(true);
      scheduleRefresh(0);
    });

    window.addEventListener("nova:state-refresh-request", function () {
      scheduleRefresh(0);
    });
  }

  async function boot() {
    if (state.booted) return;
    state.booted = true;

    log("boot start", { at: new Date().toISOString() });

    bindUi();
    syncPanelVisibility();
    renderPendingFiles();
    await refreshState();

    log("boot complete", {
      sessionId: state.sessionId,
      sessionCount: state.sessions.length
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();