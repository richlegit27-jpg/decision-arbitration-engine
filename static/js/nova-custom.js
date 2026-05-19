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
  console.log("[NovaComposerBundle] Chunk 1 loaded ✅");
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
  console.log("[NovaComposerBundle] Chunk 2 loaded ✅");

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

  const audio = new Audio(`https://api.tts.fake/${encodeURIComponent(msg.text)}`);
  state.tts.audio = audio;
  audio.play();
  state.tts.playing = true;

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
// NOVA COMPOSER BUNDLE — CHUNK 4
// Lines ~2,101–2,800
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
// NOVA COMPOSER BUNDLE — CHUNK 5
// Lines ~2,801–3,500
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
// NOVA COMPOSER BUNDLE — CHUNK 6
// Lines ~3,501–4,200
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
// NOVA COMPOSER BUNDLE — CHUNK 7
// Lines ~4,201–4,900
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
// NOVA COMPOSER BUNDLE — CHUNK 8
// Lines ~4,901–5,600
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
// NOVA COMPOSER BUNDLE — CHUNK 9
// Lines ~5,601–6,300
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

  stopCurrentTts();
  const audio = new Audio(`https://api.tts.fake/${encodeURIComponent(msg.text)}`);
  state.tts.audio = audio;
  state.tts.playing = true;

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
// NOVA COMPOSER BUNDLE — CHUNK 10
// Lines ~6,301–7,000
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
// End of Chunk 10 — Complete JS Bundle
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

    function addMessage(role, text) {
        const msg = normalizeMessage({
            role: role,
            text: text,
        });

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

            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            if (data.session_id || (data.session && data.session.id)) {
                setSessionId(data.session_id || data.session.id);
            }

            const assistant =
                data.assistant_message ||
                {
                    role: "assistant",
                    text: data.assistant_text || data.text || data.output_text || "No response text returned.",
                };

placeholder.text = assistant.text || data.assistant_text || data.text || "No response text returned.";
placeholder.role = "assistant";

state.pendingUploads = [];
if (window.NovaEmergencyAttachments && typeof window.NovaEmergencyAttachments.render === "function") {
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

        chip.textContent = "📎 " + name + " — " + status;
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