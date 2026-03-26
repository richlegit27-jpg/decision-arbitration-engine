(() => {
  "use strict";

  if (window.__novaPanelsLoaded) return;
  window.__novaPanelsLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.panels = Nova.panels || {};
  Nova.dom = Nova.dom || {};
  Nova.constants = Nova.constants || {};

  const dom = Nova.dom;
  const byId = dom.byId || ((id) => document.getElementById(id));
  const qs = dom.qs || ((sel, root = document) => root.querySelector(sel));

  const STORAGE = {
    sidebarOpen: "nova_sidebar_open",
    memoryOpen: "nova_memory_open",
    ...(Nova.constants.STORAGE || {}),
  };

  const MOBILE_BREAKPOINT = Number(Nova.constants.MOBILE_BREAKPOINT || 980);

  function safeText(value) {
    if (Nova.utils && typeof Nova.utils.safeText === "function") {
      return Nova.utils.safeText(value);
    }
    return String(value ?? "").trim();
  }

  function setStatus(text) {
    if (Nova.utils && typeof Nova.utils.setStatus === "function") {
      Nova.utils.setStatus(text);
    }
  }

  function getAppRoot() {
    return (
      byId("novaApp") ||
      byId("appShell") ||
      byId("desktopApp") ||
      qs("[data-nova-app]") ||
      document.body
    );
  }

  function getBackdrop() {
    return (
      byId("panelBackdrop") ||
      byId("mobilePanelBackdrop") ||
      qs("[data-panel-backdrop]") ||
      qs(".panel-backdrop")
    );
  }

  function getLeftPanel() {
    return (
      byId("leftPanel") ||
      byId("sidebarPanel") ||
      byId("sidebar") ||
      byId("desktopSidebar") ||
      byId("mobileSidebar") ||
      qs("[data-left-panel]") ||
      qs(".left-panel") ||
      qs(".sidebar")
    );
  }

  function getRightPanel() {
    return (
      byId("rightPanel") ||
      byId("memoryPanel") ||
      byId("desktopMemoryPanel") ||
      byId("mobileMemoryPanel") ||
      qs("[data-right-panel]") ||
      qs("[data-memory-panel]") ||
      qs(".right-panel") ||
      qs(".memory-panel")
    );
  }

  function getLeftToggleButtons() {
    return [
      byId("sidebarToggleBtn"),
      byId("leftPanelToggleBtn"),
      byId("mobileSidebarToggle"),
      byId("desktopSidebarToggle"),
      qs("[data-toggle-left-panel]"),
      qs("[data-sidebar-toggle]"),
    ].filter(Boolean);
  }

  function getRightToggleButtons() {
    return [
      byId("memoryToggleBtn"),
      byId("rightPanelToggleBtn"),
      byId("mobileMemoryToggle"),
      byId("desktopMemoryToggle"),
      qs("[data-toggle-right-panel]"),
      qs("[data-memory-toggle]"),
    ].filter(Boolean);
  }

  function getCloseButtons() {
    return [
      ...Array.from(document.querySelectorAll("[data-close-panels]")),
      ...Array.from(document.querySelectorAll("[data-close-left-panel]")),
      ...Array.from(document.querySelectorAll("[data-close-right-panel]")),
    ];
  }

  function isMobilePanel() {
    return window.innerWidth <= MOBILE_BREAKPOINT;
  }

  function readBool(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      if (raw === null || raw === undefined || raw === "") return Boolean(fallback);
      if (raw === "true") return true;
      if (raw === "false") return false;
      return Boolean(fallback);
    } catch {
      return Boolean(fallback);
    }
  }

  function writeBool(key, value) {
    try {
      localStorage.setItem(key, value ? "true" : "false");
    } catch {}
  }

  function setBodyFlags({
    leftOpen = false,
    rightOpen = false,
    mobile = isMobilePanel(),
  } = {}) {
    const app = getAppRoot();
    const body = document.body;

    body.classList.toggle("mobile-panels-mode", mobile);
    body.classList.toggle("desktop-panels-mode", !mobile);

    body.classList.toggle("left-panel-open", Boolean(leftOpen));
    body.classList.toggle("left-panel-closed", !leftOpen);

    body.classList.toggle("right-panel-open", Boolean(rightOpen));
    body.classList.toggle("right-panel-closed", !rightOpen);

    body.classList.toggle("mobile-left-open", mobile && Boolean(leftOpen));
    body.classList.toggle("mobile-right-open", mobile && Boolean(rightOpen));
    body.classList.toggle("mobile-panel-open", mobile && (Boolean(leftOpen) || Boolean(rightOpen)));

    if (app && app !== body) {
      app.classList.toggle("mobile-panels-mode", mobile);
      app.classList.toggle("desktop-panels-mode", !mobile);

      app.classList.toggle("left-panel-open", Boolean(leftOpen));
      app.classList.toggle("left-panel-closed", !leftOpen);

      app.classList.toggle("right-panel-open", Boolean(rightOpen));
      app.classList.toggle("right-panel-closed", !rightOpen);

      app.classList.toggle("mobile-left-open", mobile && Boolean(leftOpen));
      app.classList.toggle("mobile-right-open", mobile && Boolean(rightOpen));
      app.classList.toggle("mobile-panel-open", mobile && (Boolean(leftOpen) || Boolean(rightOpen)));
    }
  }

  function applyPanelState({
    leftOpen = false,
    rightOpen = false,
    mobile = isMobilePanel(),
  } = {}) {
    const left = getLeftPanel();
    const right = getRightPanel();
    const backdrop = getBackdrop();

    if (left) {
      left.hidden = false;
      left.classList.toggle("is-open", Boolean(leftOpen));
      left.classList.toggle("is-closed", !leftOpen);
      left.classList.toggle("is-mobile-panel", mobile);
      left.classList.toggle("is-desktop-panel", !mobile);
      left.setAttribute("aria-hidden", leftOpen ? "false" : "true");
    }

    if (right) {
      right.hidden = false;
      right.classList.toggle("is-open", Boolean(rightOpen));
      right.classList.toggle("is-closed", !rightOpen);
      right.classList.toggle("is-mobile-panel", mobile);
      right.classList.toggle("is-desktop-panel", !mobile);
      right.setAttribute("aria-hidden", rightOpen ? "false" : "true");
    }

    if (backdrop) {
      const showBackdrop = mobile && (Boolean(leftOpen) || Boolean(rightOpen));
      backdrop.hidden = !showBackdrop;
      backdrop.classList.toggle("is-open", showBackdrop);
      backdrop.classList.toggle("is-closed", !showBackdrop);
      backdrop.setAttribute("aria-hidden", showBackdrop ? "false" : "true");
    }

    setBodyFlags({ leftOpen, rightOpen, mobile });
    updateToggleState({ leftOpen, rightOpen, mobile });
  }

  function updateToggleState({ leftOpen, rightOpen, mobile = isMobilePanel() } = {}) {
    for (const btn of getLeftToggleButtons()) {
      btn.setAttribute("aria-expanded", leftOpen ? "true" : "false");
      btn.classList.toggle("is-active", Boolean(leftOpen));
      btn.dataset.panelMode = mobile ? "mobile" : "desktop";
    }

    for (const btn of getRightToggleButtons()) {
      btn.setAttribute("aria-expanded", rightOpen ? "true" : "false");
      btn.classList.toggle("is-active", Boolean(rightOpen));
      btn.dataset.panelMode = mobile ? "mobile" : "desktop";
    }
  }

  function getDesktopSidebarDefault() {
    return readBool(STORAGE.sidebarOpen, true);
  }

  function getDesktopMemoryDefault() {
    return readBool(STORAGE.memoryOpen, true);
  }

  function getCurrentState() {
    const body = document.body;

    return {
      mobile: isMobilePanel(),
      leftOpen:
        body.classList.contains("left-panel-open") ||
        body.classList.contains("mobile-left-open"),
      rightOpen:
        body.classList.contains("right-panel-open") ||
        body.classList.contains("mobile-right-open"),
    };
  }

  function openLeftDesktop() {
    writeBool(STORAGE.sidebarOpen, true);
    applyPanelState({
      leftOpen: true,
      rightOpen: getCurrentState().rightOpen || getDesktopMemoryDefault(),
      mobile: false,
    });
  }

  function closeLeftDesktop() {
    writeBool(STORAGE.sidebarOpen, false);
    applyPanelState({
      leftOpen: false,
      rightOpen: getCurrentState().rightOpen,
      mobile: false,
    });
  }

  function openRightDesktop() {
    writeBool(STORAGE.memoryOpen, true);
    applyPanelState({
      leftOpen: getCurrentState().leftOpen || getDesktopSidebarDefault(),
      rightOpen: true,
      mobile: false,
    });
  }

  function closeRightDesktop() {
    writeBool(STORAGE.memoryOpen, false);
    applyPanelState({
      leftOpen: getCurrentState().leftOpen,
      rightOpen: false,
      mobile: false,
    });
  }

  function openLeftMobile() {
    applyPanelState({
      leftOpen: true,
      rightOpen: false,
      mobile: true,
    });
  }

  function openRightMobile() {
    applyPanelState({
      leftOpen: false,
      rightOpen: true,
      mobile: true,
    });
  }

  function closeMobilePanels() {
    applyPanelState({
      leftOpen: false,
      rightOpen: false,
      mobile: true,
    });
  }

  function toggleLeftPanel() {
    const current = getCurrentState();

    if (isMobilePanel()) {
      if (current.leftOpen) {
        closeMobilePanels();
      } else {
        openLeftMobile();
      }
      return;
    }

    if (current.leftOpen) {
      closeLeftDesktop();
    } else {
      openLeftDesktop();
    }
  }

  function toggleRightPanel() {
    const current = getCurrentState();

    if (isMobilePanel()) {
      if (current.rightOpen) {
        closeMobilePanels();
      } else {
        openRightMobile();
      }
      return;
    }

    if (current.rightOpen) {
      closeRightDesktop();
    } else {
      openRightDesktop();
    }
  }

  function ensureDesktopMemoryOpen() {
    if (isMobilePanel()) return;
    openRightDesktop();
  }

  function ensureDesktopSidebarOpen() {
    if (isMobilePanel()) return;
    openLeftDesktop();
  }

  function restorePanelState() {
    const mobile = isMobilePanel();

    if (mobile) {
      applyPanelState({
        leftOpen: false,
        rightOpen: false,
        mobile: true,
      });
      return;
    }

    applyPanelState({
      leftOpen: getDesktopSidebarDefault(),
      rightOpen: getDesktopMemoryDefault(),
      mobile: false,
    });
  }

  function handleResize() {
    const mobile = isMobilePanel();
    const current = getCurrentState();

    if (mobile) {
      applyPanelState({
        leftOpen: current.leftOpen && !current.rightOpen,
        rightOpen: current.rightOpen,
        mobile: true,
      });
      return;
    }

    applyPanelState({
      leftOpen: readBool(STORAGE.sidebarOpen, current.leftOpen || true),
      rightOpen: readBool(STORAGE.memoryOpen, current.rightOpen || true),
      mobile: false,
    });
  }

  function initPanelFix() {
    restorePanelState();
    bindPanelEvents();
    setStatus("Ready");
  }

  function bindPanelEvents() {
    if (!document.body.dataset.novaPanelsBound) {
      document.body.dataset.novaPanelsBound = "true";

      for (const btn of getLeftToggleButtons()) {
        btn.addEventListener("click", (event) => {
          event.preventDefault();
          toggleLeftPanel();
        });
      }

      for (const btn of getRightToggleButtons()) {
        btn.addEventListener("click", (event) => {
          event.preventDefault();
          toggleRightPanel();
        });
      }

      const backdrop = getBackdrop();
      if (backdrop) {
        backdrop.addEventListener("click", () => {
          closeMobilePanels();
        });
      }

      for (const btn of getCloseButtons()) {
        if (btn.dataset.novaPanelsCloseBound === "true") continue;
        btn.dataset.novaPanelsCloseBound = "true";

        btn.addEventListener("click", (event) => {
          event.preventDefault();

          if (btn.hasAttribute("data-close-left-panel")) {
            if (isMobilePanel()) closeMobilePanels();
            else closeLeftDesktop();
            return;
          }

          if (btn.hasAttribute("data-close-right-panel")) {
            if (isMobilePanel()) closeMobilePanels();
            else closeRightDesktop();
            return;
          }

          closeMobilePanels();
        });
      }

      document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;

        if (isMobilePanel()) {
          closeMobilePanels();
        }
      });

      let resizeTimer = null;
      window.addEventListener("resize", () => {
        window.clearTimeout(resizeTimer);
        resizeTimer = window.setTimeout(() => {
          handleResize();
        }, 80);
      });
    }

    updateToggleState(getCurrentState());
  }

  Nova.panels = {
    ...Nova.panels,
    isMobilePanel,
    restorePanelState,
    initPanelFix,
    bindPanelEvents,
    toggleLeftPanel,
    toggleRightPanel,
    openLeftMobile,
    openRightMobile,
    closeMobilePanels,
    ensureDesktopMemoryOpen,
    ensureDesktopSidebarOpen,
    openLeftDesktop,
    closeLeftDesktop,
    openRightDesktop,
    closeRightDesktop,
    applyPanelState,
    handleResize,
  };
})();