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

  function truncate(value, length) {
    const text = String(value == null ? "" : value).trim();
    if (!text) return "";
    return text.length > length ? text.slice(0, length - 1) + "…" : text;
  }

  function coerceArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function formatDateTime(value) {
    if (!value) return "";
    try {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return String(value);
      return date.toLocaleString();
    } catch (_) {
      return String(value);
    }
  }

  function normalizeId(value, fallback) {
    const raw = value == null ? "" : String(value).trim();
    return raw || fallback || "";
  }

  function firstNonEmpty() {
    for (let i = 0; i < arguments.length; i += 1) {
      const value = arguments[i];
      if (value != null && String(value).trim() !== "") {
        return String(value);
      }
    }
    return "";
  }

  const RAIL_STORAGE_KEY = "nova.rail.restore.v1";

  const state = {
    sessions: [],
    artifacts: [],
    memory: [],
    web: [],
    activeSessionId: null,
    lastLoadedSessionId: null,
    sidebarOpen: true,
    railOpen: true,
    railTab: "artifacts",
    viewerOpen: false,
    viewerKind: null,
    activeArtifactId: null,
    activeMemoryId: null,
    activeWebId: null,
    selectedItem: null,
    pendingUploads: [],
    isSending: false,
    isOpeningSession: false,
  };

  const els = {
    appShell: qs("[data-app-shell]"),
    sidebar: qs("[data-sidebar]"),
    rail: qs("[data-rail]"),
    sidebarReopen: qs("[data-action='reopen-sidebar']"),
    railReopen: qs("[data-action='reopen-rail']"),

    sessionList: qs("[data-session-list]"),
    chatThread: qs("[data-chat-thread]"),
    emptyState: qs("[data-empty-state]"),
    chatInput: qs("[data-chat-input]"),
    uploadStrip: qs("[data-upload-strip]"),

    topbarTitle: qs("[data-topbar-title]"),
    topbarSubtitle: qs("[data-topbar-subtitle]"),
    topbarStatus: qs("[data-topbar-status]"),

    railTitle: qs("[data-rail-title]"),
    railSubtitle: qs("[data-rail-subtitle]"),

    railTabs: qsa("[data-rail-tab]"),
    artifactPanel: qs("[data-rail-panel='artifacts']"),
    memoryPanel: qs("[data-rail-panel='memory']"),
    webPanel: qs("[data-rail-panel='web']"),

    artifactList: qs("[data-artifact-list]"),
    memoryList: qs("[data-memory-list]"),
    webList: qs("[data-web-list]"),

    artifactEmpty: qs("[data-artifact-empty]"),
    memoryEmpty: qs("[data-memory-empty]"),
    webEmpty: qs("[data-web-empty]"),

    viewer: qs("[data-viewer]"),
    viewerShell: qs("[data-viewer-shell]"),
  };

  const TAB_META = {
    artifacts: {
      title: "Artifacts",
      subtitle: "Saved outputs and side panels",
    },
    memory: {
      title: "Memory",
      subtitle: "Saved notes and preferences",
    },
    web: {
      title: "Web",
      subtitle: "Fetched pages and web results",
    },
  };

  function safeJsonParse(value, fallback) {
    try {
      return JSON.parse(value);
    } catch (_) {
      return fallback;
    }
  }

  function getStoredRailState() {
    try {
      const raw = localStorage.getItem(RAIL_STORAGE_KEY);
      if (!raw) return null;
      return safeJsonParse(raw, null);
    } catch (_) {
      return null;
    }
  }

  function persistRailState() {
    try {
      localStorage.setItem(
        RAIL_STORAGE_KEY,
        JSON.stringify({
          railTab: state.railTab,
          railOpen: !!state.railOpen,
          viewerOpen: !!state.viewerOpen,
          viewerKind: state.viewerKind || null,
          activeArtifactId: state.activeArtifactId || null,
          activeMemoryId: state.activeMemoryId || null,
          activeWebId: state.activeWebId || null,
          activeSessionId: state.activeSessionId || null,
        })
      );
    } catch (_) {}
  }

  function clearPersistedSelection(keepTab, keepRailOpen) {
    state.viewerOpen = false;
    state.viewerKind = null;
    state.activeArtifactId = null;
    state.activeMemoryId = null;
    state.activeWebId = null;
    state.selectedItem = null;

    if (typeof keepTab === "string" && keepTab) {
      state.railTab = keepTab;
    }

    if (typeof keepRailOpen === "boolean") {
      state.railOpen = keepRailOpen;
    }

    persistRailState();
  }

  function hydrateRailStateFromStorage() {
    const saved = getStoredRailState();
    if (!saved || typeof saved !== "object") return;

    if (saved.railTab === "artifacts" || saved.railTab === "memory" || saved.railTab === "web") {
      state.railTab = saved.railTab;
    }

    state.railOpen = saved.railOpen !== false;
    state.viewerOpen = !!saved.viewerOpen;
    state.viewerKind = saved.viewerKind || null;
    state.activeArtifactId = saved.activeArtifactId || null;
    state.activeMemoryId = saved.activeMemoryId || null;
    state.activeWebId = saved.activeWebId || null;
  }

  function setTopbar(title, subtitle, status) {
    if (els.topbarTitle) {
      els.topbarTitle.textContent = title || "Nova";
    }
    if (els.topbarSubtitle) {
      els.topbarSubtitle.textContent = subtitle || "Fast local AI workspace";
    }
    if (els.topbarStatus) {
      els.topbarStatus.textContent = status || "Ready";
    }
  }

  function setRailHeader(title, subtitle) {
    if (els.railTitle) {
      els.railTitle.textContent = title || "";
    }
    if (els.railSubtitle) {
      els.railSubtitle.textContent = subtitle || "";
    }
  }

  function getTabMeta(tabName) {
    return TAB_META[tabName] || TAB_META.artifacts;
  }

  function getActiveSession() {
    return state.sessions.find((session) => session.id === state.activeSessionId) || null;
  }

  function isMobileSidebarOverlayMode() {
    try {
      return window.innerWidth <= 820;
    } catch (_) {
      return false;
    }
  }

  function isMobileRailOverlayMode() {
    try {
      return window.innerWidth <= 1180;
    } catch (_) {
      return false;
    }
  }

  function isAnyOverlayPanelOpen() {
    return (
      (isMobileSidebarOverlayMode() && !!state.sidebarOpen) ||
      (isMobileRailOverlayMode() && !!state.railOpen)
    );
  }

