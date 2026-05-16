(() => {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  if (Nova.uiLoaded) return;
  Nova.uiLoaded = true;

  const state = Nova.state;
  const dom = Nova.dom;
  const { STORAGE } = Nova.config;
  const { saveStorage } = Nova.utils;

  function byId(id) {
    return dom.byId ? dom.byId(id) : document.getElementById(id);
  }

  function closestActionTarget(target) {
    return target?.closest?.("[data-action]") || null;
  }

  async function handleOpenSession(sessionId) {
    if (!sessionId || !Nova.sessions?.loadSession) return;
    await Nova.sessions.loadSession(sessionId);
    Nova.shell?.savePreferences?.();
    Nova.render?.renderAll?.();
  }

  async function handleNewSession() {
    if (!Nova.sessions?.createSession) return;
    await Nova.sessions.createSession("New chat");
    Nova.render?.renderAll?.();
    focusComposer();
  }

  async function handleDeleteSession(sessionId) {
    if (!sessionId || !Nova.sessions?.deleteSession) return;
    await Nova.sessions.deleteSession(sessionId);
    Nova.render?.renderAll?.();
  }

  async function handleRenameSession(sessionId) {
    if (!sessionId || !Nova.sessions?.renameSession) return;

    const current = Nova.sessions.getSessionById?.(sessionId);
    const nextTitle = window.prompt("Rename chat", current?.title || "New chat");
    if (!nextTitle || !nextTitle.trim()) return;

    await Nova.sessions.renameSession(sessionId, nextTitle.trim());
    Nova.render?.renderAll?.();
  }

  async function handleDuplicateSession(sessionId) {
    if (!sessionId || !Nova.sessions?.duplicateSession) return;
    await Nova.sessions.duplicateSession(sessionId);
    Nova.render?.renderAll?.();
  }

  async function handlePinSession(sessionId) {
    if (!sessionId || !Nova.sessions?.togglePinSession) return;
    await Nova.sessions.togglePinSession(sessionId);
    Nova.render?.renderAll?.();
  }

  async function handleDeleteMemory(memoryId) {
    if (!memoryId || !Nova.memory?.deleteMemory) return;
    await Nova.memory.deleteMemory(memoryId);
    Nova.render?.renderMemory?.();
  }

  function handleRemoveAttachment(index) {
    const fileIndex = Number(index);
    if (!Number.isFinite(fileIndex)) return;

    state.attachedFiles.splice(fileIndex, 1);
    Nova.render?.renderAttachments?.();
  }

  async function handleCopyMessage(messageId) {
    const message = (state.messages || []).find((item) => String(item.id || "") === String(messageId));
    if (!message?.content) return;

    try {
      await navigator.clipboard.writeText(message.content);
    } catch (error) {
      console.error("Copy failed:", error);
    }
  }

  async function handleRegenerateMessage() {
    if (!Nova.chat?.regenerateLastAssistant) return;
    await Nova.chat.regenerateLastAssistant();
  }

  function toggleSidebar() {
    state.sidebarOpen = !state.sidebarOpen;
    saveStorage(STORAGE.sidebarOpen, String(state.sidebarOpen));
    Nova.render?.renderComposerState?.();
  }

  function toggleMemoryPanel() {
    state.memoryOpen = !state.memoryOpen;
    saveStorage(STORAGE.memoryOpen, String(state.memoryOpen));
    Nova.render?.renderComposerState?.();
  }

  function toggleTheme() {
    state.themeMode = state.themeMode === "light" ? "dark" : "light";
    saveStorage(STORAGE.themeMode, state.themeMode);
    Nova.shell?.applyTheme?.();
  }

  function cycleBackground() {
    const modes = ["default", "grid", "dots", "glow", "minimal"];
    const currentIndex = modes.indexOf(state.backgroundMode || "default");
    const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % modes.length : 0;
    state.backgroundMode = modes[nextIndex];
    saveStorage(STORAGE.backgroundMode, state.backgroundMode);
    Nova.shell?.applyTheme?.();
  }

  async function submitComposer() {
    if (!Nova.chat?.sendMessage) return;
    await Nova.chat.sendMessage();
  }

  function handleComposerKeydown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitComposer();
      return;
    }

    requestAnimationFrame(() => {
      Nova.shell?.autoResizeComposer?.();
    });
  }

  function handleComposerInput() {
    Nova.shell?.autoResizeComposer?.();
  }

  function handleFileInputChange(event) {
    const files = Array.from(event.target?.files || []);
    if (!files.length) return;

    state.attachedFiles.push(...files);
    Nova.render?.renderAttachments?.();

    if (event.target) {
      event.target.value = "";
    }
  }

  function focusComposer() {
    const input = byId("composerInput");
    if (input) input.focus();
  }

  async function handleClick(event) {
    const actionEl = closestActionTarget(event.target);
    if (!actionEl) return;

    const action = actionEl.dataset.action;
    const sessionId = actionEl.dataset.sessionId;
    const memoryId = actionEl.dataset.memoryId;
    const fileIndex = actionEl.dataset.fileIndex;
    const messageId = actionEl.dataset.messageId;

    try {
      switch (action) {
        case "open-session":
          await handleOpenSession(sessionId);
          break;
        case "new-session":
          await handleNewSession();
          break;
        case "delete-session":
          await handleDeleteSession(sessionId);
          break;
        case "rename-session":
          await handleRenameSession(sessionId);
          break;
        case "duplicate-session":
          await handleDuplicateSession(sessionId);
          break;
        case "pin-session":
          await handlePinSession(sessionId);
          break;
        case "delete-memory":
          await handleDeleteMemory(memoryId);
          break;
        case "remove-attachment":
          handleRemoveAttachment(fileIndex);
          break;
        case "copy-message":
          await handleCopyMessage(messageId);
          break;
        case "regenerate-message":
          await handleRegenerateMessage(messageId);
          break;
        case "toggle-sidebar":
          toggleSidebar();
          break;
        case "toggle-memory":
          toggleMemoryPanel();
          break;
        case "toggle-theme":
          toggleTheme();
          break;
        case "cycle-background":
          cycleBackground();
          break;
        case "send-message":
          await submitComposer();
          break;
        default:
          break;
      }
    } catch (error) {
      console.error(`UI action failed: ${action}`, error);
    }
  }

  function bindTopLevelClicks() {
    document.addEventListener("click", handleClick);
  }

  function bindComposer() {
    const input = byId("composerInput");
    const sendBtn = byId("sendBtn");
    const fileInput = byId("fileInput");

    if (input && !input.dataset.boundNovaInput) {
      input.addEventListener("keydown", handleComposerKeydown);
      input.addEventListener("input", handleComposerInput);
      input.dataset.boundNovaInput = "true";
    }

    if (sendBtn && !sendBtn.dataset.boundNovaClick) {
      sendBtn.addEventListener("click", submitComposer);
      sendBtn.dataset.boundNovaClick = "true";
    }

    if (fileInput && !fileInput.dataset.boundNovaFile) {
      fileInput.addEventListener("change", handleFileInputChange);
      fileInput.dataset.boundNovaFile = "true";
    }
  }

  function bindPanelButtons() {
    const sidebarToggle = byId("sidebarToggle");
    const memoryToggle = byId("memoryToggle");
    const newSessionBtn = byId("newSessionBtn");
    const themeBtn = byId("themeToggle");
    const backgroundBtn = byId("backgroundToggle");

    if (sidebarToggle && !sidebarToggle.dataset.boundNovaClick) {
      sidebarToggle.dataset.action = sidebarToggle.dataset.action || "toggle-sidebar";
      sidebarToggle.dataset.boundNovaClick = "true";
    }

    if (memoryToggle && !memoryToggle.dataset.boundNovaClick) {
      memoryToggle.dataset.action = memoryToggle.dataset.action || "toggle-memory";
      memoryToggle.dataset.boundNovaClick = "true";
    }

    if (newSessionBtn && !newSessionBtn.dataset.boundNovaClick) {
      newSessionBtn.dataset.action = newSessionBtn.dataset.action || "new-session";
      newSessionBtn.dataset.boundNovaClick = "true";
    }

    if (themeBtn && !themeBtn.dataset.boundNovaClick) {
      themeBtn.dataset.action = themeBtn.dataset.action || "toggle-theme";
      themeBtn.dataset.boundNovaClick = "true";
    }

    if (backgroundBtn && !backgroundBtn.dataset.boundNovaClick) {
      backgroundBtn.dataset.action = backgroundBtn.dataset.action || "cycle-background";
      backgroundBtn.dataset.boundNovaClick = "true";
    }
  }

  function bindEvents() {
    if (!document.body.dataset.novaUiBound) {
      bindTopLevelClicks();
      document.body.dataset.novaUiBound = "true";
    }

    bindComposer();
    bindPanelButtons();
  }

  Nova.ui = {
    handleOpenSession,
    handleNewSession,
    handleDeleteSession,
    handleRenameSession,
    handleDuplicateSession,
    handlePinSession,
    handleDeleteMemory,
    handleRemoveAttachment,
    handleCopyMessage,
    handleRegenerateMessage,
    toggleSidebar,
    toggleMemoryPanel,
    toggleTheme,
    cycleBackground,
    submitComposer,
    handleComposerKeydown,
    handleComposerInput,
    handleFileInputChange,
    focusComposer,
    bindEvents,
  };
})();