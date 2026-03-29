(() => {
  "use strict";

  if (window.__novaRouterControlLoaded) return;
  window.__novaRouterControlLoaded = true;

  const ROUTER_EVENT_NAME = "nova:router-meta";
  const API_STATE_URL = "/api/state";
  const POLL_INTERVAL_MS = 4000;

  const state = {
    meta: null,
    panelOpen: false,
    mounted: false,
    pollTimer: null,
    fetchWrapped: false,
    xhrWrapped: false,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function safeText(value, fallback = "—") {
    const text = String(value ?? "").trim();
    return text || fallback;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function shortJson(value) {
    if (value == null) return "—";
    try {
      const text = JSON.stringify(value, null, 2);
      return text.length > 1600 ? `${text.slice(0, 1600)}\n…` : text;
    } catch {
      return String(value);
    }
  }

  function normalizeMeta(meta) {
    if (!meta || typeof meta !== "object") return null;

    const memory = meta.memory || meta.memory_used || meta.memory_context || [];
    const retrieval = meta.retrieval || meta.sources || [];
    const flags = meta.flags || {};

    return {
      intent: safeText(meta.intent || meta.route || meta.mode || meta.category),
      model: safeText(meta.model || meta.selected_model || meta.llm),
      confidence: meta.confidence ?? meta.score ?? meta.router_confidence ?? null,
      reason: safeText(meta.reason || meta.summary || meta.explanation),
      routeTimeMs: meta.route_time_ms ?? meta.latency_ms ?? meta.router_time_ms ?? null,
      memoryCount:
        typeof meta.memory_count === "number"
          ? meta.memory_count
          : Array.isArray(memory)
            ? memory.length
            : 0,
      sourceCount:
        typeof meta.source_count === "number"
          ? meta.source_count
          : Array.isArray(retrieval)
            ? retrieval.length
            : 0,
      memory,
      retrieval,
      flags,
      raw: meta,
      timestamp: safeText(meta.timestamp || meta.created_at || new Date().toISOString()),
    };
  }

  function getRoot() {
    return byId("novaRouterControl");
  }

  function getRefs() {
    const root = getRoot();
    if (!root) return null;

    return {
      root,
      toggle: qs("[data-router-toggle]", root) || byId("novaRouterControlToggle"),
      close: qs("[data-router-close]", root) || byId("novaRouterControlClose"),
      refresh: qs("[data-router-refresh]", root) || byId("novaRouterControlRefresh"),
      status: qs("[data-router-status]", root) || byId("novaRouterControlStatus"),
      intent: qs("[data-router-intent]", root) || byId("novaRouterIntent"),
      model: qs("[data-router-model]", root) || byId("novaRouterModel"),
      confidence: qs("[data-router-confidence]", root) || byId("novaRouterConfidence"),
      routeTime: qs("[data-router-time]", root) || byId("novaRouterTime"),
      reason: qs("[data-router-reason]", root) || byId("novaRouterReason"),
      memoryCount: qs("[data-router-memory-count]", root) || byId("novaRouterMemoryCount"),
      sourceCount: qs("[data-router-source-count]", root) || byId("novaRouterSourceCount"),
      memoryList: qs("[data-router-memory-list]", root) || byId("novaRouterMemoryList"),
      sourceList: qs("[data-router-source-list]", root) || byId("novaRouterSourceList"),
      raw: qs("[data-router-raw]", root) || byId("novaRouterRaw"),
      body: qs("[data-router-body]", root) || byId("novaRouterControlBody"),
      pill: qs("[data-router-pill]", root) || byId("novaRouterIntentPill"),
      timestamp: qs("[data-router-timestamp]", root) || byId("novaRouterTimestamp"),
    };
  }

  function setStatus(text) {
    const refs = getRefs();
    if (!refs?.status) return;
    refs.status.textContent = safeText(text);
  }

  function setPanelOpen(isOpen) {
    const refs = getRefs();
    if (!refs) return;

    state.panelOpen = !!isOpen;
    refs.root.classList.toggle("is-open", state.panelOpen);
    refs.root.setAttribute("data-open", state.panelOpen ? "true" : "false");

    if (refs.body) {
      refs.body.hidden = !state.panelOpen;
    }

    if (refs.toggle) {
      refs.toggle.setAttribute("aria-expanded", state.panelOpen ? "true" : "false");
    }
  }

  function togglePanel() {
    setPanelOpen(!state.panelOpen);
  }

  function renderList(list, emptyLabel) {
    if (!Array.isArray(list) || !list.length) {
      return `<div class="nova-router-empty">${escapeHtml(emptyLabel)}</div>`;
    }

    return list
      .map((item) => {
        if (item == null) {
          return `<div class="nova-router-item">—</div>`;
        }

        if (typeof item === "string") {
          return `<div class="nova-router-item">${escapeHtml(item)}</div>`;
        }

        if (typeof item === "object") {
          const label =
            item.label ||
            item.name ||
            item.title ||
            item.key ||
            item.id ||
            JSON.stringify(item);
          const detail =
            item.value ||
            item.kind ||
            item.type ||
            item.source ||
            item.score ||
            item.preview ||
            "";

          return `
            <div class="nova-router-item">
              <div class="nova-router-item-title">${escapeHtml(String(label))}</div>
              ${detail ? `<div class="nova-router-item-meta">${escapeHtml(String(detail))}</div>` : ""}
            </div>
          `;
        }

        return `<div class="nova-router-item">${escapeHtml(String(item))}</div>`;
      })
      .join("");
  }

  function renderMeta(meta) {
    const refs = getRefs();
    if (!refs) return;

    const normalized = normalizeMeta(meta);
    state.meta = normalized;

    if (!normalized) {
      if (refs.intent) refs.intent.textContent = "—";
      if (refs.model) refs.model.textContent = "—";
      if (refs.confidence) refs.confidence.textContent = "—";
      if (refs.routeTime) refs.routeTime.textContent = "—";
      if (refs.reason) refs.reason.textContent = "No router meta yet.";
      if (refs.memoryCount) refs.memoryCount.textContent = "0";
      if (refs.sourceCount) refs.sourceCount.textContent = "0";
      if (refs.memoryList) refs.memoryList.innerHTML = `<div class="nova-router-empty">No memory used.</div>`;
      if (refs.sourceList) refs.sourceList.innerHTML = `<div class="nova-router-empty">No sources used.</div>`;
      if (refs.raw) refs.raw.textContent = "{}";
      if (refs.pill) refs.pill.textContent = "idle";
      if (refs.timestamp) refs.timestamp.textContent = "—";
      setStatus("Waiting for router meta");
      return;
    }

    if (refs.intent) refs.intent.textContent = normalized.intent;
    if (refs.model) refs.model.textContent = normalized.model;
    if (refs.confidence) {
      refs.confidence.textContent =
        typeof normalized.confidence === "number"
          ? `${Math.round(normalized.confidence * 100)}%`
          : safeText(normalized.confidence);
    }
    if (refs.routeTime) {
      refs.routeTime.textContent =
        typeof normalized.routeTimeMs === "number"
          ? `${normalized.routeTimeMs} ms`
          : safeText(normalized.routeTimeMs);
    }
    if (refs.reason) refs.reason.textContent = normalized.reason;
    if (refs.memoryCount) refs.memoryCount.textContent = String(normalized.memoryCount);
    if (refs.sourceCount) refs.sourceCount.textContent = String(normalized.sourceCount);
    if (refs.memoryList) refs.memoryList.innerHTML = renderList(normalized.memory, "No memory used.");
    if (refs.sourceList) refs.sourceList.innerHTML = renderList(normalized.retrieval, "No sources used.");
    if (refs.raw) refs.raw.textContent = shortJson(normalized.raw);
    if (refs.pill) refs.pill.textContent = normalized.intent.toLowerCase();
    if (refs.timestamp) refs.timestamp.textContent = normalized.timestamp;

    refs.root?.setAttribute("data-intent", normalized.intent.toLowerCase().replace(/\s+/g, "-"));
    setStatus("Router meta ready");
  }

  function applyRouterMeta(meta) {
    const normalized = normalizeMeta(meta);
    if (!normalized) return false;

    window.__novaLastRouterMeta = normalized.raw;
    renderMeta(normalized.raw);

    window.dispatchEvent(
      new CustomEvent("nova:router-control-updated", {
        detail: normalized.raw,
      })
    );

    return true;
  }

  function extractMetaFromPayload(payload) {
    if (!payload) return null;

    if (payload.router_meta && typeof payload.router_meta === "object") {
      return payload.router_meta;
    }

    if (payload.router && typeof payload.router === "object") {
      return payload.router;
    }

    if (payload.meta && typeof payload.meta === "object" && payload.meta.intent) {
      return payload.meta;
    }

    if (payload.state && typeof payload.state === "object") {
      return extractMetaFromPayload(payload.state);
    }

    if (payload.data && typeof payload.data === "object") {
      return extractMetaFromPayload(payload.data);
    }

    return null;
  }

  function tryReadFromWindowState() {
    const meta =
      window.__novaLastRouterMeta ||
      window.__novaRouterMeta ||
      window.__lastRouterMeta ||
      null;

    if (!meta) return false;
    return applyRouterMeta(meta);
  }

  function tryReadFromAppState() {
    const app = window.novaApp || window.__novaApp || window.app || null;
    if (!app || typeof app !== "object") return false;

    const meta =
      app.routerMeta ||
      app.lastRouterMeta ||
      app.state?.routerMeta ||
      app.state?.lastRouterMeta ||
      null;

    if (!meta) return false;
    return applyRouterMeta(meta);
  }

  async function tryReadFromApiState() {
    try {
      const response = await fetch(`${API_STATE_URL}?router_meta=1`, {
        method: "GET",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
        },
      });

      if (!response.ok) return false;

      const payload = await response.json();
      const meta = extractMetaFromPayload(payload);

      if (!meta) return false;
      return applyRouterMeta(meta);
    } catch (error) {
      console.warn("Nova router control API state read failed:", error);
      return false;
    }
  }

  function installFetchTap() {
    if (state.fetchWrapped || typeof window.fetch !== "function") return;
    state.fetchWrapped = true;

    const originalFetch = window.fetch.bind(window);

    window.fetch = async (...args) => {
      const response = await originalFetch(...args);

      try {
        const clone = response.clone();
        const contentType = clone.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
          clone
            .json()
            .then((payload) => {
              const meta = extractMetaFromPayload(payload);
              if (meta) {
                applyRouterMeta(meta);
              }
            })
            .catch(() => {});
        }
      } catch {
        // no-op
      }

      return response;
    };
  }

  function installXhrTap() {
    if (state.xhrWrapped || typeof XMLHttpRequest === "undefined") return;
    state.xhrWrapped = true;

    const OriginalOpen = XMLHttpRequest.prototype.open;
    const OriginalSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function (...args) {
      this.__novaRouterControlUrl = args[1];
      return OriginalOpen.apply(this, args);
    };

    XMLHttpRequest.prototype.send = function (...args) {
      this.addEventListener("load", function () {
        try {
          const contentType = this.getResponseHeader("content-type") || "";
          if (!contentType.includes("application/json")) return;

          const payload = JSON.parse(this.responseText);
          const meta = extractMetaFromPayload(payload);
          if (meta) {
            applyRouterMeta(meta);
          }
        } catch {
          // no-op
        }
      });

      return OriginalSend.apply(this, args);
    };
  }

  function bindEvents() {
    const refs = getRefs();
    if (!refs) return;

    refs.toggle?.addEventListener("click", () => {
      togglePanel();
    });

    refs.close?.addEventListener("click", () => {
      setPanelOpen(false);
    });

    refs.refresh?.addEventListener("click", async () => {
      setStatus("Refreshing...");
      const okWindow = tryReadFromWindowState();
      const okApp = tryReadFromAppState();
      const okApi = okWindow || okApp ? true : await tryReadFromApiState();

      if (okWindow || okApp || okApi) {
        setStatus("Router meta refreshed");
      } else {
        setStatus("No router meta found");
      }
    });

    window.addEventListener(ROUTER_EVENT_NAME, (event) => {
      const meta = event?.detail;
      if (meta && typeof meta === "object") {
        applyRouterMeta(meta);
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && state.panelOpen) {
        setPanelOpen(false);
      }
    });
  }

  function startPollingFallback() {
    stopPollingFallback();

    state.pollTimer = window.setInterval(async () => {
      const gotWindow = tryReadFromWindowState();
      const gotApp = tryReadFromAppState();

      if (!gotWindow && !gotApp) {
        await tryReadFromApiState();
      }
    }, POLL_INTERVAL_MS);
  }

  function stopPollingFallback() {
    if (state.pollTimer) {
      window.clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  function mount() {
    const root = getRoot();
    if (!root) {
      console.log("Nova router control: root not found, standing by.");
      return;
    }

    if (state.mounted) return;
    state.mounted = true;

    bindEvents();
    installFetchTap();
    installXhrTap();

    renderMeta(window.__novaLastRouterMeta || null);

    const gotWindow = tryReadFromWindowState();
    const gotApp = tryReadFromAppState();

    if (!gotWindow && !gotApp) {
      tryReadFromApiState();
    }

    startPollingFallback();

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        tryReadFromWindowState();
        tryReadFromAppState();
        tryReadFromApiState();
      }
    });

    console.log("Nova router control loaded");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount, { once: true });
  } else {
    mount();
  }

  window.NovaRouterControl = {
    render: renderMeta,
    apply: applyRouterMeta,
    refresh: async () => {
      const gotWindow = tryReadFromWindowState();
      const gotApp = tryReadFromAppState();
      if (gotWindow || gotApp) return true;
      return await tryReadFromApiState();
    },
    open: () => setPanelOpen(true),
    close: () => setPanelOpen(false),
    toggle: togglePanel,
    getMeta: () => state.meta,
  };
})();