(() => {
  "use strict";

  window.NovaRender = window.NovaRender || {};
  const NovaRender = window.NovaRender;

  if (NovaRender.panelsLoaded) return;
  NovaRender.panelsLoaded = true;

  const els = NovaRender.els || {};
  const state = NovaRender.state || {};
  const hasEl = NovaRender.hasEl || ((el) => !!el);
  const isMobileViewport = NovaRender.isMobileViewport || (() => window.innerWidth <= 900);
  const INPUT_MAX_HEIGHT = NovaRender.INPUT_MAX_HEIGHT || 220;
  const MEMORY_INPUT_MAX_HEIGHT = NovaRender.MEMORY_INPUT_MAX_HEIGHT || 180;

  function showBackdrop(show) {
    els.mobileBackdrop?.classList.toggle("hidden", !show);
  }

  function syncViewportMode() {
    state.isMobile = isMobileViewport();

    if (!state.isMobile) {
      state.sidebarOpen = !els.sidebar?.classList.contains("hidden");
      state.memoryOpen = !els.memory?.classList.contains("hidden");

      els.sidebar?.classList.remove("mobile-open");
      els.memory?.classList.remove("mobile-open");
      els.mobileBackdrop?.classList.add("hidden");
      return;
    }

    els.sidebar?.classList.add("hidden");
    els.memory?.classList.add("hidden");
    els.sidebar?.classList.remove("mobile-open");
    els.memory?.classList.remove("mobile-open");

    state.sidebarOpen = false;
    state.memoryOpen = false;

    els.mobileBackdrop?.classList.add("hidden");
  }

  function closeMobilePanels() {
    if (!state.isMobile) return;

    state.sidebarOpen = false;
    state.memoryOpen = false;

    els.sidebar?.classList.remove("mobile-open");
    els.memory?.classList.remove("mobile-open");

    showBackdrop(false);
  }

  function toggleSidebarPanel() {
    if (!hasEl(els.sidebar)) return;

    if (!state.isMobile) {
      els.sidebar.classList.toggle("hidden");
      return;
    }

    const next = !state.sidebarOpen;
    state.sidebarOpen = next;
    state.memoryOpen = false;

    els.sidebar.classList.toggle("mobile-open", next);
    els.memory?.classList.remove("mobile-open");

    showBackdrop(next);
  }

  function toggleMemoryPanel() {
    if (!hasEl(els.memory)) return;

    if (!state.isMobile) {
      els.memory.classList.toggle("hidden");
      return;
    }

    const next = !state.memoryOpen;
    state.memoryOpen = next;
    state.sidebarOpen = false;

    els.memory.classList.toggle("mobile-open", next);
    els.sidebar?.classList.remove("mobile-open");

    showBackdrop(next);
  }

  function resizeTextarea(textarea, maxHeight = INPUT_MAX_HEIGHT) {
    if (!textarea) return;

    textarea.style.height = "0px";

    const nextHeight = Math.min(textarea.scrollHeight || 56, maxHeight);
    textarea.style.height = `${Math.max(nextHeight, 56)}px`;
    textarea.style.overflowY = (textarea.scrollHeight || 0) > maxHeight ? "auto" : "hidden";
  }

  function handleViewportResize() {
    const wasMobile = !!state.isMobile;

    syncViewportMode();
    resizeTextarea(els.input, INPUT_MAX_HEIGHT);
    resizeTextarea(els.memoryInput, MEMORY_INPUT_MAX_HEIGHT);

    if (wasMobile && !state.isMobile) {
      els.sidebar?.classList.remove("hidden");
    }
  }

  NovaRender.showBackdrop = showBackdrop;
  NovaRender.syncViewportMode = syncViewportMode;
  NovaRender.closeMobilePanels = closeMobilePanels;
  NovaRender.toggleSidebarPanel = toggleSidebarPanel;
  NovaRender.toggleMemoryPanel = toggleMemoryPanel;
  NovaRender.resizeTextarea = resizeTextarea;
  NovaRender.handleViewportResize = handleViewportResize;
})();