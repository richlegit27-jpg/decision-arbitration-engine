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
  };

const state = {
  booted: false,
  activeSessionId: "",
  sessions: [],
  messages: [],
  artifacts: [],
  memory: [],
  pendingUploads: [],
  uploadInFlightCount: 0,
  stream: {
    controller: null,
    running: false,
    messageId: "",
    mode: "",
    placeholderId: "",
    buffer: "",
  },
  rail: {
    tab: "artifacts",
    selectedId: "",
    selectedKind: "",
    artifactSearch: "",
    artifactFilter: "all",
  },
};
  
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
        (data.session && data.session.id) ||
        state.activeSessionId ||
        ""
    );

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

    state.artifacts = safeArray(data.artifacts);
    state.memory = safeArray(data.memory);

    renderSessionList();
    renderChat();
    renderArtifacts();
    renderMemory();
    updateTopbarFromState();
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
      ? '<div class="message-card__body"><span class="message-card__cursor">▋</span></div>'
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
        "</div>"
      );
    })
    .join("");
}

function renderArtifacts() {
  if (!els.artifactList) return;

  const items = safeArray(state.artifacts);
  const searchQuery = String(
    (state.rail && state.rail.artifactSearch) || ""
  ).trim().toLowerCase();
  const activeFilter = String(
    (state.rail && state.rail.artifactFilter) || "all"
  ).trim().toLowerCase();

  if (els.artifactEmpty) {
    els.artifactEmpty.hidden = items.length > 0;
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

  const normalized = items.map(function (item) {
    const viewer = item && typeof item.viewer === "object" ? item.viewer : {};
    const id = String(item.id || "");
    const title = String(viewer.title || item.title || "Artifact");
    const preview = String(viewer.body || item.preview || item.body || "");
    const kind = String(viewer.kind || item.kind || "artifact");
    const kindBadge = getKindBadge(kind);
    const imageUrl = String(
      viewer.image_url || item.image_url || item.url || ""
    ).trim();
    const createdAt = String(item.created_at || item.updated_at || "");

    return {
      raw: item,
      id: id,
      title: title,
      preview: preview,
      kind: kind,
      kindBadge: kindBadge,
      imageUrl: imageUrl,
      createdAt: createdAt,
    };
  });

  const filtered = normalized.filter(function (item) {
    const haystack = (
      String(item.title || "") +
      " " +
      String(item.preview || "") +
      " " +
      String(item.kind || "") +
      " " +
      String(item.kindBadge || "")
    ).toLowerCase();

    const matchesSearch = !searchQuery || haystack.includes(searchQuery);
    const matchesFilter =
      activeFilter === "all" || item.kindBadge === activeFilter;

    return matchesSearch && matchesFilter;
  });

  filtered.sort(function (a, b) {
    const groupDiff = getGroupOrder(a.kindBadge) - getGroupOrder(b.kindBadge);
    if (groupDiff !== 0) return groupDiff;

    const at = Date.parse(a.createdAt || 0) || 0;
    const bt = Date.parse(b.createdAt || 0) || 0;
    return bt - at;
  });

  const groups = {};
  filtered.forEach(function (item) {
    if (!groups[item.kindBadge]) groups[item.kindBadge] = [];
    groups[item.kindBadge].push(item);
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

  if (!filtered.length) {
    els.artifactList.innerHTML =
      controlsHtml +
      '<div class="nova-viewer-empty">' +
      '<div class="nova-viewer-empty-title">No matching artifacts</div>' +
      '<div class="nova-viewer-empty-copy">Try a different search or filter.</div>' +
      "</div>";
    return;
  }

  const orderedGroups = ["image", "web", "chat", "analysis", "artifact"]
    .filter(function (key) {
      return Array.isArray(groups[key]) && groups[key].length > 0;
    })
    .map(function (key) {
      const entries = groups[key];

      const cards = entries
        .map(function (entry) {
          const active =
            state.rail.tab === "artifacts" &&
            state.rail.selectedKind === "artifact" &&
            String(state.rail.selectedId || "") === entry.id;

          const showThumb =
            entry.kindBadge === "image" &&
            entry.imageUrl &&
            !entry.imageUrl.endsWith("#");

          return (
            '<button type="button" class="rail-item' +
            (active ? " is-active" : "") +
            '" data-artifact-open="' +
            escapeHtml(entry.id) +
            '">' +
            (showThumb
              ? '<div class="rail-item__thumb-wrap">' +
                '<img class="rail-item__thumb" src="' +
                escapeHtml(entry.imageUrl) +
                '" alt="' +
                escapeHtml(entry.title) +
                '">' +
                "</div>"
              : "") +
            '<div class="rail-item__title">' +
            escapeHtml(entry.title) +
            "</div>" +
            '<div class="rail-item__preview">' +
            escapeHtml(summarizeText(entry.preview, 100)) +
            "</div>" +
            '<div class="rail-item__meta">' +
            '<span class="rail-badge rail-badge--' +
            escapeHtml(entry.kindBadge) +
            '">' +
            escapeHtml(entry.kindBadge) +
            "</span>" +
            "</div>" +
            "</button>"
          );
        })
        .join("");

      return (
        '<section class="rail-group">' +
        '<div class="rail-group__title">' +
        escapeHtml(getGroupTitle(key)) +
        "</div>" +
        '<div class="rail-group__items">' +
        cards +
        "</div>" +
        "</section>"
      );
    })
    .join("");

  els.artifactList.innerHTML = controlsHtml + orderedGroups;
}

  function renderMemory() {
    if (!els.memoryList) return;

    const items = safeArray(state.memory);
    if (els.memoryEmpty) {
      els.memoryEmpty.hidden = items.length > 0;
    }

    els.memoryList.innerHTML = items.length
      ? items
          .map(function (item) {
            const id = String(item.id || "");
            const text = String(item.text || item.content || item.body || "");
            const kind = String(item.kind || "note");
            const active =
              state.rail.tab === "memory" &&
              state.rail.selectedKind === "memory" &&
              String(state.rail.selectedId || "") === id;

            return (
              '<button type="button" class="rail-item' +
              (active ? " is-active" : "") +
              '" data-memory-open="' +
              escapeHtml(id) +
              '">' +
              '<div class="rail-item__title">' +
              escapeHtml(kind) +
              "</div>" +
              '<div class="rail-item__preview">' +
              escapeHtml(summarizeText(text, 120)) +
              "</div>" +
              "</button>"
            );
          })
          .join("")
      : "";
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
      tokenMessageId = String(messageId || tokenMessageId || "").trim();
      if (!tokenMessageId) return;
      if (tokenFlushQueued) return;

      tokenFlushQueued = true;

      requestAnimationFrame(function () {
        tokenFlushQueued = false;

        const id = String(tokenMessageId || "").trim();
        const chunk = tokenTextBuffer;
        tokenTextBuffer = "";

        if (!id || !chunk) return;

        let msg = findMessageById(id);

        if (!msg) {
          msg = upsertMessage({
            id,
            role: "assistant",
            text: "",
            pending: true,
            streaming: true,
            error: false,
            stopped: false,
            source: "send",
            attachments: [],
            meta: {},
          });
        }

        upsertMessage({
          ...msg,
          text: String(msg.text || "") + String(chunk || ""),
          pending: true,
          streaming: true,
          error: false,
          stopped: false,
        });

	renderChat();
	scrollChatToBottom(true);
      });
    }

    function flushTokensNow() {
      if (!tokenTextBuffer || !tokenMessageId) return;

      let msg = findMessageById(tokenMessageId);

      if (!msg) {
        msg = upsertMessage({
          id: tokenMessageId,
          role: "assistant",
          text: "",
          pending: true,
          streaming: true,
          error: false,
          stopped: false,
          source: "send",
          attachments: [],
          meta: {},
        });
      }

      upsertMessage({
        ...msg,
        text: String(msg.text || "") + String(tokenTextBuffer || ""),
        pending: true,
        streaming: true,
        error: false,
        stopped: false,
      });

      tokenTextBuffer = "";
      renderChat();
      scrollChatToBottom(true);
    }

async function loadState() {
    const payload = await apiGet("/api/state");
    applyStatePayload(payload);
  }

async function consumeChatStreamStable(payload) {
  if (state.stream && state.stream.running) {
    showToast("A generation is already running.", "info");
    return;
  }

  const outgoing = Object.assign({}, payload || {});
  const userText = String(outgoing.user_text || "");
  const memoryUsed = selectRelevantMemory(userText, 3);

  if (memoryUsed.length) {
    const memoryContext = memoryUsed
      .map(function (item, index) {
        return (
          (index + 1) +
          ". [" +
          String(item.kind || "note") +
          "] " +
          memoryText(item)
        );
      })
      .join("\n");

    outgoing.user_text =
      userText +
      "\n\n[Relevant memory context]\n" +
      memoryContext +
      "\n[/Relevant memory context]";
  }

  outgoing.stream = true;

  state.stream = state.stream || {};
  state.stream.running = true;
  state.stream.messageId = "";
  state.stream.placeholderId = "";
  state.stream.buffer = "";
  state.stream.controller = new AbortController();

  let tokenTextBuffer = "";
  let tokenMessageId = "";
  let tokenFlushQueued = false;

  function queueTokenFlush(messageId) {
    tokenMessageId = String(messageId || tokenMessageId || "").trim();
    if (!tokenMessageId) return;
    if (tokenFlushQueued) return;

    tokenFlushQueued = true;

    requestAnimationFrame(function () {
      tokenFlushQueued = false;

      const id = String(tokenMessageId || "").trim();
      const chunk = tokenTextBuffer;
      tokenTextBuffer = "";

      if (!id || !chunk) return;

      let msg = findMessageById(id);

      if (!msg) {
        msg = upsertMessage({
          id: id,
          role: "assistant",
          text: "",
          pending: true,
          streaming: true,
          error: false,
          stopped: false,
          source: "send",
          attachments: [],
          meta: {},
        });
      }

      upsertMessage({
        ...msg,
        text: String(msg.text || "") + String(chunk || ""),
        pending: true,
        streaming: true,
        error: false,
        stopped: false,
      });

      renderChat();
      scrollChatToBottom(true);
    });
  }

  function flushTokensNow() {
    if (!tokenTextBuffer || !tokenMessageId) return;

    let msg = findMessageById(tokenMessageId);

    if (!msg) {
      msg = upsertMessage({
        id: tokenMessageId,
        role: "assistant",
        text: "",
        pending: true,
        streaming: true,
        error: false,
        stopped: false,
        source: "send",
        attachments: [],
        meta: {},
      });
    }

    upsertMessage({
      ...msg,
      text: String(msg.text || "") + String(tokenTextBuffer || ""),
      pending: true,
      streaming: true,
      error: false,
      stopped: false,
    });

    tokenTextBuffer = "";
    renderChat();
    scrollChatToBottom(true);
  }

function handleStreamEvent(event) {
  const type = String((event && event.type) || "");

  if (type === "start") {
    const id = String(
      event.message_id ||
      event.assistant_message_id ||
      makeId("assistant")
    );

    state.stream.messageId = id;
    state.stream.placeholderId = id;
    tokenMessageId = id;
    tokenTextBuffer = "";

    upsertMessage({
      id: id,
      role: "assistant",
      text: "",
      pending: true,
      streaming: true,
      error: false,
      stopped: false,
      source: event.mode || "send",
      attachments: [],
      meta: {},
    });

    renderChat();
    scrollChatToBottom(true);
    return;
  }

  if (type === "token") {
    const id = String(
      event.message_id ||
      event.assistant_message_id ||
      state.stream.messageId ||
      makeId("assistant")
    );

    state.stream.messageId = id;
    state.stream.placeholderId = id;
    tokenMessageId = id;
    tokenTextBuffer += String(event.token || "");

    queueTokenFlush(id);
    return;
  }

  if (type === "final") {
    flushTokensNow();

    const finalMsg = normalizeMessage(
      event.message || {
        id: state.stream.messageId || makeId("assistant"),
        role: "assistant",
        text: "",
      }
    );

    upsertMessage({
      ...finalMsg,
      pending: false,
      streaming: false,
      stopped: false,
      error: false,
    });

      if (Array.isArray(event.memory)) {
        state.memory = event.memory.map(normalizeMemoryItem);
        renderMemory();
      }

    if (Array.isArray(event.artifacts)) {
      state.artifacts = event.artifacts;
      renderArtifacts();
    }

    if (Array.isArray(event.memory)) {
      state.memory = event.memory.map(normalizeMemoryItem);
      renderMemory();
    }

    if (event.session_id) {
      state.activeSessionId = String(event.session_id || "");
    }

    finishStreamUi({
      statusText: "Ready",
      statusState: "idle",
    });
    updateTopbarFromState();
    scrollChatToBottom(true);
    return;
  }

  if (type === "error") {
    flushTokensNow();

    const id = String(
      event.message_id ||
      event.assistant_message_id ||
      state.stream.messageId ||
      makeId("assistant")
    );

    const existing = findMessageById(id);

    upsertMessage({
      ...(existing || {
        id: id,
        role: "assistant",
        text: "",
        attachments: [],
        meta: {},
      }),
      text: String(event.error || "Generation failed."),
      pending: false,
      streaming: false,
      stopped: false,
      error: true,
    });

    renderChat();
    finishStreamUi({
      statusText: "Error",
      statusState: "error",
    });
    updateTopbarFromState();
    scrollChatToBottom(true);
  }
}

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream, application/json",
      },
      body: JSON.stringify(outgoing),
      signal: state.stream.controller.signal,
    });

    if (!response.ok) {
      throw new Error("Request failed: " + response.status);
    }

const contentType = String(response.headers.get("content-type") || "").toLowerCase();

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
    renderChat();
    renderSessionList();

if (!findMessageById(state.stream.messageId || "")) {
  try {
    const fallbackResponse = await fetch("/api/state", {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
      },
    });

    const fallbackData = await fallbackResponse.json().catch(function () {
      return {};
    });

    if (fallbackData && Array.isArray(fallbackData.sessions)) {
      setSessions(fallbackData.sessions);
    }

    if (fallbackData && Array.isArray(fallbackData.memory)) {
      state.memory = fallbackData.memory;
      renderMemory();
    }

    if (fallbackData && Array.isArray(fallbackData.artifacts)) {
      state.artifacts = fallbackData.artifacts;
      renderArtifacts();
    }

    if (
      fallbackData &&
      fallbackData.active_session &&
      Array.isArray(fallbackData.active_session.messages)
    ) {
      state.messages = fallbackData.active_session.messages.map(normalizeMessage);
      renderChat();
      renderSessionList();
      updateTopbarFromState();
      scrollChatToBottom(true);
    }
  } catch (error) {
    warn("post-stream fallback state refresh failed", error);
  }
}

    if (state.stream.running) {
      finishStreamUi({ statusState: "idle", statusText: "Ready" });
      updateTopbarFromState();
    }
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
    state.stream.running = false;
    state.stream.controller = null;
    state.stream.buffer = "";
    state.stream.placeholderId = "";
    state.stream.messageId = "";
  }
}

