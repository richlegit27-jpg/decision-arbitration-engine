(function () {
  "use strict";

  const LOG = "[NovaComposerBundle]";
  const API = {
    state: "/api/state",
    chat: "/api/chat",
    streamChat: "/api/chat/stream",
    upload: "/api/upload",
    newSession: "/api/session/new",
    renameSession: "/api/session/rename",
    pinSession: "/api/session/pin",
    deleteSession: "/api/session/delete",
    memoryCreate: "/api/memory/add",
    memoryDelete: "/api/memory/delete"
  };

  const state = {
    booted: false,
    sending: false,
    uploading: false,
    refreshing: false,
    sidebarCollapsed: false,
    rightRailOpen: true,
    sessionId: "",
    sessions: [],
    messages: [],
    memoryItems: [],
    artifacts: [],
    webItems: [],
    pendingUploads: [],
    activePanel: "artifacts",
    lastUserMessage: null,
    activeRouteInspectMessageId: "",
    lastStatePayload: null,
    lastRefreshHash: "",
    lastSendNonce: 0
  };

  const els = {};

  function log() {
    try {
      console.log(LOG, ...arguments);
    } catch (_) {}
  }

  function warn() {
    try {
      console.warn(LOG, ...arguments);
    } catch (_) {}
  }

  function err() {
    try {
      console.error(LOG, ...arguments);
    } catch (_) {}
  }

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  function safe(value) {
    return value == null ? "" : String(value);
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function escapeHtml(value) {
    return safe(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function fmtDate(value) {
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

  function shortText(value, max) {
    const s = safe(value).trim();
    const limit = typeof max === "number" ? max : 180;
    if (!s) return "";
    return s.length > limit ? s.slice(0, limit - 1) + "..." : s;
  }

  function hash(value) {
    try {
      return JSON.stringify(value || null);
    } catch (_) {
      return String(Date.now());
    }
  }

  function nl2br(value) {
    return escapeHtml(value).replace(/\n/g, "<br>");
  }

  function setComposerStatus(text, isError) {
    if (!els.composerStatus) return;
    els.composerStatus.textContent = safe(text);
    els.composerStatus.style.color = isError ? "var(--danger)" : "";
  }

  async function requestJson(url, options) {
    const res = await fetch(url, options || {});
    const contentType = res.headers.get("content-type") || "";
    let data = null;

    if (contentType.includes("application/json")) {
      data = await res.json();
    } else {
      data = { ok: res.ok, raw: await res.text() };
    }

    if (!res.ok || (data && data.ok === false)) {
      throw new Error(
        safe(data && (data.error || data.message || data.raw)) ||
          ("Request failed: " + res.status)
      );
    }

    return data || {};
  }

  function normalizeUrl(value) {
    const raw = safe(value).trim();
    if (!raw) return "";
    if (/^https?:\/\//i.test(raw) || raw.startsWith("/")) return raw;
    return raw;
  }

  function normalizeAttachment(raw, fallbackIndex) {
    const item = raw || {};
    return {
      id: safe(item.id || item.attachment_id || ("att-" + (fallbackIndex || 0))),
      name: safe(item.name || item.filename || item.stored_name || item.title || "attachment"),
      url: normalizeUrl(item.url || item.path || item.src || item.preview_url || ""),
      mime_type: safe(item.mime_type || item.mime || item.content_type || ""),
      kind: safe(item.kind || item.type || ""),
      size: Number(item.size || 0)
    };
  }

  function normalizeMessage(raw, fallbackIndex) {
    const item = raw || {};
    return {
      id: safe(item.id || item.message_id || item.uuid || ("msg-" + (fallbackIndex || 0))),
      role: safe(item.role || item.type || item.author || "assistant").toLowerCase(),
      content: safe(item.content || item.text || item.message || item.body || ""),
      created_at: safe(item.created_at || item.createdAt || item.timestamp || ""),
      attachments: asArray(item.attachments).map(normalizeAttachment),
      route_meta:
        (item.route_meta && typeof item.route_meta === "object" && item.route_meta) ||
        (item.routeMeta && typeof item.routeMeta === "object" && item.routeMeta) ||
        (item.meta && item.meta.route_meta && typeof item.meta.route_meta === "object" && item.meta.route_meta) ||
        {},
      meta: item.meta && typeof item.meta === "object" ? item.meta : {},
      badges: asArray(item.badges),
      image_url: safe(item.image_url || "")
    };
  }

  function normalizeSession(raw, fallbackIndex) {
    const item = raw || {};
    const messages = asArray(item.messages).map(normalizeMessage);
    return {
      id: safe(item.id || item.session_id || item.uuid || ("session-" + (fallbackIndex || 0))),
      session_id: safe(item.session_id || item.id || ""),
      title: safe(item.title || item.name || item.label || "New Chat"),
      pinned: !!item.pinned,
      created_at: safe(item.created_at || item.createdAt || ""),
      updated_at: safe(item.updated_at || item.updatedAt || ""),
      message_count: Number(item.message_count || item.messageCount || messages.length || 0),
      last_message_preview: safe(item.last_message_preview || item.preview || item.last_preview || ""),
      messages: messages
    };
  }

  function buildViewerFromArtifact(item) {
    const raw = item || {};
    const viewer = raw.viewer && typeof raw.viewer === "object" ? raw.viewer : {};
    const imageUrl = normalizeUrl(viewer.image_url || raw.image_url || (raw.meta && raw.meta.image_url) || "");
    const sourceUrl = normalizeUrl(
      viewer.source_url ||
        raw.source_url ||
        (raw.meta && raw.meta.source_url) ||
        (raw.web && raw.web.source_url) ||
        (raw.web && raw.web.url) ||
        raw.url ||
        ""
    );
    const body = safe(
      viewer.body ||
        viewer.analysis_text ||
        raw.content ||
        raw.body ||
        raw.preview ||
        raw.summary ||
        (raw.web && raw.web.body) ||
        (raw.web && raw.web.summary) ||
        ""
    );

    let viewerKind = safe(viewer.kind || raw.kind || "artifact");
    if (imageUrl) viewerKind = "image";
    if (!imageUrl && /web/i.test(viewerKind)) viewerKind = "web";

    return {
      kind: viewerKind,
      title: safe(viewer.title || raw.title || raw.kind || "Artifact"),
      body: body,
      analysis_text: safe(viewer.analysis_text || body),
      image_url: imageUrl,
      source_url: sourceUrl
    };
  }

  function normalizeArtifact(raw, fallbackIndex) {
    const item = raw || {};
    const viewer = buildViewerFromArtifact(item);
    return {
      id: safe(item.id || item.artifact_id || ("artifact-" + (fallbackIndex || 0))),
      artifact_id: safe(item.artifact_id || item.id || ""),
      session_id: safe(item.session_id || item.sessionId || ""),
      kind: safe(item.kind || item.type || viewer.kind || "artifact"),
      title: safe(item.title || viewer.title || item.name || "Artifact"),
      content: safe(item.content || item.text || item.body || ""),
      summary: safe(item.summary || (item.meta && item.meta.summary) || ""),
      preview: safe(item.preview || item.summary || item.content || viewer.body || "").slice(0, 220),
      pinned: !!item.pinned,
      created_at: safe(item.created_at || ""),
      updated_at: safe(item.updated_at || item.created_at || ""),
      image_url: viewer.image_url,
      source_url: viewer.source_url,
      viewer: viewer,
      meta: item.meta && typeof item.meta === "object" ? item.meta : {},
      web: item.web && typeof item.web === "object" ? item.web : {},
      debug: item.debug && typeof item.debug === "object" ? item.debug : {},
      extra: item.extra && typeof item.extra === "object" ? item.extra : {}
    };
  }

  function normalizeMemoryItem(raw, fallbackIndex) {
    const item = raw || {};
    const text = safe(item.text || item.content || item.value || item.summary || "");
    return {
      id: safe(item.id || item.memory_id || ("memory-" + (fallbackIndex || 0))),
      memory_id: safe(item.memory_id || item.id || ""),
      title: safe(item.title || item.key || item.label || item.kind || "note"),
      text: text,
      content: text,
      value: text,
      kind: safe(item.kind || item.type || "note"),
      source: safe(item.source || "user"),
      created_at: safe(item.created_at || item.timestamp || ""),
      updated_at: safe(item.updated_at || item.created_at || ""),
      session_id: safe(item.session_id || "")
    };
  }

  function getMemoryListFromPayload(payload) {
    if (!payload || typeof payload !== "object") return [];
    if (Array.isArray(payload.memory_items)) return payload.memory_items;
    if (Array.isArray(payload.memory)) return payload.memory;
    if (payload.memory && typeof payload.memory === "object" && Array.isArray(payload.memory.items)) {
      return payload.memory.items;
    }
    return [];
  }

  function getArtifactListFromPayload(payload) {
    if (!payload || typeof payload !== "object") return [];
    if (Array.isArray(payload.artifacts)) return payload.artifacts;
    if (payload.artifacts && typeof payload.artifacts === "object" && Array.isArray(payload.artifacts.items)) {
      return payload.artifacts.items;
    }
    return [];
  }

  function isWebArtifact(item) {
    const kind = safe(item && (item.kind || (item.viewer && item.viewer.kind) || "")).toLowerCase();
    return kind.indexOf("web") >= 0;
  }

  function getWebListFromPayload(payload, artifacts) {
    if (!payload || typeof payload !== "object") return asArray(artifacts).filter(isWebArtifact);
    if (Array.isArray(payload.web_items)) return payload.web_items;
    if (Array.isArray(payload.web)) return payload.web;
    if (payload.web && typeof payload.web === "object" && Array.isArray(payload.web.items)) {
      return payload.web.items;
    }
    return asArray(artifacts).filter(isWebArtifact);
  }

  function activeSession() {
    return state.sessions.find(function (session) {
      return String(session.id || "") === String(state.sessionId || "");
    }) || null;
  }

  function messageText(message) {
    return safe(
      message &&
        (message.content ||
          message.text ||
          message.body ||
          (Array.isArray(message.parts) ? message.parts.join("\n") : ""))
    );
  }

  function getMessageId(message, index) {
    return safe(message && (message.id || message.message_id || message.uuid || ("msg_" + index)));
  }

  function getRouteMeta(message) {
    if (!message || typeof message !== "object") return null;

    const directCandidates = [
      message.route_meta,
      message.routeMeta,
      message.route,
      message.meta && message.meta.route_meta,
      message.meta && message.meta.route,
      message.debug && message.debug.route_meta,
      message.debug && message.debug.route,
      message.metadata && message.metadata.route_meta,
      message.metadata && message.metadata.route
    ];

    for (let i = 0; i < directCandidates.length; i += 1) {
      const candidate = directCandidates[i];
      if (candidate && typeof candidate === "object") return candidate;
    }

    const mode =
      message.route_mode ||
      (message.meta && message.meta.route_mode) ||
      (message.metadata && message.metadata.route_mode);

    if (!mode) return null;

    return {
      mode: mode,
      reason:
        message.route_reason ||
        (message.meta && message.meta.route_reason) ||
        (message.metadata && message.metadata.route_reason) ||
        "",
      matched_keywords:
        message.route_keywords ||
        (message.meta && message.meta.route_keywords) ||
        (message.metadata && message.metadata.route_keywords) ||
        [],
      build:
        message.route_build ||
        (message.meta && message.meta.route_build) ||
        (message.metadata && message.metadata.route_build) ||
        ""
    };
  }

  function getRouteMode(message) {
    const meta = getRouteMeta(message);
    const mode = meta && (meta.mode || meta.route || meta.name);
    return mode ? String(mode) : "";
  }

  function getRouteReason(meta) {
    if (!meta) return "";
    return safe(meta.reason || meta.why || meta.note || meta.description || "");
  }

  function getRouteKeywords(meta) {
    if (!meta) return [];
    return asArray(meta.matched_keywords || meta.keywords || meta.hits || [])
      .map(function (value) {
        return safe(value).trim();
      })
      .filter(Boolean);
  }

  function toPanelKey(value) {
    const key = safe(value).toLowerCase();
    if (key === "memory" || key === "web" || key === "artifacts") return key;
    return "artifacts";
  }

  function syncDomRefs() {
    els.body = document.body;
    els.appShell = qs(".nova-app-shell, .app-shell, [data-app-shell]");
    els.sidebar = qs(".nova-sidebar, .sidebar, [data-sidebar]");
    els.rightRail = qs(".nova-right-rail, .right-rail, [data-right-rail]");
    els.sidebarToggle = qs("[data-action='toggle-sidebar'], #sidebarToggle, .nova-sidebar-toggle");
    els.rightRailToggle = qs("[data-action='toggle-right-rail'], #rightRailToggle, .nova-right-rail-toggle");
    els.rightRailClose = qs("[data-action='close-right-rail'], #closeRightRail, .nova-right-rail-close");
    els.newChatBtn = qs("[data-action='new-chat'], #newChatBtn, .nova-new-chat");
    els.sessionsList = qs("#sessionsList, .nova-sessions-list, [data-role='sessions-list']");
    els.messages = qs("#messages, #chatMessages, .nova-messages, [data-role='messages']");
    els.chatInput = qs("#chatInput, textarea[name='message'], .nova-chat-input");
    els.sendBtn = qs("#sendBtn, [data-action='send']");
    els.uploadInput = qs("#fileInput, #uploadInput, input[type='file'][data-role='upload']");
    els.attachBtn = qs("#attachBtn, [data-action='attach']");
    els.pendingUploads = qs("#pendingUploads, .nova-pending-uploads, [data-role='pending-uploads']");
    els.composerStatus = qs("#composerStatus, .nova-composer-status, [data-role='composer-status']");
    els.activeSessionTitle = qs("#activeSessionTitle, .nova-active-session-title, [data-role='active-session-title']");
    els.activeSessionMeta = qs("#activeSessionMeta, .nova-active-session-meta, [data-role='active-session-meta']");
    els.modelChip = qs("#modelChip, .nova-model-chip, [data-role='model-chip']");
    els.readyStatus = qs("#readyStatus, .nova-ready-status, [data-role='ready-status']");
    els.railTitle = qs("#railTitle, .nova-rail-title, [data-role='rail-title']");
    els.railSubtitle = qs("#railSubtitle, .nova-rail-subtitle, [data-role='rail-subtitle']");
    els.memoryList = qs("#memoryList, .nova-memory-list, [data-role='memory-list']");
    els.artifactsList = qs("#artifactsList, .nova-artifacts-list, [data-role='artifacts-list']");
    els.webList = qs("#webList, .nova-web-list, [data-role='web-list']");
    els.railContent = qs("#railContent, .nova-rail-content, [data-role='rail-content']");
    els.memoryInput = qs("#memoryInput, [data-role='memory-input']");
    els.routeInspector = qs("#routeInspector, .nova-route-inspector, [data-role='route-inspector']");
    els.emptyState = qs(".nova-empty-state, .nova-center-hero, [data-role='empty-state']");
  }

    function applyShellState() {
    const hasMessages = asArray(state.messages).length > 0;

    if (els.body) {
      els.body.classList.toggle("sidebar-collapsed", !!state.sidebarCollapsed);
      els.body.classList.toggle("right-rail-open", !!state.rightRailOpen);
      els.body.classList.toggle("right-rail-closed", !state.rightRailOpen);
      els.body.setAttribute("data-active-panel", toPanelKey(state.activePanel));
      els.body.classList.toggle("has-messages", hasMessages);
      els.body.classList.toggle("is-empty-chat", !hasMessages);
    }

    if (els.sidebar) {
      if (state.sidebarCollapsed) {
        els.sidebar.style.width = "78px";
        els.sidebar.style.minWidth = "78px";
      } else {
        els.sidebar.style.width = "";
        els.sidebar.style.minWidth = "";
      }
    }

    if (els.rightRail) {
      els.rightRail.classList.toggle("is-open", !!state.rightRailOpen);
      els.rightRail.classList.toggle("is-closed", !state.rightRailOpen);

      if (state.rightRailOpen) {
        els.rightRail.style.width = "";
        els.rightRail.style.minWidth = "";
        els.rightRail.style.opacity = "";
        els.rightRail.style.pointerEvents = "";
        els.rightRail.style.overflow = "";
        els.rightRail.style.borderLeft = "";
      } else {
        els.rightRail.style.width = "0px";
        els.rightRail.style.minWidth = "0px";
        els.rightRail.style.opacity = "0";
        els.rightRail.style.pointerEvents = "none";
        els.rightRail.style.overflow = "hidden";
        els.rightRail.style.borderLeft = "0";
      }
    }

    qsa(".nova-empty-state, .nova-center-hero, [data-role='empty-state']").forEach(function (node) {
      const inMessages = !!node.closest("#messages, #chatMessages, .nova-messages, [data-role='messages']");
      if (inMessages) {
        node.style.display = hasMessages ? "none" : "";
      }
    });
  }

  function setBusy(flag) {
    state.sending = !!flag;
    if (els.sendBtn) els.sendBtn.disabled = !!flag;
    if (els.body) els.body.classList.toggle("is-sending", !!flag);
    if (els.readyStatus) els.readyStatus.textContent = flag ? "Working..." : "Ready";
  }

  function setUploading(flag) {
    state.uploading = !!flag;
    if (els.attachBtn) els.attachBtn.disabled = !!flag;
    if (els.body) els.body.classList.toggle("is-uploading", !!flag);
  }

  function scrollMessagesToBottom() {
    if (!els.messages) return;
    requestAnimationFrame(function () {
      try {
        els.messages.scrollTop = els.messages.scrollHeight;
      } catch (_) {}
    });
  }

  function routeBadgeHtml(message) {
    const meta = getRouteMeta(message);
    const mode = safe(getRouteMode(message));
    if (!meta || !mode) return "";

    const activeId = state.activeRouteInspectMessageId;
    const messageId = getMessageId(message, 0);
    const isActive = activeId && activeId === messageId;

    return (
      '<button class="nova-route-badge' +
      (isActive ? " is-active" : "") +
      '" type="button" data-action="toggle-route-inspect" data-message-id="' +
      escapeHtml(messageId) +
      '">' +
      escapeHtml(mode) +
      "</button>"
    );
  }

  function attachmentHtml(attachment) {
    const item = attachment || {};
    const url = normalizeUrl(item.url);
    const name = safe(item.name || "attachment");
    const mime = safe(item.mime_type || "");
    const isImage = (!!url && /^image\//i.test(mime)) || /\.(png|jpg|jpeg|gif|webp|bmp|svg)$/i.test(url);

    if (isImage && url) {
      return (
        '<div class="nova-message-image-block">' +
        '<img class="nova-message-image" src="' + escapeHtml(url) + '" alt="' + escapeHtml(name) + '">' +
        '<div class="nova-message-image-actions">' +
        '<a href="' + escapeHtml(url) + '" target="_blank" rel="noreferrer">Open</a>' +
        '<a href="' + escapeHtml(url) + '" download>Download</a>' +
        "</div>" +
        "</div>"
      );
    }

    return (
      '<div class="nova-attachment-chip">' +
      (url
        ? '<a href="' + escapeHtml(url) + '" target="_blank" rel="noreferrer">' + escapeHtml(name) + "</a>"
        : "<span>" + escapeHtml(name) + "</span>") +
      (mime ? '<span class="nova-attachment-meta">' + escapeHtml(mime) + "</span>" : "") +
      "</div>"
    );
  }

  function messageHtml(message, index) {
    const item = normalizeMessage(message, index);
    const role = item.role === "user" ? "user" : "assistant";
    const text = messageText(item);
    const createdAt = fmtDate(item.created_at);
    const attachmentsHtml = item.attachments.map(attachmentHtml).join("");
    const imageHtml = item.image_url
      ? attachmentHtml({ name: "generated-image", url: item.image_url, mime_type: "image/png" })
      : "";

    const messagePills = asArray(item.badges)
      .map(function (badge) {
        return '<span class="nova-message-pill">' + escapeHtml(badge) + "</span>";
      })
      .join("");

    return (
      '<article class="nova-message nova-message-' + escapeHtml(role) + '" data-message-id="' + escapeHtml(item.id) + '">' +
      '<div class="nova-message-head">' +
      '<div class="nova-message-role">' + escapeHtml(role === "user" ? "You" : "Nova") + "</div>" +
      '<div class="nova-message-head-right">' +
      routeBadgeHtml(item) +
      (createdAt ? '<div class="nova-message-time">' + escapeHtml(createdAt) + "</div>" : "") +
      "</div>" +
      "</div>" +
      (messagePills ? '<div class="nova-message-pills">' + messagePills + "</div>" : "") +
      '<div class="nova-message-body">' + (text ? nl2br(text) : "") + "</div>" +
      imageHtml +
      attachmentsHtml +
      "</article>"
    );
  }

  function emptyHtml(title, subtitle) {
    return (
      '<div class="nova-empty-state">' +
      '<div class="nova-empty-title">' + escapeHtml(title) + "</div>" +
      '<div class="nova-empty-subtitle">' + escapeHtml(subtitle) + "</div>" +
      "</div>"
    );
  }

  function renderMessages() {
    if (!els.messages) return;

    const messages = asArray(state.messages);

    if (!messages.length) {
      els.messages.innerHTML = emptyHtml(
        "Nova is ready",
        "Start a message, attach a file, or open a saved session."
      );
      applyShellState();
      renderRouteInspector();
      return;
    }

    els.messages.innerHTML = messages.map(messageHtml).join("");
    applyShellState();
    renderRouteInspector();
    scrollMessagesToBottom();
  } 

    

  function renderSessions() {
    if (!els.sessionsList) return;

    const sessions = asArray(state.sessions);
    if (!sessions.length) {
      els.sessionsList.innerHTML = emptyHtml("No sessions yet", "Start a new chat.");
      return;
    }

    els.sessionsList.innerHTML = sessions
      .map(function (session) {
        const isActive = String(session.id) === String(state.sessionId);
        const preview = shortText(session.last_message_preview || "", 90);

        return (
          '<div class="nova-session-card' + (isActive ? " is-active" : "") + '" data-session-id="' + escapeHtml(session.id) + '">' +
          '<button class="nova-session-main" type="button" data-action="switch-session" data-session-id="' + escapeHtml(session.id) + '">' +
          '<div class="nova-session-title-row">' +
          '<div class="nova-session-title">' + escapeHtml(session.title || "New Chat") + "</div>" +
          (session.pinned ? '<span class="nova-session-pin">📌</span>' : "") +
          "</div>" +
          '<div class="nova-session-preview">' + escapeHtml(preview || "No messages yet") + "</div>" +
          '<div class="nova-session-meta">' +
          '<span>' + escapeHtml(String(session.message_count || 0)) + " msgs</span>" +
          '<span>' + escapeHtml(fmtDate(session.updated_at || session.created_at) || "") + "</span>" +
          "</div>" +
          "</button>" +
          '<div class="nova-session-actions">' +
          '<button type="button" data-action="rename-session" data-session-id="' + escapeHtml(session.id) + '">Rename</button>' +
          '<button type="button" data-action="pin-session" data-session-id="' + escapeHtml(session.id) + '">' + (session.pinned ? "Unpin" : "Pin") + "</button>" +
          '<button type="button" data-action="delete-session" data-session-id="' + escapeHtml(session.id) + '">Delete</button>' +
          "</div>" +
          "</div>"
        );
      })
      .join("");
  }

  function renderMemory() {
    if (!els.memoryList) return;

    const items = asArray(state.memoryItems);
    if (!items.length) {
      els.memoryList.innerHTML = emptyHtml("No memory yet", "Add a note to lock something in.");
      return;
    }

    els.memoryList.innerHTML = items
      .map(function (item) {
        return (
          '<div class="nova-rail-card nova-memory-card" data-memory-id="' + escapeHtml(item.id) + '">' +
          '<div class="nova-rail-card-top">' +
          '<div class="nova-rail-card-title">' + escapeHtml(item.title || item.kind || "note") + "</div>" +
          '<button type="button" data-action="delete-memory" data-memory-id="' + escapeHtml(item.id) + '">Delete</button>' +
          "</div>" +
          '<div class="nova-rail-card-body">' + nl2br(item.text || "") + "</div>" +
          '<div class="nova-rail-card-meta">' +
          '<span>' + escapeHtml(item.kind || "note") + "</span>" +
          '<span>' + escapeHtml(fmtDate(item.updated_at || item.created_at) || "") + "</span>" +
          "</div>" +
          "</div>"
        );
      })
      .join("");
  }

  function renderArtifacts() {
    if (!els.artifactsList) return;

    const items = asArray(state.artifacts);
    if (!items.length) {
      els.artifactsList.innerHTML = emptyHtml("No artifacts yet", "Saved outputs will appear here.");
      return;
    }

    els.artifactsList.innerHTML = items
      .map(function (item) {
        const viewer = item.viewer || {};
        return (
          '<div class="nova-rail-card nova-artifact-card" data-artifact-id="' + escapeHtml(item.id) + '">' +
          '<div class="nova-rail-card-top">' +
          '<div class="nova-rail-card-title">' + escapeHtml(item.title || item.kind || "Artifact") + "</div>" +
          '<div class="nova-rail-card-kind">' + escapeHtml(item.kind || viewer.kind || "artifact") + "</div>" +
          "</div>" +
          '<div class="nova-rail-card-body">' + nl2br(shortText(item.preview || viewer.body || item.summary || "", 160)) + "</div>" +
          (item.image_url ? '<div class="nova-rail-card-media"><img src="' + escapeHtml(item.image_url) + '" alt="' + escapeHtml(item.title || "artifact") + '"></div>' : "") +
          '<div class="nova-rail-card-actions">' +
          '<button type="button" data-action="open-artifact" data-artifact-id="' + escapeHtml(item.id) + '">Open</button>' +
          (item.session_id ? '<button type="button" data-action="switch-session" data-session-id="' + escapeHtml(item.session_id) + '">Open Session</button>' : "") +
          (item.source_url ? '<a href="' + escapeHtml(item.source_url) + '" target="_blank" rel="noreferrer">Source</a>' : "") +
          "</div>" +
          "</div>"
        );
      })
      .join("");
  }

  function renderWeb() {
    if (!els.webList) return;

    const items = asArray(state.webItems);
    if (!items.length) {
      els.webList.innerHTML = emptyHtml("No web results yet", "Web fetch results will appear here.");
      return;
    }

    els.webList.innerHTML = items
      .map(function (item) {
        const title = item.title || (item.viewer && item.viewer.title) || item.kind || "Web result";
        const body = item.preview || item.summary || item.content || (item.viewer && item.viewer.body) || "";
        const sourceUrl = item.source_url || (item.viewer && item.viewer.source_url) || "";

        return (
          '<div class="nova-rail-card nova-web-card">' +
          '<div class="nova-rail-card-top">' +
          '<div class="nova-rail-card-title">' + escapeHtml(title) + "</div>" +
          '<div class="nova-rail-card-kind">web</div>' +
          "</div>" +
          '<div class="nova-rail-card-body">' + nl2br(shortText(body, 180)) + "</div>" +
          '<div class="nova-rail-card-actions">' +
          (sourceUrl ? '<a href="' + escapeHtml(sourceUrl) + '" target="_blank" rel="noreferrer">Open source</a>' : "") +
          (item.id ? '<button type="button" data-action="open-artifact" data-artifact-id="' + escapeHtml(item.id) + '">Open</button>' : "") +
          "</div>" +
          "</div>"
        );
      })
      .join("");
  }

  function renderRailHeader() {
    const panel = toPanelKey(state.activePanel);

    if (els.railTitle) {
      els.railTitle.textContent =
        panel === "memory" ? "Memory" :
        panel === "web" ? "Web" :
        "Artifacts";
    }

    if (els.railSubtitle) {
      const count =
        panel === "memory" ? state.memoryItems.length :
        panel === "web" ? state.webItems.length :
        state.artifacts.length;
      els.railSubtitle.textContent = String(count) + " items";
    }

    qsa("[data-panel]").forEach(function (btn) {
      const isActive = toPanelKey(btn.getAttribute("data-panel")) === panel;
      btn.classList.toggle("is-active", isActive);
      btn.setAttribute("aria-pressed", isActive ? "true" : "false");
    });

    if (els.memoryList) els.memoryList.style.display = panel === "memory" ? "block" : "none";
    if (els.artifactsList) els.artifactsList.style.display = panel === "artifacts" ? "block" : "none";
    if (els.webList) els.webList.style.display = panel === "web" ? "block" : "none";

    applyShellState();
  }
  

  function renderActiveSessionMeta() {
    const session = activeSession();
    if (els.activeSessionTitle) {
      els.activeSessionTitle.textContent = session ? session.title || "New Chat" : "Nova";
    }
    if (els.activeSessionMeta) {
      els.activeSessionMeta.textContent = session ? String(asArray(state.messages).length) + " messages" : "Fast local AI workspace";
    }
  }

  function renderTopbar() {
    renderActiveSessionMeta();
    if (els.modelChip) {
      const model = safe(state.lastStatePayload && (state.lastStatePayload.openai_model || state.lastStatePayload.chat_model || state.lastStatePayload.model)) || "gpt-5.4";
      els.modelChip.textContent = model;
    }
    if (els.readyStatus) {
      els.readyStatus.textContent = state.sending ? "Working..." : "Ready";
    }
  }

  function renderPendingUploads() {
    if (!els.pendingUploads) return;

    const items = asArray(state.pendingUploads);
    if (!items.length) {
      els.pendingUploads.innerHTML = "";
      return;
    }

    els.pendingUploads.innerHTML = items
      .map(function (item, index) {
        return (
          '<div class="nova-upload-chip">' +
          '<span class="nova-upload-chip-name">' + escapeHtml(item.name || ("upload-" + index)) + "</span>" +
          '<button type="button" data-action="remove-pending-upload" data-upload-id="' + escapeHtml(item.id) + '">×</button>' +
          "</div>"
        );
      })
      .join("");
  }

  function renderRouteInspector() {
    if (!els.routeInspector) return;

    if (!state.activeRouteInspectMessageId) {
      els.routeInspector.innerHTML = "";
      els.routeInspector.style.display = "none";
      return;
    }

    const target = asArray(state.messages).find(function (message, index) {
      return getMessageId(message, index) === state.activeRouteInspectMessageId;
    });

    if (!target) {
      state.activeRouteInspectMessageId = "";
      els.routeInspector.innerHTML = "";
      els.routeInspector.style.display = "none";
      return;
    }

    const meta = getRouteMeta(target);
    if (!meta) {
      els.routeInspector.innerHTML = "";
      els.routeInspector.style.display = "none";
      return;
    }

    const keywords = getRouteKeywords(meta);

    els.routeInspector.style.display = "";
    els.routeInspector.innerHTML =
      '<div class="nova-route-inspector-card">' +
      '<div class="nova-route-inspector-top">' +
      '<div class="nova-route-inspector-title">Route inspector</div>' +
      '<button type="button" data-action="close-route-inspector">Close</button>' +
      "</div>" +
      '<div class="nova-route-inspector-grid">' +
      '<div><strong>Mode</strong><div>' + escapeHtml(getRouteMode(target) || "unknown") + "</div></div>" +
      '<div><strong>Reason</strong><div>' + escapeHtml(getRouteReason(meta) || "-") + "</div></div>" +
      '<div><strong>Keywords</strong><div>' + escapeHtml(keywords.join(", ") || "-") + "</div></div>" +
      "</div>" +
      "</div>";
  }

  function renderAll() {
    renderTopbar();
    renderSessions();
    renderMessages();
    renderPendingUploads();
    renderMemory();
    renderArtifacts();
    renderWeb();
    renderRailHeader();
    applyShellState();
  }

  function chooseSessionFromPayload(payload) {
    const direct = safe(payload && (payload.session_id || payload.active_session_id || payload.current_session_id || (payload.session && payload.session.id)));
    if (direct) return direct;

    const sessions = asArray(payload && payload.sessions).map(normalizeSession);
    const explicitActive = sessions.find(function (session) {
      return session.active;
    });
    if (explicitActive) return explicitActive.id;

    return state.sessionId || (sessions[0] && sessions[0].id) || "";
  }

  function applyStatePayload(payload) {
    const raw = payload || {};
    const sessions = asArray(raw.sessions).map(normalizeSession);
    const selectedSessionId = chooseSessionFromPayload(raw);

    state.lastStatePayload = raw;
    state.sessions = sessions;
    state.sessionId = selectedSessionId || state.sessionId || (sessions[0] && sessions[0].id) || "";

    const selectedSession = sessions.find(function (session) {
      return String(session.id) === String(state.sessionId);
    }) || null;

    const sessionMessages = selectedSession ? asArray(selectedSession.messages) : [];
    const topLevelMessages = asArray(raw.messages).map(normalizeMessage);
    state.messages = topLevelMessages.length ? topLevelMessages : sessionMessages;

    state.memoryItems = getMemoryListFromPayload(raw).map(normalizeMemoryItem);
    state.artifacts = getArtifactListFromPayload(raw).map(normalizeArtifact);
    state.webItems = getWebListFromPayload(raw, state.artifacts).map(normalizeArtifact);

    state.lastRefreshHash = hash({
      sessionId: state.sessionId,
      sessions: state.sessions.map(function (session) {
        return [session.id, session.title, session.updated_at, session.message_count, session.pinned];
      }),
      messages: state.messages.map(function (message) {
        return [message.id, message.role, message.content, message.created_at];
      }),
      memory: state.memoryItems.map(function (memory) {
        return [memory.id, memory.text, memory.updated_at];
      }),
      artifacts: state.artifacts.map(function (artifact) {
        return [artifact.id, artifact.title, artifact.updated_at, artifact.kind];
      })
    });

    renderAll();
  }

  async function refreshState(options) {
    const opts = options || {};
    if (state.refreshing && !opts.force) return;

    state.refreshing = true;
    try {
      log("refreshState:start");
      const payload = await requestJson(API.state, { method: "GET" });
      applyStatePayload(payload);
      setComposerStatus("Ready", false);
    } catch (error) {
      err("refreshState failed", error);
      setComposerStatus("State refresh failed: " + safe(error && error.message), true);
    } finally {
      state.refreshing = false;
    }
  }

  async function createNewSession() {
    try {
      setComposerStatus("Creating session...", false);
      const payload = await requestJson(API.newSession, { method: "POST" });
      const newId = safe(payload && (payload.session_id || payload.id || (payload.session && payload.session.id)));
      await refreshState({ force: true });
      if (newId) state.sessionId = newId;
      renderAll();
      if (els.chatInput) els.chatInput.focus();
      setComposerStatus("New chat ready", false);
    } catch (error) {
      err("createNewSession failed", error);
      setComposerStatus("New chat failed: " + safe(error && error.message), true);
    }
  }

  async function renameSession(sessionId) {
    const targetId = safe(sessionId);
    if (!targetId) return;

    const current = state.sessions.find(function (session) {
      return String(session.id) === String(targetId);
    });

    const nextTitle = window.prompt("Rename session", current ? current.title : "New Chat");
    if (!nextTitle) return;

    try {
      await requestJson(API.renameSession, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: targetId, title: nextTitle })
      });
      await refreshState({ force: true });
      setComposerStatus("Session renamed", false);
    } catch (error) {
      err("renameSession failed", error);
      setComposerStatus("Rename failed: " + safe(error && error.message), true);
    }
  }

  async function pinSession(sessionId) {
    const targetId = safe(sessionId);
    if (!targetId) return;

    try {
      await requestJson(API.pinSession, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: targetId })
      });
      await refreshState({ force: true });
      setComposerStatus("Session updated", false);
    } catch (error) {
      err("pinSession failed", error);
      setComposerStatus("Pin failed: " + safe(error && error.message), true);
    }
  }

  async function deleteSession(sessionId) {
    const targetId = safe(sessionId);
    if (!targetId) return;
    if (!window.confirm("Delete this session?")) return;

    try {
      await requestJson(API.deleteSession, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: targetId })
      });
      await refreshState({ force: true });
      setComposerStatus("Session deleted", false);
    } catch (error) {
      err("deleteSession failed", error);
      setComposerStatus("Delete failed: " + safe(error && error.message), true);
    }
  }

  function switchSessionLocal(sessionId) {
    const targetId = safe(sessionId);
    if (!targetId) return;

    const selected = state.sessions.find(function (session) {
      return String(session.id) === String(targetId);
    });

    state.sessionId = targetId;
    state.messages = selected ? asArray(selected.messages) : [];
    renderAll();
    scrollMessagesToBottom();
  }

  async function addMemoryItem() {
    const text = safe(els.memoryInput && els.memoryInput.value).trim();
    if (!text) return;

    try {
      await requestJson(API.memoryCreate, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text, session_id: state.sessionId || "" })
      });
      if (els.memoryInput) els.memoryInput.value = "";
      await refreshState({ force: true });
      setComposerStatus("Memory saved", false);
    } catch (error) {
      err("addMemoryItem failed", error);
      setComposerStatus("Memory save failed: " + safe(error && error.message), true);
    }
  }

  async function deleteMemoryItem(memoryId) {
    const id = safe(memoryId);
    if (!id) return;

    try {
      await requestJson(API.memoryDelete, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ memory_id: id, id: id })
      });
      await refreshState({ force: true });
      setComposerStatus("Memory deleted", false);
    } catch (error) {
      err("deleteMemoryItem failed", error);
      setComposerStatus("Memory delete failed: " + safe(error && error.message), true);
    }
  }

  async function uploadFiles(files) {
    const list = Array.from(files || []);
    if (!list.length) return;

    setUploading(true);
    setComposerStatus("Uploading...", false);

    try {
      for (let i = 0; i < list.length; i += 1) {
        const file = list[i];
        const form = new FormData();
        form.append("file", file);

        const payload = await requestJson(API.upload, {
          method: "POST",
          body: form
        });

        const attachment = normalizeAttachment(
          payload.attachment ||
            payload.file ||
            payload.upload || {
              id: payload.id,
              name: payload.filename || file.name,
              url: payload.url || payload.path,
              mime_type: payload.mime_type || file.type,
              size: file.size
            },
          state.pendingUploads.length + i
        );

        state.pendingUploads.push(attachment);
      }

      renderPendingUploads();
      setComposerStatus("Upload staged", false);
    } catch (error) {
      err("uploadFiles failed", error);
      setComposerStatus("Upload failed: " + safe(error && error.message), true);
    } finally {
      setUploading(false);
      if (els.uploadInput) els.uploadInput.value = "";
    }
  }

  function removePendingUpload(uploadId) {
    const targetId = safe(uploadId);
    state.pendingUploads = state.pendingUploads.filter(function (item) {
      return String(item.id) !== String(targetId);
    });
    renderPendingUploads();
  }

  function createLocalUserMessage(text, attachments) {
    return normalizeMessage({
      id: "local-user-" + Date.now(),
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
      attachments: asArray(attachments)
    });
  }

  function createLocalAssistantMessage(text, routeMeta) {
    return normalizeMessage({
      id: "local-assistant-" + Date.now(),
      role: "assistant",
      content: text,
      created_at: new Date().toISOString(),
      route_meta: routeMeta || {}
    });
  }

  async function apiStreamChat(payload) {
    const res = await fetch(API.streamChat, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok || !res.body) {
      throw new Error("Streaming unavailable");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let full = "";
    let buffer = "";
    let routeMeta = null;
    const localMessageId = "streaming-assistant-" + Date.now();

    state.messages = state.messages.concat([
      normalizeMessage({
        id: localMessageId,
        role: "assistant",
        content: "",
        created_at: new Date().toISOString()
      })
    ]);
    renderMessages();

    while (true) {
      const result = await reader.read();
      if (result.done) break;

      buffer += decoder.decode(result.value, { stream: true });
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() || "";

      for (let i = 0; i < lines.length; i += 1) {
        const line = lines[i].trim();
        if (!line) continue;

        let parsed = null;
        try {
          parsed = JSON.parse(line);
        } catch (_) {
          if (line.startsWith("data:")) {
            const maybeJson = line.slice(5).trim();
            if (maybeJson === "[DONE]") continue;
            try {
              parsed = JSON.parse(maybeJson);
            } catch (_) {
              parsed = { delta: maybeJson };
            }
          } else {
            parsed = { delta: line };
          }
        }

        const delta = safe(parsed.delta || parsed.content || parsed.text || parsed.token || parsed.message || "");
        if (parsed.route_meta && typeof parsed.route_meta === "object") {
          routeMeta = parsed.route_meta;
        }

        if (delta) {
          full += delta;
          const target = state.messages.find(function (message) {
            return message.id === localMessageId;
          });
          if (target) {
            target.content = full;
            if (routeMeta) target.route_meta = routeMeta;
          }
          renderMessages();
        }
      }
    }

    return { assistant_message: full, route_meta: routeMeta };
  }

  async function apiJsonChat(payload) {
    return requestJson(API.chat, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  }

  function extractAssistantMessage(payload) {
    if (!payload || typeof payload !== "object") return "";
    return safe(
      payload.assistant_message ||
        payload.reply ||
        payload.message ||
        payload.content ||
        payload.text ||
        (payload.assistant && payload.assistant.content) ||
        ""
    );
  }

  function extractRouteMeta(payload) {
    if (!payload || typeof payload !== "object") return null;
    return payload.route_meta || (payload.assistant && payload.assistant.route_meta) || (payload.message_data && payload.message_data.route_meta) || null;
  }

  async function finalizePostSend(sendNonce, response) {
    const responseSessionId = safe(response && (response.session_id || response.active_session_id || (response.session && response.session.id)));
    if (responseSessionId) {
      state.sessionId = responseSessionId;
    }

    await refreshState({ force: true });

    if (sendNonce !== state.lastSendNonce) {
      log("finalizePostSend skipped: newer send exists");
      return;
    }

    renderAll();
    scrollMessagesToBottom();
    setComposerStatus("Sent", false);
  }

  async function sendMessage() {
    if (state.sending) return;

    const text = safe(els.chatInput && els.chatInput.value).trim();
    const attachments = asArray(state.pendingUploads);

    if (!text && !attachments.length) {
      setComposerStatus("Type a message or attach a file", true);
      return;
    }

    const sendNonce = Date.now();
    state.lastSendNonce = sendNonce;

    const localUser = createLocalUserMessage(text, attachments);
    state.lastUserMessage = localUser;
    state.messages = state.messages.concat([localUser]);
    renderMessages();
    scrollMessagesToBottom();

    if (els.chatInput) {
      els.chatInput.value = "";
      els.chatInput.style.height = "";
    }

    const payload = {
      message: text,
      user_text: text,
      text: text,
      session_id: state.sessionId || "",
      attachments: attachments
    };

    state.pendingUploads = [];
    renderPendingUploads();
    setBusy(true);
    setComposerStatus("Sending...", false);

    try {
      let response = null;
      let streamed = false;

      try {
        response = await apiStreamChat(payload);
        streamed = true;
      } catch (streamError) {
        warn("Streaming failed, fallback -> JSON", streamError);
        response = await apiJsonChat(payload);
      }

      if (!streamed) {
        const assistantText = extractAssistantMessage(response);
        const routeMeta = extractRouteMeta(response);
        if (assistantText) {
          state.messages = state.messages.concat([createLocalAssistantMessage(assistantText, routeMeta)]);
          renderMessages();
          scrollMessagesToBottom();
        }
      }

      await finalizePostSend(sendNonce, response);
    } catch (error) {
      err("sendMessage failed", error);
      setComposerStatus("Send failed: " + safe(error && error.message), true);
      await refreshState({ force: true });
      renderAll();
      scrollMessagesToBottom();
    } finally {
      setBusy(false);
      if (els.chatInput) els.chatInput.focus();
    }
  }

  function openArtifactFromState(artifactId) {
    const id = safe(artifactId);
    if (!id) return;

    const item = state.artifacts.find(function (artifact) {
      return String(artifact.id) === String(id);
    });

    if (!item) {
      setComposerStatus("Artifact not found", true);
      return;
    }

    state.activePanel = isWebArtifact(item) ? "web" : "artifacts";
    state.rightRailOpen = true;
    renderRailHeader();

    const viewer = item.viewer || {};
    const title = viewer.title || item.title || "Artifact";
    const body = viewer.body || viewer.analysis_text || item.summary || item.content || item.preview || "";
    const imageUrl = viewer.image_url || item.image_url || "";
    const sourceUrl = viewer.source_url || item.source_url || "";

    if (els.railContent) {
      els.railContent.innerHTML =
        '<div class="nova-artifact-viewer">' +
        '<div class="nova-artifact-viewer-top">' +
        '<div class="nova-artifact-viewer-title">' + escapeHtml(title) + "</div>" +
        '<button type="button" data-action="close-artifact-viewer">Close</button>' +
        "</div>" +
        (imageUrl ? '<div class="nova-artifact-viewer-media"><img src="' + escapeHtml(imageUrl) + '" alt="' + escapeHtml(title) + '"></div>' : "") +
        '<div class="nova-artifact-viewer-body">' + nl2br(body) + "</div>" +
        (sourceUrl ? '<div class="nova-artifact-viewer-actions"><a href="' + escapeHtml(sourceUrl) + '" target="_blank" rel="noreferrer">Open source</a></div>' : "") +
        "</div>";
    }

    applyShellState();

    if (item.session_id) {
      switchSessionLocal(item.session_id);
    }
  }

  function closeArtifactViewer() {
    if (els.railContent) {
      els.railContent.innerHTML = "";
    }
  }

  function setActivePanel(panel) {
    state.activePanel = toPanelKey(panel);
    state.rightRailOpen = true;
    closeArtifactViewer();
    renderRailHeader();
    applyShellState();
  }

  function toggleRightRail(forceValue) {
    if (typeof forceValue === "boolean") {
      state.rightRailOpen = forceValue;
    } else {
      state.rightRailOpen = !state.rightRailOpen;
    }

    applyShellState();
    renderRailHeader();
  }

  function autoGrowTextarea() {
    if (!els.chatInput) return;
    els.chatInput.style.height = "auto";
    els.chatInput.style.height = Math.min(els.chatInput.scrollHeight, 320) + "px";
  }

  function toggleSidebar() {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    applyShellState();
  }

  function handleRootClick(event) {
    const button = event.target.closest("[data-action], [data-panel]");
    if (!button) return;

    const action = button.getAttribute("data-action");
    const panel = button.getAttribute("data-panel");

    if (panel) {
      event.preventDefault();
      setActivePanel(panel);
      return;
    }

    switch (action) {
      case "send":
        event.preventDefault();
        sendMessage();
        break;
      case "attach":
        event.preventDefault();
        if (els.uploadInput) els.uploadInput.click();
        break;
      case "new-chat":
        event.preventDefault();
        createNewSession();
        break;
      case "toggle-sidebar":
        event.preventDefault();
        toggleSidebar();
        break;
      case "toggle-right-rail":
        event.preventDefault();
        toggleRightRail();
        break;
      case "close-right-rail":
        event.preventDefault();
        toggleRightRail(false);
        break;
      case "switch-session":
        event.preventDefault();
        switchSessionLocal(button.getAttribute("data-session-id"));
        break;
      case "rename-session":
        event.preventDefault();
        renameSession(button.getAttribute("data-session-id"));
        break;
      case "pin-session":
        event.preventDefault();
        pinSession(button.getAttribute("data-session-id"));
        break;
      case "delete-session":
        event.preventDefault();
        deleteSession(button.getAttribute("data-session-id"));
        break;
      case "memory-add":
        event.preventDefault();
        addMemoryItem();
        break;
      case "delete-memory":
        event.preventDefault();
        deleteMemoryItem(button.getAttribute("data-memory-id"));
        break;
      case "remove-pending-upload":
        event.preventDefault();
        removePendingUpload(button.getAttribute("data-upload-id"));
        break;
      case "toggle-route-inspect": {
        event.preventDefault();
        const messageId = safe(button.getAttribute("data-message-id"));
        state.activeRouteInspectMessageId = state.activeRouteInspectMessageId === messageId ? "" : messageId;
        renderMessages();
        break;
      }
      case "close-route-inspector":
        event.preventDefault();
        state.activeRouteInspectMessageId = "";
        renderRouteInspector();
        renderMessages();
        break;
      case "open-artifact":
        event.preventDefault();
        openArtifactFromState(button.getAttribute("data-artifact-id"));
        break;
      case "close-artifact-viewer":
        event.preventDefault();
        closeArtifactViewer();
        break;
      default:
        break;
    }
  }

  function bindEvents() {
    document.addEventListener("click", handleRootClick);

    if (els.sendBtn) {
      els.sendBtn.addEventListener("click", function () {
        sendMessage();
      });
    }

    if (els.chatInput) {
      els.chatInput.addEventListener("input", autoGrowTextarea);
      els.chatInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage();
        }
      });
      autoGrowTextarea();
    }

    if (els.uploadInput) {
      els.uploadInput.addEventListener("change", function (event) {
        uploadFiles(event.target.files);
      });
    }

    if (els.memoryInput) {
      els.memoryInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          addMemoryItem();
        }
      });
    }
  }

  async function boot() {
    if (state.booted) return;
    state.booted = true;

    log("boot start");
    syncDomRefs();
    bindEvents();
    applyShellState();
    renderAll();
    await refreshState({ force: true });
    setComposerStatus("Ready", false);
    log("boot complete");
  }

  window.NovaComposerBundle = {
    state: state,
    refreshState: refreshState,
    sendMessage: sendMessage,
    createNewSession: createNewSession,
    switchSession: switchSessionLocal,
    addMemoryItem: addMemoryItem,
    deleteMemoryItem: deleteMemoryItem,
    openArtifact: openArtifactFromState,
    toggleRightRail: toggleRightRail,
    setActivePanel: setActivePanel
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();