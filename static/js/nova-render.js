(() => {
  "use strict";

  if (window.__novaRenderLoaded) return;
  window.__novaRenderLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.render = Nova.render || {};

  const byId = (id) => document.getElementById(id);

  function safeCall(fn, ...args) {
    try {
      if (typeof fn === "function") {
        return fn(...args);
      }
    } catch (error) {
      console.error("Nova render safeCall error:", error);
    }
    return null;
  }

  function getPanelsApi() {
    return Nova.panels && typeof Nova.panels === "object" ? Nova.panels : null;
  }

  function getSessionsApi() {
    return Nova.sessions && typeof Nova.sessions === "object" ? Nova.sessions : null;
  }

  function getMessagesApi() {
    return Nova.messages && typeof Nova.messages === "object" ? Nova.messages : null;
  }

  function getMemoryApi() {
    return Nova.memory && typeof Nova.memory === "object" ? Nova.memory : null;
  }

  function getChatApi() {
    return Nova.chat && typeof Nova.chat === "object" ? Nova.chat : null;
  }

  function ensureCoreDom() {
    const requiredIds = [
      "novaApp",
      "leftSidebar",
      "memoryPanel",
      "toggleSidebarBtn",
      "toggleMemoryBtn",
      "chatMessages",
      "composerInput",
      "sendBtn"
    ];

    const missing = requiredIds.filter((id) => !byId(id));
    if (missing.length) {
      console.warn("Nova render: missing DOM nodes:", missing);
      return false;
    }
    return true;
  }

  function bindSendButton() {
    const sendBtn = byId("sendBtn");
    const composerInput = byId("composerInput");
    if (!sendBtn || sendBtn.__novaBoundSend) return;

    sendBtn.__novaBoundSend = true;
    sendBtn.addEventListener("click", async (event) => {
      event.preventDefault();

      const chat = getChatApi();
      if (chat && typeof chat.sendMessage === "function") {
        await safeCall(chat.sendMessage);
        return;
      }

      const value = composerInput ? String(composerInput.value || "").trim() : "";
      if (!value) return;

      console.warn("Nova render: sendMessage() not available.");
    });
  }

  function bindComposerEnter() {
    const composerInput = byId("composerInput");
    if (!composerInput || composerInput.__novaBoundEnter) return;

    composerInput.__novaBoundEnter = true;
    composerInput.addEventListener("keydown", async (event) => {
      if (event.key !== "Enter" || event.shiftKey) return;

      event.preventDefault();

      const chat = getChatApi();
      if (chat && typeof chat.sendMessage === "function") {
        await safeCall(chat.sendMessage);
      }
    });
  }

  function hydratePanelsOnlyOnce() {
    const panels = getPanelsApi();
    if (!panels) {
      console.warn("Nova render: panels API missing.");
      return;
    }

    safeCall(panels.bootstrap);

    /* CRITICAL:
       render.js must NEVER force panel open/close state here.
       No class rewrites.
       No aria rewrites.
       No mobile overrides.
       panels.js owns all of that.
    */
  }

  async function refreshSessions() {
    const sessions = getSessionsApi();
    if (!sessions) return;

    if (typeof sessions.refresh === "function") {
      await safeCall(sessions.refresh);
      return;
    }

    if (typeof sessions.load === "function") {
      await safeCall(sessions.load);
      return;
    }

    if (typeof sessions.render === "function") {
      await safeCall(sessions.render);
    }
  }

  async function refreshMemory() {
    const memory = getMemoryApi();
    if (!memory) return;

    if (typeof memory.refresh === "function") {
      await safeCall(memory.refresh);
      return;
    }

    if (typeof memory.load === "function") {
      await safeCall(memory.load);
      return;
    }

    if (typeof memory.render === "function") {
      await safeCall(memory.render);
    }
  }

  async function refreshMessages() {
    const messages = getMessagesApi();
    if (!messages) return;

    if (typeof messages.refresh === "function") {
      await safeCall(messages.refresh);
      return;
    }

    if (typeof messages.render === "function") {
      await safeCall(messages.render);
    }
  }

  async function bootstrapModules() {
    hydratePanelsOnlyOnce();
    bindSendButton();
    bindComposerEnter();

    await refreshSessions();
    await refreshMemory();
    await refreshMessages();

    const chat = getChatApi();
    if (chat && typeof chat.bootstrap === "function") {
      await safeCall(chat.bootstrap);
    }
  }

  function exposeHelpers() {
    Nova.render.bootstrap = bootstrap;
    Nova.render.refreshSessions = refreshSessions;
    Nova.render.refreshMemory = refreshMemory;
    Nova.render.refreshMessages = refreshMessages;
  }

  async function bootstrap() {
    if (!ensureCoreDom()) {
      console.warn("Nova render: core DOM not ready.");
      return false;
    }

    exposeHelpers();
    await bootstrapModules();

    document.body.classList.add("nova-ready");
    return true;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      bootstrap().catch((error) => {
        console.error("Nova render bootstrap failed:", error);
      });
    }, { once: true });
  } else {
    bootstrap().catch((error) => {
      console.error("Nova render bootstrap failed:", error);
    });
  }
})();