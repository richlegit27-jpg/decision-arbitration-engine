(function () {
  "use strict";

  function findArtifactById(artifactId) {
    try {
      const targetId = String(artifactId || "").trim();
      if (!targetId) return null;

      const list = Array.isArray(state && state.artifacts) ? state.artifacts : [];

      for (let i = 0; i < list.length; i++) {
        const item = list[i];
        if (!item) continue;

        const id = String(item.id || item.artifact_id || item._id || "").trim();
        if (id === targetId) {
          return item;
        }
      }

      return null;
    } catch (e) {
      console.warn("[findArtifactById] failed", e);
      return null;
    }
  }

  if (window.NovaComposerBundle) return;

  function log() {
    try {
      console.log("[NovaComposerBundle]", ...arguments);
    } catch (_) {}
  }

async function jumpToSessionAndSync(sessionId, options) {
  const opts = options || {};
  const targetSessionId = String(sessionId || "").trim();
  if (!targetSessionId) return false;

  try {
    const response = await fetch("/api/sessions/switch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: targetSessionId }),
      credentials: "same-origin",
    });

    if (!response.ok) throw new Error("switch failed");

    const stateRes = await fetch("/api/state");
    const data = await stateRes.json();

if (typeof hydrateFromState === "function") {
  hydrateFromState(data || {});
}

// HARD RESET RAIL (CRITICAL)
state.rail.selectedId = "";
state.rail.selectedKind = "";
if (els.railViewer) {
  els.railViewer.innerHTML = "";
  els.railViewer.hidden = true;
}

if (state.pendingArtifactOpenId) {
  const id = state.pendingArtifactOpenId;
  state.pendingArtifactOpenId = "";

  if (id) {
    openArtifactFromStateOrBackend(id);
  }
}

    showToast("Session synced", "success");
    return true;

  } catch (e) {
    warn("jumpToSessionAndSync failed", e);
    showToast("Session sync failed", "error");
    return false;
  }
}

function resolveUploadUrl(url) {
  const raw = String(url || "").trim();
  if (!raw) return "";

  if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;
  if (raw.startsWith("/api/uploads/")) return raw;
  if (raw.startsWith("/uploads/")) return raw;

  if (
    raw.startsWith("generated_") ||
    raw.startsWith("generated_img_") ||
    raw.startsWith("upload_") ||
    raw.startsWith("image_")
  ) {
    return "/api/uploads/" + raw;
  }

  if (/^[^\/]+\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(raw)) {
    return "/api/uploads/" + raw;
  }

  return raw;
}

  function info() {
    try {
      console.info("[NovaComposerBundle]", ...arguments);
    } catch (_) {}
  }

  function ensureToastHost() {
    let host = document.querySelector("[data-toast-host]");
    if (host) return host;

    host = document.createElement("div");
    host.className = "nova-toast-host";
    host.setAttribute("data-toast-host", "true");
    document.body.appendChild(host);
    return host;
  }

  function showToast(message, kind) {
    const text = String(message || "").trim();
    if (!text) return;

    const host = ensureToastHost();
    const toast = document.createElement("div");
    toast.className = "nova-toast" + (kind ? " is-" + String(kind) : "");
    toast.textContent = text;

    host.appendChild(toast);

    requestAnimationFrame(function () {
      toast.classList.add("is-visible");
    });

    window.setTimeout(function () {
      toast.classList.remove("is-visible");
      toast.classList.add("is-leaving");
      window.setTimeout(function () {
        try {
          toast.remove();
        } catch (_) {}
      }, 220);
    }, 2200);
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

  function normalizeText(value) {
    return String(value == null ? "" : value)
      .replace(/\r\n/g, "\n")
      .replace(/\r/g, "\n");
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function makeId(prefix) {
    return (prefix || "id") + "_" + Math.random().toString(16).slice(2) + Date.now().toString(16);
  }

  function summarizeText(value, limit) {
    const text = normalizeText(value).trim();
    const max = Number(limit || 100);
    if (text.length <= max) return text;
    return text.slice(0, Math.max(0, max - 1)).trimEnd() + "â€¦";
  }

  function isImageMime(mime) {
    return /^image\//i.test(String(mime || ""));
  }

  function isVideoMime(mime) {
    return /^video\//i.test(String(mime || ""));
  }

  function isAudioMime(mime) {
    return /^audio\//i.test(String(mime || ""));
  }

  function formatBytes(value) {
    const num = Number(value || 0);
    if (!num || num < 1) return "";
    if (num < 1024) return num + " B";
    if (num < 1024 * 1024) return (num / 1024).toFixed(1).replace(/\.0$/, "") + " KB";
    if (num < 1024 * 1024 * 1024) {
      return (num / (1024 * 1024)).toFixed(1).replace(/\.0$/, "") + " MB";
    }
    return (num / (1024 * 1024 * 1024)).toFixed(1).replace(/\.0$/, "") + " GB";
  }

  function normalizeAttachment(item) {
    const raw = item && typeof item === "object" ? item : {};
    const name =
      raw.filename ||
      raw.name ||
      raw.title ||
      raw.label ||
      "attachment";
    const mimeType =
      raw.mime_type ||
      raw.type ||
      "application/octet-stream";

    return {
      id: String(raw.id || raw.attachment_id || makeId("att")),
      name: String(name),
      filename: String(name),
      stored_name: String(raw.stored_name || raw.stored_filename || name),
      url: String(raw.url || raw.file_url || raw.source_url || ""),
      mime_type: String(mimeType),
      size: Number(raw.size || 0),
      status: String(raw.status || "uploaded"),
      upload_error: String(raw.upload_error || ""),
    };
  }

function normalizeMessage(raw) {
  const item = raw && typeof raw === "object" ? raw : {};
  const meta = item.meta && typeof item.meta === "object" ? item.meta : {};
  const artifact = item.artifact && typeof item.artifact === "object" ? item.artifact : {};
  const viewer = item.viewer && typeof item.viewer === "object" ? item.viewer : {};

  const imageUrl = resolveUploadUrl(
    item.image_url ||
    artifact.image_url ||
    viewer.image_url ||
    meta.image_url ||
    ""
  );

  return {
    id: String(item.id || makeId("msg")),
    role: String(item.role || "assistant"),
    text: normalizeText(
      (item.ui && item.ui.message && item.ui.message.text) ||
      item.text ||
      item.content ||
      item.body ||
      item.message ||
      ""
    ),
    created_at: String(item.created_at || new Date().toISOString()),
    pending: Boolean(item.pending),
    streaming: Boolean(item.streaming),
    stopped: Boolean(item.stopped),
    error: Boolean(item.error),
    source: String(item.source || ""),
    ui: item.ui && typeof item.ui === "object" ? item.ui : {},
    meta: meta,
    artifact: artifact,
    viewer: viewer,
    image_url: imageUrl,
    attachments: safeArray(item.attachments).map(normalizeAttachment),
  };
}

function attachmentSummary(attachment) {
    const name = attachment.filename || attachment.name || "attachment";
    const size = formatBytes(attachment.size);
    return size ? name + " Â· " + size : name;
  }

  const els = {
    appShell: qs("[data-app-shell]"),
    body: document.body,
    sidebar: qs("[data-left-sidebar]"),
    sidebarBackdrop: qs("[data-sidebar-backdrop]"),
    sidebarToggle: qs("[data-sidebar-toggle]"),
    sidebarClose: qs("[data-sidebar-close]"),
    newChatButton: qs("[data-new-chat]"),
    sessionList: qs("[data-session-list]"),
    chatThread: qs("[data-chat-thread]"),
    chatEmpty: qs("[data-chat-empty]"),
    chatInput: qs("[data-chat-input]"),
    composerForm: qs("[data-chat-form]"),
    sendButton: qs("[data-send-button]"),
    stopButton: qs("[data-stop-button]"),
    attachButton: qs("[data-attach-button]"),
    attachInput: qs("[data-attach-input]"),
    uploadStaging: qs("[data-upload-staging]"),
    topbarTitle: qs("[data-topbar-title]"),
    topbarSubtitle: qs("[data-topbar-subtitle]"),
    topbarStatus: qs("[data-topbar-status]"),
    artifactList: null,
    artifactEmpty: null,
    memoryList: qs("[data-memory-list]"),
    webList: qs("[data-web-list]"),
    rail: qs("[data-right-rail]"),
    railTitle: qs("[data-rail-title]"),
    railSubtitle: qs("[data-rail-subtitle]"),
    railViewer: qs("[data-rail-viewer]"),
    railTabs: qsa("[data-rail-tab]"),
    railPanels: qsa("[data-rail-panel]"),
    voiceButton: qs('[data-action="voice"]'),
    ttsToggleButton: document.querySelector('[data-action="tts-toggle"]'),
  };

const state = {
  booted: false,
  activeSessionId: "",
  sessions: [],
  messages: [],
  artifacts: [],
  memory: [],
  pendingUploads: [],
  pendingArtifactOpenId: "",
  uploadInFlightCount: 0,
stream: {
  controller: null,
  running: false,
  messageId: "",
  mode: "",
  placeholderId: "",
  buffer: "",
},

execution: {
  active: false,
  steps: [],
},

  tokenRender: {
    queue: "",
    timer: null,
    targetMessageId: "",
    flushMs: 28,
  },

  imageGenPlaceholderId: null,

  voice: {
    recording: false,
    mediaRecorder: null,
    chunks: [],
    stream: null,
    busy: false,
  },

  tts: {
    enabled: false,
    playing: false,
    audio: null,
  },

  rail: {
    tab: "artifacts",
    selectedId: "",
    selectedKind: "",
    artifactSearch: "",
    artifactFilter: "all",
  },
};

function renderExecution() {
  const container =
    document.querySelector("#execution-panel") ||
    document.querySelector("[data-execution-panel]");

  if (!container) return;

  if (
    !state.execution ||
    !state.execution.active ||
    !Array.isArray(state.execution.steps) ||
    !state.execution.steps.length
  ) {
    container.innerHTML = "";
    container.hidden = true;
    return;
  }

  container.hidden = false;

  container.innerHTML = state.execution.steps
    .map(function (step) {
      const status = String(step.status || "planned").toLowerCase();
      let icon = "○";

      if (status === "completed" || status === "done") icon = "✓";
      else if (status === "running") icon = "→";
      else if (status === "failed" || status === "error") icon = "⚠";

      return (
        '<div class="exec-step exec-' + escapeHtml(status) + '">' +
          '<span class="exec-icon">' + icon + '</span>' +
          '<span class="exec-text">' +
            escapeHtml(step.title || step.text || "") +
          '</span>' +
        '</div>'
      );
    })
    .join("");
}

function syncRailReopenVisibility() {
  const el = document.querySelector("[data-rail-reopen-wrap]");
  if (!el) return;

  const open =
    document.body.classList.contains("is-rail-open") ||
    (els.rail && els.rail.classList.contains("is-open"));

  el.hidden = open;
}

function openRail() {
  if (!els.rail) return;

  els.rail.classList.add("is-open");
  document.body.classList.add("is-rail-open");

  if (els.railTabs && els.railTabs.length) {
    const activeTab =
      state.rail && state.rail.tab ? state.rail.tab : "artifacts";

    setRailTab(activeTab);
  }

  if (state.rail && state.rail.selectedKind && state.rail.selectedId) {
    setRailSelectedItem(state.rail.selectedKind, state.rail.selectedId);
  }

  if (typeof renderArtifacts === "function") renderArtifacts();
  if (typeof renderMemory === "function") renderMemory();
  if (typeof renderWeb === "function") renderWeb();

  syncRailReopenVisibility();
}

async function openArtifactFromStateOrBackend(artifactId) {
  const id = String(artifactId || "").trim();
  if (!id) return;

  let artifact =
    typeof findArtifactById === "function" ? findArtifactById(id) : null;

  if (!artifact) {
    try {
      const payload = await apiGet("/api/state");
      applyStatePayload(payload);
      artifact =
        typeof findArtifactById === "function" ? findArtifactById(id) : null;
    } catch (error) {
      warn("artifact refresh failed", error);
    }
  }

  if (!artifact) {
    state.rail.selectedId = "";
    state.rail.selectedKind = "";

    openRail();
    setRailTab("artifacts");

    if (els.railViewer) {
      els.railViewer.hidden = false;
      els.railViewer.innerHTML =
        '<div class="nova-viewer-shell">' +
        '<div class="nova-viewer-empty">' +
        '<div class="nova-viewer-empty-title">Artifact not found</div>' +
        '<div class="nova-viewer-empty-copy">This artifact is not available in the current session.</div>' +
        "</div>" +
        "</div>";
    }

    showToast("Artifact not found.", "error");
    return;
  }

  const artifactSessionId = String(
    artifact.session_id ||
      (artifact.viewer && artifact.viewer.session_id) ||
      ""
  ).trim();

  if (
    artifactSessionId &&
    artifactSessionId !== String(state.activeSessionId || "").trim()
  ) {
    try {
      await openSessionFromBackend(artifactSessionId);
      artifact =
        typeof findArtifactById === "function" ? findArtifactById(id) || artifact : artifact;
    } catch (error) {
      warn("artifact session open failed", error);
      showToast("Session switch failed.", "error");
      return;
    }
  }

  openRail();
  setRailTab("artifacts");
  setRailSelectedItem("artifact", id);

  if (els.railViewer) {
    els.railViewer.hidden = false;
    els.railViewer.innerHTML = artifactViewerHtml(artifact);
  }

  if (els.railTitle) {
    els.railTitle.textContent = "Artifacts";
  }

  if (els.railSubtitle) {
    const viewer =
      artifact.viewer && typeof artifact.viewer === "object" ? artifact.viewer : {};
    els.railSubtitle.textContent = String(
      viewer.title || artifact.title || artifact.name || "Artifact"
    );
  }

  if (typeof renderArtifacts === "function") {
    renderArtifacts();
  }
}

  function closeRail() {
    if (!els.rail) return;
    els.rail.classList.remove("is-open");
    document.body.classList.remove("is-rail-open");
  }

  function setTopbar(title, subtitle, statusText, statusState) {
    if (els.topbarTitle) {
      els.topbarTitle.textContent = title || "Nova";
    }

    if (els.topbarSubtitle) {
      els.topbarSubtitle.textContent = subtitle || "Fast local AI workspace";
    }

    if (els.topbarStatus) {
      els.topbarStatus.textContent = statusText || "Ready";
      els.topbarStatus.classList.remove("is-busy", "is-error", "is-idle");

      const nextState = String(statusState || "idle");

      if (nextState === "busy") {
        els.topbarStatus.classList.add("is-busy");
        els.topbarStatus.setAttribute("data-state", "busy");
      } else if (nextState === "error") {
        els.topbarStatus.classList.add("is-error");
        els.topbarStatus.setAttribute("data-state", "error");
      } else {
        els.topbarStatus.classList.add("is-idle");
        els.topbarStatus.setAttribute("data-state", "idle");
      }
    }
  }

function setBusyUi(isBusy) {
  if (els.sendButton) {
    els.sendButton.disabled = Boolean(isBusy);
  }
  if (els.stopButton) {
    els.stopButton.hidden = !isBusy;
    els.stopButton.disabled = !isBusy;
  }
  if (els.chatInput) {
    els.chatInput.disabled = false;
  }
  if (els.attachButton) {
    els.attachButton.disabled = Boolean(isBusy && state.uploadInFlightCount > 0);
  }
}

if (els.sendButton) {
  els.sendButton.onclick = function (event) {
    event.preventDefault();
    console.log("SEND BUTTON CLICKED");
    sendMessage();
  };
}

if (els.chatInput) {
  els.chatInput.addEventListener("input", autoResizeTextarea);
  els.chatInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });
}

  function autoResizeTextarea() {
    if (!els.chatInput) return;
    els.chatInput.style.height = "auto";
    els.chatInput.style.height = Math.min(els.chatInput.scrollHeight, 280) + "px";
  }

  function scrollChatToBottom(force) {
    if (!els.chatThread) return;

    const nearBottom =
      els.chatThread.scrollHeight - els.chatThread.scrollTop - els.chatThread.clientHeight < 160;

    if (force || nearBottom) {
      els.chatThread.scrollTop = els.chatThread.scrollHeight;
    }
  }

  function setChatEmptyVisible(isVisible) {
    if (!els.chatEmpty) return;
    els.chatEmpty.hidden = !isVisible;
  }

  function activeSession() {
    return state.sessions.find(function (session) {
      return String(session.id) === String(state.activeSessionId);
    }) || null;
  }

  function finishStreamUi(options) {
    const opts = options && typeof options === "object" ? options : {};
    const statusState = String(opts.statusState || "idle");
    const statusText = String(
      opts.statusText || (statusState === "error" ? "Error" : "Ready")
    );

    state.stream.running = false;
    state.stream.controller = null;
    state.stream.messageId = "";
    state.stream.placeholderId = "";
    state.stream.buffer = "";

    setBusyUi(false);

    const session = activeSession();
    const title = session && session.title ? session.title : "Nova";
    const subtitle =
      session && Number(session.message_count || safeArray(session.messages).length || 0) > 0
        ? Number(session.message_count || safeArray(session.messages).length || 0) + " messages"
        : "Fast local AI workspace";

    setTopbar(title, subtitle, statusText, statusState);
  }

  function updateTopbarFromState() {
    const session = activeSession();
    const title = session && session.title ? session.title : "Nova";
    const subtitle =
      session && Number(session.message_count || safeArray(session.messages).length || 0) > 0
        ? Number(session.message_count || safeArray(session.messages).length || 0) + " messages"
        : "Fast local AI workspace";

    let statusText = "Ready";
    let statusState = "idle";

    if (state.stream.running) {
      statusText = "Generating";
      statusState = "busy";
    } else {
      const lastAssistant = state.messages
        .slice()
        .reverse()
        .find(function (msg) {
          return String(msg.role || "") === "assistant";
        }) || null;

      if (lastAssistant && lastAssistant.error) {
        statusText = "Error";
        statusState = "error";
      } else if (lastAssistant && lastAssistant.stopped) {
        statusText = "Stopped";
        statusState = "idle";
      }
    }

    setTopbar(title, subtitle, statusText, statusState);
  }

  function findMessageById(messageId) {
    return state.messages.find(function (item) {
      return String(item.id) === String(messageId);
    }) || null;
  }

  function upsertMessage(rawMessage) {
    const message = normalizeMessage(rawMessage);
    const index = state.messages.findIndex(function (item) {
      return String(item.id) === String(message.id);
    });

    if (index >= 0) {
      state.messages[index] = Object.assign({}, state.messages[index], message);
    } else {
      state.messages.push(message);
    }

    renderChat();
    return message;
  }

function removeMessage(messageId) {
  const id = String(messageId || "").trim();
  if (!id) return;

  state.messages = (state.messages || []).filter(function (msg) {
    return String((msg && msg.id) || "") !== id;
  });

  renderChat();
}

  function removeMessageById(messageId) {
    const before = state.messages.length;
    state.messages = state.messages.filter(function (item) {
      return String(item.id) !== String(messageId);
    });

    if (state.messages.length !== before) {
      renderChat();
    }
  }

  function setSessions(list) {
    state.sessions = safeArray(list).map(function (item) {
      const session = item && typeof item === "object" ? item : {};
      return {
        id: String(session.id || makeId("session")),
        title: String(session.title || "Untitled chat"),
        created_at: String(session.created_at || ""),
        updated_at: String(session.updated_at || ""),
        pinned: Boolean(session.pinned),
        last_message_preview: String(session.last_message_preview || ""),
        message_count: Number(session.message_count || safeArray(session.messages).length || 0),
        messages: safeArray(session.messages).map(normalizeMessage),
      };
    });

    renderSessionList();
  }

function applyStatePayload(payload) {
  const data = payload && typeof payload === "object" ? payload : {};

state.activeSessionId = String(
  data.active_session_id ||
  data.session_id ||
  (data.session && data.session.id) ||
  (data.active_session && data.active_session.id) ||
  state.activeSessionId ||
  ""
).trim();

  if (Array.isArray(data.sessions)) {
    setSessions(data.sessions);
  }

  if (data.active_session && Array.isArray(data.active_session.messages)) {
    state.messages = data.active_session.messages.map(normalizeMessage);
  } else if (data.session && Array.isArray(data.session.messages)) {
    state.messages = data.session.messages.map(normalizeMessage);
  } else if (Array.isArray(data.messages)) {
    state.messages = data.messages.map(normalizeMessage);
  } else {
    state.messages = state.messages || [];
  }

  if (data.assistant_message) {
    upsertMessage(normalizeMessage(data.assistant_message));
  }

  state.artifacts = safeArray(data.artifacts);
  state.memory = safeArray(data.memory);
  state.web = safeArray(data.web);

  if (window.NovaArtifacts && typeof window.NovaArtifacts.reload === "function") {
    window.NovaArtifacts.reload();
  }

  renderSessionList();
  renderChat();
  renderArtifacts();
  renderMemory();

  if (typeof renderWeb === "function") {
    renderWeb();
  }

  updateTopbarFromState();

  try {
    window.dispatchEvent(new CustomEvent("nova:composer-state", {
      detail: {
        session_id: state.activeSessionId,
        artifacts: state.artifacts || []
      }
    }));
  } catch (e) {
    console.warn("composer-state dispatch failed", e);
  }
}

// ==============================
// 🔥 SESSION RESTORE (GLOBAL)
// ==============================
window.openSessionFromBackend = async function (sessionId) {
  const id = String(sessionId || "").trim();
  if (!id) return;

  const res = await fetch(`/api/sessions/${id}`, {
    method: "GET",
    credentials: "same-origin",
  });

  if (!res.ok) {
    throw new Error("Failed to load session");
  }

  const payload = await res.json();

  if (typeof applyStatePayload === "function") {
    applyStatePayload(payload);
  }
};

// ==============================
// 🔥 ARTIFACT → CHAT BRIDGE
// ==============================

window.NovaArtifactChatAction = function (text) {
  const value = String(text || "").trim();
  if (!value) return;

  const composer =
    document.querySelector('textarea[name="message"]') ||
    document.querySelector("#composer-input") ||
    document.querySelector("[data-composer-input]");

  if (!composer) return;

  composer.value = value;
  composer.dispatchEvent(new Event("input", { bubbles: true }));
  composer.focus();
};

window.NovaSendMessage = async function () {
  if (typeof sendMessage === "function") {
    return await sendMessage();
  }
};

window.NovaSendMessage = async function () {
  if (typeof sendMessage === "function") {
    return await sendMessage();
  }
};

// 👇 PUT IT RIGHT HERE
window.NovaAnalyzeArtifactImage = async function (imageUrl, artifact) {
  const url = String(imageUrl || "").trim();
  if (!url) return;

  const payload = {
    user_text: "what is in this image",
    session_id: String(state.activeSessionId || "").trim(),
    attachments: [
      {
        id: "artifact_image_" + Date.now(),
        filename: (artifact && artifact.title ? artifact.title : "artifact-image") + ".png",
        name: (artifact && artifact.title ? artifact.title : "artifact-image") + ".png",
        mime_type: "image/png",
        type: "image",
        source: "artifact",
        url: url
      }
    ]
  };

  if (typeof consumeChatStream === "function") {
    return await consumeChatStream(payload);
  }

  if (typeof consumeChatStreamStable === "function") {
    return await consumeChatStreamStable(payload);
  }
};

// ==============================
// 🔥 COPY + REGENERATE FIX (PUT THIS HERE)
// ==============================
document.addEventListener("click", async function (event) {
  const copyBtn = event.target.closest("[data-copy-message]");
  if (copyBtn) {
    const messageId = String(copyBtn.getAttribute("data-copy-message") || "").trim();
    if (!messageId) return;

    const msg = state.messages.find(function (m) {
      return String(m.id || "") === messageId;
    });
    if (!msg) return;

    const text = String(msg.text || "").trim();
    if (!text) return;

    try {
      await navigator.clipboard.writeText(text);
      console.log("copied");
    } catch (err) {
      console.warn("copy failed", err);
    }
    return;
  }

  const regenBtn = event.target.closest("[data-regenerate-message]");
  if (regenBtn) {
    const messageId = String(regenBtn.getAttribute("data-regenerate-message") || "").trim();
    if (!messageId) return;

    const userMsg = currentUserMessageForRegenerate(messageId);
    if (!userMsg) return;

    const payload = {
      user_text: String(userMsg.text || "").trim(),
      session_id: String(state.activeSessionId || "").trim(),
      attachments: Array.isArray(userMsg.attachments) ? userMsg.attachments : [],
    };

    if (!payload.user_text) return;

    if (typeof consumeChatStream === "function") {
      await consumeChatStream(payload);
    } else if (typeof consumeChatStreamStable === "function") {
      await consumeChatStreamStable(payload);
    }
  }
});

  function currentUserMessageForRegenerate(targetAssistantId) {
    const targetId = String(targetAssistantId || "");
    let targetIndex = -1;

    for (let i = 0; i < state.messages.length; i += 1) {
      if (String(state.messages[i].id) === targetId) {
        targetIndex = i;
        break;
      }
    }

    if (targetIndex <= 0) return null;

    for (let j = targetIndex - 1; j >= 0; j -= 1) {
      if (String(state.messages[j].role) === "user") {
        return state.messages[j];
      }
    }

    return null;
  }

  function createAssistantPlaceholder(mode, targetAssistantId) {
    const messageId = String(targetAssistantId || makeId("assistant"));
    const placeholder = normalizeMessage({
      id: messageId,
      role: "assistant",
      text: "",
      created_at: new Date().toISOString(),
      pending: true,
      streaming: true,
      source: mode || "send",
      attachments: [],
      meta: mode === "regenerate" ? { regenerate_of: messageId } : {},
    });

    upsertMessage(placeholder);
    return placeholder;
  }

  function attachmentChipHtml(attachment, options) {
    const item = normalizeAttachment(attachment);
    const opts = options && typeof options === "object" ? options : {};
    const removable = Boolean(opts.removable);
    const status = item.status || "uploaded";
    const error = item.upload_error || "";
    const summary = attachmentSummary(item);

    const removeButton = removable
      ? '<button type="button" class="nova-upload-chip__remove" data-upload-remove="' +
        escapeHtml(item.id) +
        '" aria-label="Remove attachment">Ã—</button>'
      : "";

    const statusHtml =
      status === "uploading"
        ? '<span class="nova-upload-chip__status">Uploadingâ€¦</span>'
        : status === "error"
        ? '<span class="nova-upload-chip__status nova-upload-chip__status--error">' +
          escapeHtml(error || "Upload failed") +
          "</span>"
        : "";

    return (
      '<div class="nova-upload-chip" data-upload-id="' +
      escapeHtml(item.id) +
      '">' +
      '<div class="nova-upload-chip__meta">' +
      '<div class="nova-upload-chip__name">' +
      escapeHtml(item.filename || item.name || "attachment") +
      "</div>" +
      '<div class="nova-upload-chip__sub">' +
      escapeHtml(summary) +
      "</div>" +
      statusHtml +
      "</div>" +
      removeButton +
      "</div>"
    );
  }

  function renderPendingUploads() {
    if (!els.uploadStaging) return;

    const items = state.pendingUploads;
    if (!items.length) {
      els.uploadStaging.innerHTML = "";
      els.uploadStaging.hidden = true;
      return;
    }

    els.uploadStaging.hidden = false;
    els.uploadStaging.innerHTML = items
      .map(function (item) {
        return attachmentChipHtml(item, { removable: item.status !== "uploading" });
      })
      .join("");
  }

function renderAttachmentBlock(attachment) {
  const item = normalizeAttachment(attachment);
  const name = item.filename || item.name || "attachment";
  const href = item.url || "#";
  const mime = item.mime_type || "application/octet-stream";
  const sub = [];

  if (mime) sub.push(mime);
  if (item.size) sub.push(formatBytes(item.size));

  const subText = sub.join(" Â· ");

  if (item.url && isImageMime(mime)) {
    return (
      '<div class="message-attachment message-attachment--image">' +
      '<a href="' +
      escapeHtml(href) +
      '" target="_blank" rel="noopener noreferrer">' +
      '<img src="' +
      escapeHtml(href) +
      '" alt="' +
      escapeHtml(name) +
      '" class="message-attachment__image">' +
      "</a>" +
      '<div class="message-attachment__footer">' +
      '<a href="' +
      escapeHtml(href) +
      '" target="_blank" rel="noopener noreferrer" class="message-attachment__name">' +
      escapeHtml(name) +
      "</a>" +
      '<div class="message-attachment__sub">' +
      escapeHtml(subText) +
      "</div>" +
      '<div class="message-attachment__actions">' +
      '<a href="' +
      escapeHtml(href) +
      '" download class="message-attachment__action">Download</a>' +
      '<button type="button" class="message-attachment__action" data-copy-url="' +
      escapeHtml(href) +
      '">Copy URL</button>' +
      "</div>" +
      "</div>" +
      "</div>"
    );
  }

  if (item.url && isVideoMime(mime)) {
    return (
      '<div class="message-attachment message-attachment--video">' +
      '<video controls preload="metadata" class="message-attachment__video">' +
      '<source src="' +
      escapeHtml(href) +
      '" type="' +
      escapeHtml(mime) +
      '">' +
      "</video>" +
      '<div class="message-attachment__footer">' +
      '<a href="' +
      escapeHtml(href) +
      '" target="_blank" rel="noopener noreferrer" class="message-attachment__name">' +
      escapeHtml(name) +
      "</a>" +
      '<div class="message-attachment__sub">' +
      escapeHtml(subText) +
      "</div>" +
      "</div>" +
      "</div>"
    );
  }

  if (item.url && isAudioMime(mime)) {
    return (
      '<div class="message-attachment message-attachment--audio">' +
      '<audio controls preload="metadata" class="message-attachment__audio">' +
      '<source src="' +
      escapeHtml(href) +
      '" type="' +
      escapeHtml(mime) +
      '">' +
      "</audio>" +
      '<div class="message-attachment__footer">' +
      '<a href="' +
      escapeHtml(href) +
      '" target="_blank" rel="noopener noreferrer" class="message-attachment__name">' +
      escapeHtml(name) +
      "</a>" +
      '<div class="message-attachment__sub">' +
      escapeHtml(subText) +
      "</div>" +
      "</div>" +
      "</div>"
    );
  }

  return (
    '<div class="message-attachment message-attachment--file">' +
    '<a href="' +
    escapeHtml(href || "#") +
    '" target="_blank" rel="noopener noreferrer" class="message-attachment__file-link">' +
    '<div class="message-attachment__icon">ðŸ“Ž</div>' +
    '<div class="message-attachment__footer">' +
    '<div class="message-attachment__name">' +
    escapeHtml(name) +
    "</div>" +
    '<div class="message-attachment__sub">' +
    escapeHtml(subText) +
    "</div>" +
    "</div>" +
    "</a>" +
    "</div>"
  );
}

  function renderMessageActions(message) {
    if (String(message.role) !== "assistant") return "";

    const disabled = state.stream.running ? ' aria-disabled="true"' : "";
    const disabledAttr = state.stream.running ? " disabled" : "";

    return (
      '<div class="nova-message-actions">' +
      '<button type="button" class="nova-message-action" data-copy-message="' +
      escapeHtml(message.id) +
      '"' +
      disabled +
      disabledAttr +
      ">Copy</button>" +
      '<button type="button" class="nova-message-action" data-regenerate-message="' +
      escapeHtml(message.id) +
      '"' +
      disabled +
      disabledAttr +
      ">Regenerate</button>" +
      "</div>"
    );
  }

function renderMessageCard(message) {
  const role = String(message.role || "assistant");
  const roleClass = role === "user" ? "message-card--user" : "message-card--assistant";
  const attachments = safeArray(message.attachments);

  const imageUrl = resolveUploadUrl(
    message.image_url ||
    (message.artifact && message.artifact.image_url) ||
    (message.viewer && message.viewer.image_url) ||
    (message.meta && message.meta.image_url) ||
    ""
  );

  const imageHtml = imageUrl
    ? '<div class="message-attachments">' +
        '<div class="message-attachment message-attachment--image">' +
          '<a href="' + escapeHtml(imageUrl) + '" target="_blank" rel="noopener noreferrer">' +
            '<img src="' + escapeHtml(imageUrl) + '" alt="Generated image" class="message-attachment__image">' +
          '</a>' +
          '<div class="message-attachment__footer">' +
            '<a href="' + escapeHtml(imageUrl) + '" target="_blank" rel="noopener noreferrer" class="message-attachment__name">Generated image</a>' +
            '<div class="message-attachment__actions">' +
              '<a href="' + escapeHtml(imageUrl) + '" download class="message-attachment__action">Download</a>' +
              '<button type="button" class="message-attachment__action" data-copy-url="' + escapeHtml(imageUrl) + '">Copy URL</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>'
    : "";

  const attachmentsHtml = attachments.length
    ? '<div class="message-attachments">' + attachments.map(renderAttachmentBlock).join("") + "</div>"
    : "";

  const textHtml = String(message.text || "").trim()
    ? '<div class="message-text-inline" style="display:block !important; white-space:pre-wrap !important; color:#ffffff !important; background:rgba(255,255,255,0.04) !important; padding:10px 12px !important; border-radius:10px !important; margin:8px 0 10px 0 !important; line-height:1.45 !important;">' +
        renderSafeText(message.text) +
      "</div>"
    : "";

  const bodyHtml = textHtml
    ? textHtml
    : message.pending || message.streaming
    ? '<div class="message-card__body"><span class="message-card__typing"><span class="message-card__dot"></span><span class="message-card__dot"></span><span class="message-card__dot"></span></span></div>'
    : "";

  const metaBits = [];
  if (message.pending || message.streaming) metaBits.push("Streaming");
  if (message.error) metaBits.push("Error");
  if (message.stopped) metaBits.push("Stopped");
  if (message.source) metaBits.push(message.source);

  const metaHtml = metaBits.length
    ? '<div class="message-card__meta">' + escapeHtml(metaBits.join(" · ")) + "</div>"
    : "";

  return (
    '<article class="message-card ' +
    roleClass +
    '" data-message-id="' +
    escapeHtml(message.id) +
    '">' +
    '<div class="message-card__header">' +
    '<div class="message-card__role">' +
    escapeHtml(role === "user" ? "You" : "Nova") +
    "</div>" +
    metaHtml +
    "</div>" +
    bodyHtml +
    imageHtml +
    attachmentsHtml +
    renderMessageActions(message) +
    "</article>"
  );
}          
 
function renderChat() {
  if (!els.chatThread) return;
  setChatEmptyVisible(state.messages.length === 0);
  els.chatThread.innerHTML = state.messages.map(renderMessageCard).join("");
  updateTopbarFromState();
  scrollChatToBottom(true);
}

function renderSessionList() {
  if (!els.sessionList) return;

  const sessions = state.sessions.slice().sort(function (a, b) {
    const ap = a.pinned ? 1 : 0;
    const bp = b.pinned ? 1 : 0;
    if (ap !== bp) return bp - ap;

    const at = Date.parse(a.updated_at || a.created_at || 0) || 0;
    const bt = Date.parse(b.updated_at || b.created_at || 0) || 0;
    return bt - at;
  });

  els.sessionList.innerHTML = sessions
    .map(function (session) {
      const active = String(session.id) === String(state.activeSessionId);

      return (
        '<div class="nova-session-card' +
        (active ? " is-active" : "") +
        '">' +
        '<button type="button" class="nova-session-card-main" data-open-session="' +
        escapeHtml(session.id) +
        '">' +
        '<div class="nova-session-card-top">' +
        '<div class="nova-session-card-title">' +
        escapeHtml(session.title || "Untitled chat") +
        "</div>" +
        (session.pinned ? '<div class="nova-session-card-pin">ðŸ“Œ</div>' : "") +
        "</div>" +
        '<div class="nova-session-card-preview">' +
        escapeHtml(session.last_message_preview || "No messages yet") +
        "</div>" +
        '<div class="nova-session-card-meta">' +
        escapeHtml(
          String(
            Number(session.message_count || safeArray(session.messages).length || 0)
          ) + " messages"
        ) +
        "</div>" +
        "</button>" +
        '<div class="nova-session-card-actions">' +
        '<button type="button" class="nova-session-card-action" data-pin-session="' +
        escapeHtml(session.id) +
        '">' +
        (session.pinned ? "Unpin" : "Pin") +
        "</button>" +
        '<button type="button" class="nova-session-card-action" data-rename-session="' +
        escapeHtml(session.id) +
        '">Rename</button>' +
        '<button type="button" class="nova-session-card-action" data-delete-session="' +
        escapeHtml(session.id) +
        '">Delete</button>' +
        "</div>" +
        "</div>"
      );
    })
    .join("");
}

function renderArtifacts() {
  if (!els.artifactList) {
    els.artifactList = document.querySelector("[data-artifact-list]");
  }
  if (!els.artifactList) return;

  const activeSessionId = String(state.activeSessionId || "").trim();
  const searchQuery = String(
    (state.rail && state.rail.artifactSearch) || ""
  ).trim().toLowerCase();
  const activeFilter = String(
    (state.rail && state.rail.artifactFilter) || "all"
  ).trim().toLowerCase();

  const allArtifacts = safeArray(state.artifacts);

  let sessionArtifacts = allArtifacts.filter(function (item) {
    if (!activeSessionId) return true;
    return String(item && item.session_id ? item.session_id : "").trim() === activeSessionId;
  });

  if (!sessionArtifacts.length && allArtifacts.length) {
    sessionArtifacts = allArtifacts.slice();
  }

  function getKindBadge(kind) {
    const kindLabel = String(kind || "artifact").toLowerCase();

    if (kindLabel.includes("image")) return "image";
    if (kindLabel.includes("web")) return "web";
    if (kindLabel.includes("chat")) return "chat";
    if (kindLabel.includes("analysis")) return "analysis";
    return "artifact";
  }

  function getGroupOrder(kindBadge) {
    if (kindBadge === "image") return 1;
    if (kindBadge === "web") return 2;
    if (kindBadge === "chat") return 3;
    if (kindBadge === "analysis") return 4;
    return 5;
  }

  function getGroupTitle(kindBadge) {
    if (kindBadge === "image") return "Images";
    if (kindBadge === "web") return "Web";
    if (kindBadge === "chat") return "Chat";
    if (kindBadge === "analysis") return "Analysis";
    return "Other";
  }

  const normalized = sessionArtifacts
    .map(function (item) {
      const viewer = item && typeof item.viewer === "object" ? item.viewer : {};
      const meta = item && typeof item.meta === "object" ? item.meta : {};

      const id = String(item.id || "").trim();
      const title = String(
        viewer.title || item.title || item.name || "Artifact"
      ).trim();

      const preview = String(
        viewer.body ||
          item.preview ||
          item.body ||
          item.content ||
          item.summary ||
          ""
      ).trim();

      const kind = String(
        viewer.kind || item.kind || "artifact"
      ).trim();

      const kindBadge = getKindBadge(kind);

      const thumbUrl = String(
        viewer.image_url ||
          item.image_url ||
          meta.image_url ||
          ""
      ).trim();

      const createdAt = String(
        item.updated_at || item.created_at || ""
      ).trim();

      let timeLabel = "";
      if (createdAt) {
        try {
          const date = new Date(createdAt);
          timeLabel = Number.isNaN(date.getTime())
            ? createdAt
            : date.toLocaleString([], {
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "2-digit",
              });
        } catch (error) {
          timeLabel = createdAt;
        }
      }

      const haystack = [
        title,
        preview,
        kind,
        kindBadge,
        String(item.session_id || "")
      ]
        .join("\n")
        .toLowerCase();

      return {
        raw: item,
        id: id,
        title: title,
        preview: preview,
        kind: kind,
        kindBadge: kindBadge,
        thumbUrl: thumbUrl,
        createdAt: createdAt,
        timeLabel: timeLabel,
        haystack: haystack,
      };
    })
    .filter(function (entry) {
      if (!entry.id) return false;

      const matchesSearch = !searchQuery || entry.haystack.indexOf(searchQuery) >= 0;
      const matchesFilter =
        activeFilter === "all" || entry.kindBadge === activeFilter;

      return matchesSearch && matchesFilter;
    });

  const controlsHtml =
    '<div class="rail-artifact-tools">' +
      '<input type="text" class="rail-artifact-search" data-artifact-search placeholder="Search artifacts..." value="' +
        escapeHtml((state.rail && state.rail.artifactSearch) || "") +
      '">' +
      '<div class="rail-artifact-filters">' +
        '<button type="button" class="rail-filter-pill' +
          (activeFilter === "all" ? " is-active" : "") +
          '" data-artifact-filter="all">All</button>' +
        '<button type="button" class="rail-filter-pill' +
          (activeFilter === "image" ? " is-active" : "") +
          '" data-artifact-filter="image">Image</button>' +
        '<button type="button" class="rail-filter-pill' +
          (activeFilter === "web" ? " is-active" : "") +
          '" data-artifact-filter="web">Web</button>' +
        '<button type="button" class="rail-filter-pill' +
          (activeFilter === "chat" ? " is-active" : "") +
          '" data-artifact-filter="chat">Chat</button>' +
        '<button type="button" class="rail-filter-pill' +
          (activeFilter === "analysis" ? " is-active" : "") +
          '" data-artifact-filter="analysis">Analysis</button>' +
      "</div>" +
    "</div>";

  if (!sessionArtifacts.length) {
    els.artifactList.innerHTML =
      controlsHtml +
      '<div class="nova-artifact-empty">' +
      '<div class="nova-artifact-empty-title">No artifacts for this session</div>' +
      '<div class="nova-artifact-empty-copy">Create an image, web result, analysis, or chat artifact in this session to see it here.</div>' +
      "</div>";

    if (
      state.rail &&
      state.rail.selectedKind === "artifact" &&
      els.railViewer
    ) {
      els.railViewer.hidden = false;
      els.railViewer.innerHTML =
        '<div class="nova-viewer-shell">' +
        '<div class="nova-viewer-empty">' +
        '<div class="nova-viewer-empty-title">No artifact selected</div>' +
        '<div class="nova-viewer-empty-copy">This session does not have any artifacts yet.</div>' +
        "</div>" +
        "</div>";
    }
    return;
  }

  if (!normalized.length) {
    els.artifactList.innerHTML =
      controlsHtml +
      '<div class="nova-artifact-empty">' +
      '<div class="nova-artifact-empty-title">No matching artifacts</div>' +
      '<div class="nova-artifact-empty-copy">Try a different search or filter.</div>' +
      "</div>";

    if (
      state.rail &&
      state.rail.selectedKind === "artifact" &&
      els.railViewer
    ) {
      els.railViewer.hidden = false;
      els.railViewer.innerHTML =
        '<div class="nova-viewer-shell">' +
        '<div class="nova-viewer-empty">' +
        '<div class="nova-viewer-empty-title">Nothing matches this filter</div>' +
        '<div class="nova-viewer-empty-copy">Change the search text or filter pills to show more artifacts.</div>' +
        "</div>" +
        "</div>";
    }
    return;
  }

  normalized.sort(function (a, b) {
    const groupDiff = getGroupOrder(a.kindBadge) - getGroupOrder(b.kindBadge);
    if (groupDiff !== 0) return groupDiff;

    const at = Date.parse(a.createdAt || 0) || 0;
    const bt = Date.parse(b.createdAt || 0) || 0;
    return bt - at;
  });

  const grouped = {};
  normalized.forEach(function (entry) {
    const key = entry.kindBadge || "artifact";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(entry);
  });

  const orderedGroups = Object.keys(grouped)
    .sort(function (a, b) {
      return getGroupOrder(a) - getGroupOrder(b);
    })
    .map(function (groupKey) {
      const cardsHtml = grouped[groupKey]
        .map(function (entry) {
          const isActive =
            state.rail &&
            state.rail.selectedKind === "artifact" &&
            String(state.rail.selectedId || "").trim() === entry.id;

          return (
            '<div class="nova-artifact-card' +
            (isActive ? " is-active" : "") +
            '" data-artifact-open="' +
            escapeHtml(entry.id) +
            '">' +
              '<div class="nova-artifact-card-top">' +
                '<span class="nova-artifact-card-kind">' +
                  escapeHtml(entry.kindBadge) +
                "</span>" +
                (entry.timeLabel
                  ? '<span class="nova-artifact-card-time">' +
                    escapeHtml(entry.timeLabel) +
                    "</span>"
                  : "") +
              "</div>" +
              '<div class="nova-artifact-card-title">' +
                escapeHtml(entry.title) +
              "</div>" +
              (entry.preview
                ? '<div class="nova-artifact-card-preview">' +
                  escapeHtml(entry.preview.slice(0, 200)) +
                  "</div>"
                : "") +
              (entry.thumbUrl
                ? '<img class="nova-artifact-card-thumb" src="' +
                  escapeHtml(entry.thumbUrl) +
                  '" alt="' +
                  escapeHtml(entry.title) +
                  '" loading="lazy" />'
                : "") +
            "</div>"
          );
        })
        .join("");

      return (
        '<section class="nova-artifact-group">' +
          '<div class="nova-artifact-group-title">' +
            escapeHtml(getGroupTitle(groupKey)) +
          "</div>" +
          '<div class="nova-artifact-list">' +
            cardsHtml +
          "</div>" +
        "</section>"
      );
    })
    .join("");

  els.artifactList.innerHTML = controlsHtml + orderedGroups;

  if (
    state.rail &&
    state.rail.selectedKind === "artifact" &&
    state.rail.selectedId
  ) {
    const selectedStillVisible = normalized.some(function (entry) {
      return entry.id === String(state.rail.selectedId || "").trim();
    });

    if (!selectedStillVisible) {
      state.rail.selectedId = "";
      if (els.railViewer) {
        els.railViewer.hidden = false;
        els.railViewer.innerHTML =
          '<div class="nova-viewer-shell">' +
          '<div class="nova-viewer-empty">' +
          '<div class="nova-viewer-empty-title">Selected artifact hidden</div>' +
          '<div class="nova-viewer-empty-copy">Your current search, filter, or session no longer includes the previously selected artifact.</div>' +
          "</div>" +
          "</div>";
      }
    }
  }
}

  async function apiGet(url) {
    const response = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
      },
    });

    const data = await response.json().catch(function () {
      return {};
    });

    if (!response.ok || data.ok === false) {
      throw new Error(data.error || ("Request failed: " + response.status));
    }

    return data;
  }

  async function apiPost(url, body, extra) {
    const response = await fetch(
      url,
      Object.assign(
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(body || {}),
        },
        extra || {}
      )
    );

    const data = await response.json().catch(function () {
      return {};
    });

    if (!response.ok || data.ok === false) {
      throw new Error(data.error || ("Request failed: " + response.status));
    }

    return data;
  }

  async function stopActiveStream(options) {
    const opts = Object.assign(
      { silent: false, reason: "Stopped.", statusState: "idle", statusText: "Ready" },
      options || {}
    );

    if (!state.stream || !state.stream.running) return;

    const controller = state.stream.controller;
    if (controller) {
      try {
        controller.abort();
      } catch (_) {}
    }

    const id = state.stream.messageId || state.stream.placeholderId;
    if (id) {
      const msg = findMessageById(id);
      if (msg) {
        upsertMessage({
          ...msg,
          pending: false,
          streaming: false,
          stopped: true,
          error: false,
        });
      }
    }

    finishStreamUi({
      statusState: opts.statusState,
      statusText: opts.statusText,
    });

    if (!opts.silent) {
      showToast(opts.reason, "info");
    }
  }

  async function stopStreamBeforeSessionChange() {
    if (!state.stream || !state.stream.running) return;

    await stopActiveStream({
      silent: true,
      reason: "Stopped before switching sessions.",
    });
  }

