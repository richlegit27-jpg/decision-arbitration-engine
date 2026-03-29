// notepad C:\Users\Owner\nova\static\js\nova-panels.js
(function () {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.panels = Nova.panels || {};
  Nova.state = Nova.state || {};

  const state = Object.assign(
    {
      sidebarOpen: true,
      railOpen: true,
      activeRailPanel: "memory",
      bootedPanels: false,
    },
    Nova.state || {}
  );

  Nova.state = state;

  const els = {};

  function qs(id) {
    return document.getElementById(id);
  }

  function on(el, eventName, handler) {
    if (!el) return;
    el.addEventListener(eventName, handler);
  }

  function bindDom() {
    els.appShell = qs("novaAppShell");
    els.sidebar = qs("novaSidebar");
    els.main = qs("novaMain");
    els.rightRail = qs("novaRightRail");

    els.sidebarToggle = qs("sidebarToggle");
    els.mobileSidebarToggle = qs("mobileSidebarToggle");

    els.memoryPanelToggle = qs("memoryPanelToggle");
    els.artifactsPanelToggle = qs("artifactsPanelToggle");

    els.memoryPanel = qs("memoryPanel");
    els.artifactsPanel = qs("novaArtifactsRoot");
    els.webDebugPanel = qs("novaWebDebugPanel");

    els.memoryCloseBtn = qs("memoryCloseBtn");
    els.artifactsCloseBtn = qs("artifactsCloseBtn");
    els.artifactViewerCloseBtn = qs("artifactViewerCloseBtn");
  }

  function isMobile() {
    return window.matchMedia("(max-width: 980px)").matches;
  }

  function applySidebarState() {
    if (!els.appShell || !els.sidebar) return;

    if (state.sidebarOpen) {
      els.appShell.classList.add("sidebar-open");
      els.appShell.classList.remove("sidebar-closed");
    } else {
      els.appShell.classList.remove("sidebar-open");
      els.appShell.classList.add("sidebar-closed");
    }
  }

  function hideAllRailPanels() {
    if (els.memoryPanel) els.memoryPanel.classList.remove("is-active");
    if (els.artifactsPanel) els.artifactsPanel.classList.remove("is-active");
    if (els.webDebugPanel) els.webDebugPanel.classList.remove("is-active");
  }

  function applyActiveRailPanel() {
    hideAllRailPanels();

    if (state.activeRailPanel === "artifacts") {
      if (els.artifactsPanel) els.artifactsPanel.classList.add("is-active");
      return;
    }

    if (state.activeRailPanel === "web") {
      if (els.webDebugPanel) els.webDebugPanel.classList.add("is-active");
      return;
    }

    if (els.memoryPanel) els.memoryPanel.classList.add("is-active");
  }

  function applyRailState() {
    if (!els.appShell || !els.rightRail) return;

    applyActiveRailPanel();

    if (state.railOpen) {
      els.appShell.classList.add("rail-open");
      els.appShell.classList.remove("rail-closed");
    } else {
      els.appShell.classList.remove("rail-open");
      els.appShell.classList.add("rail-closed");
    }
  }

  function setSidebarOpen(open) {
    state.sidebarOpen = !!open;
    applySidebarState();
  }

  function setRailOpen(open, panelName) {
    if (panelName) {
      state.activeRailPanel = panelName;
    }

    state.railOpen = !!open;
    applyRailState();
  }

  function toggleSidebar() {
    setSidebarOpen(!state.sidebarOpen);
  }

  function openSidebar() {
    setSidebarOpen(true);
  }

  function closeSidebar() {
    setSidebarOpen(false);
  }

  function openMemoryPanel() {
    state.activeRailPanel = "memory";
    setRailOpen(true, "memory");
  }

  function openArtifactsPanel() {
    state.activeRailPanel = "artifacts";
    setRailOpen(true, "artifacts");
  }

  function openWebPanel() {
    state.activeRailPanel = "web";
    setRailOpen(true, "web");
  }

  function closeRail() {
    setRailOpen(false);
  }

  function toggleMemoryPanel() {
    if (state.railOpen && state.activeRailPanel === "memory") {
      closeRail();
      return;
    }
    openMemoryPanel();
  }

  function toggleArtifactsPanel() {
    if (state.railOpen && state.activeRailPanel === "artifacts") {
      closeRail();
      return;
    }
    openArtifactsPanel();
  }

  function closeArtifactViewer() {
    const viewer = qs("novaArtifactViewer");
    const detail = qs("novaArtifactDetail");

    if (viewer) {
      viewer.hidden = true;
      viewer.setAttribute("data-open", "false");
    }

    if (detail) {
      detail.hidden = true;
    }
  }

  function handleOutsideClick(event) {
    if (!isMobile()) return;
    if (!els.appShell) return;

    const target = event.target;

    const insideSidebar =
      !!target.closest("#novaSidebar") ||
      !!target.closest("#sidebarToggle") ||
      !!target.closest("#mobileSidebarToggle");

    const insideRail =
      !!target.closest("#novaRightRail") ||
      !!target.closest("#memoryPanelToggle") ||
      !!target.closest("#artifactsPanelToggle");

    if (state.sidebarOpen && !insideSidebar) {
      closeSidebar();
    }

    if (state.railOpen && !insideRail) {
      closeRail();
    }
  }

  function handleResize() {
    applySidebarState();
    applyRailState();
  }

  function wireDom() {
    on(els.sidebarToggle, "click", function (event) {
      event.preventDefault();
      toggleSidebar();
    });

    on(els.mobileSidebarToggle, "click", function (event) {
      event.preventDefault();
      toggleSidebar();
    });

    on(els.memoryPanelToggle, "click", function (event) {
      event.preventDefault();
      toggleMemoryPanel();
    });

    on(els.artifactsPanelToggle, "click", function (event) {
      event.preventDefault();
      toggleArtifactsPanel();
    });

    on(els.memoryCloseBtn, "click", function (event) {
      event.preventDefault();
      closeRail();
    });

    on(els.artifactsCloseBtn, "click", function (event) {
      event.preventDefault();
      closeRail();
    });

    on(els.artifactViewerCloseBtn, "click", function (event) {
      event.preventDefault();
      closeArtifactViewer();
    });

    document.addEventListener("click", handleOutsideClick);
    window.addEventListener("resize", handleResize);

    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;

      if (state.railOpen) {
        closeRail();
      } else if (state.sidebarOpen && isMobile()) {
        closeSidebar();
      }

      closeArtifactViewer();
    });
  }

  function exposeApi() {
    Nova.panels.setSidebarOpen = setSidebarOpen;
    Nova.panels.setRailOpen = setRailOpen;
    Nova.panels.toggleSidebar = toggleSidebar;
    Nova.panels.openSidebar = openSidebar;
    Nova.panels.closeSidebar = closeSidebar;
    Nova.panels.openMemoryPanel = openMemoryPanel;
    Nova.panels.openArtifactsPanel = openArtifactsPanel;
    Nova.panels.openWebPanel = openWebPanel;
    Nova.panels.closeRail = closeRail;
    Nova.panels.toggleMemoryPanel = toggleMemoryPanel;
    Nova.panels.toggleArtifactsPanel = toggleArtifactsPanel;
    Nova.panels.closeArtifactViewer = closeArtifactViewer;
  }

  function bootstrap() {
    if (state.bootedPanels) return;
    state.bootedPanels = true;

    bindDom();
    wireDom();
    exposeApi();

    applySidebarState();
    applyRailState();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
  } else {
    bootstrap();
  }
})();