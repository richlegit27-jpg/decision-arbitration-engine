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
    return text.slice(0, Math.max(0, max - 1)).trimEnd() + "…";
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
    meta: item.meta && typeof item.meta === "object" ? item.meta : {},

    attachments: safeArray(item.attachments).map(normalizeAttachment),
  };
}

function attachmentSummary(attachment) {
    const name = attachment.filename || attachment.name || "attachment";
    const size = formatBytes(attachment.size);
    return size ? name + " · " + size : name;
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
    artifactList: qs("[data-artifact-list]"),
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

// ==============================
// ATTACHMENT BUTTON → UPLOAD PIPELINE
// ==============================

if (els.attachButton && els.attachInput) {
  els.attachButton.addEventListener("click", function () {
    els.attachInput.click();
  });

  els.attachInput.addEventListener("change", async function (event) {
    const files = Array.from((event.target && event.target.files) || []);
    if (!files.length) return;

    for (const file of files) {
      const pending = {
        id: makeId("upload"),
        filename: file.name,
        stored_name: "",
        url: "",
        mime_type: file.type || "application/octet-stream",
        size: file.size || 0,
        status: "uploading",
        upload_error: "",
      };

      state.pendingUploads.push(pending);
      renderPendingUploads();

      try {
        state.uploadInFlightCount++;

        const form = new FormData();
        form.append("file", file);

        const response = await fetch("/api/upload", {
          method: "POST",
          credentials: "same-origin",
          body: form,
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok || data.ok === false) {
          throw new Error(data.error || "Upload failed");
        }

        pending.status = "uploaded";
        pending.stored_name = String(data.filename || file.name);
        pending.url = resolveUploadUrl(data.url || data.file_url || "");
      } catch (err) {
        pending.status = "error";
        pending.upload_error = String(err.message || err);
        warn("upload failed", err);
      } finally {
        state.uploadInFlightCount--;
        renderPendingUploads();
      }
    }

    // allow re-select same file
    els.attachInput.value = "";
  });
}

if (els.uploadStaging) {
  els.uploadStaging.addEventListener("click", function (event) {
    const btn = event.target.closest("[data-upload-remove]");
    if (!btn) return;

    const id = String(btn.getAttribute("data-upload-remove") || "");
    state.pendingUploads = state.pendingUploads.filter(function (item) {
      return String(item.id) !== id;
    });

    renderPendingUploads();
  });
}

// ==============================
// DRAG + DROP UPLOAD
// ==============================

function uploadSelectedFiles(files) {
  const list = Array.from(files || []);
  if (!list.length) return Promise.resolve();

  return (async function () {
    for (const file of list) {
      const pending = {
        id: makeId("upload"),
        filename: file.name,
        stored_name: "",
        url: "",
        mime_type: file.type || "application/octet-stream",
        size: file.size || 0,
        status: "uploading",
        upload_error: "",
      };

      state.pendingUploads.push(pending);
      renderPendingUploads();

      try {
        state.uploadInFlightCount++;

        const form = new FormData();
        form.append("file", file);

        const response = await fetch("/api/upload", {
          method: "POST",
          credentials: "same-origin",
          body: form,
        });

        const data = await response.json().catch(function () {
          return {};
        });

        if (!response.ok || data.ok === false) {
          throw new Error(data.error || "Upload failed");
        }

        pending.status = "uploaded";
        pending.stored_name = String(data.filename || file.name);
        pending.url = resolveUploadUrl(data.url || data.file_url || "");
      } catch (err) {
        pending.status = "error";
        pending.upload_error = String(err && err.message ? err.message : err);
        warn("upload failed", err);
      } finally {
        state.uploadInFlightCount = Math.max(0, state.uploadInFlightCount - 1);
        renderPendingUploads();
      }
    }
  })();
}

// ==============================
// PASTE IMAGE UPLOAD
// ==============================

document.addEventListener("paste", function (event) {
  const items = Array.from((event.clipboardData && event.clipboardData.items) || []);
  if (!items.length) return;

  const files = items
    .filter(function (item) {
      return item && item.kind === "file";
    })
    .map(function (item) {
      return item.getAsFile();
    })
    .filter(Boolean);

  if (!files.length) return;

  uploadSelectedFiles(files).catch(function (error) {
    warn("paste upload failed", error);
    showToast("Paste upload failed", "error");
  });
});

if (els.chatThread) {
  ["dragenter", "dragover"].forEach(function (eventName) {
    els.chatThread.addEventListener(eventName, function (event) {
      event.preventDefault();
      event.stopPropagation();
      els.chatThread.classList.add("is-dragover");
    });
  });

  ["dragleave", "dragend", "drop"].forEach(function (eventName) {
    els.chatThread.addEventListener(eventName, function (event) {
      event.preventDefault();
      event.stopPropagation();
      els.chatThread.classList.remove("is-dragover");
    });
  });

  els.chatThread.addEventListener("drop", function (event) {
    const files = Array.from((event.dataTransfer && event.dataTransfer.files) || []);
    if (!files.length) return;

    uploadSelectedFiles(files).catch(function (error) {
      warn("drag-drop upload failed", error);
      showToast("Drop upload failed", "error");
    });
  });
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
      (data.active_session && data.active_session.id) ||
      (data.session && data.session.id) ||
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
  } else if (data.assistant_message) {
    upsertMessage(normalizeMessage(data.assistant_message));
  }

  state.artifacts = safeArray(data.artifacts);
  state.memory = safeArray(data.memory);
  state.web = safeArray(data.web);

  renderSessionList();
  renderChat();
  renderArtifacts();
  renderMemory();

  if (typeof renderWeb === "function") {
    renderWeb();
  }

  updateTopbarFromState();
}

// 🔥 send state to right panel (CRITICAL LINK)
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
        '" aria-label="Remove attachment">×</button>'
      : "";

    const statusHtml =
      status === "uploading"
        ? '<span class="nova-upload-chip__status">Uploading…</span>'
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

  const subText = sub.join(" · ");

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
    '<div class="message-attachment__icon">📎</div>' +
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

  const attachmentsHtml = attachments.length
    ? '<div class="message-attachments">' +
      attachments.map(renderAttachmentBlock).join("") +
      "</div>"
    : "";

  const bodyHtml = message.text
    ? '<div class="message-card__body">' + renderSafeText(message.text) + "</div>"
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
        (session.pinned ? '<div class="nova-session-card-pin">📌</div>' : "") +
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
  if (!els.artifactList) return;

  const activeSessionId = String(state.activeSessionId || "").trim();
  const searchQuery = String(
    (state.rail && state.rail.artifactSearch) || ""
  ).trim().toLowerCase();
  const activeFilter = String(
    (state.rail && state.rail.artifactFilter) || "all"
  ).trim().toLowerCase();

  const allArtifacts = safeArray(state.artifacts);

  const sessionArtifacts = allArtifacts.filter(function (item) {
    if (!activeSessionId) return true;
    return String(item && item.session_id ? item.session_id : "").trim() === activeSessionId;
  });

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

let tokenTextBuffer = null;
let tokenMessageId = null;
let tokenFlushQueued = false;

function queueTokenFlush(messageId) {
  return;
}

function flushTokensNow() {
  return;
}

function finalizeStreamMessage(payload) {
  const data = payload && typeof payload === "object" ? payload : {};

  if (!state.stream) {
    state.stream = {
      running: false,
      controller: null,
      targetMessageId: "",
      buffer: "",
      startedAt: 0,
    };
  }

  const targetId = String(
    state.stream.targetMessageId ||
    data.message_id ||
    data.id ||
    ""
  ).trim();

  const finalText = String(
    data.text ||
    data.response ||
    data.output_text ||
    data.assistant_text ||
    state.stream.buffer ||
    ""
  );

  const attachments = Array.isArray(data.attachments) ? data.attachments : [];
  const meta =
    data.meta && typeof data.meta === "object"
      ? data.meta
      : {};

  if (targetId) {
    upsertMessage(normalizeMessage({
      id: targetId,
      role: "assistant",
      text: finalText,
      streaming: false,
      pending: false,
      error: false,
      stopped: true,
      attachments: attachments,
      meta: meta,
    }));
  }

  state.stream.running = false;
  state.stream.controller = null;
  state.stream.targetMessageId = "";
  state.stream.buffer = "";
  state.stream.startedAt = 0;

  if (data.session && Array.isArray(data.session.messages)) {
    state.messages = data.session.messages.map(normalizeMessage);
  } else if (Array.isArray(data.messages)) {
    state.messages = data.messages.map(normalizeMessage);
  }

  if (Array.isArray(data.artifacts)) {
    state.artifacts = data.artifacts;
  }

  if (Array.isArray(data.memory)) {
    state.memory = data.memory;
  }

  renderChat();
  renderArtifacts();
  renderMemory();
  updateTopbarFromState();
  scrollChatToBottom();
}

function handleStreamEvent(event) {
  const payload = event && typeof event === "object" ? event : {};

  const type = String(
    payload.type ||
    payload.event ||
    payload.kind ||
    ""
  ).trim().toLowerCase();

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
    state.stream.buffer = String(state.stream.buffer || "") + delta;

    upsertMessage(normalizeMessage({
      id: targetId,
      role: "assistant",
      text: state.stream.buffer,
      streaming: true,
      pending: false,
      error: false,
      stopped: false,
      attachments: [],
      meta: {},
    }));

    renderChat();
    scrollChatToBottom(true);
    return;
  }

  if (
    type === "final" ||
    type === "done" ||
    type === "complete" ||
    payload.done === true ||
    payload.final === true
  ) {
    finalizeStreamMessage(payload);
    return;
  }

  if (payload.error) {
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

  if (!state.stream.controller) {
    state.stream.controller = new AbortController();
  }

  state.stream.running = true;
  state.stream.buffer = state.stream.buffer || "";

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

    if (!response.ok) {
      throw new Error("Request failed: " + response.status);
    }

    const contentType = String(
      response.headers.get("content-type") || ""
    ).toLowerCase();

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

      renderSessionList();
      renderChat();
      updateTopbarFromState();
      scrollChatToBottom(true);
      finishStreamUi({ statusState: "idle", statusText: "Ready" });
      return;
    }

    if (!response.body || typeof response.body.getReader !== "function") {
      throw new Error("Streaming response body is unavailable.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

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
        if (!part.startsWith("data:")) continue;

        const jsonStr = part.replace(/^data:\s*/, "");

        if (!jsonStr || jsonStr === "[DONE]") continue;

        try {
          const evt = JSON.parse(jsonStr);
          handleStreamEvent(evt);
        } catch (error) {
          warn("stream event parse failed", error);
        }
      }
    }

    if (buffer.trim().startsWith("data:")) {
      try {
        const trailing = JSON.parse(
          buffer.trim().replace(/^data:\s*/, "")
        );
        handleStreamEvent(trailing);
      } catch (error) {
        warn("trailing stream event parse failed", error);
      }
    }

    flushTokensNow();
    finalizeStreamMessage({});
    renderChat();
    renderSessionList();
    updateTopbarFromState();
    scrollChatToBottom(true);
    finishStreamUi({ statusState: "idle", statusText: "Ready" });
  } catch (error) {
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
    }
  }
}

