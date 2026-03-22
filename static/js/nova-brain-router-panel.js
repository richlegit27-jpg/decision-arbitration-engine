(() => {
  "use strict";

  if (window.__novaBrainRouterPanelLoaded) {
    console.warn("nova-brain-router-panel.js already loaded");
    return;
  }
  window.__novaBrainRouterPanelLoaded = true;

  const ROUTER_CONTAINER_ID = "routerContent";

  const state = {
    lastSignature: "",
    startedAt: Date.now(),
    pollTimer: null,
  };

  function getRouterContainer() {
    return document.getElementById(ROUTER_CONTAINER_ID);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function toTitleCase(value) {
    const text = String(value || "").trim();
    if (!text) return "—";
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function safeText(value, fallback = "—") {
    if (value === null || value === undefined) return fallback;
    const text = String(value).trim();
    return text || fallback;
  }

  function normalizeArray(value) {
    if (Array.isArray(value)) return value.filter(Boolean);
    if (typeof value === "string" && value.trim()) return [value.trim()];
    return [];
  }

  function pickRouterMeta(payload) {
    if (!payload || typeof payload !== "object") {
      return null;
    }

    const direct =
      payload.router ||
      payload.route ||
      payload.routing ||
      payload.route_meta ||
      payload.router_meta ||
      payload.debug?.router ||
      payload.debug?.route ||
      payload.meta?.router ||
      payload.meta?.route ||
      null;

    if (direct && typeof direct === "object") {
      return direct;
    }

    const hasFlatRouterFields =
      payload.mode ||
      payload.intent ||
      payload.reason ||
      payload.memory_hits ||
      payload.memory_used ||
      payload.route_time_ms;

    if (hasFlatRouterFields) {
      return payload;
    }

    return null;
  }

  function numberOrNull(value) {
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && value.trim() !== "") {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
    return null;
  }

  function formatMs(value) {
    const ms = numberOrNull(value);
    if (ms === null) return "—";
    if (ms < 1000) return `${Math.round(ms)} ms`;
    return `${(ms / 1000).toFixed(2)} s`;
  }

  function getMemoryHits(meta) {
    const candidates = [
      meta.memory_hits,
      meta.memoryHits,
      meta.memory_hit_count,
      meta.memoryHitCount,
      meta.memory_count,
      meta.memoryCount,
    ];

    for (const value of candidates) {
      const num = numberOrNull(value);
      if (num !== null) return String(num);
    }

    const used = getMemoryUsed(meta);
    if (used.length) return String(used.length);

    return "0";
  }

  function getMemoryUsed(meta) {
    const candidates = [
      meta.memory_used,
      meta.memoryUsed,
      meta.memories_used,
      meta.memoriesUsed,
      meta.memory,
      meta.memories,
      meta.context_used,
      meta.contextUsed,
    ];

    for (const value of candidates) {
      const arr = normalizeArray(value);
      if (arr.length) return arr;
    }

    return [];
  }

  function getReason(meta) {
    return (
      meta.reason ||
      meta.route_reason ||
      meta.routeReason ||
      meta.explanation ||
      meta.why ||
      "—"
    );
  }

  function getMode(meta) {
    return (
      meta.mode ||
      meta.route_mode ||
      meta.routeMode ||
      meta.type ||
      "—"
    );
  }

  function getIntent(meta) {
    return (
      meta.intent ||
      meta.route_intent ||
      meta.routeIntent ||
      meta.task ||
      "—"
    );
  }

  function getTime(meta) {
    return (
      meta.route_time_ms ??
      meta.routeTimeMs ??
      meta.routing_time_ms ??
      meta.routingTimeMs ??
      meta.time_ms ??
      meta.timeMs ??
      null
    );
  }

  function buildMemoryUsedHtml(memoryUsed) {
    if (!memoryUsed.length) {
      return `<div class="router-debug-empty">—</div>`;
    }

    return `
      <div class="router-memory-list">
        ${memoryUsed
          .map(
            (item) =>
              `<div class="router-memory-item">${escapeHtml(String(item))}</div>`
          )
          .join("")}
      </div>
    `;
  }

  function renderRouter(meta) {
    const container = getRouterContainer();
    if (!container) return;

    if (!meta) {
      container.innerHTML = `
        <div class="router-debug-row"><strong>Mode:</strong> —</div>
        <div class="router-debug-row"><strong>Intent:</strong> —</div>
        <div class="router-debug-row"><strong>Reason:</strong> —</div>
        <div class="router-debug-row"><strong>Memory Hits:</strong> —</div>
        <div class="router-debug-row"><strong>Time:</strong> —</div>
        <div class="router-debug-row"><strong>Memory Used:</strong><div class="router-debug-empty">—</div></div>
      `;
      return;
    }

    const mode = toTitleCase(getMode(meta));
    const intent = safeText(getIntent(meta));
    const reason = safeText(getReason(meta));
    const memoryHits = getMemoryHits(meta);
    const time = formatMs(getTime(meta));
    const memoryUsed = getMemoryUsed(meta);

    container.innerHTML = `
      <div class="router-debug-row"><strong>Mode:</strong> ${escapeHtml(mode)}</div>
      <div class="router-debug-row"><strong>Intent:</strong> ${escapeHtml(intent)}</div>
      <div class="router-debug-row"><strong>Reason:</strong> ${escapeHtml(reason)}</div>
      <div class="router-debug-row"><strong>Memory Hits:</strong> ${escapeHtml(memoryHits)}</div>
      <div class="router-debug-row"><strong>Time:</strong> ${escapeHtml(time)}</div>
      <div class="router-debug-row">
        <strong>Memory Used:</strong>
        ${buildMemoryUsedHtml(memoryUsed)}
      </div>
    `;
  }

  function signatureForMeta(meta) {
    try {
      return JSON.stringify({
        mode: getMode(meta),
        intent: getIntent(meta),
        reason: getReason(meta),
        memoryHits: getMemoryHits(meta),
        memoryUsed: getMemoryUsed(meta),
        time: getTime(meta),
      });
    } catch {
      return String(Date.now());
    }
  }

  function applyRouterMeta(meta) {
    if (!meta) return;

    const sig = signatureForMeta(meta);
    if (sig === state.lastSignature) return;

    state.lastSignature = sig;
    window.__novaLastRouterMeta = meta;
    renderRouter(meta);
  }

  function tryReadFromWindowState() {
    const candidates = [
      window.__novaLastRouterMeta,
      window.__novaRouterMeta,
      window.__lastRouterMeta,
      window.__routerMeta,
      window.NOVA_LAST_ROUTER_META,
    ];

    for (const item of candidates) {
      if (item && typeof item === "object") {
        applyRouterMeta(item);
        return true;
      }
    }

    return false;
  }

  function tryReadFromAppState() {
    const candidates = [
      window.novaState,
      window.__novaState,
      window.appState,
      window.__appState,
    ];

    for (const stateObj of candidates) {
      if (!stateObj || typeof stateObj !== "object") continue;

      const meta = pickRouterMeta(stateObj);
      if (meta) {
        applyRouterMeta(meta);
        return true;
      }
    }

    return false;
  }

  async function tryReadFromApiState() {
    try {
      const response = await fetch("/api/state", {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
        cache: "no-store",
      });

      if (!response.ok) return false;

      const payload = await response.json();
      const meta = pickRouterMeta(payload);
      if (!meta) return false;

      applyRouterMeta(meta);
      return true;
    } catch {
      return false;
    }
  }

  function installFetchTap() {
    if (window.__novaBrainFetchTapInstalled) return;
    window.__novaBrainFetchTapInstalled = true;

    const originalFetch = window.fetch;
    if (typeof originalFetch !== "function") return;

    window.fetch = async function (...args) {
      const response = await originalFetch.apply(this, args);

      try {
        const url = typeof args[0] === "string"
          ? args[0]
          : args[0]?.url || "";

        const shouldInspect =
          url.includes("/api/chat") ||
          url.includes("/api/state") ||
          url.includes("/api/message") ||
          url.includes("/chat");

        if (!shouldInspect) {
          return response;
        }

        const cloned = response.clone();
        const contentType = cloned.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
          const data = await cloned.json();
          const meta = pickRouterMeta(data);
          if (meta) applyRouterMeta(meta);
        } else if (
          contentType.includes("text/plain") ||
          contentType.includes("text/event-stream")
        ) {
          const text = await cloned.text();
          const meta = extractRouterMetaFromText(text);
          if (meta) applyRouterMeta(meta);
        }
      } catch (error) {
        console.debug("Brain router panel fetch tap skipped:", error);
      }

      return response;
    };
  }

  function extractRouterMetaFromText(text) {
    if (!text || typeof text !== "string") return null;

    const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);

    for (let i = lines.length - 1; i >= 0; i -= 1) {
      const line = lines[i];

      if (line.startsWith("data:")) {
        const raw = line.slice(5).trim();
        if (!raw || raw === "[DONE]") continue;

        try {
          const parsed = JSON.parse(raw);
          const meta = pickRouterMeta(parsed);
          if (meta) return meta;
        } catch {
          // ignore bad chunk
        }
      } else {
        try {
          const parsed = JSON.parse(line);
          const meta = pickRouterMeta(parsed);
          if (meta) return meta;
        } catch {
          // ignore bad chunk
        }
      }
    }

    return null;
  }

  function installXhrTap() {
    if (window.__novaBrainXhrTapInstalled) return;
    window.__novaBrainXhrTapInstalled = true;

    const OriginalXHR = window.XMLHttpRequest;
    if (!OriginalXHR) return;

    const originalOpen = OriginalXHR.prototype.open;
    const originalSend = OriginalXHR.prototype.send;

    OriginalXHR.prototype.open = function (method, url, ...rest) {
      this.__novaUrl = url;
      return originalOpen.call(this, method, url, ...rest);
    };

    OriginalXHR.prototype.send = function (...args) {
      this.addEventListener("load", function () {
        try {
          const url = String(this.__novaUrl || "");
          if (
            !url.includes("/api/chat") &&
            !url.includes("/api/state") &&
            !url.includes("/api/message") &&
            !url.includes("/chat")
          ) {
            return;
          }

          const contentType = this.getResponseHeader("content-type") || "";
          if (!this.responseText) return;

          if (
            contentType.includes("application/json") ||
            contentType.includes("text/plain") ||
            contentType.includes("text/event-stream")
          ) {
            const meta =
              extractRouterMetaFromText(this.responseText) ||
              pickRouterMeta(JSON.parseSafe?.(this.responseText));

            if (meta) applyRouterMeta(meta);
          }
        } catch (error) {
          console.debug("Brain router panel xhr tap skipped:", error);
        }
      });

      return originalSend.apply(this, args);
    };
  }

  function installJsonParseSafe() {
    if (JSON.parseSafe) return;
    JSON.parseSafe = function (value) {
      try {
        return JSON.parse(value);
      } catch {
        return null;
      }
    };
  }

  function startPollingFallback() {
    if (state.pollTimer) return;

    state.pollTimer = setInterval(async () => {
      const gotWindow = tryReadFromWindowState();
      const gotApp = tryReadFromAppState();

      if (gotWindow || gotApp) return;
      await tryReadFromApiState();
    }, 1500);
  }

  function init() {
    installJsonParseSafe();
    installFetchTap();
    installXhrTap();
    renderRouter(window.__novaLastRouterMeta || null);

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

    window.addEventListener("nova:router-meta", (event) => {
      const meta = event?.detail;
      if (meta && typeof meta === "object") {
        applyRouterMeta(meta);
      }
    });

    console.log("Nova brain router panel loaded");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();