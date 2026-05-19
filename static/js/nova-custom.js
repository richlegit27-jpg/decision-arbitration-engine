(function () {
  "use strict";

  if (window.NovaComposerBundle) return;

// ==============================
// NOVA GLOBAL HELPERS
// Must load before any composer chunk
// ==============================
window.NovaComposerState = window.NovaComposerState || window.state || {};
window.state = window.NovaComposerState;
window.els = window.els || {};

// Shorthand selectors
window.qs = function(selector, root) {
    return (root || document).querySelector(selector);
};

window.qsa = function(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
};

// Safe array
window.safeArray = function(arr) {
    return Array.isArray(arr) ? arr : [];
};

// Escape HTML
window.escapeHtml = function(str) {
    return String(str || "").replace(/[&<>'"]/g, function(tag) {
        const charsToReplace = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;',
        };
        return charsToReplace[tag] || tag;
    });
};

  // =============================
  // Chat Helpers
  // =============================
  window.setChatEmptyVisible = function (isVisible) {
    const el = qs("[data-chat-empty]");
    if (!el) return;
    el.hidden = !isVisible;
  };

  window.finishStreamUi = function () {
    try {
      if (window.NovaComposerState && window.NovaComposerState.stream) {
        window.NovaComposerState.stream.running = false;
      }
    } catch (_) {}
  };

  function log() {
    try {
      console.log("[NovaComposerBundle]", ...arguments);
    } catch (_) {}
  }

  // =============================
  // Session Helpers
  // =============================
  function applyBackendSessionState(payload, explicitSessionId) {
    const data = payload && typeof payload === "object" ? payload : {};
    if (explicitSessionId && typeof data === "object" && data) {
      state.activeSessionId = explicitSessionId;
    }
    state.sessionData = data;
  }

  // =============================
  // State Initialization
  // =============================
  window.NovaComposerState = window.NovaComposerState || {};
  const state = window.NovaComposerState;

  state.messages = state.messages || [];
  state.pendingUploads = state.pendingUploads || [];
  state.memory = state.memory || [];
  state.artifacts = state.artifacts || [];
  state.activeSessionId = state.activeSessionId || "";

  // =============================
  // End of Chunk 1
  // =============================
  console.log("[NovaComposerBundle] Chunk 1 loaded âœ…");
})();