async function openSession(sessionId) {
  return openSessionFromBackend(sessionId);
}

function artifactViewerHtml(artifact) {
  if (!artifact || typeof artifact !== "object") {
    return (
      '<div class="nova-viewer-shell">' +
      '<div class="nova-viewer-empty">' +
      '<div class="nova-viewer-empty-title">No artifact selected</div>' +
      '<div class="nova-viewer-empty-copy">Pick an artifact from the right panel to inspect it here.</div>' +
      "</div>" +
      "</div>"
    );
  }

  const viewer =
    artifact && typeof artifact.viewer === "object" && artifact.viewer
      ? artifact.viewer
      : {};

  const meta =
    artifact && typeof artifact.meta === "object" && artifact.meta
      ? artifact.meta
      : {};

  const kind = String(viewer.kind || artifact.kind || "artifact").trim();

  const title = String(
    viewer.title || artifact.title || artifact.name || "Untitled artifact"
  ).trim();

  const body = String(
    viewer.body ||
      artifact.body ||
      artifact.content ||
      artifact.summary ||
      artifact.preview ||
      ""
  ).trim();

  const preview = String(artifact.preview || "").trim();

  const sourceUrl = String(
    viewer.source_url ||
      artifact.source_url ||
      meta.source_url ||
      meta.url ||
      ""
  ).trim();

  const imageUrl = String(
    viewer.image_url ||
      artifact.image_url ||
      meta.image_url ||
      ""
  ).trim();

  const videoUrl = String(
    viewer.video_url ||
      artifact.video_url ||
      meta.video_url ||
      ""
  ).trim();

  const audioUrl = String(
    viewer.audio_url ||
      artifact.audio_url ||
      meta.audio_url ||
      ""
  ).trim();

  const analysisText = String(
    viewer.analysis_text ||
      artifact.analysis_text ||
      meta.analysis_text ||
      ""
  ).trim();

  const bullets = Array.isArray(viewer.bullets)
    ? viewer.bullets
    : Array.isArray(meta.bullets)
    ? meta.bullets
    : [];

  const cleanBullets = bullets
    .map(function (item) {
      return String(item || "").trim();
    })
    .filter(Boolean);

  const prettyKind = kind
    .replace(/[_\-]+/g, " ")
    .replace(/\b\w/g, function (m) {
      return m.toUpperCase();
    });

  const subtitle = String(
    artifact.session_id ? prettyKind + " • session artifact" : prettyKind
  ).trim();

  const sourceBadge = sourceUrl
    ? '<a class="nova-artifact-viewer-source-badge" href="' +
      escapeHtml(sourceUrl) +
      '" target="_blank" rel="noreferrer noopener">Source</a>'
    : "";

  const whenText = String(
    artifact.updated_at || artifact.created_at || ""
  ).trim();

  let whenLabel = "";
  if (whenText) {
    try {
      const d = new Date(whenText);
      whenLabel = Number.isNaN(d.getTime())
        ? whenText
        : d.toLocaleString([], {
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
          });
    } catch (error) {
      whenLabel = whenText;
    }
  }

  let html = "";

  html += '<article class="nova-artifact-viewer-shell">';

  html += '<header class="nova-artifact-viewer-header">';

  html += '<div class="nova-artifact-viewer-meta">';
  html +=
    '<span class="nova-artifact-viewer-kind">' +
    escapeHtml(prettyKind) +
    "</span>";
  if (whenLabel) {
    html +=
      '<span class="nova-artifact-viewer-date">' +
      escapeHtml(whenLabel) +
      "</span>";
  }
  html += sourceBadge;
  html += "</div>";

  html += '<div class="nova-artifact-viewer-title-wrap">';
  html +=
    '<h3 class="nova-artifact-viewer-title">' +
    escapeHtml(title) +
    "</h3>";
  html +=
    '<div class="nova-artifact-viewer-subtitle">' +
    escapeHtml(subtitle) +
    "</div>";
  html += "</div>";

  if (sourceUrl) {
    html += '<div class="nova-artifact-viewer-actions">';
    html +=
      '<a class="nova-artifact-viewer-link" href="' +
      escapeHtml(sourceUrl) +
      '" target="_blank" rel="noreferrer noopener">Open source</a>';
    html += "</div>";
  }

  html += "</header>";

  if (imageUrl) {
    html += '<div class="nova-artifact-viewer-media">';
    html +=
      '<img class="nova-artifact-viewer-image" src="' +
      escapeHtml(imageUrl) +
      '" alt="' +
      escapeHtml(title) +
      '" loading="lazy" />';
    html += "</div>";
  }

  if (videoUrl) {
    html += '<div class="nova-artifact-viewer-media">';
    html +=
      '<video class="nova-artifact-viewer-video" controls preload="metadata" src="' +
      escapeHtml(videoUrl) +
      '"></video>';
    html += "</div>";
  }

  if (audioUrl) {
    html += '<div class="nova-artifact-viewer-media">';
    html +=
      '<audio class="nova-artifact-viewer-audio" controls preload="metadata" src="' +
      escapeHtml(audioUrl) +
      '"></audio>';
    html += "</div>";
  }

  if (analysisText) {
    html += '<section class="nova-artifact-viewer-section">';
    html +=
      '<div class="nova-artifact-viewer-section-title">Analysis</div>';
    html += '<div class="nova-artifact-viewer-copy">';
    html += escapeHtml(analysisText).replace(/\n/g, "<br>");
    html += "</div>";
    html += "</section>";
  }

  if (cleanBullets.length) {
    html += '<section class="nova-artifact-viewer-section">';
    html +=
      '<div class="nova-artifact-viewer-section-title">Highlights</div>';
    html += '<ul class="nova-artifact-viewer-bullets">';
    html += cleanBullets
      .map(function (item) {
        return "<li>" + escapeHtml(item) + "</li>";
      })
      .join("");
    html += "</ul>";
    html += "</section>";
  }

  if (body) {
    html += '<section class="nova-artifact-viewer-section">';
    html +=
      '<div class="nova-artifact-viewer-section-title">Details</div>';
    html += '<div class="nova-artifact-viewer-copy">';
    html += escapeHtml(body).replace(/\n/g, "<br>");
    html += "</div>";
    html += "</section>";
  }

  if (preview && preview !== body) {
    html += '<div class="nova-artifact-viewer-preview">';
    html += escapeHtml(preview).replace(/\n/g, "<br>");
    html += "</div>";
  }

  html += "</article>";

  return html;
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

function findNewestImageArtifact(items) {
  return safeArray(items).find(function (item) {
    const artifact = item && typeof item === "object" ? item : {};
    const viewer = artifact.viewer && typeof artifact.viewer === "object" ? artifact.viewer : {};

    const kind = String(viewer.kind || artifact.kind || "");
    const imageUrl = String(viewer.image_url || artifact.image_url || "");

    return kind === "image_generation" || Boolean(imageUrl);
  }) || null;
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
    if (state.rail) {
      state.rail.selectedId = "";
      state.rail.selectedKind = "";
    }

    openRail();
    setRailTab("artifacts");

    if (els.railViewer) {
      els.railViewer.hidden = false;
      els.railViewer.innerHTML =
        '<div class="nova-viewer-shell">' +
        '<div class="nova-viewer-empty">' +
        '<div class="nova-viewer-empty-title">Artifact not found</div>' +
        '<div class="nova-viewer-empty-copy">This artifact is no longer available in the current state.</div>' +
        "</div>" +
        "</div>";
    }

    if (els.railTitle) {
      els.railTitle.textContent = "Artifacts";
    }

    if (els.railSubtitle) {
      els.railSubtitle.textContent = "Unavailable item";
    }

    showToast("Artifact not found.", "error");
    return;
  }

  const artifactSessionId = String(
    artifact.session_id ||
      (artifact.viewer && artifact.viewer.session_id) ||
      ""
  ).trim();

  const currentSessionId = String(state.activeSessionId || "").trim();

  if (artifactSessionId && artifactSessionId !== currentSessionId) {
    try {
      state.pendingArtifactOpenId = id;
      await openSessionFromBackend(artifactSessionId);

      artifact =
        typeof findArtifactById === "function" ? findArtifactById(id) : null;

      if (!artifact) {
        const payload = await apiGet("/api/state");
        applyStatePayload(payload);
        artifact =
          typeof findArtifactById === "function" ? findArtifactById(id) : null;
      }
    } catch (error) {
      warn("artifact session open failed", error);
      showToast("Session switch failed.", "error");
      return;
    }
  }

  if (!artifact) {
    if (els.railViewer) {
      els.railViewer.hidden = false;
      els.railViewer.innerHTML =
        '<div class="nova-viewer-shell">' +
        '<div class="nova-viewer-empty">' +
        '<div class="nova-viewer-empty-title">Artifact unavailable</div>' +
        '<div class="nova-viewer-empty-copy">The session switched, but this artifact could not be reopened.</div>' +
        "</div>" +
        "</div>";
    }
    showToast("Artifact could not be reopened after session switch.", "error");
    return;
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
      artifact.viewer && typeof artifact.viewer === "object"
        ? artifact.viewer
        : {};
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
    name: file && file.name ? file.name : "upload",
    filename: file && file.name ? file.name : "upload",
    mime_type: file && file.type ? file.type : "application/octet-stream",
    size: file && typeof file.size === "number" ? file.size : 0,
    status: "uploading",
  });

  const formData = new FormData();
  formData.append("file", file);

    state.uploadInFlightCount += 1;
    setBusyUi(state.stream.running);

    try {
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

           state.pendingUploads = state.pendingUploads.filter(function (item) {
        return String(item.id) !== String(tempId);
      });

      const uploadedAttachment = Object.assign({}, normalizeAttachment(data.attachment || data), {
        status: "uploaded",
        upload_error: "",
      });

      setPendingUploadItem(uploadedAttachment);
      showToast("Uploaded: " + (uploadedAttachment.filename || uploadedAttachment.name || "attachment"), "success");
      return normalizeAttachment(uploadedAttachment); 

    } catch (error) {
      warn("upload failed", error);

      const errorText = error && error.message ? error.message : "Upload failed.";

      setPendingUploadItem({
        id: tempId,
        name: file && file.name ? file.name : "upload",
        filename: file && file.name ? file.name : "upload",
        mime_type: file && file.type ? file.type : "application/octet-stream",
        size: file && typeof file.size === "number" ? file.size : 0,
        status: "error",
        upload_error: errorText,
      });

           showToast("Upload failed: " + (file && file.name ? file.name : "attachment"), "error");
      throw error;   

    } finally {
      state.uploadInFlightCount = Math.max(0, state.uploadInFlightCount - 1);
      setBusyUi(state.stream.running);
      renderPendingUploads();
    }
  }