function applyBodyLockState() {
  const overlayOpen = isAnyOverlayPanelOpen();

  // scroll lock
  document.body.style.overflow = overlayOpen ? "hidden" : "";
  document.documentElement.style.overflow = overlayOpen ? "hidden" : "";

  // 🔥 THIS WAS MISSING → THIS FIXES YOUR CSS
  document.body.classList.toggle("is-sidebar-open", !!state.sidebarOpen);
  document.body.classList.toggle("is-rail-open", !!state.railOpen);
  document.body.classList.toggle("is-shell-locked", overlayOpen);

  // existing dataset (keep)
  document.body.dataset.novaOverlayOpen = overlayOpen ? "true" : "false";
  document.body.dataset.novaSidebarOpen = state.sidebarOpen ? "true" : "false";
  document.body.dataset.novaRailOpen = state.railOpen ? "true" : "false";

  if (els.appShell) {
    els.appShell.dataset.sidebarOpen = state.sidebarOpen ? "true" : "false";
    els.appShell.dataset.railOpen = state.railOpen ? "true" : "false";
    els.appShell.dataset.overlayOpen = overlayOpen ? "true" : "false";
  }

  if (els.chatThread) {
    els.chatThread.style.overflow = overlayOpen ? "hidden" : "";
    els.chatThread.style.pointerEvents = overlayOpen ? "none" : "";
    els.chatThread.style.userSelect = overlayOpen ? "none" : "";
  }

  if (els.viewer) {
    els.viewer.style.pointerEvents = "";
  }
}


  function syncSidebarVisibility() {
    if (els.sidebar) {
      els.sidebar.hidden = !state.sidebarOpen;
    }

    if (els.sidebarReopen) {
      els.sidebarReopen.hidden = !!state.sidebarOpen;
    }

    applyBodyLockState();
  }

  function openSidebar() {
    state.sidebarOpen = true;
    syncSidebarVisibility();
  }

  function closeSidebar() {
    state.sidebarOpen = false;
    syncSidebarVisibility();
  }

  function toggleSidebar() {
    if (state.sidebarOpen) {
      closeSidebar();
    } else {
      openSidebar();
    }
  }

  function openRail() {
    state.railOpen = true;

    if (els.rail) {
      els.rail.hidden = false;
      els.rail.classList.add("is-open");
    }

    if (els.railReopen) {
      els.railReopen.hidden = true;
    }

    applyBodyLockState();
    persistRailState();
  }

  function closeRail() {
    state.railOpen = false;

    if (els.rail) {
      els.rail.classList.remove("is-open");
      els.rail.hidden = true;
    }

    if (els.railReopen) {
      els.railReopen.hidden = false;
    }

    applyBodyLockState();
    persistRailState();
  }

  function normalizeSession(raw, index) {
    const messages = coerceArray(raw && raw.messages);
    const title = firstNonEmpty(
      raw && raw.title,
      raw && raw.name,
      raw && raw.label,
      messages[0] && (messages[0].content || messages[0].text),
      "New Chat"
    );

    return {
      id: normalizeId(raw && raw.id, "session-" + index),
      title: truncate(title, 80) || "New Chat",
      updated_at: firstNonEmpty(raw && raw.updated_at, raw && raw.created_at, ""),
      message_count:
        raw && Number.isFinite(raw.message_count) ? raw.message_count : messages.length,
      last_message_preview: firstNonEmpty(
        raw && raw.last_message_preview,
        messages.length ? (messages[messages.length - 1].content || messages[messages.length - 1].text || "") : "",
        ""
      ),
      pinned: !!(raw && (raw.pinned || raw.is_pinned)),
      messages: messages.map(normalizeMessage),
    };
  }

  function normalizeMessage(raw, index) {
    return {
      id: normalizeId(raw && raw.id, "message-" + index),
      role: firstNonEmpty(raw && raw.role, raw && raw.sender, "assistant").toLowerCase(),
      content: firstNonEmpty(raw && raw.content, raw && raw.text, raw && raw.body, ""),
      image_url: firstNonEmpty(raw && raw.image_url, raw && raw.imageUrl, ""),
      attachments: coerceArray(raw && raw.attachments),
      created_at: firstNonEmpty(raw && raw.created_at, raw && raw.timestamp, ""),
      is_error: !!(raw && (raw.is_error || raw.error)),
    };
  }

  function normalizeArtifact(raw, index) {
    const id = normalizeId(raw && raw.id, "artifact-" + index);
    const viewer = raw && raw.viewer ? raw.viewer : {};
    const kind = firstNonEmpty(
      viewer && viewer.kind,
      raw && raw.kind,
      raw && raw.type,
      "artifact"
    );
    const title = firstNonEmpty(
      viewer && viewer.title,
      raw && raw.title,
      kind,
      "Artifact"
    );
    const body = firstNonEmpty(
      viewer && viewer.body,
      raw && raw.body,
      raw && raw.preview,
      raw && raw.content,
      raw && raw.summary,
      ""
    );
    const preview = firstNonEmpty(raw && raw.preview, body, raw && raw.summary, "");

    return {
      id,
      session_id: firstNonEmpty(raw && raw.session_id, raw && raw.sessionId, ""),
      kind,
      title,
      preview: truncate(preview, 160),
      body,
      created_at: firstNonEmpty(raw && raw.created_at, raw && raw.updated_at, ""),
      updated_at: firstNonEmpty(raw && raw.updated_at, raw && raw.created_at, ""),
      image_url: firstNonEmpty(
        viewer && viewer.image_url,
        raw && raw.image_url,
        raw && raw.imageUrl,
        ""
      ),
      video_url: firstNonEmpty(
        viewer && viewer.video_url,
        raw && raw.video_url,
        raw && raw.videoUrl,
        ""
      ),
      audio_url: firstNonEmpty(
        viewer && viewer.audio_url,
        raw && raw.audio_url,
        raw && raw.audioUrl,
        ""
      ),
      source_url: firstNonEmpty(
        viewer && viewer.source_url,
        raw && raw.source_url,
        raw && raw.url,
        ""
      ),
      analysis_text: firstNonEmpty(
        viewer && viewer.analysis_text,
        raw && raw.analysis_text,
        raw && raw.analysis,
        ""
      ),
      bullets: coerceArray((viewer && viewer.bullets) || (raw && raw.bullets) || []).filter(Boolean),
      meta: raw && raw.meta ? raw.meta : {},
    };
  }

  function normalizeMemory(raw, index) {
    const id = normalizeId(raw && raw.id, "memory-" + index);
    const text = firstNonEmpty(raw && raw.text, raw && raw.body, raw && raw.content, "");
    return {
      id,
      title: truncate(firstNonEmpty(raw && raw.kind, raw && raw.title, "Memory"), 40),
      kind: firstNonEmpty(raw && raw.kind, "memory"),
      text,
      preview: truncate(text, 140),
      created_at: firstNonEmpty(raw && raw.created_at, raw && raw.updated_at, ""),
      updated_at: firstNonEmpty(raw && raw.updated_at, raw && raw.created_at, ""),
      source: firstNonEmpty(raw && raw.source, ""),
      session_id: firstNonEmpty(raw && raw.session_id, ""),
    };
  }

  function normalizeWeb(raw, index) {
    const id = normalizeId(raw && raw.id, "web-" + index);
    return {
      id,
      title: firstNonEmpty(raw && raw.title, raw && raw.site_name, raw && raw.url, "Web Result"),
      subtitle: firstNonEmpty(raw && raw.site_name, raw && raw.domain, ""),
      preview: truncate(
        firstNonEmpty(raw && raw.summary, raw && raw.preview, raw && raw.description, ""),
        160
      ),
      body: firstNonEmpty(raw && raw.content, raw && raw.summary, raw && raw.description, ""),
      url: firstNonEmpty(raw && raw.url, raw && raw.source_url, ""),
      created_at: firstNonEmpty(raw && raw.fetched_at, raw && raw.created_at, ""),
      status_code: firstNonEmpty(raw && raw.status_code, ""),
    };
  }

  async function api(path, options) {
    const response = await fetch(path, {
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
      },
      ...options,
    });

    const text = await response.text();
    let data = null;

    try {
      data = text ? JSON.parse(text) : {};
    } catch (_) {
      data = { raw: text };
    }

    if (!response.ok) {
      const message = firstNonEmpty(
        data && data.error,
        data && data.message,
        response.statusText,
        "Request failed"
      );
      throw new Error(message);
    }

    return data || {};
  }

  async function postJson(path, body) {
    const data = await api(path, {
      method: "POST",
      body: JSON.stringify(body || {}),
    });

    if (!data || data.ok === false) {
      throw new Error((data && data.error) || "Request failed");
    }

    return data;
  }

  function getSelectedItemFromState() {
    if (state.activeArtifactId) {
      const artifact = state.artifacts.find((x) => x.id === state.activeArtifactId);
      if (artifact) return { type: "artifact", item: artifact };
    }

    if (state.activeMemoryId) {
      const memory = state.memory.find((x) => x.id === state.activeMemoryId);
      if (memory) return { type: "memory", item: memory };
    }

    if (state.activeWebId) {
      const webItem = state.web.find((x) => x.id === state.activeWebId);
      if (webItem) return { type: "web", item: webItem };
    }

    return null;
  }

  function getSelectedIdForTab(tabName) {
    if (tabName === "artifacts") return state.activeArtifactId;
    if (tabName === "memory") return state.activeMemoryId;
    if (tabName === "web") return state.activeWebId;
    return null;
  }

  function getSelectedTypeForTab(tabName) {
    if (tabName === "artifacts") return "artifact";
    if (tabName === "memory") return "memory";
    if (tabName === "web") return "web";
    return null;
  }

  function clearActiveIdsExcept(typeToKeep) {
    if (typeToKeep !== "artifact") state.activeArtifactId = null;
    if (typeToKeep !== "memory") state.activeMemoryId = null;
    if (typeToKeep !== "web") state.activeWebId = null;
  }

  function clearViewerState() {
    state.viewerOpen = false;
    state.viewerKind = null;
    state.activeArtifactId = null;
    state.activeMemoryId = null;
    state.activeWebId = null;
    state.selectedItem = null;
  }

  function syncSelectedItem() {
    const selected = getSelectedItemFromState();

    if (!selected) {
      state.viewerOpen = false;
      state.viewerKind = null;
      state.selectedItem = null;
      return null;
    }

    state.viewerOpen = true;
    state.viewerKind = selected.type;
    state.selectedItem = selected;
    return selected;
  }

  function syncRailHeader() {
    const selectedId = getSelectedIdForTab(state.railTab);
    const selectedType = getSelectedTypeForTab(state.railTab);

    if (state.viewerOpen && selectedId && selectedType) {
      const selected = syncSelectedItem();
      if (selected && selected.type === selectedType && selected.item) {
        const item = selected.item;

        if (selected.type === "artifact") {
          setRailHeader(
            firstNonEmpty(item.title, "Artifact"),
            firstNonEmpty(item.kind, "artifact")
          );
          return;
        }

        if (selected.type === "memory") {
          setRailHeader(
            firstNonEmpty(item.title, "Memory"),
            firstNonEmpty(item.kind, "memory")
          );
          return;
        }

        if (selected.type === "web") {
          setRailHeader(
            firstNonEmpty(item.title, "Web Result"),
            firstNonEmpty(
              item.subtitle,
              item.status_code ? "HTTP " + item.status_code : "",
              "web"
            )
          );
          return;
        }
      }
    }

    const meta = getTabMeta(state.railTab);
    setRailHeader(meta.title, meta.subtitle);
  }

  function validateRailSelectionAgainstCurrentData() {
    if (state.activeArtifactId && !state.artifacts.some((x) => x.id === state.activeArtifactId)) {
      state.activeArtifactId = null;
    }

    if (state.activeMemoryId && !state.memory.some((x) => x.id === state.activeMemoryId)) {
      state.activeMemoryId = null;
    }

    if (state.activeWebId && !state.web.some((x) => x.id === state.activeWebId)) {
      state.activeWebId = null;
    }

    const selectedId = getSelectedIdForTab(state.railTab);

    if (!selectedId) {
      state.viewerOpen = false;
      state.viewerKind = null;
      state.selectedItem = null;
      clearActiveIdsExcept(null);
      return;
    }

    const selected = getSelectedItemFromState();
    if (!selected) {
      clearViewerState();
      return;
    }

    clearActiveIdsExcept(selected.type);
    state.viewerOpen = true;
    state.viewerKind = selected.type;
    state.selectedItem = selected;
  }

  function handleSessionContextShift(previousSessionId, nextSessionId) {
    const prev = previousSessionId ? String(previousSessionId) : "";
    const next = nextSessionId ? String(nextSessionId) : "";

    if (!prev) return;
    if (!next) return;
    if (prev === next) return;

    clearPersistedSelection(state.railTab, state.railOpen);
  }

  function applyPersistedRailAfterStateLoad(previousSessionId, nextSessionId) {
    handleSessionContextShift(previousSessionId, nextSessionId);
    validateRailSelectionAgainstCurrentData();
    persistRailState();
  }

  function setRailTab(tabName, options) {
    const opts = options || {};
    const nextTab = ["artifacts", "memory", "web"].includes(tabName) ? tabName : "artifacts";

    state.railTab = nextTab;

    if (!opts.preserveSelection) {
      clearViewerState();
    } else {
      const selectedId = getSelectedIdForTab(nextTab);
      if (!selectedId) {
        state.viewerOpen = false;
        state.viewerKind = null;
        state.selectedItem = null;
      } else {
        syncSelectedItem();
      }
    }

    openRail();
    syncRailHeader();
    renderRail();
    persistRailState();
  }

  function openViewer(type, item) {
    if (!item) return;

    if (type === "artifact") {
      state.railTab = "artifacts";
      state.activeArtifactId = item.id;
      clearActiveIdsExcept("artifact");
    } else if (type === "memory") {
      state.railTab = "memory";
      state.activeMemoryId = item.id;
      clearActiveIdsExcept("memory");
    } else if (type === "web") {
      state.railTab = "web";
      state.activeWebId = item.id;
      clearActiveIdsExcept("web");
    } else {
      return;
    }

    state.viewerOpen = true;
    state.viewerKind = type;
    state.selectedItem = { type, item };

    openRail();
    syncRailHeader();
    renderRail();
    persistRailState();
  }

  // =========================================================
  // ONE TRUE SESSION OPEN / NEW CONTRACT
  // =========================================================

  async function openSessionOnBackend(sessionId) {
    const id = String(sessionId || "").trim();
    if (!id) {
      throw new Error("Missing session id");
    }

    const data = await api("/api/sessions/open", {
      method: "POST",
      body: JSON.stringify({ session_id: id }),
    });

    if (!data || !data.ok) {
      throw new Error((data && data.error) || "Session open failed");
    }

    if (!data.session || !data.active_session_id) {
      throw new Error("Invalid session open payload");
    }

    return data;
  }

  async function createNewChatOnBackend() {
    const data = await api("/api/sessions/new", {
      method: "POST",
      body: JSON.stringify({}),
    });

    if (!data || !data.ok) {
      throw new Error((data && data.error) || "New chat create failed");
    }

    const session =
      data.session ||
      coerceArray(data.sessions).find((item) => item && item.id === data.active_session_id) ||
      null;

    const activeSessionId = firstNonEmpty(
      data.active_session_id,
      session && session.id,
      ""
    );

    if (!session || !activeSessionId) {
      throw new Error("Invalid new chat payload");
    }

    return {
      ok: true,
      session,
      active_session_id: activeSessionId,
    };
  }

  async function renameSessionOnBackend(sessionId, title) {
    const id = String(sessionId || "").trim();
    const nextTitle = String(title || "").trim();

    if (!id) {
      throw new Error("Missing session id");
    }

    if (!nextTitle) {
      throw new Error("Title is required");
    }

    const data = await postJson("/api/sessions/rename", {
      session_id: id,
      title: nextTitle,
    });

    if (!data.session || !data.active_session_id) {
      throw new Error("Invalid rename payload");
    }

    return data;
  }

  async function deleteSessionOnBackend(sessionId) {
    const id = String(sessionId || "").trim();

    if (!id) {
      throw new Error("Missing session id");
    }

    const data = await postJson("/api/sessions/delete", {
      session_id: id,
    });

    if (!data.session || !data.active_session_id) {
      throw new Error("Invalid delete payload");
    }

    return data;
  }

  function upsertSession(normalizedSession) {
    let found = false;

    state.sessions = state.sessions.map((session) => {
      if (session.id === normalizedSession.id) {
        found = true;
        return normalizedSession;
      }
      return session;
    });

    if (!found) {
      state.sessions.unshift(normalizedSession);
    }
  }

  function removeSessionById(sessionId) {
    const id = String(sessionId || "").trim();
    if (!id) return;

    state.sessions = state.sessions.filter((session) => session.id !== id);
  }

  async function reloadStateFromBackend() {
    const previousSessionId = state.lastLoadedSessionId || state.activeSessionId || null;
    const data = await api("/api/state", { method: "GET" });

    state.sessions = coerceArray(data.sessions).map(normalizeSession);
    state.artifacts = coerceArray(data.artifacts).map(normalizeArtifact);
    state.memory = coerceArray(data.memory).map(normalizeMemory);
    state.web = coerceArray(data.web || data.web_results || []).map(normalizeWeb);

    const activeSessionId = firstNonEmpty(
      data.active_session_id,
      data.active_session && data.active_session.id,
      data.session && data.session.id,
      state.sessions[0] && state.sessions[0].id,
      ""
    );

    state.activeSessionId = activeSessionId || null;
    state.lastLoadedSessionId = state.activeSessionId || null;

    if (!["artifacts", "memory", "web"].includes(state.railTab)) {
      state.railTab = "artifacts";
    }

    applyPersistedRailAfterStateLoad(previousSessionId, state.activeSessionId);
    renderAll();

    return data;
  }

  async function switchToSession(sessionId) {
    const nextId = String(sessionId || "").trim();
    if (!nextId || state.isOpeningSession) return;

    if (String(state.activeSessionId || "") === nextId) {
      if (isMobileSidebarOverlayMode()) {
        closeSidebar();
      }
      return;
    }

    const previousSessionId = state.activeSessionId || null;

    state.isOpeningSession = true;
    state.lastLoadedSessionId = previousSessionId;

    setTopbar(
      (getActiveSession() && getActiveSession().title) || "Nova",
      "Restoring session...",
      "Working"
    );

    clearPersistedSelection(state.railTab, state.railOpen);
    renderRail();
    renderSessions();

    try {
      const payload = await openSessionOnBackend(nextId);
      const normalized = normalizeSession(payload.session, 0);

      state.activeSessionId = String(payload.active_session_id || normalized.id || nextId);
      state.lastLoadedSessionId = state.activeSessionId;

      upsertSession(normalized);

      clearViewerState();

      if (isMobileSidebarOverlayMode()) {
        closeSidebar();
      }

      renderAll();
    } catch (error) {
      state.activeSessionId = previousSessionId;
      warn("switchToSession failed", error);
      setTopbar("Nova", "Session restore failed", "Error");
      alert("Session open failed: " + error.message);
      renderAll();
    } finally {
      state.isOpeningSession = false;
      renderSessions();
      renderChat();
    }
  }

  async function createNewChat() {
    if (state.isOpeningSession || state.isSending) return;

    const previousSessionId = state.activeSessionId || null;

    state.isOpeningSession = true;
    state.lastLoadedSessionId = previousSessionId;

    setTopbar("Nova", "Creating new chat...", "Working");

    clearPersistedSelection(state.railTab, state.railOpen);
    renderRail();
    renderSessions();

    try {
      const payload = await createNewChatOnBackend();
      const normalized = normalizeSession(payload.session, 0);

      state.activeSessionId = String(payload.active_session_id || normalized.id || "");
      state.lastLoadedSessionId = state.activeSessionId;

      upsertSession(normalized);
      clearViewerState();

      if (isMobileSidebarOverlayMode()) {
        closeSidebar();
      }

      renderAll();

      if (els.chatInput) {
        els.chatInput.focus();
      }
    } catch (error) {
      state.activeSessionId = previousSessionId;
      warn("createNewChat failed", error);
      setTopbar("Nova", "New chat failed", "Error");
      alert("New chat failed: " + error.message);
      renderAll();
    } finally {
      state.isOpeningSession = false;
      renderSessions();
      renderChat();
    }
  }

  async function renameSession(sessionId) {
    const id = String(sessionId || "").trim();
    if (!id || state.isOpeningSession || state.isSending) return;

    const target =
      state.sessions.find((session) => session.id === id) ||
      (state.activeSessionId === id ? getActiveSession() : null);

    const currentTitle = firstNonEmpty(target && target.title, "Untitled chat");
    const nextTitleRaw = window.prompt("Rename session", currentTitle);

    if (nextTitleRaw == null) {
      return;
    }

    const nextTitle = String(nextTitleRaw || "").trim();
    if (!nextTitle) {
      return;
    }

    state.isOpeningSession = true;
    setTopbar(currentTitle, "Renaming session...", "Working");

    try {
      const payload = await renameSessionOnBackend(id, nextTitle);
      const normalized = normalizeSession(payload.session, 0);

      state.activeSessionId = String(payload.active_session_id || normalized.id || id);
      state.lastLoadedSessionId = state.activeSessionId;

      upsertSession(normalized);

      if (state.activeSessionId === normalized.id) {
        clearViewerState();
      }

      renderAll();
      await reloadStateFromBackend();
    } catch (error) {
      warn("renameSession failed", error);
      setTopbar("Nova", "Rename failed", "Error");
      alert("Rename failed: " + error.message);
      renderAll();
    } finally {
      state.isOpeningSession = false;
      renderSessions();
      renderChat();
    }
  }

  async function deleteSession(sessionId) {
    const id = String(sessionId || "").trim();
    if (!id || state.isOpeningSession || state.isSending) return;

    const target =
      state.sessions.find((session) => session.id === id) ||
      (state.activeSessionId === id ? getActiveSession() : null);

    const label = firstNonEmpty(target && target.title, "this chat");
    const confirmed = window.confirm('Delete "' + label + '"?');

    if (!confirmed) {
      return;
    }

    state.isOpeningSession = true;
    setTopbar(label, "Deleting session...", "Working");

    try {
      const payload = await deleteSessionOnBackend(id);
      const deletedSessionId = firstNonEmpty(payload.deleted_session_id, id);
      const normalized = normalizeSession(payload.session, 0);

      removeSessionById(deletedSessionId);

      state.activeSessionId = String(payload.active_session_id || normalized.id || "");
      state.lastLoadedSessionId = state.activeSessionId;

      upsertSession(normalized);
      clearViewerState();

      if (isMobileSidebarOverlayMode()) {
        closeSidebar();
      }

      renderAll();
      await reloadStateFromBackend();
    } catch (error) {
      warn("deleteSession failed", error);
      setTopbar("Nova", "Delete failed", "Error");
      alert("Delete failed: " + error.message);
      renderAll();
    } finally {
      state.isOpeningSession = false;
      renderSessions();
      renderChat();
    }
  }

  async function loadState() {
    log("loadState start");

    try {
      await reloadStateFromBackend();
      log("loadState complete");
    } catch (error) {
      warn("loadState failed", error);
      setTopbar("Nova", "State load failed", "Error");
    }
  }

  function renderSessions() {
    if (!els.sessionList) return;

    els.sessionList.innerHTML = "";

    state.sessions.forEach((session) => {
      const card = document.createElement("div");
      card.className =
        "nova-session-card" + (session.id === state.activeSessionId ? " is-active" : "");
      card.dataset.sessionId = session.id;

      const openButton = document.createElement("button");
      openButton.type = "button";
      openButton.className = "nova-session-card-main";
      openButton.dataset.action = "open-session";
      openButton.dataset.sessionId = session.id;

      if (state.isOpeningSession) {
        openButton.disabled = true;
      }

      openButton.innerHTML = [
        '<div class="nova-session-card-top">',
        `<div class="nova-session-card-title">${escapeHtml(session.title)}</div>`,
        session.pinned ? '<div class="nova-session-card-pin">📌</div>' : "",
        "</div>",
        session.last_message_preview
          ? `<div class="nova-session-card-preview">${escapeHtml(truncate(session.last_message_preview, 100))}</div>`
          : "",
        `<div class="nova-session-card-meta">${escapeHtml(
          [session.message_count + " msgs", formatDateTime(session.updated_at)].filter(Boolean).join(" · ")
        )}</div>`,
      ].join("");

      const actions = document.createElement("div");
      actions.className = "nova-session-card-actions";
      actions.innerHTML = [
        `<button type="button" class="nova-session-card-action" data-action="rename-session" data-session-id="${escapeHtml(session.id)}" title="Rename">✎</button>`,
        `<button type="button" class="nova-session-card-action" data-action="delete-session" data-session-id="${escapeHtml(session.id)}" title="Delete">×</button>`,
      ].join("");

      card.appendChild(openButton);
      card.appendChild(actions);
      els.sessionList.appendChild(card);
    });
  }

  function renderChat() {
    if (!els.chatThread) return;

    const activeSession = getActiveSession();
    const messages = activeSession ? coerceArray(activeSession.messages) : [];

    setTopbar(
      activeSession ? activeSession.title : "Nova",
      activeSession
        ? [messages.length + " messages", formatDateTime(activeSession.updated_at)].filter(Boolean).join(" · ")
        : "Fast local AI workspace",
      state.isSending || state.isOpeningSession ? "Working" : "Ready"
    );

    els.chatThread.innerHTML = "";

    if (!messages.length) {
      if (els.emptyState) {
        els.chatThread.appendChild(els.emptyState);
        els.emptyState.hidden = false;
      } else {
        const empty = document.createElement("div");
        empty.className = "nova-empty-state";
        empty.innerHTML =
          '<div class="nova-empty-state-title">Nova is live</div>' +
          '<div class="nova-empty-state-copy">Chat is working. Uploads stage before send. Artifacts rail stays available.</div>';
        els.chatThread.appendChild(empty);
      }
      return;
    }

    messages.forEach((message) => {
      const wrapper = document.createElement("div");
      wrapper.className =
        "nova-message " +
        (message.role === "user" ? "nova-message-user" : "nova-message-assistant");

      const bubble = document.createElement("div");
      bubble.className = "nova-message-bubble";

      const content = document.createElement("div");
      content.className = "nova-message-content";
      content.innerHTML = renderSafeText(message.content || "");
      bubble.appendChild(content);

      if (message.image_url) {
        const imageWrap = document.createElement("div");
        imageWrap.className = "nova-message-image-wrap";
        imageWrap.innerHTML =
          '<img class="nova-message-image" alt="Generated image" src="' +
          escapeHtml(message.image_url) +
          '">';
        bubble.appendChild(imageWrap);
      }

      const attachments = coerceArray(message.attachments);
      if (attachments.length) {
        const attachmentWrap = document.createElement("div");
        attachmentWrap.className = "nova-message-attachments";
        attachmentWrap.innerHTML = attachments
          .map((attachment) => {
            const label = firstNonEmpty(
              attachment && attachment.filename,
              attachment && attachment.name,
              attachment && attachment.url,
              "Attachment"
            );
            return '<div class="nova-message-attachment">' + escapeHtml(label) + "</div>";
          })
          .join("");
        bubble.appendChild(attachmentWrap);
      }

      wrapper.appendChild(bubble);
      els.chatThread.appendChild(wrapper);
    });

    els.chatThread.scrollTop = els.chatThread.scrollHeight;
  }

  function renderArtifactList() {
    if (!els.artifactList) return;

    els.artifactList.innerHTML = "";

    state.artifacts.forEach((artifact) => {
      const button = document.createElement("button");
      button.type = "button";

      const isActive = state.railTab === "artifacts" && state.activeArtifactId === artifact.id;

      button.className = "nova-rail-card" + (isActive ? " is-active" : "");
      button.dataset.artifactItem = "true";
      button.dataset.artifactId = artifact.id;

      if (isActive) {
        button.setAttribute("aria-current", "true");
      } else {
        button.removeAttribute("aria-current");
      }

      button.innerHTML = [
        artifact.kind
          ? `<div class="nova-rail-card-kicker">${escapeHtml(String(artifact.kind).replace(/_/g, " "))}</div>`
          : "",
        `<div class="nova-rail-card-title">${escapeHtml(truncate(artifact.title, 90))}</div>`,
        artifact.preview
          ? `<div class="nova-rail-card-preview">${escapeHtml(artifact.preview)}</div>`
          : "",
        `<div class="nova-rail-card-meta">${escapeHtml(
          [formatDateTime(artifact.updated_at || artifact.created_at), artifact.session_id ? "session linked" : ""]
            .filter(Boolean)
            .join(" · ")
        )}</div>`,
      ].join("");

      button.addEventListener("click", function () {
        openViewer("artifact", artifact);
      });

      els.artifactList.appendChild(button);
    });

    if (els.artifactEmpty) {
      els.artifactEmpty.hidden = state.artifacts.length > 0;
    }
  }

  function renderMemoryList() {
    if (!els.memoryList) return;

    els.memoryList.innerHTML = "";

    state.memory.forEach((memory) => {
      const button = document.createElement("button");
      button.type = "button";

      const isActive = state.railTab === "memory" && state.activeMemoryId === memory.id;

      button.className = "nova-rail-card" + (isActive ? " is-active" : "");
      button.dataset.memoryId = memory.id;

      if (isActive) {
        button.setAttribute("aria-current", "true");
      } else {
        button.removeAttribute("aria-current");
      }

      button.innerHTML = [
        `<div class="nova-rail-card-kicker">${escapeHtml(memory.kind || "memory")}</div>`,
        `<div class="nova-rail-card-title">${escapeHtml(memory.title || "Memory")}</div>`,
        memory.preview
          ? `<div class="nova-rail-card-preview">${escapeHtml(memory.preview)}</div>`
          : "",
        `<div class="nova-rail-card-meta">${escapeHtml(
          [memory.source, formatDateTime(memory.updated_at || memory.created_at)].filter(Boolean).join(" · ")
        )}</div>`,
      ].join("");

      button.addEventListener("click", function () {
        openViewer("memory", memory);
      });

      els.memoryList.appendChild(button);
    });

    if (els.memoryEmpty) {
      els.memoryEmpty.hidden = state.memory.length > 0;
    }
  }

  function renderWebList() {
    if (!els.webList) return;

    els.webList.innerHTML = "";

    state.web.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";

      const isActive = state.railTab === "web" && state.activeWebId === item.id;

      button.className = "nova-rail-card" + (isActive ? " is-active" : "");
      button.dataset.webId = item.id;

      if (isActive) {
        button.setAttribute("aria-current", "true");
      } else {
        button.removeAttribute("aria-current");
      }

      button.innerHTML = [
        item.subtitle ? `<div class="nova-rail-card-kicker">${escapeHtml(item.subtitle)}</div>` : "",
        `<div class="nova-rail-card-title">${escapeHtml(truncate(item.title, 90))}</div>`,
        item.preview
          ? `<div class="nova-rail-card-preview">${escapeHtml(item.preview)}</div>`
          : "",
        `<div class="nova-rail-card-meta">${escapeHtml(
          [item.status_code ? "HTTP " + item.status_code : "", formatDateTime(item.created_at)]
            .filter(Boolean)
            .join(" · ")
        )}</div>`,
      ].join("");

      button.addEventListener("click", function () {
        openViewer("web", item);
      });

      els.webList.appendChild(button);
    });

    if (els.webEmpty) {
      els.webEmpty.hidden = state.web.length > 0;
    }
  }

  function renderViewer() {
    if (!els.viewer || !els.viewerShell) return;

    const selected = state.selectedItem || getSelectedItemFromState();

    if (!state.viewerOpen || !selected || !selected.item) {
      els.viewer.hidden = true;
      els.viewerShell.innerHTML =
        '<div class="nova-viewer-empty" data-viewer-empty>' +
        '<div class="nova-viewer-empty-title">Nothing selected</div>' +
        '<div class="nova-viewer-empty-copy">Select an artifact, memory item, or web result to view details.</div>' +
        "</div>";
      return;
    }

    els.viewer.hidden = false;

    if (selected.type === "artifact") {
      els.viewerShell.innerHTML = renderArtifactViewer(selected.item);
    } else if (selected.type === "memory") {
      els.viewerShell.innerHTML = renderMemoryViewer(selected.item);
    } else if (selected.type === "web") {
      els.viewerShell.innerHTML = renderWebViewer(selected.item);
    } else {
      els.viewerShell.innerHTML =
        '<div class="nova-viewer-empty"><div class="nova-viewer-empty-title">Nothing selected</div></div>';
    }
  }

  function renderArtifactViewer(item) {
    const metaChips = [
      item.kind ? `<span class="nova-viewer-meta-chip">${escapeHtml(item.kind)}</span>` : "",
      item.created_at
        ? `<span class="nova-viewer-meta-chip">${escapeHtml(formatDateTime(item.created_at))}</span>`
        : "",
      item.session_id
        ? `<span class="nova-viewer-meta-chip">${escapeHtml("session linked")}</span>`
        : "",
    ]
      .filter(Boolean)
      .join("");

    const media = item.image_url
      ? `<div class="nova-viewer-media"><img class="nova-viewer-image" src="${escapeHtml(item.image_url)}" alt="Artifact image"></div>`
      : item.video_url
      ? `<div class="nova-viewer-media"><video class="nova-viewer-video" controls src="${escapeHtml(item.video_url)}"></video></div>`
      : item.audio_url
      ? `<div class="nova-viewer-media"><audio class="nova-viewer-audio" controls src="${escapeHtml(item.audio_url)}"></audio></div>`
      : "";

    const actions = item.source_url
      ? `<div class="nova-viewer-actions"><a class="nova-viewer-link" href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener noreferrer">Open source</a></div>`
      : "";

    const body = item.body
      ? `<div class="nova-viewer-body">${renderSafeText(item.body)}</div>`
      : "";

    const analysis = item.analysis_text
      ? '<div class="nova-viewer-analysis">' +
        '<div class="nova-viewer-section-title">Analysis</div>' +
        `<div class="nova-viewer-analysis-text">${renderSafeText(item.analysis_text)}</div>` +
        "</div>"
      : "";

    const bullets = item.bullets && item.bullets.length
      ? '<div class="nova-viewer-bullets">' +
        '<div class="nova-viewer-section-title">Highlights</div>' +
        '<ul class="nova-viewer-bullets-list">' +
        item.bullets.map((bullet) => `<li>${escapeHtml(bullet)}</li>`).join("") +
        "</ul>" +
        "</div>"
      : "";

    return (
      '<div class="nova-viewer-header">' +
      '<div class="nova-viewer-kicker">Artifact</div>' +
      `<div class="nova-viewer-title">${escapeHtml(item.title || "Artifact")}</div>` +
      `<div class="nova-viewer-meta">${metaChips}</div>` +
      "</div>" +
      media +
      actions +
      body +
      analysis +
      bullets
    );
  }

  function renderMemoryViewer(item) {
    const metaChips = [
      item.kind ? `<span class="nova-viewer-meta-chip">${escapeHtml(item.kind)}</span>` : "",
      item.source ? `<span class="nova-viewer-meta-chip">${escapeHtml(item.source)}</span>` : "",
      item.updated_at
        ? `<span class="nova-viewer-meta-chip">${escapeHtml(formatDateTime(item.updated_at))}</span>`
        : "",
    ]
      .filter(Boolean)
      .join("");

    return (
      '<div class="nova-viewer-header">' +
      '<div class="nova-viewer-kicker">Memory</div>' +
      `<div class="nova-viewer-title">${escapeHtml(item.title || "Memory")}</div>` +
      `<div class="nova-viewer-meta">${metaChips}</div>` +
      "</div>" +
      `<div class="nova-viewer-body">${renderSafeText(item.text || "")}</div>`
    );
  }

  function renderWebViewer(item) {
    const metaChips = [
      item.subtitle ? `<span class="nova-viewer-meta-chip">${escapeHtml(item.subtitle)}</span>` : "",
      item.status_code ? `<span class="nova-viewer-meta-chip">HTTP ${escapeHtml(item.status_code)}</span>` : "",
      item.created_at
        ? `<span class="nova-viewer-meta-chip">${escapeHtml(formatDateTime(item.created_at))}</span>`
        : "",
    ]
      .filter(Boolean)
      .join("");

    const actions = item.url
      ? `<div class="nova-viewer-actions"><a class="nova-viewer-link" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">Open page</a></div>`
      : "";

    return (
      '<div class="nova-viewer-header">' +
      '<div class="nova-viewer-kicker">Web</div>' +
      `<div class="nova-viewer-title">${escapeHtml(item.title || "Web Result")}</div>` +
      `<div class="nova-viewer-meta">${metaChips}</div>` +
      "</div>" +
      actions +
      `<div class="nova-viewer-body">${renderSafeText(item.body || item.preview || "")}</div>`
    );
  }

  function renderRail() {
    if (!els.rail) return;

    if (state.railOpen) {
      els.rail.hidden = false;
      els.rail.classList.add("is-open");
      if (els.railReopen) els.railReopen.hidden = true;
    } else {
      els.rail.hidden = true;
      els.rail.classList.remove("is-open");
      if (els.railReopen) els.railReopen.hidden = false;
      applyBodyLockState();
      return;
    }

    syncRailHeader();

    els.railTabs.forEach((tabButton) => {
      const tabName = tabButton.getAttribute("data-rail-tab");
      const isActive = tabName === state.railTab;
      tabButton.classList.toggle("is-active", isActive);
      tabButton.setAttribute("aria-pressed", isActive ? "true" : "false");
      tabButton.setAttribute("aria-selected", isActive ? "true" : "false");
    });

    if (els.artifactPanel) {
      const active = state.railTab === "artifacts";
      els.artifactPanel.hidden = !active;
      els.artifactPanel.classList.toggle("is-active", active);
    }

    if (els.memoryPanel) {
      const active = state.railTab === "memory";
      els.memoryPanel.hidden = !active;
      els.memoryPanel.classList.toggle("is-active", active);
    }

    if (els.webPanel) {
      const active = state.railTab === "web";
      els.webPanel.hidden = !active;
      els.webPanel.classList.toggle("is-active", active);
    }

    renderArtifactList();
    renderMemoryList();
    renderWebList();
    renderViewer();
    applyBodyLockState();
  }

  function renderAll() {
    renderSessions();
    renderChat();
    renderRail();
    syncSidebarVisibility();
  }

  async function sendMessage() {
    if (!els.chatInput || state.isSending || state.isOpeningSession) return;

    const text = String(els.chatInput.value || "").trim();
    if (!text) return;

    state.isSending = true;

    setTopbar(
      (getActiveSession() && getActiveSession().title) || "Nova",
      "Working...",
      "Working"
    );

    try {
      await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          session_id: state.activeSessionId,
          user_text: text,
        }),
      });

      els.chatInput.value = "";
      await loadState();
    } catch (error) {
      warn("sendMessage failed", error);
      alert("Send failed: " + error.message);
    } finally {
      state.isSending = false;
      renderChat();
    }
  }

  function bindActions() {
    document.addEventListener("click", function (event) {
      const button = event.target.closest("[data-action]");
      if (!button) return;

      const action = button.getAttribute("data-action");
      const sessionId =
        button.getAttribute("data-session-id") ||
        button.closest("[data-session-id]")?.getAttribute("data-session-id") ||
        "";

      if (action === "toggle-rail") {
        if (state.railOpen) {
          closeRail();
        } else {
          openRail();
          renderRail();
        }
        return;
      }

      if (action === "close-rail") {
        closeRail();
        return;
      }

      if (action === "reopen-rail") {
        openRail();
        renderRail();
        return;
      }

      if (action === "toggle-sidebar") {
        toggleSidebar();
        return;
      }

      if (action === "reopen-sidebar") {
        openSidebar();
        return;
      }

      if (action === "new-chat") {
        createNewChat();
        return;
      }

      if (action === "open-session") {
        event.preventDefault();
        event.stopPropagation();
        switchToSession(sessionId);
        return;
      }

      if (action === "rename-session") {
        event.preventDefault();
        event.stopPropagation();
        renameSession(sessionId);
        return;
      }

      if (action === "delete-session") {
        event.preventDefault();
        event.stopPropagation();
        deleteSession(sessionId);
        return;
      }

      if (action === "send") {
        sendMessage();
        return;
      }

      if (action === "attach" || action === "voice") {
        alert(action === "attach" ? "Attach wiring comes next." : "Voice wiring comes next.");
      }
    });

    els.railTabs.forEach((tabButton) => {
      tabButton.addEventListener("click", function () {
        const tabName = tabButton.getAttribute("data-rail-tab");
        setRailTab(tabName, { preserveSelection: false });
      });
    });

    if (els.chatInput) {
      els.chatInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage();
        }
      });
    }

    window.addEventListener("resize", function () {
      applyBodyLockState();
      syncSidebarVisibility();

      if (els.rail) {
        if (state.railOpen) {
          els.rail.hidden = false;
          els.rail.classList.add("is-open");
        } else {
          els.rail.hidden = true;
          els.rail.classList.remove("is-open");
        }
      }

      if (els.railReopen) {
        els.railReopen.hidden = state.railOpen;
      }
    });
  }

  async function boot() {
    log("boot start");

    hydrateRailStateFromStorage();

    state.sidebarOpen = !(els.sidebar && els.sidebar.hidden);

    if (els.sidebarReopen) {
      els.sidebarReopen.hidden = state.sidebarOpen;
    }

    if (els.railReopen) {
      els.railReopen.hidden = state.railOpen;
    }

    if (els.rail) {
      els.rail.hidden = !state.railOpen;
      els.rail.classList.toggle("is-open", state.railOpen);
    }

    syncSidebarVisibility();
    bindActions();
    await loadState();
    applyBodyLockState();

    log("boot complete");
  }

  window.NovaComposerBundle = {
    state,
    loadState,
    renderAll,
    setRailTab,
    openViewer,
    clearViewerState,
    switchToSession,
    openSessionOnBackend,
    createNewChat,
    createNewChatOnBackend,
    renameSession,
    renameSessionOnBackend,
    deleteSession,
    deleteSessionOnBackend,
    reloadStateFromBackend,
    openSidebar,
    closeSidebar,
    toggleSidebar,
    openRail,
    closeRail,
    applyBodyLockState,
  };

  boot();
})();