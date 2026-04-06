(function () {
  "use strict";

  const API = {
    state: "/api/state",
    chat: "/api/chat",
    sessionNew: "/api/session/new",
    sessionSwitch: "/api/session/switch",
    upload: "/api/upload",
  };

  const state = {
    sessionId: "",
    sessions: [],
    messages: [],
    artifacts: [],
    memoryItems: [],
    webItems: [],
    pendingUploads: [],
    lastResponse: null,
    debugOpen: false,
    sending: false,
    activePanel: "artifacts",
    sidebarCollapsed: false,
  };

  const els = {};

  function $(selector) {
    return document.querySelector(selector);
  }

  function $all(selector) {
    return Array.from(document.querySelectorAll(selector));
  }

  function safeJson(value) {
    try {
      return JSON.stringify(value ?? null, null, 2);
    } catch (_) {
      return String(value);
    }
  }

  function bindEls() {
    els.appShell = $("[data-app-shell]");
    els.sidebar = $("[data-sidebar]");
    els.sessionList = $("[data-session-list]");
    els.chatThread = $("[data-chat-thread]");
    els.chatInput = $("[data-chat-input]");
    els.uploadStrip = $("[data-upload-strip]");
    els.sessionTitle = $("[data-session-title]");
    els.sessionSubtitle = $("[data-session-subtitle]");
    els.routeChip = $("[data-route-chip]");
    els.memoryChip = $("[data-memory-chip]");
    els.stateChipText = $("[data-state-chip-text]");
    els.artifactList = $("[data-artifact-list]");
    els.memoryList = $("[data-memory-list]");
    els.webList = $("[data-web-list]");
    els.debugPanel = $("[data-debug-panel]");
    els.debugRoute = $("[data-debug-route]");
    els.debugMemory = $("[data-debug-memory]");
    els.debugState = $("[data-debug-state]");
    els.debugResponse = $("[data-debug-response]");
  }

  async function api(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data && data.error ? data.error : "Request failed");
    }
    return data;
  }

  function applyState(payload) {
    state.lastResponse = payload;
    state.sessionId = payload.session_id || payload.active_session_id || state.sessionId || "";
    state.sessions = Array.isArray(payload.sessions) ? payload.sessions : [];
    state.messages = Array.isArray(payload.messages) ? payload.messages : [];
    state.artifacts = Array.isArray(payload.artifacts) ? payload.artifacts : [];
    state.memoryItems = Array.isArray(payload.memory_items)
      ? payload.memory_items
      : Array.isArray(payload.memory)
        ? payload.memory
        : [];
    state.webItems = Array.isArray(payload.web_items)
      ? payload.web_items
      : Array.isArray(payload.web)
        ? payload.web
        : [];
  }

  function autosizeInput() {
    if (!els.chatInput) return;
    els.chatInput.style.height = "0px";
    const next = Math.min(Math.max(58, els.chatInput.scrollHeight), 220);
    els.chatInput.style.height = next + "px";
  }

  function renderSessions() {
    if (!els.sessionList) return;
    els.sessionList.innerHTML = "";

    state.sessions.forEach((session) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "nova-session-item";
      if ((session.id || "") === state.sessionId) {
        btn.classList.add("is-active");
      }

      const title = document.createElement("div");
      title.className = "nova-session-item-title";
      title.textContent = session.title || "New Chat";

      const meta = document.createElement("div");
      meta.className = "nova-session-item-meta";
      meta.textContent = (session.last_message_preview || `${session.message_count || 0} messages`).slice(0, 80);

      btn.appendChild(title);
      btn.appendChild(meta);

      btn.onclick = async () => {
        const payload = await api(API.sessionSwitch, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: session.id }),
        });
        applyState(payload);
        renderAll();
      };

      els.sessionList.appendChild(btn);
    });
  }

  function renderMessages() {
    if (!els.chatThread) return;
    els.chatThread.innerHTML = "";

    state.messages.forEach((msg) => {
      const wrap = document.createElement("div");
      wrap.className = "nova-message nova-message-" + (msg.role || "assistant");

      const body = document.createElement("div");
      body.className = "nova-message-body";
      body.textContent = msg.content || "";

      wrap.appendChild(body);
      els.chatThread.appendChild(wrap);
    });

    els.chatThread.scrollTop = els.chatThread.scrollHeight;
  }

  function renderArtifacts() {
    if (!els.artifactList) return;
    els.artifactList.innerHTML = "";

    if (!state.artifacts.length) {
      const empty = document.createElement("div");
      empty.className = "nova-list-empty";
      empty.textContent = "No artifacts yet.";
      els.artifactList.appendChild(empty);
      return;
    }

    state.artifacts.forEach((artifact) => {
      const item = document.createElement("div");
      item.className = "nova-list-item";

      const title = document.createElement("div");
      title.className = "nova-list-item-title";
      title.textContent = artifact.title || "Untitled";

      const meta = document.createElement("div");
      meta.className = "nova-list-item-meta";
      meta.textContent = artifact.kind || "artifact";

      item.appendChild(title);
      item.appendChild(meta);
      els.artifactList.appendChild(item);
    });
  }

  function renderMemory() {
    if (!els.memoryList) return;
    els.memoryList.innerHTML = "";

    if (!state.memoryItems.length) {
      const empty = document.createElement("div");
      empty.className = "nova-list-empty";
      empty.textContent = "No memory captured yet.";
      els.memoryList.appendChild(empty);
      return;
    }

    state.memoryItems.forEach((memory) => {
      const item = document.createElement("div");
      item.className = "nova-list-item";

      const title = document.createElement("div");
      title.className = "nova-list-item-title";
      title.textContent = memory.text || "";

      const meta = document.createElement("div");
      meta.className = "nova-list-item-meta";
      meta.textContent = memory.kind || "note";

      item.appendChild(title);
      item.appendChild(meta);
      els.memoryList.appendChild(item);
    });
  }

  function renderWeb() {
    if (!els.webList) return;
    els.webList.innerHTML = "";

    if (!state.webItems.length) {
      const empty = document.createElement("div");
      empty.className = "nova-list-empty";
      empty.textContent = "No web results yet.";
      els.webList.appendChild(empty);
      return;
    }

    state.webItems.forEach((webItem) => {
      const item = document.createElement("div");
      item.className = "nova-list-item";

      const title = document.createElement("div");
      title.className = "nova-list-item-title";
      title.textContent = webItem.title || "Web";

      const meta = document.createElement("div");
      meta.className = "nova-list-item-meta";
      meta.textContent = webItem.source_url || "";

      item.appendChild(title);
      item.appendChild(meta);
      els.webList.appendChild(item);
    });
  }

  function renderTopbar() {
    const active = state.sessions.find((s) => (s.id || "") === state.sessionId);

    if (els.sessionTitle) {
      els.sessionTitle.textContent = active ? active.title || "Nova" : "Nova";
    }

    if (els.sessionSubtitle) {
      els.sessionSubtitle.textContent = active
        ? `${state.messages.length} messages in this session`
        : "Fast local AI workspace";
    }

    if (els.routeChip) {
      const routeMeta = state.lastResponse && state.lastResponse.route_meta ? state.lastResponse.route_meta : null;
      const route = routeMeta && routeMeta.route ? routeMeta.route : "idle";
      const mode = routeMeta && routeMeta.mode ? routeMeta.mode : "ready";
      els.routeChip.textContent = `route: ${route} / ${mode}`;
    }

    if (els.memoryChip) {
      els.memoryChip.textContent = `memory: ${state.memoryItems.length}`;
    }

    if (els.stateChipText) {
      els.stateChipText.textContent = state.sending ? "Sending" : "Ready";
    }
  }

  function renderDebug() {
    if (!els.debugPanel) return;

    els.debugPanel.hidden = !state.debugOpen;

    if (els.debugRoute) {
      els.debugRoute.textContent = safeJson({
        route_meta: state.lastResponse ? state.lastResponse.route_meta : null,
        debug: state.lastResponse ? state.lastResponse.debug : null,
      });
    }

    if (els.debugMemory) {
      els.debugMemory.textContent = safeJson({
        learned_memory_items: state.lastResponse ? state.lastResponse.learned_memory_items : [],
        dominant_memory: state.lastResponse ? state.lastResponse.dominant_memory : [],
        memory_items: state.memoryItems,
      });
    }

    if (els.debugState) {
      els.debugState.textContent = safeJson({
        session_id: state.sessionId,
        sessions_count: state.sessions.length,
        messages_count: state.messages.length,
        artifacts_count: state.artifacts.length,
        web_items_count: state.webItems.length,
        active_panel: state.activePanel,
      });
    }

    if (els.debugResponse) {
      els.debugResponse.textContent = safeJson(state.lastResponse);
    }
  }

  function showPanel(name) {
    state.activePanel = name;
    $all("[data-panel]").forEach((node) => {
      node.classList.toggle("is-active", node.getAttribute("data-panel") === name);
    });
    $all("[data-panel-tab]").forEach((node) => {
      node.classList.toggle("is-active", node.getAttribute("data-panel-tab") === name);
    });
    renderDebug();
  }

  function toggleSidebar() {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    if (!els.appShell) return;
    els.appShell.classList.toggle("is-sidebar-collapsed", state.sidebarCollapsed);
  }

  function renderAll() {
    renderSessions();
    renderMessages();
    renderArtifacts();
    renderMemory();
    renderWeb();
    renderTopbar();
    renderDebug();
    autosizeInput();
  }

  async function refreshState() {
    const payload = await api(API.state);
    applyState(payload);
    renderAll();
  }

  async function sendMessage() {
    if (!els.chatInput || state.sending) return;

    const content = els.chatInput.value.trim();
    if (!content) return;

    state.sending = true;
    renderTopbar();

    try {
      const payload = await api(API.chat, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content,
          session_id: state.sessionId,
          attachments: state.pendingUploads,
        }),
      });

      els.chatInput.value = "";
      state.pendingUploads = [];
      applyState(payload);
      renderAll();
    } catch (err) {
      console.error(err);
      alert(err.message || "Send failed");
    } finally {
      state.sending = false;
      renderTopbar();
      autosizeInput();
    }
  }

  async function createNewChat() {
    const payload = await api(API.sessionNew, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    applyState(payload);
    renderAll();
  }

  function bindActions() {
    document.addEventListener("click", async (event) => {
      const trigger = event.target.closest("[data-action], [data-panel-tab]");
      if (!trigger) return;

      if (trigger.hasAttribute("data-panel-tab")) {
        event.preventDefault();
        showPanel(trigger.getAttribute("data-panel-tab"));
        return;
      }

      const action = trigger.getAttribute("data-action");

      if (action === "send") {
        event.preventDefault();
        await sendMessage();
        return;
      }

      if (action === "new-chat") {
        event.preventDefault();
        await createNewChat();
        return;
      }

      if (action === "toggle-debug") {
        event.preventDefault();
        state.debugOpen = !state.debugOpen;
        renderDebug();
        return;
      }

      if (action === "debug-refresh") {
        event.preventDefault();
        await refreshState();
        return;
      }

      if (action === "debug-copy") {
        event.preventDefault();
        const text = safeJson({
          route: state.lastResponse ? state.lastResponse.route_meta : null,
          memory: {
            learned: state.lastResponse ? state.lastResponse.learned_memory_items : [],
            dominant: state.lastResponse ? state.lastResponse.dominant_memory : [],
            items: state.memoryItems,
          },
          state: {
            session_id: state.sessionId,
            sessions: state.sessions,
            messages: state.messages,
            artifacts: state.artifacts,
            web_items: state.webItems,
          },
          response: state.lastResponse,
        });

        try {
          await navigator.clipboard.writeText(text);
        } catch (_) {
          console.warn("Clipboard copy failed");
        }
        return;
      }

      if (action === "toggle-sidebar") {
        event.preventDefault();
        toggleSidebar();
        return;
      }

      if (action === "upload") {
        event.preventDefault();
        alert("Upload wiring comes next.");
      }
    });

    if (els.chatInput) {
      els.chatInput.addEventListener("input", autosizeInput);
      els.chatInput.addEventListener("keydown", async (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          await sendMessage();
        }
      });
    }
  }

  async function boot() {
    bindEls();
    bindActions();
    showPanel("artifacts");
    await refreshState();
  }

  boot().catch((err) => {
    console.error("[NovaComposerBundle] boot failed", err);
  });
})();