function queueTokenFlush(messageId) {
  if (!messageId) return;
  if (tokenFlushQueued) return;

  tokenFlushQueued = true;

  if (tokenRafId) {
    try {
      cancelAnimationFrame(tokenRafId);
    } catch (_) {}
    tokenRafId = 0;
  }

  tokenRafId = requestAnimationFrame(function () {
    flushTokensNow();
  });
}
 
function clearTokenRenderState() {
  tokenTextBuffer = "";
  tokenMessageId = "";
  tokenFlushQueued = false;
  tokenLastFlushAt = 0;

  if (tokenRafId) {
    try {
      cancelAnimationFrame(tokenRafId);
    } catch (_) {}
  }

  tokenRafId = 0;
}

function flushTokensNow() {
  return;
}

function ensureTokenRenderState() {
  if (!state.tokenRender) {
    state.tokenRender = {
      buffer: "",
      targetMessageId: "",
      scheduled: false,
      lastFlushAt: 0,
      rafId: 0,
    };
  }
  return state.tokenRender;
}

function clearTokenRenderState() {
  const tr = ensureTokenRenderState();

  if (tr.rafId) {
    try {
      cancelAnimationFrame(tr.rafId);
    } catch (_) {}
  }

  tr.buffer = "";
  tr.targetMessageId = "";
  tr.scheduled = false;
  tr.lastFlushAt = 0;
  tr.rafId = 0;
}

