(function () {
  "use strict";

  if (window.NovaComposerBundle) return;

  function log() {
    try {
      console.log("[NovaComposerBundle]", ...arguments);
    } catch (_) {}
  }

function applyBackendSessionState(payload, explicitSessionId) {
  const data = payload && typeof payload === "object" ? payload : {};

  if (explicitSessionId && typeof data === "object" && data) {
    data.active_session_id = data.active_session_id || explicitSessionId;
  }

  if (typeof hydrateFromState === "function") {
    hydrateFromState(data || {});
    return;
  }

  const resolvedSession =
    data.session && typeof data.session === "object"
      ? data.session
      : data.active_session && typeof data.active_session === "object"
        ? data.active_session
        : null;

  const resolvedSessionId = String(
    explicitSessionId ||
    data.active_session_id ||
    (resolvedSession && resolvedSession.id) ||
    data.session_id ||
    state.activeSessionId ||
    ""
  ).trim();

  if (resolvedSessionId) {
    state.activeSessionId = resolvedSessionId;
  }

  if (resolvedSession && Array.isArray(resolvedSession.messages)) {
    const incoming = resolvedSession.messages.map(normalizeMessage);

    if (incoming.length > 0 || !state.messages || state.messages.length === 0) {
      state.messages = incoming;
    } else {
      console.warn("[NovaComposerBundle] skipped resolvedSession empty overwrite");
    }
  } else if (Array.isArray(data.messages)) {
    const incoming = data.messages.map(normalizeMessage);

    if (incoming.length > 0 || !state.messages || state.messages.length === 0) {
      state.messages = incoming;
    } else {
      console.warn("[NovaComposerBundle] skipped data.messages empty overwrite");
    }
  }

  if (Array.isArray(data.artifacts)) {
    state.artifacts = safeArray(data.artifacts);
  }

  if (Array.isArray(data.memory)) {
    state.memory = data.memory;
  }

  renderChat();
  renderArtifacts();
  renderMemory();
  updateTopbarFromState();
  scrollChatToBottom(true);
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

      const stateRes = await fetch("/api/state", {
        credentials: "same-origin",
        cache: "no-store",
      });
      const data = await stateRes.json();

      applyBackendSessionState(data || {}, targetSessionId);

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
      console.warn("jumpToSessionAndSync failed", e);
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

function linkifyText(text) {
  const safe = escapeHtml(String(text || ""));

  return safe.replace(
    /(https?:\/\/[^\s<]+)/g,
    '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
  );
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
  if (!raw || typeof raw !== "object") return null;

  if (raw.ok === true && raw.assistant_message) {
    raw = raw.assistant_message;
  }

  const item = raw;

  const role = String(item.role || "assistant");
  const kind = String(item.kind || "");

  const text = normalizeText(
    (item.ui && item.ui.message && item.ui.message.text) ||
    item.text ||
    item.content ||
    item.body ||
    item.message ||
    ""
  ).trim();

  if (role === "assistant" && !text && kind !== "working_context") {
    // keep empty assistant messages
  }

  if (
    typeof text === "string" &&
    (
      text.includes("'ok': True") ||
      text.includes('"ok": true') ||
      text.includes("'assistant_message':") ||
      text.includes('"assistant_message":')
    )
  ) {
    return null;
  }

  // 🔥 HARD META PRESERVE (this is the key)
  const meta =
    item.meta ||
    raw.meta ||
    (raw.assistant_message && raw.assistant_message.meta) ||
    {};

  return {
    id: item.id || makeId("msg"),
    role: role,
    kind: kind,
    text: text,
    attachments: Array.isArray(item.attachments) ? item.attachments : [],
    meta: meta, // ← FIXED
    created_at: item.created_at || new Date().toISOString(),
    pending: Boolean(item.pending),
    streaming: Boolean(item.streaming),
    error: Boolean(item.error),
    stopped: Boolean(item.stopped),
  };
}
function buildWorkingContextFromWorkingState(rawState) {
  const state = rawState && typeof rawState === "object" ? rawState : {};

  const normalizedState = {
    active_task: typeof state.active_task === "string" ? state.active_task : "",
    current_file: typeof state.current_file === "string" ? state.current_file : "",
    current_bug: typeof state.current_bug === "string" ? state.current_bug : "",
    last_success: typeof state.last_success === "string" ? state.last_success : "",
    next_move: typeof state.next_move === "string" ? state.next_move : "",
    checkpoint: typeof state.checkpoint === "string" ? state.checkpoint : "",
    updated_at: typeof state.updated_at === "string" ? state.updated_at : "",
  };

  const lines = [];

  if (normalizedState.active_task) {
    lines.push("Active task: " + normalizedState.active_task);
  }
  if (normalizedState.current_file) {
    lines.push("Current file: " + normalizedState.current_file);
  }
  if (normalizedState.current_bug) {
    lines.push("Current bug: " + normalizedState.current_bug);
  }
  if (normalizedState.last_success) {
    lines.push("Last success: " + normalizedState.last_success);
  }
  if (normalizedState.next_move) {
    lines.push("Next move: " + normalizedState.next_move);
  }
  if (normalizedState.checkpoint) {
    lines.push("Checkpoint: " + normalizedState.checkpoint);
  }

  return {
    show: lines.length > 0,
    text: lines.length ? "Working context:\n- " + lines.join("\n- ") : "",
    state: normalizedState,
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
    executionPanel: document.querySelector('[data-execution-panel]'),
    executionEmpty: document.querySelector('[data-execution-empty]'),
    executionContent: document.querySelector('[data-execution-content]'),
    execRunStepButton: document.querySelector('[data-exec-run-step]'),
    execRunAllButton: document.querySelector('[data-exec-run-all]'),
    execStopButton: document.querySelector('[data-exec-stop]'),
    execShowPlanButton: document.querySelector('[data-exec-show-plan]'),
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

  workingContext: {
    show: false,
    collapsed: false,
    text: "",
    state: {
      active_task: "",
      current_file: "",
      current_bug: "",
      last_success: "",
      next_move: "",
      checkpoint: "",
      updated_at: "",
    },
  },

  stream: {
    controller: null,
    running: false,
    messageId: "",
    mode: "",
    placeholderId: "",
    buffer: "",
  },

  execution: {
    artifactId: "",
    goal: "",
    status: "",
    progress: 0,
    currentStep: "",
    currentStepIndex: 0,
    steps: [],
    stepResults: [],
    raw: null,
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
  enabled: true,
  playing: false,
  audio: null,
  lastAutoMessageId: "",
},

  rail: {
    tab: "artifacts",
    selectedId: "",
    selectedKind: "",
    artifactSearch: "",
    artifactFilter: "all",
  },
};

function updateTtsToggleUi() {
  if (!els.ttsToggleButton) return;

  if (!state.tts) {
    state.tts = {
      enabled: true,
      playing: false,
      audio: null,
      lastAutoMessageId: "",
    };
  }

  const enabled = state.tts.enabled !== false;
  const playing = !!state.tts.playing;

  els.ttsToggleButton.classList.toggle("is-muted", !enabled);
  els.ttsToggleButton.classList.toggle("is-playing", playing);

  if (playing) {
    els.ttsToggleButton.textContent = "⏹";
    els.ttsToggleButton.setAttribute("aria-label", "Stop voice reply");
    els.ttsToggleButton.setAttribute("title", "Stop voice reply");
    return;
  }

  els.ttsToggleButton.textContent = enabled ? "🔊" : "🔇";
  els.ttsToggleButton.setAttribute(
    "aria-label",
    enabled ? "Voice replies on" : "Voice replies muted"
  );
  els.ttsToggleButton.setAttribute(
    "title",
    enabled ? "Voice replies on" : "Voice replies muted"
  );
}

function stopCurrentTtsPlayback() {
  if (!state.tts) return;

  try {
    if (state.tts.audio) {
      state.tts.audio.pause();
      state.tts.audio.currentTime = 0;
    }
  } catch (_) {}

  state.tts.playing = false;
  state.tts.audio = null;
  updateTtsToggleUi();
}

async function playVoiceReplyFromText(text) {
  const content = String(text || "").trim();
  if (!content) return;
  if (!state.tts || state.tts.enabled === false) return;

  try {
    stopCurrentTtsPlayback();

    const result = await requestVoiceReply(content);
    if (!result || !result.url) return;

    const audio = new Audio(result.url);
    state.tts.audio = audio;
    state.tts.playing = true;
    updateTtsToggleUi();

    audio.addEventListener("ended", function () {
      if (state.tts && state.tts.audio === audio) {
        state.tts.playing = false;
        state.tts.audio = null;
        updateTtsToggleUi();
      }
    });

    audio.addEventListener("pause", function () {
      if (state.tts && state.tts.audio === audio && !audio.ended) {
        state.tts.playing = false;
        state.tts.audio = null;
        updateTtsToggleUi();
      }
    });

    await audio.play();
  } catch (err) {
    console.error("TTS failed:", err);
    if (state.tts) {
      state.tts.playing = false;
      state.tts.audio = null;
    }
    updateTtsToggleUi();
  }
}

async function autoPlayTtsForAssistantMessage(message) {
  const text = String(
    (message && (message.text || message.content || message.body)) || ""
  ).trim();
  const messageId = String((message && message.id) || "").trim();

  if (!text) return;
  if (!state.tts || state.tts.enabled === false) return;
  if (messageId && state.tts.lastAutoMessageId === messageId) return;

  if (messageId) {
    state.tts.lastAutoMessageId = messageId;
  }

  await playVoiceReplyFromText(text);
}

if (els.ttsToggleButton) {
  els.ttsToggleButton.addEventListener("click", async function (event) {
    event.preventDefault();

    if (!state.tts) {
      state.tts = {
        enabled: true,
        playing: false,
        audio: null,
        lastAutoMessageId: "",
      };
    }

    if (state.tts.playing && state.tts.audio) {
      stopCurrentTtsPlayback();
      return;
    }

    state.tts.enabled = !state.tts.enabled;
    updateTtsToggleUi();

    if (state.tts.enabled) {
      const lastMsg = (state.messages || [])
        .slice()
        .reverse()
        .find(function (m) {
          return m && m.role === "assistant" && String(m.text || "").trim();
        });

      if (lastMsg && lastMsg.text) {
        await playVoiceReplyFromText(lastMsg.text);
      }
    }
  });
}

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

function getSessionArtifactsForRail() {
  const activeSessionId = String(state.activeSessionId || "").trim();
  const allArtifacts = safeArray(state.artifacts);

  let sessionArtifacts = allArtifacts.filter(function (item) {
    if (!activeSessionId) return true;
    return String(item && item.session_id ? item.session_id : "").trim() === activeSessionId;
  });

  if (!sessionArtifacts.length && allArtifacts.length) {
    sessionArtifacts = allArtifacts.slice();
  }

  return sessionArtifacts;
}

function railHasRealMemory() {
  return safeArray(state.memory).length > 0;
}

function syncRailTruth() {
  const hasArtifacts = getSessionArtifactsForRail().length > 0;
  const hasMemory = railHasRealMemory();

  if (state.rail.tab === "web") {
    state.rail.tab = hasArtifacts ? "artifacts" : (hasMemory ? "memory" : "artifacts");
  }

  if (state.rail.tab === "memory" && !hasMemory) {
    state.rail.tab = hasArtifacts ? "artifacts" : "artifacts";
  }

  if (!state.rail.tab) {
    state.rail.tab = hasArtifacts ? "artifacts" : (hasMemory ? "memory" : "artifacts");
  }

  qsa("[data-rail-tab]").forEach(function (tabEl) {
    const tabName = String(tabEl.getAttribute("data-rail-tab") || "").trim().toLowerCase();

if (tabName === "web") {
  tabEl.hidden = false;
  tabEl.setAttribute("aria-hidden", "false");
  return;
}

    if (tabName === "memory") {
      const visible = hasMemory;
      tabEl.hidden = !visible;
      tabEl.setAttribute("aria-hidden", visible ? "false" : "true");
      if (!visible) {
        tabEl.classList.remove("is-active");
      }
      return;
    }

    tabEl.hidden = false;
    tabEl.setAttribute("aria-hidden", "false");
  });
}

function setRailTab(tabName) {
  const requested = String(tabName || "artifacts").trim().toLowerCase();

  const nextTab =
    requested === "memory" || requested === "web" || requested === "artifacts"
      ? requested
      : "artifacts";

  if (!state.rail) state.rail = {};
  state.rail.tab = nextTab;

  qsa("[data-rail-tab]").forEach(function (tabEl) {
    const tab = String(tabEl.getAttribute("data-rail-tab") || "").trim().toLowerCase();
    const active = tab === nextTab;

    tabEl.hidden = false;
    tabEl.setAttribute("aria-hidden", "false");
    tabEl.classList.toggle("is-active", active);
    tabEl.setAttribute("aria-selected", active ? "true" : "false");
  });

  qsa("[data-rail-panel]").forEach(function (panelEl) {
    const panel = String(panelEl.getAttribute("data-rail-panel") || "").trim().toLowerCase();
    const active = panel === nextTab;

    panelEl.hidden = !active;
    panelEl.classList.toggle("is-active", active);
  });

  if (els.railTitle) {
    els.railTitle.textContent =
      nextTab === "memory" ? "Memory" :
      nextTab === "web" ? "Web" :
      "Artifacts";
  }

  if (els.railSubtitle) {
    els.railSubtitle.textContent =
      nextTab === "memory" ? "Saved memory" :
      nextTab === "web" ? "Recent web results" :
      "Session artifacts";
  }

  if (nextTab === "memory") {
    if (typeof renderMemory === "function") renderMemory();
  } else if (nextTab === "web") {
    if (typeof renderWeb === "function") renderWeb();
  } else {
    if (typeof renderArtifacts === "function") renderArtifacts();
  }
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

  syncRailTruth();

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

  syncRailReopenVisibility();
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
  if (!rawMessage || typeof rawMessage !== "object") return null;

  let safeRaw = rawMessage;

  if (safeRaw.ok === true && safeRaw.assistant_message) {
    safeRaw = safeRaw.assistant_message;
  }

  if (
    typeof safeRaw.text === "string" &&
    (
      safeRaw.text.includes("'ok': True") ||
      safeRaw.text.includes('"ok": true') ||
      safeRaw.text.includes("'assistant_message':") ||
      safeRaw.text.includes('"assistant_message":')
    )
  ) {
    return null;
  }

  const message = normalizeMessage(safeRaw);
  if (!message) return null;

  const existingIndex = state.messages.findIndex(function (item) {
    if (!item) return false;

    if (message.id && item.id === message.id) return true;

return (
  String(item.role || "") === String(message.role || "") &&
  String(item.text || "").trim() &&
  String(item.text || "").trim() === String(message.text || "").trim()
);
  });

  if (existingIndex >= 0) {
    state.messages[existingIndex] = message;
  } else {
    state.messages.push(message);
  }

  renderChat();
  return message;
}

function upsertWorkingContextMessage(workingContext, targetMessageId) {
  const wc = normalizeWorkingContext(workingContext);

  state.workingContext = wc.show ? wc : emptyWorkingContext();

  state.messages = (state.messages || []).filter(function (msg) {
    return !(msg && msg.kind === "working_context");
  });

  return targetMessageId || null;
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

  let nextSessionId = "";

  if (window.NovaSessionRail?.getActiveSessionId) {
    const railId = window.NovaSessionRail.getActiveSessionId();
    if (railId) nextSessionId = railId;
  }

  if (!nextSessionId) {
    nextSessionId = String(
      data.active_session_id ||
      data.session_id ||
      (data.session && data.session.id) ||
      ""
    ).trim();
  }

  state.activeSessionId = nextSessionId;

if (data.session && Array.isArray(data.session.messages)) {
  const incomingMessages = data.session.messages.map(normalizeMessage);

  if (incomingMessages.length > 0) {
    state.messages = incomingMessages;
  } else {
    console.warn("[NovaComposerBundle] BLOCKED empty overwrite");
  }
}

  state.sessions = Array.isArray(data.sessions) ? data.sessions : state.sessions;
  state.artifacts = Array.isArray(data.artifacts) ? data.artifacts : state.artifacts;
  state.memory = Array.isArray(data.memory)
    ? data.memory.map(normalizeMemoryItem)
    : state.memory;

  renderSessionList();
  renderChat();
  renderArtifacts();
  renderMemory();
  syncRailTruth();

  if (typeof renderWeb === "function") {
    renderWeb();
  }

  if (state.stream) {
    state.stream.placeholderId = "";
    state.stream.messageId = "";
    state.stream.targetMessageId = "";
  }

  updateTopbarFromState();
}

// ==============================
// 🔥 UNIFIED SESSION SWITCH (LOCKED)
// ==============================

window.openSessionFromBackend = async function (sessionId) {
  const id = String(sessionId || "").trim();
  if (!id) return false;

  if (typeof jumpToSessionAndSync === "function") {
    return await jumpToSessionAndSync(id);
  }

  console.warn("jumpToSessionAndSync missing");
  return false;
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

  // 🔥 MEMORY BADGE CLICK
  const memoryBadge = event.target.closest("[data-memory-used]");
  if (memoryBadge) {
    event.preventDefault();
    event.stopPropagation();

    try {
      const raw = decodeURIComponent(memoryBadge.getAttribute("data-memory-used") || "[]");
      const items = JSON.parse(raw);

      const rail = document.querySelector("[data-right-rail]");
      const viewer = document.querySelector("[data-rail-viewer]");
      if (!rail || !viewer) return;

      rail.classList.add("is-open");
      document.body.classList.add("is-rail-open");
      viewer.hidden = false;

viewer.innerHTML = `
  <div class="nova-viewer-shell">
    <div class="nova-viewer-title">Memory Used</div>

    <div class="nova-viewer-body">
      ${items.map(function (item) {
        return `
          <div style="
            margin-bottom:10px;
            padding:10px;
            border-radius:10px;
            background:rgba(255,255,255,0.05);
            border:1px solid rgba(255,255,255,0.08);
          ">
            <div style="font-size:13px;line-height:1.4;">
              ${escapeHtml(item.text || "")}
            </div>

            <div style="font-size:11px;opacity:.6;margin-top:4px;">
              ${escapeHtml(item.kind || "memory")} • ${escapeHtml(item.source || "auto")}
            </div>
          </div>
        `;
      }).join("") || "<div style='opacity:.6;'>No memory items</div>"}
    </div>
  </div>
`;

    } catch (err) {
      console.error("memory badge click failed", err);
    }

    return;
  }

  // 🔥 IMAGE REGENERATE (message-based)
  const imageRegenBtn = event.target.closest("[data-regenerate-image-message]");
  if (imageRegenBtn) {
    event.preventDefault();
    event.stopPropagation();

    const messageId = String(imageRegenBtn.getAttribute("data-regenerate-image-message") || "").trim();
    if (!messageId) return;

    const userMsg = currentUserMessageForRegenerate(messageId);
    if (!userMsg) return;

    const prompt = String(userMsg.text || "").trim();
    if (!prompt) return;

    const payload = {
      user_text: prompt.startsWith("/image") ? prompt : "/image " + prompt,
      session_id: String(state.activeSessionId || "").trim(),
      attachments: [],
    };

    if (typeof consumeChatStream === "function") {
      await consumeChatStream(payload);
    } else if (typeof consumeChatStreamStable === "function") {
      await consumeChatStreamStable(payload);
    } else if (typeof consumeChatJson === "function") {
      await consumeChatJson(payload);
    }

    return;
  }

  // 🔥 IMAGE REGENERATE (simple)
  const imageRegenSimple = event.target.closest("[data-regenerate-image]");
  if (imageRegenSimple) {
    event.preventDefault();

    const prompt = String(imageRegenSimple.getAttribute("data-regenerate-image") || "").trim();
    if (prompt) {
      sendMessage("/image " + prompt);
    }

    return;
  }

  // 🔥 COPY MESSAGE
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
    } catch (err) {
      console.warn("copy failed", err);
    }

    return;
  }

  // 🔥 REGENERATE MESSAGE
  const messageRegenBtn = event.target.closest("[data-regenerate-message]");
  if (messageRegenBtn) {
    const messageId = String(messageRegenBtn.getAttribute("data-regenerate-message") || "").trim();
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

    return;
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

function linkifySourceLines(html) {
  return String(html || "").replace(
    /(https?:\/\/[^\s<]+)/g,
    function (url) {
      const cleanUrl = url.replace(/[.,)]$/, "");
      return `<div class="source-row" data-url="${cleanUrl}" data-title="Source">${cleanUrl}</div>`;
    }
  );
}

function normalizeWorkingContext(raw) {
  const input = raw && typeof raw === "object" ? raw : {};
  const rawState =
    input.state && typeof input.state === "object" ? input.state : {};

  return {
    show: Boolean(input.show),
    collapsed: Boolean(input.collapsed),
    text: typeof input.text === "string" ? input.text : "",
    state: {
      active_task:
        typeof rawState.active_task === "string" ? rawState.active_task : "",
      current_file:
        typeof rawState.current_file === "string" ? rawState.current_file : "",
      current_bug:
        typeof rawState.current_bug === "string" ? rawState.current_bug : "",
      last_success:
        typeof rawState.last_success === "string" ? rawState.last_success : "",
      next_move:
        typeof rawState.next_move === "string" ? rawState.next_move : "",
      checkpoint:
        typeof rawState.checkpoint === "string" ? rawState.checkpoint : "",
      updated_at:
        typeof rawState.updated_at === "string" ? rawState.updated_at : "",
    },
  };
}

function linkifySourceLines(text) {
  const raw = String(text || "");
  if (!raw) return "";

  const lines = raw.split(/\r?\n/);
  const output = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    const match = line.match(/^\s*(\d+)\.\s*(.+?)\s*[—-]\s*(.+?)\s*$/);

    if (match) {
      const index = match[1];
      const source = match[2].trim();
      const title = match[3].trim();

      let url = "";

      const nextLine = (lines[i + 1] || "").trim();
      if (nextLine.startsWith("http://") || nextLine.startsWith("https://")) {
        url = nextLine;
        i++;
      }

      output.push(
        '<div class="source-row" data-no-chat-action="1" data-url="' +
          escapeHtml(url) +
          '" data-title="' +
          escapeHtml(title) +
          '" data-preview="' +
          escapeHtml(source + " — " + title) +
          '">' +
          escapeHtml(index) +
          ". " +
          '<span class="source-name">' +
          escapeHtml(source) +
          "</span> — " +
          '<a href="' +
          escapeHtml(url) +
          '" target="_blank" rel="noopener noreferrer" data-no-chat-action="1">' +
          escapeHtml(title) +
          "</a>" +
          "</div>"
      );
    } else {
      output.push(escapeHtml(line));
    }
  }

  return output.join("<br>");
}

document.addEventListener("click", function (e) {
  const protectedEl = e.target.closest("[data-no-chat-action='1']");
  const sourceEl = e.target.closest(".source-card, .source-row");

  if (protectedEl && !sourceEl) {
    e.preventDefault();
    e.stopPropagation();
    return;
  }

  if (!sourceEl) return;

  e.preventDefault();
  e.stopPropagation();

  let url =
    sourceEl.getAttribute("data-source-url") ||
    sourceEl.getAttribute("data-url") ||
    "";

  if (!url) {
    const link = sourceEl.querySelector("a[href]");
    if (link) url = link.getAttribute("href") || "";
  }

  if (!url) return;

  let title =
    sourceEl.getAttribute("data-title") ||
    sourceEl.getAttribute("data-preview") ||
    sourceEl.textContent ||
    "Source preview";

  title = String(title || "").trim();

  let domain = "Source";
  let favicon = "";

  try {
    const parsed = new URL(url);
    domain = parsed.hostname.replace(/^www\./, "");
    favicon =
      "https://www.google.com/s2/favicons?domain=" +
      encodeURIComponent(parsed.hostname) +
      "&sz=32";
  } catch (_) {}

  const rail = document.querySelector("[data-right-rail]");
  const viewer = document.querySelector("[data-rail-viewer]");

  if (!rail || !viewer) {
    window.open(url, "_blank");
    return;
  }

  rail.classList.add("is-open");
  document.body.classList.add("is-rail-open");
  viewer.hidden = false;

  viewer.innerHTML = `
    <div class="nova-viewer-shell">
      <div class="nova-viewer-title">Source Preview</div>

      <div class="nova-viewer-body">
        <div style="
          display:flex;
          align-items:center;
          gap:10px;
          margin-bottom:12px;
          padding:10px;
          border-radius:12px;
          background:rgba(255,255,255,0.05);
          border:1px solid rgba(255,255,255,0.08);
        ">
          ${
            favicon
              ? `<img src="${escapeHtml(favicon)}" style="width:24px;height:24px;border-radius:6px;">`
              : `<div style="width:24px;height:24px;border-radius:6px;background:rgba(255,255,255,0.1);"></div>`
          }

          <div style="min-width:0;">
            <div style="font-size:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
              ${escapeHtml(domain)}
            </div>
            <div style="font-size:11px;opacity:.65;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
              ${escapeHtml(url)}
            </div>
          </div>
        </div>

        <div style="
          padding:12px;
          border-radius:12px;
          background:rgba(255,255,255,0.035);
          border:1px solid rgba(255,255,255,0.08);
          margin-bottom:12px;
        ">
          <div style="font-size:14px;font-weight:700;line-height:1.35;margin-bottom:6px;">
            ${escapeHtml(title)}
          </div>
          <div style="font-size:12px;opacity:.7;">
            Click below to open the full source in a new tab.
          </div>
        </div>

        <a href="${escapeHtml(url)}"
           target="_blank"
           rel="noopener noreferrer"
           data-no-chat-action="1"
           style="
             display:inline-flex;
             padding:9px 12px;
             border-radius:10px;
             background:rgba(255,255,255,0.09);
             color:#fff;
             text-decoration:none;
             font-size:13px;
             font-weight:700;
           ">
          Open full article →
        </a>
      </div>
    </div>
  `;
});

function renderSourceList(message) {
  try {
    if (!message || message.role !== "assistant") return "";

    const meta = message.meta || {};
    const urls = Array.isArray(meta.source_urls) ? meta.source_urls : [];

    if (!urls.length) return "";

    return (
      '<div class="source-list">' +
        '<div class="source-title">Sources</div>' +
        urls.slice(0, 5).map(function (url) {
          let domain = "source";

          try {
            domain = new URL(url).hostname.replace("www.", "");
          } catch (e) {}

          return (
            '<div class="source-row" data-url="' + escapeHtml(url) + '">' +
              escapeHtml(domain) +
            "</div>"
          );
        }).join("") +
      "</div>"
    );
  } catch (err) {
    console.warn("renderSourceList failed:", err);
    return "";
  }
}

function renderQualityBadge(msg) {
  if (!msg || msg.role !== "assistant") return "";

  const meta = msg.meta || {};
  const score = meta.quality_score;
  const grade = meta.grade;

  if (!score || !grade) return "";

  return `
    <div style="
      margin-top:8px;
      font-size:11px;
      opacity:0.7;
    ">
      Confidence: ${score} (${grade})
    </div>
  `;
}

function wireWorkingContextPanel() {
  if (!els.chatThread) return;
  if (els.chatThread.__workingContextWired) return;

  els.chatThread.__workingContextWired = true;

  els.chatThread.addEventListener("click", function (event) {
    const toggle = event.target.closest("[data-working-context-toggle]");
    if (!toggle) return;

    const current = normalizeWorkingContext(state.workingContext || emptyWorkingContext());

    state.workingContext = Object.assign({}, current, {
      collapsed: !current.collapsed,
    });

    renderChat();
  });
}

function renderMessageCard(message) {
  if (!message) return "";

  const role = String(message.role || "assistant");
  const roleClass = role === "user" ? "message-card--user" : "message-card--assistant";
  const rawText = String(message.text || "").trim();

  const bodyHtml = rawText
    ? '<div class="message-text-inline" style="display:block !important; white-space:pre-wrap !important; color:#ffffff !important; background:rgba(255,255,255,0.04) !important; padding:10px 12px !important; border-radius:10px !important; margin:8px 0 10px 0 !important; line-height:1.45 !important;">' +
        linkifySourceLines(rawText) +
      "</div>"
    : "";

  let memoryBadgeHtml = "";

  try {
    const meta =
      message.meta && Object.keys(message.meta).length > 0
        ? message.meta
        : (message.assistant_message && message.assistant_message.meta) || {};

    const used = Array.isArray(meta.used_memory) ? meta.used_memory : [];
    const count = meta.used_memory_count || used.length;
    const confidence = meta.memory_confidence;

    if (role !== "user" && count > 0) {
      let label = "Memory used: " + escapeHtml(count);

      if (typeof confidence === "number") {
        label += " • Confidence: " + Math.round(confidence * 100) + "%";
      }

memoryBadgeHtml =
  '<button class="memory-used-badge" type="button" ' +
  'data-no-chat-action="1" ' +
  'data-memory-used="' + encodeURIComponent(JSON.stringify(used)) + '">' +
  label +
  "</button>";
    }
  } catch (e) {
    console.warn("memory badge failed", e);
  }

  return (
    '<article class="message-card ' +
    roleClass +
    '" data-message-id="' +
    escapeHtml(message.id) +
    '">' +
    bodyHtml +
    memoryBadgeHtml +
    renderSourceList(message) +
    renderMessageActions(message) +
    "</article>"
  );
}

function renderChat() {
  if (!els.chatThread) return;

  state.messages = (state.messages || []).filter(function (msg) {
    return !(msg && msg.kind === "working_context");
  });

  state.messages = (state.messages || []).slice().sort(function (a, b) {
    const at = Date.parse(a && a.created_at ? a.created_at : "") || 0;
    const bt = Date.parse(b && b.created_at ? b.created_at : "") || 0;

    if (at !== bt) return at - bt;

    const aRole = String((a && a.role) || "");
    const bRole = String((b && b.role) || "");

    if (aRole === bRole) return 0;
    if (aRole === "user" && bRole === "assistant") return -1;
    if (aRole === "assistant" && bRole === "user") return 1;

    return 0;
  });

  setChatEmptyVisible(state.messages.length === 0);

  const workingContextHtml = "";
  const messagesHtml = state.messages.map(renderMessageCard).join("");
  let nextHtml = workingContextHtml + messagesHtml;

  if (els.chatThread.__lastRenderHtml !== nextHtml) {
    els.chatThread.innerHTML = nextHtml;

    els.chatThread.__lastRenderHtml = nextHtml;
  }

  wireWorkingContextPanel();

  const firstSourceRow = els.chatThread.querySelector(".source-row");
  const firstSourceKey = firstSourceRow
    ? firstSourceRow.getAttribute("data-url")
    : "";

  if (
    firstSourceRow &&
    firstSourceKey &&
    els.chatThread.__autoOpenedSource !== firstSourceKey
  ) {
    els.chatThread.__autoOpenedSource = firstSourceKey;
    setTimeout(function () {
      firstSourceRow.click();
    }, 300);
  }

  if (typeof wireRailTabs === "function") {
    wireRailTabs();
  } else {
    document.querySelectorAll("[data-rail-tab]").forEach(function (btn) {
      if (btn.__novaRailTabWired) return;
      btn.__novaRailTabWired = true;

      btn.addEventListener("click", function () {
        const tab = String(btn.getAttribute("data-rail-tab") || "artifacts").trim();
        if (typeof setRailTab === "function") setRailTab(tab);
        if (typeof openRail === "function") openRail();
      });
    });
  }

  const memoryEl = document.getElementById("nova-memory-list");

  if (memoryEl) {
    const memory = (state.memory || []).slice().sort(function (a, b) {
      const ap = a && a.pinned ? 1 : 0;
      const bp = b && b.pinned ? 1 : 0;
      return bp - ap;
    });

    memoryEl.innerHTML = memory.map(function (item) {
      const id = String(item.id || "");
      const text = String(item.text || "");

      return `
        <div class="nova-memory-item" data-id="${id}">
          <div>
            <div>${item.pinned ? "📌" : "🧠"} ${text}</div>
            <small>${String(item.kind || "note")} · ${String(item.source || "manual")}</small>
          </div>
          <button class="nova-memory-pin" data-id="${id}">📌</button>
          <button class="nova-memory-delete" data-id="${id}">Remove</button>
        </div>
      `;
    }).join("") || `<div class="nova-empty">No memory yet</div>`;

    memoryEl.querySelectorAll(".nova-memory-delete").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        const id = this.getAttribute("data-id");

        try {
          const res = await fetch("/api/memory/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: id }),
          });

const data = await res.json();

window.__lastResponse = data;
console.log("FULL RESPONSE:", data);

if (!data.ok) { 
           state.memory = data.memory || [];
            renderChat();
          }
        } catch (err) {
          console.error("Delete memory failed", err);
        }
      });
    });
  }

  updateTopbarFromState();
  scrollChatToBottom(true);
  renderExecutionPanel();
}

