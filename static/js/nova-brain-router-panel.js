(() => {
  "use strict";

  if (window.__novaRouterPanelLoaded) return;
  window.__novaRouterPanelLoaded = true;

  const PANEL_ID = "novaRouterPanel";
  const MOBILE_BREAKPOINT = 900;
  const POLL_MS = 3500;

  const state = {
    panel: null,
    body: null,
    meta: null,
    pollTimer: null,
    isOpen: false,
    isCompact: false,
    isMobile: false,
    initialized: false,
  };

  function safeText(value) {
    if (value == null) return "";
    return String(value).trim();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function readViewportWidth() {
    return window.visualViewport?.width || window.innerWidth || document.documentElement.clientWidth || 0;
  }

  function isMobileViewport() {
    return readViewportWidth() <= MOBILE_BREAKPOINT;
  }

  function normalizeMeta(meta) {
    if (!meta || typeof meta !== "object") return null;

    return {
      mode: safeText(meta.mode || meta.route || meta.intent_mode || "unknown"),
      intent: safeText(meta.intent || meta.task || "unknown"),
      model: safeText(meta.model || meta.selected_model || "unknown"),
      confidence: meta.confidence == null ? "" : String(meta.confidence),
      source: safeText(meta.source || meta.router_source || "server"),
      memory_used: !!meta.memory_used,
      memory_count: Number.isFinite(Number(meta.memory_count)) ? Number(meta.memory_count) : 0,
      raw: meta,
    };
  }

  function formatConfidence(value) {
    const raw = safeText(value);
    if (!raw) return "—";

    const num = Number(raw);
    if (!Number.isFinite(num)) return raw;

    if (num <= 1) return `${Math.round(num * 100)}%`;
    return `${Math.round(num)}%`;
  }

  function ensurePanel() {
    if (state.panel && document.body.contains(state.panel)) {
      return state.panel;
    }

    const panel = document.createElement("aside");
    panel.id = PANEL_ID;
    panel.className = "nova-router-panel";
    panel.setAttribute("aria-hidden", "true");

    panel.innerHTML = `
      <button type="button" class="nova-router-panel-toggle" id="novaRouterPanelToggle" aria-expanded="false" aria-controls="${PANEL_ID}">
        <span class="nova-router-panel-toggle-dot"></span>
        <span class="nova-router-panel-toggle-text">Router</span>
      </button>

      <div class="nova-router-panel-shell">
        <div class="nova-router-panel-header">
          <div class="nova-router-panel-title-wrap">
            <div class="nova-router-panel-title">Router Debug</div>
            <div class="nova-router-panel-subtitle" id="novaRouterPanelSubtitle">Waiting for data</div>
          </div>

          <div class="nova-router-panel-actions">
            <button type="button" class="nova-router-panel-action" id="novaRouterPanelRefresh" title="Refresh">↻</button>
            <button type="button" class="nova-router-panel-action" id="novaRouterPanelClose" title="Close">✕</button>
          </div>
        </div>

        <div class="nova-router-panel-content">
          <div class="nova-router-grid">
            <div class="nova-router-card">
              <div class="nova-router-label">Mode</div>
              <div class="nova-router-value" id="novaRouterMode">—</div>
            </div>

            <div class="nova-router-card">
              <div class="nova-router-label">Intent</div>
              <div class="nova-router-value" id="novaRouterIntent">—</div>
            </div>

            <div class="nova-router-card">
              <div class="nova-router-label">Model</div>
              <div class="nova-router-value" id="novaRouterModel">—</div>
            </div>

            <div class="nova-router-card">
              <div class="nova-router-label">Confidence</div>
              <div class="nova-router-value" id="novaRouterConfidence">—</div>
            </div>

            <div class="nova-router-card">
              <div class="nova-router-label">Memory Used</div>
              <div class="nova-router-value" id="novaRouterMemoryUsed">—</div>
            </div>

            <div class="nova-router-card">
              <div class="nova-router-label">Memory Count</div>
              <div class="nova-router-value" id="novaRouterMemoryCount">—</div>
            </div>

            <div class="nova-router-card nova-router-card-wide">
              <div class="nova-router-label">Source</div>
              <div class="nova-router-value" id="novaRouterSource">—</div>
            </div>
          </div>

          <details class="nova-router-raw-wrap">
            <summary>Raw router meta</summary>
            <pre class="nova-router-raw" id="novaRouterRaw">{}</pre>
          </details>
        </div>
      </div>
    `;

    document.body.appendChild(panel);
    state.panel = panel;
    state.body = document.body;

    bindPanelEvents();
    applyViewportMode();
    return panel;
  }

  function bindPanelEvents() {
    const toggle = byId("novaRouterPanelToggle");
    const close = byId("novaRouterPanelClose");
    const refresh = byId("novaRouterPanelRefresh");

    toggle?.addEventListener("click", () => {
      state.isOpen ? closePanel() : openPanel();
    });

    close?.addEventListener("click", () => {
      closePanel();
    });

    refresh?.addEventListener("click", async () => {
      await tryReadFromApiState(true);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && state.isOpen) {
        closePanel();
      }
    });

    document.addEventListener("click", (event) => {
      if (!state.isMobile || !state.isOpen || !state.panel) return;

      const target = event.target;
      if (!(target instanceof Node)) return;

      const toggleBtn = byId("novaRouterPanelToggle");
      if (state.panel.contains(target)) return;
      if (toggleBtn?.contains(target)) return;

      closePanel();
    });

    window.addEventListener("resize", handleViewportChange);

    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", handleViewportChange);
    }

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        handleViewportChange();
        tryReadFromWindowState();
        tryReadFromAppState();
        tryReadFromApiState();
      }
    });

    window.addEventListener("orientationchange", () => {
      setTimeout(() => {
        handleViewportChange();
      }, 120);
    });
  }

  function handleViewportChange() {
    applyViewportMode();

    if (state.isMobile && state.isOpen) {
      lockBodyScroll(true);
    } else {
      lockBodyScroll(false);
    }
  }

  function applyViewportMode() {
    state.isMobile = isMobileViewport();

    if (!state.panel) return;

    state.panel.classList.toggle("mobile", state.isMobile);
    state.panel.classList.toggle("desktop", !state.isMobile);

    if (state.isMobile) {
      state.isCompact = true;
      state.panel.classList.add("compact");
    } else {
      state.panel.classList.remove("compact");
    }
  }

  function lockBodyScroll(lock) {
    document.documentElement.classList.toggle("nova-router-panel-lock", !!lock);
    document.body.classList.toggle("nova-router-panel-lock", !!lock);
  }

  function openPanel() {
    ensurePanel();
    state.isOpen = true;

    state.panel.classList.add("open");
    state.panel.setAttribute("aria-hidden", "false");
    byId("novaRouterPanelToggle")?.setAttribute("aria-expanded", "true");

    if (state.isMobile) {
      lockBodyScroll(true);
    }
  }

  function closePanel() {
    if (!state.panel) return;

    state.isOpen = false;
    state.panel.classList.remove("open");
    state.panel.setAttribute("aria-hidden", "true");
    byId("novaRouterPanelToggle")?.setAttribute("aria-expanded", "false");
    lockBodyScroll(false);
  }

  function renderRouter(meta) {
    ensurePanel();

    const normalized = normalizeMeta(meta);
    state.meta = normalized;

    byId("novaRouterMode").textContent = normalized?.mode || "—";
    byId("novaRouterIntent").textContent = normalized?.intent || "—";
    byId("novaRouterModel").textContent = normalized?.model || "—";
    byId("novaRouterConfidence").textContent = normalized ? formatConfidence(normalized.confidence) : "—";
    byId("novaRouterMemoryUsed").textContent = normalized ? (normalized.memory_used ? "yes" : "no") : "—";
    byId("novaRouterMemoryCount").textContent = normalized ? String(normalized.memory_count) : "—";
    byId("novaRouterSource").textContent = normalized?.source || "—";

    const subtitle = byId("novaRouterPanelSubtitle");
    if (subtitle) {
      subtitle.textContent = normalized
        ? `${normalized.mode || "unknown"} · ${normalized.intent || "unknown"}`
        : "Waiting for data";
    }

    const raw = byId("novaRouterRaw");
    if (raw) {
      raw.textContent = normalized?.raw ? JSON.stringify(normalized.raw, null, 2) : "{}";
    }

    window.__novaLastRouterMeta = normalized?.raw || null;
  }

  function tryReadFromWindowState() {
    const meta = window.__novaLastRouterMeta || window.__lastRouterMeta || window.__routerMeta || null;
    if (meta) {
      renderRouter(meta);
      return true;
    }
    return false;
  }

  function tryReadFromAppState() {
    const app = window.__novaApp || window.novaApp || null;
    const meta =
      app?.state?.router_meta ||
      app?.router_meta ||
      app?.routerMeta ||
      null;

    if (meta) {
      renderRouter(meta);
      return true;
    }

    return false;
  }

  async function tryReadFromApiState(force = false) {
    if (!force && document.hidden) return false;

    try {
      const response = await fetch("/api/state", {
        method: "GET",
        headers: { "Accept": "application/json" },
        cache: "no-store",
      });

      if (!response.ok) return false;

      const data = await response.json().catch(() => null);
      const meta =
        data?.router_meta ||
        data?.router ||
        data?.state?.router_meta ||
        data?.last_router_meta ||
        null;

      if (meta) {
        renderRouter(meta);
        return true;
      }
    } catch (_) {}

    return false;
  }

  function startPollingFallback() {
    stopPollingFallback();

    state.pollTimer = window.setInterval(() => {
      if (document.hidden) return;
      if (tryReadFromWindowState()) return;
      if (tryReadFromAppState()) return;
      tryReadFromApiState();
    }, POLL_MS);
  }

  function stopPollingFallback() {
    if (state.pollTimer) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  function installFetchTap() {
    if (window.__novaRouterFetchTapInstalled) return;
    window.__novaRouterFetchTapInstalled = true;

    const originalFetch = window.fetch;
    if (typeof originalFetch !== "function") return;

    window.fetch = async function (...args) {
      const response = await originalFetch.apply(this, args);

      try {
        const url = String(args?.[0]?.url || args?.[0] || "");
        if (!url.includes("/api/chat") && !url.includes("/api/state")) {
          return response;
        }

        const clone = response.clone();
        const contentType = clone.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
          const data = await clone.json().catch(() => null);
          const meta =
            data?.router_meta ||
            data?.router ||
            data?.state?.router_meta ||
            data?.last_router_meta ||
            null;

          if (meta) {
            renderRouter(meta);
          }
        }
      } catch (_) {}

      return response;
    };
  }

  function installXhrTap() {
    if (window.__novaRouterXhrTapInstalled) return;
    window.__novaRouterXhrTapInstalled = true;

    const OriginalXHR = window.XMLHttpRequest;
    if (!OriginalXHR) return;

    function WrappedXHR() {
      const xhr = new OriginalXHR();
      let requestUrl = "";

      const open = xhr.open;
      xhr.open = function (method, url, ...rest) {
        requestUrl = String(url || "");
        return open.call(this, method, url, ...rest);
      };

      xhr.addEventListener("load", () => {
        try {
          if (!requestUrl.includes("/api/chat") && !requestUrl.includes("/api/state")) {
            return;
          }

          const contentType = xhr.getResponseHeader("content-type") || "";
          if (!contentType.includes("application/json")) return;

          const data = JSON.parse(xhr.responseText || "{}");
          const meta =
            data?.router_meta ||
            data?.router ||
            data?.state?.router_meta ||
            data?.last_router_meta ||
            null;

          if (meta) {
            renderRouter(meta);
          }
        } catch (_) {}
      });

      return xhr;
    }

    window.XMLHttpRequest = WrappedXHR;
  }

  function installEventHooks() {
    window.addEventListener("nova:router-meta", (event) => {
      const meta = event?.detail;
      if (meta && typeof meta === "object") {
        renderRouter(meta);
      }
    });
  }

  function installStyles() {
    if (byId("novaRouterPanelInlineStyles")) return;

    const style = document.createElement("style");
    style.id = "novaRouterPanelInlineStyles";
    style.textContent = `
      .nova-router-panel {
        position: fixed;
        right: 14px;
        bottom: 14px;
        z-index: 9999;
        font-family: Arial, sans-serif;
      }

      .nova-router-panel-toggle {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(15, 20, 35, 0.96);
        color: #eef3ff;
        border-radius: 999px;
        padding: 10px 14px;
        cursor: pointer;
        box-shadow: 0 10px 25px rgba(0,0,0,0.25);
      }

      .nova-router-panel-toggle-dot {
        width: 9px;
        height: 9px;
        border-radius: 999px;
        background: #72f1a6;
        flex: 0 0 auto;
      }

      .nova-router-panel-shell {
        display: none;
        width: min(360px, calc(100vw - 28px));
        margin-top: 10px;
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(10, 15, 28, 0.98);
        color: #eef3ff;
        box-shadow: 0 18px 45px rgba(0,0,0,0.36);
      }

      .nova-router-panel.open .nova-router-panel-shell {
        display: block;
      }

      .nova-router-panel-header {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: center;
        padding: 14px 14px 10px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
      }

      .nova-router-panel-title {
        font-size: 14px;
        font-weight: 700;
      }

      .nova-router-panel-subtitle {
        margin-top: 4px;
        font-size: 12px;
        opacity: 0.72;
      }

      .nova-router-panel-actions {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .nova-router-panel-action {
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.04);
        color: #eef3ff;
        border-radius: 10px;
        min-width: 34px;
        height: 34px;
        cursor: pointer;
      }

      .nova-router-panel-content {
        padding: 14px;
        max-height: min(72vh, 560px);
        overflow: auto;
      }

      .nova-router-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
      }

      .nova-router-card {
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
        border-radius: 14px;
        padding: 10px 11px;
        min-width: 0;
      }

      .nova-router-card-wide {
        grid-column: 1 / -1;
      }

      .nova-router-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 0.68;
        margin-bottom: 6px;
      }

      .nova-router-value {
        font-size: 13px;
        font-weight: 600;
        line-height: 1.35;
        word-break: break-word;
      }

      .nova-router-raw-wrap {
        margin-top: 12px;
        border-top: 1px solid rgba(255,255,255,0.08);
        padding-top: 12px;
      }

      .nova-router-raw-wrap summary {
        cursor: pointer;
        font-size: 12px;
        opacity: 0.8;
      }

      .nova-router-raw {
        margin: 10px 0 0;
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 11px;
        line-height: 1.45;
        background: rgba(255,255,255,0.04);
        border-radius: 12px;
        padding: 10px;
        overflow: auto;
      }

      .nova-router-panel.mobile {
        right: 10px;
        left: 10px;
        bottom: calc(env(safe-area-inset-bottom, 0px) + 10px);
      }

      .nova-router-panel.mobile .nova-router-panel-toggle {
        width: 100%;
        justify-content: center;
      }

      .nova-router-panel.mobile .nova-router-panel-shell {
        width: 100%;
        max-height: min(70vh, 520px);
      }

      .nova-router-panel.mobile.open .nova-router-panel-shell {
        display: block;
      }

      .nova-router-panel-lock,
      .nova-router-panel-lock body {
        overflow: hidden !important;
      }

      @media (max-width: 900px) {
        .nova-router-grid {
          grid-template-columns: 1fr 1fr;
        }
      }

      @media (max-width: 560px) {
        .nova-router-grid {
          grid-template-columns: 1fr;
        }

        .nova-router-card-wide {
          grid-column: auto;
        }

        .nova-router-panel-content {
          max-height: 58vh;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function init() {
    if (state.initialized) return;
    state.initialized = true;

    installStyles();
    ensurePanel();
    installFetchTap();
    installXhrTap();
    installEventHooks();

    tryReadFromWindowState();
    tryReadFromAppState();
    tryReadFromApiState();
    startPollingFallback();

    console.log("Nova brain router panel loaded");
  }

  init();

  window.__novaRouterPanel = {
    open: openPanel,
    close: closePanel,
    render: renderRouter,
    refresh: tryReadFromApiState,
    state,
  };
})();