(function(){
  "use strict";

  // =============================
  // Session Hydration & Deduplication
  // =============================
  function dedupeMessages(messages) {
    const seen = new Set();
    return safeArray(messages).filter(msg => {
      const key = msg && msg.id;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function hydrateSession(data, resolvedSession) {
    if (resolvedSession && Array.isArray(resolvedSession.messages)) {
      const incoming = dedupeMessages(resolvedSession.messages);
      state.messages = incoming;
    } else if (Array.isArray(data.messages)) {
      const incoming = dedupeMessages(data.messages);
      state.messages = incoming;
    }

    if (Array.isArray(data.artifacts)) {
      state.artifacts = safeArray(data.artifacts);
    }

    if (Array.isArray(data.memory)) {
      state.memory = data.memory;
    }

    console.log("[NOVA SESSION HYDRATE]", {
      activeSessionId: state.activeSessionId,
      message_count: Array.isArray(state.messages) ? state.messages.length : -1,
      messages: (state.messages||[]).map(msg=>({
        id: msg && msg.id,
        role: msg && msg.role,
        text: String((msg && msg.text)||"").slice(0,80),
      }))
    });

    renderChat();
    renderArtifacts();
  }

  // =============================
  // Render Helpers
  // =============================
  function renderChat() {
    const chatEl = qs("#chat-messages");
    if (!chatEl) return;
    chatEl.innerHTML = "";
    safeArray(state.messages).forEach(msg=>{
      const div = document.createElement("div");
      div.className = "chat-msg";
      div.textContent = msg.text || "";
      chatEl.appendChild(div);
    });
    chatEl.scrollTop = chatEl.scrollHeight;
  }

  function renderArtifacts() {
    const container = qs("#rail-artifacts");
    if (!container) return;
    container.innerHTML = "";
    safeArray(state.artifacts).forEach(a=>{
      const div = document.createElement("div");
      div.className = "rail-artifact";
      div.textContent = a.title || a.name || "Artifact";
      container.appendChild(div);
    });
  }

  // =============================
  // Attachment Handling
  // =============================
window.addAttachment = function(att) {
    if (!att || !att.id) return;

    // Ensure pendingUploads exists
    state.pendingUploads = state.pendingUploads || [];
    state.pendingUploads.push(att);

    renderPendingUploads();
};

  function renderPendingUploads() {
    const container = qs("#upload-staging");
    if (!container) return;
    container.innerHTML = "";
    safeArray(state.pendingUploads).forEach(item=>{
      const div = document.createElement("div");
      div.className = "nova-upload-chip";
      div.textContent = item.name || item.filename || "Attachment";
      container.appendChild(div);
    });
  }

  // =============================
  // Execution Panel
  // =============================
  window.updateExecutionStatus = function(status, currentStep, stepsCount) {
    const panel = qs("#execution-panel");
    if (!panel) return;
    qs(".exec-status", panel).textContent = status || "idle";
    qs(".exec-current", panel).textContent = currentStep || "-";
    qs(".exec-steps", panel).textContent = stepsCount || 0;
  };

  window.addExecutionStep = function(title) {
    const panel = qs("#rail-execution");
    if (!panel) return;
    const div = document.createElement("div");
    div.className = "rail-exec-step";
    div.textContent = title;
    panel.appendChild(div);
    state.rail.execution = state.rail.execution || [];
    state.rail.execution.push(title);
  };

  // =============================
  // Memory Panel
  // =============================
  window.addMemory = function(title) {
    const panel = qs("#rail-memory");
    if (!panel) return;
    const div = document.createElement("div");
    div.className = "rail-memory";
    div.textContent = title;
    panel.appendChild(div);
    state.memory.push(title);
  };

  // =============================
  // Web Panel
  // =============================
  window.addWebResult = function(title) {
    const panel = qs("#rail-web");
    if (!panel) return;
    const div = document.createElement("div");
    div.className = "rail-web";
    div.textContent = title;
    panel.appendChild(div);
    state.rail.web = state.rail.web || [];
    state.rail.web.push(title);
  };

  // =============================
  // TTS
  // =============================
  let TTSEnabled = false;
  window.toggleTTS = function(enabled){
    TTSEnabled = !!enabled;
    console.log("TTS Enabled:", TTSEnabled);
  };
  const ttsCheckbox = qs("#tts-toggle");
  if(ttsCheckbox){
    ttsCheckbox.addEventListener("change", e=>toggleTTS(e.target.checked));
  }

  // =============================
  // Initialize demo content
  // =============================
  console.log("[NovaComposerBundle] Chunk 2 loaded âœ…");

})();

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
}

function scheduleTokenFlush() {
  const tr = ensureTokenRenderState();
  if (tr.scheduled) return;
  tr.scheduled = true;
  requestAnimationFrame(flushTokensNow);
}

function appendTextToMessage(messageId, chunk) {
  if (!messageId || !chunk) return;
  const index = state.messages.findIndex(msg => msg && msg.id === messageId);
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

function upsertMessage({ id, role, text = "", attachments = [], meta = {}, streaming = false, pending = true, stopped = false, error = false }) {
  const index = state.messages.findIndex(msg => msg && msg.id === id);
  const message = {
    id,
    role,
    text,
    attachments,
    meta,
    streaming,
    pending,
    stopped,
    error,
  };

  if (index === -1) {
    state.messages.push(message);
  } else {
    state.messages[index] = { ...state.messages[index], ...message };
  }

  renderChat();
}

function handleExecutionStep(action) {
  if (!state.execution) return;
  const step = state.execution.currentStep;
  if (!step) return;

  try {
    switch (action) {
      case "run_step":
        step.status = "running";
        executeStep(step);
        break;
      case "run_all":
        state.execution.steps.forEach(s => executeStep(s));
        break;
      case "retry_failed":
        state.execution.steps.filter(s => s.status === "failed").forEach(s => executeStep(s));
        break;
      case "stop":
        state.execution.currentStep.status = "stopped";
        break;
    }
  } catch (err) {
    console.error("Execution step error:", err);
    step.status = "failed";
  }

  updateExecutionPanel();
}

function executeStep(step) {
  if (!step) return;
  step.status = "running";
  // run step logic here
  step.status = "complete";
  updateExecutionPanel();
}

function updateExecutionPanel() {
  const panel = document.querySelector("[data-execution-panel]");
  if (!panel || !state.execution) return;

  const stepCount = state.execution.steps.length;
  const completed = state.execution.steps.filter(s => s.status === "complete").length;

  panel.querySelector("[data-step-count]").textContent = `${completed} / ${stepCount}`;
  panel.querySelector("[data-current-step]").textContent = state.execution.currentStep?.title || "N/A";
}

// Attachment click handling
function renderAttachmentChip(attachment) {
  const chip = document.createElement("div");
  chip.className = "attachment-chip";
  chip.textContent = attachment.name || "file";
  chip.onclick = () => handleAttachmentClick(attachment);
  return chip;
}

function handleAttachmentClick(att) {
  if (!att) return;
  if (att.url && att.type === "image") {
    showImagePreview(att.url);
  } else if (att.url) {
    window.open(att.url, "_blank");
  }
  state.lastClickedAttachment = att.id;
  console.log("Attachment clicked:", att);
}

function showImagePreview(url) {
  const preview = document.getElementById("image-preview");
  if (!preview) return;
  preview.src = url;
  preview.style.display = "block";
}

// Memory & artifact updates
function saveMemoryItem(item) {
  if (!item || !item.id) return;
  state.memory = state.memory || {};
  state.memory[item.id] = item;
}

function saveArtifact(artifact) {
  if (!artifact || !artifact.id) return;
  state.artifacts = state.artifacts || {};
  state.artifacts[artifact.id] = artifact;
}

// TTS / audio triggers
function playTTS(messageId) {
  const msg = state.messages.find(m => m.id === messageId);
  if (!msg || !msg.text) return;

  if (state.tts.audio) {
    state.tts.audio.pause();
  }

console.warn("[Nova] old fake playTTS disabled. Use nova-tts-player.js.");
return;

  audio.onended = () => {
    state.tts.playing = false;
    state.tts.audio = null;
  };
}

function stopTTS() {
  if (state.tts.audio) {
    state.tts.audio.pause();
    state.tts.audio = null;
    state.tts.playing = false;
  }
}

// ==============================
// End of Chunk 3
// ==============================

// ==============================
// NOVA COMPOSER BUNDLE â€” CHUNK 4
// Lines ~2,101â€“2,800
// Includes: execution panel updates, TTS integration, attachment rendering, working state
// ==============================

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

function scheduleTokenFlush() {
  const tr = ensureTokenRenderState();
  if (tr.scheduled) return;
  tr.scheduled = true;
  requestAnimationFrame(flushTokensNow);
}

// Render chat messages
function renderChat() {
  if (!els.chatThread) return;

  window.setChatEmptyVisible(state.messages.length === 0);

  const workingContextHtml = "";
  const messagesHtml = state.messages.map(renderMessageCard).join("");
  let nextHtml = workingContextHtml + messagesHtml;

  if (els.chatThread.__lastRenderHtml !== nextHtml) {
    els.chatThread.innerHTML = nextHtml;
    els.chatThread.__lastRenderHtml = nextHtml;
  }

  wireWorkingContextPanel();
  els.chatThread.__autoOpenedSource = "";
}

// Execution panel helpers
function wireExecutionButtons() {
  document.querySelectorAll("[data-exec-action]").forEach(btn => {
    btn.onclick = e => {
      const action = btn.dataset.execAction;
      handleExecutionStep(action);
    };
  });
}

function updateExecutionStepDisplay() {
  const panel = document.querySelector("[data-execution-panel]");
  if (!panel || !state.execution) return;

  const stepCount = state.execution.steps.length;
  const completed = state.execution.steps.filter(s => s.status === "complete").length;

  const currentStepTitle = state.execution.currentStep?.title || "N/A";
  panel.querySelector("[data-step-count]").textContent = `${completed} / ${stepCount}`;
  panel.querySelector("[data-current-step]").textContent = currentStepTitle;
}

// Attachment rendering
function renderAttachmentChips(attachments = []) {
  if (!els.uploadStaging) return;
  els.uploadStaging.innerHTML = attachments.map(att => {
    const chip = renderAttachmentChip(att);
    return chip.outerHTML;
  }).join("");
  els.uploadStaging.hidden = attachments.length === 0;
}

// Auto-play TTS for new assistant messages
function shouldAutoPlayTtsForMessage(message) {
  if (!message || message.role !== "assistant" || !message.text) return false;
  return state.settings?.tts?.autoPlay;
}

function maybeAutoPlayTts(message) {
  if (shouldAutoPlayTtsForMessage(message)) {
    playTTS(message.id);
  }
}

// Working state utilities
function updateWorkingState(patch = {}) {
  if (!state.workingState) state.workingState = {};
  state.workingState = { ...state.workingState, ...patch };
  state.workingState.updatedAt = Date.now();
}

function getWorkingState() {
  return { ...(state.workingState || {}) };
}

// Artifact / memory helpers
function saveArtifactOrMemory(obj) {
  if (!obj || !obj.id) return;

  if (obj.type === "memory") saveMemoryItem(obj);
  else saveArtifact(obj);
}

// ==============================
// End of Chunk 4
// ==============================

// ==============================
// NOVA COMPOSER BUNDLE â€” CHUNK 5
// Lines ~2,801â€“3,500
// Includes: streaming text handling, token flush scheduling, execution helpers
// ==============================

// Ensure streaming state is initialized
function ensureStreamState() {
  if (!state.stream) {
    state.stream = {
      messageId: "",
      placeholderId: "",
      buffer: "",
      controller: null,
    };
  }
  return state.stream;
}

// Append text chunk to a message
function appendChunkToMessage(messageId, chunk) {
  if (!messageId || !chunk) return;
  const index = state.messages.findIndex(msg => msg && msg.id === messageId);
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
  renderChat();
}

// Streaming flush helpers
function flushStreamBuffer() {
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
  appendChunkToMessage(tr.targetMessageId, chunk);
}

function scheduleStreamFlush() {
  const tr = ensureTokenRenderState();
  if (tr.scheduled) return;
  tr.scheduled = true;
  requestAnimationFrame(flushStreamBuffer);
}

// Execute step helper
function runExecutionStep(step) {
  if (!step) return;
  step.status = "running";
  try {
    // Actual step logic here
    step.status = "complete";
  } catch (err) {
    console.error("Step execution failed:", err);
    step.status = "failed";
  }
  updateExecutionStepDisplay();
}

// Run all steps
function runAllExecutionSteps() {
  if (!state.execution || !state.execution.steps) return;
  state.execution.steps.forEach(runExecutionStep);
  updateExecutionStepDisplay();
}

// Retry failed steps
function retryFailedSteps() {
  if (!state.execution || !state.execution.steps) return;
  const failedSteps = state.execution.steps.filter(s => s.status === "failed");
  failedSteps.forEach(runExecutionStep);
  updateExecutionStepDisplay();
}

// Stop current execution
function stopExecution() {
  if (!state.execution || !state.execution.currentStep) return;
  state.execution.currentStep.status = "stopped";
  updateExecutionStepDisplay();
}

// ==============================
// End of Chunk 5
// ==============================

// ==============================
// NOVA COMPOSER BUNDLE â€” CHUNK 6
// Lines ~3,501â€“4,200
// Includes: TTS control, attachment & message utilities, execution helpers
// ==============================

// Stop any TTS currently playing
function stopAllTTS() {
  if (state.tts.audio) {
    state.tts.audio.pause();
    state.tts.audio = null;
    state.tts.playing = false;
  }
}

// Auto-play TTS for assistant messages if enabled
function maybePlayTTS(message) {
  if (!message || message.role !== "assistant" || !message.text) return;
  if (state.settings?.tts?.autoPlay) playTTS(message.id);
}

// Render a single message card
function renderMessageCard(message) {
  if (!message) return "";
  const roleClass = message.role === "assistant" ? "assistant-msg" : "user-msg";
  return `
    <div class="message-card ${roleClass}" id="msg-${message.id}">
      <div class="message-text">${escapeHtml(message.text)}</div>
      ${renderAttachments(message.attachments)}
    </div>
  `;
}

// Render attachments for a message
function renderAttachments(attachments = []) {
  if (!attachments.length) return "";
  return attachments.map(att => `<div class="attachment-chip">${escapeHtml(att.name || "file")}</div>`).join("");
}

// Scroll chat to bottom
function scrollChatToBottom(smooth = false) {
  if (!els.chatThread) return;
  els.chatThread.scrollTo({
    top: els.chatThread.scrollHeight,
    behavior: smooth ? "smooth" : "auto"
  });
}

// Execution button wiring
function wireExecutionPanelButtons() {
  document.querySelectorAll("[data-exec-action]").forEach(btn => {
    btn.onclick = e => {
      const action = btn.dataset.execAction;
      handleExecutionStep(action);
    };
  });
}

// Update execution step panel
function updateExecutionPanelDisplay() {
  const panel = document.querySelector("[data-execution-panel]");
  if (!panel || !state.execution) return;

  const steps = state.execution.steps || [];
  const completed = steps.filter(s => s.status === "complete").length;
  const currentTitle = state.execution.currentStep?.title || "N/A";

  panel.querySelector("[data-step-count]").textContent = `${completed} / ${steps.length}`;
  panel.querySelector("[data-current-step]").textContent = currentTitle;
}

// Handle an attachment click
function handleAttachmentClickEvent(att) {
  if (!att || !att.url) return;
  if (att.type === "image") {
    showImagePreview(att.url);
  } else {
    window.open(att.url, "_blank");
  }
  state.lastClickedAttachment = att.id;
}

// Show image preview
function showImagePreview(url) {
  const preview = document.getElementById("image-preview");
  if (!preview) return;
  preview.src = url;
  preview.style.display = "block";
}

// ==============================
// End of Chunk 6
// ==============================

// ==============================
// NOVA COMPOSER BUNDLE â€” CHUNK 7
// Lines ~4,201â€“4,900
// Includes: streaming queue, token flush, execution control, and TTS helpers
// ==============================

// Initialize streaming buffer
function initStreamBuffer() {
  if (!state.stream) {
    state.stream = {
      messageId: "",
      placeholderId: "",
      buffer: "",
      controller: null,
    };
  }
  state.stream.buffer = "";
  state.stream.messageId = "";
  state.stream.placeholderId = "";
  if (state.stream.controller) {
    state.stream.controller.abort();
    state.stream.controller = null;
  }
}

// Queue a token chunk for streaming
function queueTokenChunk(chunk, messageId) {
  if (!chunk || !messageId) return;
  const tr = ensureTokenRenderState();
  tr.buffer += chunk;
  tr.targetMessageId = messageId;

  if (!tr.scheduled) {
    scheduleStreamFlush();
  }
}

// Execute next step in execution queue
function executeNextStep() {
  if (!state.execution || !state.execution.steps) return;
  const currentStep = state.execution.steps.find(s => s.status === "pending");
  if (!currentStep) return;

  runExecutionStep(currentStep);
  state.execution.currentStep = currentStep;
  updateExecutionPanelDisplay();
}

// Auto-play TTS for newly appended message text
function autoPlayTtsIfNeeded(message) {
  if (!message || message.role !== "assistant") return;
  if (!state.settings?.tts?.autoPlay) return;

  playTTS(message.id);
}

// Save memory items safely
function saveMemoryItemSafe(item) {
  if (!item || !item.id) return;
  state.memory = state.memory || {};
  state.memory[item.id] = item;
}

// Save artifact safely
function saveArtifactSafe(artifact) {
  if (!artifact || !artifact.id) return;
  state.artifacts = state.artifacts || {};
  state.artifacts[artifact.id] = artifact;
}

// Stop currently playing TTS
function stopCurrentTts() {
  if (state.tts.audio) {
    state.tts.audio.pause();
    state.tts.audio = null;
    state.tts.playing = false;
  }
}

// ==============================
// End of Chunk 7
// ==============================

// ==============================
// NOVA COMPOSER BUNDLE â€” CHUNK 8
// Lines ~4,901â€“5,600
// Includes: chat rendering, attachment wiring, execution helpers, TTS management
// ==============================

// Render the chat thread
function renderFullChat() {
  if (!els.chatThread) return;

  const messagesHtml = state.messages.map(renderMessageCard).join("");
  const nextHtml = messagesHtml;

  if (els.chatThread.__lastRenderHtml !== nextHtml) {
    els.chatThread.innerHTML = nextHtml;
    els.chatThread.__lastRenderHtml = nextHtml;
  }

  wireWorkingContextPanel();
}

// Wire attachment click events
function wireAttachmentChips() {
  document.querySelectorAll(".attachment-chip").forEach(chip => {
    chip.onclick = e => {
      const attId = chip.dataset.attachmentId;
      const attachment = state.lastMessageAttachments?.find(a => a.id === attId);
      handleAttachmentClickEvent(attachment);
    };
  });
}

// Execute step button wiring
function wireExecutionButtonsPanel() {
  document.querySelectorAll("[data-exec-action]").forEach(btn => {
    btn.onclick = e => {
      const action = btn.dataset.execAction;
      handleExecutionStep(action);
    };
  });
}

// Scroll chat to bottom safely
function scrollChatBottom(smooth = false) {
  if (!els.chatThread) return;
  els.chatThread.scrollTo({
    top: els.chatThread.scrollHeight,
    behavior: smooth ? "smooth" : "auto",
  });
}

// Auto-play TTS for last assistant message
function autoPlayTtsLastMessage() {
  const msg = state.messages.slice().reverse().find(m => m.role === "assistant");
  if (!msg) return;
  maybePlayTTS(msg);
}

// Update execution panel after step change
function refreshExecutionPanel() {
  if (!state.execution) return;
  const panel = document.querySelector("[data-execution-panel]");
  if (!panel) return;

  const steps = state.execution.steps || [];
  const completed = steps.filter(s => s.status === "complete").length;
  const currentTitle = state.execution.currentStep?.title || "N/A";

  panel.querySelector("[data-step-count]").textContent = `${completed} / ${steps.length}`;
  panel.querySelector("[data-current-step]").textContent = currentTitle;
}

// ==============================
// End of Chunk 8
// ==============================

// ==============================
// NOVA COMPOSER BUNDLE â€” CHUNK 9
// Lines ~5,601â€“6,300
// Includes: streaming flush, token handling, execution helpers, TTS
// ==============================

// Streaming token flush helpers
function flushStreamTokensNow() {
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

  appendChunkToMessage(tr.targetMessageId, chunk);
  renderChat();
}

function scheduleStreamTokens() {
  const tr = ensureTokenRenderState();
  if (tr.scheduled) return;
  tr.scheduled = true;
  requestAnimationFrame(flushStreamTokensNow);
}

// Execute a single step safely
function runSingleStep(step) {
  if (!step) return;
  try {
    step.status = "running";
    // Step logic here
    step.status = "complete";
  } catch (err) {
    console.error("Step failed:", err);
    step.status = "failed";
  }
  refreshExecutionPanel();
}

// Execute all steps
function runAllSteps() {
  if (!state.execution || !state.execution.steps) return;
  state.execution.steps.forEach(runSingleStep);
  refreshExecutionPanel();
}

// Retry all failed steps
function retryFailedExecutionSteps() {
  if (!state.execution || !state.execution.steps) return;
  const failedSteps = state.execution.steps.filter(s => s.status === "failed");
  failedSteps.forEach(runSingleStep);
  refreshExecutionPanel();
}

// Stop current step
function stopCurrentExecution() {
  if (!state.execution || !state.execution.currentStep) return;
  state.execution.currentStep.status = "stopped";
  refreshExecutionPanel();
}

// TTS helpers
function playTTSForMessage(messageId) {
  const msg = state.messages.find(m => m.id === messageId);
  if (!msg || !msg.text) return;

console.warn("[Nova] old fake playTTSForMessage disabled. Use nova-tts-player.js.");
return;

  audio.onended = () => {
    state.tts.audio = null;
    state.tts.playing = false;
  };

  audio.play();
}

function stopCurrentTts() {
  if (state.tts.audio) {
    state.tts.audio.pause();
    state.tts.audio = null;
    state.tts.playing = false;
  }
}

// ==============================
// End of Chunk 9
// ==============================

// ==============================
// NOVA COMPOSER BUNDLE â€” CHUNK 10
// Lines ~6,301â€“7,000
// Includes: final execution helpers, streaming flush, attachment & TTS cleanup
// ==============================

// Append a text chunk safely to a message
function appendTextSafe(messageId, chunk) {
  if (!messageId || !chunk) return;
  const index = state.messages.findIndex(m => m.id === messageId);
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
  renderChat();
}

// Flush any pending streaming text
function flushPendingStream() {
  const tr = ensureTokenRenderState();
  if (!tr.targetMessageId || !tr.buffer) return;

  const chunk = tr.buffer;
  tr.buffer = "";
  tr.scheduled = false;
  tr.rafId = 0;
  tr.lastFlushAt = Date.now();

  appendTextSafe(tr.targetMessageId, chunk);
}

// Wire execution panel buttons
function wireExecPanelButtons() {
  document.querySelectorAll("[data-exec-action]").forEach(btn => {
    btn.onclick = () => handleExecutionStep(btn.dataset.execAction);
  });
}

// Render attachments for a message
function renderMessageAttachments(message) {
  if (!message || !message.attachments) return "";
  return message.attachments.map(att => {
    const chip = `<div class="attachment-chip">${escapeHtml(att.name || "file")}</div>`;
    return chip;
  }).join("");
}

// Scroll chat safely
function scrollToBottom(smooth = false) {
  if (!els.chatThread) return;
  els.chatThread.scrollTo({
    top: els.chatThread.scrollHeight,
    behavior: smooth ? "smooth" : "auto",
  });
}

// Stop TTS
function stopAllTTS() {
  if (state.tts.audio) {
    state.tts.audio.pause();
    state.tts.audio = null;
    state.tts.playing = false;
  }
}

// Auto-play TTS for latest assistant message
function autoPlayLastAssistantTTS() {
  const msg = state.messages.slice().reverse().find(m => m.role === "assistant");
  if (!msg) return;
  maybePlayTTS(msg);
}

// ==============================
// End of Chunk 10 â€” Complete JS Bundle
// ==============================

// =====================================================
// NOVA EMERGENCY CHAT BRIDGE
// Append at bottom of nova-custom.js
// =====================================================
(function () {
    "use strict";

    if (window.NovaEmergencyBridgeBooted) return;
    window.NovaEmergencyBridgeBooted = true;

    const state = window.NovaComposerState || window.state || {};
    window.NovaComposerState = state;
    window.state = state;

    state.messages = Array.isArray(state.messages) ? state.messages : [];
    state.activeSessionId = state.activeSessionId || "";

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function qsa(selector, root) {
        return Array.from((root || document).querySelectorAll(selector));
    }

    function escapeHtml(value) {
        return String(value || "").replace(/[&<>'"]/g, function (char) {
            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                "'": "&#39;",
                '"': "&quot;",
            }[char] || char;
        });
    }

    function findInput() {
        return (
            qs("[data-composer-input]") ||
            qs("[data-chat-input]") ||
            qs("#composer-input") ||
            qs("#chat-input") ||
            qs("#message-input") ||
            qs("textarea")
        );
    }

    function findThread() {
        return (
            qs("[data-chat-thread]") ||
            qs("[data-messages]") ||
            qs("#chat-thread") ||
            qs("#chat-messages") ||
            qs(".chat-thread") ||
            qs(".messages")
        );
    }

    function findSendButton() {
        return (
            qs("[data-send-button]") ||
            qs("[data-composer-send]") ||
            qs("[data-action='send']") ||
            qs("#send-button") ||
            qs("#sendBtn") ||
            qsa("button").find(function (btn) {
                const text = String(btn.textContent || "").toLowerCase().trim();
                return text === "send" || text.includes("send");
            })
        );
    }

    function getSessionId() {
        return (
            state.activeSessionId ||
            document.body.getAttribute("data-session-id") ||
            ""
        );
    }

    function setSessionId(sessionId) {
        if (!sessionId) return;
        state.activeSessionId = sessionId;
        document.body.setAttribute("data-session-id", sessionId);
    }

    function normalizeMessage(msg) {
        msg = msg || {};
        return {
            id: msg.id || msg.message_id || ("msg_" + Date.now() + "_" + Math.random().toString(16).slice(2)),
            role: msg.role || "assistant",
            text: msg.text || msg.assistant_text || msg.content || "",
            attachments: Array.isArray(msg.attachments) ? msg.attachments : [],
            meta: msg.meta || {},
        };
    }

    function renderMessages() {
        const thread = findThread();
        if (!thread) return;

        thread.innerHTML = state.messages.map(function (msg) {
            const role = msg.role === "user" ? "user" : "assistant";
            return (
                '<div class="nova-message nova-message-' + role + '">' +
                    '<div class="nova-message-role">' + escapeHtml(role) + "</div>" +
                    '<div class="nova-message-text">' + escapeHtml(msg.text) + "</div>" +
                "</div>"
            );
        }).join("");

        thread.scrollTop = thread.scrollHeight;
    }

function addMessage(role, text, extra) {
    const msg = Object.assign(
        {
            id: "local_" + Date.now() + "_" + Math.random().toString(16).slice(2),
            role: role,
            text: text || "",
            created_at: new Date().toISOString()
        },
        extra || {}
    );

    state.messages.push(msg);
    renderMessages();
    return msg;
}

    async function sendMessage() {
        const input = findInput();
        if (!input) {
            console.error("[NovaEmergencyBridge] No composer input found.");
            return;
        }

        const text = String(input.value || "").trim();
        if (!text) return;

        input.value = "";
        addMessage("user", text);

        const placeholder = addMessage("assistant", "Thinking...");

        try {
            const payload = {
                user_text: text,
                session_id: getSessionId(),
                attachments: Array.isArray(state.pendingUploads) ? state.pendingUploads : [],
            };

            window.__lastNovaPayload = payload;
            console.log("[NovaEmergencyBridge] outgoing payload", payload);

            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            window.__lastNovaResponse = data;

            console.log("[NovaEmergencyBridge] chat response data", data);
            console.log("[NovaEmergencyBridge] route/debug", data.debug);
            console.log(
                "[NovaEmergencyBridge] execution_state",
                data.execution_state || data.active_execution || data.execution
            );

            if (data.session_id || (data.session && data.session.id)) {
                setSessionId(data.session_id || data.session.id);
            }

const assistant =
    data.assistant_message ||
    {
        role: "assistant",
        text: data.assistant_text || data.text || data.output_text || "No response text returned.",
    };

placeholder.text =
    assistant.text ||
    assistant.content ||
    data.assistant_text ||
    data.text ||
    data.output_text ||
    (data.saved_artifact && data.saved_artifact.summary) ||
    (data.saved_artifact && data.saved_artifact.body) ||
    "No response text returned.";

placeholder.role = "assistant";

const assistantImageUrl =
    assistant.image_url ||
    data.image_url ||
    (assistant.meta && assistant.meta.image_url) ||
    (assistant.meta && assistant.meta.preview) ||
    (data.meta && data.meta.image_url) ||
    (data.saved_artifact && data.saved_artifact.image_url) ||
    (data.saved_artifact && data.saved_artifact.preview) ||
    (data.saved_artifact &&
        data.saved_artifact.viewer &&
        data.saved_artifact.viewer.image_url) ||
    "";

placeholder.image_url = assistantImageUrl;

placeholder.meta = Object.assign(
    {},
    placeholder.meta || {},
    assistant.meta || {},
    data.meta || {},
    (data.saved_artifact && data.saved_artifact.meta) || {},
    {
        image_url: assistantImageUrl
    }
);

console.log("[NovaEmergencyBridge] assistant image url", placeholder.image_url);

renderMessages();

console.log("[NovaEmergencyBridge] forced image render after response", {
    image_url: placeholder.image_url,
    images: document.querySelectorAll(
    ".nova-message img, .assistant-msg img, .user-msg img, .message img, .chat-message img, .nova-message-image-wrap img"
).length
});

if (
    placeholder.image_url &&
    document.querySelectorAll(
        ".nova-message img, .assistant-msg img, .user-msg img, .message img, .chat-message img, .nova-message-image-wrap img"
    ).length === 0
) {
    const thread = findThread();

    const cards = thread
        ? thread.querySelectorAll(
            ".nova-message, .assistant-msg, .user-msg, .message, .chat-message, [data-message-role]"
        )
        : [];

    const lastCard = cards.length
        ? cards[cards.length - 1]
        : (thread ? thread.lastElementChild : null);

    console.log("[NovaEmergencyBridge] injection target check", {
        hasThread: !!thread,
        cardCount: cards.length,
        hasLastCard: !!lastCard,
        lastCard: lastCard,
        image_url: placeholder.image_url
    });

    if (lastCard && !lastCard.querySelector("img")) {
        const wrap = document.createElement("div");
        wrap.className = "nova-message-image-wrap";
        wrap.style.marginTop = "10px";

        const img = document.createElement("img");
        img.src = placeholder.image_url;
        img.alt = "Generated image";
        img.style.width = "100%";
        img.style.maxWidth = "420px";
        img.style.height = "auto";
        img.style.borderRadius = "14px";
        img.style.display = "block";
        img.style.border = "1px solid rgba(255,255,255,0.12)";

        wrap.appendChild(img);
        lastCard.appendChild(wrap);

        console.log("[NovaEmergencyBridge] direct image injected", {
            image_url: placeholder.image_url,
            images: document.querySelectorAll(
                ".nova-message img, .assistant-msg img, .user-msg img, .message img, .chat-message img, .nova-message-image-wrap img"
            ).length
        });
    }
}

if (window.NovaEmergencyRestoreArtifacts) {
    setTimeout(window.NovaEmergencyRestoreArtifacts, 250);
    setTimeout(window.NovaEmergencyRestoreArtifacts, 1000);
}

setTimeout(function () {
    if (!placeholder.image_url) return;

    const thread = findThread();
    const cards = thread
        ? thread.querySelectorAll(
            ".nova-message, .assistant-msg, .user-msg, .message, .chat-message, [data-message-role]"
        )
        : [];

    const lastCard = cards.length
        ? cards[cards.length - 1]
        : (thread ? thread.lastElementChild : null);

    const existingImages = document.querySelectorAll(
        ".nova-message img, .assistant-msg img, .user-msg img, .message img, .chat-message img, .nova-message-image-wrap img"
    ).length;

    console.log("[NovaEmergencyBridge] delayed image reinject check", {
        image_url: placeholder.image_url,
        existingImages: existingImages,
        hasLastCard: !!lastCard
    });

    if (lastCard && existingImages === 0) {
        const wrap = document.createElement("div");
        wrap.className = "nova-message-image-wrap";
        wrap.style.marginTop = "10px";

        const img = document.createElement("img");
        img.src = placeholder.image_url;
        img.alt = "Generated image";
        img.style.width = "100%";
        img.style.maxWidth = "420px";
        img.style.height = "auto";
        img.style.borderRadius = "14px";
        img.style.display = "block";
        img.style.border = "1px solid rgba(255,255,255,0.12)";

        wrap.appendChild(img);
        lastCard.appendChild(wrap);

        console.log("[NovaEmergencyBridge] delayed image reinjected", {
            image_url: placeholder.image_url,
            images: document.querySelectorAll(
                ".nova-message img, .assistant-msg img, .user-msg img, .message img, .chat-message img, .nova-message-image-wrap img"
            ).length
        });
    }
}, 1600);

let executionFromResponse =
    data.execution_state ||
    data.active_execution ||
    data.execution ||
    (data.session && data.session.execution_state) ||
    (data.session && data.session.active_execution) ||
    null;

if (
    !executionFromResponse &&
    data.debug &&
    data.debug.route === "execution_plan_created"
) {
    executionFromResponse = {
        status: "running",
        current_step: "Step 1",
        steps: [
            {
                title: "Step 1",
                description: "Clarify the goal and prepare the work area.",
                status: "pending",
            },
            {
                title: "Step 2",
                description: "Perform the main implementation or test action.",
                status: "pending",
            },
            {
                title: "Step 3",
                description: "Verify the result and summarize the next move.",
                status: "pending",
            },
        ],
    };
}

if (
    executionFromResponse &&
    typeof executionFromResponse === "object" &&
    Array.isArray(executionFromResponse.steps) &&
    executionFromResponse.steps.length > 0
) {
    state.execution = state.execution || {};
    state.execution.status = executionFromResponse.status || "running";
    state.execution.currentStep =
        executionFromResponse.current_step ||
        executionFromResponse.currentStep ||
        executionFromResponse.current_step_title ||
        executionFromResponse.currentStepTitle ||
        executionFromResponse.current_step_name ||
        executionFromResponse.currentStepName ||
        "Step 1";
    state.execution.steps = executionFromResponse.steps;
    state.execution.lastResponse = data;

    if (typeof window.NovaEmergencyRenderExecution === "function") {
        window.NovaEmergencyRenderExecution();
    }

    console.log("[NovaEmergencyBridge] execution synced from chat response", {
        status: state.execution.status,
        steps: state.execution.steps.length,
    });
}

state.pendingUploads = [];
if (
    window.NovaEmergencyAttachments &&
    typeof window.NovaEmergencyAttachments.render === "function"
) {
    window.NovaEmergencyAttachments.render();
}

renderMessages();

        } catch (err) {
            console.error("[NovaEmergencyBridge] Send failed:", err);
            placeholder.text = "Send failed. Check Flask console and browser network tab.";
            renderMessages();
        }
    }

    function wireSend() {
        const button = findSendButton();
        const input = findInput();

        if (button && !button.__novaEmergencyWired) {
            button.__novaEmergencyWired = true;
            button.addEventListener("click", function (event) {
                event.preventDefault();
                sendMessage();
            });
        }

        if (input && !input.__novaEmergencyWired) {
            input.__novaEmergencyWired = true;
            input.addEventListener("keydown", function (event) {
                if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage();
                }
            });
        }

        console.log("[NovaEmergencyBridge] wired", {
            hasInput: !!input,
            hasButton: !!button,
            hasThread: !!findThread(),
        });
    }

    window.NovaEmergencySend = sendMessage;
    window.NovaEmergencyRender = renderMessages;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", wireSend);
    } else {
        wireSend();
    }

    setTimeout(wireSend, 500);
    setTimeout(wireSend, 1500);
})();