function renderSessionList() {
  return;
}

async function sendExecutionCommand(commandText) {
  const payload = {
    user_text: commandText,
    session_id: state.activeSessionId || "",
    attachments: [],
  };

  return consumeChatStreamStable(payload);
}

function extractExecutionFromArtifact(artifact) {

  if (!artifact || typeof artifact !== "object") return null;

  const direct = artifact.execution && typeof artifact.execution === "object"
    ? artifact.execution
    : null;

  const metaExecution = artifact.meta &&
    typeof artifact.meta === "object" &&
    artifact.meta.execution &&
    typeof artifact.meta.execution === "object"
      ? artifact.meta.execution
      : null;

  const execution = direct || metaExecution;
  if (!execution) return null;

  const steps = Array.isArray(execution.steps) ? execution.steps : [];
  const stepResults = Array.isArray(execution.step_results)
    ? execution.step_results
    : (Array.isArray(execution.stepResults) ? execution.stepResults : []);

  return {
    artifactId: artifact.id || "",
    goal: execution.goal || artifact.title || "Execution",
    status: execution.status || "",
    progress: Number(execution.progress || 0),
    currentStep: execution.current_step || "",
    currentStepIndex: Number(execution.current_step_index || 0),
    steps,
    stepResults,
    raw: execution,
  };
}

