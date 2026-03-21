(() => {
"use strict";

if (window.__novaStuckThinkingGuardLoaded) {
  console.warn("Nova stuck thinking guard already loaded.");
  return;
}
window.__novaStuckThinkingGuardLoaded = true;

window.NovaApp = window.NovaApp || {};
const app = window.NovaApp;

function byId(id) {
  return document.getElementById(id);
}

function getSendBtn() {
  return app.el?.sendBtn || byId("sendBtn");
}

function getStopBtn() {
  return app.el?.stopBtn || byId("stopBtn");
}

function getMessageInput() {
  return app.el?.messageInput || byId("messageInput");
}

function clearBusyUi() {
  const sendBtn = getSendBtn();
  const stopBtn = getStopBtn();
  const messageInput = getMessageInput();

  if (app.composer?.state) {
    app.composer.state.isSending = false;
    app.composer.state.activeController = null;
  }

  if (app.state) {
    app.state.isLoadingChat = false;
    app.state.loading = false;
    app.state.busy = false;
  }

  document.body.classList.remove("is-thinking", "is-streaming", "loading", "busy");
  document.documentElement.classList.remove("is-thinking", "is-streaming", "loading", "busy");

  document.querySelectorAll("[data-busy='1']").forEach((el) => {
    el.removeAttribute("data-busy");
  });

  document.querySelectorAll("[disabled]").forEach((el) => {
    if (
      el.id === "sendBtn" ||
      el.id === "stopBtn" ||
      el.id === "messageInput" ||
      el.hasAttribute("data-allow-manual-enable")
    ) {
      el.disabled = false;
    }
  });

  if (sendBtn) {
    sendBtn.disabled = false;
    sendBtn.style.pointerEvents = "";
    sendBtn.removeAttribute("aria-disabled");
  }

  if (stopBtn) {
    stopBtn.disabled = true;
    stopBtn.style.pointerEvents = "";
    stopBtn.removeAttribute("aria-disabled");
  }

  if (messageInput) {
    messageInput.disabled = false;
    messageInput.readOnly = false;
  }

  if (typeof app.syncComposerState === "function") {
    app.syncComposerState();
  }

  if (typeof app.renderMessages === "function") {
    app.renderMessages({ forceScroll: false });
  }

  if (typeof app.renderAll === "function") {
    app.renderAll({ forceScroll: false });
  }
}

function bindEscapeRecovery() {
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      clearBusyUi();
    }
  });
}

function bindDoubleClickRecovery() {
  const stopBtn = getStopBtn();
  if (!stopBtn || stopBtn.dataset.stuckGuardBound === "1") return;
  stopBtn.dataset.stuckGuardBound = "1";

  stopBtn.addEventListener("dblclick", () => {
    clearBusyUi();
  });
}

function init() {
  bindEscapeRecovery();
  bindDoubleClickRecovery();

  document.addEventListener("nova:force-idle", clearBusyUi);
  document.addEventListener("nova:stream-finished", clearBusyUi);
  document.addEventListener("nova:stream-error", clearBusyUi);

  setInterval(() => {
    bindDoubleClickRecovery();
  }, 1000);

  window.NovaForceIdle = clearBusyUi;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init, { once: true });
} else {
  init();
}
})();