(() => {
  "use strict";

  if (window.__novaPhase3RepairLoaded) {
    console.warn("Nova phase 3 repair already loaded.");
    return;
  }
  window.__novaPhase3RepairLoaded = true;

  const BODY = document.body;

  const els = {
    sidebar: document.getElementById("sidebar"),
    memoryPanel: document.getElementById("memoryPanel"),
    toggleSidebar: document.getElementById("toggleSidebar"),
    mobileSidebarBtn: document.getElementById("mobileSidebarBtn"),
    memoryToggleBtnTop: document.getElementById("memoryToggleBtnTop"),
    closeMemoryBtn: document.getElementById("closeMemoryBtn"),

    newSessionBtn: document.getElementById("newSessionBtn"),
    deleteSessionBtn: document.getElementById("deleteSessionBtn"),
    renameSessionBtn: document.getElementById("renameSessionBtn"),
    duplicateSessionBtn: document.getElementById("duplicateSessionBtn"),
    pinSessionBtn: document.getElementById("pinSessionBtn"),
    exportSessionBtn: document.getElementById("exportSessionBtn"),

    sessionList: document.getElementById("sessionList"),
    sessionSearchInput: document.getElementById("sessionSearchInput"),

    chatTitle: document.getElementById("chatTitle"),
    chatSubtitle: document.getElementById("chatSubtitle"),
    memoryStatusText: document.getElementById("memoryStatusText")
  };

  function isMobile() {
    return window.innerWidth <= 768;
  }

  function setStatus(text) {
    if (els.chatSubtitle) els.chatSubtitle.textContent = text;
  }

  function setMemoryStatus(text) {
    if (els.memoryStatusText) els.memoryStatusText.textContent = text;
  }

  function setSidebarOpen(open) {
    if (!els.sidebar) return;

    if (isMobile()) {
      els.sidebar.setAttribute("aria-hidden", open ? "false" : "true");
      return;
    }

    BODY.classList.toggle("sidebar-collapsed", !open);
    els.sidebar.setAttribute("aria-hidden", "false");
  }

  function setMemoryOpen(open) {
    if (!els.memoryPanel) return;

    if (isMobile()) {
      els.memoryPanel.setAttribute("aria-hidden", open ? "false" : "true");
      return;
    }

    BODY.classList.toggle("memory-collapsed", !open);
    els.memoryPanel.setAttribute("aria-hidden", "false");
  }

  function toggleSidebar() {
    if (!els.sidebar) return;

    if (isMobile()) {
      const open = els.sidebar.getAttribute("aria-hidden") !== "false";
      setSidebarOpen(open);
      return;
    }

    const collapsed = BODY.classList.contains("sidebar-collapsed");
    setSidebarOpen(collapsed);
  }

  function toggleMemory() {
    if (!els.memoryPanel) return;

    if (isMobile()) {
      const open = els.memoryPanel.getAttribute("aria-hidden") !== "false";
      setMemoryOpen(open);
      return;
    }

    const collapsed = BODY.classList.contains("memory-collapsed");
    setMemoryOpen(collapsed);
  }

  function getSessionItems() {
    if (!els.sessionList) return [];
    return Array.from(els.sessionList.querySelectorAll(".session-item"));
  }

  function getActiveSessionItem() {
    const items = getSessionItems();
    return items.find((item) => item.classList.contains("active")) || null;
  }

  function getSessionIdFromItem(item) {
    if (!item) return "";
    return (
      item.dataset.sessionId ||
      item.getAttribute("data-session-id") ||
      item.dataset.id ||
      item.getAttribute("data-id") ||
      item.id ||
      ""
    );
  }

  function getSessionTitleFromItem(item) {
    if (!item) return "";
    const titleEl = item.querySelector(".session-item-title");
    return (titleEl?.textContent || item.textContent || "").trim();
  }

  function markActiveSession(item) {
    getSessionItems().forEach((node) => node.classList.remove("active"));
    if (item) item.classList.add("active");

    const title = getSessionTitleFromItem(item);
    if (title && els.chatTitle) {
      els.chatTitle.textContent = title;
    }
  }

  function filterSessions() {
    if (!els.sessionSearchInput || !els.sessionList) return;
    const query = els.sessionSearchInput.value.trim().toLowerCase();

    getSessionItems().forEach((item) => {
      const text = item.textContent.toLowerCase();
      item.style.display = !query || text.includes(query) ? "" : "none";
    });
  }

  async function postJSON(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {})
    });

    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      const message =
        (data && (data.error || data.message)) ||
        `Request failed: ${response.status}`;
      throw new Error(message);
    }

    return data;
  }

  async function tryPost(url, payload) {
    try {
      return await postJSON(url, payload);
    } catch (error) {
      console.warn(`POST ${url} failed:`, error);
      return null;
    }
  }

  function hardRefresh() {
    window.location.reload();
  }

  async function renameActiveSession() {
    const active = getActiveSessionItem();
    if (!active) {
      alert("Pick a chat first.");
      return;
    }

    const sessionId = getSessionIdFromItem(active);
    const currentTitle = getSessionTitleFromItem(active) || "Untitled Chat";
    const nextTitle = window.prompt("Rename chat:", currentTitle);

    if (nextTitle == null) return;

    const trimmed = nextTitle.trim();
    if (!trimmed) {
      alert("Name cannot be empty.");
      return;
    }

    setStatus("Renaming...");
    const result =
      (sessionId && await tryPost("/api/session/rename", { session_id: sessionId, name: trimmed })) ||
      (sessionId && await tryPost("/api/session/rename", { sessionId, name: trimmed })) ||
      (sessionId && await tryPost("/api/session/rename", { id: sessionId, name: trimmed }));

    if (result) {
      hardRefresh();
      return;
    }

    const titleEl = active.querySelector(".session-item-title");
    if (titleEl) titleEl.textContent = trimmed;
    if (els.chatTitle) els.chatTitle.textContent = trimmed;
    setStatus("Renamed");
  }

  async function duplicateActiveSession() {
    const active = getActiveSessionItem();
    if (!active) {
      alert("Pick a chat first.");
      return;
    }

    const sessionId = getSessionIdFromItem(active);
    if (!sessionId) {
      alert("Could not find session id for duplicate.");
      return;
    }

    setStatus("Duplicating...");
    const result =
      await tryPost("/api/session/duplicate", { session_id: sessionId }) ||
      await tryPost("/api/session/duplicate", { sessionId }) ||
      await tryPost("/api/session/duplicate", { id: sessionId });

    if (result) {
      hardRefresh();
      return;
    }

    alert("Duplicate endpoint did not respond. Frontend wiring is fixed, but backend duplicate route may still need syncing.");
    setStatus("Ready");
  }

  async function pinActiveSession() {
    const active = getActiveSessionItem();
    if (!active) {
      alert("Pick a chat first.");
      return;
    }

    const sessionId = getSessionIdFromItem(active);
    if (!sessionId) {
      alert("Could not find session id for pin.");
      return;
    }

    setStatus("Pinning...");
    const result =
      await tryPost("/api/session/pin", { session_id: sessionId }) ||
      await tryPost("/api/session/pin", { sessionId }) ||
      await tryPost("/api/session/pin", { id: sessionId });

    if (result) {
      hardRefresh();
      return;
    }

    active.classList.toggle("pinned");
    setStatus("Pinned toggle attempted");
  }

  async function deleteActiveSession() {
    const active = getActiveSessionItem();
    if (!active) {
      alert("Pick a chat first.");
      return;
    }

    const sessionId = getSessionIdFromItem(active);
    const title = getSessionTitleFromItem(active) || "this chat";
    const ok = window.confirm(`Delete "${title}"?`);

    if (!ok) return;

    setStatus("Deleting...");
    const result =
      (sessionId && await tryPost("/api/session/delete", { session_id: sessionId })) ||
      (sessionId && await tryPost("/api/session/delete", { sessionId })) ||
      (sessionId && await tryPost("/api/session/delete", { id: sessionId }));

    if (result) {
      hardRefresh();
      return;
    }

    active.remove();
    setStatus("Deleted");
  }

  function exportActiveSession() {
    const active = getActiveSessionItem();
    if (!active) {
      alert("Pick a chat first.");
      return;
    }

    const title = getSessionTitleFromItem(active) || "chat";
    const sessionId = getSessionIdFromItem(active) || "unknown";
    const lines = [
      `Title: ${title}`,
      `Session ID: ${sessionId}`,
      `Exported: ${new Date().toISOString()}`
    ];

    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/[^\w\-]+/g, "_") || "chat"}.txt`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function wireSessionClicks() {
    if (!els.sessionList) return;

    els.sessionList.addEventListener("click", (event) => {
      const item = event.target.closest(".session-item");
      if (!item) return;

      markActiveSession(item);

      if (isMobile()) {
        setSidebarOpen(false);
      }
    });
  }

  function wirePanelButtons() {
    els.toggleSidebar?.addEventListener("click", toggleSidebar);
    els.mobileSidebarBtn?.addEventListener("click", toggleSidebar);
    els.memoryToggleBtnTop?.addEventListener("click", toggleMemory);
    els.closeMemoryBtn?.addEventListener("click", toggleMemory);
  }

  function wireActionButtons() {
    els.renameSessionBtn?.addEventListener("click", renameActiveSession);
    els.duplicateSessionBtn?.addEventListener("click", duplicateActiveSession);
    els.pinSessionBtn?.addEventListener("click", pinActiveSession);
    els.deleteSessionBtn?.addEventListener("click", deleteActiveSession);
    els.exportSessionBtn?.addEventListener("click", exportActiveSession);
  }

  function wireSearch() {
    els.sessionSearchInput?.addEventListener("input", filterSessions);
  }

  function wireOutsideClose() {
    document.addEventListener("click", (event) => {
      if (!isMobile()) return;

      const target = event.target;

      const clickedInsideSidebar = !!els.sidebar?.contains(target);
      const clickedInsideMemory = !!els.memoryPanel?.contains(target);
      const clickedSidebarToggle =
        !!els.toggleSidebar?.contains(target) || !!els.mobileSidebarBtn?.contains(target);
      const clickedMemoryToggle =
        !!els.memoryToggleBtnTop?.contains(target) || !!els.closeMemoryBtn?.contains(target);

      if (
        els.sidebar &&
        els.sidebar.getAttribute("aria-hidden") === "false" &&
        !clickedInsideSidebar &&
        !clickedSidebarToggle
      ) {
        els.sidebar.setAttribute("aria-hidden", "true");
      }

      if (
        els.memoryPanel &&
        els.memoryPanel.getAttribute("aria-hidden") === "false" &&
        !clickedInsideMemory &&
        !clickedMemoryToggle
      ) {
        els.memoryPanel.setAttribute("aria-hidden", "true");
      }
    });
  }

  function wireResize() {
    window.addEventListener("resize", () => {
      if (isMobile()) {
        els.sidebar?.setAttribute("aria-hidden", "true");
        els.memoryPanel?.setAttribute("aria-hidden", "true");
      } else {
        els.sidebar?.setAttribute("aria-hidden", "false");
        els.memoryPanel?.setAttribute("aria-hidden", "false");
      }
    });
  }

  function bootstrapActiveSession() {
    const active = getActiveSessionItem() || getSessionItems()[0] || null;
    if (active) {
      markActiveSession(active);
    }
  }

  function init() {
    wirePanelButtons();
    wireActionButtons();
    wireSearch();
    wireSessionClicks();
    wireOutsideClose();
    wireResize();
    bootstrapActiveSession();
    setMemoryStatus("Repair layer loaded.");
    console.log("Nova phase 3 repair loaded.");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();