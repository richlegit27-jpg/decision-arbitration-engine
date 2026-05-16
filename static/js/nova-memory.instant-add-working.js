(function () {
  "use strict";

  const state = {
    items: [],
    filtered: [],
    loading: false,
    query: "",
    kind: "all",
    selectedId: "",
  };

  const els = {
    panel: null,
    list: null,
    empty: null,
    search: null,
    kind: null,
    refresh: null,
    addBtn: null,
    addText: null,
    addKind: null,
    addSource: null,
    status: null,
    count: null,
  };

  function q(selector) {
    return document.querySelector(selector);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function shortText(value, maxLen) {
    const text = String(value || "").trim();
    if (!text) return "";
    if (text.length <= maxLen) return text;
    return text.slice(0, maxLen - 1) + "…";
  }

  function formatDate(value) {
    if (!value) return "";
    try {
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return String(value);
      return d.toLocaleString();
    } catch (err) {
      return String(value || "");
    }
  }

  async function api(url, options) {
    const res = await fetch(url, {
      method: options && options.method ? options.method : "GET",
      headers: {
        "Content-Type": "application/json",
      },
      body: options && options.body ? JSON.stringify(options.body) : undefined,
    });

    let data = null;
    try {
      data = await res.json();
    } catch (err) {
      data = null;
    }

    if (!res.ok) {
      const message =
        (data && (data.error || data.message)) ||
        `HTTP ${res.status}`;
      throw new Error(message);
    }

    return data || {};
  }

  function getMemoryItems(payload) {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload.memory)) return payload.memory;
    if (payload.memory && Array.isArray(payload.memory.items)) return payload.memory.items;
    if (payload.items && Array.isArray(payload.items)) return payload.items;
    return [];
  }

  function getKinds(items) {
    const kinds = new Set();
    items.forEach(function (item) {
      const kind = String(item.kind || "").trim();
      if (kind) kinds.add(kind);
    });
    return ["all"].concat(Array.from(kinds).sort());
  }

  function syncEls() {
    els.panel = q("[data-memory-panel]") || q("#memory-panel");
    els.list = q("[data-memory-list]") || q("#memory-list");
    els.empty = q("[data-memory-empty]");
    els.search = q("[data-memory-search]");
    els.kind = q("[data-memory-kind]");
    els.refresh = q("[data-memory-refresh]");
    els.addBtn = q("[data-memory-add-button]");
    els.addText = q("[data-memory-add-text]");
    els.addKind = q("[data-memory-add-kind]");
    els.addSource = q("[data-memory-add-source]");
    els.status = q("[data-memory-status]");
    els.count = q("[data-memory-count]");
  }

  function setStatus(text, type) {
    if (!els.status) return;
    els.status.textContent = text || "";
    els.status.dataset.state = type || "idle";
  }

  function buildKindOptions() {
    if (!els.kind) return;
    const current = state.kind || "all";
    const kinds = getKinds(state.items);
    els.kind.innerHTML = kinds
      .map(function (kind) {
        return `<option value="${escapeHtml(kind)}"${kind === current ? " selected" : ""}>${escapeHtml(kind)}</option>`;
      })
      .join("");
  }

  function applyFilters() {
    const query = String(state.query || "").trim().toLowerCase();
    const kind = String(state.kind || "all").trim().toLowerCase();

    state.filtered = state.items.filter(function (item) {
      const itemKind = String(item.kind || "").trim().toLowerCase();
      const haystack = [
        item.text,
        item.kind,
        item.source,
        item.session_id,
        item.preview,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const kindOk = kind === "all" ? true : itemKind === kind;
      const queryOk = !query ? true : haystack.includes(query);

      return kindOk && queryOk;
    });

    renderList();
  }

function memoryCardHtml(item) {
  const id = String(item.id || "");
  const active = id && id === state.selectedId;
  const kind = String(item.kind || "memory");
  const text = String(item.text || "");
  const source = String(item.source || "");
  const sessionId = String(item.session_id || "");
  const createdAt = formatDate(item.created_at);
  const updatedAt = formatDate(item.updated_at);
  const pinned = Boolean(item.pinned);
  const weight = item.weight == null ? "1.0" : String(item.weight);

  return `
    <article class="nova-memory-card${active ? " is-active" : ""}" data-memory-id="${escapeHtml(id)}">
      <div class="nova-memory-card__top">
        <div class="nova-memory-card__badges">
          <span class="nova-memory-badge">${escapeHtml(kind)}</span>
          ${pinned ? `<span class="nova-memory-badge is-soft">Pinned</span>` : ""}
          <span class="nova-memory-badge is-soft">W:${escapeHtml(weight)}</span>
          ${source ? `<span class="nova-memory-badge is-soft">${escapeHtml(source)}</span>` : ""}
        </div>

        <div class="nova-memory-card__actions">
          <button
            class="nova-memory-icon-btn"
            type="button"
            data-memory-pin="${escapeHtml(id)}"
            data-memory-pinned="${pinned ? "1" : "0"}"
            title="Pin"
          >
            ${pinned ? "Unpin" : "Pin"}
          </button>

          <button
            class="nova-memory-icon-btn"
            type="button"
            data-memory-copy="${escapeHtml(id)}"
            title="Copy"
          >
            Copy
          </button>

          <button
            class="nova-memory-icon-btn"
            type="button"
            data-memory-edit="${escapeHtml(id)}"
            title="Edit"
          >
            Edit
          </button>

          <button
            class="nova-memory-icon-btn is-danger"
            type="button"
            data-memory-delete="${escapeHtml(id)}"
            title="Delete"
          >
            Delete
          </button>
        </div>
      </div>

      <div class="nova-memory-card__text">
        ${escapeHtml(text || "(empty memory)")}
      </div>

      <div class="nova-memory-card__meta">
        ${sessionId ? `<div><strong>Session:</strong> ${escapeHtml(shortText(sessionId, 22))}</div>` : ""}
        ${createdAt ? `<div><strong>Created:</strong> ${escapeHtml(createdAt)}</div>` : ""}
        ${updatedAt ? `<div><strong>Updated:</strong> ${escapeHtml(updatedAt)}</div>` : ""}
      </div>
    </article>
  `;
}

function renderList() {
  if (!els.list) return;

  const items = state.filtered || [];

  if (els.count) {
    els.count.textContent = `${items.length}`;
  }

  if (!items.length) {
    els.list.innerHTML = "";

    if (els.empty) {
      els.empty.hidden = false;
    }

    return;
  }

  if (els.empty) {
    els.empty.hidden = true;
  }

  els.list.innerHTML = items.map(memoryCardHtml).join("");
}
  
async function loadMemory() {
  state.loading = true;
  setStatus("Loading memory…", "loading");

  try {
    const payload = await api(`/api/memory?ts=${Date.now()}`);
    state.items = getMemoryItems(payload);
    buildKindOptions();
    applyFilters();
    setStatus(`Loaded ${state.items.length} memories`, "ok");
  } catch (err) {
    console.error("[NovaMemory] load failed:", err);
    state.items = [];
    state.filtered = [];
    renderList();
    setStatus(`Memory load failed: ${err.message}`, "error");
  } finally {
    state.loading = false;
  }
}

async function addMemory() {
  const text = els.addText ? String(els.addText.value || "").trim() : "";
  const kind = els.addKind ? String(els.addKind.value || "general").trim() : "general";
  const source = els.addSource ? String(els.addSource.value || "manual").trim() : "manual";

  if (!text) {
    setStatus("Enter memory text first", "error");
    if (els.addText) els.addText.focus();
    return;
  }

  const tempItem = {
    id: "temp_" + Date.now(),
    text: text,
    kind: kind,
    source: source,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    weight: 1.0,
  };

  if (els.addText) els.addText.value = "";

  state.items = [tempItem].concat(state.items || []);
  buildKindOptions();
  applyFilters();
  setStatus("Saving memory…", "loading");

  try {
    const payload = await api("/api/memory/add", {
      method: "POST",
      body: {
        text,
        kind,
        source,
      },
    });

    const savedItem =
      payload.item ||
      payload.memory_item ||
      payload.saved_item ||
      null;

    if (savedItem && savedItem.id) {
      state.items = (state.items || []).map(function (item) {
        return item.id === tempItem.id ? savedItem : item;
      });
      buildKindOptions();
      applyFilters();
    } else {
      await loadMemory();
    }

    setStatus("Memory saved", "ok");
  } catch (err) {
    console.error("[NovaMemory] add failed:", err);

    state.items = (state.items || []).filter(function (item) {
      return item.id !== tempItem.id;
    });

    applyFilters();
    setStatus(`Memory save failed: ${err.message}`, "error");
  }
}

  async function deleteMemory(id) {
    if (!id) return;
    setStatus("Deleting memory…", "loading");

    try {
      await api("/api/memory/delete", {
        method: "POST",
        body: { id },
      });

      if (state.selectedId === id) state.selectedId = "";
      await loadMemory();
      setStatus("Memory deleted", "ok");
    } catch (err) {
      console.error("[NovaMemory] delete failed:", err);
      setStatus(`Memory delete failed: ${err.message}`, "error");
    }
  }

  async function copyMemory(id) {
    const item = state.items.find(function (m) {
      return String(m.id || "") === String(id || "");
    });
    if (!item) return;

    try {
      await navigator.clipboard.writeText(String(item.text || ""));
      setStatus("Memory copied", "ok");
    } catch (err) {
      console.error("[NovaMemory] copy failed:", err);
      setStatus("Copy failed", "error");
    }
  }

function wireEvents() {
  if (els.search) {
    els.search.addEventListener("input", function (e) {
      state.query = e.target.value || "";
      applyFilters();
    });
  }

  if (els.kind) {
    els.kind.addEventListener("change", function (e) {
      state.kind = e.target.value || "all";
      applyFilters();
    });
  }

  if (els.refresh) {
    els.refresh.addEventListener("click", function () {
      loadMemory();
    });
  }

  if (els.addBtn) {
    els.addBtn.addEventListener("click", function () {
      addMemory();
    });
  }

  if (els.addText) {
    els.addText.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        addMemory();
      }
    });
  }

  if (els.list) {
    els.list.addEventListener("click", async function (e) {
      const pinBtn = e.target.closest("[data-memory-pin]");
      if (pinBtn) {
        const id = pinBtn.getAttribute("data-memory-pin");
        const isPinned = pinBtn.getAttribute("data-memory-pinned") === "1";

        try {
          await api("/api/memory/pin", {
            method: "POST",
            body: {
              id: id,
              pinned: !isPinned,
            },
          });

          await loadMemory();
          setStatus(isPinned ? "Unpinned" : "Pinned", "ok");
        } catch (err) {
          console.error("[NovaMemory] pin failed:", err);
          setStatus("Pin failed", "error");
        }

        return;
      }

      const deleteBtn = e.target.closest("[data-memory-delete]");
      if (deleteBtn) {
        deleteMemory(deleteBtn.getAttribute("data-memory-delete"));
        return;
      }

      const copyBtn = e.target.closest("[data-memory-copy]");
      if (copyBtn) {
        copyMemory(copyBtn.getAttribute("data-memory-copy"));
        return;
      }

      const editBtn = e.target.closest("[data-memory-edit]");
      if (editBtn) {
        const id = editBtn.getAttribute("data-memory-edit");
        const item = state.items.find(function (m) {
          return String(m.id || "") === String(id || "");
        });

        if (!item) return;

        const nextText = window.prompt("Edit memory:", String(item.text || ""));
        if (nextText == null) return;

        const cleanText = String(nextText || "").trim();
        if (!cleanText) {
          setStatus("Memory text cannot be empty", "error");
          return;
        }

        try {
          await api("/api/memory/update", {
            method: "POST",
            body: {
              id: id,
              text: cleanText,
              kind: item.kind || "note",
            },
          });

          await loadMemory();
          setStatus("✓ Memory updated", "ok");
        } catch (err) {
          console.error("[NovaMemory] update failed:", err);
          setStatus(`Memory update failed: ${err.message}`, "error");
        }

        return;
      }

      const card = e.target.closest("[data-memory-id]");
      if (card) {
        const id = card.getAttribute("data-memory-id") || "";
        state.selectedId = id;

        const item = state.items.find(function (m) {
          return String(m.id || "") === id;
        });

        renderList();

        if (!item) return;

        const viewer =
          document.querySelector("[data-rail-viewer]") ||
          document.querySelector("#rail-viewer");

        if (viewer) {
          viewer.hidden = false;
          viewer.innerHTML = `
            <div class="nova-viewer-shell">
              <div class="nova-viewer-title">Memory</div>
              <div class="nova-viewer-body">
                <p>${escapeHtml(item.text || "")}</p>
                <div style="margin-top:10px; font-size:12px; opacity:0.7;">
                  ${item.kind ? `<div><strong>Kind:</strong> ${escapeHtml(item.kind)}</div>` : ""}
                  ${item.source ? `<div><strong>Source:</strong> ${escapeHtml(item.source)}</div>` : ""}
                  ${item.weight ? `<div><strong>Weight:</strong> ${escapeHtml(item.weight)}</div>` : ""}
                  ${item.pinned ? `<div><strong>Pinned:</strong> yes</div>` : ""}
                </div>
              </div>
            </div>
          `;
        }

        return;
      }
    });
  }
}

  async function boot() {
    syncEls();
    if (!els.panel) {
      console.warn("[NovaMemory] panel not found");
      return;
    }

    wireEvents();
    await loadMemory();
    console.log("[NovaMemory] boot complete", { items: state.items.length });
  }

function waitForPanelAndBoot() {
  let tries = 0;
  const maxTries = 40;

  const tick = async () => {
    syncEls();

    if (els.panel) {
      await boot();

      const panel = document.querySelector('[data-rail-panel="memory"]');

      if (panel && els.addText) {
        const observer = new MutationObserver(() => {
          if (!panel.hidden && els.addText) {
            els.addText.focus();
          }
        });

        observer.observe(panel, { attributes: true });
      }

      return;
    }

    tries += 1;
    if (tries >= maxTries) {
      console.warn("[NovaMemory] panel never appeared");
      return;
    }

    setTimeout(tick, 100);
  };

  tick();

}

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", waitForPanelAndBoot);
  } else {
    waitForPanelAndBoot();
  }
})();