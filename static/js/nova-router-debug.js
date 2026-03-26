(() => {
  "use strict";

  if (window.__novaRouterDebugLoaded) return;
  window.__novaRouterDebugLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.debug = Nova.debug || {};
  Nova.state = Nova.state || {};
  Nova.dom = Nova.dom || {};

  const state = Nova.state;
  const dom = Nova.dom;

  const byId = dom.byId || ((id) => document.getElementById(id));
  const qs = dom.qs || ((sel, root = document) => root.querySelector(sel));

  function safeText(value) {
    if (Nova.utils && typeof Nova.utils.safeText === "function") {
      return Nova.utils.safeText(value);
    }
    return String(value ?? "").trim();
  }

  function escapeHtml(value) {
    if (Nova.utils && typeof Nova.utils.escapeHtml === "function") {
      return Nova.utils.escapeHtml(value);
    }

    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function getPanelRoot() {
    return (
      byId("routerDebugPanel") ||
      byId("routerControlRoot") ||
      byId("routerPanel") ||
      qs("[data-router-debug]") ||
      qs("[data-router-control]") ||
      qs(".router-debug-panel") ||
      qs(".router-control-panel")
    );
  }

  function getModeEl(root = getPanelRoot()) {
    return (
      root?.querySelector("[data-router-mode]") ||
      byId("routerMode") ||
      qs(".router-mode", root)
    );
  }

  function getReasonEl(root = getPanelRoot()) {
    return (
      root?.querySelector("[data-router-reason]") ||
      byId("routerReason") ||
      qs(".router-reason", root)
    );
  }

  function getToolsEl(root = getPanelRoot()) {
    return (
      root?.querySelector("[data-router-tools]") ||
      byId("routerTools") ||
      qs(".router-tools", root)
    );
  }

  function getMemoryEl(root = getPanelRoot()) {
    return (
      root?.querySelector("[data-router-memory]") ||
      byId("routerMemory") ||
      qs(".router-memory", root)
    );
  }

  function getWebEl(root = getPanelRoot()) {
    return (
      root?.querySelector("[data-router-web]") ||
      byId("routerWeb") ||
      qs(".router-web", root)
    );
  }

  function getRawEl(root = getPanelRoot()) {
    return (
      root?.querySelector("[data-router-raw]") ||
      byId("routerRaw") ||
      qs(".router-raw", root)
    );
  }

  function getStatusEl(root = getPanelRoot()) {
    return (
      root?.querySelector("[data-router-status]") ||
      byId("routerDebugStatus") ||
      qs(".router-debug-status", root)
    );
  }

  function getBadgeEl(root = getPanelRoot()) {
    return (
      root?.querySelector("[data-router-badge]") ||
      byId("routerDebugBadge") ||
      qs(".router-debug-badge", root)
    );
  }

  function asArray(value) {
    if (Array.isArray(value)) return value;
    if (value === null || value === undefined || value === "") return [];
    return [value];
  }

  function dedupeCleanStrings(values) {
    return [...new Set(asArray(values).map((item) => safeText(item)).filter(Boolean))];
  }

  function yesNoUnknown(
    value,
    { trueLabel = "Yes", falseLabel = "No", unknownLabel = "Unknown" } = {}
  ) {
    if (value === true) return trueLabel;
    if (value === false) return falseLabel;
    return unknownLabel;
  }

  function pickFirstText(...values) {
    for (const value of values) {
      const text = safeText(value);
      if (text) return text;
    }
    return "";
  }

  function normalizeRouterMeta(meta) {
    if (!meta || typeof meta !== "object") return null;

    const mode = pickFirstText(
      meta.mode,
      meta.intent,
      meta.route,
      meta.selected_mode,
      meta.selectedMode
    ).toLowerCase();

    const reason = pickFirstText(
      meta.reason,
      meta.summary,
      meta.explanation,
      meta.why,
      meta.selected_reason,
      meta.selectedReason
    );

    const tools = dedupeCleanStrings(
      meta.tools ??
        meta.selected_tools ??
        meta.selectedTools ??
        meta.tool_calls ??
        meta.toolCalls
    );

    const memory = dedupeCleanStrings(
      meta.memory_hits ??
        meta.memory_used ??
        meta.memoryUsed ??
        meta.memories ??
        meta.memory
    );

    const webValue =
      typeof meta.web_used === "boolean"
        ? meta.web_used
        : typeof meta.webUsed === "boolean"
        ? meta.webUsed
        : typeof meta.used_web === "boolean"
        ? meta.used_web
        : typeof meta.usedWeb === "boolean"
        ? meta.usedWeb
        : null;

    const webQuery = pickFirstText(
      meta.web_query,
      meta.webQuery,
      meta.search_query,
      meta.searchQuery
    );

    const confidenceRaw =
      meta.confidence ??
      meta.score ??
      meta.route_score ??
      meta.routeScore ??
      null;

    const confidence =
      typeof confidenceRaw === "number"
        ? confidenceRaw
        : !Number.isNaN(Number(confidenceRaw))
        ? Number(confidenceRaw)
        : null;

    const raw = meta;

    return {
      mode: mode || "",
      reason,
      tools,
      memory,
      web_used: webValue,
      web_query: webQuery,
      confidence,
      raw,
    };
  }

  function formatConfidence(value) {
    if (typeof value !== "number" || Number.isNaN(value)) return "";
    if (value >= 0 && value <= 1) return `${Math.round(value * 100)}%`;
    return String(Math.round(value));
  }

  function buildChip(text, extraClass = "") {
    const label = safeText(text);
    if (!label) return "";
    return `<span class="router-debug-chip${extraClass ? ` ${extraClass}` : ""}">${escapeHtml(label)}</span>`;
  }

  function buildToolChips(tools) {
    const values = dedupeCleanStrings(tools);
    if (!values.length) return `<span class="router-debug-empty">None</span>`;
    return values.map((tool) => buildChip(tool, " is-tool")).join("");
  }

  function buildMemoryChips(memory) {
    const values = dedupeCleanStrings(memory);
    if (!values.length) return `<span class="router-debug-empty">None</span>`;
    return values.map((item) => buildChip(item, " is-memory")).join("");
  }

  function buildFallbackPanel(root) {
    if (!root) return;

    root.innerHTML = `
      <div class="router-debug-shell">
        <div class="router-debug-top">
          <div class="router-debug-hero">
            <div class="router-debug-hero-main">
              <div class="router-debug-title-row">
                <div class="router-debug-title-wrap">
                  <div class="router-debug-kicker">Nova internal</div>
                  <div class="router-debug-title">Router Debug</div>
                </div>
                <div class="router-debug-badge" data-router-badge>Idle</div>
              </div>
              <div class="router-debug-status" data-router-status>Waiting for route data...</div>
            </div>
          </div>
        </div>

        <div class="router-debug-grid">
          <div class="router-debug-card router-debug-card-mode">
            <div class="router-debug-label">Mode</div>
            <div class="router-debug-value router-debug-mode-value" data-router-mode>—</div>
          </div>

          <div class="router-debug-card router-debug-card-web">
            <div class="router-debug-label">Web</div>
            <div class="router-debug-value router-debug-web-value" data-router-web>Unknown</div>
          </div>

          <div class="router-debug-card router-debug-card-wide">
            <div class="router-debug-label">Reason</div>
            <div class="router-debug-value router-debug-reason-value" data-router-reason>No route chosen yet.</div>
          </div>

          <div class="router-debug-card router-debug-card-wide">
            <div class="router-debug-label">Tools</div>
            <div class="router-debug-value router-debug-chip-row" data-router-tools>
              <span class="router-debug-empty">None</span>
            </div>
          </div>

          <div class="router-debug-card router-debug-card-wide">
            <div class="router-debug-label">Memory</div>
            <div class="router-debug-value router-debug-chip-row" data-router-memory>
              <span class="router-debug-empty">None</span>
            </div>
          </div>

          <div class="router-debug-card router-debug-card-wide">
            <div class="router-debug-label">Raw</div>
            <pre class="router-debug-raw" data-router-raw>{}</pre>
          </div>
        </div>
      </div>
    `;
  }

  function ensurePanelMarkup() {
    const root = getPanelRoot();
    if (!root) {
      console.warn("Nova router debug: root not found, standing by.");
      return null;
    }

    if (!root.querySelector("[data-router-mode]")) {
      buildFallbackPanel(root);
    }

    root.hidden = false;
    root.classList.add("nova-router-debug-ready");

    return root;
  }

  function ensureStyles() {
    if (document.getElementById("nova-router-debug-styles")) return;

    const style = document.createElement("style");
    style.id = "nova-router-debug-styles";
    style.textContent = `
.router-debug-shell {
  display: grid;
  gap: 14px;
}

.router-debug-top {
  display: grid;
  gap: 10px;
}

.router-debug-hero {
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background:
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.10), transparent 42%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.03));
  border-radius: 20px;
  padding: 16px 16px 14px;
  box-shadow:
    0 18px 36px rgba(0, 0, 0, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  overflow: hidden;
}

.router-debug-hero::after {
  content: "";
  position: absolute;
  inset: auto -40px -40px auto;
  width: 120px;
  height: 120px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  filter: blur(2px);
  pointer-events: none;
}

.router-debug-hero-main {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 8px;
}

.router-debug-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.router-debug-title-wrap {
  min-width: 0;
}

.router-debug-kicker {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.62;
  margin-bottom: 4px;
}

.router-debug-title {
  font-size: 18px;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.01em;
}

.router-debug-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(255, 255, 255, 0.09);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.router-debug-status {
  font-size: 12px;
  line-height: 1.45;
  opacity: 0.76;
}

.router-debug-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.router-debug-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.045), rgba(255, 255, 255, 0.03));
  border-radius: 18px;
  padding: 13px 13px 12px;
  box-shadow:
    0 10px 24px rgba(0, 0, 0, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.03);
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    background 0.18s ease,
    box-shadow 0.18s ease;
}

.router-debug-card:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.12);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.055), rgba(255, 255, 255, 0.035));
  box-shadow:
    0 14px 28px rgba(0, 0, 0, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.035);
}

.router-debug-card-wide {
  grid-column: 1 / -1;
}

.router-debug-label {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.62;
  margin-bottom: 8px;
}

.router-debug-value {
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}

.router-debug-mode-value,
.router-debug-web-value {
  font-size: 15px;
  font-weight: 700;
  line-height: 1.3;
}

.router-debug-reason-value {
  font-size: 13px;
  line-height: 1.6;
  opacity: 0.95;
}

.router-debug-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.router-debug-chip {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 11px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.07);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.router-debug-chip.is-tool {
  background: rgba(255, 255, 255, 0.07);
}

.router-debug-chip.is-memory {
  background: rgba(255, 255, 255, 0.12);
}

.router-debug-empty {
  opacity: 0.58;
  font-size: 12px;
}

.router-debug-raw {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.5;
  border-radius: 14px;
  padding: 12px;
  background:
    linear-gradient(180deg, rgba(0, 0, 0, 0.22), rgba(0, 0, 0, 0.14));
  border: 1px solid rgba(255, 255, 255, 0.06);
  max-height: 260px;
  overflow: auto;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
}

.router-debug-raw::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

.router-debug-raw::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 999px;
}

.router-debug-raw::-webkit-scrollbar-track {
  background: transparent;
}

@media (max-width: 720px) {
  .router-debug-title-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .router-debug-grid {
    grid-template-columns: 1fr;
  }

  .router-debug-card-wide {
    grid-column: auto;
  }

  .router-debug-title {
    font-size: 16px;
  }
}
    `.trim();

    document.head.appendChild(style);
  }

  function updateRouterDebug(meta) {
    const root = ensurePanelMarkup();
    if (!root) return null;

    ensureStyles();

    const normalized = normalizeRouterMeta(meta);

    const modeEl = getModeEl(root);
    const reasonEl = getReasonEl(root);
    const toolsEl = getToolsEl(root);
    const memoryEl = getMemoryEl(root);
    const webEl = getWebEl(root);
    const rawEl = getRawEl(root);
    const statusEl = getStatusEl(root);
    const badgeEl = getBadgeEl(root);

    if (!normalized) {
      if (modeEl) modeEl.textContent = "—";
      if (reasonEl) reasonEl.textContent = "No route chosen yet.";
      if (toolsEl) toolsEl.innerHTML = `<span class="router-debug-empty">None</span>`;
      if (memoryEl) memoryEl.innerHTML = `<span class="router-debug-empty">None</span>`;
      if (webEl) webEl.textContent = "Unknown";
      if (rawEl) rawEl.textContent = "{}";
      if (statusEl) statusEl.textContent = "Waiting for route data...";
      if (badgeEl) badgeEl.textContent = "Idle";
      return null;
    }

    const modeText = safeText(normalized.mode || "general") || "general";
    const reasonText = safeText(normalized.reason || "No reason provided.");
    const toolsHtml = buildToolChips(normalized.tools);
    const memoryHtml = buildMemoryChips(normalized.memory);

    let webText = yesNoUnknown(normalized.web_used);
    if (normalized.web_query) {
      webText =
        normalized.web_used === true
          ? `Yes • ${normalized.web_query}`
          : normalized.web_used === false
          ? `No • ${normalized.web_query}`
          : normalized.web_query;
    }

    let statusText = `Mode selected: ${modeText}`;
    const confidenceText = formatConfidence(normalized.confidence);
    if (confidenceText) {
      statusText += ` • confidence ${confidenceText}`;
    }

    if (modeEl) modeEl.textContent = modeText;
    if (reasonEl) reasonEl.textContent = reasonText;
    if (toolsEl) toolsEl.innerHTML = toolsHtml;
    if (memoryEl) memoryEl.innerHTML = memoryHtml;
    if (webEl) webEl.textContent = webText;
    if (rawEl) rawEl.textContent = JSON.stringify(normalized.raw, null, 2);
    if (statusEl) statusEl.textContent = statusText;
    if (badgeEl) badgeEl.textContent = modeText;

    return normalized;
  }

  function applyIncomingRouterMeta(meta) {
    const normalized = normalizeRouterMeta(meta);
    if (!normalized) return null;

    state.lastRouter = normalized;
    updateRouterDebug(normalized);
    return normalized;
  }

  function initRouterDebug() {
    const root = ensurePanelMarkup();
    if (!root) return;

    ensureStyles();

    if (state.lastRouter) {
      updateRouterDebug(state.lastRouter);
      return;
    }

    const lastFromMessages = [...(Array.isArray(state.messages) ? state.messages : [])]
      .reverse()
      .find((msg) => msg && msg.router);

    if (lastFromMessages?.router) {
      applyIncomingRouterMeta(lastFromMessages.router);
      return;
    }

    updateRouterDebug(null);
  }

  document.addEventListener("DOMContentLoaded", () => {
    initRouterDebug();
  });

  Nova.debug = {
    ...Nova.debug,
    normalizeRouterMeta,
    updateRouterDebug,
    applyIncomingRouterMeta,
    initRouterDebug,
  };
})();