function syncExecutionFromArtifacts() {
  const artifacts = Array.isArray(state.artifacts) ? state.artifacts : [];
  let latest = null;

  for (const artifact of artifacts) {
    const extracted = extractExecutionFromArtifact(artifact);
    if (!extracted) continue;
    latest = extracted;
  }

  if (!latest) {
    state.execution = {
      artifactId: "",
      goal: "",
      status: "",
      progress: 0,
      currentStep: "",
      currentStepIndex: 0,
      steps: [],
      stepResults: [],
      raw: null,
    };
    return;
  }

  state.execution = latest;
}

function renderExecutionPanel() {
  if (!els.executionPanel || !els.executionContent || !els.executionEmpty) return;

  syncExecutionFromArtifacts();

  const execution = state.execution || {};
  const steps = Array.isArray(execution.steps) ? execution.steps : [];
  const total = steps.length;
  const progress = Number(execution.progress || 0);
  const percent = total > 0 ? Math.max(0, Math.min(100, (progress / total) * 100)) : 0;
  const status = String(execution.status || "").toLowerCase();

  if (!execution.raw) {
    els.executionPanel.hidden = true;
    els.executionEmpty.hidden = true;
    els.executionContent.hidden = true;
    els.executionContent.innerHTML = "";
    return;
  }

  const stepsHtml = steps.map(function (step, index) {
    const title = escapeHtml((step && step.title) || `Step ${index + 1}`);
    const isDone = index < progress || String((step && step.status) || "").toLowerCase() === "done";
    const isCurrent = index === Number(execution.currentStepIndex || 0) && status !== "complete";
    const isBlocked = status === "blocked" && isCurrent;

    const classes = [
      "execution-step",
      isDone ? "is-done" : "",
      isCurrent ? "is-current" : "",
      isBlocked ? "is-blocked" : "",
    ].filter(Boolean).join(" ");

    return `
      <div class="${classes}">
        <div>${isDone ? "✓" : isCurrent ? ">" : "•"} ${title}</div>
      </div>
    `;
  }).join("");

  els.executionPanel.hidden = false;
  els.executionEmpty.hidden = true;
  els.executionContent.hidden = false;
  els.executionContent.innerHTML = `
    <div class="execution-card">
      <div class="execution-goal">${escapeHtml(execution.goal || "Execution")}</div>
      <div class="execution-meta">
        Status: ${escapeHtml(execution.status || "unknown")} ·
        Progress: ${progress}/${total} ·
        Current: ${escapeHtml(execution.currentStep || "complete")}
      </div>
      <div class="execution-progress">
        <div class="execution-progress-bar" style="width:${percent}%"></div>
      </div>
      <div class="execution-steps">${stepsHtml}</div>
    </div>
  `;
}