// =====================================================
// NOVA EMERGENCY ATTACHMENT BRIDGE
// Append at bottom of nova-custom.js
// =====================================================
(function () {
    "use strict";

    if (window.NovaEmergencyAttachmentBridgeBooted) return;
    window.NovaEmergencyAttachmentBridgeBooted = true;

    const state = window.NovaComposerState || window.state || {};
    window.NovaComposerState = state;
    window.state = state;

    state.pendingUploads = Array.isArray(state.pendingUploads) ? state.pendingUploads : [];

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function qsa(selector, root) {
        return Array.from((root || document).querySelectorAll(selector));
    }

    function findFileInput() {
        return (
            qs("input[type='file'][data-upload-input]") ||
            qs("input[type='file'][data-attachment-input]") ||
            qs("input[type='file']") ||
            null
        );
    }

function findUploadStaging() {
    let container =
        qs("[data-upload-staging]") ||
        qs("#upload-staging") ||
        qs(".upload-staging") ||
        qs("[data-attachments]");

    if (!container) {
        const input = (
            qs("[data-composer-input]") ||
            qs("[data-chat-input]") ||
            qs("#composer-input") ||
            qs("#chat-input") ||
            qs("#message-input") ||
            qs("textarea")
        );

        container = document.createElement("div");
        container.id = "upload-staging";
        container.setAttribute("data-upload-staging", "true");
        container.style.display = "flex";
        container.style.flexWrap = "wrap";
        container.style.gap = "8px";
        container.style.margin = "8px 0";
        container.style.padding = "8px";
        container.style.border = "1px solid rgba(255,255,255,0.15)";
        container.style.borderRadius = "10px";

        if (input && input.parentNode) {
            input.parentNode.insertBefore(container, input);
        } else {
            document.body.appendChild(container);
        }
    }

    return container;
}

function renderPendingUploads() {
    let container = findUploadStaging();

    if (!container) {
        container = document.createElement("div");
        container.id = "upload-staging";
        container.setAttribute("data-upload-staging", "true");

        const input =
            qs("[data-composer-input]") ||
            qs("[data-chat-input]") ||
            qs("#composer-input") ||
            qs("#chat-input") ||
            qs("#message-input") ||
            qs("textarea");

        if (input && input.parentNode) {
            input.parentNode.insertBefore(container, input);
        } else {
            document.body.appendChild(container);
        }
    }

    container.hidden = false;
    container.style.display = "flex";
    container.style.flexWrap = "wrap";
    container.style.gap = "8px";
    container.style.margin = "8px 0";
    container.style.padding = "8px";
    container.style.minHeight = "36px";
    container.style.border = "1px solid rgba(255,255,255,0.25)";
    container.style.borderRadius = "10px";
    container.style.position = "relative";
    container.style.zIndex = "9999";

    container.innerHTML = "";

    const uploads = Array.isArray(state.pendingUploads) ? state.pendingUploads : [];

    if (!uploads.length) {
        container.innerHTML = '<div style="font-size:12px;opacity:0.65;">No attachments staged</div>';
        return;
    }

    uploads.forEach(function (att, index) {
        const chip = document.createElement("div");
        chip.className = "nova-upload-chip";
        chip.setAttribute("data-emergency-attachment-index", String(index));

        const name = att.name || att.filename || att.stored_name || "attachment";
        const status = att.status || "uploaded";

        chip.textContent = "ðŸ“Ž " + name + " â€” " + status;
        chip.style.padding = "6px 10px";
        chip.style.border = "1px solid rgba(255,255,255,0.25)";
        chip.style.borderRadius = "999px";
        chip.style.cursor = att.url ? "pointer" : "default";
        chip.style.fontSize = "12px";
        chip.style.background = "rgba(255,255,255,0.08)";
        chip.style.color = "inherit";
        chip.style.maxWidth = "320px";
        chip.style.overflow = "hidden";
        chip.style.textOverflow = "ellipsis";
        chip.style.whiteSpace = "nowrap";

        chip.addEventListener("click", function () {
            if (att.url) {
                window.open(att.url, "_blank");
            }
        });

        container.appendChild(chip);
    });

    console.log("[NovaEmergencyAttachmentBridge] rendered chips", {
        count: uploads.length,
        container: container,
        uploads: uploads,
    });
}

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData,
        });

        const data = await response.json();

        if (!response.ok || data.ok === false) {
            throw new Error(data.error || "Upload failed");
        }

