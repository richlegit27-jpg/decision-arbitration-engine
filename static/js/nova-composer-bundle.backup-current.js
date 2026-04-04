(function () {
  "use strict";

  const LOG = "[NovaComposerBundle]";
  const API = {
    state: "/api/state",
    chat: "/api/chat",
    newSession: "/api/session/new"
  };

  const state = {
    booted: false,
    sending: false,
    sessionId: "",
    sessions: [],
    messages: [],
    artifacts: [],
    memoryItems: [],
    webItems: [],
    pendingUploads: [],
    activePanel: "artifacts",
    lastUserMessage: ""
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

  function normalizeUploadUrl(url) {
    if (!url || typeof url !== "string") return "";
    if (url.startsWith("/api/uploads/")) return url;
    if (url.startsWith("/uploads/")) return "/api" + url;
    return url;
  }

  function formatTime(value) {
    if (!value) return "";
    try {
      return new Date(value).toLocaleString();
    } catch (_) {
      return String(value);
    }
  }

  function trimText(value, max) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (!max || text.length <= max) return text;
    return text.slice(0, max - 1).trimEnd() + "…";
  }

  function autoGrowTextarea() {
    if (!els.chatInput) return;
    els.chatInput.style.height = "auto";
    els.chatInput.style.height = Math.min(els.chatInput.scrollHeight, 220) + "px";
  }

  function setStatus(text, isError) {
    if (!els.composerStatusText) return;
    els.composerStatusText.textContent = text || "Ready";
    if (els.composerStatus) {
      els.composerStatus.dataset.error = isError ? "true" : "false";
    }
  }

  function cacheEls() {
    els.sidebarToggle = qs("#sidebarToggle");
    els.newChatBtn = qs("#newChatBtn");
    els.sessionList = qs("#sessionList");
    els.sessionTitle = qs("#sessionTitle");
    els.sessionSubtitle = qs("#sessionSubtitle");
    els.modelChip = qs("#modelChip");
    els.chatScroll = qs("#chatScroll");
    els.chatMessages = qs("#chatMessages");
    els.chatInput = qs("#chatInput");
    els.sendBtn = qs("#sendBtn");
    els.voiceBtn = qs("#voiceBtn");
    els.clearChatBtn = qs("#clearChatBtn");
    els.fileInput = qs("#fileInput");
    els.pendingUploads = qs("#pendingUploads");
    els.composerStatus = qs("#composerStatus");
    els.composerStatusText = qs("#composerStatusText");
    els.memoryList = qs("#memoryList");
    els.webList = qs("#webList");
    els.rightRail = qs("#rightRail");
    els.memoryPanel = qs("#memoryPanel");
    els.artifactsPanel = qs("#artifactsPanel");
    els.webPanel = qs("#webPanel");
    els.panelTabs = qsa(".nova-panel-tab");
  }

  function normalizeMessage(raw) {
    const attachments = Array.isArray(raw && raw.attachments) ? raw.attachments : [];
    return {
      id: raw && raw.id ? raw.id : "",
      role: raw && raw.role ? raw.role : "assistant",
      text: raw && (raw.text || raw.content) ? (raw.text || raw.content) : "",
      content: raw && raw.content ? raw.content : (raw && raw.text ? raw.text : ""),
      image_url: normalizeUploadUrl(raw && raw.image_url ? raw.image_url : ""),
      attachments: attachments.map(function (item) {
        return {
          name: item && item.name ? item.name : "Attachment",
          url: normalizeUploadUrl(item && item.url ? item.url : ""),
          type: item && item.type ? item.type : ""
        };
      }),
      created_at: raw && raw.created_at ? raw.created_at : ""
    };
  }

  function applyState(data) {
    state.sessionId = data.active_session_id || (data.session && data.session.id) || "";
    state.sessions = Array.isArray(data.sessions) ? data.sessions : [];
    state.messages = Array.isArray(data.session && data.session.messages)
      ? data.session.messages.map(normalizeMessage)
      : [];
    state.artifacts = Array.isArray(data.artifacts) ? data.artifacts : [];
    state.memoryItems = Array.isArray(data.memory) ? data.memory : [];
    state.webItems = Array.isArray(data.web_items) ? data.web_items : [];

    renderHeader(data);
    renderSessions();
    renderMessages();
    renderMemory();
    renderWeb();

    try {
      window.dispatchEvent(new CustomEvent("nova:state-updated", {
        detail: {
          sessionId: state.sessionId,
          artifacts: state.artifacts
        }
      }));
    } catch (_) {}
  }

  function renderHeader(data) {
    const session = data.session || {};
    if (els.sessionTitle) {
      els.sessionTitle.textContent = session.title || "Nova";
    }
    if (els.sessionSubtitle) {
      const count = Array.isArray(session.messages) ? session.messages.length : 0;
      els.sessionSubtitle.textContent = count ? (count + " messages") : "Fast local AI workspace";
    }
    if (els.modelChip && data.debug && data.debug.chat_model) {
      els.modelChip.textContent = data.debug.chat_model;
    }
  }

  function renderSessions() {
    if (!els.sessionList) return;

    if (!state.sessions.length) {
      els.sessionList.innerHTML = `
        <div class="nova-empty-state">
          <div class="nova-empty-title">No sessions</div>
        </div>
      `;
      return;
    }

    els.sessionList.innerHTML = state.sessions.map(function (session) {
      const isActive = session.id === state.sessionId;
      return `
        <button
          type="button"
          class="nova-session-card${isActive ? " is-active" : ""}"
          data-session-id="${escapeHtml(session.id || "")}"
        >
          <div class="nova-session-card-title">${escapeHtml(trimText(session.title || "New chat", 60))}</div>
          <div class="nova-session-card-meta">
            <span>${escapeHtml(trimText(session.last_message_preview || "New chat", 80))}</span>
          </div>
        </button>
      `;
    }).join("");

    qsa("[data-session-id]", els.sessionList).forEach(function (button) {
      button.addEventListener("click", function () {
        const sessionId = button.getAttribute("data-session-id") || "";
        if (!sessionId || sessionId === state.sessionId) return;
        refreshState(sessionId);
      });
    });
  }

  function renderAttachmentList(message) {
    const items = Array.isArray(message.attachments) ? message.attachments : [];
    if (!items.length) return "";
    return `
      <div class="nova-message-attachments">
        ${items.map(function (item) {
          return `
            <a class="nova-message-attachment" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener">
              ${escapeHtml(item.name || "Attachment")}
            </a>
          `;
        }).join("")}
      </div>
    `;
  }

  function renderMessageActions(message) {
    if (message.role !== "assistant") return "";
    return `
      <div class="nova-message-actions">
        <button type="button" class="nova-message-action-btn" data-copy-message="${escapeHtml(message.id || "")}">Copy</button>
        <button type="button" class="nova-message-action-btn" data-regenerate-message="${escapeHtml(message.id || "")}">Regenerate</button>
      </div>
    `;
  }

  function renderMessages() {
    if (!els.chatMessages) return;

    if (!state.messages.length) {
      els.chatMessages.innerHTML = `
        <div class="nova-empty-chat">
          <div class="nova-empty-chat-title">Nova is live</div>
          <div class="nova-empty-chat-copy">Chat is working. Uploads stage before send. Artifacts rail stays available.</div>
        </div>
      `;
      return;
    }

    els.chatMessages.innerHTML = state.messages.map(function (message) {
      const body = message.text || message.content || "";
      const imageUrl = normalizeUploadUrl(message.image_url || "");
      return `
        <article class="nova-message ${escapeHtml(message.role || "assistant")}">
          <div class="nova-message-inner">
            ${body ? `<div class="nova-message-text">${escapeHtml(body)}</div>` : ""}
            ${imageUrl ? `
              <div class="nova-message-image-wrap">
                <img class="nova-message-image" src="${escapeHtml(imageUrl)}" alt="Generated image" />
                <div class="nova-message-image-actions">
                  <a href="${escapeHtml(imageUrl)}" target="_blank" rel="noopener">Open image</a>
                </div>
              </div>
            ` : ""}
            ${renderAttachmentList(message)}
            <div class="nova-message-time">${escapeHtml(formatTime(message.created_at))}</div>
            ${renderMessageActions(message)}
          </div>
        </article>
      `;
    }).join("");

    qsa("[data-copy-message]", els.chatMessages).forEach(function (button) {
      button.addEventListener("click", async function () {
        const id = button.getAttribute("data-copy-message") || "";
        const message = state.messages.find(function (item) { return item.id === id; });
        if (!message) return;
        try {
          await navigator.clipboard.writeText(message.text || message.content || "");
          setStatus("Copied", false);
        } catch (_) {
          setStatus("Copy failed", true);
        }
      });
    });

    qsa("[data-regenerate-message]", els.chatMessages).forEach(function (button) {
      button.addEventListener("click", function () {
        if (!state.lastUserMessage) return;
        els.chatInput.value = state.lastUserMessage;
        autoGrowTextarea();
        sendMessage();
      });
    });

    if (els.chatScroll) {
      els.chatScroll.scrollTop = els.chatScroll.scrollHeight;
    }
  }

  function renderMemory() {
    if (!els.memoryList) return;

    if (!state.memoryItems.length) {
      els.memoryList.innerHTML = `
        <div class="nova-empty-state">
          <div class="nova-empty-title">No memory yet</div>
          <div class="nova-empty-copy">Saved memory will appear here.</div>
        </div>
      `;
      return;
    }

    els.memoryList.innerHTML = state.memoryItems.map(function (item) {
      return `
        <div class="nova-memory-card">
          <div class="nova-memory-kind">${escapeHtml(item.kind || "memory")}</div>
          <div class="nova-memory-text">${escapeHtml(item.text || "")}</div>
          <div class="nova-memory-time">${escapeHtml(formatTime(item.created_at || item.updated_at || ""))}</div>
        </div>
      `;
    }).join("");
  }

  function renderWeb() {
    if (!els.webList) return;

    if (!state.webItems.length) {
      els.webList.innerHTML = `
        <div class="nova-empty-state">
          <div class="nova-empty-title">No web items</div>
          <div class="nova-empty-copy">Fetched pages will appear here.</div>
        </div>
      `;
      return;
    }

    els.webList.innerHTML = state.webItems.map(function (item) {
      const title = item.title || "Web result";
      const summary = item.summary || item.preview || item.content || "";
      return `
        <button type="button" class="nova-web-card" data-web-artifact-id="${escapeHtml(item.id || "")}">
          <div class="nova-web-card-title">${escapeHtml(trimText(title, 90))}</div>
          <div class="nova-web-card-preview">${escapeHtml(trimText(summary, 180))}</div>
        </button>
      `;
    }).join("");

    qsa("[data-web-artifact-id]", els.webList).forEach(function (button) {
      button.addEventListener("click", function () {
        const artifactId = button.getAttribute("data-web-artifact-id") || "";
        activatePanel("artifacts");
        if (window.NovaArtifacts && typeof window.NovaArtifacts.openArtifactById === "function") {
          window.NovaArtifacts.openArtifactById(artifactId);
        }
      });
    });
  }

  function activatePanel(panelName) {
    state.activePanel = panelName;

    els.panelTabs.forEach(function (tab) {
      const active = tab.getAttribute("data-panel") === panelName;
      tab.classList.toggle("is-active", active);
    });

    if (els.memoryPanel) els.memoryPanel.hidden = panelName !== "memory";
    if (els.artifactsPanel) els.artifactsPanel.hidden = panelName !== "artifacts";
    if (els.webPanel) els.webPanel.hidden = panelName !== "web";
  }

  async function refreshState(sessionId) {
    try {
      setStatus("Loading", false);

      const url = sessionId
        ? API.state + "?session_id=" + encodeURIComponent(sessionId)
        : API.state;

      log("refreshState request", { url });

      const response = await fetch(url, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store"
      });

      const data = await response.json();
      log("refreshState response", data);

      applyState(data);
      setStatus("Ready", false);
    } catch (error) {
      err("refreshState failed", error);
      setStatus("Load failed", true);
    }
  }

  async function createNewSession() {
    try {
      setStatus("Creating chat", false);
      const response = await fetch(API.newSession, {
        method: "POST",
        headers: { Accept: "application/json" }
      });
      const data = await response.json();
      applyState(data);
      activatePanel("artifacts");
      setStatus("Ready", false);
    } catch (error) {
      err("createNewSession failed", error);
      setStatus("New chat failed", true);
    }
  }

  async function sendMessage() {
    if (state.sending) return;

    const text = (els.chatInput && els.chatInput.value ? els.chatInput.value : "").trim();
    if (!text) return;

    state.sending = true;
    state.lastUserMessage = text;
    setStatus("Sending", false);

    if (els.sendBtn) els.sendBtn.disabled = true;

    try {
      const payload = {
        session_id: state.sessionId || "",
        user_text: text
      };

      log("send request", payload);

      const response = await fetch(API.chat, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json"
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      log("send response", data);

      applyState(data);

      if (els.chatInput) {
        els.chatInput.value = "";
        autoGrowTextarea();
      }

      try {
        window.dispatchEvent(new CustomEvent("nova:artifact-created", {
          detail: {
            artifactId: data.artifact && data.artifact.id ? data.artifact.id : "",
            artifacts: data.artifacts || []
          }
        }));
      } catch (_) {}

      activatePanel("artifacts");
      setStatus("Ready", false);
    } catch (error) {
      err("send failed", error);
      setStatus("Send failed", true);
    } finally {
      state.sending = false;
      if (els.sendBtn) els.sendBtn.disabled = false;
    }
  }

  function bindEvents() {
    if (els.newChatBtn) {
      els.newChatBtn.addEventListener("click", createNewSession);
    }

    if (els.sendBtn) {
      els.sendBtn.addEventListener("click", sendMessage);
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

    if (els.clearChatBtn) {
      els.clearChatBtn.addEventListener("click", function () {
        if (!els.chatInput) return;
        els.chatInput.value = "";
        autoGrowTextarea();
        setStatus("Cleared", false);
      });
    }

    if (els.voiceBtn) {
      els.voiceBtn.addEventListener("click", function () {
        setStatus("Voice not wired yet", false);
      });
    }

    els.panelTabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        const panel = tab.getAttribute("data-panel") || "artifacts";
        activatePanel(panel);
      });
    });

    window.addEventListener("nova:artifact-open-session", function (event) {
      const detail = event && event.detail ? event.detail : {};
      if (!detail.sessionId) return;

      refreshState(detail.sessionId).then(function () {
        activatePanel("artifacts");
        if (detail.artifactId && window.NovaArtifacts && typeof window.NovaArtifacts.openArtifactById === "function") {
          window.NovaArtifacts.openArtifactById(detail.artifactId);
        }
      });
    });
  }

  function boot() {
    if (state.booted) return;
    state.booted = true;

    cacheEls();
    bindEvents();
    activatePanel("artifacts");
    autoGrowTextarea();
    log("boot start");
    refreshState().finally(function () {
      log("boot complete");
    });
  }

  document.addEventListener("DOMContentLoaded", boot);

  window.NovaComposer = {
    boot: boot,
    refreshState: refreshState,
    sendMessage: sendMessage,
    activatePanel: activatePanel,
    getState: function () {
      return {
        sessionId: state.sessionId,
        sessions: state.sessions.slice(),
        messages: state.messages.slice(),
        artifacts: state.artifacts.slice(),
        memoryItems: state.memoryItems.slice(),
        webItems: state.webItems.slice(),
        activePanel: state.activePanel
      };
    }
  };
})();