async function uploadOneFile(file) {
  const tempId = makeId("att_local");
  setPendingUploadItem({
    id: tempId,
    name: file && file.name ? file.name : "upload",
    filename: file && file.name ? file.name : "upload",
    mime_type: file && file.type ? file.type : "application/octet-stream",
    size: file && typeof file.size === "number" ? file.size : 0,
    status: "uploading",
  });

  const formData = new FormData();
  formData.append("file", file);

    state.uploadInFlightCount += 1;
    setBusyUi(state.stream.running);

    try {
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

           state.pendingUploads = state.pendingUploads.filter(function (item) {
        return String(item.id) !== String(tempId);
      });

      const uploadedAttachment = Object.assign({}, normalizeAttachment(data.attachment || data), {
        status: "uploaded",
        upload_error: "",
      });

      setPendingUploadItem(uploadedAttachment);
      showToast("Uploaded: " + (uploadedAttachment.filename || uploadedAttachment.name || "attachment"), "success");
      return normalizeAttachment(uploadedAttachment); 

    } catch (error) {
      warn("upload failed", error);

      const errorText = error && error.message ? error.message : "Upload failed.";

      setPendingUploadItem({
        id: tempId,
        name: file && file.name ? file.name : "upload",
        filename: file && file.name ? file.name : "upload",
        mime_type: file && file.type ? file.type : "application/octet-stream",
        size: file && typeof file.size === "number" ? file.size : 0,
        status: "error",
        upload_error: errorText,
      });

           showToast("Upload failed: " + (file && file.name ? file.name : "attachment"), "error");
      throw error;   

    } finally {
      state.uploadInFlightCount = Math.max(0, state.uploadInFlightCount - 1);
      setBusyUi(state.stream.running);
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

    applyStatePayload(data || {});

    if (data && data.session && data.session.id) {
      state.activeSessionId = String(data.session.id || "");
    } else if (data && data.session_id) {
      state.activeSessionId = String(data.session_id || "");
    }

    renderSessionList();
    renderChat();
    renderArtifacts();
    renderMemory();
    updateTopbarFromState();
    scrollChatToBottom(true);

    finishStreamUi({
      statusText: "Ready",
      statusState: "idle",
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
  const text = String((els.chatInput && els.chatInput.value) || "").trim();
  const attachments = state.pendingUploads.slice();

  if (!text && !attachments.length) {
    return;
  }

  if (!state.activeSessionId) {
    const created = await apiPost("/api/sessions/new", {});
    if (created && created.session && created.session.id) {
      state.activeSessionId = String(created.session.id);
    } else if (created && created.active_session_id) {
      state.activeSessionId = String(created.active_session_id);
    }
    await loadState();
  }

  appendUserMessageLocal(text, attachments);

  if (els.chatInput) {
    els.chatInput.value = "";
    autoResizeTextarea();
  }

  clearPendingUploads();

  const payload = getSendPayload({
    user_text: text,
    attachments: attachments,
  });

  try {
    const isImageCommand = String(text || "").trim().toLowerCase().startsWith("/image");

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

      renderChat();
      scrollChatToBottom(true);

      payload.placeholder_id = pendingAssistantId;
      await consumeChatStream(payload);
     
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

  await consumeChatStream(payload);
}

function stopGeneration() {
  if (!state.stream.running || !state.stream.controller) return;
  try {
    state.stream.controller.abort();
    showToast("Generation stopped.", "info");
  } catch (_) {}
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
  els.ttsToggleButton.textContent = muted ? "🔇" : "🔊";

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

  if (els.sendButton) {
    els.sendButton.addEventListener("click", function (event) {
      event.preventDefault();
      handleComposerSubmit(event);
    });
  }

  if (els.chatInput) {
    els.chatInput.addEventListener("input", autoResizeTextarea);
    els.chatInput.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleComposerSubmit(event);
      }
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
  return text.slice(0, max) + "…";
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
    (item.session_id ? " · " + escapeHtml(item.session_id) : "") +
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