return {
    id: data.id || data.attachment_id || ("att_" + Date.now() + "_" + Math.random().toString(16).slice(2)),
    name: file.name || data.name || data.filename || "attachment",
    filename: file.name || data.filename || data.name || "attachment",
    original_name: file.name || data.name || data.filename || "attachment",
    stored_name: data.stored_name || data.saved_name || data.filename || file.name,
    url: data.url || data.file_url || data.path || "",
    mime_type: file.type || data.mime_type || data.content_type || "",
    size: data.size || data.size_bytes || file.size || 0,
    status: "uploaded",
};
    }

window.NovaEmergencyHandleFiles = null;

async function handleFiles(files) {
    const list = Array.from(files || []);
    if (!list.length) return;

    for (const file of list) {
        const temp = {
            id: "uploading_" + Date.now() + "_" + Math.random().toString(16).slice(2),
            name: file.name,
            filename: file.name,
            mime_type: file.type || "",
            size: file.size || 0,
            status: "uploading",
        };

        state.pendingUploads.push(temp);
        renderPendingUploads();

        try {
            const uploaded = await uploadFile(file);
            const index = state.pendingUploads.findIndex(function (item) {
                return item && item.id === temp.id;
            });

            if (index >= 0) {
                state.pendingUploads[index] = uploaded;
            } else {
                state.pendingUploads.push(uploaded);
            }

            console.log("[NovaEmergencyAttachmentBridge] uploaded", uploaded);
        } catch (err) {
            console.error("[NovaEmergencyAttachmentBridge] upload failed", err);

            temp.status = "failed";
            temp.error = String(err && err.message ? err.message : err);
        }

        renderPendingUploads();
    }
}

