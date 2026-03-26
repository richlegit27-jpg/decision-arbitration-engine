(() => {
  "use strict";

  if (window.__novaRenderMemoryLoaded) {
    console.warn("Nova render memory already loaded. Skipping duplicate module.");
    return;
  }
  window.__novaRenderMemoryLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  const state = (Nova.state = Nova.state || {});
  const dom = (Nova.dom = Nova.dom || {});
  const render = (Nova.render = Nova.render || {});
  const util = (Nova.util = Nova.util || {});

  function byId(id) {
    return document.getElementById(id);
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function asString(value, fallback = "") {
    return typeof value === "string" ? value : fallback;
  }

  function escapeHtml(value) {
    if (typeof util.escapeHtml === "function") {
      return util.escapeHtml(value);
    }

    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatDateLoose(value) {
    if (typeof util.formatDateLoose === "function") {
      return util.formatDateLoose(value);
    }

    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    try {
      return date.toLocaleString();
    } catch (_) {
      return "";
    }
  }

  function cacheDom() {
    dom.memoryList = dom.memoryList || byId("memoryList");
    return dom;
  }

  function isDeleting(id) {
    return state.deletingMemoryIds instanceof Set && state.deletingMemoryIds.has(id);
  }

  function buildMemoryHtml(item) {
    const id = asString(item?.id, "");
    const kind = asString(item?.kind, "note");
    const value = asString(item?.value, "");
    const createdAt = formatDateLoose(item?.created_at || "");
    const deleting = isDeleting(id);

    return `
      <article class="memory-card ${deleting ? "is-deleting" : ""}" data-memory-id="${escapeHtml(id)}">
        <div class="memory-card-top">
          <div class="memory-kind-wrap">
            <span class="memory-kind">${escapeHtml(kind)}</span>
            ${createdAt ? `<span class="memory-date">${escapeHtml(createdAt)}</span>` : ""}
          </div>
          <button
            class="memory-delete-btn ${deleting ? "is-busy" : ""}"
            type="button"
            data-delete-memory="${escapeHtml(id)}"
            aria-label="Delete memory"
            title="${deleting ? "Deleting..." : "Delete memory"}"
            ${deleting ? "disabled" : ""}
          >
            ${deleting ? "Deleting..." : "Delete"}
          </button>
        </div>

        <div class="memory-value">${escapeHtml(value)}</div>
      </article>
    `;
  }

  function renderMemory() {
    cacheDom();
    if (!dom.memoryList) return;

    const items = asArray(state.memoryItems);
    if (!items.length) {
      dom.memoryList.innerHTML = `<div class="empty-panel-note">No memory saved yet.</div>`;
      return;
    }

    dom.memoryList.innerHTML = items.map(buildMemoryHtml).join("");
  }

  render.memoryImpl = renderMemory;
})();