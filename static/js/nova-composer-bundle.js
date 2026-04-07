(function () {
  "use strict";

  if (window.NovaComposerBundle) return;

  function log() {
    try {
      console.log("[NovaComposerBundle]", ...arguments);
    } catch (_) {}
  }

  function warn() {
    try {
      console.warn("[NovaComposerBundle]", ...arguments);
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

  function renderSafeText(value) {
    return escapeHtml(String(value == null ? "" : value)).replace(/\n/g, "<br>");
  }

  function formatDate(value) {
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
    const text = String(value == null ? "" : value).trim();
    if (!text) return "";
    if (text.length <= max) return text;
    return text.slice(0, Math.max(0, max - 1)).trimEnd() + "…";
  }

  function normalizeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function normalizeAttachment(raw) {
    raw = raw || {};
    return {
      id: raw.id || "",
      name: raw.name || raw.filename || "attachment",
      filename: raw.filename || raw.name || "attachment",
      url: raw.url || raw.file_url || raw.download_url || "",
      kind: raw.kind || raw.type || "",
      mime_type: raw.mime_type || raw.mimetype || ""
    };
  }

  function normalizeMessage(raw) {
    raw = raw || {};
    return {
      id: raw.id || raw.message_id || "",
      role: raw.role || "assistant",
      content: raw.content || raw.text || "",
      created_at: raw.created_at || raw.timestamp || "",
      artifact_id: raw.artifact_id || "",
      kind: raw.kind || "",
      image_url: raw.image_url || "",
      attachments: normalizeArray(raw.attachments).map(normalizeAttachment)
    };
  }

  function normalizeSession(raw) {
    raw = raw || {};
    return {
      id: raw.id || raw.session_id || "",
      title: raw.title || "Untitled session",
      preview: raw.preview || raw.last_message_preview || "",
      updated_at: raw.updated_at || raw.created_at || "",
      pinned: !!raw.pinned,
      message_count: Number(raw.message_count || 0),
      messages: normalizeArray(raw.messages).map(normalizeMessage)
    };
  }

  function normalizeViewer(raw) {
    raw = raw || {};
    const meta = raw.meta || {};
    const viewer = raw.viewer || {};
    return {
      kind: viewer.kind || raw.kind || "artifact",
      title: viewer.title || raw.title || "Untitled",
      body:
        viewer.body ||
        raw.body ||
        raw.content ||
        raw.text ||
        raw.preview ||
        "",
      source_url: viewer.source_url || raw.source_url || meta.source_url || meta.url || "",
      image_url: viewer.image_url || raw.image_url || meta.image_url || "",
      video_url: viewer.video_url || raw.video_url || meta.video_url || "",
      audio_url: viewer.audio_url || raw.audio_url || meta.audio_url || "",
      analysis_text:
        viewer.analysis_text ||
        raw.analysis_text ||
        meta.analysis_text ||
        "",
      bullets: normalizeArray(viewer.bullets || raw.bullets || meta.bullets),
      session_id: raw.session_id || meta.session_id || "",
      created_at: raw.created_at || meta.created_at || "",
      updated_at: raw.updated_at || meta.updated_at || "",
      preview: raw.preview || "",
      id: raw.id || raw.artifact_id || ""
    };
  }

  const els = {
    appShell: qs("[data-app-shell]"),
    sidebar: qs("[data-sidebar]"),
    sidebarReopen: qs("[data-action='reopen-sidebar']"),
    sessionList: qs("[data-session-list]"),
    chatThread: qs("[data-chat-thread]"),
    emptyState: qs("[data-empty-state]"),
    chatForm: qs("[data-chat-form]"),
    chatInput: qs("[data-chat-input]"),
    sendBtn: qs("[data-send-btn]"),
    fileInput: qs("[data-file-input]"),
    uploadStrip: qs("[data-upload-strip]"),
    topbarTitle: qs("[data-topbar-title]"),
    topbarSubtitle: qs("[data-topbar-subtitle]"),
    topbarStatusText: qs("[data-topbar-status-text]"),
    topbarModelText: qs("[data-topbar-model-text]"),

    rightRail: qs("[data-right-rail]"),
    railHeader: qs("[data-rail-header]"),
    railTitle: qs("[data-rail-title]"),
    railSubtitle: qs("[data-rail-subtitle]"),
    railBack: qs("[data-rail-back]"),
    railClose: qs("[data-rail-close]"),
    railReopen: qs("[data-action='reopen-rail']"),
    railTabs: qsa("[data-rail-tab]"),
    railPanels: qsa("[data-rail-panel]"),
    railBody: qs("[data-rail-body]"),
    railViewer: qs("[data-rail-viewer]"),

    artifactList: qs("[data-artifact-list]"),
    artifactEmpty: qs("[data-artifact-empty]"),
    memoryList: qs("[data-memory-list]"),
    memoryEmpty: qs("[data-memory-empty]"),
    webList: qs("[data-web-list]"),
    webEmpty: qs("[data-web-empty]"),

    viewerShell: qs("[data-viewer-shell]"),
    viewerHeader: qs("[data-viewer-header]"),
    viewerKicker: qs("[data-viewer-kicker]"),
    viewerTitle: qs("[data-viewer-title]"),
    viewerMeta: qs("[data-viewer-meta]"),
    viewerMedia: qs("[data-viewer-media]"),
    viewerImage: qs("[data-viewer-image]"),
    viewerVideo: qs("[data-viewer-video]"),
    viewerAudio: qs("[data-viewer-audio]"),
    viewerActions: qs("[data-viewer-actions]"),
    viewerSourceLink: qs("[data-viewer-source-link]"),
    viewerOpenSession: qs("[data-viewer-open-session]"),
    viewerBody: qs("[data-viewer-body]"),
    viewerAnalysis: qs("[data-viewer-analysis]"),
    viewerAnalysisText: qs("[data-viewer-analysis-text]"),
    viewerBulletsWrap: qs("[data-viewer-bullets-wrap]"),
    viewerBullets: qs("[data-viewer-bullets]")
  };

  const state = {
    sessions: [],
    artifacts: [],
    memory: [],
    web: [],
    activeSessionId: "",
    stagedFiles: [],
    sending: false,
    regeneratingMessageId: "",
    rail: {
      open: true,
      activePanel: "artifacts",
      mode: "list",
      viewerItem: null
    }
  };

  async function api(path, options) {
    const response = await fetch(
      path,
      Object.assign(
        {
          headers: {
            "Content-Type": "application/json"
          }
        },
        options || {}
      )
    );

    const contentType = response.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");
    const payload = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      const message =
        (payload && payload.error) ||
        (payload && payload.message) ||
        (typeof payload === "string" ? payload : "Request failed");
      throw new Error(message);
    }

    return payload;
  }

  function getActiveSession() {
    return (
      state.sessions.find(function (session) {
        return session.id === state.activeSessionId;
      }) || null
    );
  }

  function findSessionIndex(sessionId) {
    return state.sessions.findIndex(function (session) {
      return session.id === sessionId;
    });
  }

  function replaceOrInsertSession(sessionLike) {
    const normalized = normalizeSession(sessionLike);
    if (!normalized.id) return null;

    const existingIndex = findSessionIndex(normalized.id);
    if (existingIndex >= 0) {
      state.sessions[existingIndex] = normalized;
    } else {
      state.sessions.unshift(normalized);
    }
    state.activeSessionId = normalized.id;
    return normalized;
  }

  function getMessageIndexById(session, messageId) {
    if (!session || !messageId) return -1;
    return normalizeArray(session.messages).findIndex(function (message) {
      return message.id === messageId;
    });
  }

  function getLastAssistantMessage(session) {
    if (!session) return null;
    const messages = normalizeArray(session.messages);
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i] && messages[i].role === "assistant") {
        return messages[i];
      }
    }
    return null;
  }

  function setTopbarFromSession() {
    const session = getActiveSession();
    if (els.topbarTitle) {
      els.topbarTitle.textContent = session ? session.title || "Nova" : "Nova";
    }
    if (els.topbarSubtitle) {
      els.topbarSubtitle.textContent = session
        ? session.message_count
          ? session.message_count + " messages"
          : "Fast local AI workspace"
        : "Fast local AI workspace";
    }
  }

  function setStatus(text) {
    if (els.topbarStatusText) {
      els.topbarStatusText.textContent = text || "Ready";
    }
  }

  function ensureRailOpen() {
    state.rail.open = true;
    if (els.rightRail) els.rightRail.hidden = false;
    if (els.rightRail) els.rightRail.classList.add("is-open");
    if (els.railReopen) els.railReopen.hidden = true;
  }

  function closeRail() {
    state.rail.open = false;
    if (els.rightRail) els.rightRail.hidden = true;
    if (els.rightRail) els.rightRail.classList.remove("is-open");
    if (els.railReopen) els.railReopen.hidden = false;
  }

  function setRailHeader(title, subtitle) {
    if (els.railTitle) {
      els.railTitle.textContent = title || "";
    }
    if (els.railSubtitle) {
      els.railSubtitle.textContent = subtitle || "";
    }
  }

  function getRailPanelMeta(panel) {
    if (panel === "memory") {
      return {
        title: "Memory",
        subtitle: "Saved preferences and notes"
      };
    }
    if (panel === "web") {
      return {
        title: "Web",
        subtitle: "Fetched pages and web results"
      };
    }
    return {
      title: "Artifacts",
      subtitle: "Saved outputs and reopened results"
    };
  }

  function syncRailTabs() {
    els.railTabs.forEach(function (button) {
      const panel = button.getAttribute("data-panel");
      const active = panel === state.rail.activePanel && state.rail.mode === "list";
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function syncRailPanels() {
    els.railPanels.forEach(function (panelEl) {
      const panelName = panelEl.getAttribute("data-rail-panel");
      const show = state.rail.mode === "list" && panelName === state.rail.activePanel;
      panelEl.hidden = !show;
      panelEl.classList.toggle("is-active", show);
    });

    if (els.railViewer) {
      const showViewer = state.rail.mode === "viewer";
      els.railViewer.hidden = !showViewer;
      els.railViewer.classList.toggle("is-active", showViewer);
    }

    if (els.railBack) {
      els.railBack.hidden = state.rail.mode !== "viewer";
    }
  }

  function setRailPanel(panelName) {
    const allowed = ["artifacts", "memory", "web"];
    if (allowed.indexOf(panelName) === -1) {
      warn("Unknown rail panel:", panelName);
      return;
    }

    state.rail.activePanel = panelName;
    state.rail.mode = "list";
    state.rail.viewerItem = null;

    const meta = getRailPanelMeta(panelName);
    setRailHeader(meta.title, meta.subtitle);
    syncRailTabs();
    syncRailPanels();
    ensureRailOpen();
  }

  function showRailViewer(viewerItem, options) {
    options = options || {};
    state.rail.mode = "viewer";
    state.rail.viewerItem = viewerItem || null;

    if (els.railTitle) {
      els.railTitle.textContent = options.headerTitle || "Viewer";
    }
    if (els.railSubtitle) {
      els.railSubtitle.textContent = options.headerSubtitle || "Detail view";
    }

    syncRailTabs();
    syncRailPanels();
    renderViewer();
    ensureRailOpen();
  }

  function backToRailList() {
    state.rail.mode = "list";
    state.rail.viewerItem = null;
    const meta = getRailPanelMeta(state.rail.activePanel);
    setRailHeader(meta.title, meta.subtitle);
    syncRailTabs();
    syncRailPanels();
  }

  function clearViewerMedia() {
    if (els.viewerImage) {
      els.viewerImage.hidden = true;
      els.viewerImage.removeAttribute("src");
      els.viewerImage.setAttribute("alt", "");
    }
    if (els.viewerVideo) {
      els.viewerVideo.hidden = true;
      els.viewerVideo.removeAttribute("src");
      try {
        els.viewerVideo.load();
      } catch (_) {}
    }
    if (els.viewerAudio) {
      els.viewerAudio.hidden = true;
      els.viewerAudio.removeAttribute("src");
      try {
        els.viewerAudio.load();
      } catch (_) {}
    }
    if (els.viewerMedia) {
      els.viewerMedia.hidden = true;
    }
  }

  function renderViewer() {
    const item = state.rail.viewerItem;

    if (!item) {
      if (els.viewerKicker) els.viewerKicker.textContent = "";
      if (els.viewerTitle) els.viewerTitle.textContent = "";
      if (els.viewerMeta) els.viewerMeta.textContent = "";
      if (els.viewerBody) els.viewerBody.innerHTML = "";
      if (els.viewerAnalysisText) els.viewerAnalysisText.innerHTML = "";
      if (els.viewerAnalysis) els.viewerAnalysis.hidden = true;
      if (els.viewerBullets) els.viewerBullets.innerHTML = "";
      if (els.viewerBulletsWrap) els.viewerBulletsWrap.hidden = true;
      if (els.viewerSourceLink) els.viewerSourceLink.hidden = true;
      if (els.viewerOpenSession) els.viewerOpenSession.hidden = true;
      clearViewerMedia();
      return;
    }

    if (els.viewerKicker) {
      els.viewerKicker.textContent = item.kind || "";
    }

    if (els.viewerTitle) {
      els.viewerTitle.textContent = item.title || "Untitled";
    }

    if (els.viewerMeta) {
      const bits = [];
      if (item.updated_at) bits.push("Updated " + formatDate(item.updated_at));
      else if (item.created_at) bits.push("Created " + formatDate(item.created_at));
      if (item.id) bits.push("ID " + item.id);
      els.viewerMeta.textContent = bits.join(" · ");
    }

    if (els.viewerBody) {
      els.viewerBody.innerHTML = renderSafeText(item.body || item.preview || "");
    }

    if (els.viewerAnalysis && els.viewerAnalysisText) {
      const hasAnalysis = !!String(item.analysis_text || "").trim();
      els.viewerAnalysis.hidden = !hasAnalysis;
      els.viewerAnalysisText.innerHTML = hasAnalysis ? renderSafeText(item.analysis_text) : "";
    }

    if (els.viewerBullets && els.viewerBulletsWrap) {
      const bullets = normalizeArray(item.bullets).filter(Boolean);
      els.viewerBulletsWrap.hidden = bullets.length === 0;
      els.viewerBullets.innerHTML = bullets
        .map(function (bullet) {
          return "<li>" + escapeHtml(String(bullet)) + "</li>";
        })
        .join("");
    }

    if (els.viewerSourceLink) {
      if (item.source_url) {
        els.viewerSourceLink.hidden = false;
        els.viewerSourceLink.href = item.source_url;
      } else {
        els.viewerSourceLink.hidden = true;
        els.viewerSourceLink.removeAttribute("href");
      }
    }

    if (els.viewerOpenSession) {
      els.viewerOpenSession.hidden = !item.session_id;
    }

    clearViewerMedia();

    if (item.image_url && els.viewerImage && els.viewerMedia) {
      els.viewerMedia.hidden = false;
      els.viewerImage.hidden = false;
      els.viewerImage.src = item.image_url;
      els.viewerImage.alt = item.title || "Viewer image";
      return;
    }

    if (item.video_url && els.viewerVideo && els.viewerMedia) {
      els.viewerMedia.hidden = false;
      els.viewerVideo.hidden = false;
      els.viewerVideo.src = item.video_url;
      try {
        els.viewerVideo.load();
      } catch (_) {}
      return;
    }

    if (item.audio_url && els.viewerAudio && els.viewerMedia) {
      els.viewerMedia.hidden = false;
      els.viewerAudio.hidden = false;
      els.viewerAudio.src = item.audio_url;
      try {
        els.viewerAudio.load();
      } catch (_) {}
    }
  }

  function renderSessions() {
    if (!els.sessionList) return;

    const items = state.sessions.slice().sort(function (a, b) {
      if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;
      const ad = new Date(a.updated_at || 0).getTime();
      const bd = new Date(b.updated_at || 0).getTime();
      return bd - ad;
    });

    if (!items.length) {
      els.sessionList.innerHTML = '<div class="nova-rail-empty">No sessions yet.</div>';
      return;
    }

    els.sessionList.innerHTML = items
      .map(function (session) {
        const active = session.id === state.activeSessionId;
        return [
          '<button class="nova-session-card' + (active ? " is-active" : "") + '" type="button" data-open-session="' + escapeHtml(session.id) + '">',
          '  <div class="nova-session-card-top">',
          '    <div class="nova-session-card-title">' + escapeHtml(session.title || "Untitled session") + "</div>",
          session.pinned ? '    <div class="nova-session-card-pin">📌</div>' : "",
          "  </div>",
          '  <div class="nova-session-card-preview">' + escapeHtml(shortText(session.preview || "", 80) || "No messages yet.") + "</div>",
          '  <div class="nova-session-card-meta">' + escapeHtml(formatDate(session.updated_at) || "") + "</div>",
          "</button>"
        ].join("");
      })
      .join("");
  }

  function renderMessageAttachment(attachment) {
    attachment = normalizeAttachment(attachment);
    const label = attachment.name || attachment.filename || "attachment";

    if (attachment.url) {
      return [
        '<a class="nova-message-attachment" href="' + escapeHtml(attachment.url) + '" target="_blank" rel="noreferrer">',
        escapeHtml(label),
        "</a>"
      ].join("");
    }

    return '<div class="nova-message-attachment">' + escapeHtml(label) + "</div>";
  }

  function renderMessageActions(message) {
    if (!message || message.role !== "assistant") return "";

    const busy = state.regeneratingMessageId && state.regeneratingMessageId === message.id;
    return [
      '<div class="nova-message-actions">',
      '  <button class="nova-secondary-btn nova-message-action-btn" type="button" data-copy-message="' + escapeHtml(message.id) + '">Copy</button>',
      '  <button class="nova-secondary-btn nova-message-action-btn' + (busy ? " is-busy" : "") + '" type="button" data-regenerate-message="' + escapeHtml(message.id) + '"' + (busy ? " disabled" : "") + ">",
      busy ? "Regenerating..." : "Regenerate",
      "  </button>",
      "</div>"
    ].join("");
  }

  function renderMessages() {
    if (!els.chatThread) return;

    const session = getActiveSession();
    const messages = session ? normalizeArray(session.messages) : [];

    if (els.emptyState) {
      els.emptyState.hidden = messages.length > 0;
    }

    if (!messages.length) {
      els.chatThread.innerHTML = els.emptyState ? els.emptyState.outerHTML : "";
      return;
    }

    els.chatThread.innerHTML = messages
      .map(function (message) {
        const role = message.role === "user" ? "user" : "assistant";
        const attachmentsHtml = normalizeArray(message.attachments).map(renderMessageAttachment).join("");
        const imageHtml = message.image_url
          ? '<div class="nova-message-image-wrap"><img class="nova-message-image" src="' + escapeHtml(message.image_url) + '" alt="Generated image"></div>'
          : "";

        return [
          '<article class="nova-message nova-message-' + role + '" data-message-id="' + escapeHtml(message.id) + '">',
          '  <div class="nova-message-bubble">',
          '    <div class="nova-message-content">' + renderSafeText(message.content || "") + "</div>",
          imageHtml,
          attachmentsHtml ? '<div class="nova-message-attachments">' + attachmentsHtml + "</div>" : "",
          message.role === "assistant" ? renderMessageActions(message) : "",
          "  </div>",
          "</article>"
        ].join("");
      })
      .join("");
  }

  function renderArtifactList() {
    if (!els.artifactList) return;

    const items = state.artifacts.slice().sort(function (a, b) {
      const ad = new Date(a.updated_at || a.created_at || 0).getTime();
      const bd = new Date(b.updated_at || b.created_at || 0).getTime();
      return bd - ad;
    });

    if (els.artifactEmpty) {
      els.artifactEmpty.hidden = items.length !== 0;
    }

    if (!items.length) {
      els.artifactList.innerHTML = "";
      return;
    }

    els.artifactList.innerHTML = items
      .map(function (artifact) {
        return [
          '<button class="nova-rail-card" type="button" data-open-artifact="' + escapeHtml(artifact.id) + '">',
          '  <div class="nova-rail-card-kicker">' + escapeHtml(artifact.kind || "artifact") + "</div>",
          '  <div class="nova-rail-card-title">' + escapeHtml(artifact.title || "Untitled") + "</div>",
          '  <div class="nova-rail-card-preview">' + escapeHtml(shortText(artifact.preview || artifact.body || "", 120)) + "</div>",
          '  <div class="nova-rail-card-meta">' + escapeHtml(formatDate(artifact.updated_at || artifact.created_at) || "") + "</div>",
          "</button>"
        ].join("");
      })
      .join("");
  }

  function renderMemoryList() {
    if (!els.memoryList) return;

    const items = state.memory.slice().sort(function (a, b) {
      const ad = new Date((a && (a.updated_at || a.created_at)) || 0).getTime();
      const bd = new Date((b && (b.updated_at || b.created_at)) || 0).getTime();
      return bd - ad;
    });

    if (els.memoryEmpty) {
      els.memoryEmpty.hidden = items.length !== 0;
    }

    if (!items.length) {
      els.memoryList.innerHTML = "";
      return;
    }

    els.memoryList.innerHTML = items
      .map(function (item, index) {
        const id = item && (item.id || "memory-" + index);
        const title = item && (item.kind || "memory");
        const body = item && (item.text || item.body || item.preview || "");
        const updatedAt = item && (item.updated_at || item.created_at || "");
        return [
          '<button class="nova-rail-card" type="button" data-open-memory="' + escapeHtml(String(id)) + '">',
          '  <div class="nova-rail-card-kicker">' + escapeHtml(String(title)) + "</div>",
          '  <div class="nova-rail-card-title">' + escapeHtml(shortText(body, 48) || "Memory item") + "</div>",
          '  <div class="nova-rail-card-preview">' + escapeHtml(shortText(body, 120)) + "</div>",
          '  <div class="nova-rail-card-meta">' + escapeHtml(formatDate(updatedAt) || "") + "</div>",
          "</button>"
        ].join("");
      })
      .join("");
  }

  function renderWebList() {
    if (!els.webList) return;

    const items = state.web.slice().sort(function (a, b) {
      const ad = new Date((a && (a.updated_at || a.created_at)) || 0).getTime();
      const bd = new Date((b && (b.updated_at || b.created_at)) || 0).getTime();
      return bd - ad;
    });

    if (els.webEmpty) {
      els.webEmpty.hidden = items.length !== 0;
    }

    if (!items.length) {
      els.webList.innerHTML = "";
      return;
    }

    els.webList.innerHTML = items
      .map(function (item, index) {
        const id = item && (item.id || "web-" + index);
        const title = item && (item.title || "Web result");
        const preview = item && (item.preview || item.description || item.body || "");
        const updatedAt = item && (item.updated_at || item.created_at || "");
        return [
          '<button class="nova-rail-card" type="button" data-open-web="' + escapeHtml(String(id)) + '">',
          '  <div class="nova-rail-card-kicker">web</div>',
          '  <div class="nova-rail-card-title">' + escapeHtml(title) + "</div>",
          '  <div class="nova-rail-card-preview">' + escapeHtml(shortText(preview, 120)) + "</div>",
          '  <div class="nova-rail-card-meta">' + escapeHtml(formatDate(updatedAt) || "") + "</div>",
          "</button>"
        ].join("");
      })
      .join("");
  }

  function renderUploadStrip() {
    if (!els.uploadStrip) return;

    const files = normalizeArray(state.stagedFiles);
    if (!files.length) {
      els.uploadStrip.hidden = true;
      els.uploadStrip.innerHTML = "";
      return;
    }

    els.uploadStrip.hidden = false;
    els.uploadStrip.innerHTML = files
      .map(function (file, index) {
        const name = file && file.name ? file.name : "file-" + index;
        return [
          '<div class="nova-upload-chip">',
          '  <span class="nova-upload-chip-name">' + escapeHtml(name) + "</span>",
          '  <button class="nova-upload-chip-remove" type="button" data-remove-upload="' + index + '" aria-label="Remove file">×</button>',
          "</div>"
        ].join("");
      })
      .join("");
  }

  function renderAll() {
    setTopbarFromSession();
    renderSessions();
    renderMessages();
    renderArtifactList();
    renderMemoryList();
    renderWebList();
    renderUploadStrip();
    syncRailTabs();
    syncRailPanels();
    renderViewer();
  }

  async function loadState() {
    setStatus("Loading");
    const data = await api("/api/state", { method: "GET" });

    state.sessions = normalizeArray(data.sessions).map(normalizeSession);
    state.artifacts = normalizeArray(data.artifacts).map(normalizeViewer);
    state.memory = normalizeArray(data.memory).map(function (item) {
      return item || {};
    });

    const rawWeb = normalizeArray(data.web);
    const webFromArtifacts = state.artifacts.filter(function (item) {
      return item.kind === "web" || item.kind === "web_result" || item.kind === "web_fetch";
    });

    state.web = rawWeb.length ? rawWeb : webFromArtifacts;

    state.activeSessionId =
      data.active_session_id ||
      (data.active_session && data.active_session.id) ||
      state.activeSessionId ||
      (state.sessions[0] ? state.sessions[0].id : "");

    if (!state.activeSessionId && state.sessions[0]) {
      state.activeSessionId = state.sessions[0].id;
    }

    renderAll();
    setStatus("Ready");
  }

  async function openSession(sessionId) {
    if (!sessionId) return;
    setStatus("Opening");

    try {
      const payload = await api("/api/sessions/open", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId })
      });

      const opened = payload.session || payload.active_session || payload;
      replaceOrInsertSession(opened);
      renderAll();
      setStatus("Ready");
    } catch (error) {
      warn("Failed to open session:", error);
      setStatus("Error");
      throw error;
    }
  }

  async function createNewChat() {
    setStatus("Creating");
    const payload = await api("/api/sessions/new", {
      method: "POST",
      body: JSON.stringify({})
    });

    replaceOrInsertSession(payload.session || payload);
    renderAll();
    setStatus("Ready");
  }

  async function sendMessage() {
    const input = els.chatInput;
    const text = input ? String(input.value || "").trim() : "";

    if (!text && !state.stagedFiles.length) return;
    if (state.sending || state.regeneratingMessageId) return;

    state.sending = true;
    if (els.sendBtn) els.sendBtn.disabled = true;
    setStatus("Sending");

    try {
      const activeSession = getActiveSession();
      const optimisticId = "local-user-" + Date.now();

      if (activeSession) {
        const optimisticMessage = normalizeMessage({
          id: optimisticId,
          role: "user",
          content: text,
          created_at: new Date().toISOString(),
          attachments: state.stagedFiles.map(function (file) {
            return { name: file.name || "file" };
          })
        });
        activeSession.messages = activeSession.messages.concat([optimisticMessage]);
        activeSession.message_count = activeSession.messages.length;
        activeSession.updated_at = new Date().toISOString();
      }

      renderMessages();

      const payload = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          session_id: state.activeSessionId,
          user_text: text
        })
      });

      const sessionPayload = payload.session || payload.active_session || null;
      const assistantMessage = payload.assistant_message || payload.message || null;
      const artifact = payload.artifact || null;

      if (sessionPayload && sessionPayload.id) {
        replaceOrInsertSession(sessionPayload);
      } else {
        const session = getActiveSession();
        if (session && assistantMessage) {
          session.messages = session.messages.concat([normalizeMessage(assistantMessage)]);
          session.message_count = session.messages.length;
          session.updated_at = new Date().toISOString();
        }
      }

      if (artifact) {
        state.artifacts.unshift(normalizeViewer(artifact));
      }

      if (els.chatInput) {
        els.chatInput.value = "";
      }

      state.stagedFiles = [];
      renderAll();
      setStatus("Ready");
    } catch (error) {
      warn("Send failed:", error);
      setStatus("Error");
      throw error;
    } finally {
      state.sending = false;
      if (els.sendBtn) els.sendBtn.disabled = false;
    }
  }

  function buildRegenerateRequestPayload(session, targetMessage) {
    return {
      session_id: session ? session.id : state.activeSessionId,
      regenerate: true,
      target_message_id: targetMessage ? targetMessage.id : "",
      assistant_message_id: targetMessage ? targetMessage.id : "",
      message_id: targetMessage ? targetMessage.id : "",
      user_text: ""
    };
  }

  async function regenerateMessage(messageId) {
    if (!messageId) return;
    if (state.sending || state.regeneratingMessageId) return;

    const session = getActiveSession();
    if (!session) return;

    const targetIndex = getMessageIndexById(session, messageId);
    if (targetIndex === -1) return;

    const targetMessage = session.messages[targetIndex];
    if (!targetMessage || targetMessage.role !== "assistant") return;

    state.regeneratingMessageId = messageId;
    setStatus("Regenerating");
    renderMessages();

    try {
      const payload = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify(buildRegenerateRequestPayload(session, targetMessage))
      });

      const sessionPayload = payload.session || payload.active_session || null;
      const assistantMessage = payload.assistant_message || payload.message || null;
      const artifact = payload.artifact || null;

      if (sessionPayload && sessionPayload.id) {
        replaceOrInsertSession(sessionPayload);
      } else if (assistantMessage) {
        const activeSession = getActiveSession();
        const normalizedAssistant = normalizeMessage(assistantMessage);
        const replaceIndex = getMessageIndexById(activeSession, messageId);

        if (replaceIndex >= 0) {
          activeSession.messages.splice(replaceIndex, 1, normalizedAssistant);
        } else {
          const lastAssistant = getLastAssistantMessage(activeSession);
          if (lastAssistant) {
            const lastAssistantIndex = getMessageIndexById(activeSession, lastAssistant.id);
            if (lastAssistantIndex >= 0) {
              activeSession.messages.splice(lastAssistantIndex, 1, normalizedAssistant);
            } else {
              activeSession.messages.push(normalizedAssistant);
            }
          } else {
            activeSession.messages.push(normalizedAssistant);
          }
        }

        activeSession.message_count = activeSession.messages.length;
        activeSession.updated_at = new Date().toISOString();
      }

      if (artifact) {
        state.artifacts.unshift(normalizeViewer(artifact));
      }

      renderAll();
      setStatus("Ready");
    } catch (error) {
      warn("Regenerate failed:", error);
      setStatus("Error");
      throw error;
    } finally {
      state.regeneratingMessageId = "";
      renderMessages();
    }
  }

  function findArtifactById(id) {
    return (
      state.artifacts.find(function (item) {
        return item.id === id;
      }) || null
    );
  }

  function findMemoryById(id) {
    return (
      state.memory.find(function (item, index) {
        return String(item && item.id ? item.id : "memory-" + index) === String(id);
      }) || null
    );
  }

  function findWebById(id) {
    return (
      state.web.find(function (item, index) {
        return String(item && item.id ? item.id : "web-" + index) === String(id);
      }) || null
    );
  }

  function openArtifactViewer(artifactId) {
    const artifact = findArtifactById(artifactId);
    if (!artifact) return;
    state.rail.activePanel = "artifacts";
    showRailViewer(artifact, {
      headerTitle: "Artifact",
      headerSubtitle: artifact.kind || "Saved output"
    });
  }

  function openMemoryViewer(memoryId) {
    const item = findMemoryById(memoryId);
    if (!item) return;

    const viewer = {
      id: item.id || memoryId,
      kind: item.kind || "memory",
      title: shortText(item.text || item.body || "Memory item", 60) || "Memory item",
      body: item.text || item.body || item.preview || "",
      created_at: item.created_at || "",
      updated_at: item.updated_at || "",
      bullets: []
    };

    state.rail.activePanel = "memory";
    showRailViewer(viewer, {
      headerTitle: "Memory",
      headerSubtitle: viewer.kind || "Saved note"
    });
  }

  function openWebViewer(webId) {
    const item = findWebById(webId);
    if (!item) return;

    const viewer = normalizeViewer(
      Object.assign({}, item, {
        kind: item.kind || "web"
      })
    );

    state.rail.activePanel = "web";
    showRailViewer(viewer, {
      headerTitle: "Web",
      headerSubtitle: "Fetched result"
    });
  }

  async function openViewerSession() {
    const item = state.rail.viewerItem;
    if (!item || !item.session_id) return;
    await openSession(item.session_id);
    closeRail();
  }

  async function copyMessageById(messageId) {
    const session = getActiveSession();
    if (!session) return;

    const message = normalizeArray(session.messages).find(function (item) {
      return item.id === messageId;
    });
    if (!message) return;

    const text = String(message.content || "");
    if (!text) return;

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const temp = document.createElement("textarea");
        temp.value = text;
        temp.setAttribute("readonly", "readonly");
        temp.style.position = "fixed";
        temp.style.top = "-9999px";
        document.body.appendChild(temp);
        temp.select();
        document.execCommand("copy");
        document.body.removeChild(temp);
      }
      setStatus("Copied");
      window.setTimeout(function () {
        if (!state.sending && !state.regeneratingMessageId) {
          setStatus("Ready");
        }
      }, 900);
    } catch (error) {
      warn("Copy failed:", error);
      setStatus("Copy error");
    }
  }

  function bindRailActions() {
    if (els.railTabs && els.railTabs.length) {
      els.railTabs.forEach(function (button) {
        button.addEventListener("click", function () {
          const panel = button.getAttribute("data-panel");
          setRailPanel(panel);
        });
      });
    }

    if (els.railClose) {
      els.railClose.addEventListener("click", function () {
        closeRail();
      });
    }

    if (els.railReopen) {
      els.railReopen.addEventListener("click", function () {
        ensureRailOpen();
      });
    }

    const topbarRailToggle = qs("[data-action='toggle-rail']");
    if (topbarRailToggle) {
      topbarRailToggle.addEventListener("click", function () {
        if (state.rail.open) closeRail();
        else ensureRailOpen();
      });
    }

    if (els.railBack) {
      els.railBack.addEventListener("click", function () {
        backToRailList();
      });
    }

    if (els.viewerOpenSession) {
      els.viewerOpenSession.addEventListener("click", function () {
        openViewerSession().catch(function (error) {
          warn("Open viewer session failed:", error);
        });
      });
    }
  }

  function bindSidebarActions() {
    const toggleSidebar = qs("[data-action='toggle-sidebar']");
    if (toggleSidebar && els.sidebar) {
      toggleSidebar.addEventListener("click", function () {
        els.sidebar.hidden = true;
        if (els.sidebarReopen) els.sidebarReopen.hidden = false;
      });
    }

    if (els.sidebarReopen && els.sidebar) {
      els.sidebarReopen.addEventListener("click", function () {
        els.sidebar.hidden = false;
        els.sidebarReopen.hidden = true;
      });
    }

    const newChatBtn = qs("[data-action='new-chat']");
    if (newChatBtn) {
      newChatBtn.addEventListener("click", function () {
        createNewChat().catch(function (error) {
          warn("New chat failed:", error);
        });
      });
    }
  }

  function bindComposerActions() {
    if (els.chatForm) {
      els.chatForm.addEventListener("submit", function (event) {
        event.preventDefault();
        sendMessage().catch(function (error) {
          warn("Submit failed:", error);
        });
      });
    }

    if (els.chatInput) {
      els.chatInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage().catch(function (error) {
            warn("Enter send failed:", error);
          });
        }
      });
    }

    if (els.fileInput) {
      els.fileInput.addEventListener("change", function () {
        const files = Array.from(els.fileInput.files || []);
        state.stagedFiles = files;
        renderUploadStrip();
      });
    }
  }

  function bindDelegatedClicks() {
    document.addEventListener("click", function (event) {
      const sessionButton = event.target.closest("[data-open-session]");
      if (sessionButton) {
        const sessionId = sessionButton.getAttribute("data-open-session");
        openSession(sessionId).catch(function (error) {
          warn("Session click failed:", error);
        });
        return;
      }

      const artifactButton = event.target.closest("[data-open-artifact]");
      if (artifactButton) {
        const artifactId = artifactButton.getAttribute("data-open-artifact");
        openArtifactViewer(artifactId);
        return;
      }

      const memoryButton = event.target.closest("[data-open-memory]");
      if (memoryButton) {
        const memoryId = memoryButton.getAttribute("data-open-memory");
        openMemoryViewer(memoryId);
        return;
      }

      const webButton = event.target.closest("[data-open-web]");
      if (webButton) {
        const webId = webButton.getAttribute("data-open-web");
        openWebViewer(webId);
        return;
      }

      const removeUploadButton = event.target.closest("[data-remove-upload]");
      if (removeUploadButton) {
        const index = Number(removeUploadButton.getAttribute("data-remove-upload"));
        if (!Number.isNaN(index)) {
          state.stagedFiles.splice(index, 1);
          renderUploadStrip();
        }
        return;
      }

      const copyButton = event.target.closest("[data-copy-message]");
      if (copyButton) {
        const messageId = copyButton.getAttribute("data-copy-message");
        copyMessageById(messageId).catch(function (error) {
          warn("Copy click failed:", error);
        });
        return;
      }

      const regenerateButton = event.target.closest("[data-regenerate-message]");
      if (regenerateButton) {
        const messageId = regenerateButton.getAttribute("data-regenerate-message");
        regenerateMessage(messageId).catch(function (error) {
          warn("Regenerate click failed:", error);
        });
      }
    });
  }

  function verifyRailContract() {
    const required = [
      "rightRail",
      "railTitle",
      "railSubtitle",
      "railBack",
      "railClose",
      "railTabs",
      "railPanels",
      "railViewer",
      "artifactList",
      "memoryList",
      "webList",
      "viewerTitle",
      "viewerBody",
      "viewerSourceLink",
      "viewerOpenSession"
    ];

    const missing = required.filter(function (key) {
      const value = els[key];
      if (Array.isArray(value)) return value.length === 0;
      return !value;
    });

    if (missing.length) {
      throw new Error("Rail DOM contract mismatch: missing " + missing.join(", "));
    }
  }

  async function boot() {
    log("boot start");
    verifyRailContract();
    bindRailActions();
    bindSidebarActions();
    bindComposerActions();
    bindDelegatedClicks();

    setRailPanel("artifacts");
    await loadState();

    if (els.topbarModelText) {
      els.topbarModelText.textContent = "gpt-5.4";
    }

    log("boot complete");
  }

  window.NovaComposerBundle = {
    state: state,
    setRailPanel: setRailPanel,
    showRailViewer: showRailViewer,
    backToRailList: backToRailList,
    openArtifactViewer: openArtifactViewer,
    openMemoryViewer: openMemoryViewer,
    openWebViewer: openWebViewer,
    loadState: loadState,
    sendMessage: sendMessage,
    regenerateMessage: regenerateMessage,
    copyMessageById: copyMessageById
  };

  boot().catch(function (error) {
    warn("boot failed:", error);
    setStatus("Boot error");
  });
})();