window.NovaEmergencyHandleFiles = handleFiles;


    function wireAttachmentInput() {
        const input = findFileInput();

        if (!input) {
            console.log("[NovaEmergencyAttachmentBridge] no file input found");
            return;
        }

        if (input.__novaEmergencyAttachmentWired) return;
        input.__novaEmergencyAttachmentWired = true;

        input.addEventListener("change", function () {
            handleFiles(input.files);
            input.value = "";
        });

        console.log("[NovaEmergencyAttachmentBridge] wired", {
            hasFileInput: true,
            hasUploadStaging: !!findUploadStaging(),
        });
    }

    window.NovaEmergencyAttachments = {
        get: function () {
            return state.pendingUploads;
        },
        clear: function () {
            state.pendingUploads = [];
            renderPendingUploads();
        },
        render: renderPendingUploads,
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", wireAttachmentInput);
    } else {
        wireAttachmentInput();
    }

    setTimeout(wireAttachmentInput, 500);
    setTimeout(wireAttachmentInput, 1500);
})();

// =====================================================
// NOVA EMERGENCY ATTACHMENT CLICK/FALLBACK PATCH
// Append at bottom of nova-custom.js
// =====================================================
(function () {
    "use strict";

    if (window.NovaEmergencyAttachmentClickPatchBooted) return;
    window.NovaEmergencyAttachmentClickPatchBooted = true;

    const state = window.NovaComposerState || window.state || {};
    window.NovaComposerState = state;
    window.state = state;

    state.pendingUploads = Array.isArray(state.pendingUploads) ? state.pendingUploads : [];

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function qsa(selector, root) {
        return Array.from((root || document).querySelectorAll(selector));
    }

    function findFileInput() {
        return qs("input[type='file']");
    }

    function findLikelyUploadButtons() {
        return qsa("button, [role='button'], label").filter(function (el) {
            const text = String(el.textContent || "").toLowerCase();
            const title = String(el.getAttribute("title") || "").toLowerCase();
            const aria = String(el.getAttribute("aria-label") || "").toLowerCase();
            const data = String(el.getAttribute("data-action") || "").toLowerCase();

            return (
                text.includes("attach") ||
                text.includes("upload") ||
                text.includes("file") ||
                text.includes("+") ||
                title.includes("attach") ||
                title.includes("upload") ||
                title.includes("file") ||
                aria.includes("attach") ||
                aria.includes("upload") ||
                aria.includes("file") ||
                data.includes("attach") ||
                data.includes("upload")
            );
        });
    }

    function ensureFileInput() {
        let input = findFileInput();

        if (!input) {
            input = document.createElement("input");
            input.type = "file";
            input.multiple = true;
            input.style.display = "none";
            input.setAttribute("data-emergency-file-input", "true");
            document.body.appendChild(input);
            console.log("[NovaEmergencyAttachmentClickPatch] created fallback file input");
        }

        return input;
    }

    function wireUploadButtons() {
        const input = ensureFileInput();
        const buttons = findLikelyUploadButtons();

        buttons.forEach(function (btn) {
            if (btn.__novaEmergencyUploadClickWired) return;
            btn.__novaEmergencyUploadClickWired = true;

            btn.addEventListener("click", function (event) {
                const tag = String(btn.tagName || "").toLowerCase();

                if (tag !== "label") {
                    event.preventDefault();
                    event.stopPropagation();
                    input.click();
                }
            }, true);
        });

        console.log("[NovaEmergencyAttachmentClickPatch] wired", {
            fileInputFound: !!input,
            uploadButtonCount: buttons.length,
        });
    }

    function wireDropZone() {
        if (document.body.__novaEmergencyDropWired) return;
        document.body.__novaEmergencyDropWired = true;

        document.body.addEventListener("dragover", function (event) {
            event.preventDefault();
        });

        document.body.addEventListener("drop", function (event) {
            event.preventDefault();

            const files = event.dataTransfer && event.dataTransfer.files;
            if (!files || !files.length) return;

            if (window.NovaEmergencyAttachments && typeof window.NovaEmergencyAttachments.render === "function") {
                console.log("[NovaEmergencyAttachmentClickPatch] dropped files", files.length);
            }

            const input = ensureFileInput();

            // Browser security does not allow assigning files to input.files.
            // So call the existing emergency handler indirectly by dispatching through a temporary upload path if available.
            if (typeof window.NovaEmergencyHandleFiles === "function") {
                window.NovaEmergencyHandleFiles(files);
            } else {
                console.warn("[NovaEmergencyAttachmentClickPatch] NovaEmergencyHandleFiles missing");
            }
        });
    }

    wireUploadButtons();
    wireDropZone();

    setTimeout(wireUploadButtons, 500);
    setTimeout(wireUploadButtons, 1500);
})();

// =====================================================
// NOVA EMERGENCY SESSION RESTORE BRIDGE
// Append at bottom of nova-custom.js
// =====================================================
(function () {
    "use strict";

    if (window.NovaEmergencySessionRestoreBooted) return;
    window.NovaEmergencySessionRestoreBooted = true;

    const state = window.NovaComposerState || window.state || {};
    window.NovaComposerState = state;
    window.state = state;

    state.messages = Array.isArray(state.messages) ? state.messages : [];
    state.activeSessionId = state.activeSessionId || "";

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function normalizeMessage(msg) {
        msg = msg || {};
        return {
            id: msg.id || msg.message_id || ("msg_" + Date.now() + "_" + Math.random().toString(16).slice(2)),
            role: msg.role || "assistant",
            text: msg.text || msg.assistant_text || msg.content || "",
            attachments: Array.isArray(msg.attachments) ? msg.attachments : [],
            meta: msg.meta || {},
        };
    }

function findThread() {
    const selectors = [
        "[data-chat-thread]",
        "[data-messages]",
        "#chat-thread",
        "#chat-messages",
        ".chat-thread",
        ".messages"
    ];

    const candidates = selectors
        .map(function (selector) {
            return qs(selector);
        })
        .filter(Boolean);

    const visible = candidates.find(function (el) {
        return (
            el &&
            el.isConnected &&
            el.getClientRects &&
            el.getClientRects().length > 0
        );
    });

    const chosen = visible || candidates[0] || null;

    console.log("[NovaEmergencyBridge] selected thread", {
        candidateCount: candidates.length,
        foundVisible: !!visible,
        chosen: chosen
    });

    return chosen;
}
    function escapeHtml(value) {
        return String(value || "").replace(/[&<>'"]/g, function (char) {
            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                "'": "&#39;",
                '"': "&quot;",
            }[char] || char;
        });
    }

function renderMessages() {
    const thread = findThread();
    if (!thread) return;

    thread.innerHTML = state.messages.map(function (msg) {
        const role = msg.role === "user" ? "user" : "assistant";

        const imageUrl =
            msg.image_url ||
            msg.imageUrl ||
            msg.url ||
            (msg.meta && msg.meta.image_url) ||
            "";

        const imageHtml = imageUrl
            ? (
                '<div class="nova-message-image-wrap" style="margin-top:10px;">' +
                    '<img src="' + escapeHtml(imageUrl) + '" alt="Generated image" ' +
                    'style="width:100%;max-width:420px;height:auto;border-radius:14px;display:block;border:1px solid rgba(255,255,255,0.12);" />' +
                '</div>'
            )
            : "";

        return (
            '<div class="nova-message nova-message-' + role + '">' +
                '<div class="nova-message-role">' + escapeHtml(role) + "</div>" +
                '<div class="nova-message-text">' + escapeHtml(msg.text || "") + "</div>" +
                imageHtml +
            "</div>"
        );
    }).join("");

    thread.scrollTop = thread.scrollHeight;
}

    function getSessionIdFromPayload(payload) {
        if (!payload || typeof payload !== "object") return "";

        return (
            payload.active_session_id ||
            payload.activeSessionId ||
            payload.session_id ||
            (payload.session && payload.session.id) ||
            (payload.active && payload.active.id) ||
            ""
        );
    }

    function getMessagesFromPayload(payload) {
        if (!payload || typeof payload !== "object") return [];

        if (Array.isArray(payload.messages)) return payload.messages;
        if (payload.session && Array.isArray(payload.session.messages)) return payload.session.messages;
        if (payload.active && Array.isArray(payload.active.messages)) return payload.active.messages;
        if (payload.current_session && Array.isArray(payload.current_session.messages)) return payload.current_session.messages;

        return [];
    }

    async function restoreActiveSession() {
        try {
            const response = await fetch("/api/sessions", {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                },
            });

            const data = await response.json();

            let activeSession = null;

            if (Array.isArray(data.sessions)) {
                activeSession =
                    data.sessions.find(function (session) {
                        return session && (session.active || session.is_active);
                    }) ||
                    data.sessions[0] ||
                    null;
            }

            if (data.active && typeof data.active === "object") {
                activeSession = data.active;
            }

            if (data.session && typeof data.session === "object") {
                activeSession = data.session;
            }

            const sessionId =
                getSessionIdFromPayload(data) ||
                (activeSession && activeSession.id) ||
                state.activeSessionId ||
                "";

            if (sessionId) {
                state.activeSessionId = sessionId;
                document.body.setAttribute("data-session-id", sessionId);
            }

            const messages =
                getMessagesFromPayload(data).length
                    ? getMessagesFromPayload(data)
                    : activeSession && Array.isArray(activeSession.messages)
                        ? activeSession.messages
                        : [];

            if (messages.length) {
                state.messages = messages.map(normalizeMessage);
                renderMessages();
            }

            console.log("[NovaEmergencySessionRestore] restored", {
                activeSessionId: state.activeSessionId,
                messageCount: state.messages.length,
                hasThread: !!findThread(),
            });
        } catch (err) {
            console.error("[NovaEmergencySessionRestore] failed", err);
        }
    }

    window.NovaEmergencyRestoreSession = restoreActiveSession;

    setTimeout(restoreActiveSession, 300);
    setTimeout(restoreActiveSession, 1200);
})();