function appendTextToMessage(messageId, chunk) {
  if (!messageId || !chunk) return;

  const index = state.messages.findIndex(function (msg) {
    return msg && msg.id === messageId;
  });

  if (index === -1) return;

  const current = state.messages[index] || {};
  const nextText = String(current.text || "") + String(chunk || "");

  state.messages[index] = normalizeMessage({
    ...current,
    text: nextText,
    pending: false,
    streaming: true,
    error: false,
  });
}

function flushTokensNow() {
  const tr = ensureTokenRenderState();
  if (!tr.targetMessageId || !tr.buffer) {
    tr.scheduled = false;
    tr.rafId = 0;
    return;
  }

  const chunk = tr.buffer;
  tr.buffer = "";
  tr.scheduled = false;
  tr.rafId = 0;
  tr.lastFlushAt = Date.now();

  appendTextToMessage(tr.targetMessageId, chunk);
  renderChat();
  scrollChatToBottom(true);
}

function scheduleTokenFlush() {
  const tr = ensureTokenRenderState();
  if (tr.scheduled) return;

  tr.scheduled = true;
  tr.rafId = requestAnimationFrame(function () {
    flushTokensNow();
  });
}

function handleStreamEvent(event) {
  const payload = event && typeof event === "object" ? event : {};

  const type = String(
    payload.type ||
    payload.event ||
    payload.kind ||
    ""
  ).trim().toLowerCase();

  if (payload.execution && Array.isArray(payload.execution.steps)) {
    state.execution.active = true;
    state.execution.steps = payload.execution.steps.map(function (step, index) {
      return {
        id: String(step.id || ("step_" + index)),
        title: String(step.title || step.text || ""),
        status: String(step.status || "planned"),
        notes: String(step.notes || ""),
      };
    });

    renderExecution();
    return;
  }

  if (!state.stream) {
    state.stream = {
      running: false,
      controller: null,
      targetMessageId: "",
      buffer: "",
      startedAt: 0,
      messageId: "",
      placeholderId: "",
    };
  }

  if (type === "token" || type === "delta" || type === "chunk") {
    const chunkText = String(
      payload.text ||
      payload.delta ||
      payload.token ||
      payload.text_delta ||
      payload.chunk ||
      ""
    );

    if (state.stream.targetMessageId && chunkText) {
      queueIncomingTokens(state.stream.targetMessageId, chunkText);
    }

    return;
  }

  if (!state.stream.targetMessageId) {
    const messageId = String(
      payload.message_id ||
      payload.id ||
      ("assistant_" + Date.now())
    ).trim();

    state.stream.targetMessageId = messageId;
    state.stream.messageId = messageId;
    state.stream.placeholderId = messageId;

    upsertMessage(normalizeMessage({
      id: messageId,
      role: "assistant",
      text: "",
      streaming: true,
      pending: false,
      error: false,
      stopped: false,
      attachments: [],
      meta: {},
    }));

    renderChat();
    scrollChatToBottom(true);
  }

  const targetId = String(state.stream.targetMessageId || "").trim();
  if (!targetId) return;

  const delta =
    typeof payload.delta === "string" ? payload.delta :
    typeof payload.token === "string" ? payload.token :
    typeof payload.text_delta === "string" ? payload.text_delta :
    typeof payload.chunk === "string" ? payload.chunk :
    "";

  if (delta) {
    queueIncomingTokens(targetId, delta);
    return;
  }

   if (
    type === "final" ||
    type === "done" ||
    type === "complete" ||
    payload.done === true ||
    payload.final === true
  ) {
    flushTokensNow();

    state.execution = {
      active: true,
      steps: [
        { text: "Thinking...", status: "done" },
        { text: "Response ready", status: "done" },
      ],
    };
    renderExecution();

    finalizeStreamMessage(payload);
    clearTokenRenderState();
    return;
  }

  if (payload.error) {
    flushTokensNow();

    state.execution = {
      active: true,
      steps: [
        { text: "Thinking...", status: "done" },
        { text: "Response failed", status: "error" },
      ],
    };
    renderExecution();

    upsertMessage(normalizeMessage({
      id: targetId,
      role: "assistant",
      text: String(payload.error || "Stream failed."),
      streaming: false,
      pending: false,
      error: true,
      stopped: true,
      attachments: [],
      meta: {},
    }));

    clearTokenRenderState();

    state.stream.running = false;
    state.stream.controller = null;
    state.stream.targetMessageId = "";
    state.stream.buffer = "";
    state.stream.startedAt = 0;
    state.stream.messageId = "";
    state.stream.placeholderId = "";

    renderChat();
    scrollChatToBottom(true);
  }
}

