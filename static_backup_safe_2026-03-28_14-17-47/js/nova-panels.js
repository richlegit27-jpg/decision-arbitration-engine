(() => {
  "use strict";

  if (window.__novaPanelsLoaded) return;
  window.__novaPanelsLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.panels = Nova.panels || {};

  const MOBILE_BREAKPOINT = 980;

  function byId(id) {
    return document.getElementById(id);
  }

  function isMobile() {
    return window.innerWidth <= MOBILE_BREAKPOINT;
  }

  function getEls() {
    return {
      app: byId("novaApp"),
      leftSidebar: byId("leftSidebar"),
      memoryPanel: byId("memoryPanel"),
      toggleSidebarBtn: byId("toggleSidebarBtn"),
      closeSidebarBtn: byId("closeSidebarBtn"),
      toggleMemoryBtn: byId("toggleMemoryBtn"),
      closeMemoryBtn: byId("closeMemoryBtn"),
      mainShell: byId("mainShell"),
    };
  }

  const panelState = {
    sidebarOpen: true,
    memoryOpen: true,
    initialized: false,
    lastMobile: null,
  };

  function setBtnExpanded(btn, open) {
    if (!btn) return;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    btn.classList.toggle("is-active", !!open);
  }

  function applySidebar(open) {
    const { app, leftSidebar, toggleSidebarBtn } = getEls();
    if (!app || !leftSidebar) return;

    panelState.sidebarOpen = !!open;

    app.classList.toggle("sidebar-open", !!open);
    app.classList.toggle("sidebar-closed", !open);

    leftSidebar.classList.toggle("is-open", !!open);
    leftSidebar.classList.toggle("is-closed", !open);
    leftSidebar.setAttribute("aria-hidden", open ? "false" : "true");

    setBtnExpanded(toggleSidebarBtn, !!open);
  }

  function applyMemory(open) {
    const { app, memoryPanel, toggleMemoryBtn } = getEls();
    if (!app || !memoryPanel) return;

    panelState.memoryOpen = !!open;

    app.classList.toggle("memory-open", !!open);
    app.classList.toggle("memory-closed", !open);

    memoryPanel.classList.toggle("is-open", !!open);
    memoryPanel.classList.toggle("is-closed", !open);
    memoryPanel.setAttribute("aria-hidden", open ? "false" : "true");

    setBtnExpanded(toggleMemoryBtn, !!open);
  }

  function syncFromDom() {
    const { app, leftSidebar, memoryPanel } = getEls();
    if (!app || !leftSidebar || !memoryPanel) return false;

    const sidebarOpen =
      leftSidebar.classList.contains("is-open") ||
      app.classList.contains("sidebar-open") ||
      (!leftSidebar.classList.contains("is-closed") &&
        !app.classList.contains("sidebar-closed"));

    const memoryOpen =
      memoryPanel.classList.contains("is-open") ||
      app.classList.contains("memory-open") ||
      (!memoryPanel.classList.contains("is-closed") &&
        !app.classList.contains("memory-closed"));

    applySidebar(sidebarOpen);
    applyMemory(memoryOpen);
    return true;
  }

  function openSidebar() {
    applySidebar(true);
  }

  function closeSidebar() {
    applySidebar(false);
  }

  function toggleSidebar() {
    applySidebar(!panelState.sidebarOpen);
  }

  function openMemory() {
    applyMemory(true);
  }

  function closeMemory() {
    applyMemory(false);
  }

  function toggleMemory() {
    applyMemory(!panelState.memoryOpen);
  }

  function handleMainShellClick() {
    if (!isMobile()) return;
    closeSidebar();
    closeMemory();
  }

  function handleEscape(event) {
    if (event.key !== "Escape") return;
    if (panelState.sidebarOpen) closeSidebar();
    if (panelState.memoryOpen) closeMemory();
  }

  function recoverForViewport() {
    const mobileNow = isMobile();
    const firstRun = panelState.lastMobile === null;
    const changed = panelState.lastMobile !== mobileNow;

    panelState.lastMobile = mobileNow;

    if (firstRun) {
      if (mobileNow) {
        applySidebar(false);
        applyMemory(false);
      } else {
        syncFromDom();
      }
      return;
    }

    if (!changed) {
      applySidebar(panelState.sidebarOpen);
      applyMemory(panelState.memoryOpen);
      return;
    }

    if (mobileNow) {
      applySidebar(false);
      applyMemory(false);
      return;
    }

    applySidebar(panelState.sidebarOpen);
    applyMemory(panelState.memoryOpen);
  }

  function bindClickOnce(el, handler) {
    if (!el || el.__novaPanelBound) return;
    el.__novaPanelBound = true;

    el.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      handler();
    });
  }

  function bindEvents() {
    const {
      toggleSidebarBtn,
      closeSidebarBtn,
      toggleMemoryBtn,
      closeMemoryBtn,
      mainShell,
    } = getEls();

    bindClickOnce(toggleSidebarBtn, toggleSidebar);
    bindClickOnce(closeSidebarBtn, closeSidebar);
    bindClickOnce(toggleMemoryBtn, toggleMemory);
    bindClickOnce(closeMemoryBtn, closeMemory);

    if (mainShell && !mainShell.__novaPanelShellBound) {
      mainShell.__novaPanelShellBound = true;
      mainShell.addEventListener("click", handleMainShellClick);
    }

    if (!window.__novaPanelsResizeBound) {
      window.__novaPanelsResizeBound = true;
      let timer = null;

      window.addEventListener("resize", () => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          recoverForViewport();
        }, 90);
      });
    }

    if (!window.__novaPanelsKeyBound) {
      window.__novaPanelsKeyBound = true;
      window.addEventListener("keydown", handleEscape);
    }
  }

  function bootstrap() {
    const { app, leftSidebar, memoryPanel } = getEls();
    if (!app || !leftSidebar || !memoryPanel) {
      console.warn("Nova panels: required elements missing.");
      return false;
    }

    bindEvents();

    if (!panelState.initialized) {
      panelState.initialized = true;
      syncFromDom();
      recoverForViewport();
    } else {
      syncFromDom();
    }

    return true;
  }

  Nova.panels.bootstrap = bootstrap;
  Nova.panels.sync = syncFromDom;
  Nova.panels.openSidebar = openSidebar;
  Nova.panels.closeSidebar = closeSidebar;
  Nova.panels.toggleSidebar = toggleSidebar;
  Nova.panels.openMemory = openMemory;
  Nova.panels.closeMemory = closeMemory;
  Nova.panels.toggleMemory = toggleMemory;
  Nova.panels.getState = () => ({
    sidebarOpen: !!panelState.sidebarOpen,
    memoryOpen: !!panelState.memoryOpen,
    mobile: isMobile(),
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
  } else {
    bootstrap();
  }
})();