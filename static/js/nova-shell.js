(() => {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  if (Nova.shellLoaded) return;
  Nova.shellLoaded = true;

  const state = Nova.state;
  const { STORAGE } = Nova.config;
  const { loadStorage, saveStorage, safeJsonParse } = Nova.utils;

  function hydratePreferences() {
    state.activeSessionId = loadStorage(STORAGE.activeSessionId, null);
    state.currentModel = loadStorage(STORAGE.currentModel, Nova.config.DEFAULT_MODEL) || Nova.config.DEFAULT_MODEL;
    state.sidebarOpen = loadStorage(STORAGE.sidebarOpen, "true") !== "false";
    state.memoryOpen = loadStorage(STORAGE.memoryOpen, "true") !== "false";
    state.themeMode = loadStorage(STORAGE.themeMode, "dark") || "dark";
    state.backgroundMode = loadStorage(STORAGE.backgroundMode, "default") || "default";
    state.pinnedSessionIds = safeJsonParse(loadStorage(STORAGE.pinnedSessionIds, "[]"), []);
    if (!Array.isArray(state.pinnedSessionIds)) state.pinnedSessionIds = [];
  }

  function applyTheme() {
    document.body.classList.toggle("theme-light", state.themeMode === "light");
    document.body.classList.toggle("theme-dark", state.themeMode !== "light");

    const modes = ["bg-default", "bg-grid", "bg-dots", "bg-glow", "bg-minimal"];
    for (const mode of modes) document.body.classList.remove(mode);
    document.body.classList.add(`bg-${state.backgroundMode || "default"}`);
  }

  function applyPanelState() {
    const sidebar = document.getElementById("sidebar");
    const memoryPanel = document.getElementById("memoryPanel");

    if (sidebar) sidebar.classList.toggle("collapsed", !state.sidebarOpen);
    if (memoryPanel) memoryPanel.classList.toggle("collapsed", !state.memoryOpen);
  }

  function savePreferences() {
    saveStorage(STORAGE.activeSessionId, state.activeSessionId || "");
    saveStorage(STORAGE.currentModel, state.currentModel || Nova.config.DEFAULT_MODEL);
    saveStorage(STORAGE.sidebarOpen, String(!!state.sidebarOpen));
    saveStorage(STORAGE.memoryOpen, String(!!state.memoryOpen));
    saveStorage(STORAGE.themeMode, state.themeMode || "dark");
    saveStorage(STORAGE.backgroundMode, state.backgroundMode || "default");
    saveStorage(STORAGE.pinnedSessionIds, JSON.stringify(state.pinnedSessionIds || []));
  }

  function autoResizeComposer() {
    const input = document.getElementById("composerInput");
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, Nova.config.MAX_INPUT_HEIGHT)}px`;
  }

  Nova.shell = {
    hydratePreferences,
    applyTheme,
    applyPanelState,
    savePreferences,
    autoResizeComposer,
  };
})();