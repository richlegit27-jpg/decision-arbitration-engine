(function () {
  "use strict";

  const LOG = "[NovaComposerBundle]";
  const API = {
    state: "/api/state",
    chat: "/api/chat",
    upload: "/api/upload",
    newSession: "/api/session/new",
    renameSession: "/api/session/rename",
    pinSession: "/api/session/pin",
    deleteSession: "/api/session/delete"
  };

  const state = {
    booted: false,
    sending: false,
    uploading: false,
    refreshing: false,
    sidebarCollapsed: false,
    sessionId: "",
    sessions: [],
    messages: [],
    memoryItems: [],
    artifacts: [],
    webItems: [],
    pendingUploads: [],
    activePanel: "artifacts",
    lastUserMessage: null
  };

  const els = {};

  function log() {
    try { console.log(LOG, ...arguments); } catch (_) {}
  }

  function warn() {
    try { console.warn(LOG, ...arguments); } catch (_) {}
  }

  function err() {
    try { console.error(LOG, ...arguments); } catch (_) {}
  }

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function safe(value) {
    return value == null ? "" : String(value);
  }

  function esc(value) {
    return safe(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function nl2br(value) {
    return esc(value).replace(/\n/g, "<br>");
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function nowIso() {
    try { return new Date().toISOString(); } catch (_) { return ""; }
  }

  function shortId() {
    return Math.random().toString(36).slice(2, 10);
  }

  function pick() {
    for (let i = 0; i < arguments.length; i += 1) {
      const value = arguments[i];
      if (value != null && value !== "") return value;
    }
    return "";
  }

  function bytesLabel(size) {
    const n = Number(size || 0);
    if (!n) return "";
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
    return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  }

  function isImageLike(name, mime) {
    const n = safe(name).toLowerCase();
    const m = safe(mime).toLowerCase();
    return m.startsWith("image/") || /\.(png|jpg|jpeg|gif|webp|bmp|svg)$/i.test(n);
  }

  function isVideoLike(name, mime) {
    const n = safe(name).toLowerCase();
    const m = safe(mime).toLowerCase();
    return m.startsWith("video/") || /\.(mp4|webm|mov|m4v|avi|mkv)$/i.test(n);
  }

  function isAudioLike(name, mime) {
    const n = safe(name).toLowerCase();
    const m = safe(mime).toLowerCase();
    return m.startsWith("audio/") || /\.(mp3|wav|ogg|m4a|aac|flac)$/i.test(n);
  }

  function normalizeUrl(url) {
    const value = safe(url);
    if (!value) return "";
    if (
      value.startsWith("http://") ||
      value.startsWith("https://") ||
      value.startsWith("/")
    ) {
      return value;
    }
    return `/api/uploads/${value}`;
  }

  function debugEnsure() {
    try {
      if (!window.__novaDebug) {
        window.__novaDebug = {
          action: "",
          request: null,
          response: null,
          error: "",
          statusText: "",
          timeline: []
        };
      }
      return window.__novaDebug;
    } catch (_) {
      return {
        action: "",
        request: null,
        response: null,
        error: "",
        statusText: "",
        timeline: []
      };
    }
  }

  function debugPush(type, action, payload) {
    try {
      const dbg = debugEnsure();
      dbg.action = action || dbg.action || "";
      if (type === "request") dbg.request = payload || null;
      if (type === "response") dbg.response = payload || null;
      if (type === "error") dbg.error = safe((payload && payload.message) || payload || "");
      dbg.timeline = asArray(dbg.timeline);
      dbg.timeline.unshift({
        at: new Date().toLocaleTimeString(),
        type: safe(type || "event"),
        action: safe(action || ""),
        text: typeof payload === "string" ? payload : "",
        responsePreview: payload && typeof payload === "object" ? JSON.stringify(payload, null, 2).slice(0, 900) : "",
        error: type === "error" ? safe((payload && payload.message) || payload || "") : ""
      });
      dbg.timeline = dbg.timeline.slice(0, 60);
      window.__novaDebug = dbg;
      window.dispatchEvent(new CustomEvent("nova:debug-updated"));
    } catch (_) {}
  }

  function setStatus(text, mode) {
    const value = safe(text);
    if (els.composerStatus) {
      els.composerStatus.textContent = value;
      els.composerStatus.dataset.mode = safe(mode || "");
    }
    try {
      const dbg = debugEnsure();
      dbg.statusText = value;
      window.__novaDebug = dbg;
      window.dispatchEvent(new CustomEvent("nova:debug-updated"));
    } catch (_) {}
  }

  function dispatch(name, detail) {
    try {
      window.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
    } catch (_) {}
  }

  function setBusy(flag) {
    state.sending = !!flag;
    if (els.sendBtn) els.sendBtn.disabled = !!flag || state.uploading;
    document.body.dataset.novaSending = flag ? "true" : "false";
  }

  function setUploading(flag) {
    state.uploading = !!flag;
    if (els.attachBtn) els.attachBtn.disabled = !!flag;
    if (els.sendBtn) els.sendBtn.disabled = !!flag || state.sending;
    document.body.dataset.novaUploading = flag ? "true" : "false";
  }

  function draftTextKey(sessionId) {
    return `nova_draft_text:${safe(sessionId) || "default"}`;
  }

  function draftAttachmentsKey(sessionId) {
    return `nova_draft_attachments:${safe(sessionId) || "default"}`;
  }

  function saveDraftText() {
    try {
      if (!els.chatInput) return;
      localStorage.setItem(draftTextKey(state.sessionId), safe(els.chatInput.value));
    } catch (_) {}
  }

  function loadDraftText() {
    try {
      if (!els.chatInput) return;
      els.chatInput.value = safe(localStorage.getItem(draftTextKey(state.sessionId)));
      autoGrowTextarea();
    } catch (_) {}
  }

  function clearDraftText(sessionId) {
    try { localStorage.removeItem(draftTextKey(sessionId || state.sessionId)); } catch (_) {}
  }

  function savePendingUploads() {
    try {
      localStorage.setItem(draftAttachmentsKey(state.sessionId), JSON.stringify(asArray(state.pendingUploads)));
    } catch (e) {
      warn("savePendingUploads failed", e);
    }
  }

  function loadPendingUploads() {
    try {
      const raw = localStorage.getItem(draftAttachmentsKey(state.sessionId));
      state.pendingUploads = asArray(JSON.parse(raw || "[]")).map(normalizeAttachment).filter(Boolean);
    } catch (e) {
      warn("loadPendingUploads failed", e);
      state.pendingUploads = [];
    }
  }

  function clearPendingUploads(sessionId) {
    try { localStorage.removeItem(draftAttachmentsKey(sessionId || state.sessionId)); } catch (_) {}
    state.pendingUploads = [];
    renderAttachmentTray();
  }

  function normalizeAttachment(input) {
    if (!input || typeof input !== "object") return null;

    const id = pick(input.id, input.attachment_id, input.file_id, input.upload_id, shortId());
    const name = pick(input.name, input.filename, input.original_filename, input.original_name, "attachment");
    const storedName = pick(
      input.stored_name,
      input.stored_filename,
      input.saved_as,
      input.server_filename,
      input.path && safe(input.path).split(/[\\/]/).pop()
    );
    const mime = pick(input.mime_type, input.content_type, input.mimetype, input.type);
    const rawUrl = pick(input.url, input.file_url, input.upload_url, input.preview_url, input.src, storedName);
    const kind = pick(
      input.kind,
      isImageLike(name, mime) ? "image" :
      isVideoLike(name, mime) ? "video" :
      isAudioLike(name, mime) ? "audio" : "file"
    );

    return {
      id: safe(id),
      name: safe(name),
      stored_name: safe(storedName),
      url: safe(normalizeUrl(rawUrl)),
      preview_url: safe(normalizeUrl(pick(input.preview_url, rawUrl))),
      mime_type: safe(mime),
      size: Number(pick(input.size, input.file_size, input.bytes, 0)) || 0,
      kind: safe(kind),
      uploaded_at: safe(pick(input.uploaded_at, input.created_at, nowIso()))
    };
  }

  function normalizeAttachmentList(value) {
    return []
      .concat(asArray(value))
      .concat(asArray(value && value.files))
      .concat(asArray(value && value.attachments))
      .concat(asArray(value && value.uploads))
      .map(normalizeAttachment)
      .filter(Boolean);
  }

  function normalizeMessageAttachments(message) {
    return []
      .concat(asArray(message.attachments))
      .concat(asArray(message.files))
      .concat(asArray(message.uploads))
      .concat(asArray(message.images))
      .concat(asArray(message.media))
      .concat(asArray(message.meta && message.meta.attachments))
      .concat(asArray(message.debug && message.debug.attachments))
      .map(normalizeAttachment)
      .filter(Boolean);
  }

  function normalizeMessage(input) {
    if (!input || typeof input !== "object") return null;
    return {
      id: safe(pick(input.id, input.message_id, shortId())),
      role: safe(pick(input.role, input.sender, input.type, "assistant")).toLowerCase(),
      content: safe(pick(input.content, input.text, input.message, input.body)),
      created_at: safe(pick(input.created_at, input.timestamp, input.time, nowIso())),
      attachments: normalizeMessageAttachments(input),
      raw: input
    };
  }

  function normalizeSession(session) {
    if (!session || typeof session !== "object") return null;
    return {
      id: safe(pick(session.id, session.session_id)),
      title: safe(pick(session.title, session.name, "New chat")),
      pinned: !!session.pinned,
      updated_at: safe(pick(session.updated_at, session.created_at, nowIso())),
      message_count: Number(pick(session.message_count, 0)) || 0,
      last_message_preview: safe(pick(session.last_message_preview, ""))
    };
  }

  function getActiveSession() {
    return state.sessions.find(function (s) {
      return s.id === state.sessionId;
    }) || null;
  }

  function inferStatePayload(payload) {
    const data = payload && typeof payload === "object" ? payload : {};
    const sessions = asArray(data.sessions).map(normalizeSession).filter(Boolean);

    const activeSessionId = safe(
      pick(
        data.active_session_id,
        data.session_id,
        data.current_session_id,
        data.session && data.session.id,
        state.sessionId,
        sessions[0] && sessions[0].id
      )
    );

    let activeSession = null;
    if (activeSessionId) {
      activeSession = sessions.find(function (s) { return s.id === activeSessionId; }) || null;
    }
    if (!activeSession && sessions.length) activeSession = sessions[0];

    const sessionRoot = data.session || activeSession || {};
    const messages = []
      .concat(asArray(sessionRoot.messages))
      .concat(asArray(data.messages))
      .map(normalizeMessage)
      .filter(Boolean);

    return {
      sessions: sessions,
      sessionId: safe(pick(activeSessionId, activeSession && activeSession.id)),
      messages: messages,
      memoryItems: asArray(data.memory_items || data.memory || []),
      artifacts: asArray(data.artifacts || []),
      webItems: asArray(data.web_items || data.web || [])
    };
  }

  async function readJson(res) {
    try { return await res.json(); } catch (_) { return null; }
  }

  async function apiGet(url) {
    debugPush("request", `GET ${url}`, { method: "GET", url: url });
    const res = await fetch(url, { method: "GET" });
    const data = await readJson(res);
    debugPush("response", `GET ${url}`, { status: res.status, ok: res.ok, data: data });

    if (!res.ok) {
      const e = new Error(safe(data && (data.error || data.message)) || `Request failed (${res.status})`);
      e.response = data;
      debugPush("error", `GET ${url}`, e);
      throw e;
    }

    return data || {};
  }

  async function apiPost(url, body) {
    debugPush("request", `POST ${url}`, { method: "POST", url: url, body: body || {} });
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {})
    });
    const data = await readJson(res);
    debugPush("response", `POST ${url}`, { status: res.status, ok: res.ok, data: data });

    if (!res.ok) {
      const e = new Error(safe(data && (data.error || data.message)) || `Request failed (${res.status})`);
      e.response = data;
      debugPush("error", `POST ${url}`, e);
      throw e;
    }

    return data || {};
  }

  function autoGrowTextarea() {
    if (!els.chatInput) return;
    els.chatInput.style.height = "auto";
    els.chatInput.style.height = `${Math.min(els.chatInput.scrollHeight, 240)}px`;
  }

  function formatTime(value) {
    const raw = safe(value);
    if (!raw) return "";
    try {
      const d = new Date(raw);
      if (Number.isNaN(d.getTime())) return raw;
      return d.toLocaleString();
    } catch (_) {
      return raw;
    }
  }

  function summarizeText(value, limit) {
    const text = safe(value).trim();
    const max = typeof limit === "number" ? limit : 180;
    if (!text) return "";
    if (text.length <= max) return text;
    return text.slice(0, max) + "…";
  }

  function attachmentHtml(item) {
    const a = normalizeAttachment(item);
    if (!a) return "";

    const subParts = [];
    if (a.mime_type) subParts.push(a.mime_type);
    if (a.size) subParts.push(bytesLabel(a.size));

    if (a.kind === "image") {
      return `
        <div class="nova-message-attachment image">
          <a class="nova-message-attachment-image-link" href="${esc(a.url || a.preview_url)}" target="_blank" rel="noopener noreferrer">
            <img class="nova-message-attachment-image" src="${esc(a.preview_url || a.url)}" alt="${esc(a.name)}" />
          </a>
          <div class="nova-message-attachment-meta">
            <div class="nova-message-attachment-name">${esc(a.name)}</div>
            ${subParts.length ? `<div class="nova-message-attachment-sub">${esc(subParts.join(" • "))}</div>` : ``}
          </div>
        </div>
      `;
    }

    return `
      <a class="nova-message-attachment file" href="${esc(a.url || "#")}" target="_blank" rel="noopener noreferrer">
        <div class="nova-message-attachment-icon">${a.kind === "video" ? "🎬" : a.kind === "audio" ? "🎧" : "📄"}</div>
        <div class="nova-message-attachment-meta">
          <div class="nova-message-attachment-name">${esc(a.name)}</div>
          ${subParts.length ? `<div class="nova-message-attachment-sub">${esc(subParts.join(" • "))}</div>` : ``}
        </div>
      </a>
    `;
  }

  function messageHtml(msg) {
    const role = safe(msg.role || "assistant");
    const attachments = asArray(msg.attachments);
    const time = formatTime(msg.created_at);

    return `
      <article class="nova-message ${role}">
        <div class="nova-message-inner">
          ${attachments.length ? `<div class="nova-message-attachments">${attachments.map(attachmentHtml).join("")}</div>` : ``}
          <div class="nova-message-markdown">${nl2br(msg.content || "")}</div>
          <div class="nova-message-meta-row">
            <div class="nova-message-time">${esc(time)}</div>
            ${role === "assistant" ? `
              <div class="nova-message-actions">
                <button class="nova-subtle-btn" type="button" data-copy-message="${esc(msg.id)}">Copy</button>
                <button class="nova-subtle-btn" type="button" data-regenerate-message="${esc(msg.id)}">Regenerate</button>
              </div>
            ` : ``}
          </div>
        </div>
      </article>
    `;
  }

  function renderTopbar() {
    const active = getActiveSession();
    if (els.activeSessionTitle) {
      els.activeSessionTitle.textContent = safe(active && active.title) || "Nova";
    }
    if (els.activeSessionSubtitle) {
      els.activeSessionSubtitle.textContent = active
        ? `${safe(active.message_count || state.messages.length)} message${Number(active.message_count || state.messages.length) === 1 ? "" : "s"}`
        : "Fast local AI workspace";
    }
    if (els.activePanelPill) {
      const name = state.activePanel === "memory" ? "Memory" : state.activePanel === "web" ? "Web" : "Artifacts";
      els.activePanelPill.textContent = name;
    }
  }

  function renderSessionCard(session) {
    const isActive = safe(session.id) === safe(state.sessionId);
    const pinText = session.pinned ? "Unpin" : "Pin";

    return `
      <div class="nova-session-item ${isActive ? "is-active" : ""}">
        <button class="nova-session-main" type="button" data-session-open="${esc(session.id)}">
          <div class="nova-session-title">${esc(session.title || "New chat")}</div>
          <div class="nova-panel-card-sub">
            ${session.pinned ? "Pinned • " : ""}${esc(formatTime(session.updated_at) || "")}
          </div>
          ${session.last_message_preview ? `<div class="nova-panel-card-text">${esc(summarizeText(session.last_message_preview, 120))}</div>` : ``}
        </button>
        <div class="nova-session-actions">
          <button class="nova-subtle-btn" type="button" data-session-rename="${esc(session.id)}">Rename</button>
          <button class="nova-subtle-btn" type="button" data-session-pin="${esc(session.id)}">${esc(pinText)}</button>
          <button class="nova-subtle-btn danger" type="button" data-session-delete="${esc(session.id)}">Delete</button>
        </div>
      </div>
    `;
  }

  function renderSessions() {
    const items = asArray(state.sessions).slice().sort(function (a, b) {
      if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;
      return safe(b.updated_at).localeCompare(safe(a.updated_at));
    });

    if (els.sessionCountBadge) els.sessionCountBadge.textContent = String(items.length);

    if (els.sessionsList) {
      els.sessionsList.innerHTML = items.length
        ? items.map(renderSessionCard).join("")
        : `<div class="nova-panel-empty">No chats yet.</div>`;
    }

    if (els.miniSessionMarkers) {
      els.miniSessionMarkers.innerHTML = items.slice(0, 24).map(function (session) {
        const active = safe(session.id) === safe(state.sessionId);
        return `
          <button
            class="nova-mini-session-marker ${active ? "is-active" : ""}"
            type="button"
            title="${esc(session.title || "Chat")}"
            aria-label="${esc(session.title || "Chat")}"
            data-session-open="${esc(session.id)}">
          </button>
        `;
      }).join("");
    }
  }

  function renderMessages() {
    if (!els.messages) return;

    const items = asArray(state.messages);
    if (!items.length) {
      els.messages.innerHTML = "";
      if (els.novaEmptyState) els.novaEmptyState.classList.add("is-visible");
      return;
    }

    if (els.novaEmptyState) els.novaEmptyState.classList.remove("is-visible");
    els.messages.innerHTML = items.map(messageHtml).join("");
    scrollMessagesToBottom(false);
  }

  function renderMemoryPanel() {
    if (!els.memoryList) return;

    const items = asArray(state.memoryItems);
    if (els.memoryCountBadge) els.memoryCountBadge.textContent = String(items.length);

    els.memoryList.innerHTML = items.length
      ? items.map(function (item, index) {
          const title = safe(item && (item.title || item.key || item.label || `Memory ${index + 1}`));
          const text = safe(item && (item.content || item.text || item.value || item.summary || ""));
          return `
            <div class="nova-panel-card">
              <div class="nova-panel-card-title">${esc(title)}</div>
              ${text ? `<div class="nova-panel-card-text">${esc(text)}</div>` : ``}
            </div>
          `;
        }).join("")
      : `<div class="nova-panel-empty">No memory yet.</div>`;
  }

  function renderWebPanel() {
    if (!els.webList) return;

    const items = asArray(state.webItems);
    if (els.webCountBadge) els.webCountBadge.textContent = String(items.length);

    els.webList.innerHTML = items.length
      ? items.map(function (item) {
          const title = safe(item && (item.title || item.url || "Web result"));
          const sub = safe(item && (item.url || item.site_name || ""));
          const preview = safe(item && (item.summary || item.content || item.preview || "")).slice(0, 220);

          return `
            <div class="nova-panel-card">
              <div class="nova-panel-card-title">${esc(title)}</div>
              ${sub ? `<div class="nova-panel-card-sub">${esc(sub)}</div>` : ""}
              ${preview ? `<div class="nova-panel-card-text">${esc(preview)}</div>` : ""}
            </div>
          `;
        }).join("")
      : `<div class="nova-panel-empty">No web results yet.</div>`;
  }

  function renderAttachmentTray() {
    if (!els.attachmentTray) return;

    const items = asArray(state.pendingUploads);
    if (!items.length) {
      els.attachmentTray.hidden = true;
      els.attachmentTray.innerHTML = "";
      return;
    }

    els.attachmentTray.hidden = false;
    els.attachmentTray.innerHTML = items.map(function (item) {
      const a = normalizeAttachment(item);
      if (!a) return "";
      return `
        <div class="nova-attachment-chip">
          <div class="nova-attachment-chip-main">
            <span class="nova-attachment-chip-icon">${a.kind === "image" ? "🖼️" : a.kind === "video" ? "🎬" : a.kind === "audio" ? "🎧" : "📄"}</span>
            <span class="nova-attachment-chip-name">${esc(a.name)}</span>
          </div>
          <button class="nova-subtle-btn" type="button" data-remove-upload="${esc(a.id)}">Remove</button>
        </div>
      `;
    }).join("");
  }

  function renderArtifactCountOnly() {
    if (els.artifactCountBadge) {
      els.artifactCountBadge.textContent = String(asArray(state.artifacts).length);
    }
  }

  function renderAll() {
    renderSessions();
    renderTopbar();
    renderMessages();
    renderMemoryPanel();
    renderWebPanel();
    renderAttachmentTray();
    renderArtifactCountOnly();
    applyShellState();

    dispatch("nova:composer-state", {
      session_id: state.sessionId,
      sessions: state.sessions,
      messages: state.messages,
      artifacts: state.artifacts,
      memory_items: state.memoryItems,
      web_items: state.webItems
    });
  }

  function scrollMessagesToBottom(smooth) {
    if (!els.messages) return;
    try {
      els.messages.scrollTo({
        top: els.messages.scrollHeight,
        behavior: smooth ? "smooth" : "auto"
      });
    } catch (_) {
      els.messages.scrollTop = els.messages.scrollHeight;
    }
  }

  function addPendingUploads(items) {
    const next = asArray(items).map(normalizeAttachment).filter(Boolean);

    next.forEach(function (item) {
      const exists = state.pendingUploads.some(function (current) {
        return current.id === item.id || (current.name === item.name && current.url === item.url);
      });
      if (!exists) state.pendingUploads.push(item);
    });

    savePendingUploads();
    renderAttachmentTray();
  }

  function removePendingUploadById(id) {
    state.pendingUploads = state.pendingUploads.filter(function (item) {
      return safe(item.id) !== safe(id);
    });
    savePendingUploads();
    renderAttachmentTray();
  }

  async function uploadFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;

    setUploading(true);
    setStatus("Uploading…", "warn");

    try {
      const form = new FormData();
      files.forEach(function (file) {
        form.append("files", file);
      });

      debugPush("request", "POST /api/upload", { file_count: files.length, names: files.map(function (f) { return f.name; }) });

      const res = await fetch(API.upload, { method: "POST", body: form });
      const data = await readJson(res);
      debugPush("response", "POST /api/upload", { status: res.status, ok: res.ok, data: data });

      if (!res.ok) {
        throw new Error(safe(data && (data.error || data.message)) || `Upload failed (${res.status})`);
      }

      const uploaded = normalizeAttachmentList(data && (data.files || data.attachments || data.uploads || data.items || data));
      addPendingUploads(uploaded);
      setStatus(`Uploaded ${uploaded.length || files.length} file(s).`, "ok");
    } catch (e) {
      debugPush("error", "POST /api/upload", e);
      setStatus(safe(e.message || "Upload failed."), "error");
    } finally {
      if (els.fileInput) els.fileInput.value = "";
      setUploading(false);
    }
  }

  function applyShellState() {
    if (els.appShell) {
      els.appShell.dataset.sidebarCollapsed = state.sidebarCollapsed ? "true" : "false";
      els.appShell.dataset.railPanel = state.activePanel;
    }

    const panels = {
      memory: els.memoryPanel,
      artifacts: els.artifactsPanel,
      web: els.webPanel
    };

    Object.keys(panels).forEach(function (key) {
      const el = panels[key];
      if (el) el.classList.toggle("is-active", key === state.activePanel);
    });

    [
      ["memory", els.memoryPanelToggle],
      ["artifacts", els.artifactsPanelToggle],
      ["web", els.webPanelToggle]
    ].forEach(function (pair) {
      const key = pair[0];
      const btn = pair[1];
      if (btn) btn.classList.toggle("is-active", key === state.activePanel);
    });
  }

  function setAppShellPanel(panel) {
    state.activePanel = panel === "memory" || panel === "web" ? panel : "artifacts";
    applyShellState();
    renderTopbar();
  }

  function toggleSidebarCollapsed() {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    applyShellState();
  }

  async function refreshState(opts) {
    if (state.refreshing) return;
    state.refreshing = true;

    const requestedSessionId = safe(opts && opts.sessionId) || safe(state.sessionId);
    const url = requestedSessionId ? `${API.state}?session_id=${encodeURIComponent(requestedSessionId)}` : API.state;

    setStatus("Refreshing…", "warn");

    try {
      const payload = await apiGet(url);
      const next = inferStatePayload(payload);

      state.sessions = next.sessions;
      state.sessionId = next.sessionId;
      state.messages = next.messages;
      state.memoryItems = next.memoryItems;
      state.artifacts = next.artifacts;
      state.webItems = next.webItems;

      loadDraftText();
      loadPendingUploads();
      renderAll();
      setStatus("Ready", "ok");
      return payload;
    } finally {
      state.refreshing = false;
    }
  }

  async function switchSession(sessionId) {
    const id = safe(sessionId);
    if (!id || id === state.sessionId) return;

    saveDraftText();
    savePendingUploads();
    state.sessionId = id;
    await refreshState({ sessionId: id });
  }

  async function createNewSession() {
    try {
      setStatus("Creating chat…", "warn");
      const data = await apiPost(API.newSession, {});
      const next = inferStatePayload(data);

      state.sessions = next.sessions;
      state.sessionId = next.sessionId;
      state.messages = next.messages;
      state.memoryItems = next.memoryItems;
      state.artifacts = next.artifacts;
      state.webItems = next.webItems;

      clearDraftText(state.sessionId);
      clearPendingUploads(state.sessionId);
      renderAll();

      if (els.chatInput) els.chatInput.focus();
      setStatus("New chat created.", "ok");
    } catch (e) {
      setStatus(safe(e.message || "New chat failed."), "error");
    }
  }

  async function renameSession(sessionId) {
    const id = safe(sessionId);
    if (!id) return;

    const current = state.sessions.find(function (s) { return s.id === id; });
    const title = window.prompt("Rename chat", safe(current && current.title) || "New chat");
    if (title == null) return;

    try {
      setStatus("Renaming chat…", "warn");
      await apiPost(API.renameSession, {
        session_id: id,
        title: safe(title).trim()
      });
      await refreshState({ sessionId: id });
      setStatus("Chat renamed.", "ok");
    } catch (e) {
      setStatus(safe(e.message || "Rename failed."), "error");
    }
  }

  async function togglePinSession(sessionId) {
    const id = safe(sessionId);
    if (!id) return;

    try {
      setStatus("Saving pin…", "warn");
      await apiPost(API.pinSession, { session_id: id });
      await refreshState({ sessionId: state.sessionId || id });
      setStatus("Pin saved.", "ok");
    } catch (e) {
      setStatus(safe(e.message || "Pin failed."), "error");
    }
  }

  async function deleteSession(sessionId) {
    const id = safe(sessionId);
    if (!id) return;
    if (!window.confirm("Delete this chat?")) return;

    try {
      setStatus("Deleting chat…", "warn");
      const data = await apiPost(API.deleteSession, { session_id: id });
      const nextId = safe(data && (data.next_session_id || data.active_session_id || ""));

      clearDraftText(id);
      clearPendingUploads(id);
      state.sessionId = nextId || "";
      await refreshState({ sessionId: nextId });
      setStatus("Chat deleted.", "ok");
    } catch (e) {
      setStatus(safe(e.message || "Delete failed."), "error");
    }
  }

  async function sendMessage(options) {
    const opts = options || {};
    const text = safe(opts.text != null ? opts.text : (els.chatInput && els.chatInput.value)).trim();
    const attachments = asArray(opts.attachments != null ? opts.attachments : state.pendingUploads)
      .map(normalizeAttachment)
      .filter(Boolean);

    if (!text && !attachments.length) {
      setStatus("Nothing to send.", "warn");
      return;
    }

    if (state.sending || state.uploading) return;

    setBusy(true);
    setStatus("Sending…", "working");

    try {
      const result = await apiPost(API.chat, {
        session_id: state.sessionId,
        content: text,
        attachments: attachments
      });

      const next = inferStatePayload(result);
      state.sessions = next.sessions;
      state.sessionId = next.sessionId || state.sessionId;
      state.messages = next.messages;
      state.memoryItems = next.memoryItems;
      state.artifacts = next.artifacts;
      state.webItems = next.webItems;

      if (els.chatInput) {
        els.chatInput.value = "";
        autoGrowTextarea();
      }

      clearDraftText(state.sessionId);
      clearPendingUploads(state.sessionId);
      renderAll();

      state.lastUserMessage = {
        content: text,
        attachments: attachments
      };

      setStatus("Sent.", "ok");
    } catch (e) {
      err("sendMessage failed", e);
      setStatus(safe((e.response && (e.response.error || e.response.message)) || e.message || "Send failed."), "error");
    } finally {
      setBusy(false);
    }
  }

  async function regenerateLastUserMessage() {
    if (!state.lastUserMessage) {
      setStatus("No user message to regenerate.", "warn");
      return;
    }

    const text = safe(state.lastUserMessage.content);
    const attachments = asArray(state.lastUserMessage.attachments).map(normalizeAttachment).filter(Boolean);

    if (els.chatInput) {
      els.chatInput.value = text;
      autoGrowTextarea();
    }

    state.pendingUploads = attachments.slice();
    savePendingUploads();
    renderAttachmentTray();

    await sendMessage({
      text: text,
      attachments: attachments
    });
  }

  async function copyMessageById(messageId) {
    const match = state.messages.find(function (msg) {
      return safe(msg.id) === safe(messageId);
    });

    if (!match) {
      setStatus("Message not found.", "warn");
      return;
    }

    try {
      await navigator.clipboard.writeText(safe(match.content));
      setStatus("Copied.", "ok");
    } catch (_) {
      setStatus("Copy failed.", "error");
    }
  }

  function bindPanelButtons() {
    if (els.memoryPanelToggle) {
      els.memoryPanelToggle.addEventListener("click", function () { setAppShellPanel("memory"); });
    }
    if (els.artifactsPanelToggle) {
      els.artifactsPanelToggle.addEventListener("click", function () { setAppShellPanel("artifacts"); });
    }
    if (els.webPanelToggle) {
      els.webPanelToggle.addEventListener("click", function () { setAppShellPanel("web"); });
    }
  }

  function bindDom() {
    els.appShell = qs("#novaAppShell");
    els.sidebarToggle = qs("#sidebarToggle");
    els.newSessionBtn = qs("#newSessionBtn");
    els.newSessionMiniBtn = qs("#newSessionMiniBtn");
    els.sessionsList = qs("#sessionsList");
    els.sessionCountBadge = qs("#sessionCountBadge");
    els.miniSessionMarkers = qs("#miniSessionMarkers");

    els.activeSessionTitle = qs("#activeSessionTitle");
    els.activeSessionSubtitle = qs("#activeSessionSubtitle");
    els.activePanelPill = qs("#activePanelPill");

    els.novaEmptyState = qs("#novaEmptyState");
    els.messages = qs("#messages");

    els.attachmentTray = qs("#attachmentTray");
    els.attachBtn = qs("#attachBtn");
    els.voiceBtn = qs("#voiceBtn");
    els.clearChatBtn = qs("#clearChatBtn");
    els.composerStatus = qs("#composerStatus");
    els.chatInput = qs("#chatInput");
    els.sendBtn = qs("#sendBtn");

    els.memoryPanelToggle = qs("#memoryPanelToggle");
    els.artifactsPanelToggle = qs("#artifactsPanelToggle");
    els.webPanelToggle = qs("#webPanelToggle");

    els.memoryPanel = qs("#memoryPanel");
    els.artifactsPanel = qs("#artifactsPanel");
    els.webPanel = qs("#webPanel");

    els.memoryList = qs("#memoryList");
    els.artifactCountBadge = qs("#artifactCountBadge");
    els.webList = qs("#webList");

    els.memoryCountBadge = qs("#memoryCountBadge");
    els.webCountBadge = qs("#webCountBadge");

    els.fileInput = qs("#fileInput");
    if (!els.fileInput) {
      els.fileInput = document.createElement("input");
      els.fileInput.type = "file";
      els.fileInput.multiple = true;
      els.fileInput.hidden = true;
      els.fileInput.id = "novaHiddenFileInput";
      document.body.appendChild(els.fileInput);
    }
  }

  function bindEvents() {
    bindPanelButtons();

    if (els.sidebarToggle) {
      els.sidebarToggle.addEventListener("click", toggleSidebarCollapsed);
    }

    if (els.newSessionBtn) {
      els.newSessionBtn.addEventListener("click", createNewSession);
    }

    if (els.newSessionMiniBtn) {
      els.newSessionMiniBtn.addEventListener("click", createNewSession);
    }

    if (els.attachBtn) {
      els.attachBtn.addEventListener("click", function () {
        if (els.fileInput) els.fileInput.click();
      });
    }

    if (els.fileInput) {
      els.fileInput.addEventListener("change", function (event) {
        uploadFiles(event.target.files);
      });
    }

    if (els.clearChatBtn) {
      els.clearChatBtn.addEventListener("click", function () {
        if (els.chatInput) {
          els.chatInput.value = "";
          autoGrowTextarea();
        }
        state.pendingUploads = [];
        savePendingUploads();
        renderAttachmentTray();
        setStatus("Composer cleared.", "ok");
      });
    }

    if (els.voiceBtn) {
      els.voiceBtn.addEventListener("click", function () {
        setStatus("Voice not wired yet.", "warn");
      });
    }

    if (els.chatInput) {
      els.chatInput.addEventListener("input", function () {
        autoGrowTextarea();
        saveDraftText();
      });

      els.chatInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage();
        }
      });
    }

    if (els.sendBtn) {
      els.sendBtn.addEventListener("click", function () {
        sendMessage();
      });
    }

    document.addEventListener("click", function (event) {
      const openBtn = event.target.closest("[data-session-open]");
      if (openBtn) {
        switchSession(openBtn.getAttribute("data-session-open"));
        return;
      }

      const renameBtn = event.target.closest("[data-session-rename]");
      if (renameBtn) {
        renameSession(renameBtn.getAttribute("data-session-rename"));
        return;
      }

      const pinBtn = event.target.closest("[data-session-pin]");
      if (pinBtn) {
        togglePinSession(pinBtn.getAttribute("data-session-pin"));
        return;
      }

      const deleteBtn = event.target.closest("[data-session-delete]");
      if (deleteBtn) {
        deleteSession(deleteBtn.getAttribute("data-session-delete"));
        return;
      }

      const fillBtn = event.target.closest("[data-fill]");
      if (fillBtn && els.chatInput) {
        els.chatInput.value = safe(fillBtn.getAttribute("data-fill"));
        autoGrowTextarea();
        els.chatInput.focus();
        saveDraftText();
        return;
      }

      const removeUploadBtn = event.target.closest("[data-remove-upload]");
      if (removeUploadBtn) {
        removePendingUploadById(removeUploadBtn.getAttribute("data-remove-upload"));
        return;
      }

      const copyBtn = event.target.closest("[data-copy-message]");
      if (copyBtn) {
        copyMessageById(copyBtn.getAttribute("data-copy-message"));
        return;
      }

      const regenBtn = event.target.closest("[data-regenerate-message]");
      if (regenBtn) {
        regenerateLastUserMessage();
      }
    });

    window.addEventListener("beforeunload", function () {
      saveDraftText();
      savePendingUploads();
    });

    window.addEventListener("nova:jump-to-session", function (event) {
      const sessionId = safe(event && event.detail && event.detail.session_id);
      if (sessionId) switchSession(sessionId);
    });

    window.addEventListener("nova:artifact-count-changed", function (event) {
      const count = Number(event && event.detail && event.detail.count) || 0;
      if (els.artifactCountBadge) els.artifactCountBadge.textContent = String(count);
    });
  }

  async function boot() {
    if (state.booted) return;
    state.booted = true;

    log("boot start");
    bindDom();
    bindEvents();
    autoGrowTextarea();
    applyShellState();
    setAppShellPanel("artifacts");

    try {
      await refreshState({ sessionId: state.sessionId });
      setStatus("Ready", "ok");
    } catch (e) {
      err("boot failed", e);
      setStatus(safe((e.response && (e.response.error || e.response.message)) || e.message || "Boot failed."), "error");
    }

    log("boot complete");
  }

  window.NovaComposerBundle = {
    state: state,
    refreshState: refreshState,
    sendMessage: sendMessage,
    switchSession: switchSession,
    createNewSession: createNewSession,
    setPanel: setAppShellPanel
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();