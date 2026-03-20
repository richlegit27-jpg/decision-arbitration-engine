(() => {
  "use strict";

  if (window.__novaUltimateLoaded) {
    console.warn("Nova ultimate already loaded.");
    return;
  }
  window.__novaUltimateLoaded = true;

  const BODY = document.body;
  const ROOT = document.documentElement;
  const MOBILE_BREAKPOINT = 760;
  const TABLET_BREAKPOINT = 980;

  const STORAGE_KEYS = {
    theme: "nova_theme",
    sidebarDesktopCollapsed: "nova_sidebar_desktop_collapsed",
    memoryDesktopCollapsed: "nova_memory_desktop_collapsed",
    activeSessionId: "nova_active_session_id"
  };

  const state = {
    isSending: false,
    sidebarOpenMobile: false,
    memoryOpenMobile: false,
    sidebarCollapsedDesktop: false,
    memoryCollapsedDesktop: false,
    attachedFiles: [],
    recognition: null,
    isListening: false,
    sessions: [],
    activeSessionId: null,
    activeStreamController: null,
    activeAssistantBubble: null,
    activeAssistantTextNode: null,
    activeAssistantCopyBtn: null,
    activeAssistantMeta: null,
    activeAssistantRawText: ""
  };

  let autosizeFrame = null;
  let lastInputHeight = 0;

  function byId(id) {
    return document.getElementById(id);
  }

  const els = {
    appShell: byId("appShell"),
    sidebar: byId("sidebar"),
    memoryPanel: byId("memoryPanel"),

    toggleSidebar: byId("toggleSidebar"),
    mobileSidebarBtn: byId("mobileSidebarBtn"),
    memoryToggleBtnTop: byId("memoryToggleBtnTop"),
    closeMemoryBtn: byId("closeMemoryBtn"),

    newSessionBtn: byId("newSessionBtn"),
    deleteSessionBtn: byId("deleteSessionBtn"),
    renameSessionBtn: byId("renameSessionBtn"),
    duplicateSessionBtn: byId("duplicateSessionBtn"),
    pinSessionBtn: byId("pinSessionBtn"),
    exportSessionBtn: byId("exportSessionBtn"),

    themeToggleBtn: byId("themeToggleBtn"),
    backgroundBtn: byId("backgroundBtn"),

    sessionList: byId("sessionList"),
    memoryList: byId("memoryList"),
    memoryStatusText: byId("memoryStatusText"),

    chatTitle: byId("chatTitle"),
    chatSubtitle: byId("chatSubtitle"),
    chatMessages: byId("chatMessages"),

    modelSelect: byId("modelSelect"),
    modelStatus: byId("modelStatus"),

    attachBtn: byId("attachBtn"),
    fileInput: byId("fileInput"),
    attachedFiles: byId("attachedFiles"),

    voiceBtn: byId("voiceBtn"),
    messageInput: byId("messageInput"),
    sendBtn: byId("sendBtn"),
    stopBtn: byId("stopBtn")
  };

  function isMobile() {
    return window.innerWidth <= MOBILE_BREAKPOINT;
  }

  function isTabletOrBelow() {
    return window.innerWidth <= TABLET_BREAKPOINT;
  }

  function readBool(key, fallback = false) {
    try {
      const raw = localStorage.getItem(key);
      if (raw === null) return fallback;
      return raw === "true";
    } catch {
      return fallback;
    }
  }

  function writeBool(key, value) {
    try {
      localStorage.setItem(key, String(Boolean(value)));
    } catch (error) {
      console.warn("localStorage write failed:", key, error);
    }
  }

  function readText(key, fallback = "") {
    try {
      return localStorage.getItem(key) || fallback;
    } catch {
      return fallback;
    }
  }

  function writeText(key, value) {
    try {
      localStorage.setItem(key, String(value ?? ""));
    } catch (error) {
      console.warn("localStorage write failed:", key, error);
    }
  }

  function getSavedTheme() {
    return readText(STORAGE_KEYS.theme, "dark");
  }

  function saveTheme(theme) {
    writeText(STORAGE_KEYS.theme, theme);
  }

  function setTheme(theme) {
    const nextTheme = String(theme).toLowerCase() === "light" ? "light" : "dark";
    ROOT.setAttribute("data-theme", nextTheme);
    saveTheme(nextTheme);

    if (els.themeToggleBtn) {
      els.themeToggleBtn.textContent = nextTheme === "dark" ? "Light" : "Dark";
    }
  }

  function toggleTheme() {
    const current = ROOT.getAttribute("data-theme") === "light" ? "light" : "dark";
    setTheme(current === "dark" ? "light" : "dark");
  }

  function updateSidebarAria() {
    if (!els.sidebar) return;
    const open = isMobile() ? state.sidebarOpenMobile : !state.sidebarCollapsedDesktop;
    els.sidebar.setAttribute("aria-hidden", open ? "false" : "true");
  }

  function updateMemoryAria() {
    if (!els.memoryPanel) return;
    const open = isTabletOrBelow() ? state.memoryOpenMobile : !state.memoryCollapsedDesktop;
    els.memoryPanel.setAttribute("aria-hidden", open ? "false" : "true");
  }

  function applyLayoutState() {
    const classNames = [
      "sidebar-open",
      "sidebar-expanded",
      "sidebar-collapsed",
      "left-collapsed",
      "memory-open",
      "memory-collapsed",
      "right-collapsed"
    ];

    BODY.classList.remove(...classNames);
    if (els.appShell) {
      els.appShell.classList.remove(...classNames);
    }

    if (isMobile()) {
      if (state.sidebarOpenMobile) {
        BODY.classList.add("sidebar-open");
        if (els.appShell) els.appShell.classList.add("sidebar-open");
      }
    } else {
      if (state.sidebarCollapsedDesktop) {
        BODY.classList.add("sidebar-collapsed", "left-collapsed");
        if (els.appShell) els.appShell.classList.add("sidebar-collapsed", "left-collapsed");
      }
    }

    if (isTabletOrBelow()) {
      if (state.memoryOpenMobile) {
        BODY.classList.add("memory-open");
        if (els.appShell) els.appShell.classList.add("memory-open");
      }
    } else {
      if (state.memoryCollapsedDesktop) {
        BODY.classList.add("memory-collapsed", "right-collapsed");
        if (els.appShell) els.appShell.classList.add("memory-collapsed", "right-collapsed");
      }
    }

    updateSidebarAria();
    updateMemoryAria();
  }

  function toggleSidebar() {
    if (isMobile()) {
      state.sidebarOpenMobile = !state.sidebarOpenMobile;
    } else {
      state.sidebarCollapsedDesktop = !state.sidebarCollapsedDesktop;
      writeBool(STORAGE_KEYS.sidebarDesktopCollapsed, state.sidebarCollapsedDesktop);
    }
    applyLayoutState();
  }

  function toggleMemory() {
    if (isTabletOrBelow()) {
      state.memoryOpenMobile = !state.memoryOpenMobile;
    } else {
      state.memoryCollapsedDesktop = !state.memoryCollapsedDesktop;
      writeBool(STORAGE_KEYS.memoryDesktopCollapsed, state.memoryCollapsedDesktop);
    }
    applyLayoutState();
  }

  function autosizeInput() {
    if (!els.messageInput) return;

    const input = els.messageInput;
    const minHeight = window.innerWidth <= 480 ? 50 : 54;
    const maxHeight = 180;

    if (autosizeFrame) {
      cancelAnimationFrame(autosizeFrame);
    }

    autosizeFrame = requestAnimationFrame(() => {
      input.style.overflowY = "hidden";
      input.style.height = "auto";

      const measured = input.scrollHeight;
      const nextHeight = Math.max(minHeight, Math.min(measured, maxHeight));

      if (nextHeight !== lastInputHeight) {
        input.style.height = `${nextHeight}px`;
        lastInputHeight = nextHeight;
      } else {
        input.style.height = `${lastInputHeight}px`;
      }

      input.style.overflowY = measured > maxHeight ? "auto" : "hidden";
      autosizeFrame = null;
    });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatTime(ts) {
    if (!ts) return "";
    try {
      return new Date(Number(ts) * 1000).toLocaleString();
    } catch {
      return "";
    }
  }

  async function apiGet(url) {
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  }

  async function apiPost(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {})
    });

    if (!response.ok) {
      let detail = "";
      try {
        const data = await response.json();
        detail = data?.detail || data?.error || "";
      } catch {
        detail = "";
      }
      throw new Error(detail ? `HTTP ${response.status}: ${detail}` : `HTTP ${response.status}`);
    }

    return response.json();
  }

  function getActiveSession() {
    return state.sessions.find((item) => item.session_id === state.activeSessionId) || null;
  }

  function setActiveSessionId(sessionId) {
    const clean = String(sessionId || "").trim();
    state.activeSessionId = clean || null;

    if (state.activeSessionId) {
      writeText(STORAGE_KEYS.activeSessionId, state.activeSessionId);
    } else {
      writeText(STORAGE_KEYS.activeSessionId, "");
    }
  }

  function clearMessages() {
    if (!els.chatMessages) return;
    els.chatMessages.innerHTML = "";
  }

  function renderEmptyState() {
    if (!els.chatMessages) return;
    els.chatMessages.innerHTML = `
      <div class="empty-state">
        <div class="empty-card">
          <div class="empty-title">Nova is ready</div>
          <div class="empty-subtitle">Start a new message, use voice, attach files, or open memory.</div>
        </div>
      </div>
    `;
  }

  function basicMarkdownToHtml(text) {
    let html = escapeHtml(text);

    html = html.replace(/```([\s\S]*?)```/g, (_, code) => {
      return `<pre><code>${escapeHtml(code.trim())}</code></pre>`;
    });

    html = html.replace(/`([^`\n]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

    html = html.replace(/(?:^|\n)((?:-\s.+(?:\n|$))+)/g, (_, block) => {
      const items = block
        .trim()
        .split("\n")
        .map((line) => line.replace(/^\-\s/, "").trim())
        .filter(Boolean)
        .map((item) => `<li>${item}</li>`)
        .join("");
      return `\n<ul>${items}</ul>`;
    });

    html = html.replace(/\n/g, "<br>");
    return html;
  }

  async function copyText(text) {
    const clean = String(text || "");
    if (!clean) return;

    try {
      await navigator.clipboard.writeText(clean);
    } catch (error) {
      console.warn("Copy failed:", error);
    }
  }

  function createCopyButton(getText) {
    const copyBtn = document.createElement("button");
    copyBtn.className = "topbar-btn";
    copyBtn.type = "button";
    copyBtn.textContent = "Copy";
    copyBtn.addEventListener("click", async () => {
      await copyText(getText());
      copyBtn.textContent = "Copied";
      setTimeout(() => {
        copyBtn.textContent = "Copy";
      }, 1200);
    });
    return copyBtn;
  }

  function createMessageElement(role, text = "", timestamp = null) {
    const wrap = document.createElement("div");
    wrap.className = `message ${role}`;

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    const body = document.createElement("div");
    body.className = "message-body";

    const textNode = document.createElement("div");
    textNode.className = "message-text";

    if (role === "assistant") {
      textNode.innerHTML = basicMarkdownToHtml(text);
    } else {
      textNode.textContent = text;
    }

    body.appendChild(textNode);
    bubble.appendChild(body);

    const footer = document.createElement("div");
    footer.className = "message-footer";

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = timestamp ? formatTime(timestamp) : "";

    footer.appendChild(meta);

    let copyBtn = null;
    if (role === "assistant") {
      copyBtn = createCopyButton(() => textNode.textContent || "");
      footer.appendChild(copyBtn);
    }

    bubble.appendChild(footer);
    wrap.appendChild(bubble);

    return { wrap, bubble, textNode, meta, copyBtn };
  }

  function appendMessage(role, text, timestamp = null) {
    if (!els.chatMessages) return null;

    const empty = els.chatMessages.querySelector(".empty-state");
    if (empty) empty.remove();

    const node = createMessageElement(role, text, timestamp);
    els.chatMessages.appendChild(node.wrap);
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    return node;
  }

  function renderMessages(messages) {
    clearMessages();

    if (!Array.isArray(messages) || !messages.length) {
      renderEmptyState();
      return;
    }

    for (const msg of messages) {
      const role = String(msg?.role || "assistant").toLowerCase();
      const content = String(msg?.content || "");
      const timestamp = msg?.timestamp || null;
      appendMessage(role, content, timestamp);
    }
  }

  function updateHeaderFromSession(sessionRecord) {
    if (els.chatTitle) {
      els.chatTitle.textContent = sessionRecord?.title || "Nova";
    }

    if (els.chatSubtitle) {
      const count = Number(sessionRecord?.message_count || 0);
      els.chatSubtitle.textContent = state.activeSessionId
        ? `${count} message${count === 1 ? "" : "s"}`
        : "Ready";
    }
  }

  function renderSessions() {
    if (!els.sessionList) return;

    if (!state.sessions.length) {
      els.sessionList.innerHTML = `
        <div class="memory-card">
          <div class="memory-card-text">No chats yet.</div>
        </div>
      `;
      return;
    }

    els.sessionList.innerHTML = state.sessions.map((item) => {
      const activeClass = item.session_id === state.activeSessionId ? " active" : "";
      const title = escapeHtml(item.title || "New Chat");
      const count = Number(item.message_count || 0);
      const meta = `${count} message${count === 1 ? "" : "s"}`;
      return `
        <button class="session-item${activeClass}" type="button" data-session-id="${escapeHtml(item.session_id)}">
          <span class="session-title">${title}</span>
          <span class="session-meta">${escapeHtml(meta)}</span>
        </button>
      `;
    }).join("");
  }

  function renderMemory() {
    if (els.memoryStatusText) {
      els.memoryStatusText.textContent = state.activeSessionId
        ? `Active chat: ${state.activeSessionId}`
        : "Memory panel ready.";
    }

    if (!els.memoryList) return;

    const active = getActiveSession();

    const blocks = [
      {
        title: "Theme",
        meta: ROOT.getAttribute("data-theme") === "light" ? "Light mode" : "Dark mode"
      },
      {
        title: "Model",
        meta: els.modelSelect ? els.modelSelect.value : "unknown"
      }
    ];

    if (active) {
      blocks.unshift({
        title: active.title || "New Chat",
        meta: `${Number(active.message_count || 0)} message${Number(active.message_count || 0) === 1 ? "" : "s"}`
      });
    }

    els.memoryList.innerHTML = blocks.map((item) => {
      return `
        <div class="memory-item">
          <div class="memory-title">${escapeHtml(item.title)}</div>
          <div class="memory-meta">${escapeHtml(item.meta)}</div>
        </div>
      `;
    }).join("");
  }

  function renderAttachedFiles() {
    if (!els.attachedFiles) return;

    if (!state.attachedFiles.length) {
      els.attachedFiles.innerHTML = "";
      return;
    }

    els.attachedFiles.innerHTML = state.attachedFiles.map((file, index) => {
      return `
        <div class="attachment-chip">
          <span>${escapeHtml(file.name)}</span>
          <button class="remove" type="button" data-remove-file="${index}" aria-label="Remove file">x</button>
        </div>
      `;
    }).join("");
  }

  function setSending(isSending) {
    state.isSending = Boolean(isSending);

    if (els.sendBtn) els.sendBtn.disabled = state.isSending;
    if (els.stopBtn) els.stopBtn.classList.toggle("hidden", !state.isSending);

    if (els.modelStatus) {
      els.modelStatus.textContent = state.isSending
        ? "Streaming..."
        : `Model: ${els.modelSelect ? els.modelSelect.value : "ready"}`;
    }
  }

  function onFilePicked(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    state.attachedFiles.push(...files);
    renderAttachedFiles();
    event.target.value = "";
  }

  function onAttachedFilesClick(event) {
    const btn = event.target.closest("[data-remove-file]");
    if (!btn) return;

    const index = Number(btn.getAttribute("data-remove-file"));
    if (Number.isNaN(index)) return;

    state.attachedFiles.splice(index, 1);
    renderAttachedFiles();
  }

  function setupVoice() {
    if (!els.voiceBtn) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition || null;

    if (!SpeechRecognition) {
      els.voiceBtn.addEventListener("click", () => {
        appendMessage("system", "Voice input is not supported in this browser.");
      });
      return;
    }

    state.recognition = new SpeechRecognition();
    state.recognition.lang = "en-US";
    state.recognition.interimResults = true;
    state.recognition.continuous = false;

    state.recognition.onstart = () => {
      state.isListening = true;
      els.voiceBtn.textContent = "Listening";
    };

    state.recognition.onend = () => {
      state.isListening = false;
      els.voiceBtn.textContent = "Voice";
    };

    state.recognition.onerror = () => {
      state.isListening = false;
      els.voiceBtn.textContent = "Voice";
    };

    state.recognition.onresult = (event) => {
      if (!els.messageInput) return;

      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        transcript += event.results[i][0].transcript;
      }

      els.messageInput.value = transcript.trim();
      autosizeInput();
    };

    els.voiceBtn.addEventListener("click", () => {
      if (!state.recognition) return;

      if (state.isListening) {
        state.recognition.stop();
        return;
      }

      try {
        state.recognition.start();
      } catch (error) {
        console.warn("Voice start blocked:", error);
      }
    });
  }

  async function loadModels() {
    if (!els.modelSelect) return;

    try {
      const data = await apiGet("/api/models");
      const models = Array.isArray(data?.models) ? data.models : [];
      const current = data?.default || "gpt-4.1-mini";

      els.modelSelect.innerHTML = models.map((model) => {
        const selected = model === current ? " selected" : "";
        return `<option value="${escapeHtml(model)}"${selected}>${escapeHtml(model)}</option>`;
      }).join("");

      if (els.modelStatus) {
        els.modelStatus.textContent = `Model: ${els.modelSelect.value}`;
      }
    } catch (error) {
      console.warn("Could not load models:", error);
    }
  }

  async function loadState() {
    const data = await apiGet("/api/state");
    state.sessions = Array.isArray(data?.sessions) ? data.sessions : [];

    const savedActive = readText(STORAGE_KEYS.activeSessionId, "").trim();
    const hasSaved = savedActive && state.sessions.some((item) => item.session_id === savedActive);

    if (hasSaved) {
      setActiveSessionId(savedActive);
    } else if (!state.activeSessionId && state.sessions.length) {
      setActiveSessionId(state.sessions[0].session_id);
    } else if (state.activeSessionId && !state.sessions.some((item) => item.session_id === state.activeSessionId)) {
      setActiveSessionId(state.sessions.length ? state.sessions[0].session_id : null);
    }

    renderSessions();
    renderMemory();
  }

  async function loadSession(sessionId) {
    if (!sessionId) {
      setActiveSessionId(null);
      updateHeaderFromSession(null);
      renderEmptyState();
      renderSessions();
      renderMemory();
      return;
    }

    const data = await apiGet(`/api/chat/${encodeURIComponent(sessionId)}`);
    setActiveSessionId(data?.session_id || sessionId);

    const summary = state.sessions.find((item) => item.session_id === state.activeSessionId);
    if (summary) {
      summary.title = data?.title || summary.title;
      summary.message_count = Number(data?.message_count || 0);
    }

    updateHeaderFromSession({
      title: data?.title || "New Chat",
      message_count: Number(data?.message_count || 0)
    });
    renderMessages(Array.isArray(data?.messages) ? data.messages : []);
    renderSessions();
    renderMemory();
  }

  async function refreshStateAndSession(preferredSessionId = null) {
    await loadState();

    const target = preferredSessionId || state.activeSessionId || (state.sessions[0]?.session_id ?? null);

    if (target) {
      await loadSession(target);
    } else {
      await loadSession(null);
    }
  }

  async function createSession() {
    const data = await apiPost("/api/session/new", {});
    await refreshStateAndSession(data?.session_id || null);
    if (els.messageInput) {
      els.messageInput.focus();
    }
  }

  async function deleteSession() {
    if (!state.activeSessionId) {
      appendMessage("system", "No active session to delete.");
      return;
    }

    const currentId = state.activeSessionId;
    await apiPost("/api/session/delete", { session_id: currentId });

    const remaining = state.sessions.filter((item) => item.session_id !== currentId);
    const nextId = remaining[0]?.session_id || null;

    await refreshStateAndSession(nextId);
  }

  async function renameSession() {
    if (!state.activeSessionId) {
      appendMessage("system", "No active session to rename.");
      return;
    }

    const current = getActiveSession();
    const nextTitle = window.prompt("Rename chat", current?.title || "New Chat");

    if (nextTitle === null) return;

    const clean = String(nextTitle).trim();
    if (!clean) {
      appendMessage("system", "Rename cancelled. Title was empty.");
      return;
    }

    await apiPost("/api/session/rename", {
      session_id: state.activeSessionId,
      title: clean
    });

    await refreshStateAndSession(state.activeSessionId);
  }

  async function duplicateSession() {
    appendMessage("system", "Duplicate is disabled for V1 lock.");
  }

  function exportSession() {
    const active = getActiveSession();
    if (!active || !state.activeSessionId) {
      appendMessage("system", "No active session to export.");
      return;
    }

    apiGet(`/api/chat/${encodeURIComponent(state.activeSessionId)}`)
      .then((data) => {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        const safeTitle = String(data?.title || "nova-chat").replace(/[^\w\-]+/g, "_");
        link.href = url;
        link.download = `${safeTitle || "nova-chat"}.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      })
      .catch((error) => {
        appendMessage("system", `Export failed: ${error.message}`);
      });
  }

  function pinSession() {
    appendMessage("system", "Pin is disabled for V1 lock.");
  }

  function backgroundAction() {
    appendMessage("system", "Background is disabled for V1 lock.");
  }

  function resetActiveAssistantState() {
    state.activeAssistantBubble = null;
    state.activeAssistantTextNode = null;
    state.activeAssistantCopyBtn = null;
    state.activeAssistantMeta = null;
    state.activeAssistantRawText = "";
  }

  function updateStreamingAssistantVisual() {
    if (!state.activeAssistantTextNode) return;
    state.activeAssistantTextNode.textContent = state.activeAssistantRawText;
    if (els.chatMessages) {
      els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    }
  }

  function finalizeStreamingAssistant(timestamp = null) {
    if (!state.activeAssistantTextNode) return;

    state.activeAssistantTextNode.innerHTML = basicMarkdownToHtml(state.activeAssistantRawText);

    if (state.activeAssistantMeta && timestamp) {
      state.activeAssistantMeta.textContent = formatTime(timestamp);
    }

    if (els.chatMessages) {
      els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    }
  }

  async function processSseEvent(rawEvent, sessionId) {
    const lines = rawEvent.split("\n");
    let eventName = "message";
    const dataLines = [];

    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    const dataText = dataLines.join("\n");
    if (!dataText) return;

    let payload = {};
    try {
      payload = JSON.parse(dataText);
    } catch {
      payload = {};
    }

    if (eventName === "start") {
      if (payload?.title && els.chatTitle) {
        els.chatTitle.textContent = payload.title;
      }
      return;
    }

    if (eventName === "delta") {
      state.activeAssistantRawText += String(payload?.text || "");
      updateStreamingAssistantVisual();
      return;
    }

    if (eventName === "error") {
      throw new Error(String(payload?.message || "Stream failed."));
    }

    if (eventName === "done") {
      const assistantTimestamp = payload?.message?.timestamp || Math.floor(Date.now() / 1000);
      finalizeStreamingAssistant(assistantTimestamp);
      await refreshStateAndSession(sessionId);
    }
  }

  async function streamMessage() {
    const input = els.messageInput;
    if (!input || state.isSending) return;

    const content = input.value.trim();
    if (!content) return;

    if (!state.activeSessionId) {
      await createSession();
    }

    const sessionId = state.activeSessionId;
    if (!sessionId) return;

    input.value = "";
    autosizeInput();
    setSending(true);

    appendMessage("user", content, Math.floor(Date.now() / 1000));

    const assistantNode = appendMessage("assistant", "");
    state.activeAssistantBubble = assistantNode?.bubble || null;
    state.activeAssistantTextNode = assistantNode?.textNode || null;
    state.activeAssistantCopyBtn = assistantNode?.copyBtn || null;
    state.activeAssistantMeta = assistantNode?.meta || null;
    state.activeAssistantRawText = "";

    const controller = new AbortController();
    state.activeStreamController = controller;

    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          content,
          model: els.modelSelect ? els.modelSelect.value : undefined
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      if (!response.body) {
        throw new Error("No stream body returned.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        let boundaryIndex;
        while ((boundaryIndex = buffer.indexOf("\n\n")) !== -1) {
          const rawEvent = buffer.slice(0, boundaryIndex);
          buffer = buffer.slice(boundaryIndex + 2);
          await processSseEvent(rawEvent, sessionId);
        }
      }

      const leftover = buffer.trim();
      if (leftover) {
        await processSseEvent(leftover, sessionId);
      }
    } catch (error) {
      if (error?.name === "AbortError") {
        if (state.activeAssistantRawText.trim()) {
          finalizeStreamingAssistant(Math.floor(Date.now() / 1000));
        } else if (state.activeAssistantBubble?.parentElement) {
          state.activeAssistantBubble.parentElement.remove();
        }
        appendMessage("system", "Stopped.");
      } else {
        if (state.activeAssistantRawText.trim()) {
          finalizeStreamingAssistant(Math.floor(Date.now() / 1000));
        } else if (state.activeAssistantBubble?.parentElement) {
          state.activeAssistantBubble.parentElement.remove();
        }
        appendMessage("assistant", `Error: ${error.message}`);
      }
    } finally {
      state.activeStreamController = null;
      resetActiveAssistantState();
      setSending(false);
    }
  }

  function stopMessage() {
    if (state.activeStreamController) {
      state.activeStreamController.abort();
      return;
    }

    setSending(false);
    appendMessage("system", "Stopped.");
  }

  function wireEvents() {
    if (els.toggleSidebar) {
      els.toggleSidebar.addEventListener("click", toggleSidebar);
    }

    if (els.mobileSidebarBtn) {
      els.mobileSidebarBtn.addEventListener("click", toggleSidebar);
    }

    if (els.memoryToggleBtnTop) {
      els.memoryToggleBtnTop.addEventListener("click", toggleMemory);
    }

    if (els.closeMemoryBtn) {
      els.closeMemoryBtn.addEventListener("click", toggleMemory);
    }

    if (els.themeToggleBtn) {
      els.themeToggleBtn.addEventListener("click", () => {
        toggleTheme();
        renderMemory();
      });
    }

    if (els.backgroundBtn) {
      els.backgroundBtn.addEventListener("click", backgroundAction);
    }

    if (els.attachBtn && els.fileInput) {
      els.attachBtn.addEventListener("click", () => els.fileInput.click());
      els.fileInput.addEventListener("change", onFilePicked);
    }

    if (els.attachedFiles) {
      els.attachedFiles.addEventListener("click", onAttachedFilesClick);
    }

    if (els.sendBtn) {
      els.sendBtn.addEventListener("click", streamMessage);
    }

    if (els.stopBtn) {
      els.stopBtn.addEventListener("click", stopMessage);
    }

    if (els.newSessionBtn) {
      els.newSessionBtn.addEventListener("click", createSession);
    }

    if (els.deleteSessionBtn) {
      els.deleteSessionBtn.addEventListener("click", deleteSession);
    }

    if (els.renameSessionBtn) {
      els.renameSessionBtn.addEventListener("click", renameSession);
    }

    if (els.duplicateSessionBtn) {
      els.duplicateSessionBtn.addEventListener("click", duplicateSession);
    }

    if (els.pinSessionBtn) {
      els.pinSessionBtn.addEventListener("click", pinSession);
    }

    if (els.exportSessionBtn) {
      els.exportSessionBtn.addEventListener("click", exportSession);
    }

    if (els.messageInput) {
      els.messageInput.addEventListener("input", autosizeInput);
      els.messageInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          streamMessage();
        }
      });
    }

    if (els.modelSelect) {
      els.modelSelect.addEventListener("change", () => {
        if (els.modelStatus) {
          els.modelStatus.textContent = `Model: ${els.modelSelect.value}`;
        }
        renderMemory();
      });
    }

    if (els.sessionList) {
      els.sessionList.addEventListener("click", async (event) => {
        const btn = event.target.closest("[data-session-id]");
        if (!btn) return;

        const sessionId = String(btn.getAttribute("data-session-id") || "").trim();
        if (!sessionId) return;

        await loadSession(sessionId);

        if (isMobile()) {
          state.sidebarOpenMobile = false;
          applyLayoutState();
        }
      });
    }

    window.addEventListener("resize", () => {
      applyLayoutState();
      autosizeInput();
    });

    document.addEventListener("click", (event) => {
      const clickedInsideSidebar = els.sidebar && els.sidebar.contains(event.target);
      const clickedSidebarButton =
        (els.toggleSidebar && els.toggleSidebar.contains(event.target)) ||
        (els.mobileSidebarBtn && els.mobileSidebarBtn.contains(event.target));

      if (isMobile() && state.sidebarOpenMobile && !clickedInsideSidebar && !clickedSidebarButton) {
        state.sidebarOpenMobile = false;
        applyLayoutState();
      }

      const clickedInsideMemory = els.memoryPanel && els.memoryPanel.contains(event.target);
      const clickedMemoryButton =
        (els.memoryToggleBtnTop && els.memoryToggleBtnTop.contains(event.target)) ||
        (els.closeMemoryBtn && els.closeMemoryBtn.contains(event.target));

      if (isTabletOrBelow() && state.memoryOpenMobile && !clickedInsideMemory && !clickedMemoryButton) {
        state.memoryOpenMobile = false;
        applyLayoutState();
      }
    });
  }

  function initState() {
    state.sidebarCollapsedDesktop = readBool(STORAGE_KEYS.sidebarDesktopCollapsed, false);
    state.memoryCollapsedDesktop = readBool(STORAGE_KEYS.memoryDesktopCollapsed, false);
    state.sidebarOpenMobile = false;
    state.memoryOpenMobile = false;
    state.activeSessionId = readText(STORAGE_KEYS.activeSessionId, "").trim() || null;
  }

  async function init() {
    initState();
    setTheme(getSavedTheme());
    autosizeInput();
    setupVoice();
    wireEvents();
    applyLayoutState();
    renderAttachedFiles();
    renderEmptyState();
    renderMemory();

    await loadModels();
    await refreshStateAndSession();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      init().catch((error) => {
        console.error("Nova init failed:", error);
        appendMessage("assistant", `Init error: ${error.message}`);
      });
    });
  } else {
    init().catch((error) => {
      console.error("Nova init failed:", error);
      appendMessage("assistant", `Init error: ${error.message}`);
    });
  }
})();