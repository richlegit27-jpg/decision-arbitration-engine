(() => {
  "use strict";

  if (window.__novaMemoryLoaded) return;
  window.__novaMemoryLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.memory = Nova.memory || {};

  const API = {
    list: "/api/memory",
    add: "/api/memory/add",
    delete: "/api/memory/delete",
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  async function parseJsonSafe(response) {
    const text = await response.text();
    try {
      return text ? JSON.parse(text) : {};
    } catch {
      return {};
    }
  }

  async function apiGet(url) {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      credentials: "same-origin",
    });

    const data = await parseJsonSafe(response);
    if (!response.ok) {
      throw new Error(data.error || `GET failed: ${url}`);
    }
    return data;
  }

  async function apiPost(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      credentials: "same-origin",
      body: JSON.stringify(payload || {}),
    });

    const data = await parseJsonSafe(response);
    if (!response.ok) {
      throw new Error(data.error || `POST failed: ${url}`);
    }
    return data;
  }

  function getStateBucket() {
    Nova.state = Nova.state || {};
    if (!Array.isArray(Nova.state.memoryItems)) {
      Nova.state.memoryItems = [];
    }
    return Nova.state;
  }

  function normalizeMemoryItems(payload) {
    const candidates = [
      payload?.items,
      payload?.memory,
      payload?.memories,
      payload?.data?.items,
      payload?.data?.memory,
      payload?.data?.memories,
    ];

    for (const value of candidates) {
      if (Array.isArray(value)) return value;
    }

    return [];
  }

  function resolveMemoryId(item) {
    return String(
      item?.id ||
      item?.memory_id ||
      item?.uuid ||
      ""
    ).trim();
  }

  function resolveMemoryKind(item) {
    return String(
      item?.kind ||
      item?.type ||
      item?.category ||
      "memory"
    ).trim() || "memory";
  }

  function resolveMemoryValue(item) {
    return String(
      item?.value ||
      item?.text ||
      item?.content ||
      item?.memory ||
      ""
    ).trim();
  }

  function resolveTimestamp(item) {
    return String(
      item?.updated_at ||
      item?.created_at ||
      item?.timestamp ||
      item?.time ||
      ""
    ).trim();
  }

  function formatTimeLabel(item) {
    const raw = resolveTimestamp(item);
    if (!raw) return "saved";

    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return "saved";

    return date.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function render() {
    const state = getStateBucket();
    const memoryList = byId("memoryList");
    if (!memoryList) return;

    const items = Array.isArray(state.memoryItems) ? state.memoryItems : [];

    if (!items.length) {
      memoryList.innerHTML = `<div class="memory-empty">No saved memory yet.</div>`;
      return;
    }

    memoryList.innerHTML = items
      .map((item) => {
        const id = resolveMemoryId(item);
        const kind = resolveMemoryKind(item);
        const value = resolveMemoryValue(item);
        const meta = formatTimeLabel(item);

        return `
          <div class="memory-card" data-memory-id="${escapeHtml(id)}">
            <div class="memory-main">
              <div class="memory-kind">${escapeHtml(kind)}</div>
              <div class="memory-value">${escapeHtml(value || "(empty)")}</div>
              <div class="memory-meta">${escapeHtml(meta)}</div>
            </div>
            <div class="memory-actions">
              <button
                class="icon-btn"
                type="button"
                data-memory-delete="${escapeHtml(id)}"
                aria-label="Delete memory"
                title="Delete memory"
              >
                🗑
              </button>
            </div>
          </div>
        `;
      })
      .join("");
  }

  async function refresh() {
    const payload = await apiGet(API.list);
    const state = getStateBucket();
    state.memoryItems = normalizeMemoryItems(payload);
    render();
    return state.memoryItems;
  }

  async function addMemoryFromValue(rawValue) {
    const value = String(rawValue || "").trim();
    if (!value) return false;

    await apiPost(API.add, {
      value,
      text: value,
      content: value,
      kind: "note",
      type: "note",
    });

    const memoryInput = byId("memoryInput");
    if (memoryInput) {
      memoryInput.value = "";
    }

    await refresh();
    return true;
  }

  async function deleteMemory(memoryId) {
    const id = String(memoryId || "").trim();
    if (!id) return false;

    await apiPost(API.delete, {
      id,
      memory_id: id,
    });

    const state = getStateBucket();
    state.memoryItems = (state.memoryItems || []).filter(
      (item) => resolveMemoryId(item) !== id
    );
    render();

    try {
      await refresh();
    } catch (error) {
      console.error("Nova memory refresh after delete failed:", error);
    }

    return true;
  }

  function bindAddButton() {
    const addMemoryBtn = byId("addMemoryBtn");
    const memoryInput = byId("memoryInput");

    if (!addMemoryBtn || addMemoryBtn.__novaMemoryAddBound) return;
    addMemoryBtn.__novaMemoryAddBound = true;

    addMemoryBtn.addEventListener("click", async (event) => {
      event.preventDefault();

      try {
        const value = memoryInput ? memoryInput.value : "";
        await addMemoryFromValue(value);
      } catch (error) {
        console.error("Nova add memory failed:", error);
      }
    });
  }

  function bindInputEnter() {
    const memoryInput = byId("memoryInput");
    if (!memoryInput || memoryInput.__novaMemoryEnterBound) return;

    memoryInput.__novaMemoryEnterBound = true;
    memoryInput.addEventListener("keydown", async (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();

      try {
        await addMemoryFromValue(memoryInput.value);
      } catch (error) {
        console.error("Nova add memory by enter failed:", error);
      }
    });
  }

  function bindListEvents() {
    const memoryList = byId("memoryList");
    if (!memoryList || memoryList.__novaMemoryListBound) return;

    memoryList.__novaMemoryListBound = true;
    memoryList.addEventListener("click", async (event) => {
      const deleteBtn = event.target.closest("[data-memory-delete]");
      if (!deleteBtn) return;

      event.preventDefault();

      try {
        await deleteMemory(deleteBtn.getAttribute("data-memory-delete"));
      } catch (error) {
        console.error("Nova delete memory failed:", error);
      }
    });
  }

  async function bootstrap() {
    bindAddButton();
    bindInputEnter();
    bindListEvents();

    try {
      await refresh();
    } catch (error) {
      console.error("Nova memory bootstrap failed:", error);
      render();
    }

    return true;
  }

  Nova.memory.refresh = refresh;
  Nova.memory.render = render;
  Nova.memory.addMemoryFromValue = addMemoryFromValue;
  Nova.memory.deleteMemory = deleteMemory;
  Nova.memory.bootstrap = bootstrap;

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      () => {
        bootstrap().catch((error) => {
          console.error("Nova memory DOM bootstrap failed:", error);
        });
      },
      { once: true }
    );
  } else {
    bootstrap().catch((error) => {
      console.error("Nova memory immediate bootstrap failed:", error);
    });
  }
})();