function getSessionArtifactsForRail() {
  const activeSessionId = String(state.activeSessionId || "").trim();
  const allArtifacts = safeArray(state.artifacts);

  let sessionArtifacts = allArtifacts.filter(function (item) {
    if (!activeSessionId) return true;
    return String(item && item.session_id ? item.session_id : "").trim() === activeSessionId;
  });

  if (!sessionArtifacts.length && allArtifacts.length) {
    sessionArtifacts = allArtifacts.slice();
  }

  return sessionArtifacts;
}

function getArtifactKindBadge(kind) {
  const value = String(kind || "").trim().toLowerCase();

  if (!value) return "artifact";
  if (value.includes("image")) return "image";
  if (value.includes("web")) return "web";
  if (value.includes("chat")) return "chat";
  if (value.includes("analysis")) return "analysis";
  return "artifact";
}

function getAvailableArtifactFilters(items) {
  const filters = new Set(["all"]);

  safeArray(items).forEach(function (item) {
    const viewer = item && typeof item.viewer === "object" ? item.viewer : {};
    const badge = getArtifactKindBadge(viewer.kind || item.kind || "artifact");
    filters.add(badge);
  });

  const preferredOrder = ["all", "image", "web", "chat", "analysis", "artifact"];
  return preferredOrder.filter(function (key) {
    return filters.has(key);
  });
}

function syncRailTruth() {
  const hasArtifacts = getSessionArtifactsForRail().length > 0;
  const hasMemory = safeArray(state.memory).length > 0;

  if (!state.rail) state.rail = {};

  if (!state.rail.tab) {
    state.rail.tab = "artifacts";
  }

  qsa("[data-rail-tab]").forEach(function (tabEl) {
    const tab = String(tabEl.getAttribute("data-rail-tab") || "").trim().toLowerCase();

    tabEl.hidden = false;
    tabEl.setAttribute("aria-hidden", "false");
  });
}