// =====================================================
// NOVA EMERGENCY ARTIFACT RAIL BRIDGE
// Append at bottom of nova-custom.js
// =====================================================
(function () {
    "use strict";

    if (window.NovaEmergencyArtifactRailBooted) return;
    window.NovaEmergencyArtifactRailBooted = true;

    const state = window.NovaComposerState || window.state || {};
    window.NovaComposerState = state;
    window.state = state;

    state.artifacts = Array.isArray(state.artifacts) ? state.artifacts : [];

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function escapeHtml(value) {
        return String(value || "").replace(/[&<>'"]/g, function (char) {
            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                "'": "&#39;",
                '"': "&quot;",
            }[char] || char;
        });
    }

    function findArtifactRail() {
        let rail =
            qs("[data-artifact-rail]") ||
            qs("[data-rail-panel='artifacts']") ||
            qs("#rail-artifacts") ||
            qs("#artifacts-rail") ||
            qs(".artifact-rail");

        if (!rail) {
            rail = document.createElement("div");
            rail.id = "rail-artifacts";
            rail.setAttribute("data-artifact-rail", "true");
            rail.style.padding = "10px";
            rail.style.display = "flex";
            rail.style.flexDirection = "column";
            rail.style.gap = "8px";

            const rightRail =
                qs("[data-right-rail]") ||
                qs("#right-rail") ||
                qs(".right-rail") ||
                qs("aside") ||
                document.body;

            rightRail.appendChild(rail);
        }

        return rail;
    }

    function normalizeArtifact(item) {
        item = item || {};

        const raw = item.raw && typeof item.raw === "object" ? item.raw : item;
        const viewer = raw.viewer && typeof raw.viewer === "object" ? raw.viewer : {};
        const meta = raw.meta && typeof raw.meta === "object" ? raw.meta : {};

        const url =
            item.url ||
            item.file_url ||
            item.source_url ||
            item.image_url ||
            item.output_url ||
            item.generated_url ||
            item.viewer_url ||
            item.path ||
            raw.url ||
            raw.file_url ||
            raw.source_url ||
            raw.image_url ||
            raw.preview ||
            raw.output_url ||
            raw.generated_url ||
            raw.viewer_url ||
            viewer.url ||
            viewer.file_url ||
            viewer.source_url ||
            viewer.image_url ||
            viewer.video_url ||
            viewer.audio_url ||
            meta.url ||
            meta.file_url ||
            meta.source_url ||
            meta.image_url ||
            "";

        return {
            id:
                item.id ||
                item.artifact_id ||
                raw.id ||
                raw.artifact_id ||
                ("artifact_" + Date.now() + "_" + Math.random().toString(16).slice(2)),

            title:
                item.title ||
                item.name ||
                item.filename ||
                raw.title ||
                raw.name ||
                raw.filename ||
                viewer.title ||
                item.type ||
                raw.type ||
                raw.kind ||
                "Artifact",

            type:
                item.type ||
                item.kind ||
                raw.type ||
                raw.kind ||
                viewer.kind ||
                "artifact",

            content:
                item.content ||
                item.text ||
                item.body ||
                raw.content ||
                raw.text ||
                raw.body ||
                raw.prompt ||
                viewer.body ||
                "",

            url: url,
            image_url: raw.image_url || viewer.image_url || meta.image_url || url,
            preview: raw.preview || url,
            session_id: item.session_id || raw.session_id || "",
            raw: raw,
        };
    }

    function getArtifactsFromPayload(payload) {
        if (!payload || typeof payload !== "object") return [];

        if (Array.isArray(payload.artifacts)) return payload.artifacts;
        if (payload.session && Array.isArray(payload.session.artifacts)) return payload.session.artifacts;
        if (payload.active && Array.isArray(payload.active.artifacts)) return payload.active.artifacts;
        if (payload.current_session && Array.isArray(payload.current_session.artifacts)) return payload.current_session.artifacts;

        return [];
    }

    function openArtifact(artifact) {
        artifact = normalizeArtifact(artifact);
        state.activeArtifact = artifact;

        const rightRail =
            qs("[data-right-rail]") ||
            qs("#right-rail") ||
            qs(".right-rail") ||
            null;

        if (rightRail) {
            rightRail.classList.add("is-open", "is-active");
            rightRail.style.display = "";
        }

        let viewer =
            qs("[data-artifact-viewer]") ||
            qs("#artifact-viewer") ||
            qs(".artifact-viewer");

        if (!viewer) {
            viewer = document.createElement("div");
            viewer.id = "artifact-viewer";
            viewer.setAttribute("data-artifact-viewer", "true");
            viewer.className = "artifact-viewer";

            viewer.style.marginTop = "10px";
            viewer.style.padding = "10px";
            viewer.style.position = "sticky";
            viewer.style.top = "8px";
            viewer.style.zIndex = "20";
            viewer.style.borderRadius = "14px";
            viewer.style.border = "1px solid rgba(255,255,255,0.12)";
            viewer.style.background = "rgba(15,23,42,0.72)";
            viewer.style.maxHeight = "70vh";
            viewer.style.overflow = "auto";

            const rail = findArtifactRail();
            const firstCard = rail.querySelector(".nova-artifact-card");

            if (firstCard) {
                rail.insertBefore(viewer, firstCard);
            } else {
                rail.appendChild(viewer);
            }
        }

        const title = artifact.title || artifact.name || "Artifact";
        const url =
            artifact.url ||
            artifact.file_url ||
            artifact.source_url ||
            artifact.image_url ||
            artifact.output_url ||
            artifact.generated_url ||
            artifact.viewer_url ||
            artifact.path ||
            "";

        const content = artifact.content || artifact.text || artifact.body || "";
        const type = String(artifact.type || artifact.kind || "").toLowerCase();

        const isImage =
            type.includes("image") ||
            /\.(png|jpg|jpeg|gif|webp|bmp|svg)(\?.*)?$/i.test(url);

        let bodyHtml = "";

        if (isImage && url) {
            bodyHtml =
                '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;margin-bottom:10px;">' +
                    '<a href="' + escapeHtml(url) + '" target="_blank" rel="noopener noreferrer" ' +
                    'style="padding:6px 10px;border-radius:999px;border:1px solid rgba(255,255,255,0.16);text-decoration:none;color:white;background:rgba(17,24,39,0.78);font-size:12px;">Open image</a>' +
                    '<a href="' + escapeHtml(url) + '" download ' +
                    'style="padding:6px 10px;border-radius:999px;border:1px solid rgba(255,255,255,0.16);text-decoration:none;color:white;background:rgba(17,24,39,0.78);font-size:12px;">Download</a>' +
                '</div>' +
                '<div style="margin-top:10px;">' +
                    '<img src="' + escapeHtml(url) + '" ' +
                    'style="width:100%;max-width:100%;height:auto;border-radius:14px;display:block;border:1px solid rgba(255,255,255,0.12);" ' +
                    'alt="' + escapeHtml(title) + '">' +
                '</div>' +
                '<div style="margin-top:8px;font-size:11px;opacity:0.7;word-break:break-all;">' +
                    escapeHtml(url) +
                '</div>';
        } else if (url) {
            bodyHtml =
                '<div style="margin-top:10px;">' +
                    '<a href="' + escapeHtml(url) + '" target="_blank" rel="noopener noreferrer">Open artifact</a>' +
                '</div>' +
                '<pre style="white-space:pre-wrap;font-size:12px;line-height:1.4;margin-top:10px;">' +
                    escapeHtml(content || url) +
                '</pre>';
        } else {
            bodyHtml =
                '<pre style="white-space:pre-wrap;font-size:12px;line-height:1.4;margin-top:10px;">' +
                    escapeHtml(content || "No artifact content.") +
                '</pre>';
        }

        viewer.innerHTML =
            '<div style="display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:10px;">' +
                '<strong>' + escapeHtml(title) + '</strong>' +
                '<button type="button" data-close-artifact-viewer="true">Close</button>' +
            '</div>' +
            '<div style="font-size:11px;opacity:0.7;">' + escapeHtml(type || "artifact") + '</div>' +
            bodyHtml;

        const closeBtn = qs("[data-close-artifact-viewer]", viewer);
        if (closeBtn) {
            closeBtn.onclick = function () {
                viewer.remove();
            };
        }

        viewer.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
        });

        console.log("[NovaEmergencyArtifactRail] opened", artifact);
    }

    function renderArtifactRail() {
        const rail = findArtifactRail();
        if (!rail) return;

        const artifacts = Array.isArray(state.artifacts) ? state.artifacts : [];

        rail.innerHTML =
            '<div style="font-weight:700;margin-bottom:6px;">Artifacts</div>';

        if (!artifacts.length) {
            rail.innerHTML += '<div style="font-size:12px;opacity:0.65;">No artifacts yet</div>';
            return;
        }

        artifacts.forEach(function (rawArtifact) {
            const artifact = normalizeArtifact(rawArtifact);

            const card = document.createElement("button");
            card.type = "button";
            card.className = "nova-artifact-card";
            card.style.textAlign = "left";
            card.style.padding = "10px";
            card.style.borderRadius = "12px";
            card.style.border = "1px solid rgba(255,255,255,0.14)";
            card.style.background = "rgba(255,255,255,0.06)";
            card.style.color = "inherit";
            card.style.cursor = "pointer";

            card.innerHTML =
                '<div style="font-weight:700;font-size:13px;">' + escapeHtml(artifact.title) + '</div>' +
                '<div style="font-size:11px;opacity:0.7;margin-top:3px;">' + escapeHtml(artifact.type) + '</div>';

            card.onclick = function () {
                openArtifact(artifact);
            };

            rail.appendChild(card);
        });

        console.log("[NovaEmergencyArtifactRail] rendered", {
            count: artifacts.length,
            rail: rail,
        });
    }

    async function restoreArtifacts() {
        try {
            const response = await fetch("/api/sessions", {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                },
            });

            const data = await response.json();

            let activeSession = null;

            if (Array.isArray(data.sessions)) {
                activeSession =
                    data.sessions.find(function (session) {
                        return session && (
                            session.active ||
                            session.is_active ||
                            session.id === state.activeSessionId
                        );
                    }) ||
                    data.sessions[0] ||
                    null;
            }

            if (data.active && typeof data.active === "object") activeSession = data.active;
            if (data.session && typeof data.session === "object") activeSession = data.session;

            let artifacts = getArtifactsFromPayload(data);

            if (!artifacts.length && activeSession && Array.isArray(activeSession.artifacts)) {
                artifacts = activeSession.artifacts;
            }

            state.artifacts = artifacts.map(normalizeArtifact);
            renderArtifactRail();

            console.log("[NovaEmergencyArtifactRail] restored", {
                count: state.artifacts.length,
                activeSessionId: state.activeSessionId,
            });
        } catch (err) {
            console.error("[NovaEmergencyArtifactRail] restore failed", err);
            renderArtifactRail();
        }
    }

    window.NovaEmergencyRenderArtifacts = renderArtifactRail;
    window.NovaEmergencyRestoreArtifacts = restoreArtifacts;
    window.NovaEmergencyOpenArtifact = openArtifact;

    setTimeout(restoreArtifacts, 400);
    setTimeout(restoreArtifacts, 1300);
})();

