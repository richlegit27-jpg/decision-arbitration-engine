(function () {
  "use strict";

  const VERSION = "brain-debug-2026-04-13-001";
  const POLL_MS = 2500;

  const state = {
    booted: false,
    polling: null,
    lastStatePayload: null,
    lastAssistantMessage: null,
    lastDebug: null,
    expanded: {
      summary: true,
      routing: true,
      memory: false,
      prompt: false,
      raw: false,
      logs: false,
    },
    logs: [],
  };

  const els = {
    root: null,
    panel: null,
    headerStatus: null,
    badgeMode: null,
    badgeConfidence: null,
    summaryBody: null,
    routingBody: null,
    memoryBody: null,
    promptBody: null,
    rawBody: null,
    logsBody: null,
    copyBtn: null,
    refreshBtn: null,
    collapseBtn: null,
  };

  function log(message, extra) {
    const stamp = new Date().toISOString();
    const line = `[NovaBrainDebug] [${stamp}] ${String(message || "")}`;
    console.log(line, extra || "");
    state.logs.unshift({
      at: stamp,
      text: String(message || ""),
      extra: extra || null,
    });
    state.logs = state.logs.slice(0, 50);
    renderLogs();
  }

  function q(sel, root) {
    return (root || document).querySelector(sel);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeObject(value) {
    return value && typeof value === "object" ? value : {};
  }

  function clamp(value, min, max) {
    const n = Number(value);
    if (!Number.isFinite(n)) return min;
    return Math.max(min, Math.min(max, n));
  }

  function formatNumber(value, digits) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "0";
    return n.toFixed(typeof digits === "number" ? digits : 2);
  }

  function formatBool(value) {
    return value ? "YES" : "NO";
  }

  function formatJson(value) {
    try {
      return JSON.stringify(value, null, 2);
    } catch (_) {
      return String(value);
    }
  }

  function scoreBar(score, maxScore) {
    const safeScore = Math.max(0, Number(score) || 0);
    const safeMax = Math.max(1, Number(maxScore) || 1);
    const pct = clamp((safeScore / safeMax) * 100, 0, 100);
    return `
      <div class="nova-brain-score-row">
        <div class="nova-brain-score-fill" style="width:${pct}%"></div>
      </div>
    `;
  }

  function buildStyles() {
    if (q("#nova-brain-debug-inline-style")) return;

    const style = document.createElement("style");
    style.id = "nova-brain-debug-inline-style";
    style.textContent = `
      .nova-brain-debug-root{
        position:fixed;
        right:16px;
        bottom:16px;
        width:420px;
        max-width:calc(100vw - 24px);
        max-height:calc(100vh - 24px);
        z-index:9999;
        font-family:Inter,Segoe UI,Arial,sans-serif;
        color:#e9eef8;
      }
      .nova-brain-debug-panel{
        display:flex;
        flex-direction:column;
        overflow:hidden;
        border:1px solid rgba(255,255,255,0.10);
        background:rgba(13,17,24,0.96);
        backdrop-filter:blur(10px);
        border-radius:16px;
        box-shadow:0 20px 50px rgba(0,0,0,0.35);
      }
      .nova-brain-debug-header{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        padding:12px 14px;
        border-bottom:1px solid rgba(255,255,255,0.08);
      }
      .nova-brain-debug-title{
        display:flex;
        flex-direction:column;
        gap:4px;
        min-width:0;
      }
      .nova-brain-debug-title strong{
        font-size:14px;
        line-height:1.2;
      }
      .nova-brain-debug-subtitle{
        font-size:11px;
        color:rgba(233,238,248,0.72);
      }
      .nova-brain-debug-actions{
        display:flex;
        gap:8px;
        align-items:center;
        flex-wrap:wrap;
        justify-content:flex-end;
      }
      .nova-brain-debug-btn{
        border:1px solid rgba(255,255,255,0.12);
        background:rgba(255,255,255,0.05);
        color:#f3f6fb;
        border-radius:10px;
        padding:6px 10px;
        font-size:11px;
        cursor:pointer;
      }
      .nova-brain-debug-btn:hover{
        background:rgba(255,255,255,0.09);
      }
      .nova-brain-debug-body{
        overflow:auto;
        padding:12px;
        display:flex;
        flex-direction:column;
        gap:10px;
      }
      .nova-brain-summary-strip{
        display:flex;
        gap:8px;
        flex-wrap:wrap;
      }
      .nova-brain-badge{
        display:inline-flex;
        align-items:center;
        gap:6px;
        font-size:11px;
        padding:6px 10px;
        border-radius:999px;
        border:1px solid rgba(255,255,255,0.09);
        background:rgba(255,255,255,0.04);
      }
      .nova-brain-badge.is-mode{
        border-color:rgba(115,196,255,0.30);
        background:rgba(65,132,255,0.16);
      }
      .nova-brain-badge.is-confidence{
        border-color:rgba(76,215,129,0.24);
        background:rgba(53,130,70,0.16);
      }
      .nova-brain-section{
        border:1px solid rgba(255,255,255,0.08);
        border-radius:14px;
        overflow:hidden;
        background:rgba(255,255,255,0.03);
      }
      .nova-brain-section-toggle{
        width:100%;
        text-align:left;
        background:transparent;
        border:none;
        color:#f3f6fb;
        cursor:pointer;
        padding:12px 14px;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:10px;
        font-size:13px;
      }
      .nova-brain-section-toggle:hover{
        background:rgba(255,255,255,0.04);
      }
      .nova-brain-section-meta{
        font-size:11px;
        color:rgba(233,238,248,0.68);
      }
      .nova-brain-section-body{
        padding:0 14px 14px 14px;
      }
      .nova-brain-grid{
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:8px;
      }
      .nova-brain-card{
        border:1px solid rgba(255,255,255,0.06);
        background:rgba(255,255,255,0.03);
        border-radius:12px;
        padding:10px;
      }
      .nova-brain-card-label{
        font-size:11px;
        color:rgba(233,238,248,0.68);
        margin-bottom:5px;
      }
      .nova-brain-card-value{
        font-size:13px;
        font-weight:600;
        word-break:break-word;
      }
      .nova-brain-score-list{
        display:flex;
        flex-direction:column;
        gap:8px;
      }
      .nova-brain-score-item{
        border:1px solid rgba(255,255,255,0.05);
        background:rgba(255,255,255,0.025);
        border-radius:12px;
        padding:10px;
      }
      .nova-brain-score-head{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:8px;
        margin-bottom:6px;
        font-size:12px;
      }
      .nova-brain-score-mode.is-winning{
        color:#7fd2ff;
        font-weight:700;
      }
      .nova-brain-score-value{
        color:rgba(233,238,248,0.78);
      }
      .nova-brain-score-row{
        width:100%;
        height:8px;
        background:rgba(255,255,255,0.06);
        border-radius:999px;
        overflow:hidden;
      }
      .nova-brain-score-fill{
        height:100%;
        border-radius:999px;
        background:linear-gradient(90deg, rgba(69,145,255,0.95), rgba(120,222,255,0.95));
      }
      .nova-brain-list{
        display:flex;
        flex-direction:column;
        gap:8px;
      }
      .nova-brain-list-item{
        border:1px solid rgba(255,255,255,0.05);
        border-radius:12px;
        padding:10px;
        background:rgba(255,255,255,0.025);
      }
      .nova-brain-list-item-title{
        font-size:12px;
        font-weight:600;
        margin-bottom:4px;
      }
      .nova-brain-list-item-sub{
        font-size:11px;
        color:rgba(233,238,248,0.66);
        margin-bottom:6px;
      }
      .nova-brain-list-item-text{
        font-size:12px;
        white-space:pre-wrap;
        word-break:break-word;
      }
      .nova-brain-pre{
        margin:0;
        white-space:pre-wrap;
        word-break:break-word;
        font-size:11px;
        line-height:1.45;
        color:#d9e4f6;
        background:rgba(0,0,0,0.22);
        border:1px solid rgba(255,255,255,0.05);
        border-radius:12px;
        padding:12px;
      }
      .nova-brain-empty{
        font-size:12px;
        color:rgba(233,238,248,0.68);
      }
      .nova-brain-mini-note{
        font-size:11px;
        color:rgba(233,238,248,0.68);
        margin-top:8px;
      }
      .nova-brain-log-line{
        font-size:11px;
        padding:8px 0;
        border-top:1px solid rgba(255,255,255,0.05);
      }
      .nova-brain-log-line:first-child{
        border-top:none;
        padding-top:0;
      }
      .nova-brain-log-time{
        color:rgba(233,238,248,0.55);
        display:block;
        margin-bottom:3px;
      }
      .nova-brain-hidden{
        display:none !important;
      }
    `;
    document.head.appendChild(style);
  }

  function sectionTemplate(key, title, meta) {
    const isOpen = !!state.expanded[key];
    return `
      <section class="nova-brain-section" data-brain-section="${escapeHtml(key)}">
        <button type="button" class="nova-brain-section-toggle" data-brain-toggle="${escapeHtml(key)}">
          <span>${escapeHtml(title)}</span>
          <span class="nova-brain-section-meta">${escapeHtml(meta || (isOpen ? "open" : "closed"))}</span>
        </button>
        <div class="nova-brain-section-body ${isOpen ? "" : "nova-brain-hidden"}" data-brain-body="${escapeHtml(key)}"></div>
      </section>
    `;
  }

  function ensureRoot() {
    if (els.root) return;

    buildStyles();

    const root = document.createElement("div");
    root.className = "nova-brain-debug-root";
    root.innerHTML = `
      <div class="nova-brain-debug-panel">
        <div class="nova-brain-debug-header">
          <div class="nova-brain-debug-title">
            <strong>Nova Brain Debug</strong>
            <div class="nova-brain-debug-subtitle" data-brain-status>Booting…</div>
          </div>
          <div class="nova-brain-debug-actions">
            <button type="button" class="nova-brain-debug-btn" data-brain-refresh>Refresh</button>
            <button type="button" class="nova-brain-debug-btn" data-brain-copy>Copy JSON</button>
            <button type="button" class="nova-brain-debug-btn" data-brain-collapse>Collapse All</button>
          </div>
        </div>
        <div class="nova-brain-debug-body">
          <div class="nova-brain-summary-strip">
            <span class="nova-brain-badge is-mode" data-brain-badge-mode>MODE: --</span>
            <span class="nova-brain-badge is-confidence" data-brain-badge-confidence>CONF: --</span>
          </div>

          ${sectionTemplate("summary", "Summary", "core decision")}
          ${sectionTemplate("routing", "Routing Scores", "winning mode + score bars")}
          ${sectionTemplate("memory", "Memory", "selected context")}
          ${sectionTemplate("prompt", "Prompt Builder", "system + user prompt")}
          ${sectionTemplate("raw", "Raw Debug JSON", "copyable backend payload")}
          ${sectionTemplate("logs", "Logs", "recent brain panel events")}
        </div>
      </div>
    `;

    document.body.appendChild(root);

    els.root = root;
    els.panel = q(".nova-brain-debug-panel", root);
    els.headerStatus = q("[data-brain-status]", root);
    els.badgeMode = q("[data-brain-badge-mode]", root);
    els.badgeConfidence = q("[data-brain-badge-confidence]", root);
    els.summaryBody = q('[data-brain-body="summary"]', root);
    els.routingBody = q('[data-brain-body="routing"]', root);
    els.memoryBody = q('[data-brain-body="memory"]', root);
    els.promptBody = q('[data-brain-body="prompt"]', root);
    els.rawBody = q('[data-brain-body="raw"]', root);
    els.logsBody = q('[data-brain-body="logs"]', root);
    els.copyBtn = q("[data-brain-copy]", root);
    els.refreshBtn = q("[data-brain-refresh]", root);
    els.collapseBtn = q("[data-brain-collapse]", root);

    wireUi();
  }

  function wireUi() {
    if (!els.root || els.root.dataset.bound === "1") return;
    els.root.dataset.bound = "1";

    els.root.addEventListener("click", function (event) {
      const toggleBtn = event.target.closest("[data-brain-toggle]");
      if (toggleBtn) {
        const key = String(toggleBtn.getAttribute("data-brain-toggle") || "");
        if (!key) return;
        state.expanded[key] = !state.expanded[key];
        render();
        return;
      }

      if (event.target.closest("[data-brain-refresh]")) {
        fetchStateNow();
        return;
      }

      if (event.target.closest("[data-brain-copy]")) {
        copyDebugJson();
        return;
      }

      if (event.target.closest("[data-brain-collapse]")) {
        const allClosed = Object.keys(state.expanded).every(function (key) {
          return !state.expanded[key];
        });

        Object.keys(state.expanded).forEach(function (key) {
          state.expanded[key] = allClosed;
        });

        els.collapseBtn.textContent = allClosed ? "Collapse All" : "Expand All";
        render();
      }
    });
  }

  function extractLatestAssistantMessage(payload) {
    const safePayload = safeObject(payload);
    const directSession = safeObject(safePayload.session);
    const directMessages = safeArray(directSession.messages);

    for (let i = directMessages.length - 1; i >= 0; i -= 1) {
      const msg = safeObject(directMessages[i]);
      if (String(msg.role || "").toLowerCase() === "assistant") {
        return msg;
      }
    }

    const sessions = safeArray(safePayload.sessions);
    for (let s = 0; s < sessions.length; s += 1) {
      const session = safeObject(sessions[s]);
      const messages = safeArray(session.messages);
      for (let i = messages.length - 1; i >= 0; i -= 1) {
        const msg = safeObject(messages[i]);
        if (String(msg.role || "").toLowerCase() === "assistant") {
          return msg;
        }
      }
    }

    return null;
  }

  function buildNormalizedDebug(payload, assistantMessage) {
    const safePayload = safeObject(payload);
    const msg = safeObject(assistantMessage);
    const msgMeta = safeObject(msg.meta);
    const debug = safeObject(msgMeta.debug);

    const decision = safeObject(
      debug.decision ||
      safePayload.debug?.decision ||
      safePayload.decision ||
      safePayload.routing
    );

    const memoryContext = safeObject(
      debug.memory_context ||
      debug._memory_context ||
      safePayload.memory_context ||
      safePayload._memory_context
    );

    const promptBuilder = safeObject(
      debug.prompt_builder ||
      safePayload.debug?.prompt_builder ||
      safePayload.prompt_builder
    );

    const routing = safeObject(
      debug.routing ||
      safePayload.routing ||
      {
        mode: decision.mode,
        confidence: decision.confidence,
        winning_score: decision.winning_score,
        top_modes: decision.mode_scores,
      }
    );

    const model = safeObject(
      debug.model ||
      safePayload.model ||
      safePayload.debug?.model
    );

    return {
      decision,
      memory_context: memoryContext,
      prompt_builder: promptBuilder,
      routing,
      model,
      raw: {
        payload: safePayload,
        assistant_message: msg,
        debug,
      },
    };
  }

  async function apiGet(url) {
    const response = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    });

    let data = {};
    try {
      data = await response.json();
    } catch (_) {
      data = {};
    }

    if (!response.ok || data.ok === false) {
      const error = new Error(data.error || data.message || `HTTP ${response.status}`);
      error.status = response.status;
      error.payload = data;
      throw error;
    }

    return data;
  }

  async function fetchStateNow() {
    try {
      log("Polling /api/state");
      const payload = await apiGet("/api/state");
      state.lastStatePayload = payload;

      const assistantMessage = extractLatestAssistantMessage(payload);
      state.lastAssistantMessage = assistantMessage;

      if (assistantMessage) {
        log("Extracted assistant meta from /api/state");
      } else {
        log("No assistant message found in /api/state");
      }

      state.lastDebug = buildNormalizedDebug(payload, assistantMessage);
      render();
    } catch (error) {
      log("State poll failed", {
        message: error?.message || "Unknown error",
        status: error?.status || 0,
      });
      renderError(error);
    }
  }

  function renderError(error) {
    ensureRoot();

    const message = error?.message || "Unknown error";
    if (els.headerStatus) {
      els.headerStatus.textContent = `State poll failed: ${message}`;
    }

    if (els.summaryBody) {
      els.summaryBody.innerHTML = `
        <div class="nova-brain-empty">Brain debug could not load /api/state.</div>
        <pre class="nova-brain-pre">${escapeHtml(formatJson({
          message,
          status: error?.status || 0,
          payload: error?.payload || {},
        }))}</pre>
      `;
    }
  }

  function renderSummary(debug) {
    const decision = safeObject(debug.decision);
    const override = safeObject(decision.override);
    const model = safeObject(debug.model);

    const mode = String(decision.mode || debug.routing.mode || "--").toUpperCase();
    const confidence = Number(decision.confidence || debug.routing.confidence || 0);
    const responseStyle = String(decision.response_style || "--");
    const artifact = !!decision.save_artifact;
    const useMemory = !!decision.use_memory;
    const extractMemory = !!decision.extract_memory;
    const preferenceLock = !!override.preference_lock;
    const modelName = String(
      model.chat_model ||
      model.model ||
      model.name ||
      "--"
    );
    const routeBuild = String(
      model.route_build ||
      model.build ||
      debug.raw.payload?.route_build ||
      "--"
    );

    els.badgeMode.textContent = `MODE: ${mode}`;
    els.badgeConfidence.textContent = `CONF: ${formatNumber(confidence, 2)}`;

    if (els.headerStatus) {
      els.headerStatus.textContent = `Live • ${mode} • ${responseStyle} • ${VERSION}`;
    }

    els.summaryBody.innerHTML = `
      <div class="nova-brain-grid">
        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Winning mode</div>
          <div class="nova-brain-card-value">${escapeHtml(mode)}</div>
        </div>

        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Confidence</div>
          <div class="nova-brain-card-value">${escapeHtml(formatNumber(confidence, 2))}</div>
        </div>

        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Response style</div>
          <div class="nova-brain-card-value">${escapeHtml(responseStyle)}</div>
        </div>

        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Artifact</div>
          <div class="nova-brain-card-value">${artifact ? "SAVED ✅" : "NO"}</div>
        </div>

        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Use memory</div>
          <div class="nova-brain-card-value">${formatBool(useMemory)}</div>
        </div>

        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Extract memory</div>
          <div class="nova-brain-card-value">${formatBool(extractMemory)}</div>
        </div>

        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Preference lock</div>
          <div class="nova-brain-card-value">${formatBool(preferenceLock)}</div>
        </div>

        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Winning score</div>
          <div class="nova-brain-card-value">${escapeHtml(formatNumber(decision.winning_score || 0, 2))}</div>
        </div>

        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Model</div>
          <div class="nova-brain-card-value">${escapeHtml(modelName)}</div>
        </div>

        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Route build</div>
          <div class="nova-brain-card-value">${escapeHtml(routeBuild)}</div>
        </div>
      </div>
    `;
  }

  function renderRouting(debug) {
    const decision = safeObject(debug.decision);
    const mode = String(decision.mode || debug.routing.mode || "");
    const modeScores = safeArray(decision.mode_scores);
    const baseScores = safeArray(decision.base_mode_scores);
    const maxScore = Math.max(
      1,
      ...modeScores.map(function (item) {
        return Number(item.score || 0);
      })
    );

    const top = modeScores.length ? modeScores : safeArray(debug.routing.top_modes);

    if (!top.length) {
      els.routingBody.innerHTML = `<div class="nova-brain-empty">No routing score data yet.</div>`;
      return;
    }

    const currentBaseMap = {};
    baseScores.forEach(function (item) {
      const key = String(item.mode || "");
      currentBaseMap[key] = Number(item.score || 0);
    });

    els.routingBody.innerHTML = `
      <div class="nova-brain-score-list">
        ${top.map(function (item) {
          const itemMode = String(item.mode || "");
          const itemScore = Number(item.score || 0);
          const baseScore = currentBaseMap[itemMode];
          return `
            <div class="nova-brain-score-item">
              <div class="nova-brain-score-head">
                <span class="nova-brain-score-mode ${itemMode === mode ? "is-winning" : ""}">
                  ${escapeHtml(itemMode.toUpperCase())}${itemMode === mode ? " • WINNER" : ""}
                </span>
                <span class="nova-brain-score-value">
                  final ${escapeHtml(formatNumber(itemScore, 2))}
                  ${Number.isFinite(baseScore) ? ` • base ${escapeHtml(formatNumber(baseScore, 2))}` : ""}
                </span>
              </div>
              ${scoreBar(itemScore, maxScore)}
            </div>
          `;
        }).join("")}
      </div>

      <div class="nova-brain-mini-note">
        Winning mode is highlighted. Bars are scaled against the highest final score.
      </div>
    `;
  }

  function renderMemory(debug) {
    const memoryContext = safeObject(debug.memory_context);
    const items = safeArray(memoryContext.items);
    const ranked = safeArray(memoryContext.ranked);
    const stats = safeObject(memoryContext.stats);

    const selectedCount =
      Number(stats.selected_count || items.length || 0);

    const preferenceLock = !!memoryContext.preference_lock;
    const totalChars = Number(stats.total_chars_used || 0);
    const maxItems = Number(stats.max_items || items.length || 0);

    let listHtml = "";

    if (items.length) {
      listHtml = items.map(function (item) {
        const safeItem = safeObject(item);
        const title = `${String(safeItem.kind || "memory")} • ${String(safeItem.id || "").slice(0, 10)}`;
        const text = safeItem.text || safeItem.memory_text || safeItem.preview || "";
        const reasons = safeArray(safeItem.reasons).join(" • ");
        return `
          <div class="nova-brain-list-item">
            <div class="nova-brain-list-item-title">${escapeHtml(title)}</div>
            <div class="nova-brain-list-item-sub">
              score ${escapeHtml(formatNumber(safeItem.score || safeItem.quality_score || 0, 2))}
              ${reasons ? ` • ${escapeHtml(reasons)}` : ""}
            </div>
            <div class="nova-brain-list-item-text">${escapeHtml(text)}</div>
          </div>
        `;
      }).join("");
    } else if (ranked.length) {
      listHtml = ranked.map(function (entry) {
        const safeEntry = safeObject(entry);
        const item = safeObject(safeEntry.item);
        return `
          <div class="nova-brain-list-item">
            <div class="nova-brain-list-item-title">${escapeHtml(String(item.kind || "memory"))}</div>
            <div class="nova-brain-list-item-sub">
              score ${escapeHtml(formatNumber(safeEntry.score || 0, 2))}
            </div>
            <div class="nova-brain-list-item-text">${escapeHtml(item.text || item.preview || "")}</div>
          </div>
        `;
      }).join("");
    } else {
      listHtml = `<div class="nova-brain-empty">No memory context selected for the latest reply.</div>`;
    }

    els.memoryBody.innerHTML = `
      <div class="nova-brain-grid">
        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Items used</div>
          <div class="nova-brain-card-value">${escapeHtml(String(selectedCount))}</div>
        </div>
        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Preference lock</div>
          <div class="nova-brain-card-value">${formatBool(preferenceLock)}</div>
        </div>
        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Total chars used</div>
          <div class="nova-brain-card-value">${escapeHtml(String(totalChars))}</div>
        </div>
        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Max items</div>
          <div class="nova-brain-card-value">${escapeHtml(String(maxItems))}</div>
        </div>
      </div>

      <div class="nova-brain-list" style="margin-top:10px;">
        ${listHtml}
      </div>
    `;
  }

  function renderPrompt(debug) {
    const promptBuilder = safeObject(debug.prompt_builder);

    const systemPrompt = String(
      promptBuilder.final_system_prompt ||
      promptBuilder.system_prompt ||
      ""
    ).trim();

    const userPrompt = String(
      promptBuilder.final_user_prompt ||
      promptBuilder.user_prompt ||
      ""
    ).trim();

    const memoryUsed = !!promptBuilder.memory_used;
    const memoryItemsUsed = Number(promptBuilder.memory_items_used || 0);

    els.promptBody.innerHTML = `
      <div class="nova-brain-grid">
        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Prompt builder memory</div>
          <div class="nova-brain-card-value">${formatBool(memoryUsed)}</div>
        </div>
        <div class="nova-brain-card">
          <div class="nova-brain-card-label">Memory items used</div>
          <div class="nova-brain-card-value">${escapeHtml(String(memoryItemsUsed))}</div>
        </div>
      </div>

      <div class="nova-brain-list" style="margin-top:10px;">
        <div class="nova-brain-list-item">
          <div class="nova-brain-list-item-title">System prompt</div>
          <pre class="nova-brain-pre">${escapeHtml(systemPrompt || "No system prompt debug data.")}</pre>
        </div>

        <div class="nova-brain-list-item">
          <div class="nova-brain-list-item-title">User prompt</div>
          <pre class="nova-brain-pre">${escapeHtml(userPrompt || "No user prompt debug data.")}</pre>
        </div>
      </div>
    `;
  }

  function renderRaw(debug) {
    els.rawBody.innerHTML = `
      <pre class="nova-brain-pre">${escapeHtml(formatJson(debug.raw))}</pre>
    `;
  }

  function renderLogs() {
    if (!els.logsBody) return;

    const items = safeArray(state.logs);
    if (!items.length) {
      els.logsBody.innerHTML = `<div class="nova-brain-empty">No logs yet.</div>`;
      return;
    }

    els.logsBody.innerHTML = items.map(function (item) {
      return `
        <div class="nova-brain-log-line">
          <span class="nova-brain-log-time">${escapeHtml(item.at || "")}</span>
          <div>${escapeHtml(item.text || "")}</div>
        </div>
      `;
    }).join("");
  }

  function render() {
    ensureRoot();

    const debug = safeObject(state.lastDebug);
    if (!Object.keys(debug).length) {
      if (els.headerStatus) {
        els.headerStatus.textContent = `Waiting for debug data • ${VERSION}`;
      }
      if (els.summaryBody) {
        els.summaryBody.innerHTML = `<div class="nova-brain-empty">No debug payload available yet.</div>`;
      }
      if (els.routingBody) {
        els.routingBody.innerHTML = `<div class="nova-brain-empty">No routing data yet.</div>`;
      }
      if (els.memoryBody) {
        els.memoryBody.innerHTML = `<div class="nova-brain-empty">No memory data yet.</div>`;
      }
      if (els.promptBody) {
        els.promptBody.innerHTML = `<div class="nova-brain-empty">No prompt-builder data yet.</div>`;
      }
      if (els.rawBody) {
        els.rawBody.innerHTML = `<div class="nova-brain-empty">No raw debug JSON yet.</div>`;
      }
      renderLogs();
      return;
    }

    renderSummary(debug);
    renderRouting(debug);
    renderMemory(debug);
    renderPrompt(debug);
    renderRaw(debug);
    renderLogs();

    Object.keys(state.expanded).forEach(function (key) {
      const body = q(`[data-brain-body="${key}"]`, els.root);
      const toggle = q(`[data-brain-toggle="${key}"] .nova-brain-section-meta`, els.root);
      if (body) {
        body.classList.toggle("nova-brain-hidden", !state.expanded[key]);
      }
      if (toggle) {
        toggle.textContent = state.expanded[key] ? "open" : "closed";
      }
    });
  }

  async function copyDebugJson() {
    try {
      const debug = state.lastDebug ? state.lastDebug.raw : {};
      await navigator.clipboard.writeText(formatJson(debug));
      log("Copied debug JSON to clipboard");
      if (els.headerStatus) {
        els.headerStatus.textContent = `Copied debug JSON • ${VERSION}`;
      }
    } catch (error) {
      log("Clipboard copy failed", { message: error?.message || "Unknown error" });
    }
  }

  function startPolling() {
    if (state.polling) {
      clearInterval(state.polling);
      state.polling = null;
    }

    state.polling = setInterval(function () {
      fetchStateNow();
    }, POLL_MS);
  }

  function boot() {
    if (state.booted) return;
    state.booted = true;

    ensureRoot();
    render();
    log("Minimal boot complete");
    fetchStateNow();
    startPolling();
  }

  window.NovaBrainDebug = {
    boot,
    refresh: fetchStateNow,
    getState() {
      return {
        lastStatePayload: state.lastStatePayload,
        lastAssistantMessage: state.lastAssistantMessage,
        lastDebug: state.lastDebug,
        logs: state.logs.slice(),
      };
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();