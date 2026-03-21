(() => {
  "use strict";

  const sessionList = document.getElementById("sessionList");
  const chatMessages = document.getElementById("chatMessages");
  const messageInput = document.getElementById("messageInput");
  const sendBtn = document.getElementById("sendBtn");

  const newSessionBtn = document.getElementById("newSessionBtn");
  const deleteSessionBtn = document.getElementById("deleteSessionBtn");
  const renameSessionBtn = document.getElementById("renameSessionBtn");
  const clearSessionBtn = document.getElementById("clearSessionBtn");
  const duplicateSessionBtn = document.getElementById("duplicateSessionBtn");
  const pinSessionBtn = document.getElementById("pinSessionBtn");
  const exportSessionBtn = document.getElementById("exportSessionBtn");

  const themeToggleBtn = document.getElementById("themeToggleBtn");
  const backgroundBtn = document.getElementById("backgroundBtn");

  const chatTitle = document.getElementById("chatTitle");
  const chatSubtitle = document.getElementById("chatSubtitle");
  const modelStatus = document.getElementById("modelStatus");
  const modelSelect = document.getElementById("modelSelect");

  const memoryPanel = document.getElementById("memoryPanel");
  const memoryToggleBtnTop = document.getElementById("memoryToggleBtnTop");
  const closeMemoryBtn = document.getElementById("closeMemoryBtn");

  const attachBtn = document.getElementById("attachBtn");
  const fileInput = document.getElementById("fileInput");
  const attachedFiles = document.getElementById("attachedFiles");

  const voiceBtn = document.getElementById("voiceBtn");
  const settingsBtnTop = document.getElementById("settingsBtnTop");
  const changePasswordBtn = document.getElementById("changePasswordBtn");
  const logoutBtn = document.getElementById("logoutBtn");

  const mobileSidebarBtn = document.getElementById("mobileSidebarBtn");
  const sidebar = document.getElementById("sidebar");

  const appShell = document.getElementById("appShell");

  const STORAGE_KEYS = {
    theme: "nova_theme",
    background: "nova_background",
    pinned: "nova_pinned_sessions",
    memoryOpen: "nova_memory_open"
  };

  const BACKGROUNDS = ["default", "midnight", "ocean", "ember"];

  let attachedFileList = [];
  let recognition = null;
  let voiceActive = false;

  let state = {
    active_session_id: null,
    sessions: [],
    active_messages: []
  };

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function normalizeState(payload) {
    const base = payload && payload.state ? payload.state : payload;
    return {
      active_session_id: base?.active_session_id ?? null,
      sessions: safeArray(base?.sessions),
      active_messages: safeArray(base?.active_messages)
    };
  }

  function getPinnedIds() {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.pinned);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function setPinnedIds(ids) {
    localStorage.setItem(STORAGE_KEYS.pinned, JSON.stringify(ids));
  }

  function isPinned(sessionId) {
    return getPinnedIds().includes(sessionId);
  }

  function sortSessionsForDisplay(sessions) {
    const pinned = new Set(getPinnedIds());
    return [...safeArray(sessions)].sort((a, b) => {
      const aPinned = pinned.has(a.id) ? 1 : 0;
      const bPinned = pinned.has(b.id) ? 1 : 0;
      if (aPinned !== bPinned) return bPinned - aPinned;
      return 0;
    });
  }

  async function api(url, options = {}) {
    const res = await fetch(url, options);
    const text = await res.text();

    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      throw new Error(`Invalid JSON from ${url}`);
    }

    if (!res.ok) {
      throw new Error(data?.error || `API error ${res.status}`);
    }

    return data;
  }

  async function refreshState() {
    const data = await api("/api/state");
    state = normalizeState(data);
    render();
  }

  function render() {
    renderSessions();
    renderMessages();
    renderHeader();
    renderThemeButtons();
    renderAttachedFiles();
    renderMemoryState();
  }

  function renderHeader() {
    const active = state.sessions.find(s => s.id === state.active_session_id);

    if (chatTitle) {
      chatTitle.textContent = active?.name || "Nova";
    }

    if (chatSubtitle) {
      const count = safeArray(state.active_messages).length;
      chatSubtitle.textContent = count > 0 ? `${count} messages` : "Ready";
    }

    if (modelStatus) {
      modelStatus.textContent = voiceActive ? "Voice listening..." : "Model ready";
    }

    if (pinSessionBtn) {
      pinSessionBtn.textContent = isPinned(state.active_session_id) ? "Unpin" : "Pin";
    }
  }

  function renderSessions() {
    if (!sessionList) return;

    sessionList.innerHTML = "";
    const sessions = sortSessionsForDisplay(state.sessions);

    sessions.forEach((session) => {
      const row = document.createElement("div");
      row.className = "session-row";
      if (session.id === state.active_session_id) {
        row.classList.add("active");
      }

      const main = document.createElement("div");
      main.className = "session-name";
      main.textContent = `${isPinned(session.id) ? "📌 " : ""}${session.name || "New Chat"}`;
      main.addEventListener("click", () => openSession(session.id));

      const tools = document.createElement("div");
      tools.className = "session-tools";

      const renameBtn = document.createElement("button");
      renameBtn.type = "button";
      renameBtn.textContent = "✎";
      renameBtn.title = "Rename";
      renameBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        renameSession(session.id, session.name || "New Chat");
      });

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.textContent = "🗑";
      deleteBtn.title = "Delete";
      deleteBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        await deleteSession(session.id);
      });

      tools.appendChild(renameBtn);
      tools.appendChild(deleteBtn);

      row.appendChild(main);
      row.appendChild(tools);
      sessionList.appendChild(row);
    });
  }

  function renderMessages() {
    if (!chatMessages) return;

    chatMessages.innerHTML = "";
    const messages = safeArray(state.active_messages);

    if (messages.length === 0) {
      chatMessages.innerHTML = `
        <div class="empty-state">
          <div class="empty-card">
            <div class="empty-title">Nova is ready</div>
            <div class="empty-subtitle">Start a new message, use voice, attach files, or open memory.</div>
          </div>
        </div>
      `;
      return;
    }

    messages.forEach((msg) => {
      const div = document.createElement("div");
      div.className = `message ${msg.role || "assistant"}`;
      div.textContent = msg.content || "";
      chatMessages.appendChild(div);
    });

    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function getCurrentTheme() {
    return localStorage.getItem(STORAGE_KEYS.theme) || "dark";
  }

  function getCurrentBackground() {
    const current = localStorage.getItem(STORAGE_KEYS.background) || "default";
    return BACKGROUNDS.includes(current) ? current : "default";
  }

  function applyTheme(theme) {
    const nextTheme = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", nextTheme);
    localStorage.setItem(STORAGE_KEYS.theme, nextTheme);
  }

  function applyBackground(background) {
    const nextBackground = BACKGROUNDS.includes(background) ? background : "default";
    document.documentElement.setAttribute("data-bg", nextBackground);
    localStorage.setItem(STORAGE_KEYS.background, nextBackground);
  }

  function toggleTheme() {
    applyTheme(getCurrentTheme() === "dark" ? "light" : "dark");
    renderThemeButtons();
  }

  function cycleBackground() {
    const current = getCurrentBackground();
    const index = BACKGROUNDS.indexOf(current);
    const next = BACKGROUNDS[(index + 1) % BACKGROUNDS.length];
    applyBackground(next);
    renderThemeButtons();
  }

  function renderThemeButtons() {
    if (themeToggleBtn) {
      themeToggleBtn.textContent = getCurrentTheme() === "dark" ? "Theme: Dark" : "Theme: Light";
    }

    if (backgroundBtn) {
      const bg = getCurrentBackground();
      backgroundBtn.textContent = `Background: ${bg.charAt(0).toUpperCase()}${bg.slice(1)}`;
    }
  }

  function setMemoryOpen(isOpen) {
    localStorage.setItem(STORAGE_KEYS.memoryOpen, isOpen ? "1" : "0");
    if (memoryPanel) {
      memoryPanel.style.display = isOpen ? "" : "none";
      memoryPanel.setAttribute("aria-hidden", isOpen ? "false" : "true");
    }
  }

  function getMemoryOpen() {
    return localStorage.getItem(STORAGE_KEYS.memoryOpen) !== "0";
  }

  function renderMemoryState() {
    setMemoryOpen(getMemoryOpen());
  }

  function toggleMemoryPanel() {
    setMemoryOpen(!getMemoryOpen());
  }

  function openMemoryPanel() {
    setMemoryOpen(true);
  }

  function closeMemoryPanelNow() {
    setMemoryOpen(false);
  }

  function renderAttachedFiles() {
    if (!attachedFiles) return;

    attachedFiles.innerHTML = "";

    attachedFileList.forEach((file, index) => {
      const chip = document.createElement("div");
      chip.className = "attachment-chip";
      chip.style.display = "inline-flex";
      chip.style.alignItems = "center";
      chip.style.gap = "8px";
      chip.style.padding = "8px 10px";
      chip.style.border = "1px solid var(--border)";
      chip.style.borderRadius = "12px";
      chip.style.background = "var(--panel-soft)";

      const text = document.createElement("span");
      text.textContent = file.name;

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.textContent = "×";
      removeBtn.style.padding = "2px 8px";
      removeBtn.addEventListener("click", () => {
        attachedFileList.splice(index, 1);
        renderAttachedFiles();
      });

      chip.appendChild(text);
      chip.appendChild(removeBtn);
      attachedFiles.appendChild(chip);
    });
  }

  function openFilePicker() {
    fileInput?.click();
  }

  function handleFilesSelected(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    attachedFileList = [...attachedFileList, ...files];
    renderAttachedFiles();
    fileInput.value = "";
  }

  function setupVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;

    const recog = new SpeechRecognition();
    recog.lang = "en-US";
    recog.interimResults = true;
    recog.continuous = false;

    recog.onstart = () => {
      voiceActive = true;
      if (voiceBtn) voiceBtn.textContent = "Listening...";
      renderHeader();
    };

    recog.onresult = (event) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        transcript += event.results[i][0].transcript;
      }

      if (messageInput) {
        const current = messageInput.value.trim();
        messageInput.value = current ? `${current} ${transcript}` : transcript;
        messageInput.focus();
      }
    };

    recog.onend = () => {
      voiceActive = false;
      if (voiceBtn) voiceBtn.textContent = "Voice";
      renderHeader();
    };

    recog.onerror = () => {
      voiceActive = false;
      if (voiceBtn) voiceBtn.textContent = "Voice";
      renderHeader();
      alert("Voice input is not available in this browser/session.");
    };

    return recog;
  }

  function toggleVoiceInput() {
    if (!recognition) {
      recognition = setupVoiceRecognition();
    }

    if (!recognition) {
      alert("Voice input is not supported in this browser.");
      return;
    }

    if (voiceActive) {
      recognition.stop();
    } else {
      recognition.start();
    }
  }

  function exportCurrentSession() {
    const active = state.sessions.find(s => s.id === state.active_session_id);
    const title = (active?.name || "nova-chat").replace(/[^\w\- ]+/g, "").replace(/\s+/g, "_");
    const messages = safeArray(state.active_messages);

    const content = messages.length
      ? messages.map(msg => `[${(msg.role || "assistant").toUpperCase()}]\n${msg.content || ""}\n`).join("\n")
      : "No messages in this session.";

    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `${title || "nova-chat"}.txt`;
    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
  }

  async function duplicateSession() {
    const active = state.sessions.find(s => s.id === state.active_session_id);
    const baseName = active?.name || "New Chat";

    await createSession();

    if (!state.active_session_id) return;

    await renameSession(state.active_session_id, `${baseName} Copy`, true);
    await refreshState();
  }

  function togglePinSession() {
    const id = state.active_session_id;
    if (!id) return;

    const pinned = getPinnedIds();
    if (pinned.includes(id)) {
      setPinnedIds(pinned.filter(x => x !== id));
    } else {
      setPinnedIds([id, ...pinned]);
    }

    render();
  }

  function openSettings() {
    window.location.href = "/admin/change-password";
  }

  function doLogout() {
    window.location.href = "/logout";
  }

  function toggleSidebarMobile() {
    if (!sidebar || !appShell) return;

    const current = sidebar.style.display;
    if (window.innerWidth > 900) return;

    if (current === "block") {
      sidebar.style.display = "none";
    } else {
      sidebar.style.display = "block";
    }
  }

  async function sessionExists(sessionId) {
    if (!sessionId) return false;

    try {
      await api(`/api/chat/${sessionId}`);
      return true;
    } catch {
      return false;
    }
  }

  async function ensureValidActiveSession() {
    if (state.active_session_id) {
      const exists = await sessionExists(state.active_session_id);
      if (exists) return state.active_session_id;
    }

    await createSession();
    await refreshState();

    if (!state.active_session_id) {
      throw new Error("Could not create a valid session.");
    }

    return state.active_session_id;
  }

  async function openSession(sessionId) {
    if (!sessionId) return;

    const data = await api(`/api/chat/${sessionId}`);
    state.active_session_id = data.session_id || sessionId;
    state.active_messages = safeArray(data.messages);

    const existing = safeArray(state.sessions).find((s) => s.id === sessionId);
    if (existing && data.name) {
      existing.name = data.name;
    }

    render();
  }

  async function createSession() {
    await api("/api/session/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });

    await refreshState();
  }

  async function deleteSession(sessionId = state.active_session_id) {
    if (!sessionId) return;

    const ok = window.confirm("Delete this session?");
    if (!ok) return;

    await api("/api/session/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId })
    });

    const pinned = getPinnedIds().filter(id => id !== sessionId);
    setPinnedIds(pinned);

    await refreshState();
  }

  async function renameSession(sessionId = state.active_session_id, currentName = "New Chat", skipPrompt = false) {
    if (!sessionId) return;

    let nextName = currentName;

    if (!skipPrompt) {
      nextName = window.prompt("Rename session:", currentName);
      if (nextName === null) return;
      nextName = nextName.trim();
      if (!nextName) return;
    }

    await api("/api/session/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        name: nextName
      })
    });

    await refreshState();
  }

  async function clearSession() {
    if (!state.active_session_id) return;

    const ok = window.confirm("Clear messages but keep this session?");
    if (!ok) return;

    await api("/api/session/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.active_session_id })
    });

    await refreshState();
  }

  async function sendMessage() {
    const content = messageInput?.value?.trim();
    if (!content) return;

    sendBtn.disabled = true;
    const oldText = sendBtn.textContent;
    sendBtn.textContent = "Sending...";

    try {
      const sessionId = await ensureValidActiveSession();

      const data = await api("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          content,
          model: modelSelect?.value || "gpt-4.1-mini"
        })
      });

      messageInput.value = "";
      attachedFileList = [];
      renderAttachedFiles();

      if (data.state || data.sessions || data.active_session_id) {
        state = normalizeState(data);
        render();
      } else {
        await refreshState();
        await openSession(sessionId);
      }
    } catch (err) {
      console.error(err);
      alert(err.message || "Send failed");
      await refreshState();
    } finally {
      sendBtn.disabled = false;
      sendBtn.textContent = oldText;
    }
  }

  function bindEvents() {
    newSessionBtn?.addEventListener("click", createSession);
    deleteSessionBtn?.addEventListener("click", () => deleteSession());
    renameSessionBtn?.addEventListener("click", () => {
      const active = state.sessions.find(s => s.id === state.active_session_id);
      renameSession(state.active_session_id, active?.name || "New Chat");
    });
    clearSessionBtn?.addEventListener("click", clearSession);

    duplicateSessionBtn?.addEventListener("click", duplicateSession);
    pinSessionBtn?.addEventListener("click", togglePinSession);
    exportSessionBtn?.addEventListener("click", exportCurrentSession);

    themeToggleBtn?.addEventListener("click", toggleTheme);
    backgroundBtn?.addEventListener("click", cycleBackground);

    memoryToggleBtnTop?.addEventListener("click", openMemoryPanel);
    closeMemoryBtn?.addEventListener("click", closeMemoryPanelNow);

    attachBtn?.addEventListener("click", openFilePicker);
    fileInput?.addEventListener("change", handleFilesSelected);

    voiceBtn?.addEventListener("click", toggleVoiceInput);

    settingsBtnTop?.addEventListener("click", openSettings);
    changePasswordBtn?.addEventListener("click", openSettings);
    logoutBtn?.addEventListener("click", doLogout);

    mobileSidebarBtn?.addEventListener("click", toggleSidebarMobile);

    sendBtn?.addEventListener("click", sendMessage);

    messageInput?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  async function init() {
    applyTheme(getCurrentTheme());
    applyBackground(getCurrentBackground());
    bindEvents();
    renderMemoryState();
    await refreshState();

    if (!state.active_session_id || safeArray(state.sessions).length === 0) {
      await createSession();
    }
  }

  init().catch((err) => {
    console.error(err);
    alert(err.message || "Nova failed to load.");
  });
})();