function finalizeStreamMessage(payload) {
  flushTokensNow();
  clearTokenRenderState();

  const data = payload && typeof payload === "object" ? payload : {};
  const targetId = String(
    data.message_id ||
    data.id ||
    (state.stream && (state.stream.targetMessageId || state.stream.messageId)) ||
    ("assistant_" + Date.now())
  ).trim();

  const existingIndex = state.messages.findIndex(function (msg) {
    return msg && msg.id === targetId;
  });

  const existing = existingIndex >= 0 ? state.messages[existingIndex] : null;

  const finalText = String(
    data.text ||
    data.message ||
    data.content ||
    (existing && existing.text) ||
    ""
  );

  upsertMessage(normalizeMessage({
    id: targetId,
    role: "assistant",
    text: finalText,
    streaming: false,
    pending: false,
    error: false,
    stopped: false,
    attachments: Array.isArray(data.attachments) ? data.attachments : [],
    meta: data.meta && typeof data.meta === "object" ? data.meta : {},
    artifact: data.artifact && typeof data.artifact === "object" ? data.artifact : {},
    viewer: data.viewer && typeof data.viewer === "object" ? data.viewer : {},
    image_url:
      data.image_url ||
      (data.artifact && data.artifact.image_url) ||
      (data.viewer && data.viewer.image_url) ||
      (data.meta && data.meta.image_url) ||
      "",
  }));

  if (data.execution && Array.isArray(data.execution.steps)) {
    state.execution.active = true;
    state.execution.steps = data.execution.steps.map(function (step, index) {
      return {
        id: String(step.id || ("step_" + index)),
        title: String(step.title || step.text || ""),
        text: String(step.text || step.title || ""),
        status: String(step.status || "planned"),
        notes: String(step.notes || ""),
      };
    });
  } else if (state.execution && state.execution.active) {
    state.execution = {
      active: true,
      steps: [
        { text: "Thinking...", status: "done" },
        { text: "Response ready", status: "done" },
      ],
    };
  }

  renderExecution();

  // CRITICAL: hydrate from the real final payload instead of partial manual updates
  applyStatePayload(data);

  if (state.stream) {
    state.stream.running = false;
    state.stream.controller = null;
    state.stream.targetMessageId = "";
    state.stream.buffer = "";
    state.stream.startedAt = 0;
    state.stream.messageId = "";
    state.stream.placeholderId = "";
  }

  renderChat();
  renderSessionList();
  renderArtifacts();
  renderMemory();
  if (typeof renderWeb === "function") {
    renderWeb();
  }
  updateTopbarFromState();
  scrollChatToBottom(true);
  finishStreamUi({ statusState: "idle", statusText: "Ready" });
}

async function openSession(sessionId) {
  const id = String(sessionId || "").trim();
  if (!id) return null;

  await stopStreamBeforeSessionChange();

  const payload = await apiPost("/api/sessions/switch", {
    session_id: id,
  });

  applyStatePayload(payload || {});
  renderSessionList();
  renderChat();
  renderArtifacts();
  renderMemory();
  updateTopbarFromState();
  scrollChatToBottom(true);

  return payload;
}

