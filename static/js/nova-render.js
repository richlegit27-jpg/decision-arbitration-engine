(() => {
  "use strict";

  if (window.__novaRenderLoaded) return;
  window.__novaRenderLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.state = Nova.state || {};
  Nova.dom = Nova.dom || {};
  Nova.render = Nova.render || {};

  const state = Nova.state;
  const renderApi = Nova.render;

  const API = {
    state: "/api/state",
    stream: "/api/chat/stream",
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
    newSession: "/api/session/new",
  };

  const byId = (id) => document.getElementById(id);
  const qs = (selector, root = document) => root.querySelector(selector);
  const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  Nova.dom.byId = Nova.dom.byId || byId;
  Nova.dom.qs = Nova.dom.qs || qs;
  Nova.dom.qsa = Nova.dom.qsa || qsa;

  function safeJsonParse(text, fallback = null) {
    try {
      return JSON.parse(text);
    } catch {
      return fallback;
    }
  }

  async function apiGet(url) {
    const response = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });

    const text = await response.text();
    const data = safeJsonParse(text, { ok: response.ok, raw: text });

    if (!response.ok) {
      throw new Error(data?.error || `GET failed: ${url}`);
    }

    return data;
  }

  async function apiPost(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload || {}),
    });

    const text = await response.text();
    const data = safeJsonParse(text, { ok: response.ok, raw: text });

    if (!response.ok) {
      throw new Error(data?.error || `POST failed: ${url}`);
    }

    return data;
  }

  function getEls() {
    return {
      appShell: byId("novaAppShell"),
      sidebar: byId("novaSidebar"),
      main: byId("novaMain"),
      rightRail: byId("novaRightRail"),

      sidebarToggle: byId("sidebarToggle"),
      mobileSidebarToggle: byId("mobileSidebarToggle"),

      memoryPanel: byId("memoryPanel"),
      memoryPanelToggle: byId("memoryPanelToggle"),
      memoryCloseBtn: byId("memoryCloseBtn"),

      artifactsRoot: byId("novaArtifactsRoot"),
      artifactsPanelToggle: byId("artifactsPanelToggle"),
      artifactsCloseBtn: byId("artifactsCloseBtn"),

      artifactViewer: byId("novaArtifactViewer"),
      artifactViewerCloseBtn: byId("artifactViewerCloseBtn"),

      themeToggle: byId("themeToggle"),

      newChatBtn: byId("newChatBtn"),
      sessionList: byId("sessionList"),
      sessionTitle: byId("sessionTitle"),

      chatScroll: byId("chatScroll"),
      messages: byId("messages"),
      emptyState: byId("emptyState"),

      composerInput: byId("composerInput"),
      sendBtn: byId("sendBtn"),
      voiceBtn: byId("voiceBtn"),
      attachBtn: byId("attachBtn"),
      attachmentsBar: byId("attachmentsBar"),
    };
  }

  function ensureState() {
    if (typeof state.sidebarOpen !== "boolean") state.sidebarOpen = true;
    if (typeof state.memoryOpen !== "boolean") state.memoryOpen = true;
    if (typeof state.artifactsOpen !== "boolean") state.artifactsOpen = true;
    if (!state.currentSessionId) state.currentSessionId = "";
    if (!state.sessions || typeof state.sessions !== "object" || Array.isArray(state.sessions)) {
      state.sessions = {};
    }
    if (!Array.isArray(state.sessionList)) state.sessionList = [];
    if (!Array.isArray(state.messages)) state.messages = [];
    if (!state.theme) {
      state.theme = document.documentElement.getAttribute("data-theme") || "dark";
    }
    if (typeof state.isSending !== "boolean") state.isSending = false;
  }

  function persistUiState() {
    try {
      localStorage.setItem(
        "nova_ui_state",
        JSON.stringify({
          sidebarOpen: state.sidebarOpen,
          memoryOpen: state.memoryOpen,
          artifactsOpen: state.artifactsOpen,
          theme: state.theme,
        })
      );
    } catch {}
  }

  function restoreUiState() {
    try {
      const raw = localStorage.getItem("nova_ui_state");
      if (!raw) return;
      const saved = JSON.parse(raw);

      if (typeof saved.sidebarOpen === "boolean") state.sidebarOpen = saved.sidebarOpen;
      if (typeof saved.memoryOpen === "boolean") state.memoryOpen = saved.memoryOpen;
      if (typeof saved.artifactsOpen === "boolean") state.artifactsOpen = saved.artifactsOpen;
      if (saved.theme === "light" || saved.theme === "dark") state.theme = saved.theme;
    } catch {}
  }

  function setTheme(theme) {
    state.theme = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", state.theme);
    persistUiState();
  }

  function toggleTheme() {
    setTheme(state.theme === "light" ? "dark" : "light");
  }

  function syncRailState() {
    const { appShell, rightRail, memoryPanel, artifactsRoot } = getEls();
    const memoryVisible = !!(memoryPanel && !memoryPanel.hidden && state.memoryOpen);
    const artifactsVisible = !!(artifactsRoot && !artifactsRoot.hidden && state.artifactsOpen);
    const anyVisible = memoryVisible || artifactsVisible;

    if (rightRail) {
      rightRail.classList.toggle("is-empty", !anyVisible);
      rightRail.hidden = !anyVisible;
    }

    if (appShell) {
      appShell.classList.toggle("right-rail-collapsed", !anyVisible);
    }
  }

  function setSidebarOpen(open) {
    state.sidebarOpen = !!open;
    const { sidebar, appShell } = getEls();

    if (sidebar) {
      sidebar.classList.toggle("is-collapsed", !state.sidebarOpen);
    }

    if (appShell) {
      appShell.classList.toggle("sidebar-collapsed", !state.sidebarOpen);
    }

    persistUiState();
  }

  function toggleSidebar() {
    setSidebarOpen(!state.sidebarOpen);
  }

  function setPanelOpen(panelName, open) {
    const els = getEls();
    const isOpen = !!open;

    if (panelName === "memory") {
      state.memoryOpen = isOpen;
      if (els.memoryPanel) {
        els.memoryPanel.classList.toggle("is-active", isOpen);
        els.memoryPanel.hidden = !isOpen;
      }
    }

    if (panelName === "artifacts") {
      state.artifactsOpen = isOpen;
      if (els.artifactsRoot) {
        els.artifactsRoot.classList.toggle("is-active", isOpen);
        els.artifactsRoot.hidden = !isOpen;
      }
      if (!isOpen) {
        closeArtifactViewer();
      }
    }

    syncRailState();
    persistUiState();
  }

  function togglePanel(panelName) {
    if (panelName === "memory") {
      setPanelOpen("memory", !state.memoryOpen);
      return;
    }
    if (panelName === "artifacts") {
      setPanelOpen("artifacts", !state.artifactsOpen);
    }
  }

  function closeArtifactViewer() {
    const { artifactViewer } = getEls();
    if (!artifactViewer) return;
    artifactViewer.hidden = true;
    artifactViewer.setAttribute("data-open", "false");
  }

  function autosizeComposer() {
    const { composerInput } = getEls();
    if (!composerInput) return;
    composerInput.style.height = "auto";
    composerInput.style.height = `${Math.min(Math.max(composerInput.scrollHeight, 52), 220)}px`;
  }

  function setSessionTitle(title) {
    const { sessionTitle } = getEls();
    if (sessionTitle) {
      sessionTitle.textContent = title || "Ready";
    }
  }

  function updateEmptyState() {
    const { emptyState, messages } = getEls();
    if (!emptyState || !messages) return;
    emptyState.hidden = messages.children.length > 0;
  }

  function scrollChatToBottom(force = false) {
    const { chatScroll } = getEls();
    if (!chatScroll) return;

    const distanceFromBottom =
      chatScroll.scrollHeight - chatScroll.scrollTop - chatScroll.clientHeight;

    if (force || distanceFromBottom < 180) {
      chatScroll.scrollTop = chatScroll.scrollHeight;
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function createMessageBubble(role, content) {
    const wrap = document.createElement("div");
    wrap.className = `nova-message nova-message-${role}`;
    wrap.setAttribute(
      "data-message-id",
      `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    );

    wrap.innerHTML = `
      <div class="nova-message-inner">
        <div class="nova-message-role">${escapeHtml(role)}</div>
        <div class="nova-message-content" data-message-content>${escapeHtml(content)}</div>
        <div class="nova-message-actions">
          <button type="button" class="nova-message-action" data-action="save-artifact">Save</button>
        </div>
      </div>
    `;

    return wrap;
  }

  function renderMessages(messages) {
    const { messages: messagesEl } = getEls();
    if (!messagesEl) return;

    messagesEl.innerHTML = "";

    (messages || []).forEach((message) => {
      const role = message?.role || "assistant";
      const content = message?.content || "";
      messagesEl.appendChild(createMessageBubble(role, content));
    });

    updateEmptyState();
    scrollChatToBottom(true);

    if (Nova.artifacts?.render) {
      Nova.artifacts.render();
    }
  }

  function appendMessage(role, content) {
    const { messages } = getEls();
    if (!messages) return null;

    const node = createMessageBubble(role, content);
    messages.appendChild(node);

    updateEmptyState();
    scrollChatToBottom(true);

    return node;
  }

  function setSending(isSending) {
    state.isSending = !!isSending;
    const { sendBtn, composerInput } = getEls();

    if (sendBtn) {
      sendBtn.disabled = !!isSending;
      sendBtn.textContent = isSending ? "..." : "Send";
    }

    if (composerInput) {
      composerInput.disabled = !!isSending;
    }
  }

  function normalizeSessionsShape(response) {
    const sessionMap =
      response?.sessions && !Array.isArray(response.sessions) && typeof response.sessions === "object"
        ? response.sessions
        : {};

    const sessionList = Array.isArray(response?.session_list)
      ? response.session_list
      : Object.values(sessionMap);

    state.sessions = sessionMap;
    state.sessionList = sessionList;

    if (!state.currentSessionId) {
      const first = sessionList[0];
      if (first?.id) {
        state.currentSessionId = first.id;
      }
    }

    return { sessionMap, sessionList };
  }

  async function ensureSession() {
    if (state.currentSessionId) return state.currentSessionId;

    try {
      const response = await apiPost(API.newSession, {});
      const sessionId =
        response?.session_id ||
        response?.id ||
        response?.session?.id ||
        "";

      if (response?.session?.id) {
        state.sessions[response.session.id] =
          response.summary ||
          {
            id: response.session.id,
            title: response.session.title || "New Chat",
            created_at: response.session.created_at,
            updated_at: response.session.updated_at,
            pinned: !!response.session.pinned,
            message_count: Array.isArray(response.session.messages) ? response.session.messages.length : 0,
            preview: "",
            last_route: {},
          };

        state.sessionList = Object.values(state.sessions).sort((a, b) =>
          String(b?.updated_at || "").localeCompare(String(a?.updated_at || ""))
        );
      }

      if (sessionId) {
        state.currentSessionId = sessionId;
        state.messages = [];
        setSessionTitle("New Chat");

        window.dispatchEvent(
          new CustomEvent("nova:session-changed", {
            detail: { session_id: sessionId },
          })
        );
      }

      return state.currentSessionId;
    } catch (error) {
      console.warn("Nova ensureSession failed:", error);
      return "";
    }
  }

  async function loadState() {
    try {
      const response = await apiGet(API.state);
      normalizeSessionsShape(response);

      if (response?.preferences?.ui?.theme) {
        state.theme = response.preferences.ui.theme;
      }

      return response;
    } catch (error) {
      console.warn("Nova state load failed:", error);
      return null;
    }
  }

  function renderSessionList() {
    const { sessionList } = getEls();
    if (!sessionList) return;

    const entries = Array.isArray(state.sessionList)
      ? state.sessionList
      : Object.values(state.sessions || {});

    if (!entries.length) {
      sessionList.innerHTML = `<div class="nova-session-empty">No sessions yet</div>`;
      return;
    }

    sessionList.innerHTML = entries
      .map((session) => {
        const id = session?.id || "";
        const title =
          session?.title ||
          session?.name ||
          session?.label ||
          "Untitled Chat";

        const active = id === state.currentSessionId ? " is-active" : "";

        return `
          <button
            type="button"
            class="nova-session-item${active}"
            data-session-id="${escapeHtml(id)}"
          >
            <span class="nova-session-item-title">${escapeHtml(title)}</span>
          </button>
        `;
      })
      .join("");

    qsa("[data-session-id]", sessionList).forEach((button) => {
      if (button.dataset.boundSessionClick === "1") return;
      button.dataset.boundSessionClick = "1";

      button.addEventListener("click", async () => {
        const sessionId = button.dataset.sessionId || "";
        if (!sessionId) return;

        state.currentSessionId = sessionId;
        const session = state.sessions?.[sessionId];
        setSessionTitle(session?.title || session?.name || "Chat");
        renderSessionList();
        await loadSession(sessionId);

        window.dispatchEvent(
          new CustomEvent("nova:session-changed", {
            detail: { session_id: sessionId },
          })
        );
      });
    });
  }

  async function loadSession(sessionId) {
    if (!sessionId) {
      state.messages = [];
      renderMessages([]);
      setSessionTitle("Ready");
      return;
    }

    try {
      const response = await apiGet(API.getChat(sessionId));
      const session = response?.session || response || {};
      const title =
        session?.title ||
        session?.name ||
        state.sessions?.[sessionId]?.title ||
        "Chat";

      setSessionTitle(title);

      const messages = session?.messages || response?.messages || [];
      state.messages = Array.isArray(messages) ? messages : [];
      renderMessages(state.messages);

      if (Array.isArray(response?.artifacts) && Nova.artifacts?.merge) {
        Nova.artifacts.merge(response.artifacts);
      }
    } catch (error) {
      console.warn("Nova loadSession failed:", error);
      renderMessages(state.messages || []);
    }
  }

  async function sendMessage() {
    const { composerInput } = getEls();
    if (!composerInput || state.isSending) return;

    const content = composerInput.value.trim();
    if (!content) return;

    const sessionId = await ensureSession();
    if (!sessionId) {
      console.warn("Nova send blocked: no session");
      return;
    }

    const userPrompt = content;

    appendMessage("user", userPrompt);
    state.messages.push({ role: "user", content: userPrompt });

    composerInput.value = "";
    autosizeComposer();
    setSending(true);

    let assistantText = "";
    const assistantNode = appendMessage("assistant", "");
    const assistantContentEl = assistantNode?.querySelector("[data-message-content]");

    try {
      const response = await fetch(API.stream, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream, application/json, text/plain",
        },
        body: JSON.stringify({
          session_id: sessionId,
          content: userPrompt,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`Stream failed: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() || "";

        for (const chunk of chunks) {
          const lines = chunk.split("\n");
          let eventName = "message";
          const dataLines = [];

          for (const line of lines) {
            if (line.startsWith("event:")) {
              eventName = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataLines.push(line.slice(5).trim());
            }
          }

          const rawData = dataLines.join("\n");
          const payload = safeJsonParse(rawData, rawData);

          window.dispatchEvent(
            new CustomEvent("nova:stream-event", {
              detail: {
                event: eventName,
                payload,
              },
            })
          );

          if (eventName === "delta") {
            const delta =
              typeof payload === "string"
                ? payload
                : payload?.delta || payload?.content || payload?.text || "";

            if (delta) {
              assistantText += delta;
              if (assistantContentEl) {
                assistantContentEl.textContent = assistantText;
              }
              scrollChatToBottom();
            }
          }

          if (eventName === "done" || eventName === "final") {
            if (typeof payload === "object" && payload) {
              const finalText =
                payload?.content ||
                payload?.text ||
                payload?.message ||
                assistantText;

              if (finalText && !assistantText) {
                assistantText = String(finalText);
              }

              if (Array.isArray(payload?.artifacts) && Nova.artifacts?.merge) {
                Nova.artifacts.merge(payload.artifacts);
              }

              window.dispatchEvent(
                new CustomEvent("nova:chat-response", {
                  detail: payload,
                })
              );
            }
          }

          if (eventName === "error") {
            const message =
              typeof payload === "string"
                ? payload
                : payload?.error || "Unknown stream error";
            throw new Error(message);
          }
        }
      }

      if (assistantContentEl) {
        assistantContentEl.textContent = assistantText || "(no response)";
      }

      state.messages.push({
        role: "assistant",
        content: assistantText || "(no response)",
      });

      scrollChatToBottom(true);
      updateEmptyState();
      await loadState();
      renderSessionList();
    } catch (error) {
      console.error("Nova sendMessage failed:", error);
      if (assistantContentEl) {
        assistantContentEl.textContent = `Error: ${error.message || "send failed"}`;
      }
    } finally {
      setSending(false);
    }
  }

  function bindComposer() {
    const { composerInput, sendBtn } = getEls();

    if (composerInput && composerInput.dataset.boundComposer !== "1") {
      composerInput.dataset.boundComposer = "1";

      composerInput.addEventListener("input", () => {
        autosizeComposer();
      });

      composerInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage().catch((error) => console.error(error));
        }
      });
    }

    if (sendBtn && sendBtn.dataset.boundSend !== "1") {
      sendBtn.dataset.boundSend = "1";
      sendBtn.addEventListener("click", () => {
        sendMessage().catch((error) => console.error(error));
      });
    }
  }

  function bindShellButtons() {
    const els = getEls();

    if (els.sidebarToggle && els.sidebarToggle.dataset.boundClick !== "1") {
      els.sidebarToggle.dataset.boundClick = "1";
      els.sidebarToggle.addEventListener("click", toggleSidebar);
    }

    if (els.mobileSidebarToggle && els.mobileSidebarToggle.dataset.boundClick !== "1") {
      els.mobileSidebarToggle.dataset.boundClick = "1";
      els.mobileSidebarToggle.addEventListener("click", toggleSidebar);
    }

    if (els.memoryPanelToggle && els.memoryPanelToggle.dataset.boundClick !== "1") {
      els.memoryPanelToggle.dataset.boundClick = "1";
      els.memoryPanelToggle.addEventListener("click", () => togglePanel("memory"));
    }

    if (els.memoryCloseBtn && els.memoryCloseBtn.dataset.boundClick !== "1") {
      els.memoryCloseBtn.dataset.boundClick = "1";
      els.memoryCloseBtn.addEventListener("click", () => setPanelOpen("memory", false));
    }

    if (els.artifactsPanelToggle && els.artifactsPanelToggle.dataset.boundClick !== "1") {
      els.artifactsPanelToggle.dataset.boundClick = "1";
      els.artifactsPanelToggle.addEventListener("click", () => togglePanel("artifacts"));
    }

    if (els.artifactsCloseBtn && els.artifactsCloseBtn.dataset.boundClick !== "1") {
      els.artifactsCloseBtn.dataset.boundClick = "1";
      els.artifactsCloseBtn.addEventListener("click", () => setPanelOpen("artifacts", false));
    }

    if (els.artifactViewerCloseBtn && els.artifactViewerCloseBtn.dataset.boundClick !== "1") {
      els.artifactViewerCloseBtn.dataset.boundClick = "1";
      els.artifactViewerCloseBtn.addEventListener("click", closeArtifactViewer);
    }

    if (els.themeToggle && els.themeToggle.dataset.boundClick !== "1") {
      els.themeToggle.dataset.boundClick = "1";
      els.themeToggle.addEventListener("click", toggleTheme);
    }

    if (els.newChatBtn && els.newChatBtn.dataset.boundClick !== "1") {
      els.newChatBtn.dataset.boundClick = "1";
      els.newChatBtn.addEventListener("click", async () => {
        state.currentSessionId = "";
        state.messages = [];
        renderMessages([]);
        setSessionTitle("New Chat");
        await ensureSession();
        await loadState();
        renderSessionList();
      });
    }
  }

  function bindGlobalEvents() {
    window.addEventListener("nova:session-changed", () => {
      syncRailState();
    });
  }

  function applyUiStateToDom() {
    setTheme(state.theme);
    setSidebarOpen(state.sidebarOpen);
    setPanelOpen("memory", state.memoryOpen);
    setPanelOpen("artifacts", state.artifactsOpen);
    autosizeComposer();
    updateEmptyState();
    syncRailState();
  }

  function installPublicApi() {
    renderApi.sendMessage = sendMessage;
    renderApi.loadState = loadState;
    renderApi.loadSession = loadSession;
    renderApi.renderMessages = renderMessages;
    renderApi.appendMessage = appendMessage;
    renderApi.toggleSidebar = toggleSidebar;
    renderApi.toggleMemoryPanel = () => togglePanel("memory");
    renderApi.toggleArtifactsPanel = () => togglePanel("artifacts");
    renderApi.closeArtifactViewer = closeArtifactViewer;
    renderApi.refreshArtifacts = () => Nova.artifacts?.refresh?.();
  }

  async function bootstrap() {
    ensureState();
    restoreUiState();
    installPublicApi();
    bindShellButtons();
    bindComposer();
    bindGlobalEvents();
    applyUiStateToDom();

    await loadState();
    renderSessionList();

    if (state.currentSessionId) {
      await loadSession(state.currentSessionId);
    } else {
      state.messages = [];
      renderMessages([]);
      setSessionTitle("Ready");
    }

    if (Nova.artifacts?.refresh) {
      try {
        await Nova.artifacts.refresh();
      } catch (error) {
        console.warn("Nova artifact refresh on bootstrap failed:", error);
      }
    }

    syncRailState();
    console.log("Nova render loaded");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      bootstrap().catch((error) => {
        console.error("Nova bootstrap failed:", error);
      });
    });
  } else {
    bootstrap().catch((error) => {
      console.error("Nova bootstrap failed:", error);
    });
  }
})();