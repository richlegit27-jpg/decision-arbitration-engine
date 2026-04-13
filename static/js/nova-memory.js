(function () {
  "use strict";

  var VERSION = "memory-split-2026-04-12-001";

  function bridge() {
    return window.NovaMemoryBridge || null;
  }

  function text(value) {
    return String(value == null ? "" : value).trim();
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeObject(value) {
    return value && typeof value === "object" ? value : {};
  }

  function fallbackEscapeHtml(value) {
    return text(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function getState() {
    var b = bridge();
    return b && typeof b.getState === "function" ? b.getState() : {};
  }

  function getElements() {
    var b = bridge();
    return b && typeof b.getElements === "function" ? b.getElements() : {};
  }

  function escapeHtml(value) {
    var b = bridge();
    if (b && typeof b.escapeHtml === "function") {
      return b.escapeHtml(value);
    }
    return fallbackEscapeHtml(value);
  }

  function formatTimeAgo(value) {
    var b = bridge();
    if (b && typeof b.formatTimeAgo === "function") {
      return b.formatTimeAgo(value);
    }
    return text(value);
  }

  function showToast(message, kind) {
    var b = bridge();
    if (b && typeof b.showToast === "function") {
      b.showToast(message, kind);
    }
  }

  function warn() {
    var b = bridge();
    if (b && typeof b.warn === "function") {
      b.warn.apply(null, arguments);
      return;
    }
    try {
      console.warn.apply(console, arguments);
    } catch (error) {}
  }

  function openRail() {
    var b = bridge();
    if (b && typeof b.openRail === "function") {
      b.openRail();
    }
  }

  function setRailTab(tabName) {
    var b = bridge();
    if (b && typeof b.setRailTab === "function") {
      b.setRailTab(tabName);
    }
  }

  function setRailSelectedItem(kind, itemId) {
    var b = bridge();
    if (b && typeof b.setRailSelectedItem === "function") {
      b.setRailSelectedItem(kind, itemId);
    }
  }

  function apiPost(url, body, extra) {
    var b = bridge();
    if (b && typeof b.apiPost === "function") {
      return b.apiPost(url, body, extra);
    }
    return Promise.reject(new Error("NovaMemoryBridge.apiPost unavailable"));
  }

  function refreshState() {
    var b = bridge();
    if (b && typeof b.refreshState === "function") {
      return b.refreshState();
    }
    return Promise.resolve();
  }

  function normalizeMemoryItem(item) {
    var b = bridge();
    if (b && typeof b.normalizeMemoryItem === "function") {
      return b.normalizeMemoryItem(item);
    }

    var entry = safeObject(item);
    return {
      id: text(entry.id),
      kind: text(entry.kind || "note"),
      source: text(entry.source || ""),
      text: text(entry.text || entry.content || entry.body || ""),
      preview: text(entry.preview || entry.text || entry.content || entry.body || ""),
      created_at: text(entry.created_at || ""),
      updated_at: text(entry.updated_at || ""),
    };
  }

  function currentMemoryItems() {
    var state = safeObject(getState());
    return safeArray(state.memory).map(normalizeMemoryItem);
  }

  function memoryViewerHtml(item) {
    var entry = normalizeMemoryItem(item);
    var kind = escapeHtml(entry.kind || "note");
    var source = escapeHtml(entry.source || "unknown");
    var createdAt = escapeHtml(formatTimeAgo(entry.updated_at || entry.created_at || ""));
    var body = escapeHtml(entry.text || entry.preview || "");

    return (
      '<div class="nova-memory-viewer">' +
        '<div class="nova-viewer-header">' +
          '<div class="nova-viewer-kicker">Memory</div>' +
          '<h3 class="nova-viewer-title">' + kind + "</h3>" +
          '<div class="nova-viewer-meta">source=' + source + " · " + createdAt + "</div>" +
        "</div>" +
        '<div class="nova-viewer-body">' +
          '<pre style="white-space:pre-wrap;word-break:break-word;margin:0;">' + body + "</pre>" +
        "</div>" +
      "</div>"
    );
  }

  function renderMemoryListItem(item) {
    var entry = normalizeMemoryItem(item);

    return (
      '<article class="nova-memory-card" data-memory-id="' + escapeHtml(entry.id) + '">' +
        '<button type="button" class="nova-memory-open" data-memory-open="' + escapeHtml(entry.id) + '">' +
          '<div class="nova-memory-card-top">' +
            '<span class="nova-memory-kind">' + escapeHtml(entry.kind || "note") + "</span>" +
            '<span class="nova-memory-time">' + escapeHtml(formatTimeAgo(entry.updated_at || entry.created_at || "")) + "</span>" +
          "</div>" +
          '<div class="nova-memory-preview">' + escapeHtml(entry.preview || entry.text || "Untitled memory") + "</div>" +
        "</button>" +
        '<div class="nova-memory-actions">' +
          '<button type="button" class="nova-memory-delete" data-memory-delete="' + escapeHtml(entry.id) + '">Delete</button>' +
        "</div>" +
      "</article>"
    );
  }

  function renderMemory() {
    var els = safeObject(getElements());
    if (!els.memoryList) return;

    var items = currentMemoryItems();

    if (els.memoryEmpty) {
      els.memoryEmpty.hidden = items.length > 0;
    }

    if (!items.length) {
      els.memoryList.innerHTML = "";
      return;
    }

    els.memoryList.innerHTML = items.map(renderMemoryListItem).join("");
  }

  function openMemoryItem(memoryId) {
    var els = safeObject(getElements());
    var items = currentMemoryItems();

    var found = null;
    for (var i = 0; i < items.length; i += 1) {
      if (text(items[i].id) === text(memoryId)) {
        found = items[i];
        break;
      }
    }

    if (!found) {
      showToast("Memory not found", "error");
      return;
    }

    openRail();
    setRailTab("memory");
    setRailSelectedItem("memory", found.id);

    if (els.railViewer) {
      els.railViewer.innerHTML = memoryViewerHtml(found);
    }

    highlightSelectedMemory(found.id);
  }

  function highlightSelectedMemory(memoryId) {
    var els = safeObject(getElements());
    if (!els.memoryList) return;

    var nodes = els.memoryList.querySelectorAll("[data-memory-id]");
    for (var i = 0; i < nodes.length; i += 1) {
      var node = nodes[i];
      var isActive = text(node.getAttribute("data-memory-id")) === text(memoryId);
      node.classList.toggle("is-active", isActive);
    }
  }

  function deleteMemory(memoryId) {
    if (!memoryId) return;

    apiPost("/api/memory/delete", { memory_id: memoryId })
      .then(function () {
        showToast("Memory deleted", "success");
        return refreshState();
      })
      .then(function () {
        renderMemory();
      })
      .catch(function (error) {
        warn("memory delete failed", error);
        showToast("Memory delete failed", "error");
      });
  }

  function bindMemoryClicks() {
    var els = safeObject(getElements());
    if (!els.memoryList || els.memoryList.dataset.boundMemorySplit === "1") {
      return;
    }

    els.memoryList.dataset.boundMemorySplit = "1";

    els.memoryList.addEventListener("click", function (event) {
      var openBtn = event.target.closest("[data-memory-open]");
      if (openBtn) {
        var memoryId = text(openBtn.getAttribute("data-memory-open"));
        if (memoryId) {
          openMemoryItem(memoryId);
        }
        return;
      }

      var deleteBtn = event.target.closest("[data-memory-delete]");
      if (deleteBtn) {
        var deleteId = text(deleteBtn.getAttribute("data-memory-delete"));
        if (deleteId) {
          deleteMemory(deleteId);
        }
      }
    });
  }

  function boot() {
    bindMemoryClicks();
    renderMemory();
  }

  window.NovaMemoryModule = {
    version: VERSION,
    bind: bindMemoryClicks,
    render: renderMemory,
    open: openMemoryItem,
    viewerHtml: memoryViewerHtml,
    boot: boot,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();