function artifactViewerHtml(artifact) {
  if (!artifact || typeof artifact !== "object") {
    return '<div class="artifact-empty">No artifact selected.</div>';
  }

  const viewer = artifact.viewer || {};
  const meta = artifact.meta || {};

  const kind = String(viewer.kind || artifact.kind || "artifact").trim();
  const title = String(viewer.title || artifact.title || "Artifact").trim();

  const summary = String(
    viewer.analysis_text ||
    artifact.summary ||
    artifact.preview ||
    ""
  ).trim();

  const body = String(
    viewer.body ||
    artifact.body ||
    meta.content ||
    ""
  ).trim();

  const sourceUrl = String(
    viewer.source_url ||
    artifact.source_url ||
    meta.url ||
    ""
  ).trim();

  const bullets = Array.isArray(viewer.bullets) ? viewer.bullets : [];
  const links = Array.isArray(viewer.links) ? viewer.links : [];
  const images = Array.isArray(viewer.images) ? viewer.images : [];

  const escapeHtml = (v) =>
    String(v || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

  const bulletsHtml = bullets.length
    ? `<section class="artifact-view-section">
        <div class="artifact-view-section__title">Highlights</div>
        <ul class="artifact-bullets">
          ${bullets.map(b => `<li>${escapeHtml(b)}</li>`).join("")}
        </ul>
      </section>`
    : "";

  const linksHtml = links.length
    ? `<section class="artifact-view-section">
        <div class="artifact-view-section__title">Links</div>
        <div class="artifact-link-list">
          ${links.map(l => `
            <a class="artifact-link-item" href="${escapeHtml(l)}" target="_blank">
              ${escapeHtml(l)}
            </a>
          `).join("")}
        </div>
      </section>`
    : "";

  const imagesHtml = images.length
    ? `<section class="artifact-view-section">
        <div class="artifact-view-section__title">Images</div>
        <div class="artifact-image-grid">
          ${images.map(src => `
            <a href="${escapeHtml(src)}" target="_blank">
              <img src="${escapeHtml(src)}" />
            </a>
          `).join("")}
        </div>
      </section>`
    : "";

  const bodyHtml = body
    ? `<section class="artifact-view-section">
        <div class="artifact-view-section__title">Content</div>
        <div class="artifact-body">
          ${body.split(/\n\n/).map(p => `<p>${escapeHtml(p)}</p>`).join("")}
        </div>
      </section>`
    : "";

  return `
    <div class="artifact-view">
      <div class="artifact-view-header">
        <div class="artifact-view-header__kind">${escapeHtml(kind)}</div>
        <div class="artifact-view-header__title">${escapeHtml(title)}</div>
        ${summary ? `<div class="artifact-view-header__summary">${escapeHtml(summary)}</div>` : ""}
      </div>

      ${bulletsHtml}
      ${linksHtml}
      ${imagesHtml}
      ${bodyHtml}

      ${sourceUrl ? `
        <section class="artifact-view-section">
          <div class="artifact-view-section__title">Source</div>
          <a class="artifact-meta-link" href="${escapeHtml(sourceUrl)}" target="_blank">
            ${escapeHtml(sourceUrl)}
          </a>
        </section>
      ` : ""}
    </div>
  `;
}

 function setRailTab(tab) {
  const t = String(tab || "").trim();
  if (!t) return;

  if (!state.rail) state.rail = {};
  state.rail.tab = t;

  /* highlight tabs */
  document.querySelectorAll("[data-rail-tab]").forEach(function (btn) {
    const btnTab = String(btn.getAttribute("data-rail-tab") || "").trim();
    if (btnTab === t) {
      btn.classList.add("is-active");
    } else {
      btn.classList.remove("is-active");
    }
  });

  /* toggle panels */
  const artifactsPanel = document.querySelector("[data-rail-artifacts]");
  const memoryPanel = document.querySelector("[data-rail-memory]");
  const webPanel = document.querySelector("[data-rail-web]");

  if (artifactsPanel) artifactsPanel.hidden = t !== "artifacts";
  if (memoryPanel) memoryPanel.hidden = t !== "memory";
  if (webPanel) webPanel.hidden = t !== "web";

  /* render */
  if (t === "artifacts" && typeof renderArtifacts === "function") {
    renderArtifacts();
  }

  if (t === "memory" && typeof renderMemory === "function") {
    renderMemory();
  }

  if (t === "web" && typeof renderWeb === "function") {
    renderWeb();
  }
}

function cssEscape(value) {
  const text = String(value || "");
  if (window.CSS && typeof window.CSS.escape === "function") {
    return window.CSS.escape(text);
  }
  return text.replace(/"/g, '\\"');
}

function setRailSelectedItem(kind, id) {
  if (!state.rail) state.rail = {};
  state.rail.selectedKind = String(kind || "").trim();
  state.rail.selectedId = String(id || "").trim();

  document
    .querySelectorAll("[data-artifact-id], [data-memory-id], [data-web-id]")
    .forEach(function (node) {
      node.classList.remove("is-active");
    });

  let selector = "";
  if (state.rail.selectedKind === "artifact") {
    selector = '[data-artifact-id="' + cssEscape(state.rail.selectedId) + '"]';
  } else if (state.rail.selectedKind === "memory") {
    selector = '[data-memory-id="' + cssEscape(state.rail.selectedId) + '"]';
  } else if (state.rail.selectedKind === "web") {
    selector = '[data-web-id="' + cssEscape(state.rail.selectedId) + '"]';
  }

  if (!selector) return;

  const target = document.querySelector(selector);
  if (!target) return;

  target.classList.add("is-active");

  try {
    target.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
      inline: "nearest",
    });
  } catch (error) {
    target.scrollIntoView();
  }
}

async function openArtifactFromStateOrBackend(artifactId) {
  const id = String(artifactId || "").trim();
  if (!id) return;

  let artifact =
    typeof findArtifactById === "function" ? findArtifactById(id) : null;

  if (!artifact) {
    try {
      const payload = await apiGet("/api/state");
      applyStatePayload(payload);
      artifact =
        typeof findArtifactById === "function" ? findArtifactById(id) : null;
    } catch (error) {
      warn("artifact refresh failed", error);
    }
  }

  if (!artifact) {
    openRail();
    setRailTab("artifacts");
    setRailSelectedItem("artifact", id);

    if (els.railViewer) {
      els.railViewer.hidden = false;
      els.railViewer.innerHTML =
        '<div class="nova-viewer-shell">' +
        '<div class="nova-viewer-empty">' +
        '<div class="nova-viewer-empty-title">Artifact not found</div>' +
        '<div class="nova-viewer-empty-copy">This artifact is not available in the current state.</div>' +
        "</div>" +
        "</div>";
    }

    showToast("Artifact not found.", "error");
    return;
  }

  const artifactSessionId = String(
    artifact.session_id ||
      (artifact.viewer && artifact.viewer.session_id) ||
      ""
  ).trim();

  if (
    artifactSessionId &&
    artifactSessionId !== String(state.activeSessionId || "").trim()
  ) {
    try {
      state.pendingArtifactOpenId = id;
      await openSessionFromBackend(artifactSessionId);

      artifact =
        typeof findArtifactById === "function" ? findArtifactById(id) || artifact : artifact;
    } catch (error) {
      warn("artifact session open failed", error);
      showToast("Session switch failed.", "error");
      return;
    }
  }

  if (!artifact) {
    if (state.pendingArtifactOpenId === id) {
      state.pendingArtifactOpenId = "";
    }

    if (els.railViewer) {
      els.railViewer.hidden = false;
      els.railViewer.innerHTML =
        '<div class="nova-viewer-shell">' +
        '<div class="nova-viewer-empty">' +
        '<div class="nova-viewer-empty-title">Artifact reopen failed</div>' +
        '<div class="nova-viewer-empty-copy">The owning session opened, but this artifact could not be resolved afterward.</div>' +
        "</div>" +
        "</div>";
    }

    showToast("Artifact could not be reopened after session switch.", "error");
    return;
  }

  state.pendingArtifactOpenId = "";
  state.rail = state.rail || {};
  state.rail.tab = "artifacts";
  state.rail.selectedKind = "artifact";
  state.rail.selectedId = id;

  openRail();
  setRailTab("artifacts");
  setRailSelectedItem("artifact", id);

  if (window.NovaArtifacts && typeof window.NovaArtifacts.setActiveArtifactById === "function") {
    window.NovaArtifacts.setActiveArtifactById(id);
  } else if (els.railViewer) {
    els.railViewer.hidden = false;
    els.railViewer.innerHTML = artifactViewerHtml(artifact);
  }

  if (els.railTitle) {
    els.railTitle.textContent = "Artifacts";
  }

  if (els.railSubtitle) {
    const viewer =
      artifact.viewer && typeof artifact.viewer === "object" ? artifact.viewer : {};
    els.railSubtitle.textContent = String(
      viewer.title || artifact.title || artifact.name || "Artifact"
    );
  }

  if (typeof renderArtifacts === "function") {
    renderArtifacts();
  }
}

function setPendingUploadItem(nextItem) {
  const normalized = normalizeAttachment(nextItem);
  const index = state.pendingUploads.findIndex(function (item) {
    return String(item.id) === String(normalized.id);
  });
  if (index >= 0) {
    state.pendingUploads[index] = Object.assign({}, state.pendingUploads[index], normalized);
  } else {
    state.pendingUploads.push(normalized);
  }
  renderPendingUploads();
}

async function uploadOneFile(file) {
  const tempId = makeId("att_local");

  setPendingUploadItem({
    id: tempId,
    filename: String(file && file.name ? file.name : ""),
    name: String(file && file.name ? file.name : ""),
    stored_name: "",
    file_url: "",
    url: "",
    mime_type: String((file && file.type) || "application/octet-stream"),
    size: Number((file && file.size) || 0),
    status: "uploading",
    upload_error: "",
  });

  state.uploadInFlightCount = Math.max(0, Number(state.uploadInFlightCount || 0)) + 1;
  setBusyUi(state.stream && state.stream.running);

  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/api/upload", {
      method: "POST",
      credentials: "same-origin",
      body: formData,
    });

    const data = await response.json().catch(function () {
      return {};
    });

    if (!response.ok || data.ok === false) {
      throw new Error(data.error || "Upload failed.");
    }

    const uploadedAttachment = normalizeAttachment({
      id: tempId,
      filename: String(data.original_filename || file.name || ""),
      name: String(data.original_filename || file.name || ""),
      stored_name: String(data.filename || ""),
      file_url: String(data.file_url || data.url || ""),
      url: String(data.url || data.file_url || ""),
      mime_type: String(data.mime_type || file.type || "application/octet-stream"),
      size: Number(data.size || file.size || 0),
      status: "uploaded",
      upload_error: "",
    });

    setPendingUploadItem(uploadedAttachment);
uploadedAttachment.status = "done";
    showToast(
      "Uploaded: " + (uploadedAttachment.filename || uploadedAttachment.name || "attachment"),
      "success"
    );
    return normalizeAttachment(uploadedAttachment);
  } catch (error) {
if (!(error instanceof TypeError)) {
  warn("upload failed", error);
}

    const errorText = error && error.message ? error.message : "Upload failed.";

    setPendingUploadItem({
      id: tempId,
      filename: String(file && file.name ? file.name : ""),
      name: String(file && file.name ? file.name : ""),
      stored_name: "",
      file_url: "",
      url: "",
      mime_type: String((file && file.type) || "application/octet-stream"),
      size: Number((file && file.size) || 0),
      status: "error",
      upload_error: errorText,
    });

    showToast(
      "Upload failed: " + (file && file.name ? file.name : "attachment"),
      "error"
    );
    throw error;
  } finally {
    state.uploadInFlightCount = Math.max(0, state.uploadInFlightCount - 1);
    setBusyUi(state.stream && state.stream.running);
    renderPendingUploads();
  }
}

  async function uploadFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    for (const file of files) {
      await uploadOneFile(file);
    }
  }

  function clearPendingUploads() {
    state.pendingUploads = [];
    if (els.attachInput) {
      els.attachInput.value = "";
    }
    renderPendingUploads();
  }

  function getSendPayload(base) {
  const source = base && typeof base === "object" ? base : {};
  const userText = String(source.user_text || "");
  const isImageCommand = userText.trim().toLowerCase().startsWith("/image");

  return {
    session_id: String(state.activeSessionId || ""),
    user_text: userText,
    stream: !isImageCommand,
    regenerate_of: source.regenerate_of ? String(source.regenerate_of) : "",
    attachments: safeArray(source.attachments).map(normalizeAttachment),
  };
}


function appendUserMessageLocal(text, attachments) {
  const message = normalizeMessage({
    id: makeId("user"),
    role: "user",
    text: text,
    attachments: safeArray(attachments).map(normalizeAttachment),
    created_at: new Date().toISOString(),
  });
  upsertMessage(message);
  return message;
}

