(() => {
"use strict";

if (window.__novaOpenCloseLoaded) {
  console.warn("Nova open/close already loaded.");
  return;
}
window.__novaOpenCloseLoaded = true;

window.NovaApp = window.NovaApp || {};
const app = window.NovaApp;

function byId(id) {
  return document.getElementById(id);
}

function getSidebar() {
  return app.el?.sidebar || byId("sidebar");
}

function getSidebarToggleBtn() {
  return app.el?.sidebarToggleBtn || byId("sidebarToggleBtn");
}

function getSidebarCloseBtn() {
  return app.el?.sidebarCloseBtn || byId("sidebarCloseBtn") || byId("btnCloseSidebar");
}

function getMemoryPanel() {
  return app.el?.memoryPanel || byId("memoryPanel");
}

function getMemoryOpenBtn() {
  return app.el?.memoryOpenBtn || byId("memoryOpenBtn") || byId("memoryBtn");
}

function getMemoryCloseBtn() {
  return app.el?.memoryCloseBtn || byId("memoryCloseBtn") || byId("btnCloseMemory");
}

function getSidebarBackdrop() {
  return byId("sidebarBackdrop");
}

function getMemoryBackdrop() {
  return byId("memoryBackdrop");
}

function ensureUiState() {
  if (!app.state) {
    app.state = {};
  }

  if (!app.state.ui) {
    app.state.ui = {
      sidebarOpen: false,
      memoryOpen: false
    };
  }

  return app.state.ui;
}

function emit(name, detail = {}) {
  document.dispatchEvent(new CustomEvent(name, { detail }));
}

function syncBodyState() {
  const body = document.body;
  const uiState = ensureUiState();

  if (!body) return;

  body.classList.toggle("sidebar-open", Boolean(uiState.sidebarOpen));
  body.classList.toggle("memory-open", Boolean(uiState.memoryOpen));
  body.classList.toggle("overlay-open", Boolean(uiState.sidebarOpen || uiState.memoryOpen));
}

function syncSidebarState() {
  const sidebar = getSidebar();
  const toggleBtn = getSidebarToggleBtn();
  const closeBtn = getSidebarCloseBtn();
  const backdrop = getSidebarBackdrop();
  const uiState = ensureUiState();
  const isOpen = Boolean(uiState.sidebarOpen);

  if (sidebar) {
    sidebar.classList.toggle("is-open", isOpen);
    sidebar.setAttribute("aria-hidden", isOpen ? "false" : "true");
  }

  if (toggleBtn) {
    toggleBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    toggleBtn.setAttribute("aria-pressed", isOpen ? "true" : "false");
    toggleBtn.title = isOpen ? "Close sidebar" : "Open sidebar";
  }

  if (closeBtn) {
    closeBtn.setAttribute("aria-label", "Close sidebar");
  }

  if (backdrop) {
    backdrop.hidden = !isOpen;
    backdrop.classList.toggle("is-visible", isOpen);
  }
}

function syncMemoryState() {
  const panel = getMemoryPanel();
  const openBtn = getMemoryOpenBtn();
  const closeBtn = getMemoryCloseBtn();
  const backdrop = getMemoryBackdrop();
  const uiState = ensureUiState();
  const isOpen = Boolean(uiState.memoryOpen);

  if (panel) {
    panel.classList.toggle("is-open", isOpen);
    panel.style.display = isOpen ? "" : "none";
    panel.setAttribute("aria-hidden", isOpen ? "false" : "true");
  }

  if (openBtn) {
    openBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    openBtn.setAttribute("aria-pressed", isOpen ? "true" : "false");
    openBtn.title = isOpen ? "Close memory panel" : "Open memory panel";
  }

  if (closeBtn) {
    closeBtn.setAttribute("aria-label", "Close memory panel");
  }

  if (backdrop) {
    backdrop.hidden = !isOpen;
    backdrop.classList.toggle("is-visible", isOpen);
  }
}

function syncAllOpenCloseState() {
  syncBodyState();
  syncSidebarState();
  syncMemoryState();
}

function openSidebar() {
  const uiState = ensureUiState();
  uiState.sidebarOpen = true;
  syncAllOpenCloseState();
  emit("nova:sidebar-opened");
}

function closeSidebar() {
  const uiState = ensureUiState();
  uiState.sidebarOpen = false;
  syncAllOpenCloseState();
  emit("nova:sidebar-closed");
}

function toggleSidebar() {
  const uiState = ensureUiState();

  if (uiState.sidebarOpen) {
    closeSidebar();
    return;
  }

  openSidebar();
}

function openMemoryPanel() {
  const uiState = ensureUiState();
  uiState.memoryOpen = true;
  syncAllOpenCloseState();
  emit("nova:memory-opened");
}

function closeMemoryPanel() {
  const uiState = ensureUiState();
  uiState.memoryOpen = false;
  syncAllOpenCloseState();
  emit("nova:memory-closed");
}

function toggleMemoryPanel() {
  const uiState = ensureUiState();

  if (uiState.memoryOpen) {
    closeMemoryPanel();
    return;
  }

  openMemoryPanel();
}

function closeAllPanels() {
  const uiState = ensureUiState();
  uiState.sidebarOpen = false;
  uiState.memoryOpen = false;
  syncAllOpenCloseState();
  emit("nova:panels-closed");
}

function onEscapeKey(event) {
  if (event.key !== "Escape") return;

  const uiState = ensureUiState();
  if (!uiState.sidebarOpen && !uiState.memoryOpen) return;

  closeAllPanels();
}

function bindSidebarEvents() {
  const toggleBtn = getSidebarToggleBtn();
  const closeBtn = getSidebarCloseBtn();
  const backdrop = getSidebarBackdrop();

  if (toggleBtn && !toggleBtn.dataset.openCloseBound) {
    toggleBtn.dataset.openCloseBound = "true";
    toggleBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleSidebar();
    });
  }

  if (closeBtn && !closeBtn.dataset.openCloseBound) {
    closeBtn.dataset.openCloseBound = "true";
    closeBtn.addEventListener("click", (event) => {
      event.preventDefault();
      closeSidebar();
    });
  }

  if (backdrop && !backdrop.dataset.openCloseBound) {
    backdrop.dataset.openCloseBound = "true";
    backdrop.addEventListener("click", closeSidebar);
  }
}

