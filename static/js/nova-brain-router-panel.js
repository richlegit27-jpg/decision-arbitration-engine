(() => {
  "use strict";

  if (window.__novaBrainRouterPanelLoaded) {
    console.warn("Nova brain router panel already loaded.");
    return;
  }
  window.__novaBrainRouterPanelLoaded = true;

  const PANEL_ID = "novaBrainRouterPanel";
  const TOGGLE_ID = "brainRouterToggleBtn";
  const STORAGE_KEY_OPEN = "nova_brain_router_open";
  const STORAGE_KEY_PIN = "nova_brain_router_pin";
  const POLL_MS = 2200;

  const state = {
    isOpen: localStorage.getItem(STORAGE_KEY_OPEN) === "1",
    isPinned: localStorage.getItem(STORAGE_KEY_PIN) === "1",
    lastHash: "",
    lastPayload: null,
    pollTimer: null
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function shortJson(value) {
    try {
      return JSON.stringify(value ?? {}, null, 2);
    } catch {
      return String(value ?? "");
    }
  }

  function safeText(value, fallback = "—") {
    if (value == null) return fallback;
    const text = String(value).trim();
    return text || fallback;
  }

  function normalizeList(value) {
    if (Array.isArray(value)) return value;
    if (value == null) return [];
    if (typeof value === "string") {
      return value
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean);
    }
    if (typeof value === "object") {
      return Object.entries(value).map(([k, v]) => `${k}: ${typeof v === "string" ? v : shortJson(v)}`);
    }
    return [String(value)];
  }

  function firstDefined(...values) {
    for (const value of values) {
      if (value !== undefined && value !== null) return value;
    }
    return null;
  }

  function routeFromMessage(message) {
    if (!message || typeof message !== "object") return null;

    const meta = firstDefined(
      message.route_meta,
      message.routeMeta,
      message.router_meta,
      message.routerMeta,
      message.meta?.route,
      message.meta?.router,
      message.metadata?.route,
      message.metadata?.router,
      message.debug?.route,
      message.debug?.router
    );

    const mode = firstDefined(
      meta?.mode,
      meta?.intent,
      meta?.route,
      meta?.selected_mode,
      meta?.selectedMode,
      message.mode,
      message.intent,
      message.route
    );

    const reasons = firstDefined(
      meta?.reasons,
      meta?.why,
      meta?.reason,
      meta?.decision_reasons,
      meta?.decisionReasons,
      meta?.notes,
      meta?.analysis
    );

    const pulledMemory = firstDefined(
      meta?.memory,
      meta?.memory_hits,
      meta?.memoryHits,
      meta?.memory_used,
      meta?.memoryUsed,
      meta?.selected_memory,
      meta?.selectedMemory,
      meta?.context,
      meta?.retrieved_context,
      meta?.retrievedContext
    );

    const model = firstDefined(
      meta?.model,
      meta?.selected_model,
      meta?.selectedModel,
      message.model
    );

    const latencyMs = firstDefined(
      meta?.latency_ms,
      meta?.latencyMs,
      meta?.duration_ms,
      meta?.durationMs,
      meta?.timing?.latency_ms,
      meta?.timing?.latencyMs
    );

    const confidence = firstDefined(
      meta?.confidence,
      meta?.score,
      meta?.route_score,
      meta?.routeScore
    );

    const promptTokens = firstDefined(
      meta?.usage?.prompt_tokens,
      meta?.usage?.promptTokens,
      meta?.prompt_tokens,
      meta?.promptTokens
    );

    const completionTokens = firstDefined(
      meta?.usage?.completion_tokens,
      meta?.usage?.completionTokens,
      meta?.completion_tokens,
      meta?.completionTokens
    );

    const totalTokens = firstDefined(
      meta?.usage?.total_tokens,
      meta?.usage?.totalTokens,
      meta?.total_tokens,
      meta?.totalTokens
    );

    if (
      mode == null &&
      reasons == null &&
      pulledMemory == null &&
      model == null &&
      latencyMs == null &&
      confidence == null &&
      meta == null
    ) {
      return null;
    }

    return {
      mode: safeText(mode),
      reasons: normalizeList(reasons),
      memory: normalizeList(pulledMemory),
      model: safeText(model),
      latencyMs: latencyMs == null ? "—" : String(latencyMs),
      confidence: confidence == null ? "—" : String(confidence),
      promptTokens: promptTokens == null ? "—" : String(promptTokens),
      completionTokens: completionTokens == null ? "—" : String(completionTokens),
      totalTokens: totalTokens == null ? "—" : String(totalTokens),
      raw: meta ?? message
    };
  }

  function findLatestAssistantRoutePayload(data) {
    if (!data) return null;

    const messageBuckets = [
      data.messages,
      data.chat,
      data.items,
      data.history,
      data.session?.messages,
      data.current_session?.messages,
      data.currentSession?.messages
    ];

    for (const bucket of messageBuckets) {
      if (!Array.isArray(bucket)) continue;
      for (let i = bucket.length - 1; i >= 0; i -= 1) {
        const message = bucket[i];
        const role = String(
          firstDefined(message?.role, message?.sender, message?.type, "")
        ).toLowerCase();

        if (role && !["assistant", "nova", "bot"].includes(role)) continue;

        const extracted = routeFromMessage(message);
        if (extracted) return extracted;
      }
    }

    const directPayloads = [
      data.route_meta,
      data.routeMeta,
      data.router_meta,
      data.routerMeta,
      data.debug?.route,
      data.debug?.router
    ];

    for (const maybe of directPayloads) {
      const extracted = routeFromMessage({ route_meta: maybe });
      if (extracted) return extracted;
    }

    return null;
  }

  function hashPayload(payload) {
    return shortJson(payload);
  }

  function ensureStyles() {
    if (document.getElementById("novaBrainRouterPanelStyles")) return;

    const style = document.createElement("style");
    style.id = "novaBrainRouterPanelStyles";
    style.textContent = `
      #${TOGGLE_ID} {
        border: 1px solid rgba(164,185,255,0.18);
        background: rgba(20, 31, 58, 0.92);
        color: #ecf2ff;
        border-radius: 12px;
        padding: 10px 14px;
        cursor: pointer;
        font: inherit;
        transition: transform .14s ease, border-color .14s ease, background .14s ease;
      }
      #${TOGGLE_ID}:hover {
        transform: translateY(-1px);
        border-color: rgba(122,156,255,0.38);
        background: rgba(28, 43, 78, 0.96);
      }
      #${PANEL_ID} {
        position: fixed;
        right: 18px;
        bottom: 18px;
        width: min(420px, calc(100vw - 20px));
        max-height: min(72vh, 760px);
        display: none;
        flex-direction: column;
        z-index: 9999;
        border-radius: 20px;
        overflow: hidden;
        border: 1px solid rgba(164,185,255,0.16);
        background: rgba(9, 15, 30, 0.97);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        box-shadow: 0 20px 70px rgba(0,0,0,.45);
        color: #ecf2ff;
      }
      #${PANEL_ID}.open {
        display: flex;
      }
      #${PANEL_ID} .nrp-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        padding: 14px 16px;
        border-bottom: 1px solid rgba(164,185,255,0.12);
        background: linear-gradient(180deg, rgba(22,33,59,0.98), rgba(12,20,38,0.98));
      }
      #${PANEL_ID} .nrp-title-wrap {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      #${PANEL_ID} .nrp-title {
        font-size: 15px;
        font-weight: 700;
        letter-spacing: .02em;
      }
      #${PANEL_ID} .nrp-subtitle {
        color: #97a8cf;
        font-size: 12px;
      }
      #${PANEL_ID} .nrp-actions {
        display: flex;
        gap: 8px;
      }
      #${PANEL_ID} .nrp-btn {
        border: 1px solid rgba(164,185,255,0.18);
        background: rgba(24, 35, 63, 0.94);
        color: #ecf2ff;
        border-radius: 10px;
        padding: 8px 10px;
        cursor: pointer;
        font: inherit;
      }
      #${PANEL_ID} .nrp-btn:hover {
        border-color: rgba(122,156,255,0.38);
        background: rgba(34, 49, 86, 0.98);
      }
      #${PANEL_ID} .nrp-body {
        padding: 14px;
        overflow: auto;
      }
      #${PANEL_ID} .nrp-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-bottom: 12px;
      }
      #${PANEL_ID} .nrp-card {
        background: rgba(19, 28, 49, 0.96);
        border: 1px solid rgba(164,185,255,0.12);
        border-radius: 14px;
        padding: 12px;
      }
      #${PANEL_ID} .nrp-label {
        font-size: 11px;
        color: #97a8cf;
        text-transform: uppercase;
        letter-spacing: .08em;
        margin-bottom: 6px;
      }
      #${PANEL_ID} .nrp-value {
        font-size: 14px;
        color: #ecf2ff;
        font-weight: 600;
        line-height: 1.35;
        word-break: break-word;
      }
      #${PANEL_ID} .nrp-section {
        margin-top: 12px;
      }
      #${PANEL_ID} .nrp-section:first-child {
        margin-top: 0;
      }
      #${PANEL_ID} .nrp-section-title {
        font-size: 12px;
        color: #97a8cf;
        text-transform: uppercase;
        letter-spacing: .08em;
        margin-bottom: 8px;
      }
      #${PANEL_ID} .nrp-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      #${PANEL_ID} .nrp-pill,
      #${PANEL_ID} .nrp-list-item {
        border: 1px solid rgba(164,185,255,0.12);
        background: rgba(20, 31, 58, 0.92);
        border-radius: 12px;
        padding: 10px 12px;
        font-size: 13px;
        line-height: 1.45;
      }
      #${PANEL_ID} pre {
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
        font-family: Consolas, "SFMono-Regular", Menlo, monospace;
        font-size: 12px;
        line-height: 1.45;
        color: #d7e3ff;
      }
      #${PANEL_ID} .nrp-empty {
        padding: 18px;
        text-align: center;
        color: #97a8cf;
        border: 1px dashed rgba(164,185,255,0.16);
        border-radius: 14px;
        background: rgba(18,27,50,0.72);
      }

      body.nova-brain-router-pinned #${PANEL_ID} {
        display: flex;
      }

      @media (max-width: 760px) {
        #${PANEL_ID} {
          left: 10px;
          right: 10px;
          bottom: 10px;
          width: auto;
          max-height: 78vh;
          border-radius: 18px;
        }
        #${PANEL_ID} .nrp-grid {
          grid-template-columns: 1fr;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function ensurePanel() {
    let panel = document.getElementById(PANEL_ID);
    if (panel) return panel;

    panel = document.createElement("aside");
    panel.id = PANEL_ID;
    panel.setAttribute("aria-label", "Brain Router Panel");
    panel.innerHTML = `
      <div class="nrp-head">
        <div class="nrp-title-wrap">
          <div class="nrp-title">Brain Router</div>
          <div class="nrp-subtitle">Nova decision trace</div>
        </div>
        <div class="nrp-actions">
          <button type="button" class="nrp-btn" data-action="refresh">Refresh</button>
          <button type="button" class="nrp-btn" data-action="pin">Pin</button>
          <button type="button" class="nrp-btn" data-action="close">Close</button>
        </div>
      </div>
      <div class="nrp-body">
        <div class="nrp-empty">Waiting for router data...</div>
      </div>
    `;
    document.body.appendChild(panel);

    panel.addEventListener("click", async (event) => {
      const btn = event.target.closest("[data-action]");
      if (!btn) return;

      const action = btn.getAttribute("data-action");
      if (action === "close") {
        setOpen(false);
      } else if (action === "pin") {
        state.isPinned = !state.isPinned;
        localStorage.setItem(STORAGE_KEY_PIN, state.isPinned ? "1" : "0");
        document.body.classList.toggle("nova-brain-router-pinned", state.isPinned);
        syncPanelUi();
      } else if (action === "refresh") {
        await refreshPanel(true);
      }
    });

    return panel;
  }

  function ensureToggleButton() {
    let btn = document.getElementById(TOGGLE_ID);
    if (btn) return btn;

    btn = document.createElement("button");
    btn.id = TOGGLE_ID;
    btn.type = "button";
    btn.textContent = "Brain";
    btn.title = "Open Brain Router Panel";

    const topbar =
      document.querySelector(".topbar-actions") ||
      document.querySelector(".topbar-right") ||
      document.querySelector(".main-topbar .topbar-controls") ||
      document.querySelector(".main-topbar") ||
      document.querySelector(".topbar");

    if (topbar) {
      topbar.appendChild(btn);
    } else {
      btn.style.position = "fixed";
      btn.style.right = "18px";
      btn.style.top = "18px";
      btn.style.zIndex = "9998";
      document.body.appendChild(btn);
    }

    btn.addEventListener("click", () => {
      setOpen(!state.isOpen);
    });

    return btn;
  }

  function setOpen(next) {
    state.isOpen = !!next;
    localStorage.setItem(STORAGE_KEY_OPEN, state.isOpen ? "1" : "0");
    syncPanelUi();
  }

  function syncPanelUi() {
    const panel = ensurePanel();
    panel.classList.toggle("open", state.isOpen || state.isPinned);
    document.body.classList.toggle("nova-brain-router-pinned", state.isPinned);

    const pinBtn = panel.querySelector('[data-action="pin"]');
    if (pinBtn) {
      pinBtn.textContent = state.isPinned ? "Unpin" : "Pin";
    }
  }

  function renderPayload(payload) {
    const panel = ensurePanel();
    const body = panel.querySelector(".nrp-body");
    if (!body) return;

    if (!payload) {
      body.innerHTML = `<div class="nrp-empty">No router metadata found yet.</div>`;
      return;
    }

    const reasons = payload.reasons.length
      ? payload.reasons.map((item) => `<div class="nrp-list-item">${escapeHtml(item)}</div>`).join("")
      : `<div class="nrp-list-item">No reasons found.</div>`;

    const memory = payload.memory.length
      ? payload.memory.map((item) => `<div class="nrp-list-item">${escapeHtml(item)}</div>`).join("")
      : `<div class="nrp-list-item">No memory pulled.</div>`;

    body.innerHTML = `
      <div class="nrp-grid">
        <div class="nrp-card">
          <div class="nrp-label">Mode</div>
          <div class="nrp-value">${escapeHtml(payload.mode)}</div>
        </div>
        <div class="nrp-card">
          <div class="nrp-label">Model</div>
          <div class="nrp-value">${escapeHtml(payload.model)}</div>
        </div>
        <div class="nrp-card">
          <div class="nrp-label">Latency</div>
          <div class="nrp-value">${escapeHtml(payload.latencyMs)} ms</div>
        </div>
        <div class="nrp-card">
          <div class="nrp-label">Confidence</div>
          <div class="nrp-value">${escapeHtml(payload.confidence)}</div>
        </div>
        <div class="nrp-card">
          <div class="nrp-label">Prompt Tokens</div>
          <div class="nrp-value">${escapeHtml(payload.promptTokens)}</div>
        </div>
        <div class="nrp-card">
          <div class="nrp-label">Completion Tokens</div>
          <div class="nrp-value">${escapeHtml(payload.completionTokens)}</div>
        </div>
      </div>

      <div class="nrp-section">
        <div class="nrp-section-title">Why this route</div>
        <div class="nrp-list">${reasons}</div>
      </div>

      <div class="nrp-section">
        <div class="nrp-section-title">Memory pulled</div>
        <div class="nrp-list">${memory}</div>
      </div>

      <div class="nrp-section">
        <div class="nrp-section-title">Raw route metadata</div>
        <div class="nrp-card"><pre>${escapeHtml(shortJson(payload.raw))}</pre></div>
      </div>
    `;
  }

  async function fetchStatePayload() {
    const urls = ["/api/state", "/api/chat/state", "/api/debug/state"];

    for (const url of urls) {
      try {
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) continue;
        const data = await response.json();
        if (data) return data;
      } catch {
        // keep trying
      }
    }

    return null;
  }

  function scanWindowForPayload() {
    const sources = [
      window.__NOVA_STATE__,
      window.__novaState,
      window.NOVA_STATE,
      window.__NOVA_DEBUG__,
      window.__novaDebug
    ];

    for (const source of sources) {
      const extracted = findLatestAssistantRoutePayload(source);
      if (extracted) return extracted;
    }

    return null;
  }

  function scanDomForPayload() {
    const selectors = [
      "[data-route-meta]",
      "[data-router-meta]",
      ".message.assistant[data-route-meta]",
      ".message.bot[data-route-meta]",
      ".chat-message.assistant[data-route-meta]"
    ];

    for (const selector of selectors) {
      const nodes = Array.from(document.querySelectorAll(selector));
      for (let i = nodes.length - 1; i >= 0; i -= 1) {
        const node = nodes[i];
        const raw =
          node.getAttribute("data-route-meta") ||
          node.getAttribute("data-router-meta");

        if (!raw) continue;

        try {
          const parsed = JSON.parse(raw);
          const extracted = routeFromMessage({ route_meta: parsed });
          if (extracted) return extracted;
        } catch {
          // ignore bad json
        }
      }
    }

    return null;
  }

  async function getBestPayload() {
    const windowPayload = scanWindowForPayload();
    if (windowPayload) return windowPayload;

    const domPayload = scanDomForPayload();
    if (domPayload) return domPayload;

    const data = await fetchStatePayload();
    return findLatestAssistantRoutePayload(data);
  }

  async function refreshPanel(forceOpenOnFirstData = false) {
    const payload = await getBestPayload();
    const hash = hashPayload(payload);

    if (hash !== state.lastHash) {
      state.lastHash = hash;
      state.lastPayload = payload;
      renderPayload(payload);

      if (payload && forceOpenOnFirstData && !state.isPinned) {
        setOpen(true);
      }
    } else if (state.lastPayload) {
      renderPayload(state.lastPayload);
    }
  }

  function startPolling() {
    stopPolling();
    state.pollTimer = window.setInterval(() => {
      refreshPanel(false);
    }, POLL_MS);
  }

  function stopPolling() {
    if (state.pollTimer) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  function hookFetchForRefresh() {
    if (window.__novaBrainRouterFetchHooked) return;
    window.__novaBrainRouterFetchHooked = true;

    const originalFetch = window.fetch;
    if (typeof originalFetch !== "function") return;

    window.fetch = async function (...args) {
      const response = await originalFetch.apply(this, args);

      try {
        const url = String(args?.[0] ?? "");
        if (
          url.includes("/api/chat") ||
          url.includes("/api/message") ||
          url.includes("/api/ask") ||
          url.includes("/api/state")
        ) {
          setTimeout(() => refreshPanel(false), 200);
          setTimeout(() => refreshPanel(false), 900);
        }
      } catch {
        // ignore
      }

      return response;
    };
  }

  function init() {
    ensureStyles();
    ensurePanel();
    ensureToggleButton();
    syncPanelUi();
    hookFetchForRefresh();
    startPolling();
    refreshPanel(false);

    window.addEventListener("beforeunload", stopPolling);
    console.log("Nova brain router panel loaded.");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();