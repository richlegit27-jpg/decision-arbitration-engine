(() => {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.artifacts = Nova.artifacts || {};

  const state = {
    artifacts: [],
    filtered: [],
    selectedId: null,
    ui: null,
    filters: {
      q: "",
      kind: "all",
      pinnedOnly: false,
      sort: "newest",
    },
  };

  function $(selector, root = document) {
    return root.querySelector(selector);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function text(value) {
    if (value == null) return "";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }

  function stripHtml(value) {
    return text(value).replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
  }

  function formatDate(value) {
    if (!value) return "";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return text(value);
    return d.toLocaleString();
  }

  function summarize(value, max = 180) {
    const clean = stripHtml(value);
    if (!clean) return "";
    if (clean.length <= max) return clean;
    return clean.slice(0, max - 1).trim() + "…";
  }

  function normalizeKind(raw) {
    const v = text(raw).toLowerCase().trim();
    if (!v) return "chat";
    if (v.includes("web")) return "web";
    if (v.includes("knowledge")) return "knowledge";
    if (v.includes("doc")) return "document";
    if (v.includes("pdf")) return "document";
    if (v.includes("image")) return "image";
    if (v.includes("upload")) return "document";
    if (v.includes("chat")) return "chat";
    return v;
  }

  function artifactUpdatedAt(a) {
    return a.updated_at || a.created_at || "";
  }

  function artifactSearchBlob(a) {
    return [
      a.title,
      a.content,
      a.kind,
      ...(Array.isArray(a.tags) ? a.tags : []),
      text(a.meta),
    ]
      .join(" ")
      .toLowerCase();
  }

  function ensureStyles() {
    if (document.getElementById("novaArtifactsSearchStyles")) return;

    const style = document.createElement("style");
    style.id = "novaArtifactsSearchStyles";
    style.textContent = `
      .nova-artifacts-toolbar{
        display:flex;
        flex-direction:column;
        gap:12px;
        padding:12px;
        border-bottom:1px solid rgba(255,255,255,0.08);
        background:rgba(255,255,255,0.02);
        position:sticky;
        top:0;
        z-index:2;
        backdrop-filter:blur(8px);
      }
      .nova-artifacts-toolbar-row{
        display:flex;
        gap:8px;
        flex-wrap:wrap;
        align-items:center;
      }
      .nova-artifacts-toolbar input[type="search"],
      .nova-artifacts-toolbar select{
        min-height:38px;
        border-radius:10px;
        border:1px solid rgba(255,255,255,0.12);
        background:rgba(255,255,255,0.04);
        color:inherit;
        padding:0 12px;
        outline:none;
      }
      .nova-artifacts-toolbar input[type="search"]{
        flex:1 1 220px;
      }
      .nova-artifacts-toolbar label{
        display:flex;
        align-items:center;
        gap:8px;
        font-size:13px;
        opacity:0.92;
      }
      .nova-artifacts-count{
        font-size:12px;
        opacity:0.75;
        margin-left:auto;
      }
      .nova-artifact-list-wrap{
        display:flex;
        flex-direction:column;
        min-height:0;
      }
      .nova-artifact-list{
        display:flex;
        flex-direction:column;
        gap:10px;
        padding:12px;
      }
      .nova-artifact-empty{
        padding:16px;
        font-size:13px;
        opacity:0.72;
      }
      .nova-artifact-card{
        border:1px solid rgba(255,255,255,0.09);
        border-radius:14px;
        padding:12px;
        background:rgba(255,255,255,0.03);
        cursor:pointer;
      }
      .nova-artifact-card:hover{
        background:rgba(255,255,255,0.05);
      }
      .nova-artifact-card.active{
        outline:1px solid rgba(110,168,255,0.55);
        background:rgba(110,168,255,0.08);
      }
      .nova-artifact-head{
        display:flex;
        align-items:flex-start;
        justify-content:space-between;
        gap:10px;
        margin-bottom:8px;
      }
      .nova-artifact-title{
        font-weight:700;
        line-height:1.25;
        word-break:break-word;
      }
      .nova-artifact-meta{
        display:flex;
        flex-wrap:wrap;
        gap:6px;
        margin:0 0 8px;
      }
      .nova-artifact-pill{
        font-size:11px;
        line-height:1;
        padding:6px 8px;
        border-radius:999px;
        background:rgba(255,255,255,0.07);
        border:1px solid rgba(255,255,255,0.08);
        opacity:0.95;
      }
      .nova-artifact-preview{
        font-size:13px;
        line-height:1.45;
        opacity:0.88;
        white-space:pre-wrap;
        word-break:break-word;
      }
      .nova-artifact-actions{
        display:flex;
        gap:6px;
        flex-wrap:wrap;
        margin-top:10px;
      }
      .nova-artifact-btn{
        border:1px solid rgba(255,255,255,0.1);
        background:rgba(255,255,255,0.04);
        color:inherit;
        border-radius:10px;
        padding:7px 10px;
        font-size:12px;
        cursor:pointer;
      }
      .nova-artifact-btn:hover{
        background:rgba(255,255,255,0.08);
      }
      .nova-artifact-viewer-fallback{
        border-top:1px solid rgba(255,255,255,0.08);
        padding:12px;
      }
      .nova-artifact-viewer-fallback pre{
        margin:0;
        white-space:pre-wrap;
        word-break:break-word;
        font-family:inherit;
        line-height:1.45;
      }
    `;
    document.head.appendChild(style);
  }

  function findPanel() {
    return (
      $("#novaArtifactsPanel") ||
      $("#artifactsPanel") ||
      $('[data-panel="artifacts"]') ||
      $(".nova-artifacts-panel") ||
      $(".artifact-panel")
    );
  }

  function findListContainer(panel) {
    return (
      $("#novaArtifactsList", panel) ||
      $("#artifactList", panel) ||
      $("#artifactsList", panel) ||
      $('[data-artifacts-list]', panel) ||
      $(".nova-artifacts-list", panel) ||
      $(".artifact-list", panel)
    );
  }

  function findViewer(panel) {
    return {
      title:
        $("#novaArtifactViewerTitle", panel) ||
        $("#artifactViewerTitle", panel) ||
        $('[data-artifact-viewer-title]', panel),
      meta:
        $("#novaArtifactViewerMeta", panel) ||
        $("#artifactViewerMeta", panel) ||
        $('[data-artifact-viewer-meta]', panel),
      content:
        $("#novaArtifactViewerContent", panel) ||
        $("#artifactViewerContent", panel) ||
        $('[data-artifact-viewer-content]', panel),
      root:
        $("#novaArtifactViewer", panel) ||
        $("#artifactViewer", panel) ||
        $('[data-artifact-viewer]', panel),
    };
  }

  function ensurePanelScaffold() {
    const panel = findPanel();
    if (!panel) {
      console.warn("Nova artifacts: panel not found");
      return null;
    }

    ensureStyles();

    let listContainer = findListContainer(panel);
    if (!listContainer) {
      const wrap = document.createElement("div");
      wrap.className = "nova-artifact-list-wrap";

      listContainer = document.createElement("div");
      listContainer.id = "novaArtifactsList";
      listContainer.className = "nova-artifact-list";

      wrap.appendChild(listContainer);
      panel.appendChild(wrap);
    } else {
      listContainer.classList.add("nova-artifact-list");
    }

    if (!findViewer(panel).content) {
      const fallback = document.createElement("div");
      fallback.className = "nova-artifact-viewer-fallback";
      fallback.innerHTML = `
        <div id="novaArtifactViewerTitle" style="font-weight:700;margin-bottom:6px;"></div>
        <div id="novaArtifactViewerMeta" style="font-size:12px;opacity:.72;margin-bottom:10px;"></div>
        <pre id="novaArtifactViewerContent"></pre>
      `;
      panel.appendChild(fallback);
    }

    return panel;
  }

  function injectToolbar(panel) {
    let toolbar = $("#novaArtifactsToolbar", panel);
    if (toolbar) return toolbar;

    toolbar = document.createElement("div");
    toolbar.id = "novaArtifactsToolbar";
    toolbar.className = "nova-artifacts-toolbar";
    toolbar.innerHTML = `
      <div class="nova-artifacts-toolbar-row">
        <input
          id="novaArtifactSearchInput"
          type="search"
          placeholder="Search title, content, tags..."
          autocomplete="off"
        />
        <select id="novaArtifactKindFilter" aria-label="Artifact kind filter">
          <option value="all">all</option>
          <option value="chat">chat</option>
          <option value="knowledge">knowledge</option>
          <option value="web">web</option>
          <option value="document">document</option>
          <option value="image">image</option>
        </select>
        <select id="novaArtifactSort" aria-label="Artifact sort">
          <option value="newest">newest first</option>
          <option value="oldest">oldest first</option>
        </select>
      </div>
      <div class="nova-artifacts-toolbar-row">
        <label>
          <input id="novaArtifactPinnedOnly" type="checkbox" />
          pinned only
        </label>
        <button id="novaArtifactRefreshBtn" type="button" class="nova-artifact-btn">refresh</button>
        <button id="novaArtifactClearBtn" type="button" class="nova-artifact-btn">clear</button>
        <div id="novaArtifactsCount" class="nova-artifacts-count">0 items</div>
      </div>
    `;

    panel.insertBefore(toolbar, panel.firstChild);
    return toolbar;
  }

  function wireToolbar(panel) {
    const searchInput = $("#novaArtifactSearchInput", panel);
    const kindFilter = $("#novaArtifactKindFilter", panel);
    const sortSelect = $("#novaArtifactSort", panel);
    const pinnedOnly = $("#novaArtifactPinnedOnly", panel);
    const refreshBtn = $("#novaArtifactRefreshBtn", panel);
    const clearBtn = $("#novaArtifactClearBtn", panel);

    searchInput.value = state.filters.q;
    kindFilter.value = state.filters.kind;
    sortSelect.value = state.filters.sort;
    pinnedOnly.checked = state.filters.pinnedOnly;

    searchInput.addEventListener("input", () => {
      state.filters.q = searchInput.value.trim().toLowerCase();
      applyFilters();
      renderArtifactList();
    });

    kindFilter.addEventListener("change", () => {
      state.filters.kind = kindFilter.value;
      applyFilters();
      renderArtifactList();
    });

    sortSelect.addEventListener("change", () => {
      state.filters.sort = sortSelect.value;
      applyFilters();
      renderArtifactList();
    });

    pinnedOnly.addEventListener("change", () => {
      state.filters.pinnedOnly = pinnedOnly.checked;
      applyFilters();
      renderArtifactList();
    });

    refreshBtn.addEventListener("click", async () => {
      await loadArtifacts();
    });

    clearBtn.addEventListener("click", () => {
      state.filters.q = "";
      state.filters.kind = "all";
      state.filters.sort = "newest";
      state.filters.pinnedOnly = false;

      searchInput.value = "";
      kindFilter.value = "all";
      sortSelect.value = "newest";
      pinnedOnly.checked = false;

      applyFilters();
      renderArtifactList();
    });
  }

  async function apiJson(url, options) {
    const res = await fetch(url, options);
    const raw = await res.text();
    let data = null;

    try {
      data = raw ? JSON.parse(raw) : null;
    } catch {
      data = raw;
    }

    if (!res.ok) {
      const message =
        (data && data.error) ||
        (data && data.message) ||
        raw ||
        `Request failed: ${res.status}`;
      throw new Error(message);
    }

    return data;
  }

  function normalizeArtifact(item) {
    const a = item || {};
    return {
      id: text(a.id),
      title: text(a.title || a.name || "Untitled artifact"),
      content: text(a.content),
      kind: normalizeKind(a.kind),
      tags: Array.isArray(a.tags) ? a.tags.map((x) => text(x)) : [],
      pinned: Boolean(a.pinned),
      created_at: a.created_at || "",
      updated_at: a.updated_at || "",
      session_id: text(a.session_id || ""),
      meta: a.meta || {},
      raw: a,
    };
  }

  async function loadArtifacts() {
    const panel = state.ui?.panel || ensurePanelScaffold();
    if (!panel) return;

    const list = state.ui?.list || findListContainer(panel);
    if (list) {
      list.innerHTML = `<div class="nova-artifact-empty">Loading artifacts...</div>`;
    }

    try {
      const data = await apiJson("/api/artifacts");

      const items = Array.isArray(data)
        ? data
        : Array.isArray(data?.items)
        ? data.items
        : Array.isArray(data?.artifacts)
        ? data.artifacts
        : [];

      console.log("Nova artifacts raw response:", data);
      console.log("Nova artifacts parsed items:", items);

      state.artifacts = items.map(normalizeArtifact);
      applyFilters();
      renderArtifactList();

      if (state.selectedId) {
        const stillExists = state.artifacts.find((a) => a.id === state.selectedId);
        if (stillExists) {
          await openArtifact(state.selectedId, false);
        } else {
          clearViewer();
        }
      }
    } catch (err) {
      console.error("Nova artifacts load failed:", err);
      if (list) {
        list.innerHTML = `<div class="nova-artifact-empty">Failed to load artifacts: ${escapeHtml(err.message)}</div>`;
      }
      state.artifacts = [];
      state.filtered = [];
      updateCount(0, 0);
    }
  }

  function applyFilters() {
    const q = state.filters.q;
    const kind = state.filters.kind;
    const pinnedOnly = state.filters.pinnedOnly;
    const sort = state.filters.sort;

    let items = [...state.artifacts];

    if (kind !== "all") {
      items = items.filter((a) => a.kind === kind);
    }

    if (pinnedOnly) {
      items = items.filter((a) => a.pinned);
    }

    if (q) {
      items = items.filter((a) => artifactSearchBlob(a).includes(q));
    }

    items.sort((a, b) => {
      const da = new Date(artifactUpdatedAt(a)).getTime() || 0;
      const db = new Date(artifactUpdatedAt(b)).getTime() || 0;
      return sort === "oldest" ? da - db : db - da;
    });

    state.filtered = items;
    updateCount(items.length, state.artifacts.length);
  }

  function updateCount(filteredCount, totalCount) {
    const el = state.ui?.count;
    if (!el) return;

    if (filteredCount === totalCount) {
      el.textContent = `${filteredCount} item${filteredCount === 1 ? "" : "s"}`;
      return;
    }

    el.textContent = `${filteredCount} of ${totalCount} items`;
  }

  function renderArtifactList() {
    const list = state.ui?.list;
    if (!list) return;

    if (!state.filtered.length) {
      list.innerHTML = `<div class="nova-artifact-empty">No artifacts match the current search/filter.</div>`;
      return;
    }

    list.innerHTML = state.filtered
      .map((a) => {
        const preview = summarize(a.content, 180);
        const active = a.id === state.selectedId ? " active" : "";
        const pills = [
          `<span class="nova-artifact-pill">${escapeHtml(a.kind)}</span>`,
          a.pinned ? `<span class="nova-artifact-pill">pinned</span>` : "",
          artifactUpdatedAt(a)
            ? `<span class="nova-artifact-pill">${escapeHtml(formatDate(artifactUpdatedAt(a)))}</span>`
            : "",
        ]
          .filter(Boolean)
          .join("");

        return `
          <div class="nova-artifact-card${active}" data-artifact-id="${escapeHtml(a.id)}">
            <div class="nova-artifact-head">
              <div class="nova-artifact-title">${escapeHtml(a.title)}</div>
            </div>
            <div class="nova-artifact-meta">${pills}</div>
            <div class="nova-artifact-preview">${escapeHtml(preview || "(no content)")}</div>
            <div class="nova-artifact-actions">
              <button type="button" class="nova-artifact-btn" data-action="open" data-artifact-id="${escapeHtml(a.id)}">open</button>
              <button type="button" class="nova-artifact-btn" data-action="copy" data-artifact-id="${escapeHtml(a.id)}">copy</button>
            </div>
          </div>
        `;
      })
      .join("");

    list.onclick = async (event) => {
      const btn = event.target.closest("[data-action]");
      if (btn) {
        event.stopPropagation();
        const id = btn.getAttribute("data-artifact-id");
        const action = btn.getAttribute("data-action");

        if (action === "open") {
          await openArtifact(id, true);
          return;
        }

        if (action === "copy") {
          await copyArtifact(id);
          return;
        }
      }

      const card = event.target.closest("[data-artifact-id]");
      if (!card) return;
      const id = card.getAttribute("data-artifact-id");
      await openArtifact(id, true);
    };
  }

  async function openArtifact(id, rerenderList = true) {
    const local = state.artifacts.find((a) => a.id === id);
    state.selectedId = id;
    if (rerenderList) renderArtifactList();

    if (local) {
      renderViewer(local);
    }

    try {
      const fresh = await apiJson(`/api/artifacts/${encodeURIComponent(id)}`);
      const item =
        fresh?.artifact && typeof fresh.artifact === "object"
          ? fresh.artifact
          : fresh;
      const normalized = normalizeArtifact(item);

      const idx = state.artifacts.findIndex((a) => a.id === normalized.id);
      if (idx >= 0) state.artifacts[idx] = normalized;

      applyFilters();
      if (rerenderList) renderArtifactList();
      renderViewer(normalized);
    } catch (err) {
      if (!local) {
        renderViewer({
          id,
          title: "Artifact load failed",
          content: `Failed to load artifact ${id}\n\n${err.message}`,
          kind: "chat",
          tags: [],
          pinned: false,
          created_at: "",
          updated_at: "",
          session_id: "",
          meta: {},
        });
      }
    }
  }

  function clearViewer() {
    const viewer = state.ui?.viewer;
    if (!viewer) return;
    if (viewer.title) viewer.title.textContent = "";
    if (viewer.meta) viewer.meta.textContent = "";
    if (viewer.content) viewer.content.textContent = "";
  }

  function renderViewer(a) {
    const viewer = state.ui?.viewer;
    if (!viewer) return;

    if (viewer.title) viewer.title.textContent = a.title || "Untitled artifact";

    const metaParts = [
      a.kind ? `kind: ${a.kind}` : "",
      a.pinned ? "pinned" : "",
      a.session_id ? `session: ${a.session_id}` : "",
      artifactUpdatedAt(a) ? `updated: ${formatDate(artifactUpdatedAt(a))}` : "",
    ].filter(Boolean);

    if (viewer.meta) viewer.meta.textContent = metaParts.join("  •  ");

    if (viewer.content) {
      const metaDump =
        a.meta && Object.keys(a.meta).length
          ? `\n\n--- meta ---\n${text(a.meta)}`
          : "";
      viewer.content.textContent = `${text(a.content || "(no content)")}${metaDump}`;
    }
  }

  async function copyArtifact(id) {
    const a = state.artifacts.find((x) => x.id === id);
    if (!a) return;

    const payload = `${a.title}\n\n${a.content || ""}`;
    try {
      await navigator.clipboard.writeText(payload);
      const btn = document.querySelector(`[data-action="copy"][data-artifact-id="${CSS.escape(id)}"]`);
      if (btn) {
        const old = btn.textContent;
        btn.textContent = "copied";
        setTimeout(() => {
          btn.textContent = old;
        }, 900);
      }
    } catch (err) {
      console.error("Copy failed:", err);
    }
  }

  function exposePublicApi() {
    Nova.artifacts.reload = loadArtifacts;
    Nova.artifacts.getAll = () => [...state.artifacts];
    Nova.artifacts.getFiltered = () => [...state.filtered];
    Nova.artifacts.open = openArtifact;
    Nova.artifacts.search = (q = "") => {
      state.filters.q = text(q).toLowerCase().trim();
      if (state.ui?.searchInput) state.ui.searchInput.value = state.filters.q;
      applyFilters();
      renderArtifactList();
    };
  }

  function bootstrap() {
    const panel = ensurePanelScaffold();
    if (!panel) return;

    injectToolbar(panel);

    state.ui = {
      panel,
      list: findListContainer(panel),
      viewer: findViewer(panel),
      count: $("#novaArtifactsCount", panel),
      searchInput: $("#novaArtifactSearchInput", panel),
    };

    wireToolbar(panel);
    exposePublicApi();
    loadArtifacts();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();