// =====================================================
// NOVA EMERGENCY EXECUTION PANEL BRIDGE
// Append at bottom of nova-custom.js
// =====================================================
(function () {
    "use strict";

    if (window.NovaEmergencyExecutionBridgeBooted) return;
    window.NovaEmergencyExecutionBridgeBooted = true;

    const state = window.NovaComposerState || window.state || {};
    window.NovaComposerState = state;
    window.state = state;

    state.execution = state.execution || {
        status: "idle",
        currentStep: "",
        steps: [],
        lastAction: "",
        lastResponse: null,
    };

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function qsa(selector, root) {
        return Array.from((root || document).querySelectorAll(selector));
    }

    function escapeHtml(value) {
        return String(value || "").replace(/[&<>'"]/g, function (char) {
            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                "'": "&#39;",
                '"': "&quot;",
            }[char] || char;
        });
    }

    function findExecutionPanel() {
        let panel =
            qs("[data-execution-panel]") ||
            qs("[data-rail-panel='execution']") ||
            qs("#execution-panel") ||
            qs("#rail-execution") ||
            qs(".execution-panel");

        if (!panel) {
            panel = document.createElement("div");
            panel.id = "execution-panel";
            panel.setAttribute("data-execution-panel", "true");
            panel.style.padding = "10px";
            panel.style.display = "flex";
            panel.style.flexDirection = "column";
            panel.style.gap = "8px";

            const rightRail =
                qs("[data-right-rail]") ||
                qs("#right-rail") ||
                qs(".right-rail") ||
                qs("aside") ||
                document.body;

            rightRail.appendChild(panel);
        }

        return panel;
    }

    function getSessionId() {
        return (
            state.activeSessionId ||
            document.body.getAttribute("data-session-id") ||
            ""
        );
    }

    function getExecutionText(action) {
        const map = {
            run_step: "run_step",
            run_all: "run_all",
            retry_failed: "retry_failed",
            stop: "stop",
            next: "next",
            resume: "resume",
        };

        return map[action] || action || "run_step";
    }

    function normalizeExecutionFromResponse(data, action) {
        data = data || {};

        const meta = data.meta || data.debug || {};
        const execution =
            data.execution ||
            data.execution_state ||
            data.active_execution ||
            meta.execution ||
            meta.execution_state ||
            {};

        const text =
            data.text ||
            data.assistant_text ||
            (data.assistant_message && data.assistant_message.text) ||
            "";

        const steps = Array.isArray(execution.steps)
            ? execution.steps
            : Array.isArray(data.steps)
                ? data.steps
                : Array.isArray(meta.steps)
                    ? meta.steps
                    : state.execution.steps || [];

        state.execution.lastAction = action || "";
        state.execution.lastResponse = data;
        state.execution.status =
            execution.status ||
            data.status ||
            meta.status ||
            state.execution.status ||
            "idle";

        state.execution.currentStep =
            execution.current_step ||
            execution.currentStep ||
            execution.step ||
            data.current_step ||
            meta.current_step ||
            "";

        state.execution.steps = steps;
        state.execution.lastText = text;
    }

    function renderExecutionPanel() {
        const panel = findExecutionPanel();
        if (!panel) return;

        const steps = Array.isArray(state.execution.steps) ? state.execution.steps : [];

        const stepHtml = steps.length
            ? steps.map(function (step, index) {
                const title =
                    (step && (step.title || step.name || step.text || step.description)) ||
                    ("Step " + (index + 1));

                const status =
                    (step && step.status) ||
                    "pending";

                return (
                    '<div style="padding:8px;border:1px solid rgba(255,255,255,0.14);border-radius:10px;margin-top:6px;">' +
                        '<div style="font-size:12px;font-weight:700;">' + escapeHtml(title) + '</div>' +
                        '<div style="font-size:11px;opacity:0.7;">' + escapeHtml(status) + '</div>' +
                    '</div>'
                );
            }).join("")
            : '<div style="font-size:12px;opacity:0.65;margin-top:8px;">No execution steps loaded.</div>';

        panel.innerHTML =
            '<div style="font-weight:800;margin-bottom:6px;">Execution</div>' +
            '<div style="font-size:12px;opacity:0.8;margin-bottom:8px;">Status: ' +
                escapeHtml(state.execution.status || "idle") +
            '</div>' +
            '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;">' +
                '<button type="button" data-emergency-exec-action="run_step">Run Step</button>' +
                '<button type="button" data-emergency-exec-action="run_all">Run All</button>' +
                '<button type="button" data-emergency-exec-action="retry_failed">Retry</button>' +
                '<button type="button" data-emergency-exec-action="stop">Stop</button>' +
            '</div>' +
            '<div style="font-size:12px;opacity:0.8;">Current: ' +
                escapeHtml(state.execution.currentStep || "-") +
            '</div>' +
            '<div style="margin-top:8px;">' + stepHtml + '</div>' +
            (
                state.execution.lastText
                    ? '<pre style="white-space:pre-wrap;font-size:12px;line-height:1.4;margin-top:10px;padding:8px;border-radius:10px;background:rgba(255,255,255,0.06);">' +
                        escapeHtml(state.execution.lastText) +
                      '</pre>'
                    : ''
            );

        qsa("[data-emergency-exec-action]", panel).forEach(function (button) {
            button.onclick = function () {
                runExecutionAction(button.getAttribute("data-emergency-exec-action"));
            };
        });

        console.log("[NovaEmergencyExecutionBridge] rendered", {
            status: state.execution.status,
            steps: steps.length,
            panel: panel,
        });
    }

    async function runExecutionAction(action) {
        const command = getExecutionText(action);

        state.execution.status = "running";
        state.execution.lastAction = action;
        renderExecutionPanel();

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({
                    user_text: command,
                    session_id: getSessionId(),
                    attachments: [],
                }),
            });

            const data = await response.json();

            if (data.session_id || (data.session && data.session.id)) {
                state.activeSessionId = data.session_id || data.session.id;
                document.body.setAttribute("data-session-id", state.activeSessionId);
            }

            normalizeExecutionFromResponse(data, action);
            renderExecutionPanel();

            if (typeof window.NovaEmergencyRestoreSession === "function") {
                window.NovaEmergencyRestoreSession();
            }

            console.log("[NovaEmergencyExecutionBridge] action complete", {
                action: action,
                command: command,
                status: state.execution.status,
                data: data,
            });
        } catch (err) {
            console.error("[NovaEmergencyExecutionBridge] action failed", err);

            state.execution.status = "error";
            state.execution.lastText = String(err && err.message ? err.message : err);
            renderExecutionPanel();
        }
    }

    async function restoreExecutionState() {
        try {
            const response = await fetch("/api/sessions", {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                },
            });

            const data = await response.json();

            let activeSession = null;

            if (Array.isArray(data.sessions)) {
                activeSession =
                    data.sessions.find(function (session) {
                        return session && (session.active || session.is_active || session.id === state.activeSessionId);
                    }) ||
                    data.sessions[0] ||
                    null;
            }

            if (data.active && typeof data.active === "object") activeSession = data.active;
            if (data.session && typeof data.session === "object") activeSession = data.session;

            const meta =
                (activeSession && activeSession.meta) ||
                (activeSession && activeSession.metadata) ||
                data.meta ||
                {};

            const execution =
                (activeSession && activeSession.execution_state) ||
                (activeSession && activeSession.active_execution) ||
                meta.execution_state ||
                meta.active_execution ||
                {};

            if (execution && typeof execution === "object" && Object.keys(execution).length) {
                state.execution.status = execution.status || state.execution.status || "idle";
                state.execution.currentStep =
                    execution.current_step ||
                    execution.currentStep ||
                    execution.step ||
                    state.execution.currentStep ||
                    "";

                state.execution.steps = Array.isArray(execution.steps)
                    ? execution.steps
                    : state.execution.steps || [];
            }

            renderExecutionPanel();

            console.log("[NovaEmergencyExecutionBridge] restored", {
                status: state.execution.status,
                steps: Array.isArray(state.execution.steps) ? state.execution.steps.length : 0,
                activeSessionId: state.activeSessionId,
            });
        } catch (err) {
            console.error("[NovaEmergencyExecutionBridge] restore failed", err);
            renderExecutionPanel();
        }
    }

    window.runExecutionAction = runExecutionAction;
    window.NovaEmergencyRunExecution = runExecutionAction;
    window.NovaEmergencyRenderExecution = renderExecutionPanel;
    window.NovaEmergencyRestoreExecution = restoreExecutionState;

    setTimeout(restoreExecutionState, 500);
    setTimeout(restoreExecutionState, 1500);
})();

