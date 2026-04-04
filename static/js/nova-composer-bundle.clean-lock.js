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
    deleteSession: "/api/session/delete",
    memoryCreate: "/api/memory/create",
    memoryDelete: "/api/memory/delete"
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
    lastUserMessage: null,
    activeRouteInspectMessageId: "",
    lastStatePayload: null
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

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function fmtDate(value) {
    if (!value) return "";
    try {
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return String(value);
      return d.toLocaleString();
    } catch (_) {
      return String(value);
    }
  }

  function shortText(value, max) {
    const s = String(value || "").trim();
    if (!s) return "";
    return s.length > max ? s.slice(0, max - 1) + "…" : s;
  }

  function setComposerStatus(text, isError) {
    if (!els.composerStatus) return;
    els.composerStatus.textContent = text || "";
    els.composerStatus.style.color = isError ? "var(--danger)" : "";
  }

  async function requestJson(url, options) {
    const res = await fetch(url, options || {});
    const contentType = res.headers.get("content-type") || "";
    let data = null;

    if (contentType.includes("application/json")) {
      data = await res.json();
    } else {
      const raw = await res.text();
      data = { ok: res.ok, raw: raw };
    }

    if (!res.ok) {
      const message =
        (data && (data.error || data.message || data.raw)) ||
        ("Request failed: " + res.status);
      throw new Error(message);
    }

    return data;
  }

  function normalizeMessages(messages) {
    return Array.isArray(messages) ? messages : [];
  }

  function normalizeSessions(sessions) {
    return Array.isArray(sessions) ? sessions : [];
  }

  function normalizeMemory(items) {
    return Array.isArray(items) ? items : [];
  }

  function normalizeArtifacts(items) {
    return Array.isArray(items) ? items : [];
  }

  function normalizeWebItems(items, artifacts) {
    if (Array.isArray(items) && items.length) return items;
    return (Array.isArray(artifacts) ? artifacts : []).filter(function (item) {
      const kind = String(item && (item.kind || (item.viewer && item.viewer.kind) || "")).toLowerCase();
      return kind.includes("web");
    });
  }

  function activeSession() {
    return state.sessions.find(function (s) {
      return String(s.id || "") === String(state.sessionId || "");
    }) || null;
  }

  function messageText(message) {
    return (
      message.content ||
      message.text ||
      message.body ||
      (message.parts && Array.isArray(message.parts) ? message.parts.join("\n") : "") ||
      ""
    );
  }

  function getMessageId(message, index) {
    return String(
      (message && (message.id || message.message_id || message.uuid)) ||
      ("msg_" + index)
    );
  }

  function getRouteMeta(message) {
    if (!message || typeof message !== "object") return null;

    const directCandidates = [
      message.route_meta,
      message.route,
      message.routeMeta,
      message.meta && message.meta.route_meta,
      message.meta && message.meta.route,
      message.debug && message.debug.route,
      message.debug && message.debug.route_meta,
      message.metadata && message.metadata.route_meta,
      message.metadata && message.metadata.route
    ];

    for (let i = 0; i < directCandidates.length; i += 1) {
      const candidate = directCandidates[i];
      if (candidate && typeof candidate === "object") {
        return candidate;
      }
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
    return (
      meta.reason ||
      meta.why ||
      meta.explanation ||
      meta.route_reason ||
      ""
    );
  }

  function getRouteKeywords(meta) {
    if (!meta) return [];
    const raw =
      meta.matched_keywords ||
      meta.keywords ||
      meta.matched ||
      meta.route_keywords ||
      [];
    if (Array.isArray(raw)) return raw.filter(Boolean).map(String);
    if (typeof raw === "string") {
      return raw
        .split(",")
        .map(function (part) { return part.trim(); })
        .filter(Boolean);
    }
    return [];
  }

  function getRouteBuild(meta) {
    if (!meta) return "";
    return String(
      meta.build ||
      meta.route_build ||
      meta.router_build ||
      meta.version ||
      ""
    );
  }

  function getRouteTimestamp(meta, message) {
    return (
      (meta && (meta.timestamp || meta.created_at || meta.time)) ||
      message.created_at ||
      message.timestamp ||
      ""
    );
  }

  function getRouteRaw(meta) {
    try {
      return JSON.stringify(meta || {}, null, 2);
    } catch (_) {
      return "{}";
    }
  }

  function findMessageById(messageId) {
    return state.messages.find(function (message, index) {
      return getMessageId(message, index) === String(messageId || "");
    }) || null;
  }

  function hasRouteMeta(message) {
    return !!getRouteMeta(message);
  }

  function setActivePanel(panel) {
    state.activePanel = panel || "artifacts";

    const titles = {
      artifacts: ["Artifacts", "Saved outputs tied to this session"],
      memory: ["Memory", "Saved notes and preferences"],
      web: ["Web", "Fetched links and web results"],
      route: ["Route Inspector", "Inspect saved routing metadata"]
    };

    const pair = titles[state.activePanel] || titles.artifacts;
    if (els.rightRailTitle) els.rightRailTitle.textContent = pair[0];
    if (els.rightRailSubtitle) els.rightRailSubtitle.textContent = pair[1];

    qsa(".nova-rail-tab").forEach(function (tab) {
      const isActive = tab.dataset.panel === state.activePanel;
      tab.classList.toggle("is-active", isActive);
    });

    const panels = {
      artifacts: els.panelArtifacts,
      memory: els.panelMemory,
      web: els.panelWeb,
      route: els.panelRoute
    };

    Object.keys(panels).forEach(function (key) {
      if (panels[key]) panels[key].classList.toggle("is-active", key === state.activePanel);
    });

    if (els.rightRail) {
      els.rightRail.dataset.open = "true";
      els.rightRail.style.display = "";
    }
  }

  function toggleSidebar() {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    if (!els.novaSidebar) return;
    els.novaSidebar.dataset.collapsed = state.sidebarCollapsed ? "true" : "false";
  }

  function autoGrowTextarea() {
    if (!els.chatInput) return;
    els.chatInput.style.height = "auto";
    els.chatInput.style.height = Math.min(220, Math.max(58, els.chatInput.scrollHeight)) + "px";
  }

  function renderAll() {
    renderTopbar();
    renderSessions();
    renderMessages();
    renderPendingUploads();
    renderMemory();
    renderArtifacts();
    renderWeb();
    renderRouteInspector();
  }

  function renderTopbar() {
    const session = activeSession();
    const title =
      (session && (session.title || session.name)) ||
      "Nova";

    const subtitle = session
      ? ((session.message_count != null ? String(session.message_count) : String(state.messages.length)) + " messages")
      : "Fast local AI workspace";

    if (els.sessionTitle) els.sessionTitle.textContent = title;
    if (els.sessionSubtitle) els.sessionSubtitle.textContent = subtitle;

    const model =
      (state.lastStatePayload && (state.lastStatePayload.chat_model || state.lastStatePayload.openai_model || state.lastStatePayload.model)) ||
      "gpt-5.4";
    if (els.modelChip) els.modelChip.textContent = model;

    if (els.statusChip) {
      els.statusChip.textContent = state.sending
        ? "Sending"
        : state.uploading
          ? "Uploading"
          : "Ready";
    }
  }

  function renderSessions() {
    if (!els.sessionList) return;

    if (!state.sessions.length) {
      els.sessionList.innerHTML = [
        '<div class="nova-empty-state">',
        '  <div class="nova-empty-title">No sessions yet</div>',
        '  <div class="nova-empty-text">Start a new chat to create your first session.</div>',
        '</div>'
      ].join("");
      if (els.sessionCount) els.sessionCount.textContent = "0 sessions";
      return;
    }

    if (els.sessionCount) {
      els.sessionCount.textContent = state.sessions.length + " session" + (state.sessions.length === 1 ? "" : "s");
    }

    els.sessionList.innerHTML = state.sessions.map(function (session) {
      const isActive = String(session.id || "") === String(state.sessionId || "");
      const title = escapeHtml(session.title || session.name || "Untitled session");
      const preview = escapeHtml(shortText(session.last_message_preview || session.preview || "", 110));
      const updated = escapeHtml(fmtDate(session.updated_at || session.created_at || ""));
      const count = session.message_count != null ? String(session.message_count) : "";
      const pinGlyph = session.pinned ? "★" : "☆";

      return [
        '<div class="nova-session-card' + (isActive ? ' is-active' : '') + '" data-session-id="' + escapeHtml(session.id || "") + '">',
        '  <div class="nova-session-top">',
        '    <div class="nova-session-card-main">',
        '      <div class="nova-session-title">' + title + "</div>",
        (preview ? '      <div class="nova-session-preview">' + preview + "</div>" : ""),
        '      <div class="nova-session-meta">' + escapeHtml(count ? count + " msgs" : "") + (updated ? (count ? " · " : "") + updated : "") + "</div>",
        "    </div>",
        '    <div class="nova-session-actions">',
        '      <button class="nova-icon-btn" type="button" data-action="pin" data-session-id="' + escapeHtml(session.id || "") + '" aria-label="Pin session">' + pinGlyph + "</button>",
        '      <button class="nova-icon-btn" type="button" data-action="rename" data-session-id="' + escapeHtml(session.id || "") + '" aria-label="Rename session">✎</button>',
        '      <button class="nova-icon-btn" type="button" data-action="delete" data-session-id="' + escapeHtml(session.id || "") + '" aria-label="Delete session">×</button>',
        "    </div>",
        "  </div>",
        "</div>"
      ].join("");
    }).join("");
  }

  function renderMessages() {
    if (!els.chatMessages) return;

    if (!state.messages.length) {
      els.chatMessages.innerHTML = [
        '<div class="nova-empty-state">',
        '  <div class="nova-empty-title">Nova is live</div>',
        '  <div class="nova-empty-text">Chat is working. Uploads stage before send. Artifacts rail stays available.</div>',
        "</div>"
      ].join("");
      return;
    }

    els.chatMessages.innerHTML = state.messages.map(function (message, index) {
      const role = String(message.role || message.author || (index % 2 ? "assistant" : "user")).toLowerCase();
      const text = escapeHtml(messageText(message));
      const id = escapeHtml(getMessageId(message, index));
      const routeMeta = getRouteMeta(message);
      const routeMode = routeMeta ? escapeHtml(getRouteMode(message)) : "";
      const hasArtifact = !!(message.artifact_id || message.artifact || (message.meta && message.meta.artifact_id));
      const hasWeb = !!(message.web_result || (message.meta && message.meta.web_result) || (routeMeta && String(getRouteMode(message)).toLowerCase() === "web"));
      const imageUrl =
        message.image_url ||
        (message.artifact && message.artifact.image_url) ||
        (message.viewer && message.viewer.image_url) ||
        "";

      const badges = [];
      if (routeMeta && role === "assistant") {
        badges.push(
          '<button class="nova-badge nova-badge-route" type="button" data-open-route="' + id + '">' +
          "Route: " + routeMode +
          "</button>"
        );
      }
      if (hasArtifact) {
        badges.push('<span class="nova-badge nova-badge-artifact">Artifact</span>');
      }
      if (hasWeb) {
        badges.push('<span class="nova-badge nova-badge-web">Web</span>');
      }

      const actions = role === "assistant"
        ? [
            '<div class="nova-message-actions">',
            '  <button class="nova-btn nova-btn-ghost" type="button" data-copy-message="' + id + '">Copy</button>',
            '  <button class="nova-btn nova-btn-ghost" type="button" data-regenerate-message="' + id + '">Regenerate</button>',
            "</div>"
          ].join("")
        : "";

      const imageBlock = imageUrl
        ? [
            '<div class="nova-artifact-image">',
            '  <img src="' + escapeHtml(imageUrl) + '" alt="Generated image" />',
            "</div>"
          ].join("")
        : "";

      return [
        '<div class="nova-message ' + escapeHtml(role) + '">',
        '  <div class="nova-message-inner">',
        '    <div class="nova-message-role">' + escapeHtml(role) + "</div>",
        '    <div class="nova-message-text">' + text + "</div>",
        imageBlock,
        (badges.length ? '    <div class="nova-message-badges">' + badges.join("") + "</div>" : ""),
        actions,
        "  </div>",
        "</div>"
      ].join("");
    }).join("");

    requestAnimationFrame(function () {
      if (els.chatScroll) {
        els.chatScroll.scrollTop = els.chatScroll.scrollHeight;
      }
    });
  }

  function renderPendingUploads() {
    if (!els.pendingUploads) return;
    if (!state.pendingUploads.length) {
      els.pendingUploads.innerHTML = "";
      return;
    }

    els.pendingUploads.innerHTML = state.pendingUploads.map(function (item, index) {
      const name = escapeHtml(item.name || ("file-" + index));
      return [
        '<div class="nova-upload-chip">',
        "  <span>" + name + "</span>",
        '  <button class="nova-link-btn" type="button" data-remove-upload="' + index + '">remove</button>',
        "</div>"
      ].join("");
    }).join("");
  }

  function renderMemory() {
    if (!els.memoryList) return;

    if (!state.memoryItems.length) {
      els.memoryList.innerHTML = [
        '<div class="nova-empty-state">',
        '  <div class="nova-empty-title">No memory items</div>',
        '  <div class="nova-empty-text">Save notes and preferences here.</div>',
        "</div>"
      ].join("");
      return;
    }

    els.memoryList.innerHTML = state.memoryItems.map(function (item) {
      const id = escapeHtml(item.id || "");
      const title = escapeHtml(item.kind || "memory");
      const body = escapeHtml(item.text || item.preview || "");
      const meta = escapeHtml(fmtDate(item.updated_at || item.created_at || ""));
      return [
        '<div class="nova-rail-card">',
        '  <div class="nova-rail-card-title">' + title + "</div>",
        (meta ? '  <div class="nova-rail-card-meta">' + meta + "</div>" : ""),
        '  <div class="nova-rail-card-body">' + body + "</div>",
        '  <div class="nova-message-actions">',
        '    <button class="nova-btn nova-btn-ghost" type="button" data-delete-memory="' + id + '">Delete</button>',
        "  </div>",
        "</div>"
      ].join("");
    }).join("");
  }

  function renderArtifacts() {
    if (!els.artifactList) return;

    if (!state.artifacts.length) {
      els.artifactList.innerHTML = [
        '<div class="nova-empty-state">',
        '  <div class="nova-empty-title">No artifacts yet</div>',
        '  <div class="nova-empty-text">Saved chat replies, web results, images, and analysis will show here.</div>',
        "</div>"
      ].join("");
      return;
    }

    els.artifactList.innerHTML = state.artifacts.map(function (item) {
      const id = escapeHtml(item.id || "");
      const viewer = item.viewer || {};
      const title = escapeHtml(item.title || viewer.title || item.kind || viewer.kind || "Artifact");
      const meta = escapeHtml([
        item.kind || viewer.kind || "",
        fmtDate(item.updated_at || item.created_at || "")
      ].filter(Boolean).join(" · "));
      const body = escapeHtml(
        shortText(
          item.preview ||
          viewer.body ||
          item.body ||
          item.summary ||
          item.notes ||
          "",
          220
        )
      );
      return [
        '<button class="nova-rail-card" type="button" data-open-artifact="' + id + '">',
        '  <div class="nova-rail-card-title">' + title + "</div>",
        (meta ? '  <div class="nova-rail-card-meta">' + meta + "</div>" : ""),
        (body ? '  <div class="nova-rail-card-body">' + body + "</div>" : ""),
        "</button>"
      ].join("");
    }).join("");
  }

  function renderWeb() {
    if (!els.webList) return;

    if (!state.webItems.length) {
      els.webList.innerHTML = [
        '<div class="nova-empty-state">',
        '  <div class="nova-empty-title">No web results</div>',
        '  <div class="nova-empty-text">Fetched pages and saved web artifacts will appear here.</div>',
        "</div>"
      ].join("");
      return;
    }

    els.webList.innerHTML = state.webItems.map(function (item) {
      const viewer = item.viewer || {};
      const title = escapeHtml(item.title || viewer.title || item.domain || "Web result");
      const url = item.source_url || viewer.source_url || item.url || "";
      const meta = escapeHtml([
        item.domain || "",
        fmtDate(item.updated_at || item.created_at || item.fetched_at || "")
      ].filter(Boolean).join(" · "));
      const body = escapeHtml(
        shortText(
          item.preview ||
          viewer.body ||
          item.summary ||
          item.description ||
          "",
          220
        )
      );

      return [
        '<div class="nova-rail-card">',
        '  <div class="nova-rail-card-title">' + title + "</div>",
        (meta ? '  <div class="nova-rail-card-meta">' + meta + "</div>" : ""),
        (body ? '  <div class="nova-rail-card-body">' + body + "</div>" : ""),
        (url ? '  <div class="nova-rail-card-meta"><a href="' + escapeHtml(url) + '" target="_blank" rel="noreferrer">Open source</a></div>' : ""),
        "</div>"
      ].join("");
    }).join("");
  }

  function renderRouteInspector() {
    if (!els.routeInspector) return;

    const message = state.activeRouteInspectMessageId
      ? findMessageById(state.activeRouteInspectMessageId)
      : findLatestAssistantRouteMessage();

    if (!message || !hasRouteMeta(message)) {
      els.routeInspector.innerHTML = [
        '<div class="nova-empty-state">',
        '  <div class="nova-empty-title">Route Inspector</div>',
        '  <div class="nova-empty-text">No route metadata saved for this message yet. Click a route badge on an assistant message after a routed response lands.</div>',
        "</div>"
      ].join("");
      return;
    }

    const meta = getRouteMeta(message);
    const mode = escapeHtml(getRouteMode(message) || "unknown");
    const reason = escapeHtml(getRouteReason(meta) || "No reason saved");
    const keywords = getRouteKeywords(meta);
    const build = escapeHtml(getRouteBuild(meta) || "n/a");
    const timestamp = escapeHtml(fmtDate(getRouteTimestamp(meta, message) || ""));
    const messageId = escapeHtml(getMessageId(message, state.messages.indexOf(message)));
    const sessionId = escapeHtml(state.sessionId || "");
    const raw = escapeHtml(getRouteRaw(meta));

    els.routeInspector.innerHTML = [
      '<div class="nova-route-card">',
      '  <div class="nova-route-card-head">',
      '    <div class="nova-route-card-title">Saved route metadata</div>',
      '    <button class="nova-btn nova-btn-ghost" type="button" data-clear-route-inspector="1">Clear</button>',
      "  </div>",

      '  <div class="nova-route-section">',
      '    <div class="nova-route-section-label">Mode</div>',
      '    <div class="nova-route-chip-row">',
      '      <span class="nova-route-chip mode">' + mode + "</span>",
      "    </div>",
      "  </div>",

      '  <div class="nova-route-section">',
      '    <div class="nova-route-section-label">Reason</div>',
      '    <div class="nova-route-value">' + reason + "</div>",
      "  </div>",

      '  <div class="nova-route-section">',
      '    <div class="nova-route-section-label">Matched keywords</div>',
      (
        keywords.length
          ? ('<div class="nova-route-chip-row">' + keywords.map(function (kw) {
              return '<span class="nova-route-chip keyword">' + escapeHtml(kw) + "</span>";
            }).join("") + "</div>")
          : '<div class="nova-route-value">No keywords saved</div>'
      ),
      "  </div>",

      '  <div class="nova-route-section">',
      '    <div class="nova-route-grid">',
      '      <div class="nova-route-mini">',
      '        <div class="nova-route-mini-label">Build</div>',
      '        <div class="nova-route-mini-value">' + build + "</div>",
      "      </div>",
      '      <div class="nova-route-mini">',
      '        <div class="nova-route-mini-label">Timestamp</div>',
      '        <div class="nova-route-mini-value">' + timestamp + "</div>",
      "      </div>",
      '      <div class="nova-route-mini">',
      '        <div class="nova-route-mini-label">Session</div>',
      '        <div class="nova-route-mini-value">' + sessionId + "</div>",
      "      </div>",
      '      <div class="nova-route-mini">',
      '        <div class="nova-route-mini-label">Message</div>',
      '        <div class="nova-route-mini-value">' + messageId + "</div>",
      "      </div>",
      "    </div>",
      "  </div>",

      '  <div class="nova-route-section">',
      '    <div class="nova-route-section-label">Raw metadata</div>',
      '    <pre class="nova-code-block">' + raw + "</pre>",
      "  </div>",
      "</div>"
    ].join("");
  }

  function findLatestAssistantRouteMessage() {
    for (let i = state.messages.length - 1; i >= 0; i -= 1) {
      const message = state.messages[i];
      const role = String(message.role || message.author || "").toLowerCase();
      if (role === "assistant" && hasRouteMeta(message)) {
        return message;
      }
    }
    return null;
  }

  function openRouteInspectorForMessage(messageId) {
    state.activeRouteInspectMessageId = String(messageId || "");
    setActivePanel("route");
    renderRouteInspector();
  }

  async function refreshState(options) {
    options = options || {};
    if (state.refreshing && !options.force) return;
    state.refreshing = true;

    try {
      const payload = await requestJson(API.state);
      state.lastStatePayload = payload || {};

      const sessions = normalizeSessions(payload.sessions);
      state.sessions = sessions;

      const explicitSessionId =
        payload.active_session_id ||
        payload.session_id ||
        (payload.active_session && payload.active_session.id) ||
        "";

      if (options.sessionId) {
        state.sessionId = String(options.sessionId);
      } else if (explicitSessionId) {
        state.sessionId = String(explicitSessionId);
      } else if (!state.sessionId && sessions.length) {
        state.sessionId = String(sessions[0].id || "");
      }

      const selectedSession =
        sessions.find(function (s) { return String(s.id || "") === String(state.sessionId || ""); }) ||
        payload.active_session ||
        null;

      if (selectedSession) {
        state.messages = normalizeMessages(selectedSession.messages || payload.messages || []);
      } else {
        state.messages = normalizeMessages(payload.messages || []);
      }

      state.memoryItems = normalizeMemory(payload.memory || payload.memory_items || []);
      state.artifacts = normalizeArtifacts(payload.artifacts || []);
      state.webItems = normalizeWebItems(payload.web || payload.web_items || [], state.artifacts);

      renderAll();
      if (!options.keepStatus) setComposerStatus("Ready", false);
    } catch (error) {
      err("refreshState failed", error);
      setComposerStatus(error.message || "Failed to load state", true);
    } finally {
      state.refreshing = false;
    }
  }

  async function createNewSession() {
    try {
      setComposerStatus("Creating session...", false);
      const data = await requestJson(API.newSession, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });

      const nextId =
        data.session_id ||
        (data.session && data.session.id) ||
        data.id ||
        "";

      if (nextId) {
        state.sessionId = String(nextId);
      }

      await refreshState({ force: true, sessionId: state.sessionId, keepStatus: true });
      setComposerStatus("New session created", false);
    } catch (error) {
      err("createNewSession failed", error);
      setComposerStatus(error.message || "Failed to create session", true);
    }
  }

  async function switchSession(sessionId) {
    state.sessionId = String(sessionId || "");
    await refreshState({ force: true, sessionId: state.sessionId, keepStatus: true });
  }

  async function renameSession(sessionId) {
    const session = state.sessions.find(function (item) {
      return String(item.id || "") === String(sessionId || "");
    });
    const currentTitle = (session && (session.title || session.name)) || "Untitled session";
    const nextTitle = window.prompt("Rename session", currentTitle);
    if (!nextTitle) return;

    try {
      await requestJson(API.renameSession, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, title: nextTitle })
      });
      await refreshState({ force: true, keepStatus: true });
      setComposerStatus("Session renamed", false);
    } catch (error) {
      err("renameSession failed", error);
      setComposerStatus(error.message || "Failed to rename session", true);
    }
  }

  async function pinSession(sessionId) {
    try {
      await requestJson(API.pinSession, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId })
      });
      await refreshState({ force: true, keepStatus: true });
      setComposerStatus("Session updated", false);
    } catch (error) {
      err("pinSession failed", error);
      setComposerStatus(error.message || "Failed to pin session", true);
    }
  }

  async function deleteSession(sessionId) {
    if (!window.confirm("Delete this session?")) return;

    try {
      const data = await requestJson(API.deleteSession, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId })
      });

      const nextSessionId =
        data.next_session_id ||
        data.session_id ||
        state.sessionId;

      state.sessionId = String(nextSessionId || "");
      await refreshState({ force: true, sessionId: state.sessionId, keepStatus: true });
      setComposerStatus("Session deleted", false);
    } catch (error) {
      err("deleteSession failed", error);
      setComposerStatus(error.message || "Failed to delete session", true);
    }
  }

  async function stageFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;

    state.uploading = true;
    renderTopbar();
    setComposerStatus("Uploading...", false);

    try {
      for (const file of files) {
        const form = new FormData();
        form.append("file", file);

        const res = await fetch(API.upload, {
          method: "POST",
          body: form
        });

        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error((data && (data.error || data.message)) || "Upload failed");
        }

        state.pendingUploads.push({
          id: data.id || data.file_id || data.upload_id || "",
          name: data.name || data.filename || file.name,
          url: data.url || data.file_url || "",
          mime_type: data.mime_type || file.type || ""
        });
      }

      renderPendingUploads();
      setComposerStatus("Upload staged", false);
    } catch (error) {
      err("stageFiles failed", error);
      setComposerStatus(error.message || "Upload failed", true);
    } finally {
      state.uploading = false;
      renderTopbar();
    }
  }

  function clearInput() {
    if (!els.chatInput) return;
    els.chatInput.value = "";
    autoGrowTextarea();
  }

  async function sendMessage(overrideText) {
    if (state.sending) return;

    const userText = (overrideText != null ? String(overrideText) : String(els.chatInput.value || "")).trim();
    if (!userText && !state.pendingUploads.length) return;

    state.sending = true;
    renderTopbar();
    setComposerStatus("Sending...", false);

    const payload = {
      session_id: state.sessionId || "",
      user_text: userText,
      attachments: state.pendingUploads.map(function (item) {
        return {
          id: item.id || "",
          name: item.name || "",
          url: item.url || "",
          mime_type: item.mime_type || ""
        };
      })
    };

    state.lastUserMessage = userText || null;

    try {
      let data = null;

      try {
        data = await requestJson(API.chat, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      } catch (streamingFallbackError) {
        warn("Streaming failed, falling back to JSON chat.", streamingFallbackError);
        data = await requestJson(API.chat, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      }

      if (data.session && data.session.id) {
        state.sessionId = String(data.session.id);
      } else if (data.session_id) {
        state.sessionId = String(data.session_id);
      }

      state.pendingUploads = [];
      clearInput();
      renderPendingUploads();

      await refreshState({ force: true, sessionId: state.sessionId, keepStatus: true });

      const latestRouteMessage = findLatestAssistantRouteMessage();
      if (latestRouteMessage && state.activePanel === "route") {
        state.activeRouteInspectMessageId = getMessageId(latestRouteMessage, state.messages.indexOf(latestRouteMessage));
      }

      renderRouteInspector();
      setComposerStatus("Sent", false);
    } catch (error) {
      err("sendMessage failed", error);
      setComposerStatus(error.message || "Send failed", true);
    } finally {
      state.sending = false;
      renderTopbar();
    }
  }

  async function regenerateFromMessage(messageId) {
    const message = findMessageById(messageId);
    if (!message) return;

    let seed = "";
    const idx = state.messages.indexOf(message);
    for (let i = idx - 1; i >= 0; i -= 1) {
      const prev = state.messages[i];
      const role = String(prev.role || prev.author || "").toLowerCase();
      if (role === "user") {
        seed = messageText(prev);
        break;
      }
    }

    if (!seed && state.lastUserMessage) {
      seed = state.lastUserMessage;
    }
    if (!seed) return;

    await sendMessage(seed);
  }

  async function addMemory() {
    const value = String((els.memoryInput && els.memoryInput.value) || "").trim();
    if (!value) return;

    if (!API.memoryCreate) {
      state.memoryItems.unshift({
        id: "local-" + Date.now(),
        text: value,
        kind: "note",
        created_at: new Date().toISOString()
      });
      if (els.memoryInput) els.memoryInput.value = "";
      renderMemory();
      setComposerStatus("Memory added locally", false);
      return;
    }

    try {
      await requestJson(API.memoryCreate, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: value })
      });
      if (els.memoryInput) els.memoryInput.value = "";
      await refreshState({ force: true, keepStatus: true });
      setComposerStatus("Memory saved", false);
    } catch (error) {
      err("addMemory failed", error);
      setComposerStatus(error.message || "Failed to save memory", true);
    }
  }

  async function deleteMemory(id) {
    if (!API.memoryDelete) {
      state.memoryItems = state.memoryItems.filter(function (item) {
        return String(item.id || "") !== String(id || "");
      });
      renderMemory();
      return;
    }

    try {
      await requestJson(API.memoryDelete, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: id })
      });
      await refreshState({ force: true, keepStatus: true });
      setComposerStatus("Memory deleted", false);
    } catch (error) {
      err("deleteMemory failed", error);
      setComposerStatus(error.message || "Failed to delete memory", true);
    }
  }

  function copyMessage(messageId) {
    const message = findMessageById(messageId);
    if (!message) return;
    const text = messageText(message);

    navigator.clipboard.writeText(text).then(function () {
      setComposerStatus("Copied", false);
    }).catch(function (error) {
      err("copyMessage failed", error);
      setComposerStatus("Copy failed", true);
    });
  }

  function openArtifact(artifactId) {
    const artifact = state.artifacts.find(function (item) {
      return String(item.id || "") === String(artifactId || "");
    });
    if (!artifact) return;

    if (window.NovaArtifacts && typeof window.NovaArtifacts.openArtifact === "function") {
      try {
        window.NovaArtifacts.openArtifact(artifact);
        setActivePanel("artifacts");
        return;
      } catch (error) {
        warn("NovaArtifacts.openArtifact failed", error);
      }
    }

    setActivePanel("artifacts");
  }

  function bindEvents() {
    if (els.sidebarToggle) {
      els.sidebarToggle.addEventListener("click", toggleSidebar);
    }

    if (els.collapsedNewChatBtn) {
      els.collapsedNewChatBtn.addEventListener("click", createNewSession);
    }

    if (els.newChatBtn) {
      els.newChatBtn.addEventListener("click", createNewSession);
    }

    if (els.routeInspectorBtn) {
      els.routeInspectorBtn.addEventListener("click", function () {
        const latest = findLatestAssistantRouteMessage();
        if (latest) {
          state.activeRouteInspectMessageId = getMessageId(latest, state.messages.indexOf(latest));
        }
        setActivePanel("route");
        renderRouteInspector();
      });
    }

    if (els.rightRailCloseBtn) {
      els.rightRailCloseBtn.addEventListener("click", function () {
        if (els.rightRail) {
          els.rightRail.style.display = "none";
        }
      });
    }

    qsa(".nova-rail-tab").forEach(function (tab) {
      tab.addEventListener("click", function () {
        setActivePanel(tab.dataset.panel || "artifacts");
      });
    });

    if (els.sendBtn) {
      els.sendBtn.addEventListener("click", function () {
        sendMessage();
      });
    }

    if (els.clearInputBtn) {
      els.clearInputBtn.addEventListener("click", clearInput);
    }

    if (els.voiceBtn) {
      els.voiceBtn.addEventListener("click", function () {
        setComposerStatus("Voice is not wired yet", false);
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
    }

    if (els.fileInput) {
      els.fileInput.addEventListener("change", function (event) {
        stageFiles(event.target.files);
        event.target.value = "";
      });
    }

    if (els.memoryAddBtn) {
      els.memoryAddBtn.addEventListener("click", addMemory);
    }

    if (els.memoryInput) {
      els.memoryInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
          addMemory();
        }
      });
    }

    document.addEventListener("click", function (event) {
      const sessionCard = event.target.closest(".nova-session-card");
      if (sessionCard && !event.target.closest("[data-action]")) {
        switchSession(sessionCard.dataset.sessionId || "");
        return;
      }

      const actionButton = event.target.closest("[data-action]");
      if (actionButton) {
        const action = actionButton.dataset.action || "";
        const sessionId = actionButton.dataset.sessionId || "";
        if (action === "rename") renameSession(sessionId);
        if (action === "pin") pinSession(sessionId);
        if (action === "delete") deleteSession(sessionId);
        return;
      }

      const removeUploadBtn = event.target.closest("[data-remove-upload]");
      if (removeUploadBtn) {
        const index = Number(removeUploadBtn.dataset.removeUpload || "-1");
        if (index >= 0) {
          state.pendingUploads.splice(index, 1);
          renderPendingUploads();
        }
        return;
      }

      const copyBtn = event.target.closest("[data-copy-message]");
      if (copyBtn) {
        copyMessage(copyBtn.dataset.copyMessage || "");
        return;
      }

      const regenBtn = event.target.closest("[data-regenerate-message]");
      if (regenBtn) {
        regenerateFromMessage(regenBtn.dataset.regenerateMessage || "");
        return;
      }

      const routeBtn = event.target.closest("[data-open-route]");
      if (routeBtn) {
        openRouteInspectorForMessage(routeBtn.dataset.openRoute || "");
        return;
      }

      const deleteMemoryBtn = event.target.closest("[data-delete-memory]");
      if (deleteMemoryBtn) {
        deleteMemory(deleteMemoryBtn.dataset.deleteMemory || "");
        return;
      }

      const openArtifactBtn = event.target.closest("[data-open-artifact]");
      if (openArtifactBtn) {
        openArtifact(openArtifactBtn.dataset.openArtifact || "");
        return;
      }

      const clearRouteBtn = event.target.closest("[data-clear-route-inspector]");
      if (clearRouteBtn) {
        state.activeRouteInspectMessageId = "";
        renderRouteInspector();
      }
    });
  }

  function cacheElements() {
    els.novaSidebar = qs("#novaSidebar");
    els.sidebarToggle = qs("#sidebarToggle");
    els.newChatBtn = qs("#newChatBtn");
    els.collapsedNewChatBtn = qs("#collapsedNewChatBtn");

    els.sessionList = qs("#sessionList");
    els.sessionCount = qs("#sessionCount");
    els.sessionTitle = qs("#sessionTitle");
    els.sessionSubtitle = qs("#sessionSubtitle");
    els.modelChip = qs("#modelChip");
    els.statusChip = qs("#statusChip");

    els.chatScroll = qs("#chatScroll");
    els.chatMessages = qs("#chatMessages");

    els.pendingUploads = qs("#pendingUploads");
    els.fileInput = qs("#fileInput");
    els.voiceBtn = qs("#voiceBtn");
    els.clearInputBtn = qs("#clearInputBtn");
    els.chatInput = qs("#chatInput");
    els.sendBtn = qs("#sendBtn");
    els.composerStatus = qs("#composerStatus");

    els.rightRail = qs("#rightRail");
    els.rightRailCloseBtn = qs("#rightRailCloseBtn");
    els.rightRailTitle = qs("#rightRailTitle");
    els.rightRailSubtitle = qs("#rightRailSubtitle");
    els.panelArtifacts = qs("#panelArtifacts");
    els.panelMemory = qs("#panelMemory");
    els.panelWeb = qs("#panelWeb");
    els.panelRoute = qs("#panelRoute");

    els.artifactList = qs("#artifactList");
    els.memoryList = qs("#memoryList");
    els.memoryInput = qs("#memoryInput");
    els.memoryAddBtn = qs("#memoryAddBtn");
    els.webList = qs("#webList");
    els.routeInspector = qs("#routeInspector");
    els.routeInspectorBtn = qs("#routeInspectorBtn");
  }

  async function boot() {
    if (state.booted) return;
    state.booted = true;

    try {
      log("boot start");
      cacheElements();
      bindEvents();
      autoGrowTextarea();
      setActivePanel(state.activePanel);
      await refreshState({ force: true });
      log("boot complete");
    } catch (error) {
      err("boot failed", error);
      setComposerStatus(error.message || "Boot failed", true);
    }
  }

  document.addEventListener("DOMContentLoaded", boot);
})();