// C:\Users\Owner\nova\static\js\nova-dom.js

(() => {
  "use strict";

  window.Nova = window.Nova || {};

  if (window.Nova.domModuleLoaded) {
    console.warn("nova-dom.js already loaded");
    return;
  }
  window.Nova.domModuleLoaded = true;

  function byId(id) {
    return document.getElementById(id);
  }

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function createEl(tag, className = "", text = "") {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined && text !== null && text !== "") {
      el.textContent = String(text);
    }
    return el;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatTimestamp(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleString();
  }

  function isVisible(el) {
    return !!(el && !el.hidden);
  }

  function show(el) {
    if (el) el.hidden = false;
  }

  function hide(el) {
    if (el) el.hidden = true;
  }

  function toggleHidden(el, shouldHide) {
    if (!el) return;
    el.hidden = !!shouldHide;
  }

  function setText(el, value = "") {
    if (el) el.textContent = String(value ?? "");
  }

  function setHtml(el, value = "") {
    if (el) el.innerHTML = String(value ?? "");
  }

  function toggleClass(el, className, force) {
    if (!el) return;
    if (typeof force === "boolean") {
      el.classList.toggle(className, force);
    } else {
      el.classList.toggle(className);
    }
  }

  function getRefs() {
    return {
      body: document.body,
      html: document.documentElement,

      appRoot: byId("novaApp") || byId("app") || byId("mobileApp"),

      sidebar: byId("sidebar") || byId("leftPanel") || byId("mobileSidebar"),
      sidebarToggle: byId("sidebarToggle") || byId("leftPanelToggle"),
      sidebarClose: byId("sidebarClose"),

      memoryPanel: byId("memoryPanel") || byId("rightPanel"),
      memoryToggle: byId("memoryToggle") || byId("rightPanelToggle"),
      memoryClose: byId("memoryClose"),

      panelBackdrop: byId("panelBackdrop") || byId("sidebarBackdrop"),

      chatList: byId("chatList") || byId("messages") || byId("messageList"),
      sessionList: byId("sessionList"),
      memoryList: byId("memoryList"),
      sourcesList: byId("sourcesList") || byId("sourceList"),

      composerForm: byId("composerForm") || byId("chatForm"),
      composerInput: byId("composerInput") || byId("messageInput"),
      sendButton: byId("sendButton"),
      stopButton: byId("stopButton"),
      regenerateButton: byId("regenerateButton"),
      voiceButton: byId("voiceButton"),
      fileInput: byId("fileInput"),
      attachmentsBar: byId("attachmentsBar"),

      modelSelect: byId("modelSelect"),
      themeToggle: byId("themeToggle"),
      backgroundToggle: byId("backgroundToggle"),

      newSessionButton: byId("newSessionButton"),
      addMemoryButton: byId("addMemoryButton"),
      memorySearchInput: byId("memorySearchInput"),

      routerPanel: byId("routerPanel"),
      routerMeta: byId("routerMeta"),
      sourcePanel: byId("sourcePanel"),

      statusBar: byId("statusBar"),
      emptyState: byId("emptyState"),
    };
  }

  function refreshRefs() {
    window.Nova.refs = getRefs();
    return window.Nova.refs;
  }

  window.Nova.dom = {
    byId,
    qs,
    qsa,
    createEl,
    escapeHtml,
    formatTimestamp,
    isVisible,
    show,
    hide,
    toggleHidden,
    setText,
    setHtml,
    toggleClass,
    getRefs,
    refreshRefs,
  };

  refreshRefs();
})();