function renderArtifacts() {
  if (!els.artifactList) {
    els.artifactList = document.querySelector("[data-artifact-list]");
  }
  if (!els.artifactList) return;

  if (!state.rail) state.rail = {};

  const activeSessionId = String(state.activeSessionId || "").trim();
  const searchQuery = String(state.rail.artifactSearch || "").trim().toLowerCase();
  let activeFilter = String(state.rail.artifactFilter || "all").trim().toLowerCase();

  const allArtifacts = safeArray(state.artifacts);

  const sessionArtifacts = allArtifacts.filter(function (item) {
    const itemSessionId = String((item && item.session_id) || "").trim();
    return !activeSessionId || !itemSessionId || itemSessionId === activeSessionId;
  });

  function getKindBadge(kind) {
    const value = String(kind || "").toLowerCase();
    if (value.includes("image")) return "image";
    if (value.includes("web")) return "web";
    if (value.includes("chat")) return "chat";
    if (value.includes("analysis")) return "analysis";
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

  const filterSet = new Set(["all"]);

  sessionArtifacts.forEach(function (item) {
    const viewer = item && typeof item.viewer === "object" ? item.viewer : {};
    const kind = String(viewer.kind || item.kind || "artifact");
    filterSet.add(getKindBadge(kind));
  });

  const filterOrder = ["all", "image", "web", "chat", "analysis", "artifact"];
  const availableFilters = filterOrder.filter(function (f) {
    return filterSet.has(f);
  });

  if (!availableFilters.includes(activeFilter)) {
    activeFilter = "all";
    state.rail.artifactFilter = "all";
  }

  const normalized = sessionArtifacts
    .map(function (item) {
      const viewer = item && typeof item.viewer === "object" ? item.viewer : {};
      const meta = item && typeof item.meta === "object" ? item.meta : {};

      const id = String(item.id || "").trim();
      const title = String(viewer.title || item.title || item.name || "Artifact").trim();

      const preview = String(
        viewer.body ||
          item.preview ||
          item.body ||
          item.content ||
          item.summary ||
          ""
      ).trim();

      const kind = String(viewer.kind || item.kind || "artifact").trim();
      const kindBadge = getKindBadge(kind);

      const thumbUrl = String(
        viewer.image_url ||
          item.image_url ||
          meta.image_url ||
          ""
      ).trim();

      const createdAt = String(item.updated_at || item.created_at || "").trim();

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
        String(item.session_id || ""),
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

      const matchesSearch = !searchQuery || entry.haystack.includes(searchQuery);
      const matchesFilter = activeFilter === "all" || entry.kindBadge === activeFilter;

      return matchesSearch && matchesFilter;
    });

  const filterLabels = {
    all: "All",
    image: "Image",
    web: "Web",
    chat: "Chat",
    analysis: "Analysis",
    artifact: "Other",
  };

  const controlsHtml =
    '<div class="rail-artifact-tools">' +
    '<input type="text" class="rail-artifact-search" data-artifact-search placeholder="Search artifacts..." value="' +
    escapeHtml(state.rail.artifactSearch || "") +
    '">' +
    '<div class="rail-artifact-filters">' +
    availableFilters
      .map(function (f) {
        return (
          '<button type="button" class="rail-filter-pill' +
          (activeFilter === f ? " is-active" : "") +
          '" data-artifact-filter="' +
          escapeHtml(f) +
          '">' +
          escapeHtml(filterLabels[f] || f) +
          "</button>"
        );
      })
      .join("") +
    "</div>" +
    "</div>";

  if (!sessionArtifacts.length) {
    els.artifactList.innerHTML =
      controlsHtml +
      '<div class="nova-artifact-empty">' +
      '<div class="nova-artifact-empty-title">No artifacts for this session</div>' +
      '<div class="nova-artifact-empty-copy">Create something to see it here.</div>' +
      "</div>";
    return;
  }

  if (!normalized.length) {
    els.artifactList.innerHTML =
      controlsHtml +
      '<div class="nova-artifact-empty">' +
      '<div class="nova-artifact-empty-title">No matching artifacts</div>' +
      '<div class="nova-artifact-empty-copy">Try a different filter.</div>' +
      "</div>";
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

  const html = Object.keys(grouped)
    .sort(function (a, b) {
      return getGroupOrder(a) - getGroupOrder(b);
    })
    .map(function (groupKey) {
      const cards = grouped[groupKey]
        .map(function (entry) {
          return (
            '<div class="nova-artifact-card" data-artifact-open="' +
            escapeHtml(entry.id) +
            '" data-artifact-id="' +
            escapeHtml(entry.id) +
            '">' +
            '<div class="nova-artifact-card-title">' +
            escapeHtml(entry.title) +
            "</div>" +
            '<button type="button" class="nova-artifact-delete" data-action="delete-artifact" data-artifact-id="' +
            escapeHtml(entry.id) +
            '" title="Delete artifact">Delete</button>' +
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
        cards +
        "</div>" +
        "</section>"
      );
    })
    .join("");

  els.artifactList.innerHTML = controlsHtml + html;
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

    upsertMessage({
      id: messageId,
      role: "assistant",
      text: "",
      streaming: true,
      pending: false,
      error: false,
      stopped: false,
      attachments: [],
      meta: {},
    });

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

    upsertMessage({
      id: targetId,
      role: "assistant",
      text: String(payload.error || "Stream failed."),
      streaming: false,
      pending: false,
      error: true,
      stopped: true,
      attachments: [],
      meta: {},
    });

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

  const existingIndex = Array.isArray(state.messages)
    ? state.messages.findIndex(function (msg) {
        return msg && msg.id === targetId;
      })
    : -1;

  const existing = existingIndex >= 0 ? state.messages[existingIndex] : null;

  const finalText = String(
    data.text ||
    data.content ||
    (data.assistant_message && typeof data.assistant_message === "object"
      ? data.assistant_message.text
      : "") ||
    (existing && existing.text) ||
    ""
  );

  const finalMessage = normalizeMessage({
    id: targetId,
    role: "assistant",
    text: finalText,
    streaming: false,
    pending: false,
    error: false,
    stopped: false,
    attachments: Array.isArray(data.attachments) ? data.attachments : [],
    meta:
  (data &&
    data.assistant_message &&
    typeof data.assistant_message.meta === "object" &&
    data.assistant_message.meta) ||
  (data && typeof data.meta === "object" && data.meta) ||
  {},

    artifact: data.artifact && typeof data.artifact === "object" ? data.artifact : {},
    viewer: data.viewer && typeof data.viewer === "object" ? data.viewer : {},
    image_url:
      data.image_url ||
      (data.artifact && data.artifact.image_url) ||
      (data.viewer && data.viewer.image_url) ||
      (data.meta && data.meta.image_url) ||
      "",
  });

  if (finalMessage && finalMessage.id) {
    upsertMessage(finalMessage);
  }

  if (data.execution && Array.isArray(data.execution.steps)) {
    state.execution = state.execution || { active: false, steps: [] };
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

  applyStatePayload(data);

  const assistantSource =
    data && data.assistant_message && typeof data.assistant_message === "object"
      ? data.assistant_message
      : finalMessage;

  const hydratedAssistantMessage = normalizeMessage(assistantSource || {});

  if (hydratedAssistantMessage && hydratedAssistantMessage.id) {
    upsertMessage(hydratedAssistantMessage);
  }

  if (finalMessage && finalMessage.id) {
    upsertMessage(finalMessage);
  }

  const workingContext = normalizeWorkingContext(
    (data && data.working_context_payload) ||
      (data && data.working_context) ||
      emptyWorkingContext()
  );

  if (workingContext.show) {
    upsertWorkingContextMessage(
      workingContext,
      (hydratedAssistantMessage && hydratedAssistantMessage.id) || finalMessage.id || ""
    );
  }

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
  if (!artifact) {
    return '<div class="nova-viewer-shell"><div class="nova-viewer-empty"><div class="nova-viewer-empty-title">No artifact</div></div></div>';
  }

  const item = artifact && typeof artifact === "object" ? artifact : {};
  const viewer = item.viewer && typeof item.viewer === "object" ? item.viewer : {};
  const meta = item.meta && typeof item.meta === "object" ? item.meta : {};

  const kind = String(viewer.kind || item.kind || "artifact").trim().toLowerCase();
  const title = String(viewer.title || item.title || item.name || "Artifact").trim();
  const body = String(
    viewer.body ||
    item.body ||
    item.preview ||
    item.summary ||
    item.content ||
    ""
  ).trim();

  const sourceUrl = String(
    viewer.source_url ||
    item.source_url ||
    meta.source_url ||
    meta.url ||
    ""
  ).trim();

  const imageUrl = String(
    viewer.image_url ||
    item.image_url ||
    meta.image_url ||
    ""
  ).trim();

  // ==============================
  // WEB VIEWER
  // ==============================
  if (kind === "web_result" || kind === "web_search") {
    const results =
      Array.isArray(viewer.results) ? viewer.results :
      Array.isArray(item.results) ? item.results :
      Array.isArray(meta.results) ? meta.results :
      Array.isArray(viewer.links) ? viewer.links :
      [];

    const query = String(
      viewer.query ||
      item.query ||
      meta.query ||
      title ||
      "Web results"
    ).trim();

    if (!results.length) {
      return `
        <div class="nova-viewer-shell">
          <div class="nova-viewer-card">
            <div class="nova-viewer-kicker">Web</div>
            <div class="nova-viewer-title">${escapeHtml(query)}</div>
            <div class="nova-viewer-body">${renderSafeText(body || "No results found.")}</div>
            ${sourceUrl ? `<a class="nova-web-viewer-open" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noreferrer">Open source</a>` : ""}
          </div>
        </div>
      `;
    }

    const items = results.slice(0, 8).map(function (r) {
      const t = escapeHtml(r.title || r.label || r.text || "Untitled");
      const s = escapeHtml(r.snippet || r.body || "");
      const u = escapeHtml(r.url || r.href || "#");

      return `
        <div class="web-card">
          <a href="${u}" target="_blank" rel="noreferrer" class="web-title">${t}</a>
          <div class="web-snippet">${s}</div>
          <div class="web-url">${u}</div>
        </div>
      `;
    }).join("");

    return `
      <div class="nova-viewer-shell">
        <div class="nova-viewer-card nova-web-viewer-card">
          <div class="nova-viewer-kicker">Web</div>
          <div class="nova-viewer-title">${escapeHtml(query)}</div>
          ${sourceUrl ? `<div class="nova-web-viewer-url">${escapeHtml(sourceUrl)}</div>` : ""}
          ${body ? `<div class="nova-viewer-body">${renderSafeText(body)}</div>` : ""}
          <div class="web-results">${items}</div>
          ${sourceUrl ? `<a class="nova-web-viewer-open" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noreferrer">Open source</a>` : ""}
        </div>
      </div>
    `;
  }

  // ==============================
  // IMAGE VIEWER
  // ==============================
  if (imageUrl) {
    return `
      <div class="nova-viewer-shell">
        <div class="nova-viewer-card">
          <div class="nova-viewer-kicker">Image</div>
          <div class="nova-viewer-title">${escapeHtml(title)}</div>
          <img src="${escapeHtml(imageUrl)}" class="nova-viewer-image" />
          ${body ? `<div class="nova-viewer-body">${renderSafeText(body)}</div>` : ""}
        </div>
      </div>
    `;
  }

  // ==============================
  // DEFAULT VIEWER
  // ==============================
  return `
    <div class="nova-viewer-shell">
      <div class="nova-viewer-card">
        <div class="nova-viewer-kicker">${escapeHtml(kind)}</div>
        <div class="nova-viewer-title">${escapeHtml(title)}</div>
        ${sourceUrl ? `<div class="nova-viewer-url">${escapeHtml(sourceUrl)}</div>` : ""}
        <div class="nova-viewer-body">${renderSafeText(body)}</div>
      </div>
    </div>
  `;
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

function findArtifactById(id) {
  const target = String(id || "").trim();
  if (!target) return null;

  return safeArray(state.artifacts).find(function (artifact) {
    return String((artifact && artifact.id) || "").trim() === target;
  }) || null;
}

async function openArtifactFromStateOrBackend(artifactId) {
  const id = String(artifactId || "").trim();
  if (!id) return;

  let artifact = typeof findArtifactById === "function" ? findArtifactById(id) : null;

  if (!artifact) {
    try {
      const payload = await apiGet("/api/state");
      applyStatePayload(payload);
      artifact = typeof findArtifactById === "function" ? findArtifactById(id) : null;
    } catch (error) {
      warn("artifact refresh failed", error);
    }
  }

  openRail();
  setRailTab("artifacts");

  if (!artifact) {
    if (els.railViewer) {
      els.railViewer.hidden = false;
      els.railViewer.innerHTML =
        '<div class="nova-viewer-shell">' +
          '<div class="nova-viewer-empty">' +
            '<div class="nova-viewer-empty-title">Artifact not found</div>' +
            '<div class="nova-viewer-empty-copy">This artifact is not available in the current state.</div>' +
          '</div>' +
        '</div>';
    }
    showToast("Artifact not found.", "error");
    return;
  }

  state.pendingArtifactOpenId = "";
  state.rail = state.rail || {};
  state.rail.tab = "artifacts";
  state.rail.selectedKind = "artifact";
  state.rail.selectedId = id;

  if (typeof setRailSelectedItem === "function") {
    setRailSelectedItem("artifact", id);
  }

  if (els.railViewer) {
    els.railViewer.hidden = false;
    els.railViewer.innerHTML = artifactViewerHtml(artifact);
  }

  if (window.NovaArtifacts && typeof window.NovaArtifacts.setActiveArtifactById === "function") {
    window.NovaArtifacts.setActiveArtifactById(id);
  }

  if (els.railTitle) {
    els.railTitle.textContent = "Artifacts";
  }

  if (els.railSubtitle) {
    const viewer = artifact.viewer && typeof artifact.viewer === "object" ? artifact.viewer : {};
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
  const messageId = makeId("user");

  const normalizedAttachments = Array.isArray(attachments)
    ? attachments.map(function (item) {
        return {
          id: String(item && item.id ? item.id : ""),
          filename: String(
            (item && (item.filename || item.name)) || ""
          ),
          name: String(
            (item && (item.name || item.filename)) || ""
          ),
          stored_name: String(item && item.stored_name ? item.stored_name : ""),
          file_url: String(item && item.file_url ? item.file_url : ""),
          url: String(
            (item && (item.url || item.file_url)) || ""
          ),
          mime_type: String(
            (item && item.mime_type) || "application/octet-stream"
          ),
          size: Number((item && item.size) || 0),
          status: "uploaded",
          upload_error: "",
        };
      })
    : [];

  const userMessage = {
    id: messageId,
    role: "user",
    kind: "message",
    text: String(text || ""),
    created_at: new Date().toISOString(),
    pending: false,
    streaming: false,
    error: false,
    stopped: false,
    attachments: normalizedAttachments,
    meta: {},
  };

  if (!Array.isArray(state.messages)) {
    state.messages = [];
  }

  state.messages.push(userMessage);
  renderChat();
  return userMessage;
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

  if (state.stream.running) {
    showToast("A generation is already running.", "info");
    throw new Error("A generation is already running.");
  }

  setBusyUi(true);
  state.stream.running = true;
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
      throw new Error("Chat returned invalid JSON.");
    }

    if (!response.ok || data.ok === false) {
      const message = String(data.error || "Chat failed.");
      showToast(message, "error");
      throw new Error(message);
    }

    window.__lastResponse = data;
    console.log("FULL CHAT RESPONSE:", data);

    if (state.stream && state.stream.targetMessageId) {
      removeMessage(state.stream.targetMessageId);
    }

    // Load backend state if present.
    applyStatePayload(data || {});

    // ✅ ASSISTANT RENDER LOCK:
    // If backend returned assistant_message but applyStatePayload did not render it,
    // insert it once here.
    const assistantMsg =
      data && data.assistant_message && typeof data.assistant_message === "object"
        ? normalizeMessage(data.assistant_message)
        : null;

    if (assistantMsg && String(assistantMsg.text || "").trim()) {
      const assistantText = String(assistantMsg.text || "").trim();

      const exists = (state.messages || []).some(function (msg) {
        return (
          msg &&
          String(msg.role || "") === "assistant" &&
          String(msg.text || "").trim() === assistantText
        );
      });

      if (!exists) {
        upsertMessage(assistantMsg);
      }
    }

    if (data && data.saved_artifact && data.saved_artifact.id) {
      openArtifactFromStateOrBackend(data.saved_artifact.id);
    }

    state.messages = (state.messages || []).map(function (msg) {
      if (!msg || String(msg.role || "") !== "assistant") return msg;

      return {
        ...msg,
        pending: false,
        streaming: false,
        stopped: false,
        error: false,
      };
    });

    renderChat();

    if (typeof flushTokensNow === "function") {
      flushTokensNow();
    }

    if (typeof clearTokenRenderState === "function") {
      clearTokenRenderState();
    }

    state.stream.running = false;
    state.stream.controller = null;
    state.stream.buffer = "";
    state.stream.placeholderId = "";
    state.stream.messageId = "";
    state.stream.targetMessageId = "";
    state.stream.startedAt = 0;

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

async function getBrowserLocation() {
  if (!navigator.geolocation) return null;

  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        resolve({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
        });
      },
      () => resolve(null),
      { enableHighAccuracy: true, timeout: 5000, maximumAge: 60000 }
    );
  });
}

async function sendMessage() {
  const inputEl =
    els.chatInput ||
    document.querySelector("[data-chat-input]") ||
    document.querySelector("textarea");

  const rawValue =
    inputEl && typeof inputEl.value === "string"
      ? inputEl.value
      : "";

  let text = String(rawValue || "").trim();

  // 🔒 BLOCK UI / DEBUG JUNK INPUT
  if (
    !inputEl ||
    inputEl !== els.chatInput ||
    text.length > 5000
  ) {
    console.warn("[Nova] blocked invalid input:", text);
    return;
  }

  const lower = text.toLowerCase();

  if (
    lower.includes("debug meta") ||
    lower.includes("memory used") ||
    lower.includes("confidence:")
  ) {
    console.warn("[Nova] blocked UI/debug text:", text);

    if (inputEl) {
      inputEl.value = "";
      autoResizeTextarea();
    }
    return;
  }

  console.log("sendMessage ENTERED", {
    hasInput: !!inputEl,
    text: text,
  });

  await maybeAutoSaveMemoryFromChatText(text);

  // 🎨 IMAGE PLACEHOLDER
  if (/^\/image|generate image|create image|draw/i.test(text)) {
    const tempId = "gen_" + Date.now();

    upsertMessage({
      id: tempId,
      role: "assistant",
      text: "🎨 Generating image...",
      pending: true,
      streaming: false,
      error: false,
      stopped: false,
      attachments: [],
    });

    state.imageGenPlaceholderId = tempId;
  }

  // 📎 ATTACHMENTS
  const attachments = (state.pendingUploads || [])
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
    showToast("Type a message first.", "info");
    return;
  }

  state.execution.active = false;
  state.execution.steps = [];
  renderExecution();

  if (!state.activeSessionId) {
    const created = await apiPost("/api/sessions/new", {});

    if (created && created.session && created.session.id) {
      state.activeSessionId = String(created.session.id);
    } else if (created && created.active_session_id) {
      state.activeSessionId = String(created.active_session_id);
    }

    await loadState();
  }

  // 🚫 PREVENT DUPLICATE USER MESSAGE
  const alreadyExists = (state.messages || []).some(function (msg) {
    return (
      msg &&
      msg.role === "user" &&
      String(msg.text || "").trim() === text
    );
  });

  if (!alreadyExists) {
    appendUserMessageLocal(text, attachments);
  }

  if (els.chatInput) {
    els.chatInput.value = "";
    autoResizeTextarea();
  }

  clearPendingUploads();

  try {
    const isImageCommand = text.toLowerCase().startsWith("/image");
    const location = await getBrowserLocation();

    const payload = {
      user_text: text,
      session_id: String(state.activeSessionId || ""),
      attachments: attachments,
      location: location,
    };

    if (isImageCommand) {
      await consumeChatJson(payload);
      showToast("Image request sent.", "success");
    } else {
      const pendingAssistantId = makeId("assistant");

      upsertMessage({
        id: pendingAssistantId,
        role: "assistant",
        text: "",
        created_at: new Date(Date.now() + 1).toISOString(),
        pending: true,
        streaming: true,
        error: false,
        stopped: false,
        attachments: [],
        meta: {},
      });

      state.stream = state.stream || {};
      state.stream.targetMessageId = pendingAssistantId;

      await consumeChatJson(payload);
    }
  } catch (error) {
    finishStreamUi({
      statusText: "Error",
      statusState: "error",
    });

    showToast("Chat failed", "error");

    upsertMessage({
      id: makeId("assistant_error"),
      role: "assistant",
      text: "⚠️ Something went wrong sending the message.",
      error: true,
    });

    if (state.imageGenPlaceholderId) {
      removeMessage(state.imageGenPlaceholderId);
      state.imageGenPlaceholderId = null;
    }

    warn("sendMessage failed", error);
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
  showToast("🎤 Recording... click again to send", "info");

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
        state.voice.recording = false;
        state.voice.mediaRecorder = null;
        state.voice.stream = null;
        state.voice.chunks = [];
        updateVoiceButtonUi();

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

const text = normalizeText(data && data.text ? data.text : "");
const safeText = typeof text === "string" ? text : "";
  if (!text) {
    showToast("No speech detected.", "info");
    return;
  }

  if (els.chatInput) {
    els.chatInput.value = text;
    autoResizeTextarea();
    els.chatInput.focus();
    els.chatInput.dispatchEvent(new Event("input", { bubbles: true }));
  }

  showToast("Voice ready. Sending...", "success");
  console.log("VOICE TRANSCRIPT =", text);
  await sendMessage();

  return text;
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
      enabled: true,
      playing: false,
      audio: null,
      lastAutoMessageId: "",
    };
  }

  if (state.tts.enabled === false) return;

  stopCurrentTtsPlayback();

  const payload = await requestVoiceReply(cleanText);

  const url = String(
    (payload &&
      payload.assistant_message &&
      payload.assistant_message.meta &&
      payload.assistant_message.meta.audio_url) ||
    (payload && payload.audio_url) ||
    (payload && payload.url) ||
    ""
  ).trim();

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

  try {
    await audio.play();
  } catch (err) {
    state.tts.playing = false;
    state.tts.audio = null;
    updateTtsToggleUi();
    throw err;
  }
}

function shouldAutoPlayTtsForMessage(message) {
  if (!message || typeof message !== "object") return false;

  const role = String(message.role || "").trim().toLowerCase();
  if (role !== "assistant") return false;

  const text = normalizeText(message.text || "").trim();
  if (!text) return false;

  if (!state.tts) {
    state.tts = {
      enabled: true,
      playing: false,
      audio: null,
      lastAutoMessageId: "",
    };
  }

  if (state.tts.enabled === false) return false;

  const meta = message.meta && typeof message.meta === "object" ? message.meta : {};
  if (meta.skip_tts === true) return false;

  const messageId = String(message.id || "").trim();
  if (messageId && state.tts.lastAutoMessageId === messageId) return false;

  return true;
}

async function autoPlayTtsForAssistantMessage(message) {
  if (!shouldAutoPlayTtsForMessage(message)) return;

  const text = normalizeText(message.text || "").trim();
  const messageId = String(message.id || "").trim();

  try {
    if (messageId) {
      state.tts.lastAutoMessageId = messageId;
    }
    await playVoiceReplyFromText(text);
  } catch (err) {
    console.error("[NovaComposerBundle] auto TTS failed:", err);
  }
}

function bindEvents() {
  // 🔥 FIXED composer submit (with debug + safety)
  if (els.composerForm) {
    els.composerForm.addEventListener("submit", function (event) {
      console.log("COMPOSER SUBMIT FIRED");

      event.preventDefault();

      if (typeof handleComposerSubmit === "function") {
        return handleComposerSubmit(event);
      }

      console.warn("handleComposerSubmit is missing or not a function");
    });
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

  // 🔥 execution buttons
  if (els.execRunStepButton) {
    els.execRunStepButton.addEventListener("click", function (event) {
      event.preventDefault();
      sendExecutionCommand("run it");
    });
  }

  if (els.execRunAllButton) {
    els.execRunAllButton.addEventListener("click", function (event) {
      event.preventDefault();
      sendExecutionCommand("run all");
    });
  }

  if (els.execStopButton) {
    els.execStopButton.addEventListener("click", function (event) {
      event.preventDefault();
      sendExecutionCommand("stop");
    });
  }

  if (els.execShowPlanButton) {
    els.execShowPlanButton.addEventListener("click", function (event) {
      event.preventDefault();
      sendExecutionCommand("show plan");
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
    renderExecutionPanel();
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
  if (!els.webList) {
    els.webList = document.querySelector("[data-web-list]");
  }

  if (!els.webList) return;

  const items = safeArray(state.web).length
    ? safeArray(state.web)
    : safeArray(state.artifacts).filter(function (item) {
        const kind = String((item && item.kind) || "").toLowerCase();
        const source = String((item && item.source) || "").toLowerCase();
        return kind === "web_result" || kind === "web_search" || source === "web_fetch";
      });

  if (!items.length) {
    els.webList.innerHTML =
      '<div class="nova-memory-empty">' +
        '<div class="nova-memory-empty-title">No web results yet</div>' +
        '<div class="nova-memory-empty-copy">Search something live and the result will appear here.</div>' +
      '</div>';
    return;
  }

els.webList.innerHTML = items.map(function (item) {
  const viewer = item.viewer || {};
  const meta = item.meta || {};

  const id = escapeHtml(item.id || meta.id || viewer.id || "");
  const title = escapeHtml(viewer.title || item.title || meta.title || "Web result");
  const summary = escapeHtml(
    viewer.analysis_text ||
    item.summary ||
    item.preview ||
    meta.summary ||
    ""
  );

  const url = escapeHtml(
    viewer.source_url ||
    item.source_url ||
    meta.source_url ||
    ""
  );

  return (
    '<button type="button" class="nova-web-card" data-artifact-open="' + id + '">' +
      '<div class="nova-web-card-title">' + title + '</div>' +
      (summary ? '<div class="nova-web-card-summary">' + summary.slice(0, 220) + '</div>' : "") +
      (url ? '<div class="nova-web-card-url">' + url + '</div>' : "") +
    '</button>'
  );
}).join("");

if (typeof wireWebLinks === "function") {
  wireWebLinks();
}
}

function renderWorkingContextCard(workingContext) {
  const wc = normalizeWorkingContext(workingContext);

  if (!wc.show) return "";

  const items = [];

  if (wc.state.active_task) {
    items.push(
      `<div class="nova-working-context-row"><span class="nova-working-context-label">Active task</span><span class="nova-working-context-value">${escapeHtml(wc.state.active_task)}</span></div>`
    );
  }

  if (wc.state.current_file) {
    items.push(
      `<div class="nova-working-context-row"><span class="nova-working-context-label">Current file</span><span class="nova-working-context-value">${escapeHtml(wc.state.current_file)}</span></div>`
    );
  }

  if (wc.state.current_bug) {
    items.push(
      `<div class="nova-working-context-row"><span class="nova-working-context-label">Current bug</span><span class="nova-working-context-value">${escapeHtml(wc.state.current_bug)}</span></div>`
    );
  }

  if (wc.state.last_success) {
    items.push(
      `<div class="nova-working-context-row"><span class="nova-working-context-label">Last success</span><span class="nova-working-context-value">${escapeHtml(wc.state.last_success)}</span></div>`
    );
  }

  if (wc.state.next_move) {
    items.push(
      `<div class="nova-working-context-row"><span class="nova-working-context-label">Next move</span><span class="nova-working-context-value">${escapeHtml(wc.state.next_move)}</span></div>`
    );
  }

  if (wc.state.checkpoint) {
    items.push(
      `<div class="nova-working-context-row"><span class="nova-working-context-label">Checkpoint</span><span class="nova-working-context-value">${escapeHtml(wc.state.checkpoint)}</span></div>`
    );
  }

  if (!items.length && wc.text) {
    items.push(
      `<pre class="nova-working-context-pre">${escapeHtml(wc.text)}</pre>`
    );
  }

  return `
    <section class="nova-working-context-card" data-working-context-card>
      <div class="nova-working-context-header">
        <span class="nova-working-context-kicker">Working context</span>
      </div>
      <div class="nova-working-context-body">
        ${items.join("")}
      </div>
    </section>
  `;
}

function wireRailClose() {
  const closeBtn = document.querySelector("[data-rail-close]");
  if (!closeBtn) return;

  closeBtn.addEventListener("click", function () {
    closeRail();
  });
}

function wireWebLinks() {
  document.querySelectorAll("[data-artifact-open]").forEach(function (node) {
    if (node.__novaWebWired) return;
    node.__novaWebWired = true;

    node.addEventListener("click", function () {
      const id = String(node.getAttribute("data-artifact-open") || "").trim();
      if (!id) return;

      if (typeof openArtifactInRail === "function") {
        openArtifactInRail(id);
      }
    });
  });
}

async function maybeAutoSaveMemoryFromChatText(userText) {
  const text = String(userText || "").trim();
  if (!text) return;

  const lower = text.toLowerCase();

  // 🚫 junk filter
  if (
    lower.length < 5 ||
    lower === "hi" ||
    lower.startsWith("auto memory saving")
  ) {
    return;
  }

  const triggers = [
    "remember that ",
    "remember this ",
    "note that ",
    "save this ",
    "add this to memory ",
    "store this "
  ];

  let memoryText = "";

  for (let i = 0; i < triggers.length; i++) {
    if (lower.startsWith(triggers[i])) {
      memoryText = text.slice(triggers[i].length).trim();
      break;
    }
  }

  if (!memoryText) {
    const autoPatterns = [
      /^my .+ is .+/i,
      /^i prefer .+/i,
      /^i like .+/i,
      /^i want .+/i,
      /^i am working on .+/i,
      /^i'm working on .+/i,
      /^from now on .+/i
    ];

    const shouldAutoSave = autoPatterns.some((p) => p.test(text));
    if (!shouldAutoSave) return;

    memoryText = text;
  }

  // 🧠 DEDUPE
  const exists = (state.memory || []).some((m) => {
    return String(m.text || "").toLowerCase() === memoryText.toLowerCase();
  });

  if (exists) return;

  // 🔥 IMPORTANCE SCORING
  let importance = 1; // default low

  if (/^my .+ is .+/i.test(memoryText)) importance = 3; // identity
  else if (/from now on|always|never/i.test(memoryText)) importance = 3; // rules
  else if (/i prefer|i like/i.test(memoryText)) importance = 2; // preference
  else if (/working on/i.test(memoryText)) importance = 2; // project

  try {
    const res = await fetch("/api/memory/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: memoryText,
        kind: "note",
        source: "chat-auto",
        importance: importance
      })
    });

    const data = await res.json();

    const memoryList =
      (data && data.data && data.data.memory) ||
      data.memory ||
      [];

    if (Array.isArray(memoryList)) {
      // 🔥 SORT BY IMPORTANCE
      const normalized = memoryList.map(normalizeMemoryItem);

      normalized.sort((a, b) => {
        const ai = Number(a.importance || 1);
        const bi = Number(b.importance || 1);
        return bi - ai; // high first
      });

      state.memory = normalized;
      renderMemory();
      wireMemoryControls();
      wireMemoryClicks();
    }
  } catch (err) {
    console.error("Auto memory save failed", err);
  }
}

function wireMemoryControls() {
  console.log("WIRE MEMORY CONTROLS ACTIVE");

  const addBtn = document.querySelector("[data-memory-add-button]");
  const input = document.querySelector("[data-memory-add-text]");

  // ✅ ADD MEMORY (button click)
  if (addBtn && !addBtn.__novaMemoryAddWired) {
    addBtn.__novaMemoryAddWired = true;

    addBtn.onclick = async function (e) {
      e.preventDefault();
      e.stopPropagation();

      const cleanText = input ? String(input.value || "").trim() : "";

      if (!cleanText) {
        alert("Type a memory first.");
        return;
      }

      try {
        const res = await fetch("/api/memory/add", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: cleanText,
            kind: "note",
            source: "manual",
          }),
        });

        const data = await res.json();
        console.log("MEMORY ADD RESPONSE", data);

        if (data && data.ok && data.data && Array.isArray(data.data.memory)) {
          state.memory = data.data.memory.map(normalizeMemoryItem);
          renderMemory();

          if (input) input.value = "";
        }
      } catch (err) {
        console.error("Memory add failed", err);
      }
    };
  }

  // ✅ ENTER TO SAVE (no button needed)
  if (input && !input.__novaMemoryEnterWired) {
    input.__novaMemoryEnterWired = true;

    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (addBtn) addBtn.click();
      }
    });
  }

  // ✅ DELETE MEMORY
  document.querySelectorAll("[data-memory-delete]").forEach(function (btn) {
    if (btn.__wired) return;
    btn.__wired = true;

    btn.onclick = async function (e) {
      e.preventDefault();
      e.stopPropagation();

      const id = btn.getAttribute("data-memory-delete");
      if (!id) return;

      try {
        const res = await fetch("/api/memory/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: id }),
        });

        const data = await res.json();
        console.log("MEMORY DELETE RESPONSE", data);

        if (data && data.ok && data.data && Array.isArray(data.data.memory)) {
          state.memory = data.data.memory.map(normalizeMemoryItem);
          renderMemory();
        }
      } catch (err) {
        console.error("Memory delete failed", err);
      }
    };
  });
}

 function wireMemoryClicks() {
  if (!els || !els.memoryList) return;

  if (els.memoryList.__wiredClicks) return;
  els.memoryList.__wiredClicks = true;

  els.memoryList.addEventListener("click", function (e) {
    if (e.target.closest("[data-memory-delete]")) return;

    const btn = e.target.closest("[data-memory-id]");
    if (!btn) return;

    const memoryId = String(btn.getAttribute("data-memory-id") || "").trim();
    if (!memoryId) return;

    const item = safeArray(state.memory).find(function (entry) {
      return String(entry.id || "") === memoryId;
    });

    if (!item) return;

    openRail();
    setRailTab("memory");
    setRailSelectedItem("memory", memoryId);

    renderMemoryViewer(item);

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

function renderWorkingContextPanel() {
  const wc = normalizeWorkingContext(state.workingContext || emptyWorkingContext());

  if (!wc.show) {
    return "";
  }

  const items = [];

  if (wc.state.active_task) {
    items.push(
      `<div class="nova-working-context-row"><span class="nova-working-context-label">Active task</span><span class="nova-working-context-value">${escapeHtml(wc.state.active_task)}</span></div>`
    );
  }

  if (wc.state.current_file) {
    items.push(
      `<div class="nova-working-context-row"><span class="nova-working-context-label">Current file</span><span class="nova-working-context-value">${escapeHtml(wc.state.current_file)}</span></div>`
    );
  }

  if (wc.state.current_bug) {
    items.push(
      `<div class="nova-working-context-row"><span class="nova-working-context-label">Current bug</span><span class="nova-working-context-value">${escapeHtml(wc.state.current_bug)}</span></div>`
    );
  }

  if (wc.state.last_success) {
    items.push(
      `<div class="nova-working-context-row"><span class="nova-working-context-label">Last success</span><span class="nova-working-context-value">${escapeHtml(wc.state.last_success)}</span></div>`
    );
  }

  if (wc.state.next_move) {
    items.push(
      `<div class="nova-working-context-row"><span class="nova-working-context-label">Next move</span><span class="nova-working-context-value">${escapeHtml(wc.state.next_move)}</span></div>`
    );
  }

  if (wc.state.checkpoint) {
    items.push(
      `<div class="nova-working-context-row"><span class="nova-working-context-label">Checkpoint</span><span class="nova-working-context-value">${escapeHtml(wc.state.checkpoint)}</span></div>`
    );
  }

  const collapsedClass = wc.collapsed ? " is-collapsed" : "";
  const buttonLabel = wc.collapsed ? "Expand working context" : "Collapse working context";
  const chevron = wc.collapsed ? "▸" : "▾";

  console.log("renderWorkingContextPanel HTML", wc, items);

  return `
    <section class="nova-working-context-panel${collapsedClass}" data-working-context-panel>
      <button
        type="button"
        class="nova-working-context-toggle"
        data-working-context-toggle
        aria-label="${escapeHtml(buttonLabel)}"
        aria-expanded="${wc.collapsed ? "false" : "true"}"
      >
        <span class="nova-working-context-toggle-icon">${chevron}</span>
        <span class="nova-working-context-title">Working context</span>
      </button>
      <div class="nova-working-context-body">
        ${items.join("")}
      </div>
    </section>
  `;
}

function emptyWorkingContext() {
  return {
    show: false,
    text: "",
    state: {
      active_task: "",
      current_file: "",
      current_bug: "",
      last_success: "",
      next_move: "",
      checkpoint: "",
      updated_at: "",
    },
  };
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
  if (!els.memoryList) {
    els.memoryList = document.querySelector("[data-memory-list]");
  }

  if (!els.memoryList) return;

  const items = safeArray(state.memory)
    .map(normalizeMemoryItem)
    .sort(function (a, b) {
      return Date.parse(b.updated_at || b.created_at || "") - Date.parse(a.updated_at || a.created_at || "");
    });

  if (!items.length) {
    els.memoryList.innerHTML =
      '<div class="nova-memory-empty">' +
        '<div class="nova-memory-empty-title">No memory yet</div>' +
        '<div class="nova-memory-empty-copy">Start teaching Nova about you.</div>' +
        '<button class="nova-memory-add-btn">+ Add Memory</button>' +
      '</div>';

    wireMemoryControls();
    return;
  }

  let html =
    '<div class="nova-memory-toolbar">' +
      '<button class="nova-memory-add-btn">+ Add</button>' +
      '<button class="nova-memory-refresh-btn">Refresh</button>' +
    '</div>';

  const groups = {
    profile: [],
    identity: [],
    style: [],
    preference: [],
    project: [],
    goal: [],
    note: [],
  };

  items.forEach(function (item) {
    const kind = String(item.kind || "note").toLowerCase();
    if (groups[kind]) {
      groups[kind].push(item);
    } else {
      groups.note.push(item);
    }
  });

function wireMemoryClicks() {
  if (!els.memoryList) return;

  els.memoryList.onclick = function (e) {
    if (e.target.closest("[data-memory-delete]")) return;

    const btn = e.target.closest("[data-memory-id]");
    if (!btn) return;

    const memoryId = String(btn.getAttribute("data-memory-id") || "").trim();
    if (!memoryId) return;

    const item = safeArray(state.memory).find(function (entry) {
      return String(entry.id || "") === memoryId;
    });

    if (!item) return;

    openRail();
    setRailTab("memory");
    setRailSelectedItem("memory", memoryId);

    renderMemoryViewer(item);

    if (els.railTitle) els.railTitle.textContent = "Memory";
    if (els.railSubtitle) els.railSubtitle.textContent = String(item.kind || "note");
  };
}

  function renderMemorySection(title, list) {
    if (!list.length) return "";

    return (
      '<div class="nova-memory-section">' +
        '<div class="nova-memory-section-title">' + escapeHtml(title) + '</div>' +
        list.map(function (item) {
          const id = escapeHtml(item.id);
          const text = escapeHtml(summarizeMemoryText(item.text, 120));
          const kind = escapeHtml(item.kind || "note");
          const source = escapeHtml(item.source || "memory");
          const session = escapeHtml(item.session_id || "");

          return (
            '<div class="nova-memory-card" data-memory-id="' + id + '">' +
              '<div class="nova-memory-card-title">' + kind + '</div>' +
              '<div class="nova-memory-card-preview">' + text + '</div>' +
              '<div class="nova-memory-meta">' +
                (session ? '<span>' + session + '</span>' : '') +
                '<span>' + source + '</span>' +
              '</div>' +
              '<button class="nova-memory-delete" data-memory-delete="' + id + '">Remove</button>' +
            '</div>'
          );
        }).join("") +
      '</div>'
    );
  }

  html +=
    renderMemorySection("Identity", groups.profile.concat(groups.identity)) +
    renderMemorySection("Style", groups.style) +
    renderMemorySection("Preferences", groups.preference) +
    renderMemorySection("Project", groups.project) +
    renderMemorySection("Goals", groups.goal) +
    renderMemorySection("Notes", groups.note);

  els.memoryList.innerHTML = html;

  wireMemoryClicks();
  wireMemoryControls();

  document.querySelectorAll(".nova-memory-refresh-btn").forEach(function (btn) {
    if (btn.__wired) return;
    btn.__wired = true;

    btn.addEventListener("click", async function () {
      try {
        const res = await fetch("/api/memory");
        const data = await res.json();

        if (data && data.data && data.data.memory) {
          state.memory = data.data.memory;
          renderMemory();
        }
      } catch (e) {
        console.error("Memory refresh failed", e);
      }
    });
  });
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
    '<div style="display:flex;align-items:center;justify-content:space-between;">' +
    '<div class="nova-viewer-title">' + escapeHtml(item.kind || "note") + "</div>" +
    '<button data-close-rail="1" style="background:transparent;border:none;color:#fff;font-size:18px;cursor:pointer;">×</button>' +
    "</div>" +
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
    const incomingFinalMessages = finalEvent.messages.map(function (msg) {
      return typeof normalizeMessage === "function" ? normalizeMessage(msg) : msg;
    });

    if (incomingFinalMessages.length >= (state.messages || []).length) {
      state.messages = incomingFinalMessages;
    } else {
      console.warn("blocked finalEvent overwrite");
    }
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
      memory_used: payload.memory_used || []
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

      if (!response.ok || data.ok === false) {
        throw new Error(data.error || ("Request failed: " + response.status));
      }

      applyStatePayload(data);

      finishStreamUi({
        statusState: "idle",
        statusText: "Ready",
      });

      return data;
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

console.warn("[NovaComposerBundle] final /api/state refresh disabled to prevent chat wipe");

if (state.stream && state.stream.targetMessageId) {
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
    const deleteBtn = event.target.closest('[data-action="delete-artifact"]');
    if (deleteBtn) {
      event.preventDefault();
      event.stopPropagation();

      const id = deleteBtn.getAttribute("data-artifact-id");
      if (!id) return;

      const artifact = (state.artifacts || []).find(function (item) {
        return String(item && item.id) === String(id);
      });

      if (!artifact) return;

      state.artifacts = (state.artifacts || []).filter(function (item) {
        return String(item && item.id) !== String(id);
      });

      renderArtifacts();

      const undo = window.confirm("Artifact hidden. Undo delete?");
      if (undo) {
        state.artifacts.unshift(artifact);
        renderArtifacts();
        return;
      }

      try {
        const res = await fetch(`/api/artifacts/${encodeURIComponent(id)}`, {
          method: "DELETE",
          headers: { "Accept": "application/json" }
        });

        const data = await res.json();

        if (!data || data.ok === false) {
          alert("Permanent delete failed. Restoring artifact.");
          state.artifacts.unshift(artifact);
          renderArtifacts();
        }
      } catch (err) {
        console.error("Delete error:", err);
        alert("Permanent delete failed. Restoring artifact.");
        state.artifacts.unshift(artifact);
        renderArtifacts();
      }

      return;
    }

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

  if (!payload || typeof payload !== "object") {
    return payload;
  }

  if (payload.session && state.activeSessionId) {
    const payloadSessionId = String(payload.session.id || payload.active_session_id || "").trim();
    const activeId = String(state.activeSessionId || "").trim();

    if (payloadSessionId && activeId && payloadSessionId !== activeId) {
      console.warn("[NovaComposerBundle] skipped stale /api/state payload", {
        payloadSessionId,
        activeId,
      });
      return payload;
    }
  }

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

window.NovaComposerBundle = {
  applyBackendSessionState,
  jumpToSessionAndSync,
};

setTimeout(() => {
  const voiceBtn = document.querySelector('[data-action="voice"]');
  if (voiceBtn) voiceBtn.textContent = 'Mic';

  const attachBtn = document.querySelector('[data-attach-button]');
  if (attachBtn) attachBtn.textContent = '+';
}, 500);

})();

