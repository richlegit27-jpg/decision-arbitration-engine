(() => {
  "use strict";

  if (window.__novaSourcesPanelLoaded) return;
  window.__novaSourcesPanelLoaded = true;

  const STATE = {
    sources: [],
    sessionId: "",
    lastUpdatedAt: 0,
    drawerOpen: false,
    wiredFetch: false,
    wiredXhr: false,
    originalFetch: window.fetch ? window.fetch.bind(window) : null
  };

  function sanitizeText(value) {
    return String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  }

  function escapeHtml(value) {
    return sanitizeText(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function isHttpUrl(value) {
    try {
      const url = new URL(String(value || ""));
      return url.protocol === "http:" || url.protocol === "https:";
    } catch (_) {
      return false;
    }
  }

  function sourceKey(item) {
    const title = sanitizeText(item?.title || "");
    const url = sanitizeText(item?.url || "");
    return `${title}__${url}`.toLowerCase();
  }

  function dedupeSources(sources) {
    const out = [];
    const seen = new Set();

    for (const item of Array.isArray(sources) ? sources : []) {
      const title = sanitizeText(item?.title || "");
      const url = sanitizeText(item?.url || "");
      const snippet = sanitizeText(item?.snippet || "");
      if (!title && !url && !snippet) continue;

      const normalized = { title, url, snippet };
      const key = sourceKey(normalized);
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(normalized);
    }

    return out.slice(0, 12);
  }

  function domainFromUrl(value) {
    try {
      return new URL(value).hostname.replace(/^www\./i, "");
    } catch (_) {
      return "";
    }
  }

  function ensureRoot() {
    let fab = document.getElementById("novaSourcesFab");
    let drawer = document.getElementById("novaSourcesDrawer");
    let toast = document.getElementById("novaSourcesToast");

    if (!fab) {
      fab = document.createElement("button");
      fab.id = "novaSourcesFab";
      fab.type = "button";
      fab.className = "nova-sources-fab";
      fab.hidden = true;
      fab.setAttribute("aria-label", "Open sources");
      fab.innerHTML = `
        <span>Sources</span>
        <span id="novaSourcesFabBadge" class="nova-sources-badge">0</span>
      `;
      document.body.appendChild(fab);
    }

    if (!drawer) {
      drawer = document.createElement("aside");
      drawer.id = "novaSourcesDrawer";
      drawer.className = "nova-sources-drawer";
      drawer.setAttribute("aria-hidden", "true");
      drawer.innerHTML = `
        <div class="nova-sources-header">
          <div class="nova-sources-title-wrap">
            <h3 class="nova-sources-title">Web sources</h3>
            <div id="novaSourcesSubtitle" class="nova-sources-subtitle">No sources yet</div>
          </div>
          <div class="nova-sources-actions">
            <button id="novaSourcesCopyBtn" class="nova-sources-icon-btn" type="button" aria-label="Copy sources">⧉</button>
            <button id="novaSourcesCloseBtn" class="nova-sources-icon-btn" type="button" aria-label="Close sources">✕</button>
          </div>
        </div>
        <div id="novaSourcesBody" class="nova-sources-body">
          <div class="nova-sources-empty">No sources yet. When Nova uses web mode, sources will appear here.</div>
        </div>
      `;
      document.body.appendChild(drawer);
    }

    if (!toast) {
      toast = document.createElement("div");
      toast.id = "novaSourcesToast";
      toast.className = "nova-sources-toast";
      toast.setAttribute("aria-live", "polite");
      document.body.appendChild(toast);
    }

    return { fab, drawer, toast };
  }

  function formatSubtitle() {
    const count = STATE.sources.length;
    if (!count) return "No sources yet";

    const updated = STATE.lastUpdatedAt
      ? new Date(STATE.lastUpdatedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
      : "just now";

    return `${count} source${count === 1 ? "" : "s"} • updated ${updated}`;
  }

  function buildSourceCard(item) {
    const safeTitle = escapeHtml(item.title || domainFromUrl(item.url) || "Untitled source");
    const safeUrl = escapeHtml(item.url || "");
    const safeSnippet = escapeHtml(item.snippet || "");
    const domain = escapeHtml(domainFromUrl(item.url || ""));

    const urlLine = safeUrl
      ? `<div class="nova-source-url">${domain || safeUrl}</div>`
      : "";

    const snippetLine = safeSnippet
      ? `<div class="nova-source-snippet">${safeSnippet}</div>`
      : "";

    if (isHttpUrl(item.url)) {
      return `
        <a class="nova-source-card" href="${safeUrl}" target="_blank" rel="noopener noreferrer">
          <div class="nova-source-row">
            <h4 class="nova-source-title">${safeTitle}</h4>
            <span class="nova-source-external">↗</span>
          </div>
          ${urlLine}
          ${snippetLine}
        </a>
      `;
    }

    return `
      <div class="nova-source-card">
        <div class="nova-source-row">
          <h4 class="nova-source-title">${safeTitle}</h4>
          <span class="nova-source-external">•</span>
        </div>
        ${urlLine}
        ${snippetLine}
      </div>
    `;
  }

  function render() {
    const { fab, drawer } = ensureRoot();
    const badge = document.getElementById("novaSourcesFabBadge");
    const body = document.getElementById("novaSourcesBody");
    const subtitle = document.getElementById("novaSourcesSubtitle");

    if (!badge || !body || !subtitle) return;

    badge.textContent = String(STATE.sources.length);
    subtitle.textContent = formatSubtitle();

    fab.hidden = STATE.sources.length === 0;

    if (!STATE.sources.length) {
      body.innerHTML = `<div class="nova-sources-empty">No sources yet. When Nova uses web mode, sources will appear here.</div>`;
    } else {
      body.innerHTML = STATE.sources.map(buildSourceCard).join("");
    }

    drawer.classList.toggle("is-open", STATE.drawerOpen);
    drawer.setAttribute("aria-hidden", STATE.drawerOpen ? "false" : "true");
  }

  function openDrawer() {
    STATE.drawerOpen = true;
    render();
  }

  function closeDrawer() {
    STATE.drawerOpen = false;
    render();
  }

  function showToast(message) {
    const toast = ensureRoot().toast;
    toast.textContent = sanitizeText(message || "");
    toast.classList.add("is-visible");
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => {
      toast.classList.remove("is-visible");
    }, 1800);
  }

  async function copySources() {
    if (!STATE.sources.length) {
      showToast("No sources to copy.");
      return;
    }

    const lines = STATE.sources.map((item, index) => {
      const parts = [
        `${index + 1}. ${sanitizeText(item.title || "Untitled source")}`,
        sanitizeText(item.url || ""),
        sanitizeText(item.snippet || "")
      ].filter(Boolean);
      return parts.join("\n");
    });

    const payload = lines.join("\n\n");
    try {
      await navigator.clipboard.writeText(payload);
      showToast("Sources copied.");
    } catch (_) {
      showToast("Clipboard failed.");
    }
  }

  function applySources(sources, sessionId = "") {
    const deduped = dedupeSources(sources);
    STATE.sources = deduped;
    STATE.sessionId = sanitizeText(sessionId || STATE.sessionId);
    STATE.lastUpdatedAt = Date.now();

    if (deduped.length) {
      window.__novaLastSources = deduped;
      window.dispatchEvent(
        new CustomEvent("nova:sources-updated", {
          detail: {
            sources: deduped,
            session_id: STATE.sessionId,
            updated_at: STATE.lastUpdatedAt
          }
        })
      );
    }

    render();
  }

  function absorbJsonPayload(payload) {
    if (!payload || typeof payload !== "object") return;

    if (Array.isArray(payload.sources)) {
      applySources(payload.sources, payload.session_id || payload.sessionId || "");
    }

    if (payload.type === "meta" && Array.isArray(payload.sources)) {
      applySources(payload.sources, payload.session_id || "");
    }

    if (payload.type === "done" && Array.isArray(payload.sources)) {
      applySources(payload.sources, payload.session_id || "");
    }

    if (payload.message && Array.isArray(payload.message.sources)) {
      applySources(payload.message.sources, payload.session_id || "");
    }
  }

  function parseSseAndAbsorb(text) {
    const chunks = String(text || "").split(/\n\n+/);
    for (const chunk of chunks) {
      const lines = chunk.split("\n");
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const raw = line.slice(5).trim();
        if (!raw || raw === "[DONE]") continue;
        try {
          const payload = JSON.parse(raw);
          absorbJsonPayload(payload);
        } catch (_) {
          // ignore non-json frames
        }
      }
    }
  }

  function hookFetch() {
    if (STATE.wiredFetch || typeof STATE.originalFetch !== "function") return;
    STATE.wiredFetch = true;

    window.fetch = async function (...args) {
      const response = await STATE.originalFetch(...args);

      try {
        const input = args[0];
        const url = typeof input === "string" ? input : input?.url || "";
        if (!/\/api\/chat(?:\/stream)?(?:\?|$)/.test(String(url))) {
          return response;
        }

        const contentType = String(response.headers.get("content-type") || "").toLowerCase();

        if (contentType.includes("application/json")) {
          const clone = response.clone();
          clone.json().then(absorbJsonPayload).catch(() => {});
          return response;
        }

        if (contentType.includes("text/event-stream")) {
          const clone = response.clone();
          clone.text().then(parseSseAndAbsorb).catch(() => {});
          return response;
        }
      } catch (_) {
        // swallow
      }

      return response;
    };
  }

  function hookXhr() {
    if (STATE.wiredXhr || typeof XMLHttpRequest === "undefined") return;
    STATE.wiredXhr = true;

    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function (method, url, ...rest) {
      this.__novaTrackedUrl = String(url || "");
      return originalOpen.call(this, method, url, ...rest);
    };

    XMLHttpRequest.prototype.send = function (...args) {
      this.addEventListener("load", function () {
        try {
          if (!/\/api\/chat(?:\/stream)?(?:\?|$)/.test(String(this.__novaTrackedUrl || ""))) {
            return;
          }

          const contentType = String(this.getResponseHeader("content-type") || "").toLowerCase();
          if (contentType.includes("application/json")) {
            absorbJsonPayload(JSON.parse(this.responseText || "{}"));
            return;
          }

          if (contentType.includes("text/event-stream")) {
            parseSseAndAbsorb(this.responseText || "");
          }
        } catch (_) {
          // swallow
        }
      });

      return originalSend.apply(this, args);
    };
  }

  function wireUi() {
    const { fab, drawer } = ensureRoot();
    const closeBtn = document.getElementById("novaSourcesCloseBtn");
    const copyBtn = document.getElementById("novaSourcesCopyBtn");

    fab.addEventListener("click", () => {
      STATE.drawerOpen = !STATE.drawerOpen;
      render();
    });

    if (closeBtn) {
      closeBtn.addEventListener("click", closeDrawer);
    }

    if (copyBtn) {
      copyBtn.addEventListener("click", copySources);
    }

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && STATE.drawerOpen) {
        closeDrawer();
      }
    });

    document.addEventListener("click", (event) => {
      if (!STATE.drawerOpen) return;
      const target = event.target;
      if (!(target instanceof Element)) return;

      if (target.closest("#novaSourcesDrawer")) return;
      if (target.closest("#novaSourcesFab")) return;

      closeDrawer();
    });

    drawer.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const card = target.closest(".nova-source-card");
      if (!card) return;
    });
  }

  function bootFromWindowState() {
    if (Array.isArray(window.__novaLastSources)) {
      applySources(window.__novaLastSources, "");
    }
  }

  function init() {
    ensureRoot();
    wireUi();
    bootFromWindowState();
    hookFetch();
    hookXhr();
    render();
    console.log("Nova sources panel loaded");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();