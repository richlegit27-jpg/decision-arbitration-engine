/* notepad C:\Users\Owner\nova\static\js\ui-hotfix.js */

(() => {
"use strict";

if (window.__novaUiHotfixLoaded) {
  console.warn("Nova UI hotfix already loaded.");
  return;
}
window.__novaUiHotfixLoaded = true;

let isBound = false;

function getApp() {
  return window.NovaApp || null;
}

function getBody() {
  return document.body;
}

function getSidebar() {
  return document.getElementById("sidebar");
}

function getSidebarToggleBtn() {
  return document.getElementById("sidebarToggleBtn");
}

function getSidebarCloseBtn() {
  return document.getElementById("btnCloseSidebar");
}

function isMobileWidth() {
  return window.innerWidth <= 820;
}

function openSidebar() {
  const app = getApp();
  const body = getBody();
  if (!body) return;

  if (isMobileWidth()) {
    body.classList.add("sidebar-open");
    body.classList.remove("sidebar-collapsed");
    if (app?.state?.sidebar) {
      app.state.sidebar.isOpen = true;
    }
    return;
  }

  body.classList.remove("sidebar-collapsed");
  body.classList.remove("sidebar-open");
  if (app?.state?.sidebar) {
    app.state.sidebar.isOpen = true;
  }
}

function closeSidebar() {
  const app = getApp();
  const body = getBody();
  if (!body) return;

  if (isMobileWidth()) {
    body.classList.remove("sidebar-open");
    if (app?.state?.sidebar) {
      app.state.sidebar.isOpen = false;
    }
    return;
  }

  body.classList.add("sidebar-collapsed");
  if (app?.state?.sidebar) {
    app.state.sidebar.isOpen = false;
  }
}

function toggleSidebar() {
  const body = getBody();
  if (!body) return;

  if (isMobileWidth()) {
    if (body.classList.contains("sidebar-open")) {
      closeSidebar();
    } else {
      openSidebar();
    }
    return;
  }

  if (body.classList.contains("sidebar-collapsed")) {
    openSidebar();
  } else {
    closeSidebar();
  }
}

function handleSidebarToggleClick(event) {
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();
  toggleSidebar();
}

function handleSidebarCloseClick(event) {
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();
  closeSidebar();
}

function handleDocumentClick(event) {
  if (!isMobileWidth()) return;

  const body = getBody();
  const sidebar = getSidebar();
  const toggleBtn = getSidebarToggleBtn();

  if (!body || !sidebar || !body.classList.contains("sidebar-open")) {
    return;
  }

  const target = event.target;
  if (!(target instanceof Element)) return;

  const clickedInsideSidebar = sidebar.contains(target);
  const clickedToggle = toggleBtn ? toggleBtn.contains(target) : false;

  if (!clickedInsideSidebar && !clickedToggle) {
    closeSidebar();
  }
}

function handleResize() {
  const body = getBody();
  if (!body) return;

  if (isMobileWidth()) {
    body.classList.remove("sidebar-collapsed");
    body.classList.remove("sidebar-open");
    return;
  }

  body.classList.remove("sidebar-open");
}

function bindSidebarControls() {
  if (isBound) return;
  isBound = true;

  const toggleBtn = getSidebarToggleBtn();
  const closeBtn = getSidebarCloseBtn();

  if (toggleBtn) {
    toggleBtn.addEventListener("click", handleSidebarToggleClick, true);
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", handleSidebarCloseClick, true);
  }

  document.addEventListener("click", handleDocumentClick);
  window.addEventListener("resize", handleResize);
}

function init() {
  bindSidebarControls();
  handleResize();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init, { once: true });
} else {
  init();
}

window.addEventListener("nova:controls-ready", init, { once: true });

})();