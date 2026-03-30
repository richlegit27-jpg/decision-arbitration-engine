(function () {
  "use strict";

  const API_BASE = "/api/artifacts";
  const CLEANUP_ROUTE = "/api/artifacts/admin/cleanup";
  const CHAT_STATE_ROUTE = "/api/state";

  const DOM = {
    panel: document.getElementById("artifactsPanel"),
    list: document.getElementById("artifactList"),
    viewer: document.getElementById("artifactViewer"),
    search: document.getElementById("artifactSearch"),
    pinnedOnly: document.getElementById("artifactPinnedOnly"),
    refreshBtn: document.getElementById("artifactRefreshBtn"),
    cleanBtn: document.getElementById("artifactCleanBtn"),
  };

  const state = {
    items: [],
    filteredItems: [],
    selectedId: null,
    search: "",
    pinnedOnly: false,
    loading: false,
  };

  function log(...args) {
    console.log("Nova artifacts loaded", ...args);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatDate(value) {
    if (!value) return "";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);
    return d.toLocaleString();
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function normalizeArtifact(raw) {
    if (!raw || typeof raw !== "object") {
      return {
        id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
        title: "Untitled",
        content: "",
        kind: "artifact",
        pinned: false,
        tags: [],
        created_at: "",
        updated_at: "",
        session_id: "",
        meta: {},
      };
    }

    const meta = raw.meta && typeof raw.meta === "object" ? raw.meta : {};
    const title =
      raw.title ||
      meta.title ||
      raw.name ||
      (raw.kind ? `${String(raw.kind).charAt(0).toUpperCase()}${String(raw.kind).slice(1)}` : "Untitled");

    return {
      id: String(raw.id || raw.artifact_id || raw._id || ""),
      title: String(title || "Untitled"),
      content: String(raw.content || raw.text || raw.body || ""),
      kind: String(raw.kind || meta.kind || "artifact"),
      pinned: Boolean(raw.pinned),
      tags: safeArray(raw.tags),
      created_at: raw.created_at || raw.createdAt || "",
      updated_at: raw.updated_at || raw.updatedAt || "",
      session_id: raw.session_id || raw.sessionId || "",
      meta,
    };
  }

  async function getJson(url, options) {
    const response = await fetch(url, options);
    const text = await response.text();
    let data = null;

    try {
      data = text ? JSON.parse(text) : null;
    } catch (error) {
      data = null;
    }

    if (!response.ok) {
      const message =
        (data && (data.error || data.message)) ||
        text ||
        `Request failed: ${response.status}`;
      throw new Error(message);
    }

    return data;
  }

  function renderEmptyList(message) {
    if (!DOM.list) return;
    DOM.list.innerHTML = `
      <div style="color:var(--muted,#9cafcf);font-size:13px;padding:8px;">
        ${escapeHtml(message)}
      </div>
    `;
  }

  function renderViewerEmpty(message) {
    if (!DOM.viewer) return;
    DOM.viewer.innerHTML = `
      <div class="nova-artifact-viewer-empty" style="color:var(--muted,#9cafcf);font-size:13px;">
        ${escapeHtml(message)}
      </div>
    `;
  }

  function getKindBadge(kind) {
    const label = String(kind || "artifact").toLowerCase();
    return `
      <span style="
        display:inline-flex;
        align-items:center;
        padding:3px 8px;
        border-radius:999px;
        border:1px solid rgba(130,158,222,0.18);
        background:rgba(255,255,255,0.04);
        font-size:11px;
        color:#cfe0ff;
      ">${escapeHtml(label)}</span>
    `;
  }

  function getPinnedBadge(pinned) {
    if (!pinned) return "";
    return `
      <span style="
        display:inline-flex;
        align-items:center;
        padding:3px 8px;
        border-radius:999px;
        border:1px solid rgba(255,215,130,0.22);
        background:rgba(255,215,130,0.08);
        font-size:11px;
        color:#ffe39a;
      ">Pinned</span>
    `;
  }

  function getTagMarkup(tags) {
    const list = safeArray(tags).filter(Boolean);
    if (!list.length) return "";
    return `
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;">
        ${list
          .map(
            (tag) => `
              <span style="
                display:inline-flex;
                align-items:center;
                padding:2px 7px;
                border-radius:999px;
                font-size:11px;
                border:1px solid rgba(130,158,222,0.16);
                background:rgba(255,255,255,0.03);
                color:#b9cfff;
              ">${escapeHtml(tag)}</span>
            `
          )
          .join("")}
      </div>
    `;
  }

  function artifactMatchesSearch(item, query) {
    if (!query) return true;
    const haystack = [
      item.title,
      item.content,
      item.kind,
      item.session_id,
      ...safeArray(item.tags),
      JSON.stringify(item.meta || {}),
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(query.toLowerCase());
  }

  function applyFilters() {
    const query = (state.search || "").trim();
    state.filteredItems = state.items.filter((item) => {
      if (state.pinnedOnly && !item.pinned) return false;
      return artifactMatchesSearch(item, query);
    });

    if (
      state.selectedId &&
      !state.filteredItems.some((item) => item.id === state.selectedId)
    ) {
      state.selectedId = state.filteredItems[0]?.id || null;
    }
  }

  function renderList() {
    if (!DOM.list) return;

    if (state.loading) {
      renderEmptyList("Loading artifacts...");
      return;
    }

    if (!state.filteredItems.length) {
      renderEmptyList("No artifacts found.");
      return;
    }

    DOM.list.innerHTML = state.filteredItems
      .map((item) => {
        const isSelected = item.id === state.selectedId;
        const preview = (item.content || "").replace(/\s+/g, " ").trim().slice(0, 140);
        const updated = formatDate(item.updated_at || item.created_at);

        return `
          <button
            type="button"
            class="nova-artifact-row"
            data-artifact-id="${escapeHtml(item.id)}"
            style="
              width:100%;
              text-align:left;
              border:1px solid ${isSelected ? "rgba(110,168,255,0.35)" : "rgba(130,158,222,0.12)"};
              background:${isSelected ? "rgba(110,168,255,0.10)" : "rgba(255,255,255,0.03)"};
              color:inherit;
              border-radius:14px;
              padding:12px;
              margin-bottom:10px;
              cursor:pointer;
            "
          >
            <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start;">
              <div style="font-weight:700;font-size:13px;line-height:1.35;">
                ${escapeHtml(item.title || "Untitled")}
              </div>
              <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;">
                ${getKindBadge(item.kind)}
                ${getPinnedBadge(item.pinned)}
              </div>
            </div>

            <div style="margin-top:8px;font-size:12px;color:#9cafcf;line-height:1.45;">
              ${escapeHtml(preview || "(no content)")}
            </div>

            <div style="margin-top:8px;font-size:11px;color:#88a1c7;">
              ${escapeHtml(updated || "")}
            </div>
          </button>
        `;
      })
      .join("");

    DOM.list.querySelectorAll("[data-artifact-id]").forEach((node) => {
      node.addEventListener("click", () => {
        const artifactId = node.getAttribute("data-artifact-id");
        state.selectedId = artifactId;
        renderList();
        renderViewer();
      });
    });
  }

  function renderViewer() {
    if (!DOM.viewer) return;

    const item = state.filteredItems.find((x) => x.id === state.selectedId)
      || state.items.find((x) => x.id === state.selectedId);

    if (!item) {
      renderViewerEmpty("Select an artifact to view it here.");
      return;
    }

    const meta = item.meta && typeof item.meta === "object" ? item.meta : {};
    const rawMeta = JSON.stringify(meta, null, 2);

    DOM.viewer.innerHTML = `
      <div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start;flex-wrap:wrap;margin-bottom:12px;">
        <div>
          <div style="font-size:18px;font-weight:700;line-height:1.35;">
            ${escapeHtml(item.title || "Untitled")}
          </div>
          <div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px;">
            ${getKindBadge(item.kind)}
            ${getPinnedBadge(item.pinned)}
          </div>
        </div>

        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button
            type="button"
            id="artifactCopyBtn"
            style="
              border:1px solid rgba(130,158,222,0.16);
              background:rgba(255,255,255,0.05);
              color:#eef4ff;
              border-radius:10px;
              padding:8px 10px;
              cursor:pointer;
            "
          >Copy</button>

          <button
            type="button"
            id="artifactPinBtn"
            style="
              border:1px solid rgba(130,158,222,0.16);
              background:rgba(255,255,255,0.05);
              color:#eef4ff;
              border-radius:10px;
              padding:8px 10px;
              cursor:pointer;
            "
          >${item.pinned ? "Unpin" : "Pin"}</button>

          <button
            type="button"
            id="artifactDeleteBtn"
            style="
              border:1px solid rgba(255,111,145,0.16);
              background:rgba(255,111,145,0.08);
              color:#ffd5df;
              border-radius:10px;
              padding:8px 10px;
              cursor:pointer;
            "
          >Delete</button>
        </div>
      </div>

      <div style="font-size:12px;color:#9cafcf;display:grid;gap:6px;margin-bottom:12px;">
        <div><strong style="color:#d9e6ff;">Created:</strong> ${escapeHtml(formatDate(item.created_at) || "-")}</div>
        <div><strong style="color:#d9e6ff;">Updated:</strong> ${escapeHtml(formatDate(item.updated_at) || "-")}</div>
        <div><strong style="color:#d9e6ff;">Session:</strong> ${escapeHtml(item.session_id || "-")}</div>
      </div>

      ${getTagMarkup(item.tags)}

      <div style="margin-top:14px;">
        <div style="font-size:12px;font-weight:700;letter-spacing:0.06em;color:#9cafcf;margin-bottom:8px;">
          CONTENT
        </div>
        <pre style="
          margin:0;
          white-space:pre-wrap;
          word-break:break-word;
          line-height:1.55;
          font-size:13px;
          color:#eef4ff;
          background:rgba(0,0,0,0.18);
          border:1px solid rgba(130,158,222,0.12);
          border-radius:14px;
          padding:12px;
        ">${escapeHtml(item.content || "")}</pre>
      </div>

      <details style="margin-top:14px;">
        <summary style="cursor:pointer;color:#9cafcf;font-size:12px;">Debug / Meta</summary>
        <pre style="
          margin-top:10px;
          white-space:pre-wrap;
          word-break:break-word;
          line-height:1.45;
          font-size:12px;
          color:#cfe0ff;
          background:rgba(0,0,0,0.18);
          border:1px solid rgba(130,158,222,0.12);
          border-radius:14px;
          padding:12px;
        ">${escapeHtml(rawMeta)}</pre>
      </details>
    `;

    const copyBtn = document.getElementById("artifactCopyBtn");
    const pinBtn = document.getElementById("artifactPinBtn");
    const deleteBtn = document.getElementById("artifactDeleteBtn");

    if (copyBtn) {
      copyBtn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(item.content || "");
          copyBtn.textContent = "Copied";
          setTimeout(() => {
            copyBtn.textContent = "Copy";
          }, 900);
        } catch (error) {
          alert(`Copy failed: ${error.message}`);
        }
      });
    }

    if (pinBtn) {
      pinBtn.addEventListener("click", async () => {
        await togglePin(item);
      });
    }

    if (deleteBtn) {
      deleteBtn.addEventListener("click", async () => {
        await deleteArtifact(item);
      });
    }
  }

  async function loadArtifacts() {
    if (!DOM.panel || !DOM.list || !DOM.viewer) {
      console.warn("NovaArtifacts: required DOM nodes missing", {
        artifactsPanel: !!DOM.panel,
        artifactList: !!DOM.list,
        artifactViewer: !!DOM.viewer,
      });
      return;
    }

    state.loading = true;
    renderList();
    renderViewerEmpty("Loading artifact viewer...");

    try {
      let data = null;

      try {
        data = await getJson(API_BASE);
      } catch (error) {
        try {
          const fallback = await getJson(CHAT_STATE_ROUTE);
          if (fallback && Array.isArray(fallback.artifacts)) {
            data = { artifacts: fallback.artifacts };
          } else {
            throw error;
          }
        } catch (innerError) {
          throw error;
        }
      }

      const list = Array.isArray(data)
        ? data
        : Array.isArray(data?.artifacts)
          ? data.artifacts
          : Array.isArray(data?.items)
            ? data.items
            : [];

      state.items = list
        .map(normalizeArtifact)
        .filter((item) => item.id)
        .sort((a, b) => {
          const aTime = new Date(a.updated_at || a.created_at || 0).getTime();
          const bTime = new Date(b.updated_at || b.created_at || 0).getTime();
          return bTime - aTime;
        });

      if (!state.selectedId) {
        state.selectedId = state.items[0]?.id || null;
      }

      applyFilters();
      renderList();
      renderViewer();
    } catch (error) {
      console.error("NovaArtifacts.loadArtifacts failed", error);
      state.items = [];
      state.filteredItems = [];
      state.selectedId = null;
      renderEmptyList(`Failed to load artifacts: ${error.message}`);
      renderViewerEmpty("Artifact viewer unavailable.");
    } finally {
      state.loading = false;
      renderList();
    }
  }

  async function togglePin(item) {
    if (!item || !item.id) return;

    const nextPinned = !item.pinned;
    const payload = { pinned: nextPinned };

    try {
      await getJson(`${API_BASE}/${encodeURIComponent(item.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (error) {
      try {
        await getJson(`${API_BASE}/pin`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            artifact_id: item.id,
            pinned: nextPinned,
          }),
        });
      } catch (innerError) {
        alert(`Pin update failed: ${innerError.message}`);
        return;
      }
    }

    item.pinned = nextPinned;
    state.items = state.items.map((x) => (x.id === item.id ? { ...x, pinned: nextPinned } : x));
    applyFilters();
    renderList();
    renderViewer();
  }

  async function deleteArtifact(item) {
    if (!item || !item.id) return;

    const ok = window.confirm(`Delete artifact?\n\n${item.title || item.id}`);
    if (!ok) return;

    try {
      await getJson(`${API_BASE}/${encodeURIComponent(item.id)}`, {
        method: "DELETE",
      });
    } catch (error) {
      try {
        await getJson(`${API_BASE}/delete`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ artifact_id: item.id }),
        });
      } catch (innerError) {
        alert(`Delete failed: ${innerError.message}`);
        return;
      }
    }

    state.items = state.items.filter((x) => x.id !== item.id);
    if (state.selectedId === item.id) {
      state.selectedId = state.items[0]?.id || null;
    }
    applyFilters();
    renderList();
    renderViewer();
  }

  async function cleanJunk() {
    const ok = window.confirm("Clean old fallback/self-echo junk artifacts?");
    if (!ok) return;

    try {
      const data = await getJson(CLEANUP_ROUTE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      const removed =
        data?.removed_count ??
        data?.deleted_count ??
        data?.count ??
        0;

      await loadArtifacts();
      alert(`Cleanup complete. Removed ${removed} artifact(s).`);
    } catch (error) {
      alert(`Cleanup failed: ${error.message}`);
    }
  }

  function bindEvents() {
    if (DOM.search) {
      DOM.search.addEventListener("input", (event) => {
        state.search = event.target.value || "";
        applyFilters();
        renderList();
        renderViewer();
      });
    }

    if (DOM.pinnedOnly) {
      DOM.pinnedOnly.addEventListener("click", () => {
        state.pinnedOnly = !state.pinnedOnly;
        DOM.pinnedOnly.textContent = state.pinnedOnly ? "Pinned Only" : "Pinned";
        DOM.pinnedOnly.classList.toggle("is-active", state.pinnedOnly);
        applyFilters();
        renderList();
        renderViewer();
      });
    }

    if (DOM.refreshBtn) {
      DOM.refreshBtn.addEventListener("click", () => {
        loadArtifacts();
      });
    }

    if (DOM.cleanBtn) {
      DOM.cleanBtn.addEventListener("click", () => {
        cleanJunk();
      });
    }

    window.addEventListener("nova:artifacts:refresh", () => {
      loadArtifacts();
    });
  }

  const NovaArtifacts = {
    init() {
      bindEvents();
      loadArtifacts();
      log();
    },
    refresh() {
      return loadArtifacts();
    },
    getState() {
      return {
        ...state,
        items: [...state.items],
        filteredItems: [...state.filteredItems],
      };
    },
  };

  window.NovaArtifacts = NovaArtifacts;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => NovaArtifacts.init(), { once: true });
  } else {
    NovaArtifacts.init();
  }
})();