async function consumeChatJson(payload) {
  state.stream = state.stream || {
    running: false,
    controller: null,
    buffer: "",
    placeholderId: "",
    messageId: "",
    targetMessageId: "",
    startedAt: 0,
  };

  state.execution = state.execution || {
    active: false,
    steps: [],
  };

  if (state.stream.running) {
    showToast("A generation is already running.", "info");
    throw new Error("A generation is already running.");
  }

  setBusyUi(true);
  state.stream.running = false;
  updateTopbarFromState();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json, text/event-stream, text/plain, */*",
      },
      body: JSON.stringify(payload || {}),
    });

    const rawText = await response.text();
    log("consumeChatJson status", response.status);
    log("consumeChatJson raw response", rawText);

    let data = {};
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch (parseError) {
      warn("consumeChatJson JSON parse failed", parseError);

      if (rawText.indexOf("data:") >= 0) {
        showToast("Chat returned stream data to JSON mode.", "error");
        throw new Error("Chat returned stream data to JSON mode.");
      }

      throw new Error("Chat returned invalid JSON.");
    }

    if (!response.ok || data.ok === false) {
      const message = String(data.error || "Chat failed.");
      showToast(message, "error");
      throw new Error(message);
    }

    // FIX: attach generated image to assistant message
    if (data && data.saved_artifact && data.saved_artifact.image_url) {
      if (!data.assistant_message) {
        data.assistant_message = {};
      }

      data.assistant_message.image_url = data.saved_artifact.image_url;
      data.assistant_message.artifact = data.saved_artifact;
    }

    applyStatePayload(data || {});

    if (data && data.session && data.session.id) {
      state.activeSessionId = String(data.session.id || "");
    } else if (data && data.session_id) {
      state.activeSessionId = String(data.session_id || "");
    }

    state.execution = state.execution || {
      active: false,
      steps: [],
    };

    if (data.execution && Array.isArray(data.execution.steps)) {
      state.execution.active = true;
      state.execution.steps = data.execution.steps.map(function (step, index) {
        return {
          id: String(step.id || ("step_" + index)),
          title: String(step.title || step.text || ""),
          status: String(step.status || "planned"),
          notes: String(step.notes || ""),
        };
      });
      renderExecution();
    } else {
      state.execution.active = false;
      state.execution.steps = [];
      renderExecution();
    }

    renderSessionList();
    renderChat();
    renderArtifacts();
    renderMemory();
    updateTopbarFromState();
    scrollChatToBottom(true);

    flushTokensNow();
    clearTokenRenderState();

    if (state.stream) {
      state.stream.running = false;
      state.stream.controller = null;
      state.stream.buffer = "";
      state.stream.placeholderId = "";
      state.stream.messageId = "";
      state.stream.targetMessageId = "";
      state.stream.startedAt = 0;
    }

    finishStreamUi({
      statusState: "idle",
      statusText: "Ready",
    });

    return data;
  } catch (error) {
    finishStreamUi({
      statusText: "Error",
      statusState: "error",
    });
    throw error;
  }
}

async function sendMessage() {
  const inputEl = els.chatInput || document.querySelector("[data-chat-input]") || document.querySelector("textarea");
  const text = String((inputEl && inputEl.value) || "").trim();

  console.log("sendMessage ENTERED", {
    hasInput: !!inputEl,
    text: text,
    inputValue: inputEl ? inputEl.value : null
  });

  if (/^\/image|generate image|create image|draw/i.test(text)) {
    const tempId = "gen_" + Date.now();

    upsertMessage(normalizeMessage({
      id: tempId,
      role: "assistant",
      text: "🎨 Generating image...",
      pending: true,
      streaming: false,
      error: false,
      stopped: false,
      attachments: [],
    }));

    state.imageGenPlaceholderId = tempId;
  }

  const attachments = state.pendingUploads
    .filter(function (item) {
      return (
        item &&
        item.status === "uploaded" &&
        (
          String(item.stored_name || "").trim() ||
          String(item.file_url || "").trim() ||
          String(item.url || "").trim()
        )
      );
    })
    .map(function (item) {
      return {
        id: String(item.id || ""),
        filename: String(item.filename || item.name || ""),
        name: String(item.name || item.filename || ""),
        stored_name: String(item.stored_name || ""),
        file_url: String(item.file_url || ""),
        url: String(item.url || item.file_url || ""),
        mime_type: String(item.mime_type || "application/octet-stream"),
        size: Number(item.size || 0),
        status: "uploaded",
        upload_error: "",
      };
    });

  if (!text && !attachments.length) {
    console.log("SEND BLOCKED: empty text and no attachments");
    showToast("Type a message first.", "info");
    return;
  }

  state.execution.active = false;
  state.execution.steps = [];
  renderExecution();

  console.log("ACTIVE SESSION BEFORE", state.activeSessionId);

  if (!state.activeSessionId) {
    console.log("CREATING NEW SESSION...");

    const created = await apiPost("/api/sessions/new", {});
    console.log("SESSION CREATE RESPONSE", created);

    if (created && created.session && created.session.id) {
      state.activeSessionId = String(created.session.id);
    } else if (created && created.active_session_id) {
      state.activeSessionId = String(created.active_session_id);
    }

    console.log("ACTIVE SESSION AFTER CREATE", state.activeSessionId);

    await loadState();
    console.log("LOAD STATE FINISHED");
  }

  appendUserMessageLocal(text, attachments);

  if (els.chatInput) {
    els.chatInput.value = "";
    autoResizeTextarea();
  }

  clearPendingUploads();

  try {
    const isImageCommand = String(text || "").trim().toLowerCase().startsWith("/image");

    const payload = {
      user_text: text,
      session_id: String(state.activeSessionId || ""),
      attachments: attachments,
    };

    if (isImageCommand) {
      await consumeChatJson(payload);
      showToast("Image request sent.", "success");
    } else {
      const pendingAssistantId = makeId("assistant");

      upsertMessage(
        normalizeMessage({
          id: pendingAssistantId,
          role: "assistant",
          text: "",
          created_at: new Date().toISOString(),
          pending: true,
          streaming: true,
          error: false,
          stopped: false,
          attachments: [],
          meta: {},
        })
      );

      if (!state.stream) {
        state.stream = {
          running: false,
          controller: null,
          targetMessageId: "",
          buffer: "",
          startedAt: 0,
          messageId: "",
          placeholderId: "",
        };
      }

      state.stream.targetMessageId = pendingAssistantId;
      state.stream.messageId = pendingAssistantId;
      state.stream.placeholderId = pendingAssistantId;

const tr = ensureTokenRenderState();
tr.targetMessageId = pendingAssistantId;
tr.buffer = "";
tr.scheduled = false;
tr.lastFlushAt = 0;
if (tr.rafId) {
  try {
    cancelAnimationFrame(tr.rafId);
  } catch (_) {}
  tr.rafId = 0;
}

renderChat();
scrollChatToBottom(true);

payload.placeholder_id = pendingAssistantId;

console.log("ABOUT TO SEND /api/chat", payload);

try {
  await consumeChatJson(payload);
} catch (err) {
  finishStreamUi({
    statusText: "Error",
    statusState: "error",
  });

  showToast("Chat failed", "error");

  upsertMessage(
    normalizeMessage({
      id: makeId("assistant_error"),
      role: "assistant",
      text: "⚠️ Something went wrong sending the message.",
      error: true,
    })
  );
}

if (state.imageGenPlaceholderId) {
  removeMessage(state.imageGenPlaceholderId);
  state.imageGenPlaceholderId = null;
}
     
    }
  } catch (error) {
    warn("sendMessage failed", error);
    showToast(
      error && error.message ? error.message : "Send failed.",
      "error"
    );
  }
}

async function regenerateMessage(targetAssistantId) {
  if (state.stream.running) {
    showToast("A generation is already running.", "info");
    return;
  }

  const targetId = String(targetAssistantId || "").trim();
  if (!targetId) {
    showToast("Nothing to regenerate.", "error");
    return;
  }

  const userMessage = currentUserMessageForRegenerate(targetId);
  if (!userMessage) {
    showToast("Could not find the user message for regenerate.", "error");
    return;
  }

  removeMessageById(targetId);

  const payload = getSendPayload({
    user_text: String(userMessage.text || ""),
    regenerate_of: targetId,
    attachments: safeArray(userMessage.attachments),
  });

console.log("ABOUT TO SEND /api/chat", payload);
  await consumeChatStream(payload);
}

function stopGeneration() {
  if (!state.stream.running || !state.stream.controller) return;
  try {
    state.stream.controller.abort();
    showToast("Generation stopped.", "info");
  } catch (_) {}
  flushTokensNow();
  clearTokenRenderState();
  finishStreamUi();
}

async function createNewChat() {
  if (state.stream.running) {
    stopGeneration();
  }
  await apiPost("/api/sessions/new", {});
  clearPendingUploads();

  if (els.chatInput) {
    els.chatInput.value = "";
    autoResizeTextarea();
  }
  await loadState();
}

async function copyMessage(messageId) {
  const message = findMessageById(messageId);
  if (!message) return;
  try {
    await navigator.clipboard.writeText(message.text || "");
  } catch (error) {
    warn("copy failed", error);
  }
}

function openAttachPicker() {
  if (!els.attachInput) return;
  els.attachInput.click();
}

function handleComposerSubmit(event) {
  if (event) {
    event.preventDefault();
  }
  sendMessage().catch(function (error) {
    warn("send failed", error);
    showToast(error && error.message ? error.message : "Send failed.", "error");
  });
}

async function renameSession(sessionId) {
  const id = String(sessionId || "").trim();
  if (!id) return;

  const session = safeArray(state.sessions).find(function (item) {
    return String(item.id || "") === id;
  });

  const currentTitle = String((session && session.title) || "Untitled chat");
  const nextTitle = window.prompt("Rename session", currentTitle);

  if (nextTitle == null) return;

  const title = String(nextTitle || "").trim();
  if (!title) {
    showToast("Title cannot be empty.", "error");
    return;
  }

  const payload = await apiPost("/api/sessions/rename", {
    session_id: id,
    title: title,
  });

  applyStatePayload(payload || {});
  await loadState();
  showToast("Session renamed.", "success");
}

async function togglePinSession(sessionId) {
  const id = String(sessionId || "").trim();
  if (!id) return;

  const session = safeArray(state.sessions).find(function (item) {
    return String(item.id || "") === id;
  });

  const pinned = !!(session && session.pinned);

  const payload = await apiPost("/api/sessions/pin", {
    session_id: id,
    pinned: !pinned,
  });

  applyStatePayload(payload || {});
  await loadState();
  showToast(!pinned ? "Session pinned." : "Session unpinned.", "success");
}

async function deleteSession(sessionId) {
  const id = String(sessionId || "").trim();
  if (!id) return;

  const session = safeArray(state.sessions).find(function (item) {
    return String(item.id || "") === id;
  });

  const title = String((session && session.title) || "this session");
  const confirmed = window.confirm('Delete "' + title + '"?');
  if (!confirmed) return;

  const payload = await apiPost("/api/sessions/delete", {
    session_id: id,
  });

  applyStatePayload(payload || {});
  await loadState();
  showToast("Session deleted.", "success");
}

async function recordVoiceOnce() {
  if (
    !navigator.mediaDevices ||
    typeof navigator.mediaDevices.getUserMedia !== "function"
  ) {
    throw new Error("Voice recording is not supported in this browser.");
  }

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const preferredMime =
    typeof MediaRecorder !== "undefined" &&
    typeof MediaRecorder.isTypeSupported === "function" &&
    MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

  const recorder = new MediaRecorder(stream, preferredMime ? { mimeType: preferredMime } : undefined);

  state.voice.recording = true;
  state.voice.mediaRecorder = recorder;
  state.voice.stream = stream;
  state.voice.chunks = [];

  recorder.addEventListener("dataavailable", function (event) {
    if (event && event.data && event.data.size > 0) {
      state.voice.chunks.push(event.data);
    }
  });

  recorder.start();
  showToast("Recording... click voice again to stop.", "info");

  return new Promise(function (resolve, reject) {
    recorder.addEventListener("stop", function () {
      try {
        const mimeType = recorder.mimeType || "audio/webm";
        const blob = new Blob(state.voice.chunks.slice(), { type: mimeType });

        if (state.voice.stream) {
          state.voice.stream.getTracks().forEach(function (track) {
            try {
              track.stop();
            } catch (_) {}
          });
        }

        state.voice.recording = false;
        state.voice.mediaRecorder = null;
        state.voice.stream = null;
        state.voice.chunks = [];

        resolve(blob);
      } catch (error) {
        reject(error);
      }
    });

    recorder.addEventListener("error", function (event) {
      if (state.voice.stream) {
        state.voice.stream.getTracks().forEach(function (track) {
          try {
            track.stop();
          } catch (_) {}
        });
      }

      state.voice.recording = false;
      state.voice.mediaRecorder = null;
      state.voice.stream = null;
      state.voice.chunks = [];

      reject(
        new Error(
          (event && event.error && event.error.message) ||
            "Voice recorder failed."
        )
      );
    });
  });
}

async function transcribeVoice(blob) {
  const form = new FormData();
  form.append("file", blob, "voice.webm");

  const response = await fetch("/api/voice/transcribe", {
    method: "POST",
    credentials: "same-origin",
    body: form,
  });

  const data = await response.json().catch(function () {
    return {};
  });

  if (!response.ok || data.ok === false) {
    throw new Error(data.error || "Voice transcription failed.");
  }

  const text = normalizeText(data.text || "").trim();

  if (!text) {
    showToast("No speech detected.", "info");
    return;
  }

  if (els.chatInput) {
    const current = normalizeText(els.chatInput.value || "").trim();
    els.chatInput.value = current ? current + "\n" + text : text;
    autoResizeTextarea();
    els.chatInput.focus();
  }

  showToast("Voice ready. Sending...", "success");

  await sendMessage();
}
let activeVoiceRecordingPromise = null;

function updateVoiceButtonUi() {
  if (!els.voiceButton) return;

  const recording = !!(state.voice && state.voice.recording);
  const busy = !!(state.voice && state.voice.busy);

  els.voiceButton.classList.toggle("is-recording", recording);
  els.voiceButton.classList.toggle("is-busy", busy);

  if (recording) {
    els.voiceButton.setAttribute("aria-label", "Stop voice recording");
    els.voiceButton.setAttribute("title", "Stop voice recording");
  } else if (busy) {
    els.voiceButton.setAttribute("aria-label", "Voice busy");
    els.voiceButton.setAttribute("title", "Voice busy");
  } else {
    els.voiceButton.setAttribute("aria-label", "Voice");
    els.voiceButton.setAttribute("title", "Voice");
  }

  els.voiceButton.disabled = busy && !recording;
}

function updateTtsToggleUi() {
  if (!els.ttsToggleButton) return;

  if (!state.tts) {
    state.tts = {
      enabled: true,
      playing: false,
      audio: null,
    };
  }

  const muted = state.tts.enabled === false;
  const playing = !!state.tts.playing;

  els.ttsToggleButton.classList.toggle("is-muted", muted);
  els.ttsToggleButton.classList.toggle("is-playing", playing);
  els.ttsToggleButton.textContent = muted ? "ðŸ”‡" : "ðŸ”Š";

  if (muted) {
    els.ttsToggleButton.setAttribute("aria-label", "Voice replies muted");
    els.ttsToggleButton.setAttribute("title", "Voice replies muted");
  } else if (playing) {
    els.ttsToggleButton.setAttribute("aria-label", "Voice replies playing");
    els.ttsToggleButton.setAttribute("title", "Voice replies playing");
  } else {
    els.ttsToggleButton.setAttribute("aria-label", "Voice replies on");
    els.ttsToggleButton.setAttribute("title", "Voice replies on");
  }
}

function toggleTtsMute() {
  if (!state.tts) {
    state.tts = {
      enabled: false,
      playing: false,
      audio: null,
    };
  }

  if (state.tts.playing && state.tts.audio) {
    stopCurrentTtsPlayback();
    showToast("Voice stopped.", "info");
    return;
  }

  state.tts.enabled = !state.tts.enabled;
  updateTtsToggleUi();

  showToast(
    state.tts.enabled ? "Voice replies on." : "Voice replies muted.",
    "info"
  );
}

async function recordVoiceOnce() {
  if (
    !navigator.mediaDevices ||
    typeof navigator.mediaDevices.getUserMedia !== "function"
  ) {
    throw new Error("Voice recording is not supported in this browser.");
  }

  if (typeof MediaRecorder === "undefined") {
    throw new Error("MediaRecorder is not available in this browser.");
  }

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

  const preferredMime =
    typeof MediaRecorder.isTypeSupported === "function" &&
    MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

  const recorder = new MediaRecorder(
    stream,
    preferredMime ? { mimeType: preferredMime } : undefined
  );

  state.voice.recording = true;
  state.voice.mediaRecorder = recorder;
  state.voice.stream = stream;
  state.voice.chunks = [];
  updateVoiceButtonUi();

  recorder.addEventListener("dataavailable", function (event) {
    if (event && event.data && event.data.size > 0) {
      state.voice.chunks.push(event.data);
    }
  });

  recorder.start();
  showToast("Recording...", "info");

  return new Promise(function (resolve, reject) {
    recorder.addEventListener("stop", function () {
      try {
        const mimeType = recorder.mimeType || "audio/webm";
        const blob = new Blob(state.voice.chunks.slice(), { type: mimeType });

        if (state.voice.stream) {
          state.voice.stream.getTracks().forEach(function (track) {
            try {
              track.stop();
            } catch (_) {}
          });
        }

        state.voice.recording = false;
        state.voice.mediaRecorder = null;
        state.voice.stream = null;
        state.voice.chunks = [];
        updateVoiceButtonUi();

        resolve(blob);
      } catch (error) {
        reject(error);
      }
    });

    recorder.addEventListener("error", function (event) {
      if (state.voice.stream) {
        state.voice.stream.getTracks().forEach(function (track) {
          try {
            track.stop();
          } catch (_) {}
        });
      }

      state.voice.recording = false;
      state.voice.mediaRecorder = null;
      state.voice.stream = null;
      state.voice.chunks = [];
      updateVoiceButtonUi();

      reject(
        new Error(
          (event && event.error && event.error.message) ||
            "Voice recorder failed."
        )
      );
    });
  });
}

async function transcribeVoice(blob) {
  if (!blob || !blob.size) {
    throw new Error("Recorded voice blob is empty.");
  }

  const form = new FormData();
  form.append("file", blob, "voice.webm");

  showToast("Transcribing voice...", "info");

  const response = await fetch("/api/voice/transcribe", {
    method: "POST",
    credentials: "same-origin",
    body: form,
  });

  const data = await response.json().catch(function () {
    return {};
  });

  if (!response.ok || data.ok === false) {
    throw new Error(data.error || "Voice transcription failed.");
  }

  const text = normalizeText(data.text || "").trim();

  if (!text) {
    showToast("No speech detected.", "info");
    return;
  }

  if (els.chatInput) {
    els.chatInput.value = text;
    autoResizeTextarea();
    els.chatInput.focus();
  }

  showToast("Voice ready. Sending...", "success");
  await sendMessage();
}

async function handleMicClick() {
  if (!state.voice) {
    state.voice = {
      recording: false,
      mediaRecorder: null,
      chunks: [],
      stream: null,
      busy: false,
    };
  }

  if (state.voice.busy) {
    showToast("Voice is busy.", "info");
    return;
  }

  if (!state.voice.recording) {
    state.voice.busy = true;
    updateVoiceButtonUi();

    try {
      activeVoiceRecordingPromise = recordVoiceOnce();
    } finally {
      state.voice.busy = false;
      updateVoiceButtonUi();
    }
    return;
  }

  const recorder = state.voice.mediaRecorder;
  if (!recorder) {
    state.voice.recording = false;
    state.voice.busy = false;
    updateVoiceButtonUi();
    throw new Error("Voice recorder is not ready.");
  }

  state.voice.busy = true;
  updateVoiceButtonUi();

  try {
    recorder.stop();

    const blob = await activeVoiceRecordingPromise;
    activeVoiceRecordingPromise = null;

    await transcribeVoice(blob);
  } finally {
    state.voice.busy = false;
    updateVoiceButtonUi();
  }
}

async function requestVoiceReply(text) {
  const cleanText = normalizeText(text || "").trim();
  if (!cleanText) return null;

  const response = await fetch("/api/voice/reply", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      text: cleanText,
      voice: "alloy",
      format: "mp3",
    }),
  });

  const data = await response.json().catch(function () {
    return {};
  });

  if (!response.ok || data.ok === false) {
    throw new Error(data.error || "Voice reply failed.");
  }

  return data;
}

function stopCurrentTtsPlayback() {
  if (!state.tts) return;

  if (state.tts.audio) {
    try {
      state.tts.audio.pause();
    } catch (_) {}
  }

  state.tts.audio = null;
  state.tts.playing = false;
  updateTtsToggleUi();
}

async function playVoiceReplyFromText(text) {
  const cleanText = normalizeText(text || "").trim();
  if (!cleanText) return;

  if (!state.tts) {
    state.tts = {
      enabled: false,
      playing: false,
      audio: null,
    };
  }

  if (state.tts.enabled === false) return;

  stopCurrentTtsPlayback();

  const payload = await requestVoiceReply(cleanText);
  const url = String((payload && payload.url) || "").trim();
  if (!url) {
    throw new Error("Voice reply URL missing.");
  }

  const absoluteUrl = url.startsWith("http")
    ? url
    : window.location.origin + url;

  log("TTS URL:", absoluteUrl);

  const audio = new Audio();
  audio.preload = "auto";
  audio.src = absoluteUrl;
  audio.load();

  state.tts.audio = audio;
  state.tts.playing = true;
  updateTtsToggleUi();

  audio.addEventListener("ended", function () {
    state.tts.playing = false;
    state.tts.audio = null;
    updateTtsToggleUi();
  });

  audio.addEventListener("error", function () {
    state.tts.playing = false;
    state.tts.audio = null;
    updateTtsToggleUi();
    showToast("Voice playback failed.", "error");
  });

  audio.addEventListener("pause", function () {
    if (!audio.ended) {
      state.tts.playing = false;
      state.tts.audio = null;
      updateTtsToggleUi();
    }
  });

  await audio.play();
}

function bindEvents() {
  if (els.composerForm) {
    els.composerForm.addEventListener("submit", handleComposerSubmit);
  }

if (els.ttsToggleButton) {
  els.ttsToggleButton.addEventListener("click", function (event) {
    event.preventDefault();
    toggleTtsMute();
  });
}

  if (els.voiceButton) {
    els.voiceButton.addEventListener("click", function (event) {
      event.preventDefault();

      handleMicClick().catch(function (error) {
        warn("voice failed", error);
        showToast(
          error && error.message ? error.message : "Voice failed.",
          "error"
        );
      });
    });
  }


if (els.attachButton) {
  els.attachButton.addEventListener("click", function (event) {
    event.preventDefault();
    openAttachPicker();
  });
}

  if (els.attachInput) {
    els.attachInput.addEventListener("change", function (event) {
      const files =
        event && event.target && event.target.files ? event.target.files : [];
      uploadFiles(files).catch(function (error) {
        warn("upload files failed", error);
        showToast(
          error && error.message ? error.message : "Upload failed.",
          "error"
        );
      });
    });
  }

  if (els.stopButton) {
    els.stopButton.addEventListener("click", function (event) {
      event.preventDefault();
      stopGeneration();
    });
  }

  if (els.newChatButton) {
    els.newChatButton.addEventListener("click", function (event) {
      event.preventDefault();
      createNewChat().catch(function (error) {
        warn("new chat failed", error);
        showToast(
          error && error.message ? error.message : "New chat failed.",
          "error"
        );
      });
    });
  }

  if (els.sessionList) {
    els.sessionList.addEventListener("click", function (event) {
      const pinButton = event.target.closest("[data-pin-session]");
      if (pinButton) {
        event.preventDefault();

        const sessionId = String(
          pinButton.getAttribute("data-pin-session") || ""
        ).trim();

        if (!sessionId) return;

        togglePinSession(sessionId).catch(function (error) {
          warn("pin session failed", error);
          showToast(
            error && error.message ? error.message : "Pin failed.",
            "error"
          );
        });
        return;
      }

      const renameButton = event.target.closest("[data-rename-session]");
      if (renameButton) {
        event.preventDefault();

        const sessionId = String(
          renameButton.getAttribute("data-rename-session") || ""
        ).trim();

        if (!sessionId) return;

        renameSession(sessionId).catch(function (error) {
          warn("rename session failed", error);
          showToast(
            error && error.message ? error.message : "Rename failed.",
            "error"
          );
        });
        return;
      }

      const deleteButton = event.target.closest("[data-delete-session]");
      if (deleteButton) {
        event.preventDefault();

        const sessionId = String(
          deleteButton.getAttribute("data-delete-session") || ""
        ).trim();

        if (!sessionId) return;

        deleteSession(sessionId).catch(function (error) {
          warn("delete session failed", error);
          showToast(
            error && error.message ? error.message : "Delete failed.",
            "error"
          );
        });
        return;
      }

      const sessionButton = event.target.closest("[data-open-session]");
      if (!sessionButton) return;

      event.preventDefault();

      const sessionId = String(
        sessionButton.getAttribute("data-open-session") || ""
      ).trim();

      if (!sessionId) return;

      openSession(sessionId).catch(function (error) {
        warn("open session failed", error);
        showToast(
          error && error.message ? error.message : "Open session failed.",
          "error"
        );
      });
    });
  }

  if (typeof wireSidebar === "function") wireSidebar();
  if (typeof wireRailClose === "function") wireRailClose();
  if (typeof wireWebLinks === "function") wireWebLinks();
  if (typeof wireRailTabs === "function") wireRailTabs();
  if (typeof wireMemoryClicks === "function") wireMemoryClicks();
}

async function boot() {
  if (state.booted) return;
  state.booted = true;

  log("boot start");
  bindEvents();
  autoResizeTextarea();
  renderPendingUploads();
  setBusyUi(false);
  setTopbar("Nova", "Fast local AI workspace", "Ready", "idle");
  updateVoiceButtonUi();
  updateTtsToggleUi();

  els.artifactList = document.querySelector("[data-artifact-list]");
  els.artifactEmpty = document.querySelector("[data-artifact-empty]");

  try {
    await loadState();
  } catch (error) {
    warn("boot state load failed", error);
    renderChat();
    renderSessionList();
    renderArtifacts();
    renderMemory();
  }

  log("boot complete");
}

function closeSidebar() {
  if (els.body) {
    els.body.classList.remove("is-sidebar-open");
  }

  if (els.sidebar) {
    els.sidebar.classList.remove("is-open");
  }

  if (els.sidebarBackdrop) {
    els.sidebarBackdrop.hidden = true;
  }
}

function openSidebar() {
  if (els.body) {
    els.body.classList.add("is-sidebar-open");
  }

  if (els.sidebar) {
    els.sidebar.classList.add("is-open");
  }

  if (els.sidebarBackdrop) {
    els.sidebarBackdrop.hidden = false;
  }
}

function wireSidebar() {
  const toggleButtons = qsa("[data-sidebar-toggle]");

  toggleButtons.forEach(function (button) {
    button.onclick = function (event) {
      if (event) event.preventDefault();

      const isOpen =
        (els.body && els.body.classList.contains("is-sidebar-open")) ||
        (els.sidebar && els.sidebar.classList.contains("is-open"));

      if (isOpen) {
        closeSidebar();
      } else {
        openSidebar();
      }
    };
  });

  if (els.sidebarClose) {
    els.sidebarClose.onclick = function (event) {
      if (event) event.preventDefault();
      closeSidebar();
    };
  }

  if (els.sidebarBackdrop) {
    els.sidebarBackdrop.onclick = function (event) {
      if (event) event.preventDefault();
      closeSidebar();
      closeRail();
    };
  }

  closeSidebar();
}

function renderWeb() {
  if (!els.webList) return;

  const items = safeArray(state.webResults);

  if (els.webEmpty) {
    els.webEmpty.hidden = items.length > 0;
  }

  els.webList.innerHTML = items.length
    ? items
        .map(function (item) {
          const id = escapeHtml(String(item.id || ""));
          const title = escapeHtml(String(item.title || "Web result"));
          const subtitle = escapeHtml(
            String(item.domain || item.url || item.source_url || "")
          );
          const preview = renderSafeText(
            summarizeText(
              item.preview ||
                item.summary ||
                item.description ||
                item.body ||
                item.content ||
                "",
              180
            )
          );

          return [
            '<button class="nova-rail-item" type="button" data-web-open="' + id + '">',
            '<div class="nova-rail-item-kicker">Web</div>',
            '<div class="nova-rail-item-title">' + title + '</div>',
            '<div class="nova-rail-item-meta">' + subtitle + '</div>',
            '<div class="nova-rail-item-preview">' + preview + '</div>',
            "</button>",
          ].join("");
        })
        .join("")
    : "";
}

function wireRailClose() {
  const closeBtn = document.querySelector("[data-rail-close]");
  if (!closeBtn) return;

  closeBtn.addEventListener("click", function () {
    closeRail();
  });
}

function wireWebLinks() {
  if (!els.webList) return;

  els.webList.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-web-open]");
    if (!btn) return;

    const openId = String(btn.getAttribute("data-web-open") || "").trim();
    if (!openId) return;

    const item = safeArray(state.artifacts).find(function (entry) {
      const viewer = entry && typeof entry.viewer === "object" ? entry.viewer : {};
      const id = String(entry.id || "");
      const sourceUrl = String(
        viewer.source_url ||
          entry.source_url ||
          (entry.meta && entry.meta.source_url) ||
          ""
      );
      return id === openId || sourceUrl === openId;
    });

    openRail();
    setRailTab("web");
    setRailSelectedItem("web", openId);

    if (typeof renderWeb === "function") {
      renderWeb();
    }

    if (item && els.railViewer) {
      els.railViewer.hidden = false;
      els.railViewer.innerHTML = artifactViewerHtml(item);
    }
  });
}

function wireRailTabs() {
  if (!els.railTabs || !els.railTabs.length) return;

  els.railTabs.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const tab = String(btn.getAttribute("data-rail-tab") || "artifacts");
      setRailTab(tab);
      setRailSelectedItem("", "");
      openRail();

      if (els.railViewer) {
        els.railViewer.hidden = false;
        els.railViewer.innerHTML =
          '<div class="nova-viewer-shell">' +
          '<div class="nova-viewer-empty">' +
          '<div class="nova-viewer-empty-title">' +
          (tab === "memory" ? "Memory" : tab === "web" ? "Web" : "Artifacts") +
          "</div>" +
          '<div class="nova-viewer-empty-copy">Select an item to view details.</div>' +
          "</div>" +
          "</div>";
      }

      if (tab === "web" && typeof renderWeb === "function") {
        renderWeb();
      }
      if (tab === "memory" && typeof renderMemory === "function") {
        renderMemory();
      }
      if (tab === "artifacts" && typeof renderArtifacts === "function") {
        renderArtifacts();
      }
    });
  });
}

function wireMemoryClicks() {
  if (!els.memoryList || els.memoryList.dataset.bound === "1") return;
  els.memoryList.dataset.bound = "1";

  els.memoryList.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-memory-open]");
    if (!btn) return;

    const memoryId = String(btn.getAttribute("data-memory-open") || "").trim();
    if (!memoryId) return;

    const item = safeArray(state.memory).find(function (entry) {
      return String(entry.id || "") === memoryId;
    });

    if (!item) return;

    openRail();
    setRailTab("memory");
    setRailSelectedItem("memory", memoryId);

    if (els.railViewer) {
      els.railViewer.hidden = false;
      els.railViewer.innerHTML =
        '<div class="nova-viewer-shell">' +
        '<div class="nova-viewer-card">' +
        '<div class="nova-viewer-kicker">Memory</div>' +
        '<div class="nova-viewer-title">' + escapeHtml(String(item.kind || "note")) + "</div>" +
        '<div class="nova-viewer-body">' + renderSafeText(String(item.text || item.content || item.body || "")) + "</div>" +
        "</div>" +
        "</div>";
    }

    if (els.railTitle) els.railTitle.textContent = "Memory";
    if (els.railSubtitle) els.railSubtitle.textContent = String(item.kind || "note");
  });
}

function normalizeMemoryItem(item) {
  const raw = item && typeof item === "object" ? item : {};
  return {
    id: String(raw.id || raw.memory_id || ("memory_" + Math.random().toString(36).slice(2))),
    text: String(raw.text || raw.content || raw.value || ""),
    kind: String(raw.kind || raw.type || "note"),
    source: String(raw.source || "memory"),
    session_id: String(raw.session_id || raw.sessionId || ""),
    created_at: String(raw.created_at || raw.createdAt || ""),
    updated_at: String(raw.updated_at || raw.updatedAt || raw.created_at || raw.createdAt || ""),
    preview: String(raw.preview || raw.summary || raw.text || raw.content || raw.value || "")
  };
}

function memoryText(item) {
  return String(
    (item && (item.text || item.preview || item.content || item.value)) || ""
  ).trim();
}

function summarizeMemoryText(value, limit) {
  const text = String(value || "").trim();
  const max = typeof limit === "number" ? limit : 140;
  if (!text) return "";
  if (text.length <= max) return text;
  return text.slice(0, max) + "â€¦";
}

function findMemoryById(memoryId) {
  const wanted = String(memoryId || "").trim();
  if (!wanted) return null;
  const items = Array.isArray(state.memory) ? state.memory : [];
  for (let i = 0; i < items.length; i += 1) {
    if (String((items[i] && items[i].id) || "") === wanted) {
      return items[i];
    }
  }
  return null;
}

function scoreMemoryAgainstText(item, text) {
  const source = (
    String((item && item.text) || "") + " " +
    String((item && item.preview) || "") + " " +
    String((item && item.kind) || "")
  ).toLowerCase();

  const query = String(text || "").toLowerCase().trim();
  if (!source || !query) return 0;

  const parts = query.split(/\s+/).filter(Boolean);
  let score = 0;

  for (let i = 0; i < parts.length; i += 1) {
    if (parts[i].length < 3) continue;
    if (source.indexOf(parts[i]) >= 0) score += 1;
  }

  if (query && source.indexOf(query) >= 0) score += 3;
  return score;
}

function selectRelevantMemory(userText, limit) {
  const items = (Array.isArray(state.memory) ? state.memory : []).map(normalizeMemoryItem);
  const ranked = items
    .map(function (item) {
      return {
        item: item,
        score: scoreMemoryAgainstText(item, userText)
      };
    })
    .filter(function (entry) {
      return entry.score > 0;
    })
    .sort(function (a, b) {
      return b.score - a.score;
    });

  return ranked.slice(0, typeof limit === "number" ? limit : 3).map(function (entry) {
    return entry.item;
  });
}

function renderMemory() {
  const list = document.querySelector("[data-memory-list]");
  const empty = document.querySelector("[data-memory-empty]");
  if (!list || !empty) return;

  const items = (Array.isArray(state.memory) ? state.memory : []).map(normalizeMemoryItem);
  state.memory = items;

  if (!items.length) {
    empty.hidden = false;
    list.innerHTML = "";
    return;
  }

  empty.hidden = true;
  list.innerHTML = items.map(function (m) {
    return (
      '<button class="nova-rail-card" type="button" data-memory-open="' + escapeHtml(m.id) + '">' +
      '<div class="nova-rail-card-title">' + escapeHtml(summarizeMemoryText(m.preview || m.text, 120) || "Memory item") + "</div>" +
      '<div class="nova-rail-card-meta">' + escapeHtml(m.kind || "note") + "</div>" +
      "</button>"
    );
  }).join("");
}

function renderMemoryViewer(item) {
  const viewer = document.querySelector("[data-rail-viewer]");
  if (!viewer) return;

  if (!item) {
    viewer.hidden = false;
    viewer.innerHTML =
      '<div class="nova-viewer-shell">' +
      '<div class="nova-viewer-empty">' +
      '<div class="nova-viewer-empty-title">Nothing selected</div>' +
      '<div class="nova-viewer-empty-copy">Select a memory item to view details.</div>' +
      "</div>" +
      "</div>";
    return;
  }

  viewer.hidden = false;
  viewer.innerHTML =
    '<div class="nova-viewer-shell">' +
    '<div class="nova-viewer-card">' +
    '<div class="nova-viewer-kicker">Memory</div>' +
    '<div class="nova-viewer-title">' + escapeHtml(item.kind || "note") + "</div>" +
    '<div class="nova-viewer-meta">' +
    escapeHtml(item.source || "memory") +
    (item.session_id ? " Â· " + escapeHtml(item.session_id) : "") +
    "</div>" +
    '<pre class="nova-artifact-meta-pre">' + escapeHtml(item.text || item.preview || "") + "</pre>" +
    "</div>" +
    "</div>";
}

function renderReplyUi() {
  if (typeof renderThread === "function") {
    renderThread();
  } else if (typeof renderChat === "function") {
    renderChat();
  } else if (typeof renderMessages === "function") {
    renderMessages();
  } else {
    console.warn("[NovaComposerBundle] no known message render function found");
  }

  if (typeof scrollThreadToBottom === "function") {
    scrollThreadToBottom();
  }
}

function mergeAssistantReplyIntoState(payload) {
  const sessionId = String(payload.session_id || state.activeSessionId || "");
  const finalEvent = payload.finalEvent || null;
  const assistantId = String(payload.assistantId || ("assistant_" + Date.now()));
  const builtText = String(payload.builtText || "").trim();

  if (sessionId) {
    state.activeSessionId = sessionId;
  }

  if (!Array.isArray(state.sessions)) {
    state.sessions = [];
  }

  let sessionIndex = state.sessions.findIndex(function (session) {
    return String((session && session.id) || "") === String(sessionId || "");
  });

  if (sessionIndex < 0 && sessionId) {
    state.sessions.push({
      id: sessionId,
      title: "New Chat",
      messages: []
    });
    sessionIndex = state.sessions.length - 1;
  }

  if (finalEvent && Array.isArray(finalEvent.messages) && finalEvent.messages.length) {
    state.messages = finalEvent.messages.map(function (msg) {
      return typeof normalizeMessage === "function" ? normalizeMessage(msg) : msg;
    });
  } else if (finalEvent && finalEvent.message && typeof finalEvent.message === "object") {
    const msgObj = typeof normalizeMessage === "function"
      ? normalizeMessage(finalEvent.message)
      : finalEvent.message;

    if (!Array.isArray(state.messages)) {
      state.messages = [];
    }

    const msgId = String(msgObj.id || assistantId);
    const existingIndex = state.messages.findIndex(function (item) {
      return String((item && item.id) || "") === msgId;
    });

    if (existingIndex >= 0) {
      state.messages[existingIndex] = Object.assign({}, state.messages[existingIndex], msgObj);
    } else {
      state.messages.push(msgObj);
    }
  } else if (builtText) {
    if (!Array.isArray(state.messages)) {
      state.messages = [];
    }

    const fallbackMessage = {
      id: assistantId,
      role: "assistant",
      text: builtText,
      created_at: new Date().toISOString(),
      attachments: [],
      artifacts: [],
      memory_used: payload.memoryUsed || []
    };

    const normalizedFallback = typeof normalizeMessage === "function"
      ? normalizeMessage(fallbackMessage)
      : fallbackMessage;

    const existingIndex = state.messages.findIndex(function (item) {
      return String((item && item.id) || "") === assistantId;
    });

    if (existingIndex >= 0) {
      state.messages[existingIndex] = Object.assign({}, state.messages[existingIndex], normalizedFallback);
    } else {
      state.messages.push(normalizedFallback);
    }
  }

  if (sessionIndex >= 0) {
    state.sessions[sessionIndex] = Object.assign({}, state.sessions[sessionIndex], {
      id: String(sessionId || state.sessions[sessionIndex].id || ""),
      messages: Array.isArray(state.messages) ? state.messages.slice() : [],
      updated_at: new Date().toISOString()
    });
  }

  if (finalEvent && Array.isArray(finalEvent.artifacts)) {
    state.artifacts = finalEvent.artifacts.slice();
  }

  if (finalEvent && Array.isArray(finalEvent.memory)) {
    state.memory = finalEvent.memory.map(normalizeMemoryItem);
  }

  renderReplyUi();

  if (typeof renderArtifacts === "function") {
    renderArtifacts();
  }
  renderMemory();
  if (typeof renderSessions === "function") {
    renderSessions();
  }
}

function clearTokenRenderState() {
  if (!state) return;
  state.tokenRender = {
    buffer: "",
    text: "",
    messageId: "",
    targetMessageId: "",
    placeholderId: "",
    startedAt: 0,
    lastFlushAt: 0,
    pending: false
  };
}

async function consumeChatStreamStable(payload) {
  if (!state.stream) {
    state.stream = {
      running: false,
      controller: null,
      targetMessageId: "",
      buffer: "",
      startedAt: 0,
      messageId: "",
      placeholderId: "",
    };
  }

  if (state.stream.controller) {
    try {
      state.stream.controller.abort();
    } catch (_) {}
  }

  state.stream.controller = new AbortController();
  state.stream.running = true;
  state.stream.startedAt = Date.now();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream, application/json",
      },
      body: JSON.stringify(payload || {}),
      signal: state.stream.controller.signal,
    });

    const contentType = String(
      response.headers.get("content-type") || ""
    ).toLowerCase();

    if (!response.ok) {
      let raw = "";
      try {
        raw = await response.text();
      } catch (_) {}

      throw new Error(raw || ("Request failed: " + response.status));
    }

    if (contentType.includes("application/json")) {
      const data = await response.json().catch(function () {
        return {};
      });

      if (data.session_id) {
        state.activeSessionId = String(data.session_id || "");
      } else if (data.session && data.session.id) {
        state.activeSessionId = String(data.session.id || "");
      }

      if (Array.isArray(data.sessions)) {
        setSessions(data.sessions);
      }

      if (data.session && Array.isArray(data.session.messages)) {
        state.messages = data.session.messages.map(normalizeMessage);
      } else if (Array.isArray(data.messages)) {
        state.messages = data.messages.map(normalizeMessage);
      } else if (data.assistant_message) {
        upsertMessage(normalizeMessage(data.assistant_message));
      }

      if (Array.isArray(data.artifacts)) {
        state.artifacts = data.artifacts;
        renderArtifacts();
      }

      if (Array.isArray(data.memory)) {
        state.memory = data.memory;
        renderMemory();
      }

      flushTokensNow();
      clearTokenRenderState();
      finishStreamUi({ statusState: "idle", statusText: "Ready" });
      renderSessionList();
      renderChat();
      updateTopbarFromState();
      scrollChatToBottom(true);
      return;
    }

    if (!response.body || typeof response.body.getReader !== "function") {
      throw new Error("Streaming response body is unavailable.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let sawDoneMarker = false;
    let sawAnyEvent = false;

    while (true) {
      const result = await reader.read();
      const done = result.done;
      const value = result.value;

      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (let part of parts) {
        part = String(part || "").trim();
        if (!part) continue;
        if (!part.startsWith("data:")) continue;

        const jsonStr = part.replace(/^data:\s*/, "").trim();
        if (!jsonStr) continue;

        if (jsonStr === "[DONE]") {
          sawDoneMarker = true;
          break;
        }

        try {
          const evt = JSON.parse(jsonStr);
          sawAnyEvent = true;
          handleStreamEvent(evt);
        } catch (error) {
          console.error("stream event parse failed", jsonStr, error);
        }
      }

      if (sawDoneMarker) {
        break;
      }
    }

    const trailing = String(buffer || "").trim();
    if (trailing.startsWith("data:")) {
      const trailingJson = trailing.replace(/^data:\s*/, "").trim();
      if (trailingJson && trailingJson !== "[DONE]") {
        try {
          const evt = JSON.parse(trailingJson);
          sawAnyEvent = true;
          handleStreamEvent(evt);
        } catch (error) {
          console.error("trailing stream event parse failed", trailingJson, error);
        }
      } else if (trailingJson === "[DONE]") {
        sawDoneMarker = true;
      }
    }

