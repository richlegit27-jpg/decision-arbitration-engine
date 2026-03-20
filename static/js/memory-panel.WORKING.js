(() => {
"use strict";

if (window.__novaMemoryPanelLoaded) {
  console.warn("Nova memory panel already loaded.");
  return;
}
window.__novaMemoryPanelLoaded = true;

window.NovaApp = window.NovaApp || {};
const app = window.NovaApp;

function byId(id) {
  return document.getElementById(id);
}

function nowIso() {
  return new Date().toISOString();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function safeRandomId() {
  try {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
  } catch (error) {
    console.warn("[Nova memory] randomUUID unavailable.", error);
  }

  return `mem_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function ensureState() {
  app.state = app.state || {};

  if (!app.state.memory || typeof app.state.memory !== "object") {
    app.state.memory = {
      isOpen: false,
      items: []
    };
  }

  if (!Array.isArray(app.state.memory.items)) {
    app.state.memory.items = [];
  }

  if (!app.state.ui || typeof app.state.ui !== "object") {
    app.state.ui = {};
  }

  if (typeof app.state.ui.memoryOpen !== "boolean") {
    app.state.ui.memoryOpen = false;
  }

  return app.state;
}

function getMemoryState() {
  return ensureState().memory;
}

function getMemoryItems() {
  return Array.isArray(getMemoryState().items) ? getMemoryState().items : [];
}

function setMemoryItems(items) {
  getMemoryState().items = Array.isArray(items) ? items : [];
}

function normalizeMemoryItem(item) {
  const text = String(item?.text ?? "").trim();

  return {
    id: String(item?.id || safeRandomId()),
    text,
    created_at: String(item?.created_at || nowIso())
  };
}

function getPanel() {
  return byId("memoryPanel");
}

function getList() {
  return byId("memoryList");
}

function getOpenButtons() {
  return [
    byId("btnOpenMemory"),
    byId("openMemoryBtn"),
    byId("memoryOpenBtn")
  ].filter(Boolean);
}

function getCloseButtons() {
  return [
    byId("btnCloseMemory"),
    byId("btnCloseMemoryPanel"),
    byId("closeMemoryBtn"),
    byId("hideMemoryBtn")
  ].filter(Boolean);
}

function getClearBtn() {
  return byId("btnClearMemory") || byId("clearMemoryBtn");
}

function getAddBtn() {
  return byId("btnAddMemory") || byId("addMemoryBtn");
}

function getExportBtn() {
  return byId("btnExportMemory") || byId("exportMemoryBtn");
}

function focusSafely(element) {
  if (!element || typeof element.focus !== "function") return;

  try {
    element.focus({ preventScroll: true });
  } catch (_) {
    try {
      element.focus();
    } catch (_) {}
  }
}

function getSafeFocusTarget() {
  return (
    getOpenButtons()[0]
    || byId("sidebarToggleBtn")
    || byId("topbarSidebarToggleBtn")
    || byId("messageInput")
    || document.body
  );
}

function moveFocusOutOfPanel() {
  const panel = getPanel();
  const active = document.activeElement;

  if (!panel || !active) return;
  if (!panel.contains(active)) return;

  focusSafely(getSafeFocusTarget());
}

function notifySuccess(message) {
  if (typeof app.notifySuccess === "function") {
    app.notifySuccess(message);
    return;
  }

  console.log(message);
}

function notifyError(message) {
  if (typeof app.notifyError === "function") {
    app.notifyError(message);
    return;
  }

  console.error(message);
}

async function askText(title, message, defaultValue = "") {
  if (typeof app.askText === "function") {
    return app.askText(title, message, defaultValue);
  }

  const value = window.prompt(`${title}\n\n${message}`, defaultValue);
  return value == null ? "" : String(value);
}

function syncPanelState(isOpen) {
  const panel = getPanel();
  const state = ensureState();
  const open = !!isOpen;

  state.memory.isOpen = open;
  state.ui.memoryOpen = open;

  if (!open) {
    moveFocusOutOfPanel();
  }

  document.body.classList.toggle("memory-open", open);

  if (!panel) return;

  panel.classList.toggle("is-open", open);

  if (open) {
    panel.removeAttribute("inert");
    panel.setAttribute("aria-hidden", "false");
  } else {
    panel.setAttribute("inert", "");
    panel.setAttribute("aria-hidden", "true");
  }
}

function openMemoryPanel() {
  syncPanelState(true);
  renderMemoryList();
}

function closeMemoryPanel() {
  syncPanelState(false);
}

async function persistMemoryToState() {
  const items = getMemoryItems();

  try {
    localStorage.setItem("nova_memory", JSON.stringify(items));
  } catch (error) {
    console.error("[Nova memory] localStorage save failed.", error);
  }

  try {
    if (typeof app.persistState === "function") {
      await app.persistState();
    }
  } catch (error) {
    console.error("[Nova memory] app.persistState failed.", error);
  }

  try {
    if (typeof app.saveState === "function") {
      await app.saveState();
    }
  } catch (error) {
    console.error("[Nova memory] app.saveState failed.", error);
  }
}

function persistMemoryToStateDeferred() {
  window.setTimeout(() => {
    persistMemoryToState().catch((error) => {
      console.error("[Nova memory] deferred save failed.", error);
    });
  }, 0);
}

async function loadMemoryFromState() {
  try {
    const existing = app?.state?.memory?.items;
    if (Array.isArray(existing)) {
      const normalized = existing
        .map(normalizeMemoryItem)
        .filter((item) => item.text);

      setMemoryItems(normalized);
      return normalized;
    }
  } catch (error) {
    console.error("[Nova memory] app state read failed.", error);
  }

  try {
    const raw = localStorage.getItem("nova_memory");
    if (!raw) {
      setMemoryItems([]);
      return [];
    }

    const parsed = JSON.parse(raw);
    const items = Array.isArray(parsed)
      ? parsed.map(normalizeMemoryItem).filter((item) => item.text)
      : [];

    setMemoryItems(items);
    return items;
  } catch (error) {
    console.error("[Nova memory] load failed.", error);
    setMemoryItems([]);
    return [];
  }
}

function buildEmptyMarkup() {
  return `<div class="memory-empty">No memory items yet.</div>`;
}

function buildMemoryMarkup(items) {
  return items.map((item, index) => {
    let createdText = item.created_at;

    try {
      createdText = new Date(item.created_at).toLocaleString();
    } catch (error) {
      console.warn("[Nova memory] date parse failed.", error);
    }

    return `
      <div class="memory-card" data-memory-id="${escapeHtml(item.id)}">
        <div class="memory-card-top">
          <div class="memory-card-label">Memory</div>
          <div class="memory-card-index">#${index + 1}</div>
        </div>

        <div class="memory-card-text">${escapeHtml(item.text)}</div>

        <div class="memory-card-meta">${escapeHtml(createdText)}</div>

        <div class="memory-card-actions">
          <button
            type="button"
            class="ghost-btn memory-delete-btn"
            data-delete-memory-id="${escapeHtml(item.id)}"
            aria-label="Delete memory"
            title="Delete memory"
          >
            Delete
          </button>
        </div>
      </div>
    `;
  }).join("");
}

function renderMemoryList() {
  const list = getList();
  if (!list) return;

  const items = getMemoryItems();
  list.innerHTML = items.length ? buildMemoryMarkup(items) : buildEmptyMarkup();
}

async function refreshMemoryList() {
  await loadMemoryFromState();
  renderMemoryList();
}

async function addMemoryItem() {
  try {
    const text = await askText("Add memory", "Save something to memory.", "");
    const clean = String(text || "").trim();

    if (!clean) {
      return;
    }

    const newItem = normalizeMemoryItem({ text: clean });
    const nextItems = [newItem, ...getMemoryItems()];

    setMemoryItems(nextItems);
    openMemoryPanel();
    renderMemoryList();
    notifySuccess("Memory added.");
    persistMemoryToStateDeferred();
  } catch (error) {
    console.error(error);
    notifyError(error?.message || "Failed to add memory.");
  }
}

async function deleteMemoryItem(id) {
  try {
    const targetId = String(id || "").trim();
    if (!targetId) return;

    const nextItems = getMemoryItems().filter((item) => item.id !== targetId);
    setMemoryItems(nextItems);
    renderMemoryList();
    persistMemoryToStateDeferred();
  } catch (error) {
    console.error(error);
    notifyError(error?.message || "Failed to delete memory.");
  }
}

async function clearMemory() {
  try {
    const ok = window.confirm("Delete all memories?");
    if (!ok) return;

    setMemoryItems([]);
    renderMemoryList();
    persistMemoryToStateDeferred();
    notifySuccess("Memory cleared.");
  } catch (error) {
    console.error(error);
    notifyError(error?.message || "Failed to clear memory.");
  }
}

function exportMemory() {
  try {
    const items = getMemoryItems();
    const blob = new Blob(
      [JSON.stringify(items, null, 2)],
      { type: "application/json;charset=utf-8" }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `nova_memory_${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    notifySuccess("Memory exported.");
  } catch (error) {
    console.error(error);
    notifyError(error?.message || "Failed to export memory.");
  }
}

function bindClickOnce(el, key, handler) {
  if (!el) return;
  const flag = `novaMemoryBound${key}`;
  if (el.dataset[flag] === "1") return;
  el.dataset[flag] = "1";
  el.addEventListener("click", handler);
}

function bindButtons() {
  const list = getList();

  getOpenButtons().forEach((btn) => {
    bindClickOnce(btn, "Open", (event) => {
      event.preventDefault();
      openMemoryPanel();
    });
  });

  getCloseButtons().forEach((btn) => {
    bindClickOnce(btn, "Close", (event) => {
      event.preventDefault();
      closeMemoryPanel();
    });
  });

  bindClickOnce(getClearBtn(), "Clear", (event) => {
    event.preventDefault();
    clearMemory();
  });

  bindClickOnce(getAddBtn(), "Add", (event) => {
    event.preventDefault();
    addMemoryItem();
  });

  bindClickOnce(getExportBtn(), "Export", (event) => {
    event.preventDefault();
    exportMemory();
  });

  if (list && list.dataset.novaMemoryListBound !== "1") {
    list.dataset.novaMemoryListBound = "1";
    list.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      const deleteBtn = target ? target.closest("[data-delete-memory-id]") : null;
      if (!deleteBtn) return;

      event.preventDefault();
      const memoryId = deleteBtn.getAttribute("data-delete-memory-id");
      deleteMemoryItem(memoryId);
    });
  }

  if (document.body.dataset.novaMemoryEscapeBound !== "1") {
    document.body.dataset.novaMemoryEscapeBound = "1";
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && ensureState().ui.memoryOpen) {
        closeMemoryPanel();
      }
    });
  }
}

function initMemoryPanel() {
  ensureState();
  bindButtons();
  refreshMemoryList().catch((error) => {
    console.error("[Nova memory] init refresh failed.", error);
  });

  if (app.state.memory.isOpen || app.state.ui.memoryOpen) {
    syncPanelState(true);
  } else {
    syncPanelState(false);
  }

  console.log("Nova memory panel loaded.");
}

app.memoryPanel = app.memoryPanel || {};
app.memoryPanel.open = openMemoryPanel;
app.memoryPanel.close = closeMemoryPanel;
app.memoryPanel.refresh = refreshMemoryList;
app.memoryPanel.add = addMemoryItem;
app.memoryPanel.clear = clearMemory;
app.memoryPanel.export = exportMemory;
app.memoryPanel.getItems = getMemoryItems;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initMemoryPanel, { once: true });
} else {
  initMemoryPanel();
}
})();