async function openSessionFromBackend(sessionId) {
  const id = String(sessionId || "").trim();
  if (!id) return;

  await stopStreamBeforeSessionChange();

  const session = safeArray(state.sessions).find(function (item) {
    return String(item.id || "") === id;
  });

  if (!session) {
    showToast("Session not found.", "error");
    return;
  }

  state.activeSessionId = id;
  state.messages = safeArray(session.messages).map(normalizeMessage);

  clearPendingUploads();

  if (els.chatInput) {
    els.chatInput.value = "";
    autoResizeTextarea();
  }

  renderSessionList();
  renderChat();
  renderArtifacts();
  renderMemory();
  updateTopbarFromState();
}

async function openSession(sessionId) {
  return openSessionFromBackend(sessionId);
}

function artifactViewerHtml(artifact) {
  const item = artifact && typeof artifact === "object" ? artifact : {};
  const viewer = item.viewer && typeof item.viewer === "object" ? item.viewer : {};

  const title = String(
    viewer.title ||
      item.title ||
      item.name ||
      "Artifact"
  );

  const kind = String(
    viewer.kind ||
      item.kind ||      
item.viewer_kind ||
      "artifact"
  );

  const body = String(
    viewer.body ||
      item.body ||
      item.content ||
      item.summary ||
      item.preview ||
      ""
  );

  const imageUrl = String(
    viewer.image_url ||
      item.image_url ||
      item.url ||
      ""
  );

  const videoUrl = String(
    viewer.video_url ||
      item.video_url ||
      ""
  );

  const audioUrl = String(
    viewer.audio_url ||
      item.audio_url ||
      ""
  );

  const sourceUrl = String(
    viewer.source_url ||
      item.source_url ||
      ""
  );

  const analysisText = String(
    viewer.analysis_text ||
      item.analysis_text ||
      ""
  );

  const bullets = Array.isArray(viewer.bullets) ? viewer.bullets : [];

  const imageBlock = imageUrl
    ? '<div class="rail-viewer__media">' +
      '<img src="' +
      escapeHtml(imageUrl) +
      '" alt="' +
      escapeHtml(title) +
      '" class="rail-viewer__image">' +
      "</div>"
    : "";

  const videoBlock = videoUrl
    ? '<div class="rail-viewer__media">' +
      '<video controls preload="metadata" class="rail-viewer__video">' +
      '<source src="' +
      escapeHtml(videoUrl) +
      '">' +
      "</video>" +
      "</div>"
    : "";

  const audioBlock = audioUrl
    ? '<div class="rail-viewer__media">' +
      '<audio controls class="rail-viewer__audio">' +
      '<source src="' +
      escapeHtml(audioUrl) +
      '">' +
      "</audio>" +
      "</div>"
    : "";

  const sourceBlock = sourceUrl
    ? '<div class="rail-viewer__links">' +
      '<a href="' +
      escapeHtml(sourceUrl) +
      '" target="_blank" rel="noopener noreferrer" class="rail-viewer__link">Open source</a>' +
      "</div>"
    : "";

  const analysisBlock = analysisText
    ? '<div class="rail-viewer__section">' +
      '<div class="rail-viewer__label">Analysis</div>' +
      '<div class="rail-viewer__body">' +
      renderSafeText(analysisText) +
      "</div>" +
      "</div>"
    : "";

  const bulletsBlock = bullets.length
    ? '<div class="rail-viewer__section">' +
      '<div class="rail-viewer__label">Highlights</div>' +
      '<ul class="rail-viewer__bullets">' +
      bullets
        .map(function (bullet) {
          return "<li>" + escapeHtml(String(bullet || "")) + "</li>";
        })
        .join("") +
      "</ul>" +
      "</div>"
    : "";

  const bodyBlock = body
    ? '<div class="rail-viewer__section">' +
      '<div class="rail-viewer__label">Content</div>' +
      '<div class="rail-viewer__body">' +
      renderSafeText(body) +
      "</div>" +
      "</div>"
    : "";

  return (
    '<div class="rail-viewer__card">' +
    '<div class="rail-viewer__eyebrow">' +
    escapeHtml(kind) +
    "</div>" +
    '<div class="rail-viewer__title">' +
    escapeHtml(title) +
    "</div>" +
    imageBlock +
    videoBlock +
    audioBlock +
    sourceBlock +
    analysisBlock +
    bulletsBlock +
    bodyBlock +
    "</div>"
  );
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

function setRailSelectedItem(kind, itemId) {
  state.rail.selectedKind = String(kind || "");
  state.rail.selectedId = String(itemId || "");

  qsa(".rail-item", els.rail).forEach(function (node) {
    const artifactId = String(node.getAttribute("data-artifact-open") || "");
    const webId = String(node.getAttribute("data-web-open") || "");
    const memoryId = String(node.getAttribute("data-memory-open") || "");
    const isActive =
      (kind === "artifact" && artifactId && artifactId === state.rail.selectedId) ||
      (kind === "web" && webId && webId === state.rail.selectedId) ||
      (kind === "memory" && memoryId && memoryId === state.rail.selectedId);

    node.classList.toggle("is-active", isActive);
  });
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
        '<div class="nova-viewer-empty-copy">This artifact is not available in the current state.</div>' +
        "</div>" +
        "</div>";
    }

    showToast("Artifact not found.", "error");
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
  const text = els.chatInput ? normalizeText(els.chatInput.value) : "";
  const attachments = state.pendingUploads
    .filter(function (item) {
      return String(item.status || "") === "uploaded";
    })
    .map(normalizeAttachment);

  const hasUploading = state.pendingUploads.some(function (item) {
    return String(item.status || "") === "uploading";
  });

  const hasUploadErrors = state.pendingUploads.some(function (item) {
    return String(item.status || "") === "error";
  });

  if (hasUploading) {
    showToast("Uploads are still in progress.", "info");
    throw new Error("Please wait for uploads to finish.");
  }

  if (hasUploadErrors) {
    showToast("Remove failed uploads before sending.", "error");
    throw new Error("Remove failed uploads before sending.");
  }

  if (!text.trim() && !attachments.length) {
    showToast("Nothing to send yet.", "info");
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
      await consumeChatStream(payload);
      showToast("Message sent.", "success");
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

function bindEvents() {
  if (els.composerForm) {
    els.composerForm.addEventListener("submit", handleComposerSubmit);
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
      const files = event && event.target && event.target.files ? event.target.files : [];
      uploadFiles(files).catch(function (error) {
        warn("upload files failed", error);
        showToast(error && error.message ? error.message : "Upload failed.", "error");
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
        showToast(error && error.message ? error.message : "New chat failed.", "error");
      });
    });
  }

  if (els.sessionList) {
    els.sessionList.addEventListener("click", function (event) {
      const sessionButton = event.target.closest("[data-open-session]");
      if (!sessionButton) return;

      event.preventDefault();

      const sessionId = String(
        sessionButton.getAttribute("data-open-session") || ""
      ).trim();

      if (!sessionId) return;

      openSession(sessionId).catch(function (error) {
        warn("open session failed", error);
        showToast(error && error.message ? error.message : "Open session failed.", "error");
      });
    });
  }

  if (els.artifactList) {
    els.artifactList.addEventListener("click", async function (event) {
      const filterButton = event.target.closest("[data-artifact-filter]");
      if (filterButton) {
        event.preventDefault();
        state.rail.artifactFilter = String(
          filterButton.getAttribute("data-artifact-filter") || "all"
        ).trim().toLowerCase();
        renderArtifacts();
        return;
      }

      const artifactButton = event.target.closest("[data-artifact-open]");
      if (!artifactButton) return;

      event.preventDefault();

      const artifactId = String(
        artifactButton.getAttribute("data-artifact-open") || ""
      ).trim();

      if (!artifactId) return;

      try {
        await openArtifactFromStateOrBackend(artifactId);
      } catch (error) {
        warn("open artifact failed", error);
        showToast("Failed to open artifact.", "error");
      }
    });

    els.artifactList.addEventListener("input", function (event) {
      const searchInput = event.target.closest("[data-artifact-search]");
      if (!searchInput) return;

      state.rail.artifactSearch = String(searchInput.value || "");
      renderArtifacts();
    });
  }

  if (els.chatThread) {
    els.chatThread.addEventListener("click", function (event) {
      const copyButton = event.target.closest("[data-copy-message]");
      if (copyButton) {
        const messageId = String(
          copyButton.getAttribute("data-copy-message") || ""
        ).trim();

        if (messageId) {
          copyMessage(messageId).catch(function (error) {
            warn("copy failed", error);
            showToast("Copy failed.", "error");
          });
        }
        return;
      }

      const regenerateButton = event.target.closest("[data-regenerate-message]");
      if (regenerateButton) {
        const targetId = String(
          regenerateButton.getAttribute("data-regenerate-message") || ""
        ).trim();

        if (targetId) {
          regenerateMessage(targetId).catch(function (error) {
            warn("regenerate failed", error);
            showToast(
              error && error.message ? error.message : "Regenerate failed.",
              "error"
            );
          });
        }
      }
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

async function consumeChatStream(payload) {
  return consumeChatStreamStable(payload);
}









boot();

if (typeof initShellExtensions === "function") {
  initShellExtensions();
}

if (typeof syncRailReopenVisibility === "function") {
  syncRailReopenVisibility();
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