// =====================================================
// NOVA EMERGENCY FLOATING EXECUTION BUTTONS
// Append at bottom of nova-custom.js
// =====================================================
(function () {
    "use strict";

    if (window.NovaEmergencyFloatingExecBooted) return;
    window.NovaEmergencyFloatingExecBooted = true;

    function makeButton(label, action) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = label;
        btn.style.padding = "8px 10px";
        btn.style.borderRadius = "10px";
        btn.style.border = "1px solid rgba(255,255,255,0.2)";
        btn.style.background = "rgba(255,255,255,0.08)";
        btn.style.color = "inherit";
        btn.style.cursor = "pointer";

        btn.onclick = function () {
            if (typeof window.NovaEmergencyRunExecution === "function") {
                window.NovaEmergencyRunExecution(action);
            } else if (typeof window.runExecutionAction === "function") {
                window.runExecutionAction(action);
            } else {
                console.error("[NovaFloatingExec] execution function missing");
            }
        };

        return btn;
    }

    function bootFloatingExec() {
        if (document.querySelector("[data-floating-exec-controls]")) return;

        const box = document.createElement("div");
        box.setAttribute("data-floating-exec-controls", "true");
        box.style.position = "fixed";
        box.style.right = "18px";
        box.style.bottom = "18px";
        box.style.zIndex = "999999";
        box.style.display = "flex";
        box.style.flexDirection = "column";
        box.style.gap = "8px";
        box.style.padding = "12px";
        box.style.borderRadius = "16px";
        box.style.background = "rgba(10,10,10,0.92)";
        box.style.border = "1px solid rgba(255,255,255,0.18)";
        box.style.boxShadow = "0 12px 40px rgba(0,0,0,0.45)";
        box.style.color = "#fff";

        const title = document.createElement("div");
        title.textContent = "Execution";
        title.style.fontWeight = "800";
        title.style.fontSize = "13px";
        title.style.marginBottom = "2px";

        box.appendChild(title);
        box.appendChild(makeButton("Run Step", "run_step"));
        box.appendChild(makeButton("Run All", "run_all"));
        box.appendChild(makeButton("Retry", "retry_failed"));
        box.appendChild(makeButton("Stop", "stop"));

        document.body.appendChild(box);

        console.log("[NovaFloatingExec] loaded");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bootFloatingExec);
    } else {
        bootFloatingExec();
    }

    setTimeout(bootFloatingExec, 500);
})();

// =====================================================
// NOVA EMERGENCY MEMORY BRIDGE
// Append at bottom of nova-custom.js
// =====================================================
(function () {
    "use strict";

    if (window.NovaEmergencyMemoryBridgeBooted) return;
    window.NovaEmergencyMemoryBridgeBooted = true;

    const state = window.NovaComposerState || window.state || {};
    window.NovaComposerState = state;
    window.state = state;

    state.memory = Array.isArray(state.memory) ? state.memory : [];

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function escapeHtml(value) {
        return String(value || "").replace(/[&<>'"]/g, function (char) {
            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                "'": "&#39;",
                '"': "&quot;",
            }[char] || char;
        });
    }

    function findMemoryRail() {
        let rail =
            qs("[data-memory-rail]") ||
            qs("[data-rail-panel='memory']") ||
            qs("#rail-memory") ||
            qs("#memory-rail") ||
            qs(".memory-rail");

        if (!rail) {
            rail = document.createElement("div");
            rail.id = "rail-memory";
            rail.setAttribute("data-memory-rail", "true");
            rail.style.padding = "10px";
            rail.style.display = "flex";
            rail.style.flexDirection = "column";
            rail.style.gap = "8px";

            const rightRail =
                qs("[data-right-rail]") ||
                qs("#right-rail") ||
                qs(".right-rail") ||
                qs("aside") ||
                document.body;

            rightRail.appendChild(rail);
        }

        return rail;
    }

    function normalizeMemory(item) {
        if (typeof item === "string") {
            return {
                id: "memory_" + Math.random().toString(16).slice(2),
                text: item,
                kind: "memory",
                pinned: false,
            };
        }

        item = item || {};

        return {
            id: item.id || item.memory_id || ("memory_" + Math.random().toString(16).slice(2)),
            text: item.text || item.content || item.body || item.summary || item.title || "",
            kind: item.kind || item.type || "memory",
            pinned: !!item.pinned,
            raw: item,
        };
    }

    function extractMemoryFromSession(session) {
        if (!session || typeof session !== "object") return [];

        if (Array.isArray(session.memory)) return session.memory;
        if (Array.isArray(session.memories)) return session.memories;
        if (session.meta && Array.isArray(session.meta.memory)) return session.meta.memory;
        if (session.meta && Array.isArray(session.meta.used_memory)) return session.meta.used_memory;

        if (session.working_state && typeof session.working_state === "object") {
            const ws = session.working_state;
            const items = [];

            if (ws.active_task) items.push({ text: "Active task: " + ws.active_task, kind: "working_state" });
            if (ws.current_file) items.push({ text: "Current file: " + ws.current_file, kind: "working_state" });
            if (ws.current_bug) items.push({ text: "Current bug: " + ws.current_bug, kind: "working_state" });
            if (ws.last_success) items.push({ text: "Last success: " + ws.last_success, kind: "working_state" });
            if (ws.next_move) items.push({ text: "Next move: " + ws.next_move, kind: "working_state" });
            if (ws.checkpoint) items.push({ text: "Checkpoint: " + ws.checkpoint, kind: "working_state" });

            return items;
        }

        return [];
    }

    function renderMemoryRail() {
        const rail = findMemoryRail();
        if (!rail) return;

        const memories = Array.isArray(state.memory)
            ? state.memory.map(normalizeMemory)
            : [];

        rail.innerHTML =
            '<div style="font-weight:800;margin-bottom:6px;">Memory</div>' +
            '<div style="display:flex;gap:6px;margin-bottom:8px;">' +
                '<button type="button" data-memory-refresh="true">Refresh</button>' +
                '<button type="button" data-memory-clear-view="true">Clear View</button>' +
            '</div>';

        if (!memories.length) {
            rail.innerHTML += '<div style="font-size:12px;opacity:0.65;">No memory items loaded.</div>';
        } else {
            memories.forEach(function (memory) {
                const card = document.createElement("div");
                card.className = "nova-memory-card";
                card.style.padding = "10px";
                card.style.borderRadius = "12px";
                card.style.border = "1px solid rgba(255,255,255,0.16)";
                card.style.background = "rgba(255,255,255,0.06)";
                card.style.fontSize = "12px";
                card.style.lineHeight = "1.4";

                card.innerHTML =
                    '<div style="font-weight:700;font-size:11px;opacity:0.7;margin-bottom:4px;">' +
                        escapeHtml(memory.kind) +
                        (memory.pinned ? " · pinned" : "") +
                    '</div>' +
                    '<div>' + escapeHtml(memory.text || "(empty memory)") + '</div>';

                rail.appendChild(card);
            });
        }

        const refresh = qs("[data-memory-refresh]", rail);
        if (refresh) refresh.onclick = restoreMemory;

        const clear = qs("[data-memory-clear-view]", rail);
        if (clear) {
            clear.onclick = function () {
                state.memory = [];
                renderMemoryRail();
            };
        }

        console.log("[NovaEmergencyMemoryBridge] rendered", {
            count: memories.length,
            rail: rail,
        });
    }

    async function restoreMemory() {
        try {
            const response = await fetch("/api/sessions", {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                },
            });

            const data = await response.json();

            let activeSession = null;

            if (Array.isArray(data.sessions)) {
                activeSession =
                    data.sessions.find(function (session) {
                        return session && (
                            session.active ||
                            session.is_active ||
                            session.id === state.activeSessionId
                        );
                    }) ||
                    data.sessions[0] ||
                    null;
            }

            if (data.active && typeof data.active === "object") activeSession = data.active;
            if (data.session && typeof data.session === "object") activeSession = data.session;

            let memory = [];

            if (Array.isArray(data.memory)) memory = data.memory;
            if (!memory.length && Array.isArray(data.memories)) memory = data.memories;
            if (!memory.length && activeSession) memory = extractMemoryFromSession(activeSession);

            state.memory = memory.map(normalizeMemory);

            renderMemoryRail();

            console.log("[NovaEmergencyMemoryBridge] restored", {
                count: state.memory.length,
                activeSessionId: state.activeSessionId,
            });
        } catch (err) {
            console.error("[NovaEmergencyMemoryBridge] restore failed", err);
            renderMemoryRail();
        }
    }

    window.NovaEmergencyRenderMemory = renderMemoryRail;
    window.NovaEmergencyRestoreMemory = restoreMemory;

    setTimeout(restoreMemory, 600);
    setTimeout(restoreMemory, 1600);
})();

// =====================================================
// NOVA EMERGENCY MANUAL FILE PICKER
// Append at bottom of nova-custom.js
// =====================================================
(function () {
    "use strict";

    if (window.NovaEmergencyManualFilePickerBooted) return;
    window.NovaEmergencyManualFilePickerBooted = true;

    function bootManualPicker() {
        if (document.querySelector("[data-manual-file-picker]")) return;

        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = "Attach File";
        btn.setAttribute("data-manual-file-picker", "true");

        btn.style.position = "fixed";
        btn.style.left = "18px";
        btn.style.bottom = "18px";
        btn.style.zIndex = "999999";
        btn.style.padding = "10px 12px";
        btn.style.borderRadius = "12px";
        btn.style.border = "1px solid rgba(255,255,255,0.2)";
        btn.style.background = "rgba(10,10,10,0.92)";
        btn.style.color = "#fff";
        btn.style.cursor = "pointer";

        const input = document.createElement("input");
        input.type = "file";
        input.multiple = true;
        input.style.display = "none";
        input.accept = [
            ".mp3",
            ".wav",
            ".m4a",
            ".aac",
            ".ogg",
            ".webm",
            ".flac",
            ".txt",
            ".py",
            ".js",
            ".json",
            ".html",
            ".css",
            ".md",
            ".docx",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp"
        ].join(",");

        input.addEventListener("change", function () {
            if (
                typeof window.NovaEmergencyHandleFiles === "function" &&
                input.files &&
                input.files.length
            ) {
                window.NovaEmergencyHandleFiles(input.files);
            } else {
                console.error("[NovaManualFilePicker] NovaEmergencyHandleFiles missing or no files selected", {
                    hasHandler: typeof window.NovaEmergencyHandleFiles === "function",
                    files: input.files ? input.files.length : 0,
                });
            }

            input.value = "";
        });

        btn.onclick = function () {
            input.click();
        };

        document.body.appendChild(input);
        document.body.appendChild(btn);

        console.log("[NovaManualFilePicker] loaded");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bootManualPicker);
    } else {
        bootManualPicker();
    }

    setTimeout(bootManualPicker, 500);
})();