function bindMemoryEvents() {
  const openBtn = getMemoryOpenBtn();
  const closeBtn = getMemoryCloseBtn();
  const backdrop = getMemoryBackdrop();

  if (openBtn && !openBtn.dataset.openCloseBound) {
    openBtn.dataset.openCloseBound = "true";
    openBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleMemoryPanel();
    });
  }

  if (closeBtn && !closeBtn.dataset.openCloseBound) {
    closeBtn.dataset.openCloseBound = "true";
    closeBtn.addEventListener("click", (event) => {
      event.preventDefault();
      closeMemoryPanel();
    });
  }

  if (backdrop && !backdrop.dataset.openCloseBound) {
    backdrop.dataset.openCloseBound = "true";
    backdrop.addEventListener("click", closeMemoryPanel);
  }
}

function bindGlobalEvents() {
  if (!document.body?.dataset.novaEscapeBound) {
    document.body.dataset.novaEscapeBound = "true";
    document.addEventListener("keydown", onEscapeKey);
  }
}

function initOpenClose() {
  ensureUiState();
  bindSidebarEvents();
  bindMemoryEvents();
  bindGlobalEvents();
  syncAllOpenCloseState();
}

app.openClose = {
  initOpenClose,
  openSidebar,
  closeSidebar,
  toggleSidebar,
  openMemoryPanel,
  closeMemoryPanel,
  toggleMemoryPanel,
  closeAllPanels,
  syncAllOpenCloseState
};

app.openSidebar = openSidebar;
app.closeSidebar = closeSidebar;
app.toggleSidebar = toggleSidebar;
app.openMemoryPanel = openMemoryPanel;
app.closeMemoryPanel = closeMemoryPanel;
app.toggleMemoryPanel = toggleMemoryPanel;
app.closeAllPanels = closeAllPanels;

document.addEventListener("DOMContentLoaded", initOpenClose);
})();