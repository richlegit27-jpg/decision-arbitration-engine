(function () {
  "use strict";

  const LOG = "[NovaComposerBundle]";

  function trimSlash(value) {
    return String(value || "").replace(/\/+$/, "");
  }

  function detectApiBase() {
    const explicit =
      window.NOVA_API_BASE ||
      document.documentElement.getAttribute("data-api-base") ||
      (document.body && document.body.getAttribute("data-api-base")) ||
      "";

    if (explicit) return trimSlash(explicit);
    return trimSlash(window.location.origin);
  }

  const API_BASE = detectApiBase();
  window.NOVA_API_BASE = API_BASE;

  const API = {
    base: API_BASE,
    state: `${API_BASE}/api/state`,
    chat: `${API_BASE}/api/chat`,
    upload: `${API_BASE}/api/upload`,
    artifacts: `${API_BASE}/api/artifacts`
  };

  const state = {
    sessionId: "",
    sessions: [],
    sending: false,
    stagedFiles: [],
    activeRightPanel: "",
    memoryItems: [],
    webItems: [],
    lastRequest: null,
    lastResponse: null
  };

  function log() {
    try {
      console.log(LOG, ...arguments);
    } catch (_) {}
  }

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function safe(value) {
    return value == null ? "" : String(value);
  }

  function esc(value) {
    return safe(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function dispatch(name, detail) {
    try {
      window.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
    } catch (_) {}
  }

  function apiUrl(path) {
    if (!path) return API_BASE;
    if (/^https?:\/\//i.test(path)) return path;
    return `${API_BASE}${path.startsWith("/") ? "" : "/"}${path}`;
  }

  function setActiveSessionId(sessionId) {
    state.sessionId = safe(sessionId).trim();
    try {
      localStorage.setItem("nova_active_session_id", state.sessionId);
    } catch (_) {}
    if (document.body) {
      document.body.dataset.activeSessionId = state.sessionId;
    }
  }

  function getSavedSessionId() {
    try {
      return safe(localStorage.getItem("nova_active_session_id")).trim();
    } catch (_) {
      return "";
    }
  }

  function formatTime(value) {
    if (!value) return "";
    try {
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return safe(value);
      return d.toLocaleString();
    } catch (_) {
      return safe(value);
    }
  }

  function renderMarkdownLite(text) {
    let html = esc(text);
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\n/g, "<br>");
    html = html.replace(
      /!\[([^\]]*)\]\(([^)]+)\)/g,
      function (_, alt, src) {
        const finalSrc = src.indexOf("attachment://") === 0 ? "#" : apiUrl(src);
        return `<img class="nova-inline-image" src="${esc(finalSrc)}" alt="${esc(alt || "image")}">`;
      }
    );
    return html;
  }

  function getMessagesEl() {
    return byId("messages");
  }

  function getEmptyEl() {
    return byId("novaEmptyState");
  }

  function getInputEl() {
    return byId("chatInput");
  }

  function getSendBtn() {
    return byId("sendBtn");
  }

  function getUploadBtn() {
    return byId("uploadBtn");
  }

  function getFileInput() {
    return byId("fileInput");
  }

  function getSessionsListEl() {
    return byId("sessionsList");
  }

  function getStagedFilesEl() {
    return byId("stagedFiles");
  }

  function getRightRailEl() {
    return byId("rightRail");
  }

  function getMemoryListEl() {
    return byId("memoryList");
  }

  function getMemoryStatusEl() {
    return byId("memoryStatus");
  }

  function getWebResultsEl() {
    return byId("webResults");
  }

  function getWebStatusEl() {
    return byId("webStatus");
  }

  function panelIds() {
    return ["memoryPanel", "artifactsPanel", "webPanel"];
  }

  function openPanel(panelId) {
    const rail = getRightRailEl();
    if (!rail) return;

    panelIds().forEach(function (id) {
      const panel = byId(id);
      if (!panel) return;
      const active = id === panelId;
      panel.hidden = !active;
      panel.setAttribute("aria-hidden", active ? "false" : "true");
      panel.classList.toggle("is-active", active);
    });

    rail.classList.toggle("is-collapsed", !panelId);
    rail.setAttribute("aria-hidden", panelId ? "false" : "true");
    state.activeRightPanel = panelId || "";
  }

  function closeRightRail() {
    openPanel("");
  }

  function createMessageBubble(role, content, meta) {
    const wrap = document.createElement("div");
    wrap.className = `nova-message nova-message-${role}`;

    const inner = document.createElement("div");
    inner.className = "nova-message-inner";

    const badges = [];
    if (meta && meta.kind) badges.push(meta.kind);
    if (meta && meta.session_id) badges.push(`session ${meta.session_id.slice(0, 8)}`);

    const badgesHtml = badges.length
      ? `<div class="nova-message-badges">${badges.map(function (b) {
          return `<span class="nova-badge">${esc(b)}</span>`;
        }).join("")}</div>`
      : "";

    inner.innerHTML = `
      ${badgesHtml}
      <div class="nova-message-markdown">${renderMarkdownLite(content || "")}</div>
      <div class="nova-message-time">${esc(formatTime(meta && meta.created_at))}</div>
    `;

    wrap.appendChild(inner);
    return wrap;
  }

  function appendMessage(role, content, meta) {
    const messages = getMessagesEl();
    if (!messages) return null;

    const empty = getEmptyEl();
    if (empty) empty.style.display = "none";

    const node = createMessageBubble(role, content, meta || {});
    messages.appendChild(node);
    messages.scrollTop = messages.scrollHeight;
    return node;
  }

  function replaceMessages(messagesPayload) {
    const messages = getMessagesEl();
    if (!messages) return;

    messages.innerHTML = "";

    if (!Array.isArray(messagesPayload) || !messagesPayload.length) {
      const empty = getEmptyEl();
      if (empty) empty.style.display = "";
      return;
    }

    const empty = getEmptyEl();
    if (empty) empty.style.display = "none";

    messagesPayload.forEach(function (msg) {
      appendMessage(
        safe(msg && msg.role) || "assistant",
        safe(msg && (msg.content || msg.text || "")),
        {
          created_at: msg && (msg.created_at || msg.timestamp),
          kind: msg && msg.kind,
          session_id: msg && msg.session_id
        }
      );
    });
  }

  function normalizeSessions(payload) {
    if (Array.isArray(payload)) return payload;
    if (payload && Array.isArray(payload.sessions)) return payload.sessions;
    return [];
  }

  function normalizeMessages(payload) {
    if (Array.isArray(payload && payload.messages)) return payload.messages;
    if (payload && payload.session && Array.isArray(payload.session.messages)) return payload.session.messages;
    return [];
  }

  function normalizeMemory(payload) {
    if (payload && payload.memory && Array.isArray(payload.memory.items)) return payload.memory.items;
    return [];
  }

  function normalizeWeb(payload) {
    if (payload && payload.web && Array.isArray(payload.web.items)) return payload.web.items;
    return [];
  }

  function pickSessionFromState(payload) {
    const sessions = normalizeSessions(payload);
    const saved = getSavedSessionId();

    if (state.sessionId) {
      const found = sessions.find(function (s) {
        return safe(s && s.id) === state.sessionId;
      });
      if (found) return found;
    }

    if (saved) {
      const found = sessions.find(function (s) {
        return safe(s && s.id) === saved;
      });
      if (found) return found;
    }

    return sessions[0] || null;
  }

  function renderSessions() {
    const root = getSessionsListEl();
    if (!root) return;

    root.innerHTML = "";

    state.sessions.forEach(function (session) {
      const id = safe(session && session.id);
      const active = id === state.sessionId;

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `nova-session-item${active ? " is-active" : ""}`;
      btn.dataset.sessionId = id;
      btn.innerHTML = `
        <div class="nova-session-title">${esc(session && session.title ? session.title : "Untitled session")}</div>
        <div class="nova-session-meta">${esc(formatTime(session && (session.updated_at || session.created_at)))}</div>
      `;
      btn.addEventListener("click", function () {
        setActiveSessionId(id);
        refreshState({ silentMessages: false, preferredSessionId: id });
      });

      root.appendChild(btn);
    });
  }

  function renderStagedFiles() {
    const root = getStagedFilesEl();
    if (!root) return;

    root.innerHTML = "";

    state.stagedFiles.forEach(function (file, index) {
      const chip = document.createElement("div");
      chip.className = "nova-attachment-chip";
      chip.innerHTML = `
        <span class="nova-attachment-name">${esc(file.name || ("file-" + index))}</span>
        <button type="button" class="nova-chip-remove" aria-label="Remove file">×</button>
      `;
      chip.querySelector("button").addEventListener("click", function () {
        state.stagedFiles.splice(index, 1);
        renderStagedFiles();
      });
      root.appendChild(chip);
    });
  }

  function renderMemoryPanel() {
    const listEl = getMemoryListEl();
    const statusEl = getMemoryStatusEl();
    if (!listEl || !statusEl) return;

    listEl.innerHTML = "";

    if (!state.memoryItems.length) {
      statusEl.textContent = "No saved memory yet.";
      listEl.innerHTML = `
        <div class="nova-panel-empty">
          <div class="nova-panel-empty-title">No memory yet</div>
          <div class="nova-panel-empty-copy">Say something like “remember that my name is Richard” and it will appear here.</div>
        </div>
      `;
      return;
    }

    statusEl.textContent = `${state.memoryItems.length} memory item${state.memoryItems.length === 1 ? "" : "s"}`;

    const frag = document.createDocumentFragment();
    state.memoryItems.forEach(function (item) {
      const card = document.createElement("div");
      card.className = "nova-memory-card";
      card.innerHTML = `
        <div class="nova-memory-card-text">${esc(item.text || item.content || "")}</div>
        <div class="nova-memory-card-meta">
          <span>${esc(item.source || "memory")}</span>
          <span>${esc(formatTime(item.updated_at || item.created_at))}</span>
        </div>
      `;
      frag.appendChild(card);
    });
    listEl.appendChild(frag);
  }

  function renderWebPanel() {
    const root = getWebResultsEl();
    const statusEl = getWebStatusEl();
    if (!root || !statusEl) return;

    root.innerHTML = "";

    if (!state.webItems.length) {
      statusEl.textContent = "No saved web fetches yet.";
      root.innerHTML = `
        <div class="nova-panel-empty">
          <div class="nova-panel-empty-title">No web results yet</div>
          <div class="nova-panel-empty-copy">Use /web https://example.com and the result will persist here.</div>
        </div>
      `;
      return;
    }

    statusEl.textContent = `${state.webItems.length} web result${state.webItems.length === 1 ? "" : "s"}`;

    const frag = document.createDocumentFragment();

    state.webItems.forEach(function (item) {
      const meta = item.meta || {};
      const web = meta.web || {};
      const url = safe(web.final_url || web.url || "");
      const preview = safe(item.viewer && item.viewer.preview || item.content || "");
      const card = document.createElement("div");
      card.className = "nova-web-card";
      card.innerHTML = `
        <div class="nova-web-card-top">
          <span class="nova-badge">web</span>
          <span class="nova-web-card-time">${esc(formatTime(item.updated_at || item.created_at))}</span>
        </div>
        <div class="nova-web-card-title">${esc(item.title || "Web result")}</div>
        <div class="nova-web-card-preview">${esc(preview)}</div>
        ${url ? `<a class="nova-web-card-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(url)}</a>` : ""}
      `;
      frag.appendChild(card);
    });

    root.appendChild(frag);
  }

  async function uploadStagedFiles() {
    if (!state.stagedFiles.length) return [];

    const form = new FormData();
    state.stagedFiles.forEach(function (file) {
      form.append("files", file);
    });

    const reqMeta = {
      method: "POST",
      url: API.upload,
      file_count: state.stagedFiles.length
    };
    state.lastRequest = reqMeta;
    log("upload request", reqMeta);

    const res = await fetch(API.upload, {
      method: "POST",
      body: form,
      credentials: "same-origin"
    });

    const data = await res.json().catch(function () { return {}; });
    state.lastResponse = data;
    log("upload response", { ok: res.ok, data: data });

    if (!res.ok || data.ok === false) {
      throw new Error(safe(data.error) || "Upload failed.");
    }

    return Array.isArray(data.files) ? data.files : [];
  }

  async function refreshState(options) {
    const opts = Object.assign({ silentMessages: false, preferredSessionId: "" }, options || {});
    const reqMeta = { method: "GET", url: API.state };
    state.lastRequest = reqMeta;
    log("refreshState request", reqMeta);

    const res = await fetch(API.state, {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store"
    });

    const data = await res.json().catch(function () { return {}; });
    state.lastResponse = data;
    log("refreshState response", { ok: res.ok, data: data });

    if (!res.ok || data.ok === false) {
      throw new Error(safe(data.error) || "State request failed.");
    }

    state.sessions = normalizeSessions(data);
    state.memoryItems = normalizeMemory(data);
    state.webItems = normalizeWeb(data);

    const wantedId = safe(opts.preferredSessionId).trim();
    let chosenSession =
      state.sessions.find(function (s) { return safe(s && s.id) === wantedId; }) ||
      pickSessionFromState(data);

    if (!chosenSession && state.sessions.length) chosenSession = state.sessions[0];

    setActiveSessionId(chosenSession ? chosenSession.id : "");
    renderSessions();
    renderMemoryPanel();
    renderWebPanel();

    if (!opts.silentMessages) {
      replaceMessages(normalizeMessages(chosenSession || data));
    }

    dispatch("nova:session-changed", {
      session_id: state.sessionId,
      session: chosenSession || null
    });

    dispatch("nova:artifacts-refresh", {
      session_id: state.sessionId
    });

    return data;
  }

  async function sendMessage() {
    if (state.sending) return;

    const input = getInputEl();
    if (!input) return;

    const content = safe(input.value).trim();
    if (!content && !state.stagedFiles.length) return;

    state.sending = true;

    const sendBtn = getSendBtn();
    if (sendBtn) sendBtn.disabled = true;

    try {
      const uploadedFiles = await uploadStagedFiles();

      appendMessage("user", content || "(attachment)", {
        created_at: new Date().toISOString(),
        session_id: state.sessionId
      });

      input.value = "";
      state.stagedFiles = [];
      renderStagedFiles();

      const payload = {
        content: content,
        session_id: state.sessionId,
        attachments: uploadedFiles
      };

      const reqMeta = {
        method: "POST",
        url: API.chat,
        payload: payload
      };
      state.lastRequest = reqMeta;
      log("sendMessage request", reqMeta);

      const res = await fetch(API.chat, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        credentials: "same-origin",
        body: JSON.stringify(payload)
      });

      const data = await res.json().catch(function () { return {}; });
      state.lastResponse = data;
      log("sendMessage response", { ok: res.ok, data: data });

      if (!res.ok || data.ok === false) {
        throw new Error(safe(data.error) || "Chat request failed.");
      }

      const session =
        data.session ||
        (data.message && data.message.session) ||
        null;

      if (session && session.id) {
        setActiveSessionId(session.id);
      }

      const assistant =
        data.assistant_message ||
        data.message ||
        {};

      const assistantText = safe(
        assistant.content ||
        assistant.text ||
        data.reply ||
        ""
      );

      appendMessage("assistant", assistantText, {
        created_at: assistant.created_at || new Date().toISOString(),
        kind: assistant.kind || "reply",
        session_id: state.sessionId
      });

      if (content.toLowerCase().startsWith("/web")) {
        openPanel("webPanel");
      }

      dispatch("nova:message-sent", {
        session_id: state.sessionId,
        payload: payload
      });

      dispatch("nova:assistant-message", {
        session_id: state.sessionId,
        assistant_message: assistant
      });

      await refreshState({ silentMessages: false, preferredSessionId: state.sessionId });
    } catch (err) {
      log("sendMessage failed", err);
      appendMessage("assistant", `Error\n\n${safe(err && err.message || err)}`, {
        created_at: new Date().toISOString(),
        kind: "error",
        session_id: state.sessionId
      });
    } finally {
      state.sending = false;
      if (sendBtn) sendBtn.disabled = false;
    }
  }

  function bindComposer() {
    const sendBtn = getSendBtn();
    const input = getInputEl();
    const uploadBtn = getUploadBtn();
    const fileInput = getFileInput();

    if (sendBtn) {
      sendBtn.addEventListener("click", sendMessage);
    }

    if (input) {
      input.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage();
        }
      });
    }

    if (uploadBtn && fileInput) {
      uploadBtn.addEventListener("click", function () {
        fileInput.click();
      });

      fileInput.addEventListener("change", function () {
        state.stagedFiles = Array.from(fileInput.files || []);
        renderStagedFiles();
      });
    }
  }

  function bindPanelButtons() {
    const memoryBtn = byId("memoryPanelToggle");
    const artifactsBtn = byId("artifactsPanelToggle");
    const webBtn = byId("webPanelToggle");
    const closeBtn = byId("closeRightRailBtn");

    if (memoryBtn) {
      memoryBtn.addEventListener("click", function () {
        openPanel("memoryPanel");
      });
    }

    if (artifactsBtn) {
      artifactsBtn.addEventListener("click", function () {
        openPanel("artifactsPanel");
      });
    }

    if (webBtn) {
      webBtn.addEventListener("click", function () {
        openPanel("webPanel");
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        closeRightRail();
      });
    }
  }

  function bindSessionButtons() {
    const newBtn = byId("newSessionBtn");
    const refreshBtn = byId("refreshSessionsBtn");

    if (newBtn) {
      newBtn.addEventListener("click", function () {
        setActiveSessionId("");
        replaceMessages([]);
        dispatch("nova:session-changed", { session_id: "" });
      });
    }

    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        refreshState({ silentMessages: false, preferredSessionId: state.sessionId }).catch(function (err) {
          log("refresh button failed", err);
        });
      });
    }
  }

  function bindArtifactSessionJump() {
    window.addEventListener("nova:artifact-owning-session-request", function (event) {
      const sessionId = safe(
        event && event.detail && event.detail.session_id
      ).trim();

      if (!sessionId) return;

      setActiveSessionId(sessionId);

      refreshState({
        silentMessages: false,
        preferredSessionId: sessionId
      }).then(function () {
        dispatch("nova:artifact-owning-session-opened", {
          artifact_id: event && event.detail && event.detail.artifact_id,
          session_id: sessionId
        });
      }).catch(function (err) {
        log("artifact owning session open failed", err);
      });
    });
  }

  async function boot() {
    log("boot start", { api_base: API_BASE });

    bindComposer();
    bindPanelButtons();
    bindSessionButtons();
    bindArtifactSessionJump();
    renderStagedFiles();
    closeRightRail();

    try {
      await refreshState({
        silentMessages: false,
        preferredSessionId: getSavedSessionId()
      });
      log("boot complete", {
        api_base: API_BASE,
        sessionId: state.sessionId,
        sessionCount: state.sessions.length,
        memoryCount: state.memoryItems.length,
        webCount: state.webItems.length
      });
    } catch (err) {
      log("boot failed", err);
      appendMessage("assistant", `Startup error\n\n${safe(err && err.message || err)}`, {
        created_at: new Date().toISOString(),
        kind: "error"
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();