flushTokensNow();

if (state.stream && state.stream.targetMessageId) {
  try {
    const latestState = await apiGet("/api/state");
    applyStatePayload(latestState || {});
  } catch (error) {
    console.warn("final state refresh failed", error);
  }

  finalizeStreamMessage({
    message_id: state.stream.targetMessageId,
    text: (
      findMessageById(state.stream.targetMessageId) &&
      findMessageById(state.stream.targetMessageId).text
    ) || "",
    artifacts: Array.isArray(state.artifacts) ? state.artifacts : [],
    memory: Array.isArray(state.memory) ? state.memory : [],
    sessions: Array.isArray(state.sessions) ? state.sessions : [],
    session_id: state.activeSessionId || "",
  });
}

clearTokenRenderState();
finishStreamUi({ statusState: "idle", statusText: "Ready" });
renderChat();
renderSessionList();
renderArtifacts();
renderMemory();
if (typeof renderWeb === "function") {
  renderWeb();
}
updateTopbarFromState();
scrollChatToBottom(true);

  } catch (error) {
    flushTokensNow();
    clearTokenRenderState();

    if (error && error.name === "AbortError") {
      finishStreamUi({ statusState: "idle", statusText: "Stopped" });
      updateTopbarFromState();
      return;
    }

    finishStreamUi({ statusState: "error", statusText: "Error" });
    updateTopbarFromState();
    throw error;
  } finally {
    if (state.stream) {
      state.stream.running = false;
      state.stream.controller = null;
      state.stream.buffer = "";
      state.stream.placeholderId = "";
      state.stream.messageId = "";
      state.stream.targetMessageId = "";
      state.stream.startedAt = 0;
    }
  }
}
function consumeChatStream(payload) {
  return consumeChatStreamStable(payload);
}

