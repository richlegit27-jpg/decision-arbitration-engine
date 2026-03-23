(() => {
  "use strict";

  if (window.__novaBrainRouterPanelLoaded) return;
  window.__novaBrainRouterPanelLoaded = true;

  const PANEL_ID = "novaRouterPanel";
  const STYLE_HOOK = "nova-router-panel-ready";
  const STORAGE_KEY_VISIBLE = "nova.router.panel.visible";
  const STORAGE_KEY_COLLAPSED = "nova.router.panel.collapsed";

  const DEFAULT_META = {
    intent: "general",
    route: "general",
    mode: "general",
    confidence: null,
    memory_used: null,
    memory_count: null,
    model: null,
    provider: null,
    source: "idle",
    timestamp: null,
  };

  let panel = null;
  let body = null;
  let valueRoute = null;
  let valueIntent = null;
  let valueConfidence = null;
  let valueMemory = null;
  let valueModel = null;
  let valueSource = null;
  let toggleBtn = null;
  let hideBtn = null;

  let state = {
    visible: readBool(STORAGE_KEY_VISIBLE, true),
    collapsed: readBool(STORAGE_KEY_COLLAPSED, false),
    meta: { ...DEFAULT_META },
  };

  function readBool(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      if (raw === null) return fallback;
      return raw === "1";
    } catch {
      return fallback;
    }
  }

  function writeBool(key, value) {
    try {
      localStorage.setItem(key, value ? "1" : "0");
    } catch {}
  }

  function safeText(value, fallback = "—") {
    const text = String(value ?? "").trim();
    return text || fallback;
  }

  function clampConfidence(value) {
    if (value === null || value === undefined || value === "") return null;
    const num = Number(value);
    if (!Number.isFinite(num)) return null;
    if (num <= 1) return `${Math.round(num * 100)}%`;
    return `${Math.round(num)}%`;
  }

  function boolish(value) {
    if (value === true) return "yes";
    if (value === false) return "no";
    return null;
  }

  function normalizeMeta(input) {
    const raw = input && typeof input === "object" ? input : {};
    const route = raw.route || raw.mode || raw.intent || DEFAULT_META.route;
    const intent = raw.intent || raw.route || raw.mode || DEFAULT_META.intent;

    let memoryValue = null;
    if (typeof raw.memory_count !== "undefined" && raw.memory_count !== null) {
      memoryValue = String(raw.memory_count);
    } else if (typeof raw.memory_used !== "undefined") {
      memoryValue = boolish(raw.memory_used);
    } else if (typeof raw.memory !== "undefined") {
      memoryValue = boolish(raw.memory);
    }

    const modelValue =
      raw.model ||
      raw.model_name ||
      raw.selected_model ||
      raw.provider_model ||
      null;

    const providerValue = raw.provider || raw.vendor || null;
    const sourceValue =
      raw.source ||
      raw.origin ||
      raw.from ||
      (raw.debug ? "debug" : null) ||
      "live";

    return {
      route: safeText(route),
      intent: safeText(intent),
      mode: safeText(raw.mode || route),
      confidence: clampConfidence(raw.confidence),
      memory_used:
        typeof raw.memory_used !== "undefined" ? raw.memory_used : raw.memory,
      memory_count:
        typeof raw.memory_count !== "undefined" ? raw.memory_count : null,
      memory_display: memoryValue,
      model: modelValue ? safeText(modelValue) : null,
      provider: providerValue ? safeText(providerValue) : null,
      source: safeText(sourceValue),
      timestamp: raw.timestamp || raw.ts || Date.now(),
    };
  }

  function modeClass(value) {
    const key = String(value || "general").toLowerCase();
    if (["coding", "planning", "writing", "analysis", "general"].includes(key)) {
      return key;
    }
    return "general";
  }

  function ensurePanel() {
    if (panel && document.body.contains(panel)) return panel;

    panel = document.createElement("section");
    panel.id = PANEL_ID;
    panel.className = "nova-router-panel";
    panel.setAttribute("aria-live", "polite");
    panel.setAttribute("aria-label", "Nova router panel");

    panel.innerHTML = `
      <div class="nova-router-header">
        <div class="nova-router-title">Router Debug</div>
        <div class="nova-router-header-actions">
          <button
            type="button"
            class="nova-router-toggle"
            id="novaRouterToggle"
            aria-label="Collapse router panel"
            title="Collapse"
          >–</button>
          <button
            type="button"
            class="nova-router-toggle"
            id="novaRouterHide"
            aria-label="Hide router panel"
            title="Hide"
          >×</button>
        </div>
      </div>

      <div class="nova-router-body" id="novaRouterBody">
        <div class="nova-router-row">
          <span class="nova-router-label">Route</span>
          <span class="nova-router-value">
            <span class="nova-router-badge general" id="novaRouterValueRoute">general</span>
          </span>
        </div>

        <div class="nova-router-row">
          <span class="nova-router-label">Intent</span>
          <span class="nova-router-value" id="novaRouterValueIntent">general</span>
        </div>

        <div class="nova-router-row">
          <span class="nova-router-label">Confidence</span>
          <span class="nova-router-value" id="novaRouterValueConfidence">—</span>
        </div>

        <div class="nova-router-row">
          <span class="nova-router-label">Memory</span>
          <span class="nova-router-value" id="novaRouterValueMemory">—</span>
        </div>

        <div class="nova-router-row">
          <span class="nova-router-label">Model</span>
          <span class="nova-router-value" id="novaRouterValueModel">—</span>
        </div>

        <div class="nova-router-row">
          <span class="nova-router-label">Source</span>
          <span class="nova-router-value" id="novaRouterValueSource">idle</span>
        </div>
      </div>

      <div class="nova-router-footer">
        <button type="button" class="nova-router-btn" id="novaRouterShowBtn">show</button>
        <button type="button" class="nova-router-btn" id="novaRouterResetBtn">reset</button>
      </div>
    `;

    document.body.appendChild(panel);

    body = panel.querySelector("#novaRouterBody");
    valueRoute = panel.querySelector("#novaRouterValueRoute");
    valueIntent = panel.querySelector("#novaRouterValueIntent");
    valueConfidence = panel.querySelector("#novaRouterValueConfidence");
    valueMemory = panel.querySelector("#novaRouterValueMemory");
    valueModel = panel.querySelector("#novaRouterValueModel");
    valueSource = panel.querySelector("#novaRouterValueSource");
    toggleBtn = panel.querySelector("#novaRouterToggle");
    hideBtn = panel.querySelector("#novaRouterHide");

    const showBtn = panel.querySelector("#novaRouterShowBtn");
    const resetBtn = panel.querySelector("#novaRouterResetBtn");

    toggleBtn?.addEventListener("click", toggleCollapsed);
    hideBtn?.addEventListener("click", hidePanel);
    showBtn?.addEventListener("click", showPanel);
    resetBtn?.addEventListener("click", resetPanel);

    panel.addEventListener("dblclick", () => {
      if (!state.visible) showPanel();
    });

    document.documentElement.classList.add(STYLE_HOOK);

    syncPanelState();
    renderMeta(state.meta);

    return panel;
  }

  function syncPanelState() {
    if (!panel) return;

    panel.classList.toggle("hidden", !state.visible);
    panel.classList.toggle("is-collapsed", !!state.collapsed);

    if (body) {
      body.style.display = state.collapsed ? "none" : "";
    }

    const footer = panel.querySelector(".nova-router-footer");
    if (footer) {
      footer.style.display = state.collapsed ? "none" : "";
    }

    if (toggleBtn) {
      toggleBtn.textContent = state.collapsed ? "+" : "–";
      toggleBtn.setAttribute(
        "aria-label",
        state.collapsed ? "Expand router panel" : "Collapse router panel"
      );
      toggleBtn.title = state.collapsed ? "Expand" : "Collapse";
    }
  }

  function renderMeta(metaInput) {
    const meta = normalizeMeta(metaInput);
    state.meta = meta;

    if (!panel) ensurePanel();

    if (valueRoute) {
      valueRoute.textContent = safeText(meta.route);
      valueRoute.className = `nova-router-badge ${modeClass(meta.route)}`;
    }

    if (valueIntent) {
      valueIntent.textContent = safeText(meta.intent);
    }

    if (valueConfidence) {
      valueConfidence.textContent = meta.confidence || "—";
    }

    if (valueMemory) {
      const memoryText =
        meta.memory_display ??
        (meta.memory_count !== null ? String(meta.memory_count) : "—");
      valueMemory.textContent = memoryText;
    }

    if (valueModel) {
      valueModel.textContent = meta.provider
        ? `${safeText(meta.provider)} / ${safeText(meta.model)}`
        : safeText(meta.model);
    }

    if (valueSource) {
      valueSource.textContent = safeText(meta.source);
    }

    window.__novaLastRouterMeta = meta;
  }

  function applyRouterMeta(meta) {
    renderMeta(meta);
    if (!state.visible) {
      state.visible = true;
      writeBool(STORAGE_KEY_VISIBLE, true);
      syncPanelState();
    }
  }

  function toggleCollapsed() {
    state.collapsed = !state.collapsed;
    writeBool(STORAGE_KEY_COLLAPSED, state.collapsed);
    syncPanelState();
  }

  function hidePanel() {
    state.visible = false;
    writeBool(STORAGE_KEY_VISIBLE, false);
    syncPanelState();
  }

  function showPanel() {
    state.visible = true;
    writeBool(STORAGE_KEY_VISIBLE, true);
    syncPanelState();
  }

  function resetPanel() {
    state.meta = { ...DEFAULT_META, source: "reset" };
    state.visible = true;
    state.collapsed = false;
    writeBool(STORAGE_KEY_VISIBLE, true);
    writeBool(STORAGE_KEY_COLLAPSED, false);
    syncPanelState();
    renderMeta(state.meta);
  }

  function tryReadWindowMeta() {
    const meta = window.__novaLastRouterMeta || window.__novaRouterMeta || null;
    if (meta && typeof meta === "object") {
      applyRouterMeta(meta);
      return true;
    }
    return false;
  }

  function tryReadAppMeta() {
    const app = window.novaApp || window.__novaApp || null;
    const meta =
      app?.routerMeta ||
      app?.state?.routerMeta ||
      app?.state?.lastRouterMeta ||
      null;

    if (meta && typeof meta === "object") {
      applyRouterMeta(meta);
      return true;
    }
    return false;
  }

  async function tryReadApiMeta() {
    try {
      const res = await fetch("/api/state", {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          "Cache-Control": "no-cache",
          Pragma: "no-cache",
        },
      });

      if (!res.ok) return false;

      const data = await res.json();
      const meta =
        data?.router_meta ||
        data?.routerMeta ||
        data?.last_router_meta ||
        data?.lastRouterMeta ||
        null;

      if (meta && typeof meta === "object") {
        applyRouterMeta(meta);
        return true;
      }
    } catch {}
    return false;
  }

  function patchFetch() {
    if (window.__novaRouterFetchPatched) return;
    window.__novaRouterFetchPatched = true;

    const originalFetch = window.fetch;
    if (typeof originalFetch !== "function") return;

    window.fetch = async function (...args) {
      const response = await originalFetch.apply(this, args);

      try {
        const cloned = response.clone();
        const url =
          typeof args[0] === "string"
            ? args[0]
            : args[0]?.url || response.url || "";

        if (
          url.includes("/api/chat") ||
          url.includes("/api/send") ||
          url.includes("/api/state")
        ) {
          cloned
            .json()
            .then((data) => {
              const meta =
                data?.router_meta ||
                data?.routerMeta ||
                data?.last_router_meta ||
                data?.lastRouterMeta ||
                data?.meta?.router ||
                null;

              if (meta && typeof meta === "object") {
                applyRouterMeta(meta);
              }
            })
            .catch(() => {});
        }
      } catch {}

      return response;
    };
  }

  function patchXhr() {
    if (window.__novaRouterXhrPatched) return;
    window.__novaRouterXhrPatched = true;

    const OriginalOpen = XMLHttpRequest.prototype.open;
    const OriginalSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function (method, url, ...rest) {
      this.__novaUrl = String(url || "");
      return OriginalOpen.call(this, method, url, ...rest);
    };

    XMLHttpRequest.prototype.send = function (...args) {
      this.addEventListener("load", function () {
        try {
          const url = this.__novaUrl || "";
          if (
            !url.includes("/api/chat") &&
            !url.includes("/api/send") &&
            !url.includes("/api/state")
          ) {
            return;
          }

          const data = JSON.parse(this.responseText || "{}");
          const meta =
            data?.router_meta ||
            data?.routerMeta ||
            data?.last_router_meta ||
            data?.lastRouterMeta ||
            data?.meta?.router ||
            null;

          if (meta && typeof meta === "object") {
            applyRouterMeta(meta);
          }
        } catch {}
      });

      return OriginalSend.apply(this, args);
    };
  }

  function startPollingFallback() {
    let attempts = 0;
    const maxAttempts = 20;

    const tick = async () => {
      attempts += 1;

      const gotWindow = tryReadWindowMeta();
      const gotApp = tryReadAppMeta();

      if (!gotWindow && !gotApp) {
        await tryReadApiMeta();
      }

      if (attempts >= maxAttempts) {
        clearInterval(timer);
      }
    };

    const timer = window.setInterval(tick, 2500);
    tick();
  }

  function bindEvents() {
    window.addEventListener("nova:router-meta", (event) => {
      const meta = event?.detail;
      if (meta && typeof meta === "object") {
        applyRouterMeta(meta);
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "F8") {
        event.preventDefault();
        state.visible ? hidePanel() : showPanel();
      }

      if (event.key === "F9") {
        event.preventDefault();
        toggleCollapsed();
      }
    });

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        tryReadWindowMeta();
        tryReadAppMeta();
        tryReadApiMeta();
      }
    });
  }

  function bootstrap() {
    ensurePanel();
    patchFetch();
    patchXhr();
    bindEvents();

    const gotWindow = tryReadWindowMeta();
    const gotApp = tryReadAppMeta();

    if (!gotWindow && !gotApp) {
      tryReadApiMeta();
    }

    startPollingFallback();
    console.log("Nova brain router panel loaded");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
  } else {
    bootstrap();
  }
})();