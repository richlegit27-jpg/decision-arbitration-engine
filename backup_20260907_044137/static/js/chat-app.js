```javascript
// C:\Users\Owner\nova\static\js\chat-app.js

(() => {
  "use strict";

  let chatStateApi = window.NovaChatState;
  let chatStorage = window.NovaChatStorage;
  let chatSidebar = window.NovaChatSidebar;
  let chatMessages = window.NovaChatMessages;
  let composer = window.NovaComposer;
  let memoryPanel = window.NovaMemoryPanel;
  let chatOrchestratorApi = window.NovaChatOrchestrator;
  let chatBootstrapApi = window.NovaChatBootstrap;

  let state = null;
  let orchestrator = null;

  let topbarEventsBound = false;
  let appStarted = false;

  function ensureState() {
    if (state) {
      return state;
    }

    if (
      window.NovaChatState &&
      window.NovaChatState.state
    ) {
      state = window.NovaChatState.state;
    } else {
      state = {
        activeSessionId: null,
        sessions: [],
        messages: [],
        models: [],
        selectedModel: null,
        isSending: false,
        pendingAttachments: [],
        booted: false
      };
    }

    window.Nova = window.Nova || {};
    window.Nova.state = state;

    return state;
  }

  function refreshDependencies() {
    chatStateApi = window.NovaChatState;
    chatStorage = window.NovaChatStorage;
    chatSidebar = window.NovaChatSidebar;
    chatMessages = window.NovaChatMessages;
    composer = window.NovaComposer;
    memoryPanel = window.NovaMemoryPanel;
    chatOrchestratorApi = window.NovaChatOrchestrator;
    chatBootstrapApi = window.NovaChatBootstrap;

    /*
     * IMPORTANT:
     *
     * nova-composer-bridge.js owns creation of the live
     * NovaComposerActions instance.
     *
     * chat-app.js must NOT create another instance here.
     *
     * composer-actions.js publishes the factory.
     * nova-composer-bridge.js creates the live instance.
     */
    if (
      window.NovaComposerActions &&
      typeof window.NovaComposerActions.sendCurrentMessage === "function"
    ) {
      console.log(
        "[NovaChatApp] using live NovaComposerActions instance"
      );
    }
  }

  function getAttachmentsService() {
    return window.NovaAttachmentsService || null;
  }

  function getStreamService() {
    return window.NovaStreamService || null;
  }

  function getWorkspaceFilesApi() {
    return window.NovaWorkspaceFiles || null;
  }

  function ensureOrchestrator() {
    refreshDependencies();

    if (orchestrator) {
      return orchestrator;
    }

    if (!chatOrchestratorApi) {
      console.warn(
        "[NovaChatApp] orchestrator not ready"
      );

      return null;
    }

    orchestrator =
      chatOrchestratorApi.create({
        state: ensureState(),
        chatStorage,
        chatSidebar,
        chatMessages,
        composer,
        memoryPanel,
        getAttachmentsService,
        getStreamService
      });

    window.novaOrchestrator = orchestrator;

    return orchestrator;
  }

  function openWorkspaceFilesPanel() {
    const api = getWorkspaceFilesApi();

    if (
      api &&
      typeof api.open === "function"
    ) {
      api.open();
    }
  }

  function openMemoryPanel() {
    const instance = ensureOrchestrator();

    if (
      instance &&
      typeof instance.openMemoryPanel === "function"
    ) {
      instance.openMemoryPanel();
    }
  }

  function closeMemoryPanel() {
    const instance = ensureOrchestrator();

    if (
      instance &&
      typeof instance.closeMemoryPanel === "function"
    ) {
      instance.closeMemoryPanel();
    }
  }

  function refreshMemoryList() {
    const instance = ensureOrchestrator();

    if (
      instance &&
      typeof instance.refreshMemoryList === "function"
    ) {
      return instance.refreshMemoryList();
    }
  }

  function bindTopbarButtons() {
    if (topbarEventsBound) {
      return;
    }

    const workspace =
      document.getElementById(
        "btnWorkspaceFiles"
      );

    const memory =
      document.getElementById(
        "btnTopbarMemory"
      );

    workspace?.addEventListener(
      "click",
      openWorkspaceFilesPanel
    );

    memory?.addEventListener(
      "click",
      openMemoryPanel
    );

    topbarEventsBound = true;
  }

  async function init() {
    if (appStarted) {
      return;
    }

    const instance = ensureOrchestrator();

    if (!instance) {
      console.warn(
        "[NovaChatApp] waiting for orchestrator"
      );

      setTimeout(
        init,
        250
      );

      return;
    }

    appStarted = true;

    bindTopbarButtons();

    if (
      typeof instance.init === "function"
    ) {
      await instance.init();
    }
  }

  window.Nova = window.Nova || {};

  window.Nova.state = ensureState();

  window.NovaChatApp = {
    state: window.Nova.state,

    init,

    renderAll() {
      const instance = ensureOrchestrator();
      return instance?.renderAll();
    },

    loadActiveChatMessages() {
      const instance = ensureOrchestrator();
      return instance?.loadActiveChatMessages();
    },

    createChatAndLoad() {
      const instance = ensureOrchestrator();
      return instance?.createChatAndLoad();
    },

    scrollMessagesToBottom(force) {
      const instance = ensureOrchestrator();
      return instance?.scrollMessagesToBottom(force);
    },

    syncSidebarAndLayout() {
      const instance = ensureOrchestrator();
      return instance?.syncSidebarAndLayout();
    },

    openMemoryPanel,
    closeMemoryPanel,
    refreshMemoryList,
    openWorkspaceFilesPanel
  };

  console.log(
    "[NOVA SINGLE STATE]",
    window.Nova.state === window.NovaChatApp.state
  );

  function startNovaChatApp() {
    if (
      window.NovaChatBootstrap &&
      typeof window.NovaChatBootstrap.start === "function"
    ) {
      window.NovaChatBootstrap.start(init);
    } else {
      console.log(
        "[NovaChatApp] bootstrap waiting"
      );

      setTimeout(
        startNovaChatApp,
        250
      );
    }
  }

  startNovaChatApp();
})();
```