function wireArtifactClicks() {
  if (!els.artifactList || els.artifactList.dataset.bound === "1") return;
  els.artifactList.dataset.bound = "1";

  els.artifactList.addEventListener("click", async function (event) {
    const card = event.target.closest("[data-artifact-open]");
    if (!card) return;

    const artifactId = String(
      card.getAttribute("data-artifact-open") || ""
    ).trim();

    if (!artifactId) return;

    await openArtifactFromStateOrBackend(artifactId);
  });
}

function wireArtifactControls() {
  if (!els.artifactList || els.artifactList.dataset.controlsBound === "1") return;
  els.artifactList.dataset.controlsBound = "1";

  els.artifactList.addEventListener("click", function (event) {
    const filterBtn = event.target.closest("[data-artifact-filter]");
    if (!filterBtn) return;

    const nextFilter = String(
      filterBtn.getAttribute("data-artifact-filter") || "all"
    ).trim().toLowerCase();

    if (!state.rail) state.rail = {};
    state.rail.artifactFilter = nextFilter || "all";

    renderArtifacts();
  });

  els.artifactList.addEventListener("input", function (event) {
    const input = event.target.closest("[data-artifact-search]");
    if (!input) return;

    if (!state.rail) state.rail = {};
    state.rail.artifactSearch = String(input.value || "");

    renderArtifacts();
  });
}

function syncArtifactViewerToActiveSession() {
  if (!state.rail || state.rail.tab !== "artifacts") return;

  const activeSessionId = String(state.activeSessionId || "").trim();
  const items = safeArray(state.artifacts).filter(function (item) {
    if (!activeSessionId) return true;
    return String(item.session_id || "").trim() === activeSessionId;
  });

  if (!items.length) {
    state.rail.selectedId = "";
    state.rail.selectedKind = "artifact";

    if (els.railViewer) {
      els.railViewer.hidden = false;
      els.railViewer.innerHTML =
        '<div class="nova-viewer-shell">' +
        '<div class="nova-viewer-empty">' +
        '<div class="nova-viewer-empty-title">No artifact selected</div>' +
        '<div class="nova-viewer-empty-copy">This session does not have any artifacts yet.</div>' +
        "</div>" +
        "</div>";
    }
    return;
  }

  const currentSelectedId = String(state.rail.selectedId || "").trim();
  const selectedStillExists = items.some(function (item) {
    return String(item.id || "").trim() === currentSelectedId;
  });

  if (selectedStillExists && currentSelectedId) {
    openArtifactFromStateOrBackend(currentSelectedId);
    return;
  }

  const firstId = String(items[0].id || "").trim();
  if (!firstId) return;

  state.rail.selectedKind = "artifact";
  state.rail.selectedId = firstId;
  openArtifactFromStateOrBackend(firstId);
}

async function loadState() {
  const payload = await apiGet("/api/state");
  applyStatePayload(payload || {});
  return payload;
}
boot();

if (typeof initShellExtensions === "function") {
  initShellExtensions();
}

if (typeof syncRailReopenVisibility === "function") {
  syncRailReopenVisibility();
}

if (typeof wireSessionClicks === "function") {
  wireSessionClicks();
}

if (typeof wireArtifactClicks === "function") {
  wireArtifactClicks();
}

if (typeof wireArtifactControls === "function") {
  wireArtifactControls();
}

if (typeof wireMemoryClicks === "function") {
  wireMemoryClicks();
}

if (typeof renderMemory === "function") {
  renderMemory();
}

const btn = document.getElementById("rail-reopen-btn");
if (btn) {
  btn.onclick = function () {